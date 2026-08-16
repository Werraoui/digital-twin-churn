"""Read/write access to the Data Agent warehouse. Other agents should use this."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.agents.data_agent.warehouse import (
    Customer,
    PersonaRecord,
    PipelineMeta,
    RetailRFM,
    SyntheticEvent,
    SyntheticReview,
    get_session_factory,
    init_db,
)
from src.persona.schema import Persona


class CustomerNotFoundError(KeyError):
    pass


def _session(engine: Engine | None = None) -> Session:
    init_db(engine)
    return get_session_factory(engine)()


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


def replace_personas(personas: list[Persona], engine: Engine | None = None) -> int:
    with _session(engine) as session:
        session.execute(delete(PersonaRecord))
        session.add_all([
            PersonaRecord(customer_id=persona.customer_id, payload=persona.to_dict())
            for persona in personas
        ])
        session.commit()
        return len(personas)


def save_persona(persona: Persona, engine: Engine | None = None) -> None:
    """Insert or replace one Persona without wiping the table."""
    with _session(engine) as session:
        session.merge(
            PersonaRecord(customer_id=persona.customer_id, payload=persona.to_dict())
        )
        session.commit()


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
    with _session(engine) as session:
        row = session.get(PersonaRecord, customer_id)
        if row is None:
            raise CustomerNotFoundError(customer_id)
        return Persona.from_dict(row.payload)


def list_personas(engine: Engine | None = None) -> list[Persona]:
    with _session(engine) as session:
        rows = session.scalars(select(PersonaRecord)).all()
        return [Persona.from_dict(row.payload) for row in rows]


def list_persona_ids(engine: Engine | None = None) -> list[str]:
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
