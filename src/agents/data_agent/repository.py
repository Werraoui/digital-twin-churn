"""Read/write access to the Data Agent warehouse. Other agents should use this.

Persona / pipeline_runs backend is controlled by PERSONA_BACKEND:
  - supabase: cloud primary (optional LOCAL_MIRROR to SQLite)
  - local: SQLite only
  - dual: write both; read from PERSONA_READ_FROM
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from config.settings import LOCAL_MIRROR, PERSONA_BACKEND, PERSONA_READ_FROM
from src.agents.data_agent.warehouse import (
    Customer,
    PersonaRecord,
    PipelineMeta,
    PipelineRun,
    RetailRFM,
    SyntheticEvent,
    SyntheticReview,
    get_session_factory,
    init_db,
)
from src.integrations import supabase_store
from src.persona.ops import utc_now_iso
from src.persona.schema import Persona


class CustomerNotFoundError(KeyError):
    pass


def _session(engine: Engine | None = None) -> Session:
    init_db(engine)
    return get_session_factory(engine)()


def _use_cloud_read(engine: Engine | None) -> bool:
    if engine is not None:
        return False
    return PERSONA_READ_FROM == "supabase" and supabase_store.is_configured()


def _write_cloud(engine: Engine | None = None) -> bool:
    # Explicit SQLAlchemy engine ⇒ local/test path only (never touch cloud).
    if engine is not None:
        return False
    return PERSONA_BACKEND in {"supabase", "dual"} and supabase_store.is_configured()


def _write_local(engine: Engine | None = None) -> bool:
    if engine is not None:
        return True
    if PERSONA_BACKEND == "local":
        return True
    if PERSONA_BACKEND == "dual":
        return True
    if PERSONA_BACKEND == "supabase":
        return LOCAL_MIRROR
    return True


def replace_customers(rows: list[dict], engine: Engine | None = None) -> int:
    with _session(engine) as session:
        session.execute(delete(Customer))
        session.add_all([Customer(**row) for row in rows])
        session.commit()
        return len(rows)


def replace_retail_rfm(rows: list[dict], engine: Engine | None = None) -> int:
    with _session(engine) as session:
        session.execute(delete(RetailRFM))
        session.add_all([RetailRFM(**row) for row in rows])
        session.commit()
        return len(rows)


def replace_synthetic_events(rows: list[dict], engine: Engine | None = None) -> int:
    with _session(engine) as session:
        session.execute(delete(SyntheticEvent))
        session.add_all([SyntheticEvent(**row) for row in rows])
        session.commit()
        return len(rows)


def replace_synthetic_reviews(rows: list[dict], engine: Engine | None = None) -> int:
    with _session(engine) as session:
        session.execute(delete(SyntheticReview))
        session.add_all([SyntheticReview(**row) for row in rows])
        session.commit()
        return len(rows)


def _save_local(persona: Persona, engine: Engine | None = None) -> None:
    with _session(engine) as session:
        session.merge(
            PersonaRecord(customer_id=persona.customer_id, payload=persona.to_dict())
        )
        session.commit()


def replace_personas(personas: list[Persona], engine: Engine | None = None) -> int:
    stamped = []
    now = utc_now_iso()
    for persona in personas:
        if not persona.updated_at:
            persona.updated_at = now
        stamped.append(persona)

    if _write_cloud(engine):
        supabase_store.replace_all_personas(stamped)

    if _write_local(engine):
        with _session(engine) as session:
            session.execute(delete(PersonaRecord))
            session.add_all(
                [
                    PersonaRecord(customer_id=p.customer_id, payload=p.to_dict())
                    for p in stamped
                ]
            )
            session.commit()
    return len(stamped)


def save_persona(persona: Persona, engine: Engine | None = None) -> None:
    """Persist one Persona to the configured backend(s)."""
    if not persona.updated_at:
        persona.updated_at = utc_now_iso()

    if _write_cloud(engine):
        ok = supabase_store.upsert_persona(persona)
        if not ok and PERSONA_BACKEND == "supabase":
            raise RuntimeError(f"Supabase upsert failed for {persona.customer_id}")

    if _write_local(engine):
        _save_local(persona, engine)


def record_pipeline_run(row: dict[str, Any], engine: Engine | None = None) -> int:
    """Persist orchestrator history to cloud and/or local."""
    payload = {
        "customer_id": row["customer_id"],
        "status": row.get("status"),
        "action": row.get("action"),
        "message": row.get("message"),
        "justification": row.get("justification"),
        "score_before": row.get("score_before"),
        "score_after": row.get("score_after"),
        "operator": row.get("operator"),
        "created_at": row.get("created_at") or utc_now_iso(),
    }

    run_id = 0
    if _write_cloud(engine):
        cloud_id = supabase_store.insert_pipeline_run(payload)
        if cloud_id is not None:
            run_id = cloud_id

    if _write_local(engine):
        with _session(engine) as session:
            run = PipelineRun(**payload)
            session.add(run)
            session.commit()
            run_id = int(run.id)
    return run_id


def list_pipeline_runs(
    customer_id: str | None = None,
    *,
    limit: int = 100,
    engine: Engine | None = None,
) -> list[dict[str, Any]]:
    if _use_cloud_read(engine):
        rows = supabase_store.list_pipeline_runs(customer_id, limit=limit)
        return [
            {
                "id": row.get("id"),
                "customer_id": row.get("customer_id"),
                "status": row.get("status"),
                "action": row.get("action"),
                "message": row.get("message"),
                "justification": row.get("justification"),
                "score_before": row.get("score_before"),
                "score_after": row.get("score_after"),
                "operator": row.get("operator"),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    with _session(engine) as session:
        stmt = select(PipelineRun).order_by(desc(PipelineRun.id)).limit(limit)
        if customer_id:
            stmt = (
                select(PipelineRun)
                .where(PipelineRun.customer_id == customer_id)
                .order_by(desc(PipelineRun.id))
                .limit(limit)
            )
        rows = session.scalars(stmt).all()
        return [
            {
                "id": row.id,
                "customer_id": row.customer_id,
                "status": row.status,
                "action": row.action,
                "message": row.message,
                "justification": row.justification,
                "score_before": row.score_before,
                "score_after": row.score_after,
                "operator": row.operator,
                "created_at": row.created_at,
            }
            for row in rows
        ]


def upsert_meta(key: str, value: dict, engine: Engine | None = None) -> None:
    with _session(engine) as session:
        session.merge(PipelineMeta(key=key, value=value))
        session.commit()


def get_customer(customer_id: str, engine: Engine | None = None) -> dict:
    with _session(engine) as session:
        row = session.get(Customer, customer_id)
        if row is None:
            raise CustomerNotFoundError(customer_id)
        return {column.key: getattr(row, column.key) for column in Customer.__table__.columns}


def list_customers(limit: int = 100, offset: int = 0, engine: Engine | None = None) -> list[dict]:
    with _session(engine) as session:
        rows = session.scalars(
            select(Customer).order_by(Customer.customer_id).offset(offset).limit(limit)
        ).all()
        return [
            {column.key: getattr(row, column.key) for column in Customer.__table__.columns}
            for row in rows
        ]


def get_persona(customer_id: str, engine: Engine | None = None) -> Persona:
    if _use_cloud_read(engine):
        payload = supabase_store.fetch_persona_payload(customer_id)
        if payload is None:
            raise CustomerNotFoundError(customer_id)
        return Persona.from_dict(payload)

    with _session(engine) as session:
        row = session.get(PersonaRecord, customer_id)
        if row is None:
            raise CustomerNotFoundError(customer_id)
        return Persona.from_dict(row.payload)


def list_personas(engine: Engine | None = None) -> list[Persona]:
    if _use_cloud_read(engine):
        payloads = supabase_store.list_persona_payloads()
        return [Persona.from_dict(payload) for payload in payloads]

    with _session(engine) as session:
        rows = session.scalars(select(PersonaRecord)).all()
        return [Persona.from_dict(row.payload) for row in rows]


def list_persona_ids(engine: Engine | None = None) -> list[str]:
    if _use_cloud_read(engine):
        return supabase_store.list_persona_ids()

    with _session(engine) as session:
        return list(
            session.scalars(
                select(PersonaRecord.customer_id).order_by(PersonaRecord.customer_id)
            )
        )


def get_rfm_distributions(engine: Engine | None = None) -> dict:
    with _session(engine) as session:
        row = session.get(PipelineMeta, "rfm_stats")
        if row is None:
            raise CustomerNotFoundError("rfm_stats")
        return dict(row.value)


def get_retail_rfm(engine: Engine | None = None) -> list[dict]:
    with _session(engine) as session:
        rows = session.scalars(select(RetailRFM)).all()
        return [
            {column.key: getattr(row, column.key) for column in RetailRFM.__table__.columns}
            for row in rows
        ]


def sync_personas_from_supabase(engine: Engine | None = None) -> int:
    """Pull Persona payloads from Supabase into the local SQLite warehouse."""
    payloads = supabase_store.list_persona_payloads()
    if not payloads:
        return 0
    personas = [Persona.from_dict(payload) for payload in payloads]
    with _session(engine) as session:
        for persona in personas:
            session.merge(
                PersonaRecord(customer_id=persona.customer_id, payload=persona.to_dict())
            )
        session.commit()
    return len(personas)


def push_personas_to_supabase(engine: Engine | None = None) -> int:
    """Push all local SQLite Personas to Supabase (migration helper)."""
    with _session(engine) as session:
        rows = session.scalars(select(PersonaRecord)).all()
        personas = [Persona.from_dict(row.payload) for row in rows]
    if not personas:
        return 0
    supabase_store.replace_all_personas(personas)
    return len(personas)
