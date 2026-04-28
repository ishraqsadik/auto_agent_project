"""Google OAuth2 flow for Calendar API (shop user)."""

from __future__ import annotations

import os
import secrets

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
PENDING_OAUTH: dict[str, str] = {}


def _client_config() -> dict:
    cid = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not cid or not secret:
        raise RuntimeError("Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env")
    return {
        "web": {
            "client_id": cid,
            "client_secret": secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/integrations/google/callback")],
        }
    }


def build_authorization_url(state: str | None = None) -> tuple[str, str]:
    redirect = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/integrations/google/callback")
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect)
    final_state = state or secrets.token_urlsafe(24)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=final_state,
    )
    if not flow.code_verifier:
        raise RuntimeError("OAuth flow did not generate a PKCE code verifier.")
    PENDING_OAUTH[final_state] = flow.code_verifier
    return url, final_state


def exchange_code(code: str, state: str) -> Credentials:
    redirect = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/integrations/google/callback")
    code_verifier = PENDING_OAUTH.pop(state, None)
    if not code_verifier:
        raise RuntimeError("Missing or expired OAuth state. Start the Google connection flow again.")
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect)
    flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    return flow.credentials
