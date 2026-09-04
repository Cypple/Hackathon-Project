from collections import Counter
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.services.anomaly_detector import detect_anomalies
from app.api.v1.routes.projects import load_works


router = APIRouter()


@lru_cache(maxsize=1)
def get_cached_anomalies():
    works = list(load_works())
    return tuple(detect_anomalies(works))


@router.get("/anomalies")
def get_anomalies(
    anomaly_type: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
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

    anomalies = list(get_cached_anomalies())

    if anomaly_type:
        anomalies = [
            anomaly
            for anomaly in anomalies
            if anomaly.get("anomaly_type", "").lower()
            == anomaly_type.lower()
        ]

    if severity:
        anomalies = [
            anomaly
            for anomaly in anomalies
            if anomaly.get("severity", "").lower()
            == severity.lower()
        ]

    total = len(anomalies)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "disclaimer": (
            "Anomalies indicate statistical irregularities "
            "and require verification; they do not prove fraud."
        ),
        "anomalies": anomalies[offset:offset + limit],
    }


@router.get("/anomalies/summary")
def get_anomaly_summary():

    anomalies = get_cached_anomalies()

    type_counts = Counter(
        anomaly.get("anomaly_type", "unknown")
        for anomaly in anomalies
    )

    severity_counts = Counter(
        anomaly.get("severity", "Unknown")
        for anomaly in anomalies
    )

    detector_counts = Counter(
        anomaly.get("detector", "Unknown")
        for anomaly in anomalies
    )

    pattern_scores = [
        anomaly.get("pattern_score")
        for anomaly in anomalies
        if isinstance(
            anomaly.get("pattern_score"),
            (int, float)
        )
    ]

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

    return {
        "total_anomalies": len(anomalies),
        "anomalies_by_type": dict(type_counts),
        "anomalies_by_severity": dict(severity_counts),
        "anomalies_by_detector": dict(detector_counts),
        "extreme_allocation_count": len(extreme_allocations),
        "repeated_amount_pattern_count": len(repeated_patterns),
        "average_pattern_score": (
            round(
                sum(pattern_scores) / len(pattern_scores),
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
        ),
    }


@router.post("/refresh")
def refresh():

    if hasattr(load_works, "cache_clear"):
        load_works.cache_clear()
    get_cached_anomalies.cache_clear()

    works = load_works()
    anomalies = get_cached_anomalies()

    return {
        "message": "Dataset and anomaly results refreshed successfully.",
        "projects_loaded": len(works),
        "anomalies_detected": len(anomalies),
    }