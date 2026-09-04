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

## CURRENT CHECKPOINT
Checkpoint 0

## NEXT CHECKPOINT
Checkpoint 1 — Backend/anomaly API verification

---

## Backend Architecture
- **Framework**: FastAPI (Python 3.10+) running via Uvicorn.
- **Application Factory**: [`backend/app/main.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/main.py) defines `create_app() -> FastAPI` and exports the application object `app`.
  - Intended launch command: `uvicorn app.main:app --reload` (run from the `backend/` directory).
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
   - Results are cached in-memory with `@lru_cache(maxsize=1)`.
2. **`GET /api/v1/anomalies/summary`**
   - Returns aggregated statistics: counts by anomaly type, severity, detector, extreme allocation count, repeated amount pattern count, average and maximum pattern scores.
3. **`POST /api/v1/refresh`**
   - Cache invalidation and re-detection trigger. *(See Known Issues regarding `load_works.cache_clear()`)*.

---

## API Response Format

### `GET /api/v1/anomalies`
```json
{
  "total": 120,
  "limit": 50,
  "offset": 0,
  "disclaimer": "Anomalies indicate statistical irregularities and require verification; they do not prove fraud.",
  "anomalies": [
    {
      "project_id": "MPLADS_...",
      "anomaly_type": "extreme_allocation",
      "result": "Requires verification",
      "severity": "Strong anomaly",
      "allocation_amount": 50000000.0,
      "peer_group": {
        "state": "Uttar Pradesh",
        "category": "Normal/Others",
        "size": 2291
      },
      "peer_median": 200000.0,
      "peer_median_ratio": 250.0,
      "percentile": 99.95,
      "robust_z_score": 12.34,
      "strong_anomaly_evidence": {
        "ratio_ge_4x": true,
        "percentile_ge_99": true,
        "robust_z_ge_threshold": true
      },
      "message": "Allocation is unusually high compared with comparable projects."
    }
  ]
}
```

### `GET /api/v1/anomalies/summary`
```json
{
  "total_anomalies": 120,
  "anomalies_by_type": {
    "extreme_allocation": 45,
    "repeated_amount_pattern": 75
  },
  "anomalies_by_severity": {
    "Very high": 20,
    "Strong anomaly": 15,
    "High": 30,
    "Review flag": 30,
    "Medium": 15,
    "Low": 10
  },
  "anomalies_by_detector": {
    "A_strong_pattern": 40,
    "B_broader_pattern": 35,
    "Unknown": 45
  },
  "extreme_allocation_count": 45,
  "repeated_amount_pattern_count": 75,
  "average_pattern_score": 82.5,
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
- **Network Calls**: There are currently **no `fetch()` or AJAX calls** in `frontend/index2.html`; all rendering logic operates purely in-memory on the static JS objects.

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
  - Default `CORS_ORIGINS`: `"http://localhost:3000,http://localhost:5173"`.
  - `allow_credentials = True`
  - `allow_methods = ["*"]`
  - `allow_headers = ["*"]`
- **Integration Note**: To allow `frontend/index2.html` to communicate with the backend when served via local development servers (e.g. port 5500, 8080, 8000) or file systems, `CORS_ORIGINS` will need to include the local frontend development origin (or allow `*`).

---

## Dependencies
- **Backend** ([`backend/requirements.txt`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/requirements.txt)):
  - `fastapi==0.115.6`
  - `uvicorn[standard]==0.34.0`
  - `pydantic==2.10.4`
  - `pydantic-settings==2.7.0`
  - `python-dotenv==1.0.1`
  - `supabase==2.11.0`
  - `httpx==0.27.2`
  - `pytest==8.3.4`
- **Frontend**:
  - Pure Vanilla HTML5, CSS3, JavaScript.
  - External CDN Fonts: Google Fonts (*DM Sans*, *Manrope*).

---

## Known Issues
1. **Cache clear bug in `/api/v1/refresh`**:
   - In [`backend/app/api/v1/routes/anomalies.py:143`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/anomalies.py#L143), `refresh()` calls `load_works.cache_clear()`.
   - However, `load_works` in [`backend/app/api/v1/routes/projects.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/api/v1/routes/projects.py#L16) is a regular function without `@lru_cache`, causing an `AttributeError` if `POST /api/v1/refresh` is called.
2. **Synchronous Uncached CSV Loading in Projects API**:
   - Every invocation of endpoints in `projects.py` re-reads the full CSV file from disk synchronously.
3. **Frontend File Size and Decoupling**:
   - `frontend/index2.html` is 2.76 MB due to 5,816 inlined JSON project rows. The UI needs to be connected to the backend API (`/api/v1/works`, `/api/v1/anomalies`, `/api/v1/anomalies/summary`) via `fetch()` calls so the hardcoded data can be removed.
4. **Data-Quality vs. Statistical Anomaly Discrepancy**:
   - The frontend's current `#anomalies` tab displays Excel missing data flags (e.g., missing date), whereas the backend service provides statistical anomaly detection (extreme allocation via Robust Z-score and repeated amount clustering).

---

## Completed Checkpoints
- **Checkpoint 0**: Project inspection and persistent handoff system created (`ANTIGRAVITY_HANDOFF.md` and `.agents/rules/project_rules.md`).

---

## Next Checkpoint
- **Checkpoint 1 — Backend/anomaly API verification**:
  - Test and verify FastAPI server startup (`app.main:app`).
  - Verify `/health`, `/api/v1/works`, `/api/v1/anomalies`, and `/api/v1/anomalies/summary` return valid responses against the real dataset.
  - Address the `load_works.cache_clear()` issue in `anomalies.py`.
  - Validate CORS configuration against local frontend serving origins.

---

## Important Warnings for Future Agents
- **STRICT BRANCH RULE**: Work ONLY on `frontend-backendintegration`. Do not switch, create, or merge branches.
- **NO DUPLICATE LOGIC**: Do NOT modify the existing anomaly detection algorithm in [`backend/app/services/anomaly_detector.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/services/anomaly_detector.py) and do NOT create a second anomaly detector.
- **NO DUPLICATE DASHBOARDS**: Do NOT build a second dashboard or another anomaly UI. [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html) is the designated dashboard and anomaly interface.
- **SOURCE OF TRUTH**: The backend anomaly detection engine is the source of truth; frontend must fetch and present real API data instead of hardcoded data.
- **NO GUESSING**: Inspect files directly for endpoint routes and JSON fields rather than assuming schema structures.
- **SECURITY**: Never commit secrets or `.env` files.
- **DISCIPLINE**: Work strictly checkpoint-by-checkpoint. Verify changes, update `ANTIGRAVITY_HANDOFF.md`, commit, push to `origin/frontend-backendintegration`, and stop.
