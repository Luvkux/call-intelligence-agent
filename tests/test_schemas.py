from src.intelligence.schemas import CallIntelligenceOutput, Decision, ActionItem, CallSentiment

def test_schema_valid_construction():
    output = CallIntelligenceOutput(
        short_tag="Support Call",
        summary="Customer inquired about refund status.",
        decisions=[
            Decision(decision="Issue 50% refund", line_numbers=[4], source_excerpt="We will credit 50%.")
        ],
        action_items=[
            ActionItem(
                task="Process refund in system",
                owner="Agent Sarah",
                raw_date_mention="tomorrow",
                resolved_due_date="2026-07-02",
                line_numbers=[5],
                source_excerpt="I will issue the refund tomorrow."
            )
        ],
        blockers=[],
        compliance_observations=[],
        human_review_items=[],
        sentiment=CallSentiment(
            overall_sentiment="Positive",
            customer_angry=False,
            profanity_detected=False,
            sentiment_explanation="Customer was satisfied."
        )
    )

    json_str = output.model_dump_json()
    reloaded = CallIntelligenceOutput.model_validate_json(json_str)
    assert reloaded.short_tag == "Support Call"
    assert reloaded.action_items[0].owner == "Agent Sarah"
