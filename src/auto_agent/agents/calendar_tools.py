"""CrewAI tool: create Google Calendar event (requires prior OAuth)."""

from __future__ import annotations

from crewai.tools import tool

from auto_agent.agents.tools import log_agent_action
from auto_agent.context import current_call_db_id, current_customer_db_id
from auto_agent.services.database import Booking, get_session_factory
from auto_agent.services.google_calendar_client import create_calendar_event, default_demo_window_iso


@tool("Create Google Calendar Event")
def create_google_calendar_event(
    title: str,
    attendee_email: str,
    description: str,
    start_iso: str = "",
    end_iso: str = "",
) -> str:
    """Creates a calendar invite. If start_iso/end_iso are empty, uses a demo window."""
    log_agent_action("Calendar Specialist", f"Creating calendar event: {title}")
    if not attendee_email or "@" not in attendee_email:
        return "Cannot create calendar event without a valid attendee email."
    if not start_iso or not end_iso:
        start_iso, end_iso = default_demo_window_iso()
    try:
        result = create_calendar_event(
            title=title,
            start_iso=start_iso,
            end_iso=end_iso,
            attendee_email=attendee_email.strip(),
            description=description,
        )
        event_id = result.get("id", "")
        call_id = current_call_db_id.get()
        cust_id = current_customer_db_id.get()
        if event_id and (call_id or cust_id):
            Session = get_session_factory()
            with Session() as session:
                q = session.query(Booking).order_by(Booking.id.desc())
                if call_id:
                    q = q.filter(Booking.call_id == call_id)
                elif cust_id:
                    q = q.filter(Booking.customer_id == cust_id)
                row = q.first()
                if row:
                    row.calendar_event_id = event_id
                    session.commit()
        return f"Calendar event created. id={event_id}. Link={result.get('htmlLink', '')}"
    except Exception as e:
        log_agent_action("Calendar Specialist", f"Calendar error: {e}")
        return f"Calendar event was not created: {e}"
