from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import csv
import os
from collections import Counter
from functools import lru_cache

from anomaly_detector import detect_anomalies


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="MPLADS Monitoring & Anomaly Detection API",
    description="Backend API for MPLADS project monitoring and explainable anomaly detection.",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATASET LOCATION
# ============================================================

DATA_FILE = os.path.join(
    os.path.dirname(__file__),
    "data",
    "sanctioned_mplads_projects.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

@lru_cache(maxsize=1)
def load_works():
    """
    Load the complete MPLADS dataset once and keep it in memory.

    This prevents the CSV from being read from disk on every request.
    """

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        return tuple(
            dict(row)
            for row in reader
        )


# ============================================================
# ANOMALY CACHE
# ============================================================

@lru_cache(maxsize=1)
def get_cached_anomalies():
    """
    Run Team A's anomaly detector once and cache the result.

    This is important because anomaly detection over the complete
    dataset can take noticeably longer than a normal API request.
    """

    works = list(load_works())

    return tuple(
        detect_anomalies(works)
    )


# ============================================================
# REFRESH CACHE
# ============================================================

def refresh_data():

    load_works.cache_clear()
    get_cached_anomalies.cache_clear()

    # Reload dataset
    works = load_works()

    # Recalculate anomalies
    anomalies = get_cached_anomalies()

    return {
        "projects_loaded": len(works),
        "anomalies_detected": len(anomalies)
    }


# ============================================================
# CONVERT ALLOCATION AMOUNT TO NUMBER
# ============================================================

def get_amount(work):

    value = (
        work.get("ALLOCATION_AMOUNT_NUM")
        or work.get("ALLOCATION AMOUNT")
        or "0"
    )

    try:

        return float(
            str(value)
            .replace(",", "")
            .strip()
        )

    except (ValueError, TypeError):

        return 0


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "message": "MPLADS Backend is running!",
        "version": "1.0.0",
        "projects": len(load_works()),
        "anomalies": len(get_cached_anomalies())
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    works = load_works()
    anomalies = get_cached_anomalies()

    return {
        "status": "healthy",
        "backend": "MPLADS Backend",
        "projects": len(works),
        "anomalies": len(anomalies)
    }


# ============================================================
# WORKS
# ============================================================

@app.get("/works")
def get_works(
    state: str | None = None,
    district: str | None = None,
    constituency: str | None = None,
    category: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0
):

    # --------------------------------------------------------
    # Validate pagination
    # --------------------------------------------------------

    if limit < 1 or limit > 500:

        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500"
        )

    if offset < 0:

        raise HTTPException(
            status_code=400,
            detail="offset cannot be negative"
        )

    # --------------------------------------------------------
    # Load cached dataset
    # --------------------------------------------------------

    works = list(load_works())

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

    if state:

        works = [
            work
            for work in works
            if work.get("STATE", "").lower()
            == state.lower()
        ]

    if district:

        works = [
            work
            for work in works
            if work.get("DISTRICT", "").lower()
            == district.lower()
        ]

    if constituency:

        works = [
            work
            for work in works
            if work.get("CONSTITUENCY", "").lower()
            == constituency.lower()
        ]

    if category:

        works = [
            work
            for work in works
            if work.get("CATEGORY", "").lower()
            == category.lower()
        ]

    if status:

        works = [
            work
            for work in works
            if work.get("STATUS", "").lower()
            == status.lower()
        ]

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    total = len(works)

    paginated_works = works[
        offset:offset + limit
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "works": paginated_works
    }


# ============================================================
# GET ONE WORK
# ============================================================

@app.get("/works/{work_id}")
def get_work(work_id: str):

    works = load_works()

    for work in works:

        if work.get("PROJECT_ID") == work_id:

            return work

    raise HTTPException(
        status_code=404,
        detail="Work not found"
    )


# ============================================================
# FILTER OPTIONS
# ============================================================

@app.get("/filters")
def get_filters():

    works = load_works()

    states = sorted({
        work.get("STATE")
        for work in works
        if work.get("STATE")
    })

    districts = sorted({
        work.get("DISTRICT")
        for work in works
        if work.get("DISTRICT")
    })

    constituencies = sorted({
        work.get("CONSTITUENCY")
        for work in works
        if work.get("CONSTITUENCY")
    })

    categories = sorted({
        work.get("CATEGORY")
        for work in works
        if work.get("CATEGORY")
    })

    statuses = sorted({
        work.get("STATUS")
        for work in works
        if work.get("STATUS")
    })

    return {
        "states": states,
        "districts": districts,
        "constituencies": constituencies,
        "categories": categories,
        "statuses": statuses
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard")
def get_dashboard():

    works = load_works()

    # --------------------------------------------------------
    # Total projects
    # --------------------------------------------------------

    total_projects = len(works)

    # --------------------------------------------------------
    # Total allocation
    # --------------------------------------------------------

    total_allocation = sum(
        get_amount(work)
        for work in works
    )

    # --------------------------------------------------------
    # Projects by status
    # --------------------------------------------------------

    status_counts = Counter(
        work.get("STATUS", "Unknown")
        for work in works
    )

    # --------------------------------------------------------
    # Projects by category
    # --------------------------------------------------------

    category_counts = Counter(
        work.get("CATEGORY", "Unknown")
        for work in works
    )

    # --------------------------------------------------------
    # Projects by state
    # --------------------------------------------------------

    state_counts = Counter(
        work.get("STATE", "Unknown")
        for work in works
    )

    return {
        "total_projects": total_projects,
        "total_allocation_amount": total_allocation,
        "projects_by_status": dict(status_counts),
        "projects_by_category": dict(category_counts),
        "projects_by_state": dict(state_counts)
    }


# ============================================================
# ANOMALY SUMMARY
# ============================================================

@app.get("/anomalies/summary")
def get_anomaly_summary():

    anomalies = get_cached_anomalies()

    # --------------------------------------------------------
    # Count anomaly types
    # --------------------------------------------------------

    type_counts = Counter(
        anomaly.get(
            "anomaly_type",
            "unknown"
        )
        for anomaly in anomalies
    )

    # --------------------------------------------------------
    # Count severity
    # --------------------------------------------------------

    severity_counts = Counter(
        anomaly.get(
            "severity",
            "Unknown"
        )
        for anomaly in anomalies
    )

    # --------------------------------------------------------
    # Count detectors
    # --------------------------------------------------------

    detector_counts = Counter(
        anomaly.get(
            "detector",
            "Unknown"
        )
        for anomaly in anomalies
    )

    # --------------------------------------------------------
    # Pattern score statistics
    # --------------------------------------------------------

    pattern_scores = [
        anomaly.get("pattern_score")
        for anomaly in anomalies
        if isinstance(
            anomaly.get("pattern_score"),
            (int, float)
        )
    ]

    # --------------------------------------------------------
    # Extreme allocation statistics
    # --------------------------------------------------------

    extreme_allocations = [
        anomaly
        for anomaly in anomalies
        if anomaly.get("anomaly_type")
        == "extreme_allocation"
    ]

    repeated_patterns = [
        anomaly
        for anomaly in anomalies
        if anomaly.get("anomaly_type")
        == "repeated_amount_pattern"
    ]

    # --------------------------------------------------------
    # Return summary
    # --------------------------------------------------------

    return {

        "total_anomalies": len(anomalies),

        "anomalies_by_type": dict(
            type_counts
        ),

        "anomalies_by_severity": dict(
            severity_counts
        ),

        "anomalies_by_detector": dict(
            detector_counts
        ),

        "extreme_allocation_count": len(
            extreme_allocations
        ),

        "repeated_amount_pattern_count": len(
            repeated_patterns
        ),

        "average_pattern_score": (
            round(
                sum(pattern_scores)
                / len(pattern_scores),
                2
            )
            if pattern_scores
            else 0
        ),

        "maximum_pattern_score": (
            max(pattern_scores)
            if pattern_scores
            else 0
        ),

        "disclaimer": (
            "Anomalies indicate statistical irregularities "
            "and require verification; they do not prove fraud."
        )
    }


# ============================================================
# ANOMALIES
# ============================================================

@app.get("/anomalies")
def get_anomalies(
    anomaly_type: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0
):

    # --------------------------------------------------------
    # Validate pagination
    # --------------------------------------------------------

    if limit < 1 or limit > 500:

        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500"
        )

    if offset < 0:

        raise HTTPException(
            status_code=400,
            detail="offset cannot be negative"
        )

    # --------------------------------------------------------
    # Get cached anomalies
    # --------------------------------------------------------

    anomalies = list(
        get_cached_anomalies()
    )

    # --------------------------------------------------------
    # Filter by anomaly type
    # --------------------------------------------------------

    if anomaly_type:

        anomalies = [
            anomaly
            for anomaly in anomalies
            if anomaly.get(
                "anomaly_type",
                ""
            ).lower()
            == anomaly_type.lower()
        ]

    # --------------------------------------------------------
    # Filter by severity
    # --------------------------------------------------------

    if severity:

        anomalies = [
            anomaly
            for anomaly in anomalies
            if anomaly.get(
                "severity",
                ""
            ).lower()
            == severity.lower()
        ]

    # --------------------------------------------------------
    # Total after filtering
    # --------------------------------------------------------

    total = len(anomalies)

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    paginated_anomalies = anomalies[
        offset:offset + limit
    ]

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "total": total,

        "limit": limit,

        "offset": offset,

        "disclaimer": (
            "Anomalies indicate statistical irregularities "
            "and require verification; they do not prove fraud."
        ),

        "anomalies": paginated_anomalies
    }


# ============================================================
# REFRESH DATA
# ============================================================

@app.post("/refresh")
def refresh():

    result = refresh_data()

    return {
        "message": "Dataset and anomaly results refreshed successfully.",
        **result
    }