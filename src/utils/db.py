"""Database engine used by the Data Agent warehouse."""

from src.agents.data_agent.warehouse import get_engine, init_db

engine = get_engine()


def get_db_engine():
    return get_engine()


def initialize_warehouse():
    return init_db(engine)
