"""SQLAlchemy warehouse schema for the Data Agent.

Telco and Retail IDs live in different tables and are never used as a join key.
Customers do not store Churn.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Float, Integer, String, Text, create_engine
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config.settings import DATABASE_URL, DATA_DIR


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    gender: Mapped[str] = mapped_column(String(16))
    senior_citizen: Mapped[int] = mapped_column(Integer)
    partner: Mapped[str] = mapped_column(String(8))
    dependents: Mapped[str] = mapped_column(String(8))
    tenure: Mapped[int] = mapped_column(Integer)
    phone_service: Mapped[str] = mapped_column(String(8))
    multiple_lines: Mapped[str] = mapped_column(String(32))
    internet_service: Mapped[str] = mapped_column(String(32))
    online_security: Mapped[str] = mapped_column(String(32))
    online_backup: Mapped[str] = mapped_column(String(32))
    device_protection: Mapped[str] = mapped_column(String(32))
    tech_support: Mapped[str] = mapped_column(String(32))
    streaming_tv: Mapped[str] = mapped_column(String(32))
    streaming_movies: Mapped[str] = mapped_column(String(32))
    contract: Mapped[str] = mapped_column(String(32))
    paperless_billing: Mapped[str] = mapped_column(String(8))
    payment_method: Mapped[str] = mapped_column(String(64))
    monthly_charges: Mapped[float] = mapped_column(Float)
    total_charges: Mapped[float] = mapped_column(Float)


class RetailRFM(Base):
    __tablename__ = "retail_rfm"

    retail_customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_purchase_date: Mapped[str] = mapped_column(String(32))
    recency_days: Mapped[int] = mapped_column(Integer)
    frequency: Mapped[int] = mapped_column(Integer)
    monetary: Mapped[float] = mapped_column(Float)
    avg_order_value: Mapped[float] = mapped_column(Float)
    r_score: Mapped[int] = mapped_column(Integer)
    f_score: Mapped[int] = mapped_column(Integer)
    m_score: Mapped[int] = mapped_column(Integer)
    rfm_segment: Mapped[str] = mapped_column(String(32))


class SyntheticEvent(Base):
    __tablename__ = "synthetic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(32), index=True)
    event_index: Mapped[int] = mapped_column(Integer)
    months_before_snapshot: Mapped[int] = mapped_column(Integer)
    amount: Mapped[float] = mapped_column(Float)
    event_type: Mapped[str] = mapped_column(String(64))
    lineage: Mapped[str] = mapped_column(String(32))
    profile: Mapped[str] = mapped_column(String(64))


class SyntheticReview(Base):
    __tablename__ = "synthetic_reviews"

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tone: Mapped[str] = mapped_column(String(16))
    review_text: Mapped[str] = mapped_column(Text)
    lineage: Mapped[str] = mapped_column(String(32), default="SYNTHETIC")


class PersonaRecord(Base):
    __tablename__ = "personas"

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class PipelineRun(Base):
    """History of orchestrator runs (local + mirrored to Supabase)."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40))


class PipelineMeta(Base):
    __tablename__ = "pipeline_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


def _ensure_sqlite_directory(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    raw_path = url.removeprefix("sqlite:///")
    if raw_path in {":memory:", ""} or raw_path.startswith("file:"):
        return
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


def get_engine(url: str | None = None) -> Engine:
    database_url = url or DATABASE_URL
    _ensure_sqlite_directory(database_url)
    return create_engine(database_url, future=True)


def get_session_factory(engine: Engine | None = None):
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False, future=True)


def init_db(engine: Engine | None = None) -> Engine:
    engine = engine or get_engine()
    Base.metadata.create_all(engine)
    return engine


def default_warehouse_path() -> Path:
    return DATA_DIR / "processed" / "warehouse.db"
