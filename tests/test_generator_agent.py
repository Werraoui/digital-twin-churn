from pathlib import Path
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine

from src.agents.data_agent.repository import get_persona, replace_personas
from src.agents.data_agent.warehouse import init_db
from src.agents.generator_agent.corpus import ACTION_LABELS, build_ticket_documents
from src.agents.generator_agent.message_generator import generate_retention_message
from src.agents.generator_agent.retriever import retrieve_context
from src.agents.generator_agent.run import generate_for_persona, generate_stored_persona
from src.persona.schema import Persona


def _persona(**overrides) -> Persona:
    data = {
        "customer_id": "7590-VHVEG",
        "demographics": {"gender": "Female"},
        "services": {"internet_service": "DSL", "online_security": "No"},
        "contract": {
            "type": "Month-to-month",
            "payment_method": "Electronic check",
            "paperless_billing": "Yes",
            "tenure": 1,
        },
        "billing": {"monthly_charges": 29.85, "total_charges": 29.85},
        "raw_review_text": (
            "The payment was deducted from my bank account but the transaction shows failed."
        ),
        "sentiment": "negative",
        "sentiment_confidence": 0.9,
        "emotions": ["frustration"],
        "complaint_topics": ["Payment Problem"],
        "churn_risk_score": 0.81,
        "recommended_action": {
            "action": "disable_paperless_billing",
            "channel": "call",
            "delta": 0.06,
            "cost": 0.3,
        },
        "contact_channel": "call",
    }
    data.update(overrides)
    return Persona(**data)


def test_resolve_provider_prefers_groq(monkeypatch):
    from src.agents.generator_agent import llm as llm_mod

    monkeypatch.setattr(llm_mod, "GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr(llm_mod, "GEMINI_API_KEY", "gem_test")
    monkeypatch.setattr(llm_mod, "ANTHROPIC_API_KEY", "ant_test")
    monkeypatch.setattr(llm_mod, "LLM_PROVIDER", "")
    assert llm_mod.resolve_provider() == "groq"


def test_resolve_provider_explicit_template(monkeypatch):
    from src.agents.generator_agent import llm as llm_mod

    monkeypatch.setattr(llm_mod, "LLM_PROVIDER", "template")
    assert llm_mod.resolve_provider() == "template"


def test_build_ticket_documents_dedupes_unique_issues(tmp_path: Path):
    csv_path = tmp_path / "tickets.csv"
    pd.DataFrame(
        [
            {
                "ticket_id": 1,
                "category": "Payment Problem",
                "issue_description": "Payment failed.",
                "resolution_notes": "Refund issued.",
            },
            {
                "ticket_id": 2,
                "category": "Payment Problem",
                "issue_description": "Payment failed.",
                "resolution_notes": "Different note.",
            },
            {
                "ticket_id": 3,
                "category": "Bug Report",
                "issue_description": "App crashes.",
                "resolution_notes": "Patch deployed.",
            },
        ]
    ).to_csv(csv_path, index=False)
    docs = build_ticket_documents(path=csv_path)
    assert len(docs) == 2
    assert all("Customer issue:" in doc["text"] for doc in docs)
    assert "customerID" not in docs[0]["metadata"]


def test_retrieve_context_lexical_fallback():
    docs = [
        {
            "id": "1",
            "text": "Category: Payment Problem\nCustomer issue: payment failed\nResolution note: refund",
            "metadata": {},
        },
        {
            "id": "2",
            "text": "Category: Bug Report\nCustomer issue: app crashes\nResolution note: patch",
            "metadata": {},
        },
    ]
    hits = retrieve_context(
        "payment failed on my bill",
        top_k=1,
        use_chroma=False,
        documents=docs,
    )
    assert hits
    assert "payment" in hits[0].lower()


def test_generate_retention_message_template_call():
    message = generate_retention_message(
        _persona(),
        use_llm=False,
        retrieve=False,
        rag_snippets=["Category: Payment Problem\nCustomer issue: payment failed"],
    )
    assert "CALL SCRIPT" in message
    assert "7590-VHVEG" in message
    assert "paper" in message.lower() or "billing" in message.lower()


def test_generate_retention_message_template_email():
    persona = _persona(
        contact_channel="email",
        recommended_action={"action": "offer_two_year_contract", "channel": "email"},
    )
    message = generate_retention_message(
        persona,
        use_llm=False,
        retrieve=False,
        rag_snippets=["Category: Account Suspension\nCustomer issue: cancelled"],
    )
    assert "Subject:" in message
    assert "two-year" in message.lower() or "two year" in message.lower()


def test_generate_retention_message_requires_action():
    import pytest

    persona = _persona(recommended_action=None)
    with pytest.raises(ValueError, match="recommended_action"):
        generate_retention_message(persona, recommended_action=None, use_llm=False)


def test_action_labels_cover_simulation_actions():
    expected = (
        "offer_two_year_contract",
        "offer_one_year_contract",
        "add_online_security",
        "switch_to_autopay",
        "disable_paperless_billing",
    )
    for action in expected:
        assert action in ACTION_LABELS


def test_generate_stored_persona_persists_message():
    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    replace_personas([_persona()], engine=engine)

    with patch(
        "src.agents.generator_agent.run.retrieve_context",
        return_value=["Category: Payment Problem\nCustomer issue: payment failed"],
    ):
        updated, message = generate_stored_persona(
            "7590-VHVEG", engine=engine, use_llm=False
        )

    reloaded = get_persona("7590-VHVEG", engine=engine)
    assert updated.retention_message == message
    assert reloaded.retention_message
    assert reloaded.rag_context
    assert reloaded.lineage["retention_message"] == "DERIVED"
    assert "Churn" not in reloaded.to_dict()


def test_generate_for_persona_sets_lineage():
    with patch(
        "src.agents.generator_agent.run.retrieve_context",
        return_value=["Category: Payment Problem\nCustomer issue: payment failed"],
    ):
        persona, message = generate_for_persona(_persona(), use_llm=False)
    assert message
    assert persona.lineage["rag_context"] == "REAL"
    assert persona.retention_message == message
