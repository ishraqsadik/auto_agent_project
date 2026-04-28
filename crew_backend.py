import os
from crewai import Agent, Task, Crew, Process
from tools import get_repair_estimate, book_appointment, log_agent_action
from dotenv import load_dotenv

load_dotenv()
MODEL_NAME = os.getenv("CREWAI_MODEL", "gemini/gemini-2.5-flash")

def run_crew_backend(customer_name: str, symptom: str, date: str, time: str) -> str:
    log_agent_action("SYSTEM", f"--- New request received from Vapi for {customer_name} ---")
    
    diagnostic_agent = Agent(
        role='Diagnostic Specialist',
        goal='Provide an accurate repair estimate based on customer symptoms.',
        backstory='An expert mechanic who knows the cost of every repair.',
        verbose=True,
        allow_delegation=False,
        llm=MODEL_NAME,
        tools=[get_repair_estimate]
    )

    scheduling_agent = Agent(
        role='Scheduling Coordinator',
        goal='Book appointments for customers after they receive an estimate.',
        backstory='A highly organized receptionist managing the shop calendar.',
        verbose=True,
        allow_delegation=False,
        llm=MODEL_NAME,
        tools=[book_appointment]
    )

    diagnostic_task = Task(
        description=f"Find the repair estimate for this symptom: {symptom}.",
        expected_output="A short sentence stating the estimated price.",
        agent=diagnostic_agent
    )

    scheduling_task = Task(
        description=f"Book an appointment for {customer_name} on {date} at {time}. Include the repair estimate from the previous task in your final response.",
        expected_output="A friendly confirmation message including the price and appointment time.",
        agent=scheduling_agent
    )

    crew = Crew(
        agents=[diagnostic_agent, scheduling_agent],
        tasks=[diagnostic_task, scheduling_task],
        process=Process.sequential
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