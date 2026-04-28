"""CrewAI tools: pricing, booking log, file logging for Streamlit."""

from __future__ import annotations

from datetime import datetime

from crewai.tools import tool

SERVICE_CATALOG = [
    {
        "name": "brake inspection and pad replacement",
        "price": 250,
        "keywords": ["brake", "brakes", "squeak", "squeaking", "grinding", "stopping"],
        "summary": "Brake issues like squeaking, grinding, or weak stopping power.",
    },
    {
        "name": "oil change service",
        "price": 50,
        "keywords": ["oil", "maintenance", "service light", "oil change"],
        "summary": "Routine oil change and basic maintenance service.",
    },
    {
        "name": "engine diagnostic service",
        "price": 500,
        "keywords": ["engine", "check engine", "misfire", "overheating", "knocking"],
        "summary": "Engine diagnostics for warning lights, overheating, or poor performance.",
    },
    {
        "name": "transmission inspection",
        "price": 1200,
        "keywords": ["transmission", "shifting", "slipping", "gear", "gears"],
        "summary": "Transmission issues like slipping, rough shifting, or gear engagement problems.",
    },
    {
        "name": "tire service",
        "price": 100,
        "keywords": ["tire", "tires", "flat", "rotation", "alignment", "wheel"],
        "summary": "Tire problems including flats, uneven wear, and alignment concerns.",
    },
    {
        "name": "battery test and replacement",
        "price": 150,
        "keywords": ["battery", "won't start", "wont start", "dead battery", "jump start"],
        "summary": "Battery and starting issues, including dead battery concerns.",
    },
]


def log_agent_action(agent_name: str, action: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {agent_name}: {action}\n"
    with open("agent_logs.txt", "a", encoding="utf-8") as f:
        f.write(log_entry)
    print(log_entry.strip())


@tool("Get Repair Estimate")
def get_repair_estimate(symptom: str) -> str:
    """Searches the service catalog for a repair estimate based on the symptom."""
    log_agent_action("Diagnostic Specialist", f"Searching database for symptom: '{symptom}'")
    symptom_lower = symptom.lower()

    for service in SERVICE_CATALOG:
        if any(keyword in symptom_lower for keyword in service["keywords"]):
            log_agent_action(
                "Diagnostic Specialist",
                f"Matched service '{service['name']}'. Estimated cost: ${service['price']}",
            )
            return (
                f"It sounds like you may need a {service['name']}, which starts at "
                f"${service['price']}. {service['summary']}"
            )

    log_agent_action("Diagnostic Specialist", "No exact match found. Recommending general inspection.")
    return "I couldn't find an exact price. We recommend an inspection for $89."


@tool("Book Appointment")
def book_appointment(date: str, time: str, customer_name: str, customer_email: str = "") -> str:
    """Records an appointment slot in the shop system (demo). Use customer_email for calendar invite."""
    log_agent_action(
        "Scheduling Coordinator",
        f"Checking availability for {customer_name} ({customer_email or 'no email'}) on {date} at {time}...",
    )
    log_agent_action("Scheduling Coordinator", "Slot is available. Booking confirmed in system.")
    return f"Appointment successfully booked for {customer_name} on {date} at {time}."
