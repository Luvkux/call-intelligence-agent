from datetime import datetime
from src.db.database import SessionLocal, init_db
from src.db.models import CallRecord, TranscriptLineRecord, ExtractedNoteRecord, HumanReviewRecord, AuditLogRecord
from src.db.vector_store import VectorStore

def test_call_record_session_lifecycle_and_persistence(tmp_path):
    init_db()
    
    # 1. Create CallRecord in session
    db = SessionLocal()
    call_rec = CallRecord(
        title="Test Settlement Call",
        recording_date=datetime(2026, 7, 1),
        short_tag="Settlement Test",
        summary="Test summary",
        overall_sentiment="Neutral"
    )
    db.add(call_rec)
    db.commit()
    db.refresh(call_rec)

    call_id = call_rec.id
    call_title = call_rec.title

    # Add child records
    db.add(TranscriptLineRecord(call_id=call_id, line_number=1, speaker="Agent", text="Hello"))
    db.add(ExtractedNoteRecord(call_id=call_id, item_type="Decision", title="Split approved", line_numbers=[1], source_excerpt="Hello"))
    db.commit()
    
    # 2. Close session
    db.close()

    # 3. Verify post-close attribute access does NOT raise DetachedInstanceError due to expire_on_commit=False
    assert call_rec.id == call_id
    assert call_rec.title == "Test Settlement Call"
    assert call_rec.short_tag == "Settlement Test"

    # 4. Verify record can be retrieved from fresh session
    db2 = SessionLocal()
    retrieved = db2.query(CallRecord).filter(CallRecord.id == call_id).first()
    assert retrieved is not None
    assert retrieved.title == "Test Settlement Call"
    assert len(retrieved.lines) == 1
    assert len(retrieved.notes) == 1
    db2.close()

def test_human_review_isolation_by_active_call_id(tmp_path):
    """
    Verifies that querying HumanReviewRecord by call_id isolates records
    between Call A (e.g. PDF sample) and Call B (e.g. new audio upload).
    """
    init_db()
    db = SessionLocal()

    # Create Call A (PDF Sample)
    call_a = CallRecord(
        title="Call A - PDF Sample",
        recording_date=datetime(2026, 7, 1),
        short_tag="Sample",
        summary="PDF summary"
    )
    db.add(call_a)
    db.commit()
    db.refresh(call_a)

    # Add review items to Call A
    db.add(HumanReviewRecord(
        call_id=call_a.id,
        reason="Supervisor Approval Required",
        description="Split settlement requires supervisor approval.",
        line_numbers_json="[5]",
        source_excerpt="I will need a supervisor to approve",
        status="Pending"
    ))
    db.commit()

    # Create Call B (New Audio Call)
    call_b = CallRecord(
        title="Call B - New Uploaded Audio",
        recording_date=datetime(2026, 7, 2),
        short_tag="Audio Dispute",
        summary="Customer dispute summary"
    )
    db.add(call_b)
    db.commit()
    db.refresh(call_b)

    # Add review items to Call B
    db.add(HumanReviewRecord(
        call_id=call_b.id,
        reason="Legal Threat Detected",
        description="Customer mentioned consulting an attorney.",
        line_numbers_json="[12]",
        source_excerpt="I am going to speak to my lawyer",
        status="Pending"
    ))
    db.commit()

    # Create Call C (Call with NO review items)
    call_c = CallRecord(
        title="Call C - Clean Routine Call",
        recording_date=datetime(2026, 7, 3),
        short_tag="Clean",
        summary="Routine inquiry"
    )
    db.add(call_c)
    db.commit()
    db.refresh(call_c)

    # 1. Verify querying for active_call_id = call_b.id returns ONLY Call B's items
    active_id_b = call_b.id
    items_b = db.query(HumanReviewRecord).filter(
        HumanReviewRecord.call_id == active_id_b,
        HumanReviewRecord.status == "Pending"
    ).all()
    assert len(items_b) == 1
    assert items_b[0].reason == "Legal Threat Detected"
    assert items_b[0].call_id == call_b.id

    # 2. Verify Call A's items are NOT present in Call B's query
    assert all(item.call_id == active_id_b for item in items_b)

    # 3. Verify querying for active_call_id = call_a.id returns ONLY Call A's items
    active_id_a = call_a.id
    items_a = db.query(HumanReviewRecord).filter(
        HumanReviewRecord.call_id == active_id_a,
        HumanReviewRecord.status == "Pending"
    ).all()
    assert len(items_a) == 1
    assert items_a[0].reason == "Supervisor Approval Required"
    assert items_a[0].call_id == call_a.id

    # 4. Verify querying for active_call_id = call_c.id returns empty list (empty state)
    active_id_c = call_c.id
    items_c = db.query(HumanReviewRecord).filter(
        HumanReviewRecord.call_id == active_id_c,
        HumanReviewRecord.status == "Pending"
    ).all()
    assert len(items_c) == 0

    db.close()

def test_vector_store_call_id_scoping(tmp_path):
    """
    Verifies that VectorStore.search with call_id scoping returns only
    transcript lines belonging to that specific call.
    """
    vstore = VectorStore(index_dir=str(tmp_path / "faiss"))
    
    # Add transcript lines for Call 1
    lines_call_1 = [
        {"line_number": 1, "speaker": "Agent", "text": "Settlement split of 700 dollars today and 700 next month."},
        {"line_number": 2, "speaker": "Consumer", "text": "Thank you for helping me arrange the debt repayment."}
    ]
    vstore.add_transcript_lines(call_id=1, call_title="Call 1", lines=lines_call_1)

    # Add transcript lines for Call 2
    lines_call_2 = [
        {"line_number": 1, "speaker": "Agent", "text": "Your warranty plan has been renewed."},
        {"line_number": 2, "speaker": "Consumer", "text": "I want to dispute the unauthorized billing charge."}
    ]
    vstore.add_transcript_lines(call_id=2, call_title="Call 2", lines=lines_call_2)

    # Search with call_id=2
    res_call_2 = vstore.search("settlement debt", call_id=2)
    # Should not return Call 1 lines even if they are semantically closer
    assert all(r["call_id"] == 2 for r in res_call_2)

    # Search with call_id=1
    res_call_1 = vstore.search("settlement debt", call_id=1)
    assert len(res_call_1) > 0
    assert all(r["call_id"] == 1 for r in res_call_1)

def test_source_type_persistence_and_isolation(tmp_path):
    """
    Verifies that CallRecord correctly stores source_type (audio, transcript_upload,
    transcript_paste, pdf_sample) and maintains complete record isolation.
    """
    init_db()
    db = SessionLocal()

    c_pdf = CallRecord(
        title="PDF Sample Call",
        source_type="pdf_sample",
        summary="PDF test"
    )
    c_upload = CallRecord(
        title="Uploaded Transcript Call",
        source_type="transcript_upload",
        summary="Upload test"
    )
    c_paste = CallRecord(
        title="Pasted Transcript Call",
        source_type="transcript_paste",
        summary="Paste test"
    )
    c_audio = CallRecord(
        title="Audio Call",
        source_type="audio",
        summary="Audio test"
    )
    db.add_all([c_pdf, c_upload, c_paste, c_audio])
    db.commit()

    for rec, expected_src in [
        (c_pdf, "pdf_sample"),
        (c_upload, "transcript_upload"),
        (c_paste, "transcript_paste"),
        (c_audio, "audio")
    ]:
        db.refresh(rec)
        assert rec.source_type == expected_src

    db.close()
