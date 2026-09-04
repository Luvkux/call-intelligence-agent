import os
import sys
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
import streamlit as st

# Configure full-width page settings (Sidebar removed)
st.set_page_config(
    page_title="Call Intelligence AI Agent",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for executive AI dashboard styling
st.markdown("""
<style>
    /* Hide standard sidebar completely */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    .main .block-container {
        max-width: 100% !important;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }
    /* Executive Header styling */
    .app-header {
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }

    /* Clean, Minimal Top Navigation Tabs styling */
    button[data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        color: #475569 !important;
        padding: 8px 16px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ff4b4b !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #ff4b4b !important;
    }

    :target {
        outline: 3px solid #4f46e5 !important;
        box-shadow: 0 0 15px rgba(79, 70, 229, 0.5) !important;
        border-radius: 8px;
        animation: highlight-pulse 2.5s ease-out;
    }
    @keyframes highlight-pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.7);
            border-color: #4f46e5 !important;
            background-color: #dbeafe !important;
        }
        50% {
            box-shadow: 0 0 0 12px rgba(79, 70, 229, 0);
            border-color: #6366f1 !important;
            background-color: #ede9fe !important;
        }
        100% {
            box-shadow: 0 0 0 0 rgba(79, 70, 229, 0);
            border-color: #4f46e5 !important;
            background-color: #f5f7ff !important;
        }
    }
    .transcript-highlight-active {
        animation: highlight-pulse 2.5s ease-in-out !important;
        border: 2px solid #4f46e5 !important;
        border-left: 6px solid #4f46e5 !important;
        background-color: #eef2ff !important;
    }

    .badge-line-num {
        background-color: #0f172a;
        color: #ffffff !important;
        font-weight: 700;
        padding: 3px 9px;
        border-radius: 4px;
        font-size: 0.85rem;
        letter-spacing: 0.02em;
        display: inline-block;
    }
    .badge-line-pill {
        background-color: #2563eb;
        color: #ffffff !important;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.80rem;
        text-decoration: none !important;
        display: inline-block;
        margin-right: 4px;
        cursor: pointer;
        transition: transform 0.1s ease-in-out, background-color 0.15s ease-in-out;
    }
    .badge-line-pill:hover {
        background-color: #1d4ed8;
        color: #ffffff !important;
        transform: scale(1.05);
    }
    .badge-agent {
        background-color: #e0e7ff;
        color: #3730a3;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.82rem;
        letter-spacing: 0.03em;
    }
    .badge-customer {
        background-color: #fef3c7;
        color: #92400e;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.82rem;
        letter-spacing: 0.03em;
    }
    .badge-supervisor {
        background-color: #ede9fe;
        color: #5b21b6;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.82rem;
    }
    .badge-timestamp {
        background-color: #f1f5f9;
        color: #475569;
        font-family: monospace;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.80rem;
    }
    .transcript-turn {
        padding: 12px 16px;
        margin-bottom: 12px;
        border-radius: 8px;
        border-left: 4px solid #cbd5e1;
        background-color: #f8fafc;
        scroll-margin-top: 80px;
    }
    .transcript-turn-agent {
        border-left-color: #4f46e5;
        background-color: #f5f7ff;
    }
    .transcript-turn-customer {
        border-left-color: #f59e0b;
        background-color: #fffdf5;
    }
</style>
<script>
(function() {
    function setupJumpHandler() {
        const handler = function(lineNum, callId) {
            try {
                var docs = [document];
                try { if (window.parent && window.parent.document) docs.push(window.parent.document); } catch(e) {}
                
                // 1. Switch to Tab 2 ('Intelligence & Grounded Notes')
                for (var d of docs) {
                    var tabBtns = Array.from(d.querySelectorAll('button[data-baseweb="tab"]'));
                    for (var btn of tabBtns) {
                        if (btn.innerText && (btn.innerText.indexOf("2. Intelligence") !== -1 || btn.innerText.indexOf("Intelligence & Grounded Notes") !== -1)) {
                            if (btn.getAttribute('aria-selected') !== 'true') {
                                btn.click();
                            }
                            break;
                        }
                    }
                }
                
                // 2. Smoothly scroll to and pulse-highlight the targeted transcript line
                function highlightAndScroll() {
                    var target = null;
                    for (var d of docs) {
                        target = d.getElementById('transcript-line-' + lineNum);
                        if (target) break;
                    }
                    if (target) {
                        for (var d of docs) {
                            var prevs = d.querySelectorAll('.transcript-highlight-active');
                            prevs.forEach(function(el) { el.classList.remove('transcript-highlight-active'); });
                        }
                        target.classList.add('transcript-highlight-active');
                        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        setTimeout(function() {
                            target.classList.remove('transcript-highlight-active');
                        }, 3000);
                        return true;
                    }
                    return false;
                }
                
                if (!highlightAndScroll()) {
                    setTimeout(highlightAndScroll, 50);
                    setTimeout(highlightAndScroll, 150);
                    setTimeout(highlightAndScroll, 350);
                }
            } catch(err) {
                console.error("Jump to line error:", err);
            }
        };
        
        window.jumpToTranscriptLine = handler;
        try { if (window.parent) window.parent.jumpToTranscriptLine = handler; } catch(e) {}
    }
    
    setupJumpHandler();
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupJumpHandler);
    }
})();
</script>
""", unsafe_allow_html=True)

import config
from src.audio.ffmpeg_check import check_ffmpeg_installed, get_ffmpeg_instructions
from src.audio.processor import AudioPipeline, format_transcript_as_text
from src.audio.role_mapper import format_timestamp_range
from src.transcript.parser import parse_transcript
from src.intelligence.extractor import CallIntelligenceExtractor
from src.intelligence.schemas import (
    CallIntelligenceOutput, Decision, ActionItem,
    Blocker, ComplianceObservation, HumanReviewItem, CallSentiment,
)
from src.grounding.validator import GroundingValidator
from src.db.database import init_db, SessionLocal
from src.db.models import (
    CallRecord, TranscriptLineRecord, ExtractedNoteRecord,
    HumanReviewRecord, AuditLogRecord,
)
from src.db.vector_store import VectorStore
from src.utils.helpers import (
    render_severity_badge, render_line_pills, export_call_to_json,
    export_call_to_markdown, serialize_for_sqlite, deserialize_from_sqlite,
)

# Initialize database tables on startup
init_db()

# ---------------------------------------------------------------------------
# Load secrets from st.secrets (populated from .streamlit/secrets.toml)
# ---------------------------------------------------------------------------
def _load_secret(key: str, required: bool = True) -> str:
    """Read a secret from st.secrets; show a clear error and stop if required but absent."""
    try:
        value = st.secrets[key]
    except (KeyError, FileNotFoundError):
        value = ""
    if required and not value:
        st.error(
            f"⛔ **Configuration Error**: Required secret `{key}` is missing.\n\n"
            "Please add it to `.streamlit/secrets.toml`:\n"
            f"```\n{key} = \"<your-value>\"\n```\n\n"
            "See `.streamlit/secrets.toml.example` for a template."
        )
        st.stop()
    return value


_gemini_api_key = _load_secret("GEMINI_API_KEY", required=True)
_hf_token       = _load_secret("HF_TOKEN",        required=False)
_gemini_model   = _load_secret("GEMINI_MODEL",    required=False) or "gemini-3.6-flash"

# Push secrets into config
config.GEMINI_API_KEY    = _gemini_api_key
config.HF_TOKEN          = _hf_token
config.GEMINI_MODEL      = _gemini_model
config.GEMINI_MODEL_NAME = _gemini_model

# Pre-flight FFmpeg check (done silently)
ffmpeg_ok = check_ffmpeg_installed()

# ---------------------------------------------------------------------------
# Session-state initialization
# ---------------------------------------------------------------------------
if "active_call_id" not in st.session_state:
    st.session_state.active_call_id = None

if "prev_audio_name" not in st.session_state:
    st.session_state.prev_audio_name = None

if "prev_transcript_name" not in st.session_state:
    st.session_state.prev_transcript_name = None

def run_unified_intelligence_pipeline(
    title: str,
    file_path: Optional[str],
    source_type: str,
    lines: List[Dict[str, Any]],
    call_dt: datetime,
    extra_review_flags: Optional[List[Dict[str, Any]]] = None
) -> int:
    """
    Unified downstream analysis pipeline for all inputs:
    1. Gemini LLM structured intelligence extraction
    2. Exact line grounding validation & auto-correction
    3. Database persistence with strict call_id isolation
    4. FAISS semantic vector store indexing
    """
    extractor = CallIntelligenceExtractor(api_key=config.GEMINI_API_KEY)
    extracted_output = extractor.extract(lines, call_dt)
    validated_output, audit_logs = GroundingValidator.validate_output(extracted_output, lines)

    db = SessionLocal()
    try:
        call_rec = CallRecord(
            title=title,
            file_path=file_path,
            source_type=source_type,
            recording_date=call_dt,
            short_tag=validated_output.short_tag,
            summary=validated_output.summary,
            overall_sentiment=validated_output.sentiment.overall_sentiment,
            customer_angry=validated_output.sentiment.customer_angry,
            profanity_detected=validated_output.sentiment.profanity_detected,
            sentiment_explanation=validated_output.sentiment.sentiment_explanation,
        )
        db.add(call_rec)
        db.commit()
        db.refresh(call_rec)

        call_id = call_rec.id
        call_title = call_rec.title

        for line in lines:
            db.add(TranscriptLineRecord(
                call_id=call_id,
                line_number=line["line_number"],
                speaker=line["speaker"],
                raw_speaker=line.get("raw_speaker") or ("SPEAKER_00" if line["speaker"] == "Agent" else "SPEAKER_01"),
                start_time=line.get("start"),
                end_time=line.get("end"),
                text=line["text"],
            ))

        for dec in validated_output.decisions:
            db.add(ExtractedNoteRecord(
                call_id=call_id, item_type="Decision", title=dec.decision,
                line_numbers=dec.line_numbers, source_excerpt=dec.source_excerpt,
            ))

        for act in validated_output.action_items:
            db.add(ExtractedNoteRecord(
                call_id=call_id, item_type="ActionItem", title=act.task,
                owner=act.owner, raw_date_mention=act.raw_date_mention,
                resolved_due_date=act.resolved_due_date,
                line_numbers=act.line_numbers, source_excerpt=act.source_excerpt,
            ))

        for blk in validated_output.blockers:
            db.add(ExtractedNoteRecord(
                call_id=call_id, item_type="Blocker", title=blk.blocker,
                line_numbers=blk.line_numbers, source_excerpt=blk.source_excerpt,
            ))

        for obs in validated_output.compliance_observations:
            db.add(ExtractedNoteRecord(
                call_id=call_id, item_type="Compliance", title=obs.observation,
                severity=obs.severity, line_numbers=obs.line_numbers, source_excerpt=obs.source_excerpt,
            ))

        for rev in validated_output.human_review_items:
            db.add(HumanReviewRecord(
                call_id=call_id, reason=rev.reason, description=rev.description,
                line_numbers=rev.line_numbers, source_excerpt=rev.source_excerpt, status="Pending",
            ))

        if extra_review_flags:
            for flag in extra_review_flags:
                db.add(HumanReviewRecord(
                    call_id=call_id, reason=flag["reason"], description=flag["description"],
                    line_numbers=flag.get("line_numbers", [1]), source_excerpt=flag.get("source_excerpt", ""), status="Pending",
                ))

        if audit_logs:
            for log in audit_logs:
                try:
                    db.add(AuditLogRecord(
                        call_id=call_id,
                        reviewer="System Grounding Engine",
                        action="Grounding Validation",
                        details=serialize_for_sqlite(log)
                    ))
                except Exception as log_err:
                    import logging
                    logging.getLogger(__name__).warning("Failed to record grounding audit log for call #%s: %s", call_id, log_err)

        db.commit()
    finally:
        db.close()

    VectorStore().add_transcript_lines(call_id, call_title, lines)
    return call_id

# ---------------------------------------------------------------------------
# Executive Top Header (Full Width)
# ---------------------------------------------------------------------------
st.title("🎙️ Call Intelligence AI Agent")
st.caption("Verifiable speech analytics, speaker diarization, line-grounded intelligence, and compliance monitoring.")

# Surface FFmpeg warning banner only if missing
if not ffmpeg_ok:
    st.warning(
        "⚠️ **FFmpeg not found.** Audio processing is unavailable.\n\n"
        + get_ffmpeg_instructions()
    )

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 1. Upload & Process Call",
    "📋 2. Intelligence & Grounded Notes",
    "⚠️ 3. Human Review Queue",
    "🔍 4. Transcript Search & Analytics"
])

# =============================================================================
# TAB 1: UPLOAD & PROCESS CALL
# =============================================================================
with tab1:
    st.header("Process Call Audio Recording or Existing Transcript")
    st.markdown(
        "Analyze call conversations using either **Audio Recordings** (with STT, word timestamps & diarization) "
        "or **Existing Transcripts** (supporting `.txt`, `.json`, `.csv`, `.srt`, `.vtt`, and raw pasted text)."
    )

    # Quick Demo Section
    with st.container():
        st.markdown(
            """
            <div style="background-color: #1e293b; border-left: 4px solid #6366f1; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px;">
                <strong style="color:#f8fafc; font-size:1rem;">🚀 Quick Demo: PDF Problem Sample</strong>
                <div style="color:#94a3b8; font-size:0.85rem; margin-top:2px;">Test the exact debt-collection settlement scenario from page 3 of the assignment PDF.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🚀 Process PDF Debt Collection Sample", key="btn_pdf_sample", use_container_width=True):
            if not config.GEMINI_API_KEY:
                st.error("Please add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to process the call.")
            else:
                with st.spinner("Processing PDF Debt Collection Sample (July 1, 2026)..."):
                    try:
                        call_dt = datetime(2026, 7, 1, 0, 0, 0)
                        sample_lines = [
                            {"line_number": 1, "speaker": "Agent",    "start": 0.0,  "end": 4.0,  "text": "Hello, thank you for calling debt management services. This call is being recorded for quality assurance."},
                            {"line_number": 2, "speaker": "Customer", "start": 4.5,  "end": 7.0,  "text": "Hi, I'm calling about my account settlement offer."},
                            {"line_number": 3, "speaker": "Agent",    "start": 7.5,  "end": 12.0, "text": "Thank you. Our total balance is $1,400. We require full payment by end of month."},
                            {"line_number": 4, "speaker": "Customer", "start": 12.5, "end": 16.0, "text": "That's still too much right now. Could I do $700 now and $700 next month?"},
                            {"line_number": 5, "speaker": "Agent",    "start": 16.5, "end": 24.0, "text": "Let me note that – $700 today and $700 on the 15th of next month. I'll need a supervisor to approve the settlement split, I'll follow up by Friday."},
                        ]
                        for line in sample_lines:
                            line["timestamp_str"] = format_timestamp_range(line.get("start"), line.get("end"))

                        call_id = run_unified_intelligence_pipeline(
                            title="Debt Collection Call - Sample Split",
                            file_path="sample_pdf_debt_collection.wav",
                            source_type="pdf_sample",
                            lines=sample_lines,
                            call_dt=call_dt
                        )
                        st.session_state.active_call_id = call_id
                        st.success("✅ Call processed successfully! Switch to Tab 2: Intelligence & Grounded Notes to view the results.")
                    except Exception as e:
                        st.error(f"Error processing sample: {e}")

    st.markdown("---")

    # Two distinct input cards: Audio Recording vs Existing Transcript
    col_audio, col_transcript = st.columns([1, 1], gap="large")

    with col_audio:
        st.markdown("### 🎙️ Audio Recording")
        st.caption("Upload MP3, WAV, M4A, or OGG audio for STT, diarization, role mapping, and intelligence.")
        uploaded_audio_file = st.file_uploader(
            "Choose a call audio recording",
            type=["mp3", "wav", "m4a", "ogg"],
            key="audio_uploader"
        )
        process_audio_btn = st.button("▶️ Process Audio Call", key="btn_proc_audio", use_container_width=True)

    with col_transcript:
        st.markdown("### 📄 Upload or Paste Call Transcript")
        st.caption("If you already have a transcript, upload a transcript file or paste the transcript directly. The system will analyze it without requiring audio processing.")
        uploaded_transcript_file = st.file_uploader(
            "Upload Transcript File (.txt, .json, .csv, .srt, .vtt)",
            type=["txt", "json", "csv", "srt", "vtt"],
            key="transcript_uploader"
        )
        st.markdown("**OR Paste Transcript Directly:**")
        pasted_transcript_text = st.text_area(
            "Paste Transcript Text",
            placeholder="[00:00 - 00:04] Agent: Good morning, you have reached Apex Financial Services...\n[00:05 - 00:08] Customer: Yes, this is Vikram speaking...",
            height=130,
            key="pasted_transcript_area"
        )
        process_transcript_btn = st.button("▶️ Process Transcript", key="btn_proc_transcript", use_container_width=True)

    # ------------------------------------------------------------------
    # Detect input removal: reset active call if current inputs are removed
    # ------------------------------------------------------------------
    curr_audio_name = uploaded_audio_file.name if uploaded_audio_file is not None else None
    curr_transcript_name = uploaded_transcript_file.name if uploaded_transcript_file is not None else None
    curr_pasted_has_text = bool(pasted_transcript_text and pasted_transcript_text.strip())

    if (
        st.session_state.prev_audio_name is not None
        and curr_audio_name is None
        and curr_transcript_name is None
        and not curr_pasted_has_text
    ):
        st.session_state.active_call_id = None

    if (
        st.session_state.prev_transcript_name is not None
        and curr_transcript_name is None
        and curr_audio_name is None
        and not curr_pasted_has_text
    ):
        st.session_state.active_call_id = None

    st.session_state.prev_audio_name = curr_audio_name
    st.session_state.prev_transcript_name = curr_transcript_name

    # ------------------------------------------------------------------
    # Audio Processing Handler
    # ------------------------------------------------------------------
    if process_audio_btn:
        if uploaded_audio_file is None:
            st.warning("Please choose an audio file to upload.")
        elif not ffmpeg_ok:
            st.error("Cannot process audio file because FFmpeg is missing.")
        elif not config.GEMINI_API_KEY:
            st.error("Please add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to process the call.")
        else:
            with st.spinner("Processing Audio (STT with Word Timestamps, Diarization, Role Mapping, Extraction)..."):
                try:
                    save_path = os.path.join(config.UPLOADS_DIR, uploaded_audio_file.name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_audio_file.getbuffer())

                    call_dt = datetime.now()

                    audio_pipeline = AudioPipeline(hf_token=config.HF_TOKEN)
                    lines = audio_pipeline.process_audio(save_path)

                    call_id = run_unified_intelligence_pipeline(
                        title=uploaded_audio_file.name,
                        file_path=save_path,
                        source_type="audio",
                        lines=lines,
                        call_dt=call_dt,
                        extra_review_flags=getattr(audio_pipeline, "last_review_flags", [])
                    )

                    st.session_state.active_call_id = call_id
                    st.success("✅ Call processed successfully! Switch to Tab 2: Intelligence & Grounded Notes to view the results.")
                except Exception as e:
                    st.error(f"Failed to process audio call: {e}")

    # ------------------------------------------------------------------
    # Transcript Processing Handler
    # ------------------------------------------------------------------
    if process_transcript_btn:
        if uploaded_transcript_file is None and not (pasted_transcript_text and pasted_transcript_text.strip()):
            st.warning("Transcript is empty. Please upload a valid transcript or paste transcript text.")
        elif not config.GEMINI_API_KEY:
            st.error("Please add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to process the call.")
        else:
            with st.spinner("Parsing & Analyzing Transcript (Role Normalization, Extraction, Grounding)..."):
                try:
                    call_dt = datetime.now()

                    if uploaded_transcript_file is not None:
                        lines, role_mapping, role_conf, review_flags = parse_transcript(
                            uploaded_transcript_file.getvalue(),
                            filename=uploaded_transcript_file.name
                        )
                        call_title = f"Transcript: {uploaded_transcript_file.name}"
                        source_type = "transcript_upload"
                        save_path = os.path.join(config.UPLOADS_DIR, uploaded_transcript_file.name)
                        try:
                            with open(save_path, "wb") as f:
                                f.write(uploaded_transcript_file.getbuffer())
                        except Exception:
                            save_path = None
                    else:
                        lines, role_mapping, role_conf, review_flags = parse_transcript(
                            pasted_transcript_text.strip()
                        )
                        call_title = f"Pasted Transcript ({datetime.now().strftime('%b %d, %H:%M')})"
                        source_type = "transcript_paste"
                        save_path = None

                    call_id = run_unified_intelligence_pipeline(
                        title=call_title,
                        file_path=save_path,
                        source_type=source_type,
                        lines=lines,
                        call_dt=call_dt,
                        extra_review_flags=review_flags
                    )

                    st.session_state.active_call_id = call_id
                    st.success("✅ Call processed successfully! Switch to Tab 2: Intelligence & Grounded Notes to view the results.")
                except Exception as e:
                    st.error(f"Failed to process transcript: {e}")

# =============================================================================
# TAB 2: INTELLIGENCE & GROUNDED NOTES
# =============================================================================
with tab2:
    st.header("Call Intelligence & Line-Grounded Notes")

    active_id = st.session_state.active_call_id

    if active_id is None:
        st.info("💡 **No call data available.** Upload an audio recording or upload/paste a transcript in Tab 1 to begin.")
    else:
        db = SessionLocal()
        call_obj   = db.query(CallRecord).filter(CallRecord.id == active_id).first()
        lines_obj  = (db.query(TranscriptLineRecord)
                        .filter(TranscriptLineRecord.call_id == active_id)
                        .order_by(TranscriptLineRecord.line_number)
                        .all())
        notes_obj  = db.query(ExtractedNoteRecord).filter(ExtractedNoteRecord.call_id == active_id).all()
        review_obj = db.query(HumanReviewRecord).filter(HumanReviewRecord.call_id == active_id).all()

        if call_obj is None:
            st.warning(f"Call #{active_id} was not found in the database.")
            db.close()
        else:
            # Source Type Display
            source_labels = {
                "audio": "🎙️ Audio Recording",
                "transcript_upload": "📄 Uploaded Transcript",
                "transcript_paste": "📝 Pasted Transcript",
                "pdf_sample": "📑 PDF Problem Sample"
            }
            source_str = source_labels.get(getattr(call_obj, 'source_type', 'audio') or 'audio', '🎙️ Audio Recording')

            # Call Metadata Banner
            st.markdown(f"### 📞 {call_obj.title}")
            st.markdown(
                f"**Call ID:** `#{call_obj.id}` &nbsp;|&nbsp; "
                f"**Source:** `{source_str}` &nbsp;|&nbsp; "
                f"**Recording Date:** `{call_obj.recording_date.strftime('%Y-%m-%d') if call_obj.recording_date else 'N/A'}`"
            )
            st.markdown(f"**Tag:** `{call_obj.short_tag}`")
            st.write(f"**Summary:** {call_obj.summary}")

            # Top KPI metrics
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Overall Sentiment", call_obj.overall_sentiment)
            col_b.metric("Angry Customer", "🔴 YES" if call_obj.customer_angry else "🟢 NO")
            col_c.metric("Profanity Flag", "🔴 DETECTED" if call_obj.profanity_detected else "🟢 CLEAN")
            col_d.metric("Transcript Lines", len(lines_obj))

            st.markdown("---")

            left_col, right_col = st.columns([1, 1])

            with left_col:
                st.subheader("📌 Extracted Structured Notes")

                # Decisions
                st.markdown("#### Decisions Made")
                decisions = [n for n in notes_obj if n.item_type == "Decision"]
                if decisions:
                    for d in decisions:
                        st.markdown(
                            f"""
                            <div style="padding:10px 14px; margin-bottom:10px; border-radius:6px; background-color:#f0fdf4; border-left:4px solid #22c55e;">
                                <strong>Decision:</strong> {d.title}<br>
                                <div style="margin-top:4px; margin-bottom:4px;"><small><b>Grounded Lines:</b> {render_line_pills(d.line_numbers, call_id=active_id)}</small></div>
                                <div style="font-size:0.88rem; color:#475569; font-style:italic;">"{d.source_excerpt}"</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("No explicit decisions recorded.")

                # Action Items
                st.markdown("#### Action Items")
                actions = [n for n in notes_obj if n.item_type == "ActionItem"]
                if actions:
                    for a in actions:
                        due = a.resolved_due_date or a.raw_date_mention or "No deadline"
                        st.markdown(
                            f"""
                            <div style="padding:10px 14px; margin-bottom:10px; border-radius:6px; background-color:#eff6ff; border-left:4px solid #3b82f6;">
                                <strong>Task:</strong> {a.title}<br>
                                <div style="margin-top:2px; font-size:0.88rem;"><b>Owner:</b> {a.owner or 'Unassigned'} | <b>Due:</b> <code>{due}</code></div>
                                <div style="margin-top:4px; margin-bottom:4px;"><small><b>Grounded Lines:</b> {render_line_pills(a.line_numbers, call_id=active_id)}</small></div>
                                <div style="font-size:0.88rem; color:#475569; font-style:italic;">"{a.source_excerpt}"</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("No action items recorded.")

                # Blockers
                st.markdown("#### Blockers")
                blockers = [n for n in notes_obj if n.item_type == "Blocker"]
                if blockers:
                    for b in blockers:
                        st.markdown(
                            f"""
                            <div style="padding:10px 14px; margin-bottom:10px; border-radius:6px; background-color:#fffbeb; border-left:4px solid #f59e0b;">
                                <strong>Blocker:</strong> {b.title}<br>
                                <div style="margin-top:4px; margin-bottom:4px;"><small><b>Grounded Lines:</b> {render_line_pills(b.line_numbers, call_id=active_id)}</small></div>
                                <div style="font-size:0.88rem; color:#475569; font-style:italic;">"{b.source_excerpt}"</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("No blockers identified.")

                # Compliance
                st.markdown("#### Compliance & Policy Observations")
                compliance = [n for n in notes_obj if n.item_type == "Compliance"]
                if compliance:
                    for c in compliance:
                        st.markdown(
                            f"""
                            <div style="padding:10px 14px; margin-bottom:10px; border-radius:6px; background-color:#f8fafc; border-left:4px solid #64748b;">
                                {render_severity_badge(c.severity)} - <strong>{c.title}</strong><br>
                                <div style="margin-top:4px; margin-bottom:4px;"><small><b>Grounded Lines:</b> {render_line_pills(c.line_numbers, call_id=active_id)}</small></div>
                                <div style="font-size:0.88rem; color:#475569; font-style:italic;">"{c.source_excerpt}"</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("No compliance observations.")

                # Human Review Items for this call
                st.markdown("#### ⚠️ Flagged for Human Review")
                if review_obj:
                    for r in review_obj:
                        st.markdown(
                            f"""
                            <div style="padding:10px 14px; margin-bottom:10px; border-radius:6px; background-color:#fef2f2; border-left:4px solid #ef4444;">
                                <strong style="color:#b91c1c;">Reason:</strong> {r.reason}<br>
                                <div style="font-size:0.90rem; margin-top:2px;"><b>Description:</b> {r.description}</div>
                                <div style="margin-top:4px; margin-bottom:4px;"><small><b>Grounded Lines:</b> {render_line_pills(r.line_numbers, call_id=active_id)}</small></div>
                                <div style="font-size:0.88rem; color:#475569; font-style:italic;">"{r.source_excerpt}"</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("No items pending human review for this call.")

            with right_col:
                st.subheader("📜 Line-Indexed Grounded Transcript")
                st.caption("Every note points back to exact, un-reworded transcript lines with audio timestamps.")

                req_target_line = st.session_state.get("target_scroll_line")
                req_target_call = st.session_state.get("target_call_id")
                is_valid_target_call = (req_target_call is None or req_target_call == active_id)

                for line in lines_obj:
                    time_badge = format_timestamp_range(line.start_time, line.end_time)
                    spk = line.speaker
                    spk_id_str = getattr(line, 'raw_speaker', None) or ("SPEAKER_00" if spk == "Agent" else "SPEAKER_01" if spk == "Customer" else "SPEAKER_02")
                    
                    is_active_target = (
                        req_target_line is not None
                        and req_target_line == line.line_number
                        and is_valid_target_call
                    )

                    if spk == "Agent":
                        badge_html = f'<span class="badge-agent">AGENT</span> <span class="badge-timestamp">{spk_id_str}</span> <span class="badge-timestamp">{time_badge}</span>'
                        card_class = "transcript-turn transcript-turn-agent"
                    elif spk == "Customer":
                        badge_html = f'<span class="badge-customer">CUSTOMER</span> <span class="badge-timestamp">{spk_id_str}</span> <span class="badge-timestamp">{time_badge}</span>'
                        card_class = "transcript-turn transcript-turn-customer"
                    elif spk == "Supervisor":
                        badge_html = f'<span class="badge-supervisor">SUPERVISOR</span> <span class="badge-timestamp">{spk_id_str}</span> <span class="badge-timestamp">{time_badge}</span>'
                        card_class = "transcript-turn transcript-turn-agent"
                    else:
                        badge_html = f'<span class="badge-timestamp">{spk}</span> <span class="badge-timestamp">{spk_id_str}</span> <span class="badge-timestamp">{time_badge}</span>'
                        card_class = "transcript-turn"

                    if is_active_target:
                        card_class += " transcript-highlight-active"

                    st.markdown(
                        f"""
                        <div id="transcript-line-{line.line_number}" class="{card_class}">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; padding-bottom:4px; border-bottom:1px solid rgba(0,0,0,0.06);">
                                <span class="badge-line-num">Line {line.line_number}</span>
                                <div style="display:flex; align-items:center; gap:6px;">{badge_html}</div>
                            </div>
                            <div style="font-size:0.95rem; color:#1e293b; line-height:1.5;">{line.text}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                if req_target_line is not None and is_valid_target_call:
                    line_numbers_in_call = [l.line_number for l in lines_obj]
                    if req_target_line in line_numbers_in_call:
                        st.markdown(
                            f"""
                            <script>
                                (function() {{
                                    setTimeout(function() {{
                                        var targetEl = document.getElementById("transcript-line-{req_target_line}");
                                        if (targetEl) {{
                                            targetEl.scrollIntoView({{ behavior: "smooth", block: "center" }});
                                        }}
                                    }}, 150);
                                }})();
                            </script>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.warning(f"⚠️ Transcript Line {req_target_line} could not be found for the current call.")
                    # Reset target scroll line after one render pass
                    st.session_state.target_scroll_line = None

            st.markdown("---")
            st.subheader("📥 Export Call Intelligence Report")
            exp_col1, exp_col2 = st.columns(2)

            call_export_data = {
                "title": call_obj.title,
                "recording_date": call_obj.recording_date,
                "source_type": getattr(call_obj, 'source_type', 'audio'),
                "short_tag": call_obj.short_tag,
                "summary": call_obj.summary,
                "overall_sentiment": call_obj.overall_sentiment,
                "decisions": [{"decision": d.title, "line_numbers": d.line_numbers, "source_excerpt": d.source_excerpt} for d in decisions],
                "action_items": [{"task": a.title, "owner": a.owner, "raw_date_mention": a.raw_date_mention, "resolved_due_date": a.resolved_due_date, "line_numbers": a.line_numbers, "source_excerpt": a.source_excerpt} for a in actions],
                "blockers": [{"blocker": b.title, "line_numbers": b.line_numbers, "source_excerpt": b.source_excerpt} for b in blockers],
                "compliance_observations": [{"severity": c.severity, "category": "Compliance", "observation": c.title, "line_numbers": c.line_numbers, "source_excerpt": c.source_excerpt} for c in compliance],
                "human_review_items": [{"reason": r.reason, "description": r.description, "line_numbers": r.line_numbers, "source_excerpt": r.source_excerpt} for r in review_obj],
            }

            with exp_col1:
                st.download_button(
                    "Export as JSON",
                    data=export_call_to_json(call_export_data),
                    file_name=f"call_{call_obj.id}_intelligence.json",
                    mime="application/json",
                    use_container_width=True
                )
            with exp_col2:
                st.download_button(
                    "Export as Markdown",
                    data=export_call_to_markdown(call_export_data),
                    file_name=f"call_{call_obj.id}_intelligence.md",
                    mime="text/markdown",
                    use_container_width=True
                )

            db.close()

# =============================================================================
# TAB 3: HUMAN REVIEW QUEUE
# =============================================================================
with tab3:
    st.header("⚠️ Human Review & Escalation Queue")
    st.markdown(
        "The AI Agent flags items whenever confidence, missing information, "
        "recording consent absence, Cease & Desist triggers, or policy limits "
        "require human judgment."
    )

    active_id = st.session_state.active_call_id

    if active_id is None:
        st.info("💡 **No call data available.** Upload an audio recording or upload/paste a transcript in Tab 1 to begin.")
    else:
        db = SessionLocal()

        pending_items = (
            db.query(HumanReviewRecord)
            .filter(
                HumanReviewRecord.call_id == active_id,
                HumanReviewRecord.status == "Pending",
            )
            .all()
        )

        st.caption(f"Showing human review items for **Call #{active_id}**")

        if not pending_items:
            st.success("🎉 No pending review items for this call.")
        else:
            st.write(f"**Items Awaiting Review:** `{len(pending_items)}`")

            for item in pending_items:
                with st.expander(f"⚠️ [{item.reason}] — Call #{item.call_id} (Line {item.line_numbers})", expanded=True):
                    st.write(f"**Issue Description:** {item.description}")
                    st.markdown(f"**Grounding Citation:** {render_line_pills(item.line_numbers, call_id=active_id)}", unsafe_allow_html=True)
                    st.info(f"\"{item.source_excerpt}\"")

                    reviewer_note = st.text_input(f"Reviewer Comments (ID: {item.id})", key=f"note_{item.id}")

                    btn_col1, btn_col2, btn_col3 = st.columns(3)

                    with btn_col1:
                        if st.button("✅ Approve", key=f"app_{item.id}"):
                            item.status = "Approved"
                            item.reviewer_notes = reviewer_note
                            db.add(AuditLogRecord(call_id=item.call_id, action="Approve", details=f"Approved review item #{item.id}: {item.reason}"))
                            db.commit()
                            st.success("Approved!")
                            st.rerun()

                    with btn_col2:
                        if st.button("✏️ Edit & Resolve", key=f"edit_{item.id}"):
                            item.status = "Edited"
                            item.reviewer_notes = reviewer_note
                            db.add(AuditLogRecord(call_id=item.call_id, action="Edit & Resolve", details=f"Edited item #{item.id}: {reviewer_note}"))
                            db.commit()
                            st.success("Resolved with edit!")
                            st.rerun()

                    with btn_col3:
                        if st.button("❌ Dismiss / Reject", key=f"dism_{item.id}"):
                            item.status = "Dismissed"
                            item.reviewer_notes = reviewer_note
                            db.add(AuditLogRecord(call_id=item.call_id, action="Dismiss", details=f"Dismissed item #{item.id}"))
                            db.commit()
                            st.info("Dismissed!")
                            st.rerun()

        st.markdown("---")
        st.subheader("📋 Audit Log — This Call")
        logs = (
            db.query(AuditLogRecord)
            .filter(AuditLogRecord.call_id == active_id)
            .order_by(AuditLogRecord.timestamp.desc())
            .all()
        )
        if logs:
            log_data = []
            for l in logs:
                det = l.details
                parsed = deserialize_from_sqlite(det)
                if isinstance(parsed, (dict, list)):
                    det_str = json.dumps(parsed, ensure_ascii=False)
                else:
                    det_str = str(det) if det is not None else ""
                log_data.append({
                    "Timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "Reviewer": l.reviewer,
                    "Action": l.action,
                    "Details": det_str,
                })
            st.dataframe(log_data, use_container_width=True)
        else:
            st.caption("No human intervention logs recorded for this call yet.")

        db.close()

# =============================================================================
# TAB 4: TRANSCRIPT SEARCH & ANALYTICS
# =============================================================================
with tab4:
    st.header("🔍 Transcript Semantic Search (FAISS)")

    active_id = st.session_state.active_call_id

    if active_id is None:
        st.info("💡 **No call data available.** Upload an audio recording or upload/paste a transcript in Tab 1 to begin.")
    else:
        db = SessionLocal()
        call_obj = db.query(CallRecord).filter(CallRecord.id == active_id).first()
        db.close()

        call_label = f"Call #{active_id}" if call_obj is None else f"Call #{active_id} — {call_obj.title}"
        st.caption(f"Searching transcript for **{call_label}**")
        st.markdown("Search the transcript of the current call using vector embeddings.")

        query = st.text_input(
            "Enter search query",
            placeholder="e.g. 'settlement split', 'recording permission', 'supervisor approval', 'lawyer', 'overdue emi'"
        )

        if query:
            vector_store = VectorStore()
            search_results = vector_store.search(query, top_k=5, call_id=active_id)

            if not search_results:
                st.info("No matching transcript lines found for this call.")
            else:
                st.markdown(f"### Search Results for: *\"{query}\"*")
                for res in search_results:
                    pill_html = render_line_pills([res['line_number']], call_id=res['call_id'])
                    st.markdown(f"""
**Call #{res['call_id']}: {res['call_title']}** | Grounding: {pill_html} | **Similarity Score:** `{res['score']}`
> `{res['speaker']}`: {res['text']}
                    """, unsafe_allow_html=True)
