import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=True)
    source_type = Column(String(50), nullable=True, default="audio")  # audio, transcript_upload, transcript_paste, pdf_sample
    recording_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    short_tag = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    overall_sentiment = Column(String(50), nullable=True)
    customer_angry = Column(Boolean, default=False)
    profanity_detected = Column(Boolean, default=False)
    sentiment_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship("TranscriptLineRecord", back_populates="call", cascade="all, delete-orphan")
    notes = relationship("ExtractedNoteRecord", back_populates="call", cascade="all, delete-orphan")
    review_items = relationship("HumanReviewRecord", back_populates="call", cascade="all, delete-orphan")

class TranscriptLineRecord(Base):
    __tablename__ = "transcript_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, ForeignKey("call_records.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    speaker = Column(String(100), nullable=False)
    raw_speaker = Column(String(100), nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    text = Column(Text, nullable=False)

    call = relationship("CallRecord", back_populates="lines")

class ExtractedNoteRecord(Base):
    __tablename__ = "extracted_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, ForeignKey("call_records.id"), nullable=False)
    item_type = Column(String(50), nullable=False)  # Decision, ActionItem, Blocker, Compliance
    title = Column(Text, nullable=False)
    owner = Column(String(100), nullable=True)
    raw_date_mention = Column(String(100), nullable=True)
    resolved_due_date = Column(String(50), nullable=True)
    severity = Column(String(20), nullable=True)  # Red, Yellow, Green
    line_numbers_json = Column(Text, nullable=False)
    source_excerpt = Column(Text, nullable=False)

    call = relationship("CallRecord", back_populates="notes")

    @property
    def line_numbers(self):
        return json.loads(self.line_numbers_json) if self.line_numbers_json else []

    @line_numbers.setter
    def line_numbers(self, value):
        self.line_numbers_json = json.dumps(value)

class HumanReviewRecord(Base):
    __tablename__ = "human_review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, ForeignKey("call_records.id"), nullable=False)
    reason = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    line_numbers_json = Column(Text, nullable=False)
    source_excerpt = Column(Text, nullable=False)
    status = Column(String(50), default="Pending")  # Pending, Approved, Edited, Dismissed
    reviewer_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    call = relationship("CallRecord", back_populates="review_items")

    @property
    def line_numbers(self):
        return json.loads(self.line_numbers_json) if self.line_numbers_json else []

    @line_numbers.setter
    def line_numbers(self, value):
        self.line_numbers_json = json.dumps(value)

from src.utils.helpers import serialize_for_sqlite

class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, nullable=True)
    reviewer = Column(String(100), nullable=False, default="QA Agent")
    action = Column(String(100), nullable=False)
    _details = Column("details", Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        if "details" in kwargs:
            kwargs["_details"] = serialize_for_sqlite(kwargs.pop("details"))
        super().__init__(**kwargs)

    @property
    def details(self):
        return self._details

    @details.setter
    def details(self, value):
        self._details = serialize_for_sqlite(value)

