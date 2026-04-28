"""CRUD helpers for customers, calls, and bookings."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from auto_agent.services.database import Booking, Call, Customer


def find_customer_by_phone(session: Session, phone_e164: str | None) -> Customer | None:
    if not phone_e164:
        return None
    return session.query(Customer).filter(Customer.phone_e164 == phone_e164).first()


def find_customer_by_email(session: Session, email: str | None) -> Customer | None:
    if not email:
        return None
    return session.query(Customer).filter(Customer.email == email).first()


def upsert_customer(
    session: Session,
    *,
    name: str | None,
    phone_e164: str | None,
    email: str | None,
    vehicle: str | None,
) -> Customer:
    cust = find_customer_by_phone(session, phone_e164) if phone_e164 else None
    if cust is None and email:
        cust = find_customer_by_email(session, email)
    if cust is None:
        cust = Customer(
            phone_e164=phone_e164,
            name=name,
            email=email,
            vehicle=vehicle,
        )
        session.add(cust)
        session.flush()
    else:
        if name:
            cust.name = name
        if email:
            cust.email = email
        if vehicle:
            cust.vehicle = vehicle
        if phone_e164 and not cust.phone_e164:
            cust.phone_e164 = phone_e164
        cust.updated_at = datetime.utcnow()
    session.flush()
    return cust


def ensure_open_call(
    session: Session,
    *,
    external_call_id: str | None,
    customer_id: int | None,
    payload_snippet: dict[str, Any] | None = None,
) -> Call:
    if external_call_id:
        existing = session.query(Call).filter(Call.external_call_id == external_call_id).first()
        if existing:
            if customer_id and existing.customer_id is None:
                existing.customer_id = customer_id
            if payload_snippet is not None:
                existing.raw_summary_json = json.dumps(payload_snippet)[:8000]
            session.flush()
            return existing
    call = Call(
        external_call_id=external_call_id,
        customer_id=customer_id,
        status="open",
        raw_summary_json=json.dumps(payload_snippet)[:8000] if payload_snippet else None,
    )
    session.add(call)
    session.flush()
    return call


def close_call(session: Session, call: Call, status: str = "completed") -> None:
    call.status = status
    call.ended_at = datetime.utcnow()
    session.flush()


def create_booking(
    session: Session,
    *,
    call_id: int | None,
    customer_id: int | None,
    symptom: str | None,
    date_text: str | None,
    time_text: str | None,
    estimate_text: str | None,
    calendar_event_id: str | None = None,
) -> Booking:
    b = Booking(
        call_id=call_id,
        customer_id=customer_id,
        symptom=symptom,
        requested_date_text=date_text,
        requested_time_text=time_text,
        estimate_text=estimate_text,
        calendar_event_id=calendar_event_id,
    )
    session.add(b)
    session.flush()
    return b
