from datetime import datetime
from crewai.tools import tool

# Mock Database
PRICING_DB = {
    "brake": 250,
    "oil": 50,
    "engine": 500,
    "transmission": 1200,
    "tire": 100,
    "battery": 150
}

# The Logger - Streamlit will read the file this creates!
def log_agent_action(agent_name, action):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {agent_name}: {action}\n"
    with open("agent_logs.txt", "a") as f:
        f.write(log_entry)
    print(log_entry.strip())

@tool("Get Repair Estimate")
def get_repair_estimate(symptom: str) -> str:
    """Searches the database for a repair estimate based on the symptom."""
    log_agent_action("Diagnostic Specialist", f"Searching database for symptom: '{symptom}'")
    symptom_lower = symptom.lower()
    
    for key, price in PRICING_DB.items():
        if key in symptom_lower:
            log_agent_action("Diagnostic Specialist", f"Found match! Estimated cost: ${price}")
            return f"The estimated cost for {key} repair is ${price}."
    
    log_agent_action("Diagnostic Specialist", "No exact match found. Recommending general inspection.")
    return "I couldn't find an exact price. We recommend an inspection for $89."

@tool("Book Appointment")
def book_appointment(date: str, time: str, customer_name: str) -> str:
    """Books an appointment in the calendar system."""
    log_agent_action("Scheduling Coordinator", f"Checking availability for {customer_name} on {date} at {time}...")
    log_agent_action("Scheduling Coordinator", "Slot is available. Booking confirmed in system.")
    return f"Appointment successfully booked for {customer_name} on {date} at {time}."