import json
from typing import Dict, Any, List, Optional

def render_severity_badge(severity: str) -> str:
    """Returns Streamlit markdown badge color for Red, Yellow, Green severity."""
    if severity == "Red":
        return "🔴 **RED (Critical Risk)**"
    elif severity == "Yellow":
        return "🟡 **YELLOW (Caution/Warning)**"
    elif severity == "Green":
        return "🟢 **GREEN (Compliant)**"
    return severity

def serialize_for_sqlite(value: Any) -> Any:
    """
    Safely serializes Python dictionaries, lists, or tuples into JSON strings for SQLite storage.
    Leaves primitive types (None, int, float, str, bytes) untouched.
    """
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value

def deserialize_from_sqlite(value: Any) -> Any:
    """
    Safely deserializes JSON strings retrieved from SQLite back into Python dict/list.
    Returns the original string if it is not valid JSON.
    """
    if value is None:
        return None
    if isinstance(value, str):
        v_stripped = value.strip()
        if (v_stripped.startswith("{") and v_stripped.endswith("}")) or (v_stripped.startswith("[") and v_stripped.endswith("]")):
            try:
                return json.loads(v_stripped)
            except Exception:
                return value
    return value

def render_line_pills(line_numbers: List[int], call_id: Optional[int] = None) -> str:
    """Renders line numbers as clickable pills linking directly to canonical transcript cards client-side."""
    if not line_numbers:
        return "None"
    pills = []
    for num in line_numbers:
        call_arg = f"{call_id}" if call_id is not None else "null"
        pills.append(
            f'<a href="#transcript-line-{num}" '
            f'onclick="if(window.jumpToTranscriptLine){{window.jumpToTranscriptLine({num}, {call_arg});}} return false;" '
            f'class="badge-line-pill" title="Jump to Line {num} in Grounded Transcript">'
            f'Line {num}</a>'
        )
    return " ".join(pills)

def export_call_to_json(call_data: Dict[str, Any]) -> str:
    """Formats full call intelligence output as JSON string."""
    return json.dumps(call_data, indent=2, default=str)

def export_call_to_markdown(call_data: Dict[str, Any]) -> str:
    """Formats full call intelligence output as a readable Markdown document."""
    md = []
    md.append(f"# Call Intelligence Report: {call_data.get('title', 'Call Record')}")
    md.append(f"**Date:** {call_data.get('recording_date')}")
    md.append(f"**Tag:** `{call_data.get('short_tag')}`")
    md.append(f"**Overall Sentiment:** {call_data.get('overall_sentiment')}")
    md.append("\n## Summary")
    md.append(call_data.get('summary', 'No summary available.'))

    md.append("\n## Decisions Made")
    for dec in call_data.get('decisions', []):
        md.append(f"- **{dec['decision']}** *(Lines: {dec['line_numbers']})*")
        md.append(f"  > \"{dec['source_excerpt']}\"")

    md.append("\n## Action Items")
    for act in call_data.get('action_items', []):
        md.append(f"- **{act['task']}**")
        md.append(f"  - **Owner:** {act.get('owner') or 'Unassigned'}")
        md.append(f"  - **Due Date:** {act.get('resolved_due_date') or act.get('raw_date_mention') or 'Vague/None'}")
        md.append(f"  - **Source Lines:** {act['line_numbers']}")
        md.append(f"  > \"{act['source_excerpt']}\"")

    md.append("\n## Blockers")
    for blk in call_data.get('blockers', []):
        md.append(f"- **{blk['blocker']}** *(Lines: {blk['line_numbers']})*")
        md.append(f"  > \"{blk['source_excerpt']}\"")

    md.append("\n## Compliance Observations")
    for obs in call_data.get('compliance_observations', []):
        md.append(f"- [{obs['severity']}] **{obs['category']}**: {obs['observation']} *(Lines: {obs['line_numbers']})*")
        md.append(f"  > \"{obs['source_excerpt']}\"")

    md.append("\n## Items Needing Human Review")
    for rev in call_data.get('human_review_items', []):
        md.append(f"- ⚠️ **{rev['reason']}**: {rev['description']} *(Lines: {rev['line_numbers']})*")
        md.append(f"  > \"{rev['source_excerpt']}\"")

    return "\n".join(md)
