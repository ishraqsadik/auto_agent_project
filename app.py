"""Streamlit manager dashboard: live logs + SQLite call/customer/booking views."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import time

import pandas as pd
import streamlit as st
from sqlalchemy import text

from auto_agent.services.database import DATABASE_URL, get_engine, init_db

st.set_page_config(page_title="Bulls Auto Repair Dashboard", layout="wide", initial_sidebar_state="expanded")

init_db()


def read_agent_logs() -> str:
    path = _root / "agent_logs.txt"
    if not path.exists():
        path.write_text("System Initialized...\n", encoding="utf-8")
    return path.read_text(encoding="utf-8", errors="replace")


def load_sql_df(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


st.title("Bulls Auto Repair — Manager Dashboard")
st.caption(f"Database: `{DATABASE_URL}`")

mode = st.sidebar.radio("View", ["Live logs", "CRM tables"], index=0)

if mode == "Live logs":
    st.subheader("Agent activity")
    auto = st.sidebar.toggle("Auto-refresh", value=True)
    interval = st.sidebar.slider("Interval (seconds)", 1, 10, 2)
    st.markdown(
        f'<div style="background:#0d1117;color:#c9d1d9;padding:1rem;border-radius:8px;font-family:ui-monospace,monospace;white-space:pre-wrap;max-height:520px;overflow-y:auto;">{read_agent_logs()}</div>',
        unsafe_allow_html=True,
    )
    if auto:
        time.sleep(interval)
        st.rerun()
else:
    tab_calls, tab_customers, tab_bookings = st.tabs(["Calls", "Customers", "Bookings"])

    with tab_calls:
        st.subheader("Recent calls")
        try:
            df = load_sql_df(
                "SELECT id, external_call_id, customer_id, status, started_at, ended_at FROM calls ORDER BY id DESC LIMIT 50"
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"No call data yet or DB error: {e}")

    with tab_customers:
        st.subheader("Customers")
        try:
            df = load_sql_df(
                "SELECT id, phone_e164, name, email, vehicle, created_at FROM customers ORDER BY id DESC LIMIT 100"
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"No customer data yet or DB error: {e}")

    with tab_bookings:
        st.subheader("Bookings")
        try:
            df = load_sql_df(
                """
                SELECT b.id, b.call_id, b.customer_id, b.symptom, b.requested_date_text,
                       b.requested_time_text, b.estimate_text, b.calendar_event_id, b.created_at
                FROM bookings b
                ORDER BY b.id DESC LIMIT 100
                """
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"No bookings yet or DB error: {e}")
