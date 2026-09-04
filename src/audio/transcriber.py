import os
import subprocess
from typing import List, Dict, Any
import numpy as np
from pydub import AudioSegment
from faster_whisper import WhisperModel
import config

def decode_audio_to_pcm_array(audio_path: str, sampling_rate: int = 16000) -> np.ndarray:
    """
    Decodes audio into a 16kHz mono float32 NumPy array using FFmpeg CLI.
    This guarantees full un-truncated decoding for long files, variable bitrates,
    ID3 metadata frames, and non-standard MP3/WAV/M4A/OGG containers where PyAV aborts early.
    """
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", audio_path,
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sampling_rate),
        "-"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, check=True)
        audio = np.frombuffer(res.stdout, np.int16).flatten().astype(np.float32) / 32768.0
        return audio
    except Exception:
        # Fallback to pydub if direct ffmpeg invocation fails
        sound = AudioSegment.from_file(audio_path)
        sound = sound.set_frame_rate(sampling_rate).set_channels(1)
        raw_samples = sound.get_array_of_samples()
        return np.array(raw_samples).astype(np.float32) / 32768.0

class AudioTranscriber:
    """
    Transcribes audio using faster-whisper with word-level timestamps and VAD filtering.
    """

    def __init__(self, model_size: str = None, compute_type: str = None):
        self.model_size = model_size or config.WHISPER_MODEL_SIZE
        self.compute_type = compute_type or config.WHISPER_COMPUTE_TYPE
        self._model = None

    def _load_model(self):
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type=self.compute_type
            )
        return self._model

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Transcribe an audio file and return a list of segments with word timestamps:
        [
          {
            "start": float,
            "end": float,
            "text": str,
            "words": [{"word": str, "start": float, "end": float, "probability": float}]
          },
          ...
        ]
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Decode full audio into 16kHz mono float32 samples to prevent PyAV premature truncation
        audio_data = decode_audio_to_pcm_array(audio_path, sampling_rate=16000)
        if len(audio_data) == 0:
            return []

        model = self._load_model()
        segments_gen, info = model.transcribe(
            audio_data,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
            word_timestamps=True
        )

        result_segments = []
        for seg in segments_gen:
            text = seg.text.strip()
            if text:
                words_list = []
                if seg.words:
                    for w in seg.words:
                        words_list.append({
                            "word": w.word.strip(),
                            "start": round(w.start, 2),
                            "end": round(w.end, 2),
                            "probability": round(w.probability, 2)
                        })

                result_segments.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": text,
                    "words": words_list
                })

        return result_segments
