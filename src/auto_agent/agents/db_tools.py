"""CrewAI tools for SQLite customer/call/booking records."""

from __future__ import annotations

import json

from crewai.tools import tool

from auto_agent.agents.tools import log_agent_action
from auto_agent.context import current_call_db_id, current_customer_db_id
from auto_agent.services.database import Booking, Call, Customer, get_session_factory
from auto_agent.services.repositories import create_booking, find_customer_by_phone, upsert_customer


@tool("Lookup Customer By Phone")
def lookup_customer_by_phone(phone_e164: str) -> str:
    """Find an existing customer by E.164 phone (e.g. +15551234567). Returns a short summary or not found."""
    log_agent_action("Database Specialist", f"Lookup customer by phone: {phone_e164}")
    Session = get_session_factory()
    with Session() as session:
        c = find_customer_by_phone(session, phone_e164.strip() or None)
        if not c:
            return "No existing customer record for this phone."
        current_customer_db_id.set(c.id)
        parts = [f"Found customer id {c.id}", f"name: {c.name or 'unknown'}"]
        if c.vehicle:
            parts.append(f"vehicle: {c.vehicle}")
        if c.email:
            parts.append(f"email: {c.email}")
        return "; ".join(parts)


@tool("Upsert Customer Record")
def upsert_customer_record(
    name: str,
    phone_e164: str,
    email: str,
    vehicle: str,
) -> str:
    """Create or update customer by phone/email."""
    log_agent_action("Database Specialist", f"Upsert customer: {name}, phone={phone_e164}")
    Session = get_session_factory()
    with Session() as session:
        c = upsert_customer(
            session,
            name=name or None,
            phone_e164=phone_e164.strip() or None,
            email=email.strip() or None,
            vehicle=vehicle.strip() or None,
        )
        session.commit()
        current_customer_db_id.set(c.id)
        return f"Customer saved with id {c.id}."


@tool("Save Booking Row")
def save_booking_row(symptom: str, date_text: str, time_text: str, estimate_summary: str) -> str:
    """Persist booking details linked to the current call/customer context."""
    log_agent_action("Database Specialist", "Saving booking row to SQLite.")
    call_id = current_call_db_id.get()
    cust_id = current_customer_db_id.get()
    Session = get_session_factory()
    with Session() as session:
        b = create_booking(
            session,
            call_id=call_id,
            customer_id=cust_id,
            symptom=symptom,
            date_text=date_text,
            time_text=time_text,
            estimate_text=estimate_summary,
        )
        session.commit()
        return f"Booking row {b.id} saved for call_id={call_id}, customer_id={cust_id}."


@tool("Append Call Note")
def append_call_note(note: str) -> str:
    """Append a short note to the current call's raw_summary_json (best-effort)."""
    call_id = current_call_db_id.get()
    if not call_id:
        return "No active call context."
    log_agent_action("Database Specialist", f"Call note: {note[:200]}")
    Session = get_session_factory()
    with Session() as session:
        call = session.get(Call, call_id)
        if not call:
            return "Call not found."
        prev = call.raw_summary_json or "[]"
        try:
            arr = json.loads(prev)
            if not isinstance(arr, list):
                arr = [prev]
        except json.JSONDecodeError:
            arr = [prev]
        arr.append(note[:2000])
        call.raw_summary_json = json.dumps(arr)[:8000]
        session.commit()
    return "Note appended to call record."
