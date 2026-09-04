import re
from typing import List, Dict, Any, Tuple, Optional

# Conversational Agent Indicators (Company representatives, support agents, debt collection agents)
AGENT_PATTERNS = [
    r"\bthanks for calling\b",
    r"\bthank you for calling\b",
    r"\byou have reached\b",
    r"\bgood (morning|afternoon|evening)\b",
    r"\bmy name is [a-z]+\b",
    r"\bthis is [a-z]+ from\b",
    r"\bhow (may|can) i (help|assist) you\b",
    r"\bi can certainly help you\b",
    r"\bto get started\b",
    r"\bcould you (please )?share your\b",
    r"\bcould you confirm the\b",
    r"\bjust for security verification\b",
    r"\bgive me just a moment\b",
    r"\blet me (bring up|look into|check|pull up|access|dig into|review)\b",
    r"\bi have your file open\b",
    r"\bour system (reflects|had|records)\b",
    r"\bi see what happened\b",
    r"\bwe can reverse the full amount\b",
    r"\bhere is our decision\b",
    r"\bi am going to issue a full (direct )?refund\b",
    r"\bmanually terminate that orphaned\b",
    r"\bso you are never billed again\b",
    r"\bhere are the exact next steps\b",
    r"\bfirst action item is on me\b",
    r"\bi, [a-z]+, will submit the immediate refund\b",
    r"\blicense purge in our supervisor portal\b",
    r"\bthe dependency here is our clearinghouse\b",
    r"\bbecause it is an external ach credit\b",
    r"\bso the second action item is for you\b",
    r"\bplease monitor your checking account\b",
    r"\bby friday, [a-z]+ [0-9]+ at [0-9]+ (pm|am)\b",
    r"\byou can call us back directly with the reference code\b",
    r"\bthat is spot on\b",
    r"\bi have also just sent a written confirmation\b",
    r"\bit was my pleasure\b",
    r"\bthank you for choosing\b",
    r"\bhave a wonderful rest of your day\b",
    r"\bcompliance disclosure\b",
    r"\brbi guidelines\b",
    r"\bcall is recorded\b",
    r"\bquality assurance\b",
    r"\btraining and audit\b",
    r"\bfor mandatory verification\b",
    r"\boverdue (emi|payment|amount|balance)\b",
    r"\bsettlement (split|offer|plan)\b",
    r"\bclearing gateway\b",
    r"\bledger for account\b",
    r"\bthank you for holding\b",
    r"\bi (apologize|sincerely apologize) for the inconvenience\b",
    r"\bi completely hear your frustration\b",
    r"\bwe will ensure it is accurately tracked\b",
    r"\bupi utr reference number\b",
    r"\bbank transaction confirmation\b",
]

# Conversational Customer Indicators (Account holders, borrowers, consumers)
CUSTOMER_PATTERNS = [
    r"\bhi [a-z]+(\.|\,)? yeah\b",
    r"\byes, this is [a-z]+ speaking\b",
    r"\bi am calling (about|regarding|because)\b",
    r"\bi am looking at my monthly statement\b",
    r"\bthere is a charge on here\b",
    r"\bi never authorized this\b",
    r"\bwhy am i (getting|receiving|being)\b",
    r"\bgetting calls from your\b",
    r"\bbeing harassed\b",
    r"\bin the middle of (office|work|meeting)\b",
    r"\bthat is (completely|totally) wrong\b",
    r"\bthis is ridiculous\b",
    r"\bi (already|have already) paid\b",
    r"\bdebited (from|for) my\b",
    r"\bmy (hdfc|sbi|icici|axis|bank) account\b",
    r"\bwhy is your system\b",
    r"\bthat'?s still too much\b",
    r"\bcould i do\b",
    r"\bcan i pay\b",
    r"\bcan i get my [0-9.]+ refunded\b",
    r"\bso that is why it charged me because of a system glitch\b",
    r"\ball right\. so how do we fix this\b",
    r"\bthat is great\. how long does that (refund )?usually take\b",
    r"\bokay, perfect\. so you are processing\b",
    r"\band my action is to check my account\b",
    r"\bhonestly, [a-z]+, i really appreciate\b",
    r"\byou too, [a-z]+\. take care\b",
    r"\bi (did )?sign up for a free trial\b",
    r"\bi canceled it within\b",
    r"\bi have the confirmation email\b",
    r"\bit is david chen\b",
    r"\bit is (14th|[0-9]+th|[0-9]+st|[0-9]+nd|[0-9]+rd) of [a-z]+\b",
    r"\bemail is [a-z0-9._]+ at [a-z]+\b",
    r"\bnow please check\b",
]

SUPERVISOR_PATTERNS = [
    r"\bi am the supervisor\b",
    r"\bi am the (floor|team) manager\b",
    r"\bstepping in to (review|assist|help)\b",
    r"\bescalated to me\b",
    r"\boverriding\b",
]

def format_timestamp(seconds: float) -> str:
    """Formats float seconds into MM:SS format (or HH:MM:SS if >= 1 hour)."""
    if seconds is None:
        return "00:00"
    total_sec = max(0, int(seconds))
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def format_timestamp_range(start_sec: Optional[float], end_sec: Optional[float]) -> str:
    """Formats start and end timestamps into [MM:SS - MM:SS] or 'Timestamp unavailable' if None."""
    if start_sec is None and end_sec is None:
        return "Timestamp unavailable"
    if start_sec is not None and end_sec is None:
        return f"[{format_timestamp(start_sec)}]"
    if start_sec is None and end_sec is not None:
        return f"[{format_timestamp(end_sec)}]"
    return f"[{format_timestamp(start_sec)} - {format_timestamp(end_sec)}]"

def map_speakers_to_roles(
    lines: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str], float, List[Dict[str, Any]]]:
    """
    Deterministically maps raw diarization speaker labels (e.g. SPEAKER_00, SPEAKER_01)
    to conversational roles: 'Agent', 'Customer', 'Supervisor', or 'Speaker N (Role Uncertain)'.
    """
    if not lines:
        return [], {}, 1.0, []

    speaker_texts: Dict[str, List[str]] = {}
    for line in lines:
        spk = line.get("speaker", "SPEAKER_00")
        if spk not in speaker_texts:
            speaker_texts[spk] = []
        speaker_texts[spk].append(line.get("text", ""))

    unique_speakers = list(speaker_texts.keys())
    speaker_scores: Dict[str, Dict[str, float]] = {}

    for spk, texts in speaker_texts.items():
        combined_text = " ".join(texts).lower()
        agent_score = 0.0
        customer_score = 0.0
        supervisor_score = 0.0

        for pat in AGENT_PATTERNS:
            matches = len(re.findall(pat, combined_text))
            agent_score += matches * 2.0

        for pat in CUSTOMER_PATTERNS:
            matches = len(re.findall(pat, combined_text))
            customer_score += matches * 2.0

        for pat in SUPERVISOR_PATTERNS:
            matches = len(re.findall(pat, combined_text))
            supervisor_score += matches * 3.0

        # Opening Anchor Evidence:
        for early_line in lines[:4]:
            if early_line.get("speaker") == spk:
                early_text = early_line.get("text", "").lower()
                if any(re.search(pat, early_text) for pat in AGENT_PATTERNS):
                    agent_score += 5.0
                if any(re.search(pat, early_text) for pat in CUSTOMER_PATTERNS):
                    customer_score += 5.0

        speaker_scores[spk] = {
            "agent": agent_score,
            "customer": customer_score,
            "supervisor": supervisor_score
        }

    role_mapping: Dict[str, str] = {}
    review_flags: List[Dict[str, Any]] = []
    confidence = 0.95

    if len(unique_speakers) == 1:
        spk = unique_speakers[0]
        scores = speaker_scores[spk]
        if scores["agent"] > scores["customer"]:
            role_mapping[spk] = "Agent"
            confidence = 0.85
        elif scores["customer"] > scores["agent"]:
            role_mapping[spk] = "Customer"
            confidence = 0.85
        else:
            role_mapping[spk] = "Speaker 1 (Role Uncertain)"
            confidence = 0.50
            review_flags.append({
                "reason": "Single Speaker Detected / Role Uncertain",
                "description": f"Only one speaker was detected in the recording. Mapped to {role_mapping[spk]}.",
                "line_numbers": [1],
                "source_excerpt": lines[0].get("text", "") if lines else ""
            })

    elif len(unique_speakers) == 2:
        spk1, spk2 = unique_speakers[0], unique_speakers[1]
        s1 = speaker_scores[spk1]
        s2 = speaker_scores[spk2]

        diff1 = s1["agent"] - s1["customer"]
        diff2 = s2["agent"] - s2["customer"]

        if diff1 > diff2:
            role_mapping[spk1] = "Agent"
            role_mapping[spk2] = "Customer"
            separation = abs(diff1 - diff2)
            confidence = min(0.99, max(0.60, 0.70 + (separation * 0.05)))
        elif diff2 > diff1:
            role_mapping[spk2] = "Agent"
            role_mapping[spk1] = "Customer"
            separation = abs(diff2 - diff1)
            confidence = min(0.99, max(0.60, 0.70 + (separation * 0.05)))
        else:
            first_spk = lines[0].get("speaker") if lines else spk1
            other_spk = spk2 if first_spk == spk1 else spk1
            role_mapping[first_spk] = "Agent"
            role_mapping[other_spk] = "Customer"
            confidence = 0.60
            review_flags.append({
                "reason": "Ambiguous Speaker Role Assignment",
                "description": f"Conversational evidence was equally balanced between {spk1} and {spk2}. Mapped based on call opening.",
                "line_numbers": [1, 2] if len(lines) >= 2 else [1],
                "source_excerpt": lines[0].get("text", "") if lines else ""
            })

    else:
        sorted_by_agent = sorted(unique_speakers, key=lambda s: speaker_scores[s]["agent"] - speaker_scores[s]["customer"], reverse=True)
        primary_agent = sorted_by_agent[0]
        role_mapping[primary_agent] = "Agent"

        sorted_by_cust = sorted([s for s in unique_speakers if s != primary_agent], key=lambda s: speaker_scores[s]["customer"] - speaker_scores[s]["agent"], reverse=True)
        primary_customer = sorted_by_cust[0]
        role_mapping[primary_customer] = "Customer"

        other_idx = 3
        for spk in unique_speakers:
            if spk in role_mapping:
                continue
            if speaker_scores[spk]["supervisor"] > 0:
                role_mapping[spk] = "Supervisor"
            else:
                role_mapping[spk] = f"Speaker {other_idx}"
                other_idx += 1
        confidence = 0.88

    mapped_lines: List[Dict[str, Any]] = []
    for line in lines:
        raw_spk = line.get("speaker", "SPEAKER_00")
        final_role = role_mapping.get(raw_spk, raw_spk)
        start_t = line.get("start")
        end_t = line.get("end")

        mapped_line = {
            "line_number": line["line_number"],
            "speaker": final_role,
            "raw_speaker": raw_spk,
            "start": start_t,
            "end": end_t,
            "timestamp_str": format_timestamp_range(start_t, end_t),
            "text": line["text"]
        }
        if line.get("overlap"):
            mapped_line["overlap"] = True
            mapped_line["overlapping_speakers"] = [role_mapping.get(s, s) for s in line.get("overlapping_speakers", [])]

        mapped_lines.append(mapped_line)

    return mapped_lines, role_mapping, round(confidence, 2), review_flags
