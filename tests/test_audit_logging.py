import json
import pytest
from src.db.database import SessionLocal, init_db
from src.db.models import CallRecord, AuditLogRecord, HumanReviewRecord
from src.utils.helpers import serialize_for_sqlite, deserialize_from_sqlite

def test_serialize_for_sqlite_primitives_unchanged():
    assert serialize_for_sqlite(None) is None
    assert serialize_for_sqlite("Plain text string") == "Plain text string"
    assert serialize_for_sqlite(123) == 123
    assert serialize_for_sqlite(45.67) == 45.67
    assert serialize_for_sqlite(b"bytes_data") == b"bytes_data"

def test_serialize_and_deserialize_dictionaries():
    data = {
        "type": "Decision",
        "status": "corrected",
        "original_excerpt": "I will follow up by Friday",
        "lines": [62, 63, 64]
    }
    serialized = serialize_for_sqlite(data)
    assert isinstance(serialized, str)
    deserialized = deserialize_from_sqlite(serialized)
    assert deserialized == data

def test_audit_log_record_direct_dict_insertion(tmp_path):
    """
    Tests the exact scenario requested by the user:
    Passing a python dict as details into AuditLogRecord and committing to SQLite.
    """
    init_db()
    db = SessionLocal()

    call = CallRecord(title="Audit Log Test Call", summary="Testing audit logs")
    db.add(call)
    db.commit()
    db.refresh(call)

    exact_details = {
        "type": "Decision",
        "status": "corrected",
        "original_excerpt": "...",
        "lines": [62, 63, 64]
    }

    audit_entry = AuditLogRecord(
        call_id=call.id,
        reviewer="System Grounding Engine",
        action="Grounding Validation",
        details=exact_details
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)

    assert audit_entry.id is not None
    # Verify stored in SQLite as valid JSON
    assert isinstance(audit_entry.details, str)
    parsed = json.loads(audit_entry.details)
    assert parsed["type"] == "Decision"
    assert parsed["lines"] == [62, 63, 64]

    # Verify retrieval from fresh session
    db2 = SessionLocal()
    fetched = db2.query(AuditLogRecord).filter(AuditLogRecord.id == audit_entry.id).first()
    assert fetched is not None
    assert fetched.reviewer == "System Grounding Engine"
    assert fetched.action == "Grounding Validation"
    deserialized = deserialize_from_sqlite(fetched.details)
    assert deserialized == exact_details
    db2.close()
    db.close()

def test_audit_log_record_nested_structure(tmp_path):
    """
    Tests nested dictionary and list structure storage and retrieval.
    """
    init_db()
    db = SessionLocal()

    call = CallRecord(title="Nested Audit Test Call", summary="Testing nested audit logs")
    db.add(call)
    db.commit()
    db.refresh(call)

    nested_details = {
        "status": "corrected",
        "evidence": [
            {
                "line": 62,
                "text": "example"
            },
            {
                "line": 63,
                "text": "example"
            }
        ]
    }

    audit_entry = AuditLogRecord(
        call_id=call.id,
        reviewer="System Grounding Engine",
        action="Grounding Validation",
        details=nested_details
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)

    db2 = SessionLocal()
    fetched = db2.query(AuditLogRecord).filter(AuditLogRecord.id == audit_entry.id).first()
    assert fetched is not None
    deserialized = deserialize_from_sqlite(fetched.details)
    assert deserialized == nested_details
    assert len(deserialized["evidence"]) == 2
    assert deserialized["evidence"][0]["line"] == 62
    db2.close()
    db.close()

def test_grounding_validation_audit_logging_vs_human_review_isolation():
    """
    Verifies that:
    1. Every audited item (Decision, Action Item, Blocker, Compliance) is logged in audit_logs.
    2. 'passed' and 'corrected' items do NOT create Human Review Queue items.
    3. 'escalated' items (ungrounded or invalid citations) create Human Review Queue items.
    """
    from src.intelligence.schemas import (
        CallIntelligenceOutput, Decision, ActionItem, Blocker,
        ComplianceObservation, CallSentiment
    )
    from src.grounding.validator import GroundingValidator

    raw_transcript = [
        {"line_number": 1, "speaker": "Agent", "text": "This call is recorded."},
        {"line_number": 2, "speaker": "Agent", "text": "We will issue a full refund of $89.99."},
        {"line_number": 3, "speaker": "Customer", "text": "I will check my bank on Friday."}
    ]

    output = CallIntelligenceOutput(
        short_tag="Refund Call",
        summary="Customer refund call.",
        sentiment=CallSentiment(overall_sentiment="Positive", customer_angry=False, profanity_detected=False, sentiment_explanation="Good"),
        decisions=[
            # 1. Exact match -> 'passed'
            Decision(decision="Issue full refund", line_numbers=[2], source_excerpt="We will issue a full refund of $89.99.")
        ],
        action_items=[
            # 2. Reworded excerpt -> 'corrected'
            ActionItem(task="Check bank account", owner="Customer", line_numbers=[3], source_excerpt="Check bank Friday")
        ],
        blockers=[
            # 3. Invalid line number 99 -> 'escalated'
            Blocker(blocker="Bank delay", line_numbers=[99], source_excerpt="External delay")
        ],
        compliance_observations=[
            # 4. Exact match -> 'passed'
            ComplianceObservation(category="Disclosure", severity="Green", observation="Consent provided", line_numbers=[1], source_excerpt="This call is recorded.")
        ],
        human_review_items=[]
    )

    validated_output, audit_logs = GroundingValidator.validate_output(output, raw_transcript)

    # 4 audit logs total (1 for each audited item)
    assert len(audit_logs) == 4
    statuses = [log["status"] for log in audit_logs]
    assert statuses.count("passed") == 2
    assert statuses.count("corrected") == 1
    assert statuses.count("escalated") == 1

    # Only the 1 'escalated' blocker should be escalated to Human Review Queue
    assert len(validated_output.human_review_items) == 1
    assert validated_output.human_review_items[0].reason == "Ungrounded Blocker Citation"
    assert validated_output.human_review_items[0].line_numbers == [99]

def test_human_review_resolution_lifecycle():
    """
    Verifies that when a pending HumanReviewRecord is Approved or Dismissed:
    1. It is excluded from status='Pending' queries (removed from active UI queue).
    2. Its record remains in human_review_queue table.
    3. An audit record is created and persists in audit_logs table.
    """
    init_db()
    db = SessionLocal()

    call = CallRecord(title="Review Lifecycle Test", summary="Testing review lifecycle")
    db.add(call)
    db.commit()
    db.refresh(call)

    # Add 2 review items: 1 to Approve, 1 to Dismiss
    item1 = HumanReviewRecord(
        call_id=call.id,
        reason="Supervisor Approval Required",
        description="Split payment requires signoff",
        line_numbers=[5],
        source_excerpt="Supervisor approval needed",
        status="Pending"
    )
    item2 = HumanReviewRecord(
        call_id=call.id,
        reason="Missing Recording Consent",
        description="Consent not found",
        line_numbers=[1],
        source_excerpt="Line 1 excerpt",
        status="Pending"
    )
    db.add_all([item1, item2])
    db.commit()

    # Initial state: 2 pending items
    pending_before = db.query(HumanReviewRecord).filter(
        HumanReviewRecord.call_id == call.id,
        HumanReviewRecord.status == "Pending"
    ).all()
    assert len(pending_before) == 2

    # Reviewer approves item 1
    item1.status = "Approved"
    item1.reviewer_notes = "Supervisor approved split"
    db.add(AuditLogRecord(
        call_id=call.id,
        reviewer="Compliance Officer",
        action="Approve",
        details=f"Approved review item #{item1.id}: {item1.reason}"
    ))

    # Reviewer dismisses item 2
    item2.status = "Dismissed"
    item2.reviewer_notes = "Consent verified manually from audio"
    db.add(AuditLogRecord(
        call_id=call.id,
        reviewer="Compliance Officer",
        action="Dismiss",
        details=f"Dismissed review item #{item2.id}: {item2.reason}"
    ))
    db.commit()

    # Active pending queue is now empty
    pending_after = db.query(HumanReviewRecord).filter(
        HumanReviewRecord.call_id == call.id,
        HumanReviewRecord.status == "Pending"
    ).all()
    assert len(pending_after) == 0

    # Historical audit logs contain both actions
    audit_records = db.query(AuditLogRecord).filter(
        AuditLogRecord.call_id == call.id
    ).all()
    assert len(audit_records) == 2
    actions = [a.action for a in audit_records]
    assert "Approve" in actions
    assert "Dismiss" in actions

    db.close()

