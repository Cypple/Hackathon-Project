"""Explainable anomaly detection for the MPLADS prototype.

Implements Team A's two anomaly families:
1. Extreme allocation compared with a peer group.
2. Repeated amount patterns, with a strong exact-pattern detector and a
   broader same-MP/same-work/same-amount detector.

The detector reports statistical irregularities that require verification.
It does not label records as fraud.
"""

from collections import defaultdict
from statistics import median
import math
import re


# Team A specified a threshold but did not provide its numeric value.
# 3.5 is kept as a named constant so it is easy to change later.
ROBUST_Z_THRESHOLD = 3.5
MIN_PEER_GROUP_SIZE = 5


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _work_type(work):
    """Remove the dataset's leading work/reference code from WORK."""
    text = _norm(work)
    if " - " in text:
        return text.split(" - ", 1)[1].strip()
    return text


def _amount(row):
    try:
        return float(row.get("ALLOCATION_AMOUNT_NUM") or row.get("ALLOCATION AMOUNT") or 0)
    except (TypeError, ValueError):
        return 0.0


def _date(row):
    return _norm(row.get("RECOMMENDED DATE"))


def _location(row):
    # Use the most specific available location components.
    parts = []
    for field in ("CITY", "WARD", "BLOCK", "VILLAGE"):
        value = _norm(row.get(field))
        if value:
            parts.append(f"{field.lower()}={value}")
    return " | ".join(parts)


def _robust_z(value, values):
    med = median(values)
    deviations = [abs(v - med) for v in values]
    mad = median(deviations)
    if mad == 0:
        return None
    return 0.6745 * (value - med) / mad


def _peer_key(row):
    # Comparable projects: same state + same broad category.
    return (_norm(row.get("STATE")), _norm(row.get("CATEGORY")))


def _score_repeated_pattern(row_count, different_locations, same_date):
    score = 25 + 25 + 20  # same MP + same work type + same amount
    if same_date:
        score += 15
    if different_locations >= 3:
        score += 15
    return min(score, 100)


def _pattern_strength(count):
    if count >= 6:
        return "Very high"
    if count >= 4:
        return "High"
    if count == 3:
        return "Medium"
    return "Low"


def detect_anomalies(works):
    """Return a list of explainable anomaly records for the supplied works."""
    rows = [dict(w) for w in works]

    # -----------------------------
    # Detector 1: Extreme allocation
    # -----------------------------
    peer_values = defaultdict(list)
    for row in rows:
        amount = _amount(row)
        key = _peer_key(row)
        if amount > 0 and all(key):
            peer_values[key].append(amount)

    anomalies = []
    allocation_by_id = {}

    for row in rows:
        amount = _amount(row)
        key = _peer_key(row)
        values = peer_values.get(key, [])
        if amount <= 0 or len(values) < MIN_PEER_GROUP_SIZE:
            continue

        peer_median = median(values)
        if peer_median <= 0:
            continue

        ratio = amount / peer_median
        sorted_values = sorted(values)
        percentile = 100.0 * sum(v <= amount for v in sorted_values) / len(sorted_values)
        robust_z = _robust_z(amount, values)

        evidence = {
            "ratio_ge_4x": ratio >= 4,
            "percentile_ge_99": percentile >= 99,
            "robust_z_ge_threshold": robust_z is not None and robust_z >= ROBUST_Z_THRESHOLD,
        }
        strong = sum(evidence.values()) >= 2

        if ratio >= 3 or strong:
            result = {
                "project_id": row.get("PROJECT_ID"),
                "anomaly_type": "extreme_allocation",
                "result": "Requires verification",
                "severity": "Strong anomaly" if strong else "Review flag",
                "allocation_amount": amount,
                "peer_group": {
                    "state": row.get("STATE"),
                    "category": row.get("CATEGORY"),
                    "size": len(values),
                },
                "peer_median": peer_median,
                "peer_median_ratio": round(ratio, 4),
                "percentile": round(percentile, 4),
                "robust_z_score": round(robust_z, 4) if robust_z is not None else None,
                "strong_anomaly_evidence": evidence,
                "message": "Allocation is unusually high compared with comparable projects.",
            }
            anomalies.append(result)
            allocation_by_id[row.get("PROJECT_ID")] = result

    # ---------------------------------
    # Detector 2A: exact repeated pattern
    # ---------------------------------
    exact_groups = defaultdict(list)
    for row in rows:
        amount = _amount(row)
        key = (
            _norm(row.get("MP NAME")),
            _work_type(row.get("WORK")),
            _date(row),
            amount,
        )
        if key[0] and key[1] and key[2] and amount > 0:
            exact_groups[key].append(row)

    repeated_by_id = {}
    for key, group in exact_groups.items():
        if len(group) < 2:
            continue

        locations = {_location(row) for row in group if _location(row)}
        score = _score_repeated_pattern(len(group), len(locations), True)
        strength = _pattern_strength(len(group))

        for row in group:
            result = {
                "project_id": row.get("PROJECT_ID"),
                "anomaly_type": "repeated_amount_pattern",
                "detector": "A_strong_pattern",
                "result": "Requires verification",
                "severity": strength,
                "pattern_score": score,
                "matching_projects": len(group),
                "different_locations": len(locations),
                "same_mp": True,
                "same_work_type": True,
                "same_amount": True,
                "same_recommendation_date": True,
                "mp": row.get("MP NAME"),
                "work_type": _work_type(row.get("WORK")),
                "recommendation_date": row.get("RECOMMENDED DATE"),
                "allocation_amount": _amount(row),
                "locations": sorted(locations),
                "message": "The same MP repeatedly recommended the same work type for the same amount on the same date across multiple locations.",
            }
            anomalies.append(result)
            repeated_by_id.setdefault(row.get("PROJECT_ID"), []).append(result)

    # ----------------------------------
    # Detector 2B: broader repeated pattern
    # ----------------------------------
    broad_groups = defaultdict(list)
    for row in rows:
        amount = _amount(row)
        key = (_norm(row.get("MP NAME")), _work_type(row.get("WORK")), amount)
        if key[0] and key[1] and amount > 0:
            broad_groups[key].append(row)

    # Avoid duplicating rows already covered by the exact detector.
    exact_ids = {r.get("project_id") for r in anomalies if r["anomaly_type"] == "repeated_amount_pattern" and r.get("detector") == "A_strong_pattern"}

    for key, group in broad_groups.items():
        if len(group) < 2:
            continue

        locations = {_location(row) for row in group if _location(row)}
        dates = {_date(row) for row in group if _date(row)}
        same_date = len(dates) == 1
        score = _score_repeated_pattern(len(group), len(locations), same_date)
        strength = _pattern_strength(len(group))

        for row in group:
            pid = row.get("PROJECT_ID")
            if pid in exact_ids:
                continue
            result = {
                "project_id": pid,
                "anomaly_type": "repeated_amount_pattern",
                "detector": "B_broader_pattern",
                "result": "Requires verification",
                "severity": strength,
                "pattern_score": score,
                "matching_projects": len(group),
                "different_locations": len(locations),
                "same_mp": True,
                "same_work_type": True,
                "same_amount": True,
                "same_recommendation_date": same_date,
                "mp": row.get("MP NAME"),
                "work_type": _work_type(row.get("WORK")),
                "recommendation_date": row.get("RECOMMENDED DATE"),
                "allocation_amount": _amount(row),
                "locations": sorted(locations),
                "message": "The same MP repeatedly recommended the same work type for exactly the same amount, even though dates may differ.",
            }
            anomalies.append(result)

    # Stable ordering: strongest exact patterns first, then extreme allocation.
    severity_order = {"Very high": 5, "High": 4, "Strong anomaly": 4, "Medium": 3, "Review flag": 3, "Low": 2}
    anomalies.sort(
        key=lambda x: (
            severity_order.get(x.get("severity"), 0),
            x.get("pattern_score", 0),
            x.get("peer_median_ratio", 0),
        ),
        reverse=True,
    )

    return anomalies
