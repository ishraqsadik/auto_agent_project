"""Streamlit manager dashboard: live logs + call/customer/booking views (local SQLite or remote API)."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import time

import httpx
import pandas as pd
import streamlit as st
from sqlalchemy import text

from auto_agent.services.database import DATABASE_URL, get_engine, init_db

st.set_page_config(page_title="Bulls Auto Repair Dashboard", layout="wide", initial_sidebar_state="expanded")


def _remote_dashboard_config() -> tuple[str | None, str | None]:
    """Streamlit Cloud: set PUBLIC_API_URL and STREAMLIT_DASHBOARD_KEY in app secrets."""
    try:
        secrets = st.secrets
    except Exception:
        return None, None
    try:
        base = str(secrets.get("PUBLIC_API_URL", "") or "").strip().rstrip("/")
        key = str(secrets.get("STREAMLIT_DASHBOARD_KEY", "") or "").strip()
    except Exception:
        return None, None
    if not base or not key:
        return None, None
    return base, key


REMOTE_BASE, REMOTE_KEY = _remote_dashboard_config()
_HEADERS = {"X-Dashboard-Key": REMOTE_KEY} if REMOTE_KEY else {}

if not (REMOTE_BASE and REMOTE_KEY):
    init_db()


def read_agent_logs() -> str:
    if REMOTE_BASE and REMOTE_KEY:
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(f"{REMOTE_BASE}/api/agent_logs", headers=_HEADERS)
                r.raise_for_status()
                return str(r.json().get("text", ""))
        except Exception as e:
            return f"(Could not load remote logs: {e})"
    path = _root / "agent_logs.txt"
    if not path.exists():
        path.write_text("System Initialized...\n", encoding="utf-8")
    return path.read_text(encoding="utf-8", errors="replace")


def load_sql_df(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def load_remote_table(path: str) -> pd.DataFrame:
    with httpx.Client(timeout=45.0) as client:
        r = client.get(f"{REMOTE_BASE}{path}", headers=_HEADERS)
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)


st.title("Bulls Auto Repair — Manager Dashboard")
if REMOTE_BASE and REMOTE_KEY:
    st.caption(f"Remote API: `{REMOTE_BASE}`")
else:
    st.caption(f"Database: `{DATABASE_URL}`")

mode = st.sidebar.radio("View", ["Live logs", "CRM tables"], index=0)

if mode == "Live logs":
    st.subheader("Agent activity")
    auto = st.sidebar.toggle("Auto-refresh", value=True)
    interval = st.sidebar.slider("Interval (seconds)", 1, 10, 2)
    st.code(read_agent_logs(), language=None)
    if auto:
        time.sleep(interval)
        st.rerun()
else:
    tab_calls, tab_customers, tab_bookings = st.tabs(["Calls", "Customers", "Bookings"])

    with tab_calls:
        st.subheader("Recent calls")
        try:
            if REMOTE_BASE and REMOTE_KEY:
                df = load_remote_table("/api/calls")
            else:
                df = load_sql_df(
                    "SELECT id, external_call_id, customer_id, status, started_at, ended_at FROM calls ORDER BY id DESC LIMIT 50"
                )
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"No call data yet or load error: {e}")

    with tab_customers:
        st.subheader("Customers")
        try:
            if REMOTE_BASE and REMOTE_KEY:
                df = load_remote_table("/api/customers")
            else:
                df = load_sql_df(
                    "SELECT id, name, email, vehicle, created_at FROM customers ORDER BY id DESC LIMIT 100"
                )
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"No customer data yet or load error: {e}")

    with tab_bookings:
        st.subheader("Bookings")
        try:
            if REMOTE_BASE and REMOTE_KEY:
                df = load_remote_table("/api/bookings")
            else:
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
            st.warning(f"No bookings yet or load error: {e}")
