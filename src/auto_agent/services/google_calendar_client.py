"""Create Calendar events using stored OAuth credentials."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from auto_agent.services.database import OAuthToken, get_session_factory


def _load_stored_credentials() -> Credentials | None:
    Session = get_session_factory()
    with Session() as session:
        row = session.query(OAuthToken).filter(OAuthToken.provider == "google").order_by(OAuthToken.id.desc()).first()
        if not row or (not row.refresh_token and not row.access_token):
            return None
        cid = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
        return Credentials(
            token=row.access_token,
            refresh_token=row.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cid or None,
            client_secret=secret or None,
            scopes=["https://www.googleapis.com/auth/calendar.events"],
        )


def store_google_credentials(creds: Credentials, user_email: str | None = None) -> None:
    Session = get_session_factory()
    with Session() as session:
        row = session.query(OAuthToken).filter(OAuthToken.provider == "google").order_by(OAuthToken.id.desc()).first()
        if row is None:
            row = OAuthToken(provider="google", user_email=user_email)
            session.add(row)
        row.refresh_token = creds.refresh_token or row.refresh_token
        row.access_token = creds.token
        row.expires_at = creds.expiry
        row.user_email = user_email or row.user_email
        session.commit()


def create_calendar_event(
    *,
    title: str,
    start_iso: str,
    end_iso: str,
    attendee_email: str,
    description: str = "",
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """Insert an event on the connected user's primary calendar."""
    creds = _load_stored_credentials()
    if creds is None:
        raise RuntimeError(
            "Google Calendar is not connected. Open GET /integrations/google/start in a browser once to authorize."
        )
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": "America/New_York"},
        "end": {"dateTime": end_iso, "timeZone": "America/New_York"},
        "attendees": [{"email": attendee_email}],
    }
    event = service.events().insert(calendarId=calendar_id, body=body, sendUpdates="all").execute()
    return {"id": event.get("id"), "htmlLink": event.get("htmlLink")}


def default_demo_window_iso() -> tuple[str, str]:
    """Fallback window when natural-language date/time is not parsed."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1)
    start = start.replace(hour=15, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return start.isoformat(), end.isoformat()
