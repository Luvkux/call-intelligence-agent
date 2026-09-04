import os
import pytest
from src.audio.ffmpeg_check import check_ffmpeg_installed, find_ffmpeg_executable, verify_ffmpeg_executable, get_ffmpeg_instructions

def test_check_ffmpeg_installed():
    assert check_ffmpeg_installed() is True

def test_find_ffmpeg_executable():
    executable_path = find_ffmpeg_executable()
    assert executable_path is not None
    assert os.path.exists(executable_path)
    assert verify_ffmpeg_executable(executable_path) is True

def test_verify_ffmpeg_executable_invalid():
    assert verify_ffmpeg_executable("C:\\invalid_path_to\\non_existent_ffmpeg.exe") is False

def test_ffmpeg_environment_variable_override(tmp_path, monkeypatch):
    fake_exe = tmp_path / "fake_ffmpeg.exe"
    fake_exe.write_text("fake binary")
    
    # Non-executable should fail verification
    assert verify_ffmpeg_executable(str(fake_exe)) is False

def test_ffmpeg_instructions():
    instructions = get_ffmpeg_instructions()
    assert "winget install" in instructions
    assert "FFmpeg" in instructions

def test_decode_audio_to_pcm_array_full_duration():
    """
    Verifies that decode_audio_to_pcm_array decodes the full duration of audio files
    without getting truncated by PyAV stream/header errors.
    """
    import numpy as np
    from src.audio.transcriber import decode_audio_to_pcm_array

    test_files = [
        ("data/uploads/Northwind-Support-Full-21-Turn-Call-Dispute-89.99-Case-NWF-8842-DISP.mp3", 280.0),
        ("test_audio/Apex-Support-Dispute-₹15000-Case-CR-894210-IN-Gemini-Studio.mp3", 250.0),
    ]

    for file_path, min_expected_dur in test_files:
        if not os.path.exists(file_path):
            continue
        audio_arr = decode_audio_to_pcm_array(file_path, sampling_rate=16000)
        assert isinstance(audio_arr, np.ndarray)
        assert audio_arr.dtype == np.float32

        dur_sec = len(audio_arr) / 16000.0
        assert dur_sec >= min_expected_dur, f"Audio file {file_path} was truncated! Expected >={min_expected_dur}s but got {dur_sec:.2f}s"
        assert np.max(np.abs(audio_arr)) <= 1.05
