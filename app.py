import streamlit as st
import time
import os

st.set_page_config(page_title="Bulls Auto Repair Dashboard", layout="wide")

st.title("🔧 Bulls Auto Repair - Manager Dashboard")
st.markdown("### Live Multi-Agent Collaboration Feed")

# Create the log file if it doesn't exist
if not os.path.exists("agent_logs.txt"):
    with open("agent_logs.txt", "w") as f:
        f.write("System Initialized...\n")

def read_logs():
    with open("agent_logs.txt", "r") as f:
        return f.read()

log_placeholder = st.empty()

# Refresh every 2 seconds
while True:
    logs = read_logs()
    log_placeholder.code(logs, language="text")
    time.sleep(2)