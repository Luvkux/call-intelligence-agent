from src.intelligence.compliance import ComplianceDetector

def test_cease_and_desist_detection():
    line = "I told you guys not to call me, take me off from your list!"
    flags = ComplianceDetector.check_line(line)
    assert len(flags) > 0
    assert flags[0]["category"] == "Cease & Desist"
    assert flags[0]["severity"] == "Red"

def test_legal_mention_detection():
    line = "I will sue you if you keep harassing me, contact my attorney."
    flags = ComplianceDetector.check_line(line)
    assert len(flags) > 0
    assert any(f["category"] == "Legal Mention" for f in flags)
    assert any(f["severity"] == "Red" for f in flags)

def test_consent_check():
    lines_with_consent = [
        {"line_number": 1, "text": "Agent: Thank you for calling. This call is being recorded for quality assurance."}
    ]
    check = ComplianceDetector.check_transcript_consent(lines_with_consent)
    assert check["has_consent"] is True

    lines_without_consent = [
        {"line_number": 1, "text": "Agent: Hello, I am calling regarding your account."}
    ]
    check_no = ComplianceDetector.check_transcript_consent(lines_without_consent)
    assert check_no["has_consent"] is False
