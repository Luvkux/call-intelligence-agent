from typing import List, Dict, Any, Tuple
from src.intelligence.schemas import CallIntelligenceOutput, HumanReviewItem

class GroundingValidator:
    """
    Deterministic post-processing validator.
    Audits every extracted item against raw transcript lines to guarantee:
    1. Line numbers cited exist in transcript.
    2. Excerpt matches raw line text verbatim without quiet rewording.
    3. Auto-corrects reworded excerpts to original raw line text.
    4. Escalates ungrounded items to human review.
    """

    @staticmethod
    def validate_output(
        extracted_output: CallIntelligenceOutput,
        transcript_lines: List[Dict[str, Any]]
    ) -> Tuple[CallIntelligenceOutput, List[Dict[str, Any]]]:
        """
        Validates output and returns (validated_output, audit_report_logs).
        """
        line_map = {item["line_number"]: item["text"] for item in transcript_lines}
        audit_logs = []

        def audit_item(item, item_type: str):
            if not hasattr(item, "line_numbers") or not item.line_numbers:
                audit_logs.append({
                    "type": item_type,
                    "status": "escalated",
                    "reason": "Missing line citations"
                })
                return False

            valid_lines = []
            exact_excerpts = []

            for line_num in item.line_numbers:
                if line_num not in line_map:
                    audit_logs.append({
                        "type": item_type,
                        "status": "escalated",
                        "reason": f"Cited line {line_num} does not exist in transcript"
                    })
                    return False
                valid_lines.append(line_num)
                exact_excerpts.append(line_map[line_num])

            # Force exact verbatim replacement if excerpt was reworded
            combined_raw = " | ".join(exact_excerpts)

            if item.source_excerpt != combined_raw:
                audit_logs.append({
                    "type": item_type,
                    "status": "corrected",
                    "original_excerpt": item.source_excerpt,
                    "verbatim_excerpt": combined_raw,
                    "lines": valid_lines
                })
                item.source_excerpt = combined_raw
            else:
                audit_logs.append({
                    "type": item_type,
                    "status": "passed",
                    "lines": valid_lines
                })

            return True

        # Audit Decisions
        for dec in extracted_output.decisions:
            if not audit_item(dec, "Decision"):
                extracted_output.human_review_items.append(
                    HumanReviewItem(
                        reason="Ungrounded Decision Citation",
                        description=f"Decision '{dec.decision}' cited invalid line numbers.",
                        line_numbers=dec.line_numbers if hasattr(dec, 'line_numbers') else [1],
                        source_excerpt=dec.source_excerpt
                    )
                )

        # Audit Action Items
        for action in extracted_output.action_items:
            if not audit_item(action, "Action Item"):
                extracted_output.human_review_items.append(
                    HumanReviewItem(
                        reason="Ungrounded Action Item Citation",
                        description=f"Action Item '{action.task}' cited invalid line numbers.",
                        line_numbers=action.line_numbers if hasattr(action, 'line_numbers') else [1],
                        source_excerpt=action.source_excerpt
                    )
                )

        # Audit Blockers
        for blocker in extracted_output.blockers:
            if not audit_item(blocker, "Blocker"):
                extracted_output.human_review_items.append(
                    HumanReviewItem(
                        reason="Ungrounded Blocker Citation",
                        description=f"Blocker '{blocker.blocker}' cited invalid line numbers.",
                        line_numbers=blocker.line_numbers if hasattr(blocker, 'line_numbers') else [1],
                        source_excerpt=blocker.source_excerpt
                    )
                )

        # Audit Compliance Observations
        for obs in extracted_output.compliance_observations:
            audit_item(obs, "Compliance Observation")

        return extracted_output, audit_logs
