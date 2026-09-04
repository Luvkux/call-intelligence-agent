import pytest
from src.transcript.parser import parse_transcript, parse_timestamp_to_seconds, parse_transcript_text

def test_parse_timestamp_to_seconds():
    assert parse_timestamp_to_seconds(None) is None
    assert parse_timestamp_to_seconds(4.5) == 4.5
    assert parse_timestamp_to_seconds("00:04") == 4.0
    assert parse_timestamp_to_seconds("01:23") == 83.0
    assert parse_timestamp_to_seconds("01:23.450") == 83.45
    assert parse_timestamp_to_seconds("00:01:23,500") == 83.5
    assert parse_timestamp_to_seconds("01:00:05") == 3605.0

def test_plain_text_with_bracket_timestamps():
    txt = """
    [00:00 - 00:04] Agent: Good morning, you have reached Apex Financial Services, my name is Pooja.
    [00:05 - 00:08] Customer: Yes, this is Vikram speaking. I have a problem with my payment.
    [00:09 - 00:14] Agent: I understand, let me pull up your account right away.
    """
    lines, mapping, conf, flags = parse_transcript(txt)
    assert len(lines) == 3
    assert lines[0]["line_number"] == 1
    assert lines[0]["speaker"] == "Agent"
    assert lines[0]["start"] == 0.0
    assert lines[0]["end"] == 4.0
    assert lines[0]["timestamp_str"] == "[00:00 - 00:04]"
    assert "Good morning" in lines[0]["text"]

    assert lines[1]["line_number"] == 2
    assert lines[1]["speaker"] == "Customer"
    assert lines[1]["start"] == 5.0
    assert lines[1]["end"] == 8.0
    assert lines[1]["timestamp_str"] == "[00:05 - 00:08]"

    assert lines[2]["line_number"] == 3
    assert lines[2]["speaker"] == "Agent"

def test_plain_text_without_timestamps():
    txt = """
    Agent: Good morning, you have reached Apex Financial Services.
    Customer: Hi, I'm calling about my account settlement offer.
    Agent: Thank you. Our total balance is $1,400.
    """
    lines, mapping, conf, flags = parse_transcript(txt)
    assert len(lines) == 3
    assert lines[0]["line_number"] == 1
    assert lines[0]["speaker"] == "Agent"
    assert lines[0]["start"] is None
    assert lines[0]["end"] is None
    assert lines[0]["timestamp_str"] == "Timestamp unavailable"
    assert lines[1]["speaker"] == "Customer"
    assert lines[1]["timestamp_str"] == "Timestamp unavailable"

def test_speaker_0_1_contextual_role_mapping():
    txt = """
    Speaker 0: Thank you for calling North Wind Financial Customer Care. My name is Marcus. How can I help you today?
    Speaker 1: Hi Marcus, I am looking at my monthly statement and there is an unauthorized charge for $89.99.
    Speaker 0: I can certainly help you look into that right away.
    """
    lines, mapping, conf, flags = parse_transcript(txt)
    assert len(lines) == 3
    assert mapping["Speaker 0"] == "Agent"
    assert mapping["Speaker 1"] == "Customer"
    assert lines[0]["speaker"] == "Agent"
    assert lines[1]["speaker"] == "Customer"
    assert lines[2]["speaker"] == "Agent"

def test_srt_parsing():
    srt_content = """
    1
    00:00:00,000 --> 00:00:04,000
    Agent: Good morning, you have reached support.

    2
    00:00:04,500 --> 00:00:08,000
    Customer: I want to check my account balance.
    """
    lines, mapping, conf, flags = parse_transcript(srt_content, filename="call.srt")
    assert len(lines) == 2
    assert lines[0]["line_number"] == 1
    assert lines[0]["speaker"] == "Agent"
    assert lines[0]["start"] == 0.0
    assert lines[0]["end"] == 4.0
    assert lines[1]["speaker"] == "Customer"
    assert lines[1]["start"] == 4.5
    assert lines[1]["end"] == 8.0

def test_vtt_parsing():
    vtt_content = """WEBVTT

    00:00.000 --> 00:04.000
    <v Agent>Good morning, you have reached support.</v>

    00:04.500 --> 00:08.000
    <v Customer>I want to check my account balance.</v>
    """
    lines, mapping, conf, flags = parse_transcript(vtt_content, filename="call.vtt")
    assert len(lines) == 2
    assert lines[0]["line_number"] == 1
    assert lines[0]["speaker"] == "Agent"
    assert lines[1]["speaker"] == "Customer"

def test_json_parsing():
    json_content = """
    [
        {"start": 0.0, "end": 4.0, "speaker": "Agent", "text": "Good morning, how can I help you?"},
        {"start": 4.5, "end": 8.0, "speaker": "Customer", "text": "I need help with my bill."}
    ]
    """
    lines, mapping, conf, flags = parse_transcript(json_content, filename="transcript.json")
    assert len(lines) == 2
    assert lines[0]["line_number"] == 1
    assert lines[0]["speaker"] == "Agent"
    assert lines[0]["start"] == 0.0
    assert lines[1]["speaker"] == "Customer"

def test_csv_parsing():
    csv_content = """Speaker,Text,Start,End
    Agent,Good morning how can I help you?,00:00,00:04
    Customer,I have a dispute with a charge.,00:05,00:10
    """
    lines, mapping, conf, flags = parse_transcript(csv_content, filename="transcript.csv")
    assert len(lines) == 2
    assert lines[0]["line_number"] == 1
    assert lines[0]["speaker"] == "Agent"
    assert lines[0]["start"] == 0.0
    assert lines[0]["end"] == 4.0
    assert lines[1]["speaker"] == "Customer"

def test_empty_transcript_raises_error():
    with pytest.raises(ValueError):
        parse_transcript("   \n\t  ")
