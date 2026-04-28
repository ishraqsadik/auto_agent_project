# Bulls Auto Repair — Agentic voice + CrewAI backend

Public voice front desk (Vapi) calls a FastAPI webhook. CrewAI agents estimate repairs, record SQLite data, and optionally create Google Calendar events after OAuth.

## Code source declaration

This project was developed with human guidance and implementation support from **Cursor** (AI coding assistant), including iterative code generation, refactoring, debugging, and documentation drafting.

## Quick start

1. Create a virtual environment and install dependencies:

```powershell
cd "D:\Coding\CIS4930 Agentic AI\auto_agent_project"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create a `.env` file in the project root (example):

```env
GOOGLE_API_KEY=your_gemini_api_key
CREWAI_MODEL=gemini/gemini-2.5-flash
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/integrations/google/callback
```

3. Run three terminals:

**API**

```powershell
venv\Scripts\python -m uvicorn main:app --port 8000
```

**Tunnel (example)**

```powershell
ngrok http 8000
```

Point Vapi custom tool `process_booking` to:

`https://<your-ngrok-host>/vapi-webhook`

**Dashboard**

```powershell
venv\Scripts\python -m streamlit run app.py
```

## Google Calendar (shop OAuth)

1. In Google Cloud Console, create OAuth **Web** client credentials.
2. Add authorized redirect URI matching `GOOGLE_OAUTH_REDIRECT_URI` in `.env` (e.g. `http://127.0.0.1:8000/integrations/google/callback` or your ngrok callback URL).
3. Start the API, then open in a browser:

`http://127.0.0.1:8000/integrations/google/start`

Complete consent once. Refresh token is stored in SQLite (`oauth_tokens`).

## Vapi tool: `process_booking`

Use a server tool with JSON arguments (all strings):

- `customer_name`
- `customer_email` (required for calendar invite)
- `vehicle` (e.g. `2018 Honda Civic`)
- `symptom`
- `date`
- `time`

## Runtime architecture

- **Voice/front desk layer:** Vapi assistant collects booking details and calls `process_booking`.
- **Backend reasoning layer:** FastAPI invokes two CrewAI agents (`Diagnostic Specialist` and `Scheduling Coordinator`) for estimate + booking response synthesis.
- **Persistence/integration layer:** deterministic Python services save call/customer/booking rows in SQLite and create Google Calendar events.
- **Dashboard layer:** Streamlit reads logs + SQLite tables for live monitoring.

## Project layout

- `main.py` — Uvicorn entry (`uvicorn main:app`)
- `src/auto_agent/` — application package (API, agents, services)
- `vapi_system_prompt.txt` — paste into Vapi assistant system prompt
- `data/app.db` — local SQLite (created at runtime, gitignored)

## Health check

`GET http://127.0.0.1:8000/health` → `{"ok":true}`
