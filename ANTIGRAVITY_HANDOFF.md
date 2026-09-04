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
- Checkpoint 2: Connected existing Anomaly UI in `frontend/index2.html` to real backend API endpoints (`/api/v1/anomalies`, `/api/v1/anomalies/summary`) with loading, empty, error, and modal states
- Checkpoint 3: Real frontend ↔ backend integration verified end-to-end via automated browser QA. Anomaly Center UI confirmed rendering real backend anomaly data from `/api/v1/anomalies` and `/api/v1/anomalies/summary` across all states (loading, success, empty, error, modal, house filter, reload)

## CURRENT CHECKPOINT
Checkpoint 3

## NEXT CHECKPOINT
Checkpoint 4: Authentication

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
- **Technology**: Vanilla HTML5, CSS3, and JavaScript in a single file. Typography uses Google Fonts (*DM Sans* and *Manrope*).
- **Navigation & Views**:
  - **▦ Dashboard (`#dashboard`)**: Summary cards (Total projects, Sanctioned amount, Lok Sabha count, Data-quality alerts), State distribution bar chart, House split, Recent project records table.
  - **▤ Project Explorer (`#projects`)**: Search input, state filter, house filter, risk filter dropdowns, paginated project table, and row counter.
  - **⚠ Anomaly Center (`#anomalies`)**: Flagged records table and KPI summary cards connected directly to the backend anomaly API.
  - **◫ Analytics (`#analytics`)**: Top states by sanctioned amount, project categories breakdown, and workbook profile metrics.
  - **Detail Modal (`#modal`)**: Pop-up inspector displaying unified project attributes and statistical anomaly metrics (severity, pattern scores, peer ratios, location clusters).
  - **Top Bar**: Lok Sabha / Rajya Sabha / All toggle.

---

## Anomaly UI & API Integration
- **Location**: Section `<section id="anomalies" class="page">` in [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html#L78-L86).
- **API Endpoints Used**:
  - `GET /api/v1/anomalies/summary`: Populates KPI summary cards, sidebar navigation badge, and overview alerts.
  - `GET /api/v1/anomalies?limit=250`: Populates the flagged records table.
- **Data Mapping**:
  - Card 1 (`#missingDate`): Displays `ANOMALIES_SUMMARY.repeated_amount_pattern_count` (e.g. 4,466).
  - Card 2 (`#missingAmount`): Displays `ANOMALIES_SUMMARY.extreme_allocation_count` (e.g. 631).
  - Card 3 (`#futureInvalid`): Displays `ANOMALIES_SUMMARY.total_anomalies` (e.g. 5,097).
  - Sidebar Badge (`#riskBadge`): Real-time total count `ANOMALIES_SUMMARY.total_anomalies` (e.g. 5,097).
  - Overview Card (`#alerts`): Real-time total count `ANOMALIES_SUMMARY.total_anomalies` (e.g. 5,097).
  - Table Rows (`#anomalyRows`):
    - **Project**: Work name (`proj.work || a.work_type || a.project_id`) + subtitle (`a.project_id · a.mp`).
    - **State**: Peer group state or record state (`a.peer_group?.state || proj.state || 'N/A'`).
    - **Amount**: `moneyFull(a.allocation_amount)`.
    - **Reason**: `a.message` explainable text.
    - **Risk**: Red pill with `a.severity` (e.g. "Very high", "Strong anomaly", "High", etc.).
    - **Details Button**: Triggers `openModal(a.project_id)` displaying complete anomaly evidence alongside project data.
- **UI States Handled**:
  - **Loading State**: Displays animated spinner indicator with text `⏳ Loading real anomalies from backend API...`. Summary cards show `...`.
  - **Empty State**: Displays `No anomaly records detected by backend.` or `No anomalies found for the "${ACTIVE_HOUSE}" filter.`.
  - **Error State**: Displays a red warning panel `⚠️ Unable to load anomaly records from backend API` with server endpoint, error message, and an interactive `Retry API Connection` button. Cards show `—` and badge shows `!`. Other dashboard sections continue functioning without crash.

---

## Authentication
- **Current Branch Status**:
  - Backend endpoints are publicly accessible and do not require authentication headers.
  - Frontend makes direct fetch requests to backend.
  - Authentication is deferred until core frontend-backend functionality is complete.

---

## CORS
- **Configuration Location**: [`backend/app/main.py:43-49`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/main.py#L43-L49) and [`backend/app/core/config.py:47`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/core/config.py#L47).
- **Configured `CORS_ORIGINS`**:
  `"http://localhost:3000,http://localhost:5173,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080,null"`
  - `null` origin is safely explicitly included to support browsers opening `frontend/index2.html` directly as a local file (`file:///...`), without wildcard credentials.

---

## Dependencies & Runtime Status
- **Environment**: Python 3.14 venv (`backend/venv`).
- **FastAPI / Uvicorn**: Verified running and serving API requests on port 8000.
- **Frontend**: Pure Vanilla HTML5/CSS3/JS, zero build step required.

---

## Known Issues
1. **Frontend File Size and Decoupling**:
   - `frontend/index2.html` still contains the inlined `ALL_DATA` array for the Project Explorer tab. This will be decoupled and wired to `/api/v1/works` and `/api/v1/dashboard` in Checkpoint 3.

---

## Completed Checkpoints
- **Checkpoint 0**: Project inspection and persistent handoff system created (`ANTIGRAVITY_HANDOFF.md` and `.agents/rules/project_rules.md`).
- **Checkpoint 1**: Expose existing anomaly detector through backend API (`/api/v1/anomalies`, `/api/v1/anomalies/summary`, `/api/v1/refresh`).
- **Checkpoint 2**: Connect existing Anomaly UI in `frontend/index2.html` to real backend API:
  - Frontend queries `/api/v1/anomalies/summary` and `/api/v1/anomalies?limit=250`.
  - Replaced hardcoded anomaly card counts and mock table data with live backend data.
  - Added loading state, empty state, API error state with retry button.
  - Upgraded modal inspector to display statistical anomaly evidence and peer metrics.
  - Added safe `null` origin to backend `CORS_ORIGINS` for `file://` execution.
- **Checkpoint 3**: Real frontend ↔ backend integration verified end-to-end with automated browser QA:
  - **Status**: Completed and fully verified end-to-end.
  - **Backend Endpoints Used**:
    - `GET http://127.0.0.1:8000/api/v1/anomalies/summary`
    - `GET http://127.0.0.1:8000/api/v1/anomalies?limit=250`
  - **Exact JSON Fields Mapped by Frontend**:
    - From `/api/v1/anomalies/summary`:
      - `total_anomalies` (5,097) -> `#futureInvalid` (Card 3: Total detected anomalies), `#riskBadge` (Sidebar badge), `#alerts` (Dashboard overview alerts card)
      - `repeated_amount_pattern_count` (4,466) -> `#missingDate` (Card 1: Repeated amount patterns)
      - `extreme_allocation_count` (631) -> `#missingAmount` (Card 2: Extreme allocations)
    - From `/api/v1/anomalies`:
      - `anomalies`: Array of anomaly records:
        - `project_id` -> Displayed in table subtitle, used as key for inspector modal
        - `work_type` -> Fallback title when record not in local index
        - `mp` -> Member of Parliament name in table subtitle
        - `allocation_amount` -> Formatted via `moneyFull()` (e.g. "₹5,40,000") in Amount column
        - `message` -> Human-readable explanation text in Reason column
        - `severity` -> Severity string ("Very high", "High", "Strong anomaly", etc.) in Risk pill
        - `anomaly_type` -> Modal inspector subtitle and detection type field
        - `result` -> Verification flag ("Requires verification") in Modal
        - `pattern_score` -> Pattern score ("X / 100") in Modal
        - `matching_projects` -> Project count ("X works") in Modal
        - `different_locations` -> Location count ("X locations") in Modal
        - `peer_group` (`state`, `category`, `size`) -> Peer group summary in Modal
        - `peer_median` -> Statistical median formatted as currency in Modal
        - `peer_median_ratio` -> Ratio vs peer median ("Xx") in Modal
        - `robust_z_score` -> Robust Z-score in Modal
        - `percentile` -> Percentile ranking ("X%") in Modal
        - `locations` -> Location cluster list in Modal
  - **End-to-End Test Results**:
    - Automated browser test run via Chrome DevTools Protocol (CDP) connecting headless Chrome to `frontend/index2.html` and the live FastAPI backend.
    - Verified all 10 QA checkpoints:
      1. In-memory API data correctly loaded (`REAL_ANOMALIES` length: 250, `ANOMALIES_SUMMARY.total_anomalies`: 5097).
      2. UI summary cards and sidebar badges accurately display live backend counts ("5,097", "4,466", "631").
      3. Anomaly table renders 150 rows sliced from backend results with correct titles, states, formatted amounts, explainable messages, and severity badges.
      4. Detail modal successfully triggers from table rows and renders complete statistical evidence.
      5. House filter buttons dynamically filter anomalies (Lok Sabha: 150, Rajya Sabha: 36, All: 150).
      6. Loading state verified (spinner row, ellipsis `...` in badges and cards).
      7. Empty state verified ("No anomaly records detected by backend.").
      8. Error state verified (red alert panel, "!" in badge, "—" in cards, and "Retry API Connection" button).
      9. Recovery verified (re-invoking `fetchBackendAnomalies()` restores all live data).
      10. Full page reload verified (clean re-fetch and DOM population in 0.5s).
  - **Remaining Known Issues**:
    - `frontend/index2.html` still retains the inlined `ALL_DATA` constant for the Project Explorer tab (to be decoupled in future work).
- **Next Checkpoint**:
  - `Checkpoint 4: Authentication`

---

## Next Checkpoint
- **Checkpoint 4: Authentication**:
  - Implement user authentication (Supabase or backend auth), login/logout states, and token-based protection where appropriate.

---

## Important Warnings for Future Agents
- **STRICT BRANCH RULE**: Work ONLY on `frontend-backendintegration`. Do not switch, create, or merge branches.
- **NO DUPLICATE LOGIC**: Do NOT modify the existing anomaly detection algorithm in [`backend/app/services/anomaly_detector.py`](file:///c:/Users/keert/Hackathon/Hackathon-Project/backend/app/services/anomaly_detector.py) and do NOT create a second anomaly detector.
- **NO DUPLICATE DASHBOARDS**: Do NOT build a second dashboard or another anomaly UI. [`frontend/index2.html`](file:///c:/Users/keert/Hackathon/Hackathon-Project/frontend/index2.html) is the designated dashboard and anomaly interface.
- **SOURCE OF TRUTH**: The backend anomaly detection engine is the source of truth; frontend must fetch and present real API data instead of hardcoded data.
- **NO GUESSING**: Inspect files directly for endpoint routes and JSON fields rather than assuming schema structures.
- **SECURITY**: Never commit secrets or `.env` files.
- **DISCIPLINE**: Work strictly checkpoint-by-checkpoint. Verify changes, update `ANTIGRAVITY_HANDOFF.md`, commit, push to `origin/frontend-backendintegration`, and stop.
