"""Free-first LLM backends for the Generator Agent.

Providers (set LLM_PROVIDER or auto-detect from keys):
  - groq     → free tier  https://console.groq.com
  - gemini   → free tier  https://aistudio.google.com/apikey
  - anthropic → paid/optional Claude
  - template → no API (deterministic fallback)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Optional

from config.settings import (
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
)

logger = logging.getLogger(__name__)

# Sensible free defaults
_GROQ_MODEL = "llama-3.1-8b-instant"
_GEMINI_MODEL = "gemini-2.0-flash"
_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


def resolve_provider(explicit: str | None = None) -> str:
    """Pick a provider: explicit > LLM_PROVIDER > first available free key > template."""
    if explicit:
        return explicit.lower().strip()
    if LLM_PROVIDER:
        return LLM_PROVIDER.lower().strip()
    if GROQ_API_KEY:
        return "groq"
    if GEMINI_API_KEY:
        return "gemini"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    return "template"


def resolve_model(provider: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if LLM_MODEL:
        return LLM_MODEL
    if provider == "groq":
        return _GROQ_MODEL
    if provider == "gemini":
        return _GEMINI_MODEL
    if provider == "anthropic":
        return _ANTHROPIC_MODEL
    return ""


def _http_json(url: str, payload: dict, *, headers: dict | None = None, timeout: int = 60) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from LLM API: {detail[:500]}") from exc


def call_groq(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    key = api_key or GROQ_API_KEY
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set (free key: https://console.groq.com)")
    data = _http_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {
            "model": resolve_model("groq", model),
            "temperature": 0.4,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    text = data["choices"][0]["message"]["content"].strip()
    if not text:
        raise RuntimeError("empty response from Groq")
    return text


def call_gemini(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    key = api_key or GEMINI_API_KEY
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set (free key: https://aistudio.google.com/apikey)"
        )
    model_name = resolve_model("gemini", model)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={key}"
    )
    data = _http_json(
        url,
        {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 500},
        },
    )
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"empty Gemini response: {data}")
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "\n".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError("empty text from Gemini")
    return text


def call_anthropic(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    key = api_key or ANTHROPIC_API_KEY
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=resolve_model("anthropic", model),
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    message = "\n".join(parts).strip()
    if not message:
        raise RuntimeError("empty response from Claude")
    return message


def generate_with_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """Dispatch to Groq / Gemini / Anthropic."""
    name = resolve_provider(provider)
    if name == "template":
        raise RuntimeError("no LLM provider configured")
    if name == "groq":
        return call_groq(system_prompt, user_prompt, api_key=api_key, model=model)
    if name == "gemini":
        return call_gemini(system_prompt, user_prompt, api_key=api_key, model=model)
    if name == "anthropic":
        return call_anthropic(system_prompt, user_prompt, api_key=api_key, model=model)
    raise ValueError(f"unknown LLM provider: {name!r} (use groq|gemini|anthropic|template)")
