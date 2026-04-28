"""CrewAI orchestration: fast diagnostic + scheduling path for Vapi."""

from __future__ import annotations

import os

from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from auto_agent.agents.tools import book_appointment, get_repair_estimate, log_agent_action
from auto_agent.context import current_call_db_id, current_customer_db_id

load_dotenv()
MODEL_NAME = os.getenv("CREWAI_MODEL", "gemini/gemini-2.5-flash")


def run_crew_backend(
    customer_name: str,
    symptom: str,
    date: str,
    time: str,
    *,
    customer_email: str = "",
    vehicle: str = "",
) -> str:
    log_agent_action("SYSTEM", f"--- New request from Vapi for {customer_name} ---")

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

    diagnostic_task = Task(
        description=(
            f"Customer vehicle: {vehicle or 'unknown vehicle'}. "
            f"Find the repair estimate for this symptom: {symptom}."
        ),
        expected_output="A short sentence stating the estimated price or inspection recommendation.",
        agent=diagnostic_agent,
    )

    scheduling_task = Task(
        description=(
            f"Book an appointment for {customer_name} on {date} at {time}. "
            f"Use customer_email '{customer_email}' in the book appointment tool when provided. "
            "Include the repair estimate from the previous task in your final response. "
            "Keep the response conversational and concise."
        ),
        expected_output="A friendly confirmation message including the price and appointment time.",
        agent=scheduling_agent,
        context=[diagnostic_task],
    )

    crew = Crew(
        agents=[diagnostic_agent, scheduling_agent],
        tasks=[diagnostic_task, scheduling_task],
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
