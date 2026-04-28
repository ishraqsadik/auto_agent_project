# Developer guide — Bulls Auto Repair

Internal notes for running locally, deploying the API to Render, and hosting the Streamlit dashboard on Streamlit Community Cloud.

## Code source declaration

This project was developed with human guidance and implementation support from **Cursor** (AI coding assistant), including iterative code generation, refactoring, debugging, and documentation drafting.

## Local quick start

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

3. Run the API and dashboard:

**API**

```powershell
venv\Scripts\python -m uvicorn main:app --port 8000
```

**Dashboard (local SQLite + log file)**

```powershell
venv\Scripts\python -m streamlit run app.py
```

Do not set `PUBLIC_API_URL` / `STREAMLIT_DASHBOARD_KEY` in local Streamlit secrets unless you want the dashboard to read from a deployed API instead.

## Render (FastAPI)

1. Push this repo to GitHub and create a **Web Service** from the repo (or use **Blueprint** with `render.yaml` in the root).
2. Set environment variables in the Render dashboard (values marked `sync: false` in `render.yaml` must be added manually):
   - `GOOGLE_API_KEY`, `CREWAI_MODEL`
   - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_OAUTH_REDIRECT_URI` — must be `https://<your-service>.onrender.com/integrations/google/callback`
   - `STREAMLIT_DASHBOARD_KEY` — long random string; reuse the same value in Streamlit Cloud secrets
3. In Google Cloud Console OAuth client, add the Render callback URL to **Authorized redirect URIs**.
4. In Vapi, set the `process_booking` tool server URL to `https://<your-service>.onrender.com/vapi-webhook`.
5. Smoke test: `GET /health`, one test `POST /vapi-webhook`, complete Google OAuth once on the public URL.

**Note:** SQLite on a free Render web instance is on ephemeral disk; data can reset on redeploys.

## Dashboard read API (for Streamlit Cloud)

Protected JSON endpoints (header `X-Dashboard-Key` must match `STREAMLIT_DASHBOARD_KEY` on Render):

- `GET /api/calls`
- `GET /api/customers`
- `GET /api/bookings`
- `GET /api/agent_logs` — returns `{"text": "..."}`

## Streamlit Community Cloud

1. Connect the GitHub repo and set the main file to `app.py`.
2. In **Secrets**, add:

```toml
PUBLIC_API_URL = "https://<your-render-service>.onrender.com"
STREAMLIT_DASHBOARD_KEY = "<same as Render STREAMLIT_DASHBOARD_KEY>"
```

3. Deploy and open the app URL; CRM tabs and live logs should load from the Render API.

## Google Calendar (shop OAuth)

1. In Google Cloud Console, create OAuth **Web** client credentials.
2. Add authorized redirect URI matching `GOOGLE_OAUTH_REDIRECT_URI` (local or Render).
3. Start the API, then open `/integrations/google/start` on that host.

## Vapi tool: `process_booking`

Server tool with JSON arguments (strings): `customer_name`, `customer_email`, `vehicle`, `symptom`, `date`, `time`.

## Layout

- `main.py` — Uvicorn entry (`uvicorn main:app`)
- `src/auto_agent/` — package (API, agents, services)
- `data/app.db` — local SQLite (created at runtime, gitignored)

## Health check

`GET /health` → `{"ok":true}`
