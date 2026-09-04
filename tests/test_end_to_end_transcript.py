import pytest
from datetime import datetime
from src.transcript.parser import parse_transcript
from src.audio.processor import format_transcript_as_text
from src.intelligence.schemas import (
    CallIntelligenceOutput, Decision, ActionItem, Blocker,
    ComplianceObservation, HumanReviewItem, CallSentiment
)
from src.grounding.validator import GroundingValidator

def test_transcript_workflow_canonical_line_numbering():
    raw_text = """
    [00:00 - 00:04] Speaker 0: Good morning, thank you for reaching Apex Financial Services. My name is Pooja.
    [00:05 - 00:08] Speaker 1: Yes, this is Vikram speaking. Why am I getting continuous calls regarding my loan?
    [00:09 - 00:14] Speaker 0: I apologize for the trouble Mr. Vikram. Let me check your account statement right away.
    [00:15 - 00:20] Speaker 1: I already paid that 15,000 rupees last Thursday. Please stop your recovery team from calling me.
    """
    lines, role_mapping, role_conf, review_flags = parse_transcript(raw_text)

    # 1. Check Canonical Line Numbering (1 to N)
    assert len(lines) == 4
    for i, line in enumerate(lines):
        assert line["line_number"] == i + 1

    # 2. Check Role Mapping Evidence
    assert role_mapping["Speaker 0"] == "Agent"
    assert role_mapping["Speaker 1"] == "Customer"
    assert lines[0]["speaker"] == "Agent"
    assert lines[1]["speaker"] == "Customer"
    assert lines[2]["speaker"] == "Agent"
    assert lines[3]["speaker"] == "Customer"

    # 3. Check Timestamps Preserved
    assert lines[0]["timestamp_str"] == "[00:00 - 00:04]"
    assert lines[3]["timestamp_str"] == "[00:15 - 00:20]"

    # 4. Check Grounding Validation on Parsed Transcript
    mock_extracted = CallIntelligenceOutput(
        short_tag="Loan Repayment Dispute",
        summary="Customer Vikram inquired about repeated collection calls after making payment.",
        sentiment=CallSentiment(
            overall_sentiment="Negative",
            customer_angry=True,
            profanity_detected=False,
            sentiment_explanation="Customer expressed frustration over collection calls after paying."
        ),
        decisions=[],
        action_items=[
            ActionItem(
                task="Review account statement for 15,000 INR payment",
                owner="Agent",
                raw_date_mention="right away",
                resolved_due_date="2026-07-01",
                line_numbers=[3],
                source_excerpt="Let me check your account statement right away."
            )
        ],
        blockers=[],
        compliance_observations=[
            ComplianceObservation(
                category="Cease & Desist",
                observation="Customer demanded collection calls to stop.",
                severity="Red",
                line_numbers=[4],
                source_excerpt="Please stop your recovery team from calling me."
            )
        ],
        human_review_items=[
            HumanReviewItem(
                reason="Cease & Desist Trigger",
                description="Customer requested recovery calls to stop.",
                line_numbers=[4],
                source_excerpt="Please stop your recovery team from calling me."
            )
        ]
    )

    validated_output, audit_logs = GroundingValidator.validate_output(mock_extracted, lines)

    assert validated_output.action_items[0].line_numbers == [3]
    assert validated_output.compliance_observations[0].line_numbers == [4]
    assert validated_output.human_review_items[0].line_numbers == [4]
