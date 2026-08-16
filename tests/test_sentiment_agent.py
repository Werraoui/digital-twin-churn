from src.persona.schema import Persona
from src.agents.sentiment_agent.persona_updater import update_persona
from src.agents.sentiment_agent.sentiment_model import (
    analyze,
    classify_sentiment,
    extract_complaint_topics,
    infer_emotions,
    infer_satisfaction_score,
)


def _persona(text: str | None) -> Persona:
    return Persona(
        customer_id="7590-VHVEG",
        demographics={},
        services={},
        contract={},
        billing={},
        raw_review_text=text,
    )


def test_importing_sentiment_model_does_not_create_pipeline():
    import src.agents.sentiment_agent.sentiment_model as module

    assert module._pipeline is None


def test_classify_sentiment_normalizes_labels(monkeypatch):
    import src.agents.sentiment_agent.sentiment_model as module

    monkeypatch.setattr(
        module,
        "_get_pipeline",
        lambda: lambda *_args, **_kwargs: [{"label": "LABEL_0", "score": 0.91}],
    )
    result = classify_sentiment("The payment failed.")
    assert result == {"sentiment": "negative", "confidence": 0.91}


def test_analyze_uses_persona_review_text_only(monkeypatch):
    import src.agents.sentiment_agent.sentiment_model as module

    monkeypatch.setattr(
        module,
        "_get_pipeline",
        lambda: lambda *_args, **_kwargs: [{"label": "positive", "score": 0.77}],
    )
    persona = _persona("I found a bug in the latest update affecting report generation.")
    persona.review_tone = "negative"
    analysis = analyze(persona)

    assert analysis["sentiment"] == "positive"
    assert analysis["confidence"] == 0.77
    assert analysis["emotions"] == ["satisfaction"]
    assert analysis["complaint_topics"] == ["Bug Report"]
    assert analysis["satisfaction_score"] == 4.54
    assert "Churn" not in analysis


def test_classify_sentiment_rejects_empty_text():
    import pytest

    with pytest.raises(ValueError, match="non-empty text"):
        classify_sentiment("   ")


def test_extract_complaint_topics_from_known_ticket_phrases():
    assert extract_complaint_topics(
        "The payment was deducted from my bank account but the transaction shows failed."
    ) == ["Payment Problem"]
    assert extract_complaint_topics(
        "I would like to request a refund for the recent charge."
    ) == ["Refund Request"]
    assert extract_complaint_topics(
        "I am experiencing very slow performance while using the dashboard."
    ) == ["Performance Issue"]
    assert extract_complaint_topics("hello there") == []
    assert extract_complaint_topics("   ") == []


def test_infer_emotions_polarity_wins_then_topics_refine_negatives():
    assert infer_emotions("positive", ["Bug Report"]) == ["satisfaction"]
    assert infer_emotions("neutral", ["Payment Problem"]) == ["calm"]
    assert infer_emotions("negative", ["Payment Problem"]) == ["frustration", "anger"]
    assert infer_emotions("negative", ["Login Issue"]) == ["anxiety"]
    assert infer_emotions("negative", []) == ["frustration"]


def test_infer_satisfaction_score_maps_polarity_to_csat_scale():
    assert infer_satisfaction_score("positive", 0.77) == 4.54
    assert infer_satisfaction_score("positive", 1.0) == 5.0
    assert infer_satisfaction_score("neutral", 0.99) == 3.0
    assert infer_satisfaction_score("negative", 0.91) == 1.18
    assert infer_satisfaction_score("negative", 1.0) == 1.0


def test_update_persona_writes_derived_fields_and_ignores_churn():
    persona = _persona("billing issue")
    persona.lineage = {"raw_review_text": "SYNTHETIC"}

    updated = update_persona(
        persona,
        {
            "sentiment": "negative",
            "confidence": 0.91,
            "emotions": ["frustration", "anger"],
            "complaint_topics": ["Payment Problem"],
            "satisfaction_score": 1.18,
            "Churn": "Yes",
        },
    )

    assert updated is persona
    assert updated.sentiment == "negative"
    assert updated.sentiment_confidence == 0.91
    assert updated.emotions == ["frustration", "anger"]
    assert updated.complaint_topics == ["Payment Problem"]
    assert updated.satisfaction_score == 1.18
    assert updated.is_enriched()
    assert updated.lineage["raw_review_text"] == "SYNTHETIC"
    assert updated.lineage["sentiment"] == "DERIVED"
    assert updated.lineage["satisfaction_score"] == "DERIVED"
    assert "Churn" not in updated.to_dict()
    assert "churn" not in updated.to_dict()


def test_enrich_stored_persona_persists_derived_fields(monkeypatch):
    from sqlalchemy import create_engine

    from src.agents.data_agent.repository import get_persona, replace_personas
    from src.agents.data_agent.warehouse import init_db
    from src.agents.sentiment_agent.run import enrich_stored_persona
    import src.agents.sentiment_agent.sentiment_model as module

    monkeypatch.setattr(
        module,
        "_get_pipeline",
        lambda: lambda *_args, **_kwargs: [{"label": "negative", "score": 0.91}],
    )

    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    stored = _persona(
        "The payment was deducted from my bank account but the transaction shows failed."
    )
    stored.lineage = {"raw_review_text": "SYNTHETIC"}
    replace_personas([stored], engine=engine)

    enriched = enrich_stored_persona("7590-VHVEG", engine=engine)
    reloaded = get_persona("7590-VHVEG", engine=engine)

    assert enriched.is_enriched()
    assert reloaded.sentiment == "negative"
    assert reloaded.sentiment_confidence == 0.91
    assert reloaded.complaint_topics == ["Payment Problem"]
    assert reloaded.satisfaction_score == 1.18
    assert reloaded.lineage["sentiment"] == "DERIVED"
    assert reloaded.lineage["raw_review_text"] == "SYNTHETIC"
    assert "Churn" not in reloaded.to_dict()


def test_enrich_all_personas_enriches_every_stored_persona(monkeypatch):
    from sqlalchemy import create_engine

    from src.agents.data_agent.repository import get_persona, replace_personas
    from src.agents.data_agent.warehouse import init_db
    from src.agents.sentiment_agent.run import enrich_all_personas
    import src.agents.sentiment_agent.sentiment_model as module

    monkeypatch.setattr(
        module,
        "_get_pipeline",
        lambda: lambda *_args, **_kwargs: [{"label": "negative", "score": 0.91}],
    )

    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    first = _persona(
        "The payment was deducted from my bank account but the transaction shows failed."
    )
    first.customer_id = "0001-AAAAA"
    second = _persona(
        "I am experiencing very slow performance while using the dashboard."
    )
    second.customer_id = "0002-BBBBB"
    empty = _persona("   ")
    empty.customer_id = "0003-CCCCC"
    already = _persona("already done")
    already.customer_id = "0004-DDDDD"
    already.sentiment = "positive"
    replace_personas([first, second, empty, already], engine=engine)

    summary = enrich_all_personas(engine=engine, skip_enriched=True)

    assert summary["n_total"] == 4
    assert summary["n_ok"] == 2
    assert summary["n_skipped"] == 2
    assert summary["n_failed"] == 0
    assert get_persona("0001-AAAAA", engine=engine).is_enriched()
    assert get_persona("0002-BBBBB", engine=engine).complaint_topics == ["Performance Issue"]
    assert get_persona("0003-CCCCC", engine=engine).sentiment is None
    assert get_persona("0004-DDDDD", engine=engine).sentiment == "positive"
