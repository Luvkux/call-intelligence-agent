import pytest
from src.intelligence.schemas import CallIntelligenceOutput, Decision, ActionItem, CallSentiment
from src.grounding.validator import GroundingValidator

def test_grounding_auto_correction():
    transcript_lines = [
        {"line_number": 7, "speaker": "Consumer", "text": "That's still too much right now. Could I do $700 now and $700 next month?"},
        {"line_number": 8, "speaker": "Agent", "text": "Let me note that – $700 today and $700 on the 15th of next month. I'll need a supervisor to approve the settlement split, I'll follow up by Friday."}
    ]

    # Model output where quote was slightly reworded
    output = CallIntelligenceOutput(
        short_tag="Settlement Split",
        summary="Customer agreed to settlement split.",
        decisions=[],
        action_items=[
            ActionItem(
                task="Consumer to pay second $700 installment",
                owner="James (consumer)",
                raw_date_mention="15th of next month",
                resolved_due_date="2026-08-15",
                line_numbers=[8],
                source_excerpt="$700 today and $700 next month"  # reworded slightly
            )
        ],
        blockers=[],
        compliance_observations=[],
        human_review_items=[],
        sentiment=CallSentiment(
            overall_sentiment="Neutral",
            customer_angry=False,
            profanity_detected=False,
            sentiment_explanation="Neutral negotiation."
        )
    )

    validated_output, logs = GroundingValidator.validate_output(output, transcript_lines)

    # Check auto-correction replaced quote with exact raw transcript line
    assert validated_output.action_items[0].source_excerpt == transcript_lines[1]["text"]
    assert any(log["status"] == "corrected" for log in logs)
