import re
from typing import List, Dict, Any

class ComplianceDetector:
    """
    Rule-based compliance and risk trigger detector for call transcripts.
    Runs alongside LLM compliance checks to ensure zero-miss safety on critical risk flags.
    """

    CEASE_DESIST_PATTERNS = [
        r"stop\s+calling(?:\s+me)?",
        r"don'?t\s+call\s+me",
        r"don'?t\s+bother\s+me",
        r"take\s+me\s+off\s+(?:from\s+)?(?:your\s+)?list",
        r"don'?t\s+contact\s+me",
        r"told\s+you\s+(?:guys\s+)?not\s+to\s+call",
        r"remove\s+my\s+number"
    ]

    LEGAL_PATTERNS = [
        r"i\s+will\s+sue",
        r"contact\s+my\s+attorney",
        r"contact\s+my\s+lawyer",
        r"i\s+am\s+bankrupt",
        r"filing\s+for\s+bankruptcy",
        r"legal\s+action",
        r"court\s+order"
    ]

    WRONG_NUMBER_PATTERNS = [
        r"wrong\s+number",
        r"don'?t\s+know\s+(?:who\s+that\s+is|this\s+person)",
        r"no\s+one\s+by\s+that\s+name",
        r"got\s+the\s+wrong\s+person"
    ]

    RECORDING_CONSENT_PATTERNS = [
        r"call\s+is\s+being\s+recorded",
        r"recorded\s+for\s+(?:quality|training)",
        r"do\s+i\s+have\s+your\s+permission\s+to\s+record",
        r"this\s+call\s+may\s+be\s+monitored"
    ]

    @classmethod
    def check_line(cls, line_text: str) -> List[Dict[str, Any]]:
        """
        Scans a single transcript line for compliance triggers.
        """
        flags = []
        text_lower = line_text.lower()

        # Cease & Desist
        for pattern in cls.CEASE_DESIST_PATTERNS:
            if re.search(pattern, text_lower):
                flags.append({
                    "category": "Cease & Desist",
                    "severity": "Red",
                    "observation": f"Customer issued Cease & Desist request matching pattern '{pattern}'"
                })
                break

        # Legal Mention
        for pattern in cls.LEGAL_PATTERNS:
            if re.search(pattern, text_lower):
                flags.append({
                    "category": "Legal Mention",
                    "severity": "Red",
                    "observation": f"Customer mentioned legal action or bankruptcy ('{pattern}')"
                })
                break

        # Wrong Number
        for pattern in cls.WRONG_NUMBER_PATTERNS:
            if re.search(pattern, text_lower):
                flags.append({
                    "category": "Wrong Number",
                    "severity": "Yellow",
                    "observation": f"Consumer indicated wrong number or wrong party ('{pattern}')"
                })
                break

        return flags

    @classmethod
    def check_transcript_consent(cls, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Checks if call recording disclosure or consent is present in early transcript lines.
        """
        # Check first 5 lines for recording disclosure
        first_few_lines = lines[:5]
        for line in first_few_lines:
            text_lower = line["text"].lower()
            for pattern in cls.RECORDING_CONSENT_PATTERNS:
                if re.search(pattern, text_lower):
                    return {
                        "has_consent": True,
                        "line_number": line["line_number"],
                        "excerpt": line["text"]
                    }

        return {
            "has_consent": False,
            "line_number": None,
            "excerpt": None
        }
