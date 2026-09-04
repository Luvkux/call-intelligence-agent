from src.audio.diarizer import SpeakerDiarizer

def test_diarizer_fallback_initialization():
    # Verify SpeakerDiarizer initializes without crashing even when HF_TOKEN is None
    diarizer = SpeakerDiarizer(hf_token=None)
    segments = [
        {"start": 0.0, "end": 2.5, "text": "Hello, how can I help?"},
        {"start": 3.0, "end": 6.0, "text": "I am calling about my balance."}
    ]
    # Check that fallback returns valid non-fake speaker turns
    turns = diarizer.diarize_fallback_clustering("non_existent_path.wav", segments)
    assert len(turns) == 2
    assert all("speaker" in turn for turn in turns)
    assert all(turn["speaker"].startswith("SPEAKER_") or turn["speaker"].startswith("Speaker ") for turn in turns)
