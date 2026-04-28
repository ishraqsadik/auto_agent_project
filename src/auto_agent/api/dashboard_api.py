"""Read-only JSON endpoints for Streamlit Cloud (same host as SQLite on Render)."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select

from auto_agent.services.database import Booking, Call, Customer, get_session_factory

router = APIRouter(prefix="/api", tags=["dashboard"])


def _require_dashboard_key(x_dashboard_key: str | None) -> None:
    expected = os.getenv("STREAMLIT_DASHBOARD_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="STREAMLIT_DASHBOARD_KEY is not set on the server")
    if not x_dashboard_key or x_dashboard_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Dashboard-Key")


def _serialize_call(row: Call) -> dict:
    return {
        "id": row.id,
        "external_call_id": row.external_call_id,
        "customer_id": row.customer_id,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "ended_at": row.ended_at.isoformat() if row.ended_at else None,
    }


def _serialize_customer(row: Customer) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "vehicle": row.vehicle,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _serialize_booking(row: Booking) -> dict:
    return {
        "id": row.id,
        "call_id": row.call_id,
        "customer_id": row.customer_id,
        "symptom": row.symptom,
        "requested_date_text": row.requested_date_text,
        "requested_time_text": row.requested_time_text,
        "estimate_text": row.estimate_text,
        "calendar_event_id": row.calendar_event_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/calls")
async def api_calls(x_dashboard_key: str | None = Header(None, alias="X-Dashboard-Key")):
    _require_dashboard_key(x_dashboard_key)
    Session = get_session_factory()
    with Session() as session:
        rows = session.scalars(select(Call).order_by(Call.id.desc()).limit(50)).all()
        return [_serialize_call(r) for r in rows]


@router.get("/customers")
async def api_customers(x_dashboard_key: str | None = Header(None, alias="X-Dashboard-Key")):
    _require_dashboard_key(x_dashboard_key)
    Session = get_session_factory()
    with Session() as session:
        rows = session.scalars(select(Customer).order_by(Customer.id.desc()).limit(100)).all()
        return [_serialize_customer(r) for r in rows]


@router.get("/bookings")
async def api_bookings(x_dashboard_key: str | None = Header(None, alias="X-Dashboard-Key")):
    _require_dashboard_key(x_dashboard_key)
    Session = get_session_factory()
    with Session() as session:
        rows = session.scalars(select(Booking).order_by(Booking.id.desc()).limit(100)).all()
        return [_serialize_booking(r) for r in rows]


@router.get("/agent_logs")
async def api_agent_logs(x_dashboard_key: str | None = Header(None, alias="X-Dashboard-Key")):
    _require_dashboard_key(x_dashboard_key)
    # Same cwd as uvicorn: repo root on Render
    path = Path("agent_logs.txt")
    if not path.exists():
        return {"text": ""}
    return {"text": path.read_text(encoding="utf-8", errors="replace")[-120_000:]}
