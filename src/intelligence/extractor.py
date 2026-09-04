import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

import config
from src.intelligence.schemas import CallIntelligenceOutput, HumanReviewItem, ComplianceObservation
from src.intelligence.date_resolver import DateResolver
from src.intelligence.compliance import ComplianceDetector

class CallIntelligenceExtractor:
    """
    Extracts structured call intelligence from line-indexed transcripts using Gemini API.
    Enforces strict Pydantic JSON schema output.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def extract(self, transcript_lines: List[Dict[str, Any]], call_date: datetime) -> CallIntelligenceOutput:
        """
        Processes line-indexed transcript lines and returns structured CallIntelligenceOutput object.
        """
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not set. Please configure your API key in .env or settings.")

        formatted_transcript = []
        for item in transcript_lines:
            formatted_transcript.append(f"Line {item['line_number']}: {item['speaker']}: {item['text']}")
        transcript_text = "\n".join(formatted_transcript)

        reference_date_str = call_date.strftime("%Y-%m-%d (%A, %d %B %Y)")

        prompt = f"""You are an expert Call Intelligence AI Agent reviewing a call recording transcript.

Reference Call Date: {reference_date_str}

CRITICAL RULES FOR TRUSTWORTHINESS:
1. LINE-LEVEL GROUNDING: Every extracted decision, action item, blocker, compliance observation, and human review item MUST specify the exact `line_numbers` it came from.
2. VERBATIM EXCERPT: The `source_excerpt` field for every item MUST contain the exact, un-reworded quotes directly from the transcript text line(s). Do NOT reword or rewrite source quotes.
3. RELATIVE DATES: Resolve relative dates mentioned in the conversation (e.g. "15th of next month", "this Friday", "tomorrow") to exact YYYY-MM-DD dates using the Reference Call Date provided above. Populate `raw_date_mention` and `resolved_due_date`.
4. CAUTIOUS HUMAN ESCALATION: Flag items for human review whenever:
   - An action item has an ambiguous owner or vague deadline.
   - A decision requires supervisor sign-off or higher authority (e.g., settlement splits, fee waivers).
   - Recording consent is unclear or absent.
   - A customer mentions Cease & Desist ("stop calling me"), legal action ("I will sue"), or bankruptcy.
   - Any financial or policy threshold exceeds standard terms.
   - The transcript is unclear on a point.

TRANSCRIPT:
{transcript_text}
"""

        try:
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CallIntelligenceOutput,
                    temperature=0.1,
                )
            )

            # Parse JSON into Pydantic model
            extracted_output = CallIntelligenceOutput.model_validate_json(response.text)

            # Post-process date resolutions using DateResolver
            for action in extracted_output.action_items:
                if action.raw_date_mention and not action.resolved_due_date:
                    action.resolved_due_date = DateResolver.resolve_date(action.raw_date_mention, call_date)

            # Post-process rule-based compliance checks to ensure zero-miss safety
            rule_flags = []
            for line in transcript_lines:
                detected_flags = ComplianceDetector.check_line(line["text"])
                for flag in detected_flags:
                    # Avoid duplicates
                    already_exists = any(
                        line["line_number"] in obs.line_numbers and obs.category == flag["category"]
                        for obs in extracted_output.compliance_observations
                    )
                    if not already_exists:
                        extracted_output.compliance_observations.append(
                            ComplianceObservation(
                                category=flag["category"],
                                severity=flag["severity"],
                                observation=flag["observation"],
                                line_numbers=[line["line_number"]],
                                source_excerpt=line["text"]
                            )
                        )
                        # Also escalate Cease & Desist and Legal mentions to Human Review if not already present
                        if flag["severity"] == "Red":
                            extracted_output.human_review_items.append(
                                HumanReviewItem(
                                    reason=f"{flag['category']} Risk Trigger",
                                    description=flag["observation"],
                                    line_numbers=[line["line_number"]],
                                    source_excerpt=line["text"]
                                )
                            )

            # Check recording consent
            consent_check = ComplianceDetector.check_transcript_consent(transcript_lines)
            if not consent_check["has_consent"]:
                # Flag missing consent
                consent_flag_exists = any(
                    "Consent" in item.reason for item in extracted_output.human_review_items
                )
                if not consent_flag_exists:
                    extracted_output.human_review_items.append(
                        HumanReviewItem(
                            reason="Missing Recording Consent",
                            description="Customer recording consent disclosure was not clearly detected in the beginning of the call.",
                            line_numbers=[1],
                            source_excerpt=transcript_lines[0]["text"] if transcript_lines else "Line 1"
                        )
                    )

            return extracted_output

        except Exception as e:
            print(f"[Extraction Error] Gemini API extraction failed: {e}")
            raise RuntimeError(f"Gemini API structured extraction failed: {e}")
