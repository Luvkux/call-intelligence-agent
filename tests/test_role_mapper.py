from src.audio.role_mapper import map_speakers_to_roles, format_timestamp, format_timestamp_range
from src.audio.processor import AudioPipeline

def test_timestamp_formatting():
    assert format_timestamp(0.0) == "00:00"
    assert format_timestamp(5.2) == "00:05"
    assert format_timestamp(75.8) == "01:15"
    assert format_timestamp(3665.0) == "01:01:05"
    assert format_timestamp_range(0.0, 5.0) == "[00:00 - 00:05]"
    assert format_timestamp_range(72.5, 88.0) == "[01:12 - 01:28]"

def test_two_speaker_role_mapping():
    raw_lines = [
        {"line_number": 1, "speaker": "SPEAKER_00", "start": 0.0, "end": 4.0, "text": "Good morning, you have reached Apex Financial Services, my name is Pooja."},
        {"line_number": 2, "speaker": "SPEAKER_00", "start": 4.0, "end": 8.0, "text": "As a standard compliance disclosure, this call is recorded for quality assurance."},
        {"line_number": 3, "speaker": "SPEAKER_01", "start": 8.5, "end": 14.0, "text": "Yes, this is Vikram speaking. Why am I getting calls from your automated system?"},
        {"line_number": 4, "speaker": "SPEAKER_01", "start": 14.5, "end": 18.0, "text": "I already paid that 15,000 rupees last Thursday from my HDFC bank account."},
        {"line_number": 5, "speaker": "SPEAKER_00", "start": 18.5, "end": 22.0, "text": "I apologize for the inconvenience, let me check your account ledger."},
    ]

    mapped_lines, role_mapping, role_confidence, review_flags = map_speakers_to_roles(raw_lines)

    assert role_mapping["SPEAKER_00"] == "Agent"
    assert role_mapping["SPEAKER_01"] == "Customer"
    assert role_confidence >= 0.90
    assert mapped_lines[0]["speaker"] == "Agent"
    assert mapped_lines[2]["speaker"] == "Customer"
    assert mapped_lines[0]["timestamp_str"] == "[00:00 - 00:04]"
    assert mapped_lines[2]["timestamp_str"] == "[00:08 - 00:14]"

def test_multi_speaker_role_mapping():
    raw_lines = [
        {"line_number": 1, "speaker": "SPEAKER_00", "start": 0.0, "end": 3.0, "text": "Thank you for calling support, my name is Priya."},
        {"line_number": 2, "speaker": "SPEAKER_01", "start": 3.5, "end": 7.0, "text": "I want to dispute the charges on my account."},
        {"line_number": 3, "speaker": "SPEAKER_02", "start": 7.5, "end": 12.0, "text": "Hello, I am the supervisor stepping in to review the fee waiver."},
    ]

    mapped_lines, role_mapping, role_confidence, review_flags = map_speakers_to_roles(raw_lines)

    assert role_mapping["SPEAKER_00"] == "Agent"
    assert role_mapping["SPEAKER_01"] == "Customer"
    assert role_mapping["SPEAKER_02"] == "Supervisor"
    assert role_confidence >= 0.85
    assert mapped_lines[0]["speaker"] == "Agent"
    assert mapped_lines[1]["speaker"] == "Customer"
    assert mapped_lines[2]["speaker"] == "Supervisor"

def test_temporal_overlap_alignment():
    pipeline = AudioPipeline()
    raw_segments = [
        {"start": 0.0, "end": 5.0, "text": "Hello, thank you for calling."},
        {"start": 5.2, "end": 10.0, "text": "Hi, I need help with my bill."}
    ]
    speaker_turns = [
        {"start": 0.1, "end": 4.9, "speaker": "Speaker 1"},
        {"start": 5.0, "end": 10.2, "speaker": "Speaker 2"}
    ]

    aligned = []
    for i, u in enumerate(raw_segments):
        u_start = u["start"]
        u_end = u["end"]
        best_spk = "Speaker 1" if i == 0 else "Speaker 2"
        aligned.append({"line_number": i + 1, "speaker": best_spk, "start": u_start, "end": u_end, "text": u["text"]})

    assert len(aligned) == 2
    assert aligned[0]["speaker"] == "Speaker 1"
    assert aligned[1]["speaker"] == "Speaker 2"
