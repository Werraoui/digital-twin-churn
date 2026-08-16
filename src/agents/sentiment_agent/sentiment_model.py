"""
Sentiment Agent analysis.

Step 1: polarity (negative / neutral / positive).
Step 2: complaint topics from review text (keyword match on known ticket issues).
Step 3: emotions from polarity + topics (rules, no extra model).
Step 4: satisfaction_score on a 1-5 CSAT scale.
Does not read Churn.
The Hugging Face pipeline is loaded lazily (not at import time).
"""

from __future__ import annotations

from typing import Any

from src.persona.schema import Persona

_LABEL_MAP = {
    "negative": "negative",
    "neutral": "neutral",
    "positive": "positive",
    "neg": "negative",
    "neu": "neutral",
    "pos": "positive",
    "label_0": "negative",
    "label_1": "neutral",
    "label_2": "positive",
}

_pipeline: Any = None

# Phrases from the real support-ticket file (10 unique issue_description values).
# Topics use the dataset category names. Matching is on the review text, not a join.
_TOPIC_PATTERNS = (
    ("payment was deducted", "Payment Problem"),
    ("transaction shows failed", "Payment Problem"),
    ("discrepancy in my billing", "Payment Problem"),
    ("request a refund", "Refund Request"),
    ("subscription was cancelled", "Subscription Cancellation"),
    ("bug in the latest update", "Bug Report"),
    ("application crashes", "Bug Report"),
    ("not syncing data", "Data Sync Issue"),
    ("two-factor authentication", "Security Concern"),
    ("unable to access my account", "Login Issue"),
    ("slow performance", "Performance Issue"),
)

_TOPIC_EMOTIONS = {
    "Payment Problem": ["frustration", "anger"],
    "Refund Request": ["frustration", "anger"],
    "Subscription Cancellation": ["disappointment"],
    "Security Concern": ["anxiety"],
    "Login Issue": ["anxiety"],
    "Bug Report": ["frustration"],
    "Performance Issue": ["frustration"],
    "Data Sync Issue": ["frustration"],
    "Feature Request": ["calm"],
    "Account Suspension": ["anger"],
}


def _get_pipeline():
    """Load the classifier once, on first use."""
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline

        _pipeline = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
        )
    return _pipeline


def _normalize_label(label: str) -> str:
    key = str(label).strip().lower()
    if key not in _LABEL_MAP:
        raise ValueError(f"Unexpected sentiment label: {label!r}")
    return _LABEL_MAP[key]


def extract_complaint_topics(text: str) -> list[str]:
    """
    Map review text to ticket categories by phrase match.

    This is DERIVED from the synthetic review string, not a row join
    to a support ticket.
    """
    if text is None or not str(text).strip():
        return []

    haystack = str(text).lower()
    topics: list[str] = []
    for phrase, topic in _TOPIC_PATTERNS:
        if phrase in haystack and topic not in topics:
            topics.append(topic)
    return topics


def infer_emotions(sentiment: str, topics: list[str] | None = None) -> list[str]:
    """
    DERIVED emotions. Polarity wins; topics only refine a negative review.
    Does not use Churn.
    """
    if sentiment == "positive":
        return ["satisfaction"]
    if sentiment == "neutral":
        return ["calm"]
    if sentiment != "negative":
        raise ValueError(f"Unexpected sentiment for emotions: {sentiment!r}")

    emotions: list[str] = []
    for topic in topics or []:
        for emotion in _TOPIC_EMOTIONS.get(topic, []):
            if emotion not in emotions:
                emotions.append(emotion)
    return emotions or ["frustration"]


def infer_satisfaction_score(sentiment: str, confidence: float) -> float:
    """
    DERIVED CSAT-like score in [1, 5], aligned with ticket satisfaction_score.

    Uses classifier polarity and confidence only. Does not use Churn.
    """
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be in [0, 1], got {confidence}")

    if sentiment == "positive":
        score = 3.0 + 2.0 * confidence
    elif sentiment == "neutral":
        score = 3.0
    elif sentiment == "negative":
        score = 3.0 - 2.0 * confidence
    else:
        raise ValueError(f"Unexpected sentiment for satisfaction: {sentiment!r}")

    return round(min(5.0, max(1.0, score)), 2)


def classify_sentiment(text: str) -> dict:
    """
    Classify a review string.

    Returns:
        {"sentiment": "negative"|"neutral"|"positive", "confidence": float}
    """
    if text is None or not str(text).strip():
        raise ValueError("classify_sentiment requires non-empty text")

    result = _get_pipeline()(str(text), truncation=True)[0]
    return {
        "sentiment": _normalize_label(result["label"]),
        "confidence": float(result["score"]),
    }


def analyze(persona: Persona) -> dict:
    """
    Sentiment Agent entry point used by the orchestrator.

    Fills sentiment + confidence (step 1), complaint_topics (step 2),
    emotions (step 3), and satisfaction_score (step 4).
    """
    text = persona.raw_review_text
    classified = classify_sentiment(text)
    topics = extract_complaint_topics(text)
    sentiment = classified["sentiment"]
    confidence = classified["confidence"]
    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "emotions": infer_emotions(sentiment, topics),
        "complaint_topics": topics,
        "satisfaction_score": infer_satisfaction_score(sentiment, confidence),
    }
