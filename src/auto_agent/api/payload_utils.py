"""Extract stable identifiers from Vapi webhook payloads (best-effort)."""

from __future__ import annotations

from typing import Any


def extract_external_call_id(payload: dict[str, Any]) -> str | None:
    for path in (
        ("call", "id"),
        ("message", "call", "id"),
        ("callId",),
        ("message", "callId"),
    ):
        cur: Any = payload
        for key in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(key)
        if isinstance(cur, str) and cur:
            return cur
    return None


def extract_caller_phone(payload: dict[str, Any]) -> str | None:
    for path in (
        ("call", "customer", "number"),
        ("message", "call", "customer", "number"),
        ("customer", "number"),
    ):
        cur: Any = payload
        for key in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(key)
        if isinstance(cur, str) and cur:
            return cur
    return None


def payload_snippet(payload: dict[str, Any]) -> dict[str, Any]:
    """Small JSON-safe summary for DB storage."""
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    return {
        "call_id": extract_external_call_id(payload),
        "phone": extract_caller_phone(payload),
        "message_type": msg.get("type"),
    }
