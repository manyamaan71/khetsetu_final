"""
database.py

SQLite by default for the MVP (see DATABASE_URL in config.py). Because
we use SQLAlchemy's engine/URL abstraction rather than raw sqlite3
calls, switching to PostgreSQL later is just a DATABASE_URL change -
no application code needs to change.
"""
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ScanRecord(Base):
    """Aggregate-only record used to power /api/admin/stats.
    Does NOT store the uploaded image or any farmer-identifying data -
    only what's needed for aggregate counts, per the admin page's
    'no individual farmer information' requirement.
    """
    __tablename__ = "scan_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    class_name = Column(String, nullable=False)
    crop = Column(String, nullable=False)
    disease = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    is_healthy = Column(Boolean, nullable=False)
    is_confident = Column(Boolean, nullable=False)
    demo_mode = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="ok")      # ok | low_confidence | not_a_leaf
    source = Column(String, nullable=False, default="web")     # web | whatsapp


class TranslationCache(Base):
    """Persistent translations keyed by the source text and target language."""
    __tablename__ = "translation_cache"

    text_hash = Column(String(64), primary_key=True)
    language = Column(String(8), primary_key=True)
    translated_text = Column(Text, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
