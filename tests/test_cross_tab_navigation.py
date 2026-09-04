import pytest
from src.utils.helpers import render_line_pills
from src.db.database import SessionLocal, init_db
from src.db.models import CallRecord, TranscriptLineRecord

def test_render_line_pills_client_navigation():
    """
    Verifies that render_line_pills generates correct client-side onclick handlers
    targeting the original transcript tab with specific line numbers and call IDs
    without triggering full page refreshes.
    """
    # 1. Without call_id
    html_no_call = render_line_pills([61])
    assert 'href="#transcript-line-61"' in html_no_call
    assert 'window.jumpToTranscriptLine(61, null)' in html_no_call
    assert 'Line 61' in html_no_call

    # 2. With call_id=125
    html_with_call = render_line_pills([61], call_id=125)
    assert 'href="#transcript-line-61"' in html_with_call
    assert 'window.jumpToTranscriptLine(61, 125)' in html_with_call
    assert 'Line 61' in html_with_call

    # 3. Multi-line citation (e.g. Line 59, 60, 61)
    html_multi = render_line_pills([59, 60, 61], call_id=125)
    assert 'window.jumpToTranscriptLine(59, 125)' in html_multi
    assert 'window.jumpToTranscriptLine(60, 125)' in html_multi
    assert 'window.jumpToTranscriptLine(61, 125)' in html_multi

    # 4. Empty list returns "None"
    assert render_line_pills([]) == "None"

def test_canonical_line_isolation_across_calls(tmp_path):
    """
    Verifies that Line 61 in Call #125 and Line 61 in Call #124 are strictly isolated
    in SQLite database and mapped accurately to their own call_id.
    """
    init_db()
    db = SessionLocal()

    # Create Call 124
    call_124 = CallRecord(title="Call 124 - Dispute", summary="Dispute call")
    db.add(call_124)
    db.commit()
    db.refresh(call_124)

    line_124_61 = TranscriptLineRecord(
        call_id=call_124.id,
        line_number=61,
        speaker="Customer",
        text="This is Call 124 line 61 text."
    )
    db.add(line_124_61)

    # Create Call 125
    call_125 = CallRecord(title="Call 125 - Apex Cease & Desist", summary="Cease & Desist call")
    db.add(call_125)
    db.commit()
    db.refresh(call_125)

    line_125_60 = TranscriptLineRecord(
        call_id=call_125.id,
        line_number=60,
        speaker="Agent",
        text="I understand your frustration."
    )
    line_125_61 = TranscriptLineRecord(
        call_id=call_125.id,
        line_number=61,
        speaker="Customer",
        text="Please take my number off that call list immediately."
    )
    db.add_all([line_125_60, line_125_61])
    db.commit()

    # Query Call 125 line 61
    res_125 = db.query(TranscriptLineRecord).filter(
        TranscriptLineRecord.call_id == call_125.id,
        TranscriptLineRecord.line_number == 61
    ).first()

    assert res_125 is not None
    assert res_125.text == "Please take my number off that call list immediately."

    # Query Call 124 line 61
    res_124 = db.query(TranscriptLineRecord).filter(
        TranscriptLineRecord.call_id == call_124.id,
        TranscriptLineRecord.line_number == 61
    ).first()

    assert res_124 is not None
    assert res_124.text == "This is Call 124 line 61 text."
    assert res_124.text != res_125.text

    # Verify query for non-existent Line 999
    res_non_existent = db.query(TranscriptLineRecord).filter(
        TranscriptLineRecord.call_id == call_125.id,
        TranscriptLineRecord.line_number == 999
    ).first()
    assert res_non_existent is None

    db.close()
