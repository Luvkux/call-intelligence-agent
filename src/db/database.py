from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import config
from src.db.models import Base, CallRecord, TranscriptLineRecord, ExtractedNoteRecord, HumanReviewRecord, AuditLogRecord

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {})

# Set expire_on_commit=False so instances remain readable and bound to their loaded data after db.commit() and db.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

def init_db():
    """Initializes database tables and performs lightweight migrations."""
    Base.metadata.create_all(bind=engine)
    # Perform lightweight migration for raw_speaker and source_type if missing
    try:
        with engine.connect() as conn:
            # Migration 1: transcript_lines.raw_speaker
            result_tl = conn.execute(text("PRAGMA table_info(transcript_lines)")).fetchall()
            tl_columns = [row[1] for row in result_tl]
            if "raw_speaker" not in tl_columns:
                conn.execute(text("ALTER TABLE transcript_lines ADD COLUMN raw_speaker VARCHAR(100)"))
                conn.commit()

            # Migration 2: call_records.source_type
            result_cr = conn.execute(text("PRAGMA table_info(call_records)")).fetchall()
            cr_columns = [row[1] for row in result_cr]
            if "source_type" not in cr_columns:
                conn.execute(text("ALTER TABLE call_records ADD COLUMN source_type VARCHAR(50)"))
                conn.commit()
    except Exception:
        # Ignore if table doesn't exist yet or already altered
        pass

def get_db():
    """Context manager / generator for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
