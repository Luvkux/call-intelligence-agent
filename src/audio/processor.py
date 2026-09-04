import os
import re
from typing import List, Dict, Any, Tuple
from src.audio.transcriber import AudioTranscriber
from src.audio.diarizer import SpeakerDiarizer
from src.audio.role_mapper import map_speakers_to_roles, format_timestamp_range
from src.audio.ffmpeg_check import check_ffmpeg_installed

COMMON_ABBREVIATIONS = {"mr.", "mrs.", "ms.", "dr.", "prof.", "p.m.", "a.m.", "pm.", "am.", "e.g.", "i.e.", "govt.", "ltd.", "inc.", "corp.", "u.s.", "u.k.", "rbi."}

class AudioPipeline:
    """
    Orchestrates transcription and speaker diarization into a line-indexed transcript
    with exact timestamps, speaker segmentation, and deterministic Customer/Agent role mapping.
    """

    def __init__(self, hf_token: str = None):
        self.transcriber = AudioTranscriber()
        self.diarizer = SpeakerDiarizer(hf_token=hf_token)
        self.last_role_mapping: Dict[str, str] = {}
        self.last_role_confidence: float = 1.0
        self.last_review_flags: List[Dict[str, Any]] = []

    def _split_into_clean_utterances(self, raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits STT segments at natural sentence & clause boundaries using word timestamps,
        preventing multiple speakers or disjoint turns from being fused into a single line.
        Avoids splitting on common titles/abbreviations (Mr., Mrs., p.m., etc.).
        """
        utterances = []

        for seg in raw_segments:
            words = seg.get("words", [])
            if not words:
                utterances.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })
                continue

            current_words = []
            for i, w in enumerate(words):
                current_words.append(w)
                word_clean = w["word"].strip().lower()

                # Check if this word ends a sentence and is not an abbreviation
                ends_punct = any(w["word"].strip().endswith(p) for p in [".", "?", "!", ":"])
                is_abbrev = word_clean in COMMON_ABBREVIATIONS

                # Check if there is a noticeable inter-word pause (> 0.65s) to the next word
                has_pause = False
                if i + 1 < len(words):
                    gap = words[i+1]["start"] - w["end"]
                    if gap >= 0.65:
                        has_pause = True

                if (ends_punct and not is_abbrev) or has_pause:
                    u_start = current_words[0]["start"]
                    u_end = current_words[-1]["end"]
                    u_text = " ".join(cw["word"].strip() for cw in current_words)
                    # Clean up punctuation spacing
                    u_text = re.sub(r'\s+([,.:;?!])', r'\1', u_text)
                    if u_text:
                        utterances.append({
                            "start": u_start,
                            "end": u_end,
                            "text": u_text
                        })
                    current_words = []

            if current_words:
                u_start = current_words[0]["start"]
                u_end = current_words[-1]["end"]
                u_text = " ".join(cw["word"].strip() for cw in current_words)
                u_text = re.sub(r'\s+([,.:;?!])', r'\1', u_text)
                if u_text:
                    utterances.append({
                        "start": u_start,
                        "end": u_end,
                        "text": u_text
                    })

        return utterances

    def process_audio(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Process audio file and return a list of line-indexed dialogue turns with
        exact timestamps and deterministic role mapping (Agent / Customer):
        [
          {
            "line_number": 1,
            "speaker": "Agent",
            "start": 0.0,
            "end": 3.54,
            "timestamp_str": "[00:00 - 00:03]",
            "text": "Good morning, you have reached Apex Financial Services."
          },
          ...
        ]
        """
        if not check_ffmpeg_installed():
            raise RuntimeError("FFmpeg is missing from system environment. Please install FFmpeg.")

        # 1. Speech-to-Text with word timestamps
        raw_segments = self.transcriber.transcribe(audio_path)
        if not raw_segments:
            return []

        # 2. Refine into clean, non-fused sentence utterances
        utterances = self._split_into_clean_utterances(raw_segments)

        # 3. Speaker Diarization with timestamps
        speaker_turns = self.diarizer.diarize(audio_path, utterances)

        # 4. Temporal Overlap Alignment
        aligned_raw_lines = []
        for i, u in enumerate(utterances):
            u_start = u["start"]
            u_end = u["end"]
            u_dur = max(0.01, u_end - u_start)

            speaker_overlaps: Dict[str, float] = {}
            for turn in speaker_turns:
                overlap_start = max(u_start, turn["start"])
                overlap_end = min(u_end, turn["end"])
                overlap = max(0.0, overlap_end - overlap_start)
                if overlap > 0:
                    spk = turn["speaker"]
                    speaker_overlaps[spk] = speaker_overlaps.get(spk, 0.0) + overlap

            if speaker_overlaps:
                best_speaker = max(speaker_overlaps.items(), key=lambda x: x[1])[0]
                overlapping_speakers = [
                    spk for spk, ov in speaker_overlaps.items() if (ov / u_dur) >= 0.25
                ]
                has_overlap = len(overlapping_speakers) > 1
            else:
                best_speaker = "SPEAKER_00"
                overlapping_speakers = ["SPEAKER_00"]
                has_overlap = False

            aligned_raw_lines.append({
                "line_number": i + 1,
                "speaker": best_speaker,
                "start": round(u_start, 2),
                "end": round(u_end, 2),
                "overlap": has_overlap,
                "overlapping_speakers": overlapping_speakers if has_overlap else [],
                "text": u["text"]
            })

        # 5. Global Deterministic Customer vs Agent Role Mapping
        mapped_lines, role_mapping, role_confidence, review_flags = map_speakers_to_roles(aligned_raw_lines)
        self.last_role_mapping = role_mapping
        self.last_role_confidence = role_confidence
        self.last_review_flags = review_flags

        # If overlapping speech was detected, create human review flags
        overlap_lines = [l for l in mapped_lines if l.get("overlap")]
        if overlap_lines:
            self.last_review_flags.append({
                "reason": "Overlapping Speech Detected",
                "description": f"Overlapping speech detected across multiple speakers in lines: {[l['line_number'] for l in overlap_lines]}.",
                "line_numbers": [l["line_number"] for l in overlap_lines],
                "source_excerpt": overlap_lines[0]["text"]
            })

        # If role confidence is low, create human review flag
        if role_confidence < 0.70:
            self.last_review_flags.append({
                "reason": "Low Speaker Role Confidence",
                "description": f"Speaker role assignment has low confidence ({role_confidence*100:.1f}%). Please verify Agent vs Customer assignment.",
                "line_numbers": [1],
                "source_excerpt": mapped_lines[0]["text"] if mapped_lines else ""
            })

        return mapped_lines

def format_transcript_as_text(lines: List[Dict[str, Any]]) -> str:
    """
    Converts line-indexed dialogue dictionaries into plain formatted text for LLM:
    Line 1: Agent: Text...
    Line 2: Customer: Text...
    """
    formatted_lines = []
    for line in lines:
        formatted_lines.append(f"Line {line['line_number']}: {line['speaker']}: {line['text']}")
    return "\n".join(formatted_lines)
