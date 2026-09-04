from fastapi import APIRouter, HTTPException
import csv
import os

router = APIRouter()


from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[4] / "data" / "sanctioned_mplads_projects.csv"


# Load data from CSV
@lru_cache(maxsize=1)
def load_works():
    with open(DATA_FILE, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return tuple(reader)


# Convert amount to number
def get_amount(work):
    value = work.get("ALLOCATION AMOUNT", "0")

    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


# Home endpoint
@router.get("/")
def home():
    return {
        "message": "MPLADS Backend is running!"
    }


# Works endpoint with filters and pagination
@router.get("/works")
def get_works(
    state: str | None = None,
    district: str | None = None,
    constituency: str | None = None,
    category: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0
):
    works = load_works()

    # Filters
    if state:
        works = [
            work for work in works
            if work.get("STATE", "").lower() == state.lower()
        ]

    if district:
        works = [
            work for work in works
            if work.get("DISTRICT", "").lower() == district.lower()
        ]

    if constituency:
        works = [
            work for work in works
            if work.get("CONSTITUENCY", "").lower() == constituency.lower()
        ]

    if category:
        works = [
            work for work in works
            if work.get("CATEGORY", "").lower() == category.lower()
        ]

    if status:
        works = [
            work for work in works
            if work.get("STATUS", "").lower() == status.lower()
        ]

    # Pagination
    total = len(works)

    paginated_works = works[offset:offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "works": paginated_works
    }


# Get one specific work
@router.get("/works/{work_id}")
def get_work(work_id: str):

    works = load_works()

    for work in works:
        if work.get("PROJECT_ID") == work_id:
            return work

    raise HTTPException(
        status_code=404,
        detail="Work not found"
    )


# Get available filter options
@router.get("/filters")
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


# Dashboard summary
@router.get("/dashboard")
def get_dashboard():

    works = load_works()

    # Total projects
    total_projects = len(works)

    # Total allocation amount
    total_allocation = sum(
        get_amount(work)
        for work in works
    )

    # Projects by status
    status_counts = {}

    for work in works:
        status = work.get("STATUS", "Unknown")

        if status not in status_counts:
            status_counts[status] = 0

        status_counts[status] += 1

    # Projects by category
    category_counts = {}

    for work in works:
        category = work.get("CATEGORY", "Unknown")

        if category not in category_counts:
            category_counts[category] = 0

        category_counts[category] += 1

    # Projects by state
    state_counts = {}

    for work in works:
        state = work.get("STATE", "Unknown")

        if state not in state_counts:
            state_counts[state] = 0

        state_counts[state] += 1

    return {
        "total_projects": total_projects,
        "total_allocation_amount": total_allocation,
        "projects_by_status": status_counts,
        "projects_by_category": category_counts,
        "projects_by_state": state_counts
    }