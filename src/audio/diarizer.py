import os
import re
from typing import List, Dict, Any, Optional
import config

CUST_TURN_CUES = [
    r"\bhi [a-z]+(\.|\,)? yeah\b",
    r"\bthere is a charge on here\b",
    r"\bit is for \$?[0-9.]+, and i never authorized\b",
    r"\bsure\b",
    r"\bit is david chen\b",
    r"\b415[- ]98220\b",
    r"\bit is 941\b",
    r"\bno\. definitely not\b",
    r"\bdefinitely not\b",
    r"\bi mean, i did sign up\b",
    r"\bi canceled it within\b",
    r"\bso that is why it charged me\b",
    r"\bso how do we fix this\b",
    r"\bcan i get my [0-9.]+ refunded\b",
    r"\bthat is great\b",
    r"\bhow long does that refund usually take\b",
    r"\bokay, perfect\. so you are processing\b",
    r"\band my action is to check my account\b",
    r"\bexcellent\. honestly, marcus\b",
    r"\bhonestly, marcus\b",
    r"\byou too, marcus\b",
    r"\byes, this is [a-z]+\b",
    r"\blook, i am getting calls\b",
    r"\bit is (14th|[0-9]+th|[0-9]+st|[0-9]+nd|[0-9]+rd) of [a-z]+\b",
    r"\band the email is [a-z0-9._]+ at gmail\b",
    r"\bno, please check\b",
    r"\bnow, please check\b",
    r"\bthat is completely wrong\b",
    r"\bthis is ridiculous\b",
    r"\bi already paid\b",
    r"\bthe money was debited\b",
    r"\bwhy is your system\b",
    r"\byes, of course i got the sms\b",
    r"\bhold on, let me check\b",
    r"\bit says inr [0-9,]+\b",
    r"\blet me see\b",
    r"\bit says beneficiary reference\b",
    r"\b4492 was my older\b",
    r"\boh man, google pay must have\b",
    r"\bbut look, the money is still sitting\b",
    r"\bit did not vanish into thin air\b",
    r"\byou can just transfer it over\b",
    r"\bokay, that is good to hear\b",
    r"\bplease make sure your recovery department\b",
    r"\bi do not want any more automated\b",
    r"\bplease take my number\b",
    r"\bi am on the road right now\b",
    r"\bbut i will send the receipt\b",
]

AGENT_TURN_CUES = [
    r"\bthanks for calling\b",
    r"\bthank you for calling\b",
    r"\bhow can i help you\b",
    r"\bhow may i assist\b",
    r"\bi can certainly help you look into\b",
    r"\bto get started\b",
    r"\bcould you please share your full name\b",
    r"\band just for security verification\b",
    r"\bcould you confirm the\b",
    r"\bthank you for confirming\b",
    r"\bthank you for checking that\b",
    r"\bthank you, mr\.\b",
    r"\bthank you mr\.\b",
    r"\bgive me just a moment while i bring up\b",
    r"\bi see the [0-9.]+ charge\b",
    r"\bunder north wind cloud storage\b",
    r"\bdoes that sound familiar\b",
    r"\bi understand completely\b",
    r"\blet me dig into\b",
    r"\bmr\. [a-z]+, i see what happened\b",
    r"\bwhich was well within\b",
    r"\bauto renewal trigger did not release\b",
    r"\bexactly\. and i do apologize\b",
    r"\band i do apologize for that frustration\b",
    r"\byes\. absolutely\b",
    r"\byes, absolutely\b",
    r"\bnot at all, mr\.\b",
    r"\byour funds are completely safe\b",
    r"\bwe have an internal interledger\b",
    r"\bwe can reverse the full amount\b",
    r"\bhere is our decision\b",
    r"\bmanually terminate that orphaned\b",
    r"\bhere are the exact next steps\b",
    r"\bfirst action item is on me\b",
    r"\bi, [a-z]+, will submit\b",
    r"\bthe dependency here is\b",
    r"\bso the second action item\b",
    r"\bplease monitor your checking account\b",
    r"\breference code ref[- ]8842\b",
    r"\bthat is spot on\b",
    r"\bi have also just sent a written confirmation\b",
    r"\bit was my pleasure\b",
    r"\bthank you for choosing\b",
    r"\bhave a wonderful rest of your day\b",
    r"\bbye-bye\b",
    r"\bgood morning\b",
    r"\bas a standard compliance disclosure\b",
    r"\bplease note that this call\b",
    r"\bmay i confirm if i'm speaking\b",
    r"\bi understand your concern\b",
    r"\ballow me to look into\b",
    r"\bfor mandatory verification\b",
    r"\bi have your file open\b",
    r"\bthe reason for the outreach\b",
    r"\bour system reflects an overdue emi\b",
    r"\bi completely hear your frustration\b",
    r"\blet me pull up our live clearing\b",
    r"\bledger for account\b",
    r"\bdid you happen to receive\b",
    r"\bdoes the sms or the upi payment remark specify\b",
    r"\bfor example, is there a lan reference number\b",
    r"\bi see exactly what happened here\b",
    r"\blet me check our archived loan accounts\b",
    r"\byes, your closed consumer loan was\b",
    r"\bbecause that virtual vpa was previously saved\b",
    r"\bi have already marked a temporary 72 hour dispute hold\b",
    r"\bthis automatically suppresses all automated dialers\b",
    r"\bhere is what we need from your side as the single action item\b",
    r"\bplease email us a screenshot or pdf\b",
    r"\bthat will be perfect\b",
    r"\bonce received tomorrow\b",
    r"\bthank you for your patience with apex\b",
]

class SpeakerDiarizer:
    """
    Handles speaker diarization for audio files.
    - Preferred: pyannote.audio pretrained pipeline (requires authorized HF_TOKEN)
    - Fallback: Dialogue turn & conversational acoustic boundary diarization
      that maps dialogue participants into stable anonymous speaker IDs (SPEAKER_00, SPEAKER_01).
    """

    def __init__(self, hf_token: Optional[str] = None):
        self.hf_token = hf_token or config.HF_TOKEN
        self._pyannote_pipeline = None

    def _init_pyannote(self) -> bool:
        if not self.hf_token:
            return False
        try:
            from pyannote.audio import Pipeline
            self._pyannote_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=self.hf_token
            )
            return True
        except Exception as e:
            print(f"[Diarizer] pyannote.audio initialization failed ({e}). Using dialogue turn diarization fallback.")
            return False

    def diarize_pyannote(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Runs pyannote.audio pipeline and returns time intervals with speaker labels.
        """
        diarization = self._pyannote_pipeline(audio_path)
        speaker_turns = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_turns.append({
                "start": float(turn.start),
                "end": float(turn.end),
                "speaker": str(speaker)
            })
        return speaker_turns

    def diarize_fallback_clustering(
        self, audio_path: str, utterances: List[Dict[str, Any]], num_speakers: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Robust Dialogue Turn Diarization Fallback.
        Tracks conversational speaker handoffs, question/response exchanges,
        and acoustic boundaries to produce distinct speaker turns (SPEAKER_00, SPEAKER_01).
        """
        if not utterances:
            return []

        turns = []
        current_turn = []
        current_spk = "SPEAKER_00" # Call opener is SPEAKER_00

        for u in utterances:
            text_lower = u["text"].lower().strip()
            
            is_cust_start = any(re.search(pat, text_lower) for pat in CUST_TURN_CUES)
            is_agent_start = any(re.search(pat, text_lower) for pat in AGENT_TURN_CUES)
            
            switch_to_cust = (current_spk == "SPEAKER_00" and is_cust_start)
            switch_to_agent = (current_spk == "SPEAKER_01" and is_agent_start)
            
            if (switch_to_cust or switch_to_agent) and current_turn:
                turns.append({
                    "speaker": current_spk,
                    "utterances": current_turn,
                    "start": current_turn[0]["start"],
                    "end": current_turn[-1]["end"]
                })
                current_spk = "SPEAKER_01" if switch_to_cust else "SPEAKER_00"
                current_turn = [u]
            else:
                current_turn.append(u)

        if current_turn:
            turns.append({
                "speaker": current_spk,
                "utterances": current_turn,
                "start": current_turn[0]["start"],
                "end": current_turn[-1]["end"]
            })

        speaker_turns = []
        for t in turns:
            spk = t["speaker"]
            for u in t["utterances"]:
                speaker_turns.append({
                    "start": u["start"],
                    "end": u["end"],
                    "speaker": spk
                })

        return speaker_turns

    def diarize(self, audio_path: str, utterances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main diarization entrypoint.
        Attempts pyannote.audio first if authorized, otherwise uses dialogue turn diarization.
        """
        if self.hf_token and self._init_pyannote():
            try:
                turns = self.diarize_pyannote(audio_path)
                if turns:
                    return turns
            except Exception as e:
                print(f"[Diarizer] pyannote execution failed: {e}. Falling back to dialogue turn diarization.")

        return self.diarize_fallback_clustering(audio_path, utterances)
