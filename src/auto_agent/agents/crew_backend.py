"""CrewAI orchestration: database, diagnostic, scheduling, calendar."""

from __future__ import annotations

import os

from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from auto_agent.agents.calendar_tools import create_google_calendar_event
from auto_agent.agents.db_tools import append_call_note, lookup_customer_by_phone, save_booking_row, upsert_customer_record
from auto_agent.agents.tools import book_appointment, get_repair_estimate, log_agent_action
from auto_agent.context import current_call_db_id, current_customer_db_id
from auto_agent.services.database import Call, get_session_factory

load_dotenv()
MODEL_NAME = os.getenv("CREWAI_MODEL", "gemini/gemini-2.5-flash")


def run_crew_backend(
    customer_name: str,
    symptom: str,
    date: str,
    time: str,
    *,
    customer_email: str = "",
    customer_phone: str = "",
    vehicle: str = "",
    internal_call_id: int | None = None,
) -> str:
    log_agent_action("SYSTEM", f"--- New request from Vapi for {customer_name} ---")
    if internal_call_id is not None:
        current_call_db_id.set(internal_call_id)
        Session = get_session_factory()
        with Session() as session:
            call = session.get(Call, internal_call_id)
            if call and call.customer_id:
                current_customer_db_id.set(call.customer_id)

    db_agent = Agent(
        role="Database Specialist",
        goal="Maintain accurate customer and call records in SQLite.",
        backstory="You use tools only. Never invent database state.",
        verbose=True,
        allow_delegation=False,
        llm=MODEL_NAME,
        tools=[lookup_customer_by_phone, upsert_customer_record, save_booking_row, append_call_note],
    )

    diagnostic_agent = Agent(
        role="Diagnostic Specialist",
        goal="Provide an accurate repair estimate based on customer symptoms.",
        backstory="An expert mechanic who knows the cost of every repair.",
        verbose=True,
        allow_delegation=False,
        llm=MODEL_NAME,
        tools=[get_repair_estimate],
    )

    scheduling_agent = Agent(
        role="Scheduling Coordinator",
        goal="Book appointments after an estimate is known.",
        backstory="A highly organized receptionist managing the shop calendar.",
        verbose=True,
        allow_delegation=False,
        llm=MODEL_NAME,
        tools=[book_appointment],
    )

    calendar_agent = Agent(
        role="Calendar Specialist",
        goal="Create Google Calendar invites when email is available.",
        backstory="You create calendar events using the provided tool and OAuth-connected shop calendar.",
        verbose=True,
        allow_delegation=False,
        llm=MODEL_NAME,
        tools=[create_google_calendar_event],
    )

    db_task = Task(
        description=(
            f"Customer: {customer_name}. Phone (E.164 if known): {customer_phone or 'unknown'}. "
            f"Email: {customer_email or 'unknown'}. Vehicle: {vehicle or 'unknown'}. "
            "If phone looks like a real phone number, call Lookup Customer By Phone first. "
            "Then call Upsert Customer Record with the best known fields. "
            "Finally call Append Call Note with a one-line summary of the intake."
        ),
        expected_output="Short confirmation that customer records were updated.",
        agent=db_agent,
    )

    diagnostic_task = Task(
        description=f"Find the repair estimate for this symptom: {symptom}.",
        expected_output="A short sentence stating the estimated price or inspection recommendation.",
        agent=diagnostic_agent,
        context=[db_task],
    )

    scheduling_task = Task(
        description=(
            f"Book an appointment for {customer_name} on {date} at {time}. "
            f"Use customer_email '{customer_email}' in the book appointment tool when provided. "
            "Include the repair estimate from the previous task in your final response."
        ),
        expected_output="A friendly confirmation message including the price and appointment time.",
        agent=scheduling_agent,
        context=[diagnostic_task],
    )

    persist_booking_task = Task(
        description=(
            f"Save a booking row with symptom '{symptom}', date '{date}', time '{time}', "
            "and a one-sentence estimate summary from the diagnostic task output."
        ),
        expected_output="Confirmation that the booking row was saved.",
        agent=db_agent,
        context=[scheduling_task, diagnostic_task],
    )

    calendar_task = Task(
        description=(
            f"If customer_email is a valid email, create a Google Calendar event titled "
            f"'Bulls Auto Repair - {customer_name}' for {date} {time} with attendee customer_email. "
            "Use a short description including symptom and estimate. "
            "If email is missing or invalid, skip creating an event and say so."
        ),
        expected_output="Calendar confirmation or explanation why it was skipped.",
        agent=calendar_agent,
        context=[persist_booking_task, scheduling_task],
    )

    crew = Crew(
        agents=[db_agent, diagnostic_agent, scheduling_agent, calendar_agent],
        tasks=[db_task, diagnostic_task, scheduling_task, persist_booking_task, calendar_task],
        process=Process.sequential,
    )

    try:
        result = crew.kickoff()
        log_agent_action("SYSTEM", "Process complete. Sending back to Vapi Voice Agent.")
        return str(result)
    except Exception as e:
        error_text = str(e)
        log_agent_action("SYSTEM", f"CrewAI execution failed: {error_text}")
        return (
            "I am sorry, our AI service is temporarily unavailable while processing your request. "
            "Please try again in a minute."
        )
    finally:
        current_call_db_id.set(None)
        current_customer_db_id.set(None)
