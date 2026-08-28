"""Supabase PostgREST store for Personas and pipeline runs (cloud warehouse)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

from config.settings import (
    SUPABASE_ENABLED,
    SUPABASE_SERVICE_KEY,
    SUPABASE_STRICT,
    SUPABASE_URL,
)
from src.persona.schema import Persona

logger = logging.getLogger(__name__)

_PAGE_SIZE = 1000
_TIMEOUT = 60


def is_configured() -> bool:
    return bool(SUPABASE_ENABLED and SUPABASE_URL and SUPABASE_SERVICE_KEY)


def _headers(*, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request(
    method: str,
    path: str,
    *,
    body: Any = None,
    prefer: str | None = None,
    query: str = "",
    timeout: int = _TIMEOUT,
) -> Any:
    if not is_configured():
        return None
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path.lstrip('/')}{query}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers=_headers(prefer=prefer),
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {"ok": True, "status": getattr(resp, "status", 200)}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error("Supabase HTTP %s %s: %s — %s", method, path, exc.code, detail)
        if SUPABASE_STRICT:
            raise RuntimeError(f"Supabase HTTP {exc.code}: {detail}") from exc
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Supabase request failed: %s", exc)
        if SUPABASE_STRICT:
            raise
        return None


def _ok(result: Any) -> bool:
    return result is not None or not SUPABASE_STRICT


def _flat_row(persona: Persona) -> dict[str, Any]:
    action = persona.recommended_action or {}
    return {
        "customer_id": persona.customer_id,
        "payload": persona.to_dict(),
        "churn_risk_score": persona.churn_risk_score,
        "contact_channel": persona.contact_channel or action.get("channel"),
        "ops_status": persona.ops_status or "none",
        "message_status": persona.message_status or "none",
        "recommended_action": action.get("action"),
        "retention_message": persona.retention_message,
        "agent_notes": persona.agent_notes,
        "contacted_at": persona.contacted_at,
        "updated_at": persona.updated_at,
    }


def upsert_persona(persona: Persona) -> bool:
    if not is_configured():
        return True
    result = _request(
        "POST",
        "personas",
        body=_flat_row(persona),
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return _ok(result)


def replace_all_personas(personas: list[Persona]) -> bool:
    if not is_configured():
        return True
    _request(
        "DELETE",
        "personas",
        query="?customer_id=not.is.null",
        prefer="return=minimal",
    )
    if not personas:
        return True
    for i in range(0, len(personas), 200):
        chunk = [_flat_row(p) for p in personas[i : i + 200]]
        result = _request(
            "POST",
            "personas",
            body=chunk,
            prefer="resolution=merge-duplicates,return=minimal",
            timeout=120,
        )
        if not _ok(result):
            return False
    return True


def insert_pipeline_run(row: dict[str, Any]) -> int | None:
    if not is_configured():
        return None
    # Drop local-only fields that Supabase may not accept if absent from schema
    body = {
        "customer_id": row["customer_id"],
        "status": row.get("status"),
        "action": row.get("action"),
        "message": row.get("message"),
        "justification": row.get("justification"),
        "score_before": row.get("score_before"),
        "score_after": row.get("score_after"),
        "operator": row.get("operator"),
        "created_at": row.get("created_at"),
    }
    result = _request(
        "POST",
        "pipeline_runs",
        body=body,
        prefer="return=representation",
    )
    if isinstance(result, list) and result:
        rid = result[0].get("id")
        return int(rid) if rid is not None else None
    if not _ok(result):
        return None
    return None


def fetch_persona_payload(customer_id: str) -> dict[str, Any] | None:
    if not is_configured():
        return None
    rows = _request(
        "GET",
        "personas",
        query=f"?customer_id=eq.{quote(customer_id, safe='')}&select=payload",
    )
    if isinstance(rows, list) and rows:
        return rows[0].get("payload")
    return None


def list_persona_payloads(*, limit: int | None = None) -> list[dict[str, Any]]:
    """Paginated fetch of all Persona payloads (PostgREST default page is 1000)."""
    if not is_configured():
        return []
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        page_limit = _PAGE_SIZE
        if limit is not None:
            remaining = limit - len(out)
            if remaining <= 0:
                break
            page_limit = min(_PAGE_SIZE, remaining)
        rows = _request(
            "GET",
            "personas",
            query=f"?select=payload&order=customer_id.asc&limit={page_limit}&offset={offset}",
            timeout=120,
        )
        if not isinstance(rows, list):
            break
        for row in rows:
            payload = row.get("payload")
            if isinstance(payload, dict):
                out.append(payload)
        if len(rows) < page_limit:
            break
        offset += page_limit
    return out


def list_persona_ids() -> list[str]:
    if not is_configured():
        return []
    out: list[str] = []
    offset = 0
    while True:
        rows = _request(
            "GET",
            "personas",
            query=(
                f"?select=customer_id&order=customer_id.asc"
                f"&limit={_PAGE_SIZE}&offset={offset}"
            ),
            timeout=120,
        )
        if not isinstance(rows, list):
            break
        out.extend(str(r["customer_id"]) for r in rows if r.get("customer_id"))
        if len(rows) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return out


def list_pipeline_runs(
    customer_id: str | None = None,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if not is_configured():
        return []
    query = f"?select=*&order=created_at.desc&limit={int(limit)}"
    if customer_id:
        query = (
            f"?customer_id=eq.{quote(customer_id, safe='')}"
            f"&select=*&order=created_at.desc&limit={int(limit)}"
        )
    rows = _request("GET", "pipeline_runs", query=query)
    if not isinstance(rows, list):
        return []
    return rows
