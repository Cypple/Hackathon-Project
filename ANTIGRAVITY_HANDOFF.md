# ANTIGRAVITY PROJECT HANDOFF

## PROJECT
MPLADS Monitoring / Anomaly Detection Hackathon Project

## CURRENT BRANCH
`frontend-backendintegration`

## COMPLETED
- Repository inspection
- Existing backend identified
- Existing anomaly detector identified
- Existing frontend identified
- Existing anomaly UI identified
- Relevant branches/commits inspected
- Checkpoint 0: Project handoff system & rules established
- Checkpoint 1: Backend verified, cached data loading enabled, cache_clear bug fixed, CORS expanded, anomaly endpoints tested live

## CURRENT CHECKPOINT
Checkpoint 1

## NEXT CHECKPOINT
Checkpoint 2 — Connect frontend dashboard and anomaly UI to backend API

---

## Backend Architecture
- **Framework**: FastAPI (Python 3.10+) running via Uvicorn.
- **Application Factory**: [`backend/app/main.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/main.py) defines `create_app() -> FastAPI` and exports the application object `app`.
  - Launch command: `uvicorn app.main:app --reload` (run from the `backend/` directory) or `python -m uvicorn app.main:app --app-dir backend --reload`.
- **Configuration & Settings**: [`backend/app/core/config.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/core/config.py) uses `pydantic-settings` to load configuration from `.env` and environment variables (`APP_NAME`, `APP_VERSION`, `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`, `API_V1_PREFIX`, `CORS_ORIGINS`, `SUPABASE_*`).
- **Database & External Services**: [`backend/app/db/supabase.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/db/supabase.py) contains factory functions `get_supabase_client()`, `get_supabase_admin_client()`, and `check_supabase_connection()`.
- **Modular Routing**:
  - Root routes in [`backend/app/main.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/main.py): `GET /` and unversioned `GET /health` (from [`backend/app/api/v1/routes/health.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/health.py)).
  - API v1 Router in [`backend/app/api/v1/router.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/router.py) (prefix `/api/v1`):
    - `config.router` from [`backend/app/api/v1/routes/config.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/config.py)
    - `projects.router` from [`backend/app/api/v1/routes/projects.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/projects.py)
    - `anomalies.router` from [`backend/app/api/v1/routes/anomalies.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/anomalies.py)
- **Data Source**: CSV dataset located at [`backend/data/sanctioned_mplads_projects.csv`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/data/sanctioned_mplads_projects.csv) containing 5,816 sanctioned MPLADS project records.
- **Legacy Standalone Script**: [`backend/main.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/main.py) is a standalone flat FastAPI prototype created prior to modularization; [`backend/app/main.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/main.py) is the active architectural entry point.

---

## Anomaly Detector Location
- **File**: [`backend/app/services/anomaly_detector.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/services/anomaly_detector.py)
- **Primary Function**: `detect_anomalies(works)`
- **Algorithm Methodology**:
  1. **Extreme Allocation (`extreme_allocation`)**:
     - Groups records by `(STATE, CATEGORY)` peer groups (minimum peer group size: 5).
     - Compares individual allocation amount against the peer group median (`peer_median_ratio = amount / peer_median`).
     - Calculates percentile and robust Z-score using Median Absolute Deviation (`0.6745 * (amount - median) / MAD`) with threshold `ROBUST_Z_THRESHOLD = 3.5`.
     - Flags projects if `ratio >= 3` or if strong evidence threshold is met (`ratio >= 4`, `percentile >= 99`, `robust_z >= 3.5`).
     - Severities assigned: `"Strong anomaly"` or `"Review flag"`.
  2. **Exact Repeated Pattern (`repeated_amount_pattern`, detector `A_strong_pattern`)**:
     - Clusters projects sharing identical `(MP NAME, WORK type, RECOMMENDED DATE, ALLOCATION AMOUNT)`.
     - Calculates pattern score based on matching MP, work type, amount, recommendation date, and spread across distinct locations.
     - Severities assigned based on count: `"Very high"` (≥6), `"High"` (≥4), `"Medium"` (3), `"Low"` (2).
  3. **Broader Repeated Pattern (`repeated_amount_pattern`, detector `B_broader_pattern`)**:
     - Clusters projects sharing identical `(MP NAME, WORK type, ALLOCATION AMOUNT)` across multiple locations regardless of date.
- **Sorting & Ethics**: Results are sorted with strongest patterns and highest ratios first. Output explicitly includes an explainability disclaimer: *"Anomalies indicate statistical irregularities and require verification; they do not prove fraud."*

---

## Anomaly API
The anomaly endpoints are implemented in [`backend/app/api/v1/routes/anomalies.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/anomalies.py) and exposed under the `/api/v1` prefix:

1. **`GET /api/v1/anomalies`**
   - Query Parameters:
     - `anomaly_type` (optional string): filter by `"extreme_allocation"` or `"repeated_amount_pattern"`.
     - `severity` (optional string): filter by severity name (e.g. `"Strong anomaly"`, `"Very high"`, etc.).
     - `limit` (integer, 1 to 500, default 50).
     - `offset` (integer, non-negative, default 0).
   - In-memory cached with `@lru_cache(maxsize=1)`.
2. **`GET /api/v1/anomalies/summary`**
   - Returns aggregated statistics: counts by anomaly type, severity, detector, extreme allocation count, repeated amount pattern count, average and maximum pattern scores.
3. **`POST /api/v1/refresh`**
   - Cache invalidation and re-detection trigger. Safely calls `cache_clear()` on `load_works` and `get_cached_anomalies`.

---

## API Response Format

### `GET /api/v1/anomalies`
```json
{
  "total": 5097,
  "limit": 2,
  "offset": 0,
  "disclaimer": "Anomalies indicate statistical irregularities and require verification; they do not prove fraud.",
  "anomalies": [
    {
      "project_id": "MPLADS_fc05439ee83842d2",
      "anomaly_type": "repeated_amount_pattern",
      "detector": "A_strong_pattern",
      "result": "Requires verification",
      "severity": "Very high",
      "pattern_score": 100,
      "matching_projects": 6,
      "different_locations": 6,
      "same_mp": true,
      "same_work_type": true,
      "same_amount": true,
      "same_recommendation_date": true,
      "mp": "SR Parthiban",
      "work_type": "lighting of public spaces",
      "recommendation_date": "10/19/2023",
      "allocation_amount": 540000.0,
      "locations": [
        "city=elampillai | ward=17",
        "city=elampillai | ward=9",
        "city=kadayampatti | ward=12",
        "city=konganapuram | ward=8",
        "city=nangavalli | ward=12",
        "city=poolampatti | ward=1"
      ],
      "message": "The same MP repeatedly recommended the same work type for the same amount on the same date across multiple locations."
    }
  ]
}
```

### `GET /api/v1/anomalies/summary`
```json
{
  "total_anomalies": 5097,
  "anomalies_by_type": {
    "repeated_amount_pattern": 4466,
    "extreme_allocation": 631
  },
  "anomalies_by_severity": {
    "Very high": 3144,
    "High": 407,
    "Strong anomaly": 439,
    "Medium": 289,
    "Review flag": 192,
    "Low": 626
  },
  "anomalies_by_detector": {
    "A_strong_pattern": 4064,
    "B_broader_pattern": 402,
    "Unknown": 631
  },
  "extreme_allocation_count": 631,
  "repeated_amount_pattern_count": 4466,
  "average_pattern_score": 96.31,
  "maximum_pattern_score": 100,
  "disclaimer": "Anomalies indicate statistical irregularities and require verification; they do not prove fraud."
}
```

---

## Frontend Dashboard
- **File**: [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html)
- **Technology**: Vanilla HTML5, CSS3, and JavaScript in a single file (~2.76 MB). Typography uses Google Fonts (*DM Sans* and *Manrope*).
- **Navigation & Views**:
  - **▦ Dashboard (`#dashboard`)**: Summary cards (Total projects, Sanctioned amount, Lok Sabha count, Data-quality alerts), State distribution bar chart, House split, Recent project records table.
  - **▤ Project Explorer (`#projects`)**: Search input, state filter, house filter, risk filter dropdowns, paginated project table, and row counter.
  - **⚠ Anomaly Center (`#anomalies`)**: Flagged records table and KPI summary cards.
  - **◫ Analytics (`#analytics`)**: Top states by sanctioned amount, project categories breakdown, and workbook profile metrics.
  - **Detail Modal (`#modal`)**: Pop-up inspector for individual project record attributes.
  - **Top Bar**: Lok Sabha / Rajya Sabha / All toggle.

---

## Anomaly UI
- **Location**: Tab `<section id="anomalies" class="page">` in [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html#L78-L86).
- **Key UI Elements**:
  - Metric summary cards:
    - Missing recommended date (`#missingDate`)
    - Missing amount (`#missingAmount`)
    - Future date / invalid amount (`#futureInvalid`)
  - Anomaly Table:
    - Table tbody `#anomalyRows` rendered by `renderAnomalies()`.
    - Columns: Project, State, Amount, Reason, Risk pill, and Details button.
  - Navigation Indicator:
    - Live count badge `#riskBadge` on the sidebar navigation button.

---

## Mock/Hardcoded Frontend Data
- **Location**: Script block in [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html#L101-L148).
- **Embedded Static Constants**:
  - `ALL_DATA`: An inlined JavaScript array containing all 5,816 project JSON objects (~2.76 MB of HTML file size).
  - Anomaly flags in `ALL_DATA`: Currently contains static flags derived directly from workbook data-cleaning columns (`"risk": 25, "anomaly": "Missing date"` or `"risk": 0, "anomaly": "No flagged anomaly"`).
  - `SUMMARY`: Precomputed static totals (`missing_date: 4035`, `missing_amount: 0`, `zero_neg: 0`, `future: 0`, `critical: 0`, etc.).
  - `STATES` and `CATS`: Precomputed static category and state arrays.
- **Network Calls**: Currently operates in-memory; will be connected to the FastAPI endpoints in Checkpoint 2.

---

## Authentication
- **Current Branch Status**:
  - No authentication or authorization is required by [`backend/app/api/v1/routes/projects.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/projects.py) or [`backend/app/api/v1/routes/anomalies.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/anomalies.py). All endpoints are publicly accessible.
  - [`backend/app/db/supabase.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/db/supabase.py) contains scaffolded client factories and `/api/v1/config/status` provides connection status.
  - [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html) has no login screens or token handlers.
- **Git History Note**: A TanStack Start Supabase Auth implementation was built in remote branch `lovable/main`, but authentication is deliberately deferred until after core frontend-backend anomaly integration is complete.

---

## CORS
- **Configuration Location**: [`backend/app/main.py:43-49`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/main.py#L43-L49) and [`backend/app/core/config.py:47`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/core/config.py#L47).
- **Current Settings**:
  - `CORSMiddleware` active on the FastAPI app.
  - Configured `CORS_ORIGINS`: `"http://localhost:3000,http://localhost:5173,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080"`.
  - `allow_credentials = True`
  - `allow_methods = ["*"]`
  - `allow_headers = ["*"]`

---

## Dependencies & Runtime Status
- **Environment**: Verified running on Python 3.14 venv (`backend/venv`).
- **Installed Packages** ([`backend/requirements.txt`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/requirements.txt)):
  - `fastapi==0.115.6`
  - `uvicorn[standard]==0.34.0`
  - `pydantic==2.10.4`
  - `pydantic-settings==2.7.0`
  - `python-dotenv==1.0.1`
  - `supabase==2.11.0`
  - `httpx==0.27.2`
  - `pytest==8.3.4`
- **Runtime Status**: Clean startup, zero import errors, interactive docs available at `/docs`.

---

## Known Issues
1. **Frontend File Size and Decoupling**:
   - `frontend/index2.html` is 2.76 MB due to 5,816 inlined JSON project rows. The UI needs to be connected to the backend API (`/api/v1/works`, `/api/v1/anomalies`, `/api/v1/anomalies/summary`) via `fetch()` calls so the hardcoded data can be removed.
2. **Data-Quality vs. Statistical Anomaly Discrepancy**:
   - The frontend's current `#anomalies` tab displays Excel missing data flags (e.g., missing date), whereas the backend service provides statistical anomaly detection (extreme allocation via Robust Z-score and repeated amount clustering).

---

## Completed Checkpoints
- **Checkpoint 0**: Project inspection and persistent handoff system created (`ANTIGRAVITY_HANDOFF.md` and `.agents/rules/project_rules.md`).
- **Checkpoint 1**: Expose existing anomaly detector through backend API.
  - Files modified:
    - [`backend/app/api/v1/routes/projects.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/projects.py): Added `@lru_cache(maxsize=1)` to `load_works()` returning `tuple(reader)` for caching and compatibility with `.cache_clear()`.
    - [`backend/app/api/v1/routes/anomalies.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/anomalies.py): Added defensive `hasattr(load_works, "cache_clear")` in `/api/v1/refresh`.
    - [`backend/app/core/config.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/core/config.py): Expanded default `CORS_ORIGINS` to allow standard frontend development ports (5500, 8000, 8080, 5173, 3000).
  - Verified API functionality:
    - `GET /health` -> 200 OK
    - `GET /docs` -> 200 OK
    - `GET /api/v1/works` -> 200 OK (5,816 real records loaded)
    - `GET /api/v1/anomalies` -> 200 OK (5,097 real anomalies returned)
    - `GET /api/v1/anomalies/summary` -> 200 OK (4,466 repeated amount patterns, 631 extreme allocations)
    - `POST /api/v1/refresh` -> 200 OK (cache cleared and reloaded)
    - Live Uvicorn server test confirmed live HTTP requests succeed with 200 OK.

---

## Next Checkpoint
- **Checkpoint 2 — Connect frontend to real backend anomaly & project APIs**:
  - Wire `frontend/index2.html` to fetch real dataset summary from `/api/v1/dashboard`.
  - Wire project table to fetch paginated rows from `/api/v1/works`.
  - Wire Anomaly Center to fetch statistical anomaly data from `/api/v1/anomalies` and `/api/v1/anomalies/summary`.
  - Remove hardcoded `ALL_DATA` constant from `frontend/index2.html` to decouple frontend and drastically reduce bundle size.

---

## Important Warnings for Future Agents
- **STRICT BRANCH RULE**: Work ONLY on `frontend-backendintegration`. Do not switch, create, or merge branches.
- **NO DUPLICATE LOGIC**: Do NOT modify the existing anomaly detection algorithm in [`backend/app/services/anomaly_detector.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/services/anomaly_detector.py) and do NOT create a second anomaly detector.
- **NO DUPLICATE DASHBOARDS**: Do NOT build a second dashboard or another anomaly UI. [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html) is the designated dashboard and anomaly interface.
- **SOURCE OF TRUTH**: The backend anomaly detection engine is the source of truth; frontend must fetch and present real API data instead of hardcoded data.
- **NO GUESSING**: Inspect files directly for endpoint routes and JSON fields rather than assuming schema structures.
- **SECURITY**: Never commit secrets or `.env` files.
- **DISCIPLINE**: Work strictly checkpoint-by-checkpoint. Verify changes, update `ANTIGRAVITY_HANDOFF.md`, commit, push to `origin/frontend-backendintegration`, and stop.
