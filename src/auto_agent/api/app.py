"""FastAPI app: health, Vapi webhook, Google OAuth for Calendar."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from auto_agent.agents.crew_backend import run_crew_backend
from auto_agent.agents.tools import log_agent_action
from auto_agent.api.payload_utils import extract_external_call_id, payload_snippet
from auto_agent.services.database import Call, get_session_factory, init_db
from auto_agent.services.google_calendar_client import create_calendar_event, default_demo_window_iso, store_google_credentials
from auto_agent.services.google_oauth import build_authorization_url, exchange_code
from auto_agent.services.repositories import close_call, create_booking, ensure_open_call, find_customer_by_email, upsert_customer

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
        url, _state = build_authorization_url()
        return RedirectResponse(url)

    @app.get("/integrations/google/callback")
    async def google_oauth_callback(
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ):
        if error:
            return {"ok": False, "error": error}
        if not code:
            return {"ok": False, "error": "missing_code"}
        if not state:
            return {"ok": False, "error": "missing_state"}
        creds = exchange_code(code, state)
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
            vehicle = args.get("vehicle", "") or ""

            internal_call_id: int | None = None
            customer_id: int | None = None
            is_returning_customer = False
            try:
                Session = get_session_factory()
                with Session() as session:
                    existing_customer = find_customer_by_email(session, customer_email.strip() or None)
                    is_returning_customer = existing_customer is not None
                    cust = upsert_customer(
                        session,
                        name=name,
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
                    customer_id = cust.id
                    internal_call_id = call.id
            except Exception as e:
                logger.exception("DB best-effort write failed: %s", e)

            final_response = run_crew_backend(
                name,
                symptom,
                date,
                time,
                customer_email=customer_email,
                vehicle=vehicle,
            )

            if is_returning_customer:
                final_response = f"Welcome back, {name}. {final_response}"

            calendar_event_id = None
            try:
                Session = get_session_factory()
                with Session() as session:
                    if internal_call_id:
                        call = session.get(Call, internal_call_id)
                    else:
                        call = None
                    booking = create_booking(
                        session,
                        call_id=internal_call_id,
                        customer_id=customer_id,
                        symptom=symptom,
                        date_text=date,
                        time_text=time,
                        estimate_text=final_response,
                    )
                    if customer_email and "@" in customer_email:
                        try:
                            start_iso, end_iso = default_demo_window_iso()
                            event = create_calendar_event(
                                title=f"Bulls Auto Repair - {name}",
                                start_iso=start_iso,
                                end_iso=end_iso,
                                attendee_email=customer_email.strip(),
                                description=f"Vehicle: {vehicle or 'unknown'}. Concern: {symptom}.",
                            )
                            calendar_event_id = event.get("id")
                            booking.calendar_event_id = calendar_event_id
                        except Exception as e:
                            logger.exception("Calendar create failed: %s", e)
                    if call:
                        close_call(session, call)
                    session.commit()
            except Exception as e:
                logger.exception("Post-processing DB/calendar failed: %s", e)

            results.append({"toolCallId": tool_call_id, "result": final_response})

        return {"results": results}

    return app


# Uvicorn entry: `from auto_agent.api.app import app` when PYTHONPATH includes src
app = create_app()
