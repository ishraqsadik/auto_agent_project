"""FastAPI app: health, Vapi webhook, Google OAuth for Calendar."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from auto_agent.agents.crew_backend import run_crew_backend
from auto_agent.agents.tools import log_agent_action
from auto_agent.api.payload_utils import extract_caller_phone, extract_external_call_id, payload_snippet
from auto_agent.services.database import get_session_factory, init_db
from auto_agent.services.google_calendar_client import store_google_credentials
from auto_agent.services.google_oauth import build_authorization_url, exchange_code
from auto_agent.services.repositories import ensure_open_call, upsert_customer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Bulls Auto Repair API", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/integrations/google/start")
    async def google_oauth_start():
        url = build_authorization_url()
        return RedirectResponse(url)

    @app.get("/integrations/google/callback")
    async def google_oauth_callback(code: str | None = None, error: str | None = None):
        if error:
            return {"ok": False, "error": error}
        if not code:
            return {"ok": False, "error": "missing_code"}
        creds = exchange_code(code)
        store_google_credentials(creds)
        return {"ok": True, "message": "Google Calendar connected. You can close this tab."}

    @app.post("/vapi-webhook")
    async def vapi_webhook(request: Request):
        payload = await request.json()
        log_agent_action("SYSTEM", "Webhook received from Vapi/ngrok.")

        message = payload.get("message", {})
        tool_calls = (
            message.get("toolCalls")
            or message.get("tool_calls")
            or payload.get("toolCalls")
            or payload.get("tool_calls")
            or []
        )
        if not tool_calls:
            log_agent_action("SYSTEM", "No tool calls found in webhook payload.")
            return {"results": []}

        external_call_id = extract_external_call_id(payload)
        caller_phone = extract_caller_phone(payload)
        snippet = payload_snippet(payload)

        results = []
        for tool_call in tool_calls:
            tool_call_id = tool_call.get("id")
            function_payload = tool_call.get("function", {})
            args = function_payload.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)

            name = args.get("customer_name", "Customer")
            symptom = args.get("symptom", "unknown")
            date = args.get("date", "soon")
            time = args.get("time", "anytime")
            customer_email = args.get("customer_email", "") or ""
            customer_phone = args.get("customer_phone", "") or caller_phone or ""
            vehicle = args.get("vehicle", "") or ""

            internal_call_id: int | None = None
            try:
                Session = get_session_factory()
                with Session() as session:
                    cust = upsert_customer(
                        session,
                        name=name,
                        phone_e164=(customer_phone.strip() or None),
                        email=customer_email.strip() or None,
                        vehicle=vehicle.strip() or None,
                    )
                    call = ensure_open_call(
                        session,
                        external_call_id=external_call_id,
                        customer_id=cust.id,
                        payload_snippet=snippet,
                    )
                    session.commit()
                    internal_call_id = call.id
            except Exception as e:
                logger.exception("DB best-effort write failed: %s", e)

            final_response = run_crew_backend(
                name,
                symptom,
                date,
                time,
                customer_email=customer_email,
                customer_phone=customer_phone,
                vehicle=vehicle,
                internal_call_id=internal_call_id,
            )

            results.append({"toolCallId": tool_call_id, "result": final_response})

        return {"results": results}

    return app


# Uvicorn entry: `from auto_agent.api.app import app` when PYTHONPATH includes src
app = create_app()
