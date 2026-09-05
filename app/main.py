"""
MPLADS Sentinel FastAPI application.

Run from the backend directory:
    uvicorn app.main:app --reload

This single file:
- serves the frontend at /ui/
- exposes the API under /api/v1/
- loads the real MPLADS CSV
- exposes dashboard, works, filters and anomaly endpoints
- keeps anomaly results cached until /refresh is called
"""

from __future__ import annotations

import csv
import importlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

DATA_FILE = (
    BACKEND_DIR
    / "data"
    / "sanctioned_mplads_projects.csv"
)

UI_DIR = (
    PROJECT_DIR
    / "frontend"
    / "anomaly"
)

UI_INDEX = UI_DIR / "index.html"


# ---------------------------------------------------------------------
# ANOMALY DETECTOR
# ---------------------------------------------------------------------

def _load_detector():
    """
    Find the anomaly detector wherever it exists
    in the current project.
    """

    candidates = (
        "app.anomaly_detector",
        "app.services.anomaly_detector",
        "app.detectors.anomaly_detector",
        "anomaly_detector",
    )

    last_error = None

    for module_name in candidates:

        try:

            module = importlib.import_module(
                module_name
            )

            detector = getattr(
                module,
                "detect_anomalies",
                None
            )

            if callable(detector):
                return detector

        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        "Could not import detect_anomalies. "
        "Place anomaly_detector.py in backend/ or backend/app/."
    ) from last_error


detect_anomalies = _load_detector()


# ---------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------

app = FastAPI(
    title="MPLADS Sentinel API",
    version="1.0.0",
    description=(
        "AI-assisted MPLADS monitoring and early-warning prototype. "
        "Anomaly results indicate statistical irregularities requiring "
        "verification and do not prove fraud."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# DATA HELPERS
# ---------------------------------------------------------------------

def _require_data_file() -> None:

    if not DATA_FILE.exists():

        raise HTTPException(
            status_code=500,
            detail=f"Dataset not found: {DATA_FILE}",
        )


def _to_number(value: Any) -> float:

    if value is None:
        return 0.0

    try:

        text = str(value)
        text = text.replace(",", "").strip()

        if not text:
            return 0.0

        return float(text)

    except (TypeError, ValueError):

        return 0.0


def _first(
    row: dict[str, Any],
    *keys: str,
    default: Any = ""
) -> Any:

    for key in keys:

        value = row.get(key)

        if (
            value is not None
            and str(value).strip() != ""
        ):
            return value

    return default


@lru_cache(maxsize=1)
def load_works() -> tuple[dict[str, str], ...]:

    """
    Load the complete CSV once and reuse it.
    """

    _require_data_file()

    with DATA_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        return tuple(
            dict(row)
            for row in reader
        )


@lru_cache(maxsize=1)
def get_anomalies() -> tuple[dict[str, Any], ...]:

    """
    Run the anomaly detector once and cache its result.
    """

    works = load_works()

    return tuple(
        detect_anomalies(works)
    )


def _invalidate_caches() -> None:

    load_works.cache_clear()
    get_anomalies.cache_clear()


# ---------------------------------------------------------------------
# FRONTEND
# ---------------------------------------------------------------------

@app.get(
    "/ui/",
    include_in_schema=False
)
def ui_home():

    if not UI_INDEX.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                f"Frontend index.html not found: "
                f"{UI_INDEX}"
            ),
        )

    return FileResponse(UI_INDEX)


# Serve style.css, script.js and other frontend files.

if UI_DIR.exists():

    app.mount(
        "/ui",
        StaticFiles(
            directory=UI_DIR,
            html=True
        ),
        name="ui-static",
    )


# ---------------------------------------------------------------------
# ROOT
# ---------------------------------------------------------------------

@app.get("/")
def root():

    return {
        "message":
            "MPLADS Sentinel backend is running",

        "ui":
            "/ui/",

        "docs":
            "/docs",

        "api":
            "/api/v1",
    }


@app.get("/health")
def health():

    return {
        "status":
            "online",

        "dataset_exists":
            DATA_FILE.exists(),

        "dataset":
            DATA_FILE.name,

        "ui_exists":
            UI_INDEX.exists(),
    }


# ---------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------

@app.get("/api/v1/dashboard")
def dashboard():

    works = load_works()

    total_projects = len(works)

    total_allocation = sum(
        _to_number(
            _first(
                row,
                "ALLOCATION_AMOUNT_NUM",
                "ALLOCATION AMOUNT",
                default=0,
            )
        )
        for row in works
    )

    projects_by_status: dict[str, int] = {}

    projects_by_category: dict[str, int] = {}

    projects_by_state: dict[str, int] = {}


    for row in works:

        status = (
            str(
                row.get("STATUS")
                or "Unknown"
            )
            .strip()
            or "Unknown"
        )

        category = (
            str(
                row.get("CATEGORY")
                or "Unknown"
            )
            .strip()
            or "Unknown"
        )

        state = (
            str(
                row.get("STATE")
                or "Unknown"
            )
            .strip()
            or "Unknown"
        )


        projects_by_status[status] = (
            projects_by_status.get(
                status,
                0
            ) + 1
        )


        projects_by_category[category] = (
            projects_by_category.get(
                category,
                0
            ) + 1
        )


        projects_by_state[state] = (
            projects_by_state.get(
                state,
                0
            ) + 1
        )


    anomalies = get_anomalies()


    repeated_count = sum(
        1
        for item in anomalies
        if item.get(
            "anomaly_type"
        )
        == "repeated_amount_pattern"
    )


    extreme_count = sum(
        1
        for item in anomalies
        if item.get(
            "anomaly_type"
        )
        == "extreme_allocation"
    )


    return {

        "total_projects":
            total_projects,

        "total_allocation":
            total_allocation,

        "total_anomalies":
            len(anomalies),

        "detection_types":
            2,

        "states":
            list(
                projects_by_state.keys()
            ),

        "categories":
            list(
                projects_by_category.keys()
            ),

        "projects_by_status":
            projects_by_status,

        "projects_by_category":
            projects_by_category,

        "projects_by_state":
            projects_by_state,

        "repeated_amount_pattern":
            repeated_count,

        "extreme_allocation":
            extreme_count,

        "total_allocation_amount":
            total_allocation,

        "anomaly_count":
            len(anomalies),
    }


# ---------------------------------------------------------------------
# FILTERS
# ---------------------------------------------------------------------

def _build_filters() -> dict[str, list[str]]:

    works = load_works()


    def values_for(
        field: str
    ) -> list[str]:

        values = {

            str(
                row.get(field)
                or ""
            ).strip()

            for row in works

            if str(
                row.get(field)
                or ""
            ).strip()
        }

        return sorted(
            values,
            key=str.lower
        )


    return {

        "states":
            values_for("STATE"),

        "districts":
            values_for("DISTRICT"),

        "constituencies":
            values_for("CONSTITUENCY"),

        "categories":
            values_for("CATEGORY"),

        "statuses":
            values_for("STATUS"),
    }


@app.get("/api/v1/filters")
def filters():

    return _build_filters()


# Compatibility route for earlier frontend.

@app.get("/api/v1/works/filters")
def works_filters_compatibility():

    return _build_filters()


# ---------------------------------------------------------------------
# WORKS / PROJECTS
# ---------------------------------------------------------------------

@app.get("/api/v1/works")
def works(

    search: str | None = None,

    state: str | None = None,

    district: str | None = None,

    constituency: str | None = None,

    category: str | None = None,

    status: str | None = None,

    limit: int = Query(
        25,
        ge=1,
        le=500
    ),

    offset: int = Query(
        0,
        ge=0
    ),
):

    all_works = list(
        load_works()
    )


    if search:

        needle = (
            search
            .strip()
            .lower()
        )


        all_works = [

            row

            for row in all_works

            if needle
            in " ".join(

                str(
                    row.get(field)
                    or ""
                )

                for field in (

                    "PROJECT_ID",
                    "MP NAME",
                    "WORK",
                    "STATE",
                    "CONSTITUENCY",
                    "CATEGORY",
                    "STATUS",

                )

            ).lower()

        ]


    def exact_filter(

        rows:
            list[dict[str, str]],

        field:
            str,

        value:
            str | None,

    ) -> list[dict[str, str]]:

        if not value:
            return rows


        wanted = (
            value
            .strip()
            .lower()
        )


        return [

            row

            for row in rows

            if str(
                row.get(field)
                or ""
            ).strip().lower()
            == wanted

        ]


    all_works = exact_filter(
        all_works,
        "STATE",
        state
    )


    all_works = exact_filter(
        all_works,
        "DISTRICT",
        district
    )


    all_works = exact_filter(
        all_works,
        "CONSTITUENCY",
        constituency
    )


    all_works = exact_filter(
        all_works,
        "CATEGORY",
        category
    )


    all_works = exact_filter(
        all_works,
        "STATUS",
        status
    )


    total = len(
        all_works
    )


    selected = all_works[
        offset:
        offset + limit
    ]


    return {

        "total":
            total,

        "limit":
            limit,

        "offset":
            offset,

        "works":
            selected,

        "projects":
            selected,

        "items":
            selected,
    }


# ---------------------------------------------------------------------
# SINGLE WORK
# ---------------------------------------------------------------------

@app.get("/api/v1/works/{work_id}")
def single_work(
    work_id: str
):

    for row in load_works():

        project_id = str(

            _first(
                row,
                "PROJECT_ID",
                "IDA",
                default=""
            )

        ).strip()


        if project_id == work_id:

            return row


    raise HTTPException(
        status_code=404,
        detail="Work not found",
    )


# ---------------------------------------------------------------------
# ANOMALY SUMMARY
# ---------------------------------------------------------------------

@app.get(
    "/api/v1/anomalies/summary"
)
def anomaly_summary():

    anomalies = list(
        get_anomalies()
    )


    repeated = [

        item

        for item in anomalies

        if item.get(
            "anomaly_type"
        )
        == "repeated_amount_pattern"

    ]


    extreme = [

        item

        for item in anomalies

        if item.get(
            "anomaly_type"
        )
        == "extreme_allocation"

    ]


    scores = [

        float(
            item.get(
                "pattern_score"
            )
            or 0
        )

        for item in repeated

        if item.get(
            "pattern_score"
        )
        is not None

    ]


    severity_counts: dict[str, int] = {}


    for item in anomalies:

        severity = str(
            item.get(
                "severity"
            )
            or "Unknown"
        )


        severity_counts[
            severity
        ] = (
            severity_counts.get(
                severity,
                0
            )
            + 1
        )


    return {

        "total_anomalies":
            len(anomalies),

        "total":
            len(anomalies),

        "repeated_amount_pattern":
            len(repeated),

        "extreme_allocation":
            len(extreme),

        "max_pattern_score":
            max(scores)
            if scores
            else 0,

        "severity_counts":
            severity_counts,

        "detection_types":
            2,
    }


# ---------------------------------------------------------------------
# ANOMALIES
# ---------------------------------------------------------------------

@app.get(
    "/api/v1/anomalies"
)
def anomalies(

    anomaly_type:
        str | None = None,

    severity:
        str | None = None,

    limit: int = Query(
        50,
        ge=1,
        le=500
    ),

    offset: int = Query(
        0,
        ge=0
    ),

):

    results = list(
        get_anomalies()
    )


    if anomaly_type:

        wanted = (
            anomaly_type
            .strip()
            .lower()
        )


        results = [

            item

            for item in results

            if str(
                item.get(
                    "anomaly_type"
                )
                or ""
            ).lower()
            == wanted

        ]


    if severity:

        wanted = (
            severity
            .strip()
            .lower()
        )


        results = [

            item

            for item in results

            if str(
                item.get(
                    "severity"
                )
                or ""
            ).lower()
            == wanted

        ]


    total = len(
        results
    )


    selected = results[
        offset:
        offset + limit
    ]


    return {

        "total":
            total,

        "limit":
            limit,

        "offset":
            offset,

        "disclaimer":
            (
                "Anomalies indicate "
                "statistical irregularities "
                "and require verification; "
                "they do not prove fraud."
            ),

        "anomalies":
            selected,

        "items":
            selected,
    }


# ---------------------------------------------------------------------
# REFRESH
# ---------------------------------------------------------------------

@app.post(
    "/api/v1/refresh"
)
def refresh():

    _invalidate_caches()


    works_count = len(
        load_works()
    )


    anomaly_count = len(
        get_anomalies()
    )


    return {

        "status":
            "refreshed",

        "projects":
            works_count,

        "anomalies":
            anomaly_count,
    }


# Compatibility GET refresh.

@app.get(
    "/api/v1/refresh"
)
def refresh_get():

    return refresh()