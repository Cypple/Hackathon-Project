from pathlib import Path
from functools import lru_cache
import importlib.util
import math

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "sanctioned_mplads_projects.csv"
)

FRONTEND_DIR = (
    BASE_DIR.parent
    / "frontend"
    / "anomaly"
)

DETECTOR_PATH = BASE_DIR / "anomaly_detector.py"


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="MPLADS Sentinel API",
    version="1.0.0",
    description="AI-assisted MPLADS monitoring and early-warning system",
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
# FRONTEND
# ============================================================

if FRONTEND_DIR.exists():
    app.mount(
        "/ui/assets",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="ui-assets",
    )


# ============================================================
# ANOMALY DETECTOR
# ============================================================

def load_detector():

    if not DETECTOR_PATH.exists():
        raise FileNotFoundError(
            f"anomaly_detector.py not found at: {DETECTOR_PATH}"
        )

    spec = importlib.util.spec_from_file_location(
        "mplads_anomaly_detector",
        DETECTOR_PATH,
    )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    if not hasattr(module, "detect_anomalies"):
        raise AttributeError(
            "anomaly_detector.py must contain "
            "detect_anomalies(works)"
        )

    return module.detect_anomalies


# ============================================================
# DATA
# ============================================================

@lru_cache(maxsize=1)
def load_dataframe():

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"CSV not found at: {DATA_PATH}"
        )

    df = pd.read_csv(
        DATA_PATH,
        low_memory=False,
    )

    # Make sure allocation is numeric
    if "ALLOCATION_AMOUNT_NUM" in df.columns:

        df["ALLOCATION_AMOUNT_NUM"] = pd.to_numeric(
            df["ALLOCATION_AMOUNT_NUM"],
            errors="coerce",
        ).fillna(0)

    elif "ALLOCATION AMOUNT" in df.columns:

        df["ALLOCATION_AMOUNT_NUM"] = (
            df["ALLOCATION AMOUNT"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("₹", "", regex=False)
            .str.extract(
                r"([-+]?\d*\.?\d+)"
            )[0]
            .astype(float)
            .fillna(0)
        )

    return df


# ============================================================
# ANOMALIES
# ============================================================

@lru_cache(maxsize=1)
def anomaly_records():

    df = load_dataframe()

    detector = load_detector()

    records = detector(
        df.to_dict(orient="records")
    )

    return records


# ============================================================
# JSON HELPERS
# ============================================================

def clean_value(value):

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, float) and math.isnan(value):
        return None

    return value


def jsonable(value):

    if isinstance(value, dict):

        return {
            str(k): jsonable(v)
            for k, v in value.items()
        }

    if isinstance(value, list):

        return [
            jsonable(v)
            for v in value
        ]

    if hasattr(value, "item"):

        try:
            return value.item()
        except Exception:
            pass

    return clean_value(value)


def unique_values(df, column):

    if column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        values != ""
    ]

    return (
        values
        .drop_duplicates()
        .sort_values()
        .tolist()
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "MPLADS Sentinel API is running",
        "ui": "/ui/",
        "docs": "/docs",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    df = load_dataframe()

    return {
        "status": "healthy",
        "rows": int(len(df)),
        "columns": list(df.columns),
    }


# ============================================================
# UI
# ============================================================

@app.get("/ui/")
def ui():

    index_file = FRONTEND_DIR / "index.html"

    if not index_file.exists():

        return {
            "error": (
                f"Frontend not found at: "
                f"{index_file}"
            )
        }

    return FileResponse(index_file)


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/api/v1/dashboard")
def dashboard():

    df = load_dataframe()

    anomalies = anomaly_records()

    total_projects = int(len(df))

    total_allocation = float(
        df["ALLOCATION_AMOUNT_NUM"].sum()
    )

    states = unique_values(
        df,
        "STATE"
    )

    categories = unique_values(
        df,
        "CATEGORY"
    )

    statuses = unique_values(
        df,
        "STATUS"
    )

    if "STATE" in df.columns:

        state_counts = (
            df["STATE"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .head(10)
            .to_dict()
        )

    else:

        state_counts = {}

    if "CATEGORY" in df.columns:

        category_counts = (
            df["CATEGORY"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .head(10)
            .to_dict()
        )

    else:

        category_counts = {}

    if "STATUS" in df.columns:

        status_counts = (
            df["STATUS"]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .head(10)
            .to_dict()
        )

    else:

        status_counts = {}

    repeated = sum(
        1
        for item in anomalies
        if item.get(
            "anomaly_type"
        ) == "repeated_amount_pattern"
    )

    extreme = sum(
        1
        for item in anomalies
        if item.get(
            "anomaly_type"
        ) == "extreme_allocation"
    )

    return jsonable({

        "total_projects":
            total_projects,

        "total_allocation":
            total_allocation,

        "total_anomalies":
            len(anomalies),

        "detection_types":
            2,

        "states":
            len(states),

        "categories":
            len(categories),

        "statuses":
            len(statuses),

        "state_counts":
            state_counts,

        "category_counts":
            category_counts,

        "status_counts":
            status_counts,

        "repeated_patterns":
            repeated,

        "extreme_allocations":
            extreme,
    })


# ============================================================
# PROJECTS
# ============================================================

@app.get("/api/v1/works")
def works(

    limit: int = Query(
        25,
        ge=1,
        le=200
    ),

    offset: int = Query(
        0,
        ge=0
    ),

    search: str = Query(
        "",
        alias="search"
    ),

    state: str = "",

    category: str = "",

    status: str = "",
):

    df = load_dataframe().copy()

    # ----------------------------
    # SEARCH
    # ----------------------------

    if search.strip():

        query = search.strip().lower()

        mask = pd.Series(
            False,
            index=df.index
        )

        for column in [
            "MP NAME",
            "WORK",
            "CONSTITUENCY",
            "CITY",
            "PROJECT_ID",
        ]:

            if column in df.columns:

                mask = (
                    mask
                    |
                    df[column]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        query,
                        regex=False
                    )
                )

        df = df[mask]

    # ----------------------------
    # FILTERS
    # ----------------------------

    if state and state != "All":

        df = df[
            df["STATE"]
            .fillna("")
            .astype(str)
            == state
        ]

    if category and category != "All":

        df = df[
            df["CATEGORY"]
            .fillna("")
            .astype(str)
            == category
        ]

    if status and status != "All":

        df = df[
            df["STATUS"]
            .fillna("")
            .astype(str)
            == status
        ]

    total = int(len(df))

    page = df.iloc[
        offset:offset + limit
    ].copy()

    items = page.to_dict(
        orient="records"
    )

    return jsonable({

        "total":
            total,

        "limit":
            limit,

        "offset":
            offset,

        "items":
            items,
    })


# ============================================================
# FILTERS
# ============================================================

@app.get("/api/v1/filters")
def filters():

    df = load_dataframe()

    return jsonable({

        "states":
            unique_values(
                df,
                "STATE"
            ),

        "categories":
            unique_values(
                df,
                "CATEGORY"
            ),

        "statuses":
            unique_values(
                df,
                "STATUS"
            ),
    })


# ============================================================
# ANOMALY SUMMARY
# ============================================================

@app.get("/api/v1/anomalies/summary")
def anomaly_summary():

    anomalies = anomaly_records()

    repeated = [
        item
        for item in anomalies
        if item.get(
            "anomaly_type"
        ) == "repeated_amount_pattern"
    ]

    extreme = [
        item
        for item in anomalies
        if item.get(
            "anomaly_type"
        ) == "extreme_allocation"
    ]

    scores = [

        float(
            item.get(
                "pattern_score"
            )
        )

        for item in repeated

        if item.get(
            "pattern_score"
        ) is not None
    ]

    return jsonable({

        "total":
            len(anomalies),

        "total_anomalies":
            len(anomalies),

        "repeated_patterns":
            len(repeated),

        "repeated_amount_patterns":
            len(repeated),

        "extreme_allocations":
            len(extreme),

        "extreme_allocation":
            len(extreme),

        "max_pattern_score":
            max(scores)
            if scores
            else 0,
    })


# ============================================================
# ANOMALIES
# ============================================================

@app.get("/api/v1/anomalies")
def anomalies(

    limit: int = Query(
        50,
        ge=1,
        le=200
    ),

    offset: int = Query(
        0,
        ge=0
    ),

    anomaly_type: str = "",

    severity: str = "",
):

    records = list(
        anomaly_records()
    )

    # ----------------------------
    # TYPE FILTER
    # ----------------------------

    if (
        anomaly_type
        and anomaly_type != "All"
    ):

        records = [

            item
            for item in records

            if item.get(
                "anomaly_type"
            ) == anomaly_type
        ]

    # ----------------------------
    # SEVERITY FILTER
    # ----------------------------

    if (
        severity
        and severity != "All"
    ):

        records = [

            item
            for item in records

            if item.get(
                "severity"
            ) == severity
        ]

    total = len(records)

    page = records[
        offset:offset + limit
    ]

    return jsonable({

        "total":
            total,

        "limit":
            limit,

        "offset":
            offset,

        "items":
            page,
    })


# ============================================================
# REFRESH
# ============================================================

@app.post("/api/v1/refresh")
def refresh():

    load_dataframe.cache_clear()

    anomaly_records.cache_clear()

    df = load_dataframe()

    anomalies = anomaly_records()

    return {

        "status":
            "refreshed",

        "projects":
            len(df),

        "anomalies":
            len(anomalies),
    }