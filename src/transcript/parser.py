import re
import json
import csv
import io
from typing import List, Dict, Any, Optional, Tuple, Union
from src.audio.role_mapper import map_speakers_to_roles, format_timestamp_range, format_timestamp

def parse_timestamp_to_seconds(ts_val: Union[str, int, float, None]) -> Optional[float]:
    """
    Parses timestamp string or number into float seconds.
    Supported formats:
    - 4.5 -> 4.5
    - "00:04" -> 4.0
    - "01:23" -> 83.0
    - "01:23.450" -> 83.45
    - "00:01:23" -> 83.0
    - "00:01:23,450" -> 83.45
    - "00:01:23.450" -> 83.45
    """
    if ts_val is None:
        return None
    if isinstance(ts_val, (int, float)):
        return float(ts_val)

    ts_clean = str(ts_val).strip()
    if not ts_clean:
        return None

    # Replace comma decimal with dot (SRT style 00:01:23,450)
    ts_clean = ts_clean.replace(',', '.')

    # Pure numeric
    try:
        return float(ts_clean)
    except ValueError:
        pass

    parts = ts_clean.split(':')
    try:
        if len(parts) == 2:  # MM:SS or MM:SS.mmm
            mins = float(parts[0])
            secs = float(parts[1])
            return mins * 60.0 + secs
        elif len(parts) == 3:  # HH:MM:SS or HH:MM:SS.mmm
            hrs = float(parts[0])
            mins = float(parts[1])
            secs = float(parts[2])
            return hrs * 3600.0 + mins * 60.0 + secs
    except ValueError:
        return None

    return None

def normalize_role_name(raw_role: str) -> str:
    """Normalizes role strings into canonical Agent / Customer / Supervisor labels if explicit."""
    clean = raw_role.strip()
    lower = clean.lower()

    if lower in ("agent", "representative", "rep", "support", "advisor", "specialist"):
        return "Agent"
    if lower in ("customer", "client", "caller", "user", "borrower"):
        return "Customer"
    if lower in ("supervisor", "manager", "team lead", "lead"):
        return "Supervisor"

    return clean

def parse_transcript_text(text: str) -> List[Dict[str, Any]]:
    """
    Parses unstructured or structured plain text transcript into list of raw turn dicts.
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    raw_turns = []
    current_turn = None

    # Regex patterns for line matching
    # Pattern 1: [00:00 - 00:04] Speaker: Text OR [00:00-00:04] [Speaker]: Text
    p_range_first = re.compile(r'^\s*\[?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*(?:-|–|to)\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*\]?\s*\[?([^:\]\n]+?)\]?\s*:\s*(.*)$', re.IGNORECASE)

    # Pattern 2: Speaker [00:00 - 00:04]: Text
    p_spk_first = re.compile(r'^\s*\[?([^:\[\]\n]+?)\]?\s*\[\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*(?:-|–|to)\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*\]\s*:\s*(.*)$', re.IGNORECASE)

    # Pattern 3: [00:00] Speaker: Text OR 00:00 Speaker: Text
    p_single_ts = re.compile(r'^\s*\[?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*\]?\s*\[?([^:\]\n]+?)\]?\s*:\s*(.*)$', re.IGNORECASE)

    # Pattern 4: Speaker: Text (no timestamp)
    p_no_ts = re.compile(r'^\s*\[?([A-Za-z0-9_\- ]{1,40}?)\]?\s*:\s*(.*)$')

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Try Pattern 1: [00:00 - 00:04] Speaker: Text
        m = p_range_first.match(line_str)
        if m:
            if current_turn:
                raw_turns.append(current_turn)
            start_sec = parse_timestamp_to_seconds(m.group(1))
            end_sec = parse_timestamp_to_seconds(m.group(2))
            speaker = normalize_role_name(m.group(3))
            content = m.group(4).strip()
            current_turn = {"start": start_sec, "end": end_sec, "speaker": speaker, "text": content}
            continue

        # Try Pattern 2: Speaker [00:00 - 00:04]: Text
        m = p_spk_first.match(line_str)
        if m:
            if current_turn:
                raw_turns.append(current_turn)
            speaker = normalize_role_name(m.group(1))
            start_sec = parse_timestamp_to_seconds(m.group(2))
            end_sec = parse_timestamp_to_seconds(m.group(3))
            content = m.group(4).strip()
            current_turn = {"start": start_sec, "end": end_sec, "speaker": speaker, "text": content}
            continue

        # Try Pattern 3: [00:00] Speaker: Text
        m = p_single_ts.match(line_str)
        if m:
            spk_candidate = m.group(2).strip()
            if len(spk_candidate) <= 30:
                if current_turn:
                    raw_turns.append(current_turn)
                start_sec = parse_timestamp_to_seconds(m.group(1))
                speaker = normalize_role_name(spk_candidate)
                content = m.group(3).strip()
                current_turn = {"start": start_sec, "end": None, "speaker": speaker, "text": content}
                continue

        # Try Pattern 4: Speaker: Text (no timestamp)
        m = p_no_ts.match(line_str)
        if m:
            spk_candidate = m.group(1).strip()
            if len(spk_candidate) <= 30 and not spk_candidate.lower().startswith(('http', 'https', 'ftp', 'note', 'line')):
                if current_turn:
                    raw_turns.append(current_turn)
                speaker = normalize_role_name(spk_candidate)
                content = m.group(2).strip()
                current_turn = {"start": None, "end": None, "speaker": speaker, "text": content}
                continue

        # If line starts with "Line N: Speaker: Text"
        p_line_prefix = re.compile(r'^\s*Line\s+\d+\s*(?:\[([^\]]+)\])?\s*\[?([^:\]\n]+?)\]?\s*:\s*(.*)$', re.IGNORECASE)
        m = p_line_prefix.match(line_str)
        if m:
            if current_turn:
                raw_turns.append(current_turn)
            ts_part = m.group(1)
            start_sec, end_sec = None, None
            if ts_part:
                ts_splits = re.split(r'[-–to]', ts_part)
                if len(ts_splits) == 2:
                    start_sec = parse_timestamp_to_seconds(ts_splits[0])
                    end_sec = parse_timestamp_to_seconds(ts_splits[1])
                elif len(ts_splits) == 1:
                    start_sec = parse_timestamp_to_seconds(ts_splits[0])
            speaker = normalize_role_name(m.group(2))
            content = m.group(3).strip()
            current_turn = {"start": start_sec, "end": end_sec, "speaker": speaker, "text": content}
            continue

        # Multiline continuation
        if current_turn:
            current_turn["text"] += " " + line_str
        else:
            current_turn = {"start": None, "end": None, "speaker": "Speaker 0", "text": line_str}

    if current_turn:
        raw_turns.append(current_turn)

    for i in range(len(raw_turns) - 1):
        if raw_turns[i]["start"] is not None and raw_turns[i]["end"] is None:
            if raw_turns[i+1]["start"] is not None:
                raw_turns[i]["end"] = raw_turns[i+1]["start"]

    return raw_turns

def parse_srt(content: str) -> List[Dict[str, Any]]:
    """Parses SubRip (.srt) and WebVTT (.vtt) subtitle format."""
    clean_content = re.sub(r'^WEBVTT.*?\n', '', content.strip(), flags=re.IGNORECASE).strip()
    blocks = re.split(r'\n\s*\n', clean_content)
    raw_turns = []

    time_pattern = re.compile(r'(\d{1,2}:(?:\d{2}:)?\d{2}[,\.]\d{2,3})\s*-->\s*(\d{1,2}:(?:\d{2}:)?\d{2}[,\.]\d{2,3})')

    for block in blocks:
        block_lines = [b.strip() for b in block.splitlines() if b.strip()]
        if not block_lines:
            continue

        time_line_idx = -1
        m = None
        for idx, bl in enumerate(block_lines):
            m = time_pattern.search(bl)
            if m:
                time_line_idx = idx
                break

        if not m or time_line_idx == -1:
            continue

        start_sec = parse_timestamp_to_seconds(m.group(1))
        end_sec = parse_timestamp_to_seconds(m.group(2))

        text_lines = block_lines[time_line_idx + 1:]
        full_text = " ".join(text_lines)

        # Check for Speaker: Text prefix
        spk_match = re.match(r'^\s*\[?([A-Za-z0-9_\- ]{1,30}?)\]?\s*:\s*(.*)$', full_text)
        if spk_match:
            speaker = normalize_role_name(spk_match.group(1))
            text_val = spk_match.group(2).strip()
        else:
            # Check for <v Speaker>Text</v> voice tag
            v_match = re.match(r'^\s*<v\s+([^>]+)>(.*)$', full_text)
            if v_match:
                speaker = normalize_role_name(v_match.group(1))
                text_val = re.sub(r'</v>', '', v_match.group(2)).strip()
            else:
                speaker = "Speaker 0"
                text_val = full_text

        raw_turns.append({
            "start": start_sec,
            "end": end_sec,
            "speaker": speaker,
            "text": text_val
        })

    return raw_turns

def parse_vtt(content: str) -> List[Dict[str, Any]]:
    """Parses WebVTT (.vtt) subtitle format."""
    return parse_srt(content)

def parse_json_transcript(content: str) -> List[Dict[str, Any]]:
    """Parses JSON format transcript (list or nested structure)."""
    data = json.loads(content)
    items = []

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("transcript", "lines", "turns", "segments", "utterances", "dialogue", "data"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        if not items and "text" in data:
            return parse_transcript_text(data["text"])

    raw_turns = []
    for item in items:
        if isinstance(item, str):
            parsed_sub = parse_transcript_text(item)
            raw_turns.extend(parsed_sub)
            continue

        if not isinstance(item, dict):
            continue

        speaker = (
            item.get("speaker") or item.get("role") or item.get("speakerId") or
            item.get("speaker_id") or item.get("speaker_name") or "Speaker 0"
        )
        text_val = (
            item.get("text") or item.get("content") or item.get("transcript") or
            item.get("utterance") or item.get("message") or ""
        )
        
        # Use explicit key check to prevent 0.0 evaluating as falsy
        start_val = None
        for sk in ("start", "startTime", "start_time", "begin", "start_sec"):
            if sk in item and item[sk] is not None:
                start_val = item[sk]
                break

        end_val = None
        for ek in ("end", "endTime", "end_time", "finish", "end_sec"):
            if ek in item and item[ek] is not None:
                end_val = item[ek]
                break

        start_sec = parse_timestamp_to_seconds(start_val)
        end_sec = parse_timestamp_to_seconds(end_val)

        if text_val:
            raw_turns.append({
                "start": start_sec,
                "end": end_sec,
                "speaker": normalize_role_name(str(speaker)),
                "text": str(text_val).strip()
            })

    return raw_turns

def parse_csv_transcript(content: str) -> List[Dict[str, Any]]:
    """Parses CSV format transcript."""
    reader = csv.reader(io.StringIO(content.strip()))
    rows = list(reader)
    if not rows:
        return []

    # Check header
    header = [h.strip().lower() for h in rows[0]]
    spk_col, text_col, start_col, end_col = -1, -1, -1, -1

    for idx, col_name in enumerate(header):
        if col_name in ("speaker", "role", "speaker_id", "speakerid", "person", "agent_customer"):
            spk_col = idx
        elif col_name in ("text", "transcript", "utterance", "content", "message", "dialogue", "line"):
            text_col = idx
        elif col_name in ("start", "start_time", "starttime", "start_sec", "time", "timestamp"):
            start_col = idx
        elif col_name in ("end", "end_time", "endtime", "end_sec"):
            end_col = idx

    start_row = 1 if (spk_col != -1 or text_col != -1) else 0

    # If no header detected, infer by column count
    if spk_col == -1 and text_col == -1:
        if len(rows[0]) == 2:
            spk_col, text_col = 0, 1
        elif len(rows[0]) >= 3:
            if parse_timestamp_to_seconds(rows[0][0]) is not None:
                start_col, spk_col, text_col = 0, 1, 2
            else:
                spk_col, text_col, start_col = 0, 1, 2

    raw_turns = []
    for r in rows[start_row:]:
        if not r or len(r) == 0:
            continue
        speaker = r[spk_col].strip() if (0 <= spk_col < len(r)) else "Speaker 0"
        text_val = r[text_col].strip() if (0 <= text_col < len(r)) else ""
        start_sec = parse_timestamp_to_seconds(r[start_col]) if (0 <= start_col < len(r)) else None
        end_sec = parse_timestamp_to_seconds(r[end_col]) if (0 <= end_col < len(r)) else None

        if text_val:
            raw_turns.append({
                "start": start_sec,
                "end": end_sec,
                "speaker": normalize_role_name(speaker),
                "text": text_val
            })

    return raw_turns

def parse_transcript(
    content_or_file: Union[str, bytes],
    filename: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str], float, List[Dict[str, Any]]]:
    """
    Main entry point for parsing any transcript file or pasted string.
    """
    if isinstance(content_or_file, bytes):
        try:
            content = content_or_file.decode('utf-8')
        except UnicodeDecodeError:
            content = content_or_file.decode('latin-1')
    else:
        content = str(content_or_file)

    content_clean = content.strip()
    if not content_clean:
        raise ValueError("Transcript is empty. Please upload a valid transcript file or paste transcript text.")

    fn_lower = filename.lower() if filename else ""

    # Dispatch to specific parser based on filename or content detection
    if fn_lower.endswith(".json") or (content_clean.startswith("{") and content_clean.endswith("}")) or (content_clean.startswith("[") and content_clean.endswith("]")):
        try:
            raw_turns = parse_json_transcript(content_clean)
        except Exception:
            raw_turns = parse_transcript_text(content_clean)
    elif fn_lower.endswith(".srt"):
        raw_turns = parse_srt(content_clean)
    elif fn_lower.endswith(".vtt") or content_clean.startswith("WEBVTT"):
        raw_turns = parse_vtt(content_clean)
    elif fn_lower.endswith(".csv"):
        raw_turns = parse_csv_transcript(content_clean)
    else:
        raw_turns = parse_transcript_text(content_clean)

    if not raw_turns:
        raise ValueError("Could not parse any dialogue turns from the transcript. Please check the transcript format.")

    # Assign sequential 1-based line numbers to prepare for canonical mapping
    aligned_lines = []
    for i, turn in enumerate(raw_turns):
        aligned_lines.append({
            "line_number": i + 1,
            "speaker": turn.get("speaker", "Speaker 0"),
            "start": turn.get("start"),
            "end": turn.get("end"),
            "text": turn["text"]
        })

    # Run deterministic role mapping to establish global stable Agent / Customer mapping
    mapped_lines, role_mapping, role_confidence, review_flags = map_speakers_to_roles(aligned_lines)

    # Ensure canonical timestamps formatting
    for line in mapped_lines:
        start_t = line.get("start")
        end_t = line.get("end")
        line["timestamp_str"] = format_timestamp_range(start_t, end_t)

    return mapped_lines, role_mapping, role_confidence, review_flags
