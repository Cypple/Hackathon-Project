# MPLADS Backend (foundation)

Python + FastAPI + Supabase backend for our Smart India Hackathon MPLADS project.

> This README grows with each stage. Right now **Stage 1 (app skeleton) and
> Stage 2 (configuration)** are done.

## What this backend does today

- Starts a FastAPI web server
- Serves a public health check: `GET /health`
- Reads all settings from environment variables (`.env`)
- Writes basic logs on startup/shutdown
- Auto-generates API documentation at `/docs`

## What it does NOT do yet

Nothing dataset-specific. These are intentionally missing because the
MPLADS dataset has not been collected:

- MPLADS works/projects database schema — `[DATABASE SCHEMA WILL BE DESIGNED AFTER DATASET REVIEW]`
- Dataset fields — `[FINAL DATA DICTIONARY WILL BE PROVIDED LATER]`
- Anomaly detection — `[ANOMALY METHODOLOGY WILL BE DECIDED AFTER DATA ANALYSIS]`
- Risk scoring — `[FINAL RISK LEVELS WILL BE DEFINED LATER]`
- Dashboard metrics, filters, search — defined after the dataset arrives

Also not built yet (coming in later stages): Supabase connection, auth,
user profiles, authorization, error handling, tests.

## Project structure

```
backend/
  app/
    main.py                  # entry point: creates the FastAPI app
    core/
      config.py              # all settings, read from environment variables
      logging_config.py      # logging setup
    api/
      v1/
        router.py            # collects all /api/v1 endpoints
        routes/
          health.py          # GET /health
  requirements.txt           # Python packages we need
  .env.example               # template for secrets (committed)
  .env                       # real secrets (NEVER committed)
  .gitignore
```

## Setup (first time only)

Run these from inside the `backend/` folder.

1. Create a virtual environment (a private folder for this project's packages):

   ```bash
   python -m venv venv
   ```

2. Activate it:

   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

3. Install packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Create your `.env`:

   - Windows: `copy .env.example .env`
   - Mac/Linux: `cp .env.example .env`

   Every variable is explained inside `.env.example`. Supabase values can stay
   empty until Stage 3.

## Run the server

```bash
uvicorn app.main:app --reload
```

`--reload` restarts the server automatically when you save a file.

Then open:

- http://127.0.0.1:8000/health → `{"status": "ok", ...}`
- http://127.0.0.1:8000/docs → interactive API documentation

## Git branches

- `main` — always working code. Do not commit directly.
- feature branches — one per task, e.g. `feature/backend-auth`.
- Open a Pull Request into `main`, get one teammate to look at it, then merge.

## Where future dataset work will go

- Database tables → a new `app/models/` folder (after schema is decided)
- Data endpoints → `app/api/v1/routes/works.py`, `anomalies.py`, `dashboard.py`
- Analysis / anomaly logic → a new `app/services/` folder

None of these exist yet on purpose.
