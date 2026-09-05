"""Explainable anomaly detection for the MPLADS Sentinel prototype.

Implements Team A's two anomaly families:

1. Extreme allocation compared with a peer group.
2. Repeated amount patterns:
   - Strong exact pattern
   - Broader same-MP / same-work / same-amount pattern

The detector reports statistical irregularities that require verification.
It does not label records as fraud.
"""

from collections import defaultdict
from statistics import median
import math
import re


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

# Team A specified a robust-z based condition but did not
# provide a numeric threshold.
ROBUST_Z_THRESHOLD = 3.5

# Minimum number of comparable projects required for an
# extreme-allocation peer comparison.
MIN_PEER_GROUP_SIZE = 5


# ---------------------------------------------------------
# NORMALIZATION HELPERS
# ---------------------------------------------------------

def _norm(value):
    """Normalize text for reliable comparisons."""
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower()
    )


def _work_type(work):
    """
    Extract the actual work type from the WORK field.

    Example:
        'ABC123 - Construction of Road'
    becomes:
        'construction of road'
    """
    text = _norm(work)

    if " - " in text:
        return text.split(" - ", 1)[1].strip()

    return text


def _amount(row):
    """Return allocation amount as a float."""
    try:
        value = (
            row.get("ALLOCATION_AMOUNT_NUM")
            or row.get("ALLOCATION AMOUNT")
            or 0
        )

        return float(
            str(value)
            .replace(",", "")
            .strip()
        )

    except (TypeError, ValueError):
        return 0.0


def _date(row):
    """Normalize recommendation date."""
    return _norm(
        row.get("RECOMMENDED DATE")
    )


def _location(row):
    """
    Build a normalized location identifier using the most
    specific available location fields.
    """

    parts = []

    for field in (
        "CITY",
        "WARD",
        "BLOCK",
        "VILLAGE",
    ):
        value = _norm(row.get(field))

        if value:
            parts.append(
                f"{field.lower()}={value}"
            )

    return " | ".join(parts)


# ---------------------------------------------------------
# ROBUST STATISTICS
# ---------------------------------------------------------

def _robust_z(value, values):
    """
    Calculate a robust z-score using median and MAD.

    Formula:
        0.6745 * (value - median) / MAD

    Returns None if MAD is zero.
    """

    if not values:
        return None

    med = median(values)

    deviations = [
        abs(v - med)
        for v in values
    ]

    mad = median(deviations)

    if mad == 0:
        return None

    return (
        0.6745
        * (value - med)
        / mad
    )


# ---------------------------------------------------------
# PEER GROUP
# ---------------------------------------------------------

def _peer_key(row):
    """
    Comparable projects are grouped by:

        STATE + CATEGORY
    """

    return (
        _norm(row.get("STATE")),
        _norm(row.get("CATEGORY")),
    )


# ---------------------------------------------------------
# REPEATED PATTERN SCORING
# ---------------------------------------------------------

def _score_repeated_pattern(
    row_count,
    different_locations,
    same_date,
):
    """
    Team A pattern score:

        Same MP          = 25
        Same work type   = 25
        Same amount      = 20
        Same date        = 15
        3+ locations     = 15

    Maximum = 100
    """

    # Same MP + same work type + same amount
    score = 25 + 25 + 20

    # Same recommendation date
    if same_date:
        score += 15

    # Three or more different locations
    if different_locations >= 3:
        score += 15

    return min(score, 100)


def _pattern_strength(count):
    """
    Pattern strength based on number of matching projects.
    """

    if count >= 6:
        return "Very high"

    if count >= 4:
        return "High"

    if count == 3:
        return "Medium"

    return "Low"


# ---------------------------------------------------------
# MAIN DETECTOR
# ---------------------------------------------------------

def detect_anomalies(works):
    """
    Return explainable anomaly records for the supplied
    MPLADS projects.
    """

    # Make independent dictionaries so that we never mutate
    # the original dataset.
    rows = [
        dict(work)
        for work in works
    ]

    anomalies = []

    # =====================================================
    # DETECTOR 1
    # EXTREME ALLOCATION
    # =====================================================

    peer_values = defaultdict(list)

    # Build peer groups.
    for row in rows:

        amount = _amount(row)
        key = _peer_key(row)

        # Only positive allocations with valid peer fields.
        if (
            amount > 0
            and all(key)
        ):
            peer_values[key].append(amount)

    # Check each project against its peer group.
    for row in rows:

        amount = _amount(row)
        key = _peer_key(row)

        values = peer_values.get(
            key,
            []
        )

        # Not enough peers for a meaningful comparison.
        if (
            amount <= 0
            or len(values) < MIN_PEER_GROUP_SIZE
        ):
            continue

        peer_median = median(values)

        if peer_median <= 0:
            continue

        # -------------------------------------------------
        # Ratio
        # -------------------------------------------------

        ratio = (
            amount
            / peer_median
        )

        # -------------------------------------------------
        # Percentile
        # -------------------------------------------------

        sorted_values = sorted(values)

        percentile = (
            100.0
            * sum(
                value <= amount
                for value in sorted_values
            )
            / len(sorted_values)
        )

        # -------------------------------------------------
        # Robust Z
        # -------------------------------------------------

        robust_z = _robust_z(
            amount,
            values
        )

        # -------------------------------------------------
        # Evidence conditions
        # -------------------------------------------------

        evidence = {
            "ratio_ge_4x": ratio >= 4,
            "percentile_ge_99": percentile >= 99,
            "robust_z_ge_threshold": (
                robust_z is not None
                and robust_z >= ROBUST_Z_THRESHOLD
            ),
        }

        # Strong anomaly requires at least
        # two independent evidence conditions.
        strong = (
            sum(evidence.values())
            >= 2
        )

        # Team A also flags projects where allocation
        # is at least 3x the peer median.
        if ratio >= 3 or strong:

            result = {
                "project_id": row.get(
                    "PROJECT_ID"
                ),

                "anomaly_type":
                    "extreme_allocation",

                "result":
                    "Requires verification",

                "severity":
                    (
                        "Strong anomaly"
                        if strong
                        else "Review flag"
                    ),

                "allocation_amount":
                    amount,

                "peer_group": {
                    "state":
                        row.get("STATE"),

                    "category":
                        row.get("CATEGORY"),

                    "size":
                        len(values),
                },

                "peer_median":
                    peer_median,

                "peer_median_ratio":
                    round(
                        ratio,
                        4
                    ),

                "percentile":
                    round(
                        percentile,
                        4
                    ),

                "robust_z_score":
                    (
                        round(
                            robust_z,
                            4
                        )
                        if robust_z is not None
                        else None
                    ),

                "strong_anomaly_evidence":
                    evidence,

                "message":
                    (
                        "Allocation is unusually high "
                        "compared with comparable projects."
                    ),
            }

            anomalies.append(result)

    # =====================================================
    # DETECTOR 2A
    # STRONG EXACT REPEATED PATTERN
    # =====================================================

    exact_groups = defaultdict(list)

    for row in rows:

        amount = _amount(row)

        key = (
            _norm(
                row.get("MP NAME")
            ),

            _work_type(
                row.get("WORK")
            ),

            _date(row),

            amount,
        )

        # All four components must exist.
        if (
            key[0]
            and key[1]
            and key[2]
            and amount > 0
        ):
            exact_groups[key].append(row)

    # Process exact groups.
    for key, group in exact_groups.items():

        # A repeated pattern needs at least 2 projects.
        if len(group) < 2:
            continue

        locations = {
            _location(row)
            for row in group
            if _location(row)
        }

        score = _score_repeated_pattern(
            len(group),
            len(locations),
            True,
        )

        strength = _pattern_strength(
            len(group)
        )

        for row in group:

            result = {
                "project_id":
                    row.get("PROJECT_ID"),

                "anomaly_type":
                    "repeated_amount_pattern",

                "detector":
                    "A_strong_pattern",

                "result":
                    "Requires verification",

                "severity":
                    strength,

                "pattern_score":
                    score,

                "matching_projects":
                    len(group),

                "different_locations":
                    len(locations),

                "same_mp":
                    True,

                "same_work_type":
                    True,

                "same_amount":
                    True,

                "same_recommendation_date":
                    True,

                "mp":
                    row.get("MP NAME"),

                "work_type":
                    _work_type(
                        row.get("WORK")
                    ),

                "recommendation_date":
                    row.get(
                        "RECOMMENDED DATE"
                    ),

                "allocation_amount":
                    _amount(row),

                "locations":
                    sorted(locations),

                "message":
                    (
                        "The same MP repeatedly "
                        "recommended the same work type "
                        "for the same amount on the same "
                        "date across multiple locations."
                    ),
            }

            anomalies.append(result)

    # =====================================================
    # DETECTOR 2B
    # BROADER REPEATED PATTERN
    # =====================================================

    broad_groups = defaultdict(list)

    for row in rows:

        amount = _amount(row)

        key = (
            _norm(
                row.get("MP NAME")
            ),

            _work_type(
                row.get("WORK")
            ),

            amount,
        )

        if (
            key[0]
            and key[1]
            and amount > 0
        ):
            broad_groups[key].append(row)

    # -----------------------------------------------------
    # Identify projects already detected by the exact
    # pattern detector.
    # -----------------------------------------------------

    exact_ids = {
        item.get("project_id")

        for item in anomalies

        if (
            item.get("anomaly_type")
            == "repeated_amount_pattern"

            and item.get("detector")
            == "A_strong_pattern"
        )
    }

    # -----------------------------------------------------
    # Process broader groups.
    # -----------------------------------------------------

    for key, group in broad_groups.items():

        if len(group) < 2:
            continue

        locations = {
            _location(row)
            for row in group
            if _location(row)
        }

        dates = {
            _date(row)
            for row in group
            if _date(row)
        }

        same_date = (
            len(dates) == 1
        )

        score = _score_repeated_pattern(
            len(group),
            len(locations),
            same_date,
        )

        strength = _pattern_strength(
            len(group)
        )

        for row in group:

            pid = row.get(
                "PROJECT_ID"
            )

            # Do not create a duplicate anomaly
            # when the project was already detected
            # by the stronger exact detector.
            if pid in exact_ids:
                continue

            result = {
                "project_id":
                    pid,

                "anomaly_type":
                    "repeated_amount_pattern",

                "detector":
                    "B_broader_pattern",

                "result":
                    "Requires verification",

                "severity":
                    strength,

                "pattern_score":
                    score,

                "matching_projects":
                    len(group),

                "different_locations":
                    len(locations),

                "same_mp":
                    True,

                "same_work_type":
                    True,

                "same_amount":
                    True,

                "same_recommendation_date":
                    same_date,

                "mp":
                    row.get("MP NAME"),

                "work_type":
                    _work_type(
                        row.get("WORK")
                    ),

                "recommendation_date":
                    row.get(
                        "RECOMMENDED DATE"
                    ),

                "allocation_amount":
                    _amount(row),

                "locations":
                    sorted(locations),

                "message":
                    (
                        "The same MP repeatedly "
                        "recommended the same work type "
                        "for exactly the same amount, "
                        "even though dates may differ."
                    ),
            }

            anomalies.append(result)

    # =====================================================
    # STABLE SORTING
    # =====================================================

    severity_order = {
        "Very high": 5,
        "High": 4,
        "Strong anomaly": 4,
        "Medium": 3,
        "Review flag": 3,
        "Low": 2,
    }

    anomalies.sort(
        key=lambda item: (
            severity_order.get(
                item.get("severity"),
                0,
            ),

            item.get(
                "pattern_score",
                0,
            ),

            item.get(
                "peer_median_ratio",
                0,
            ),
        ),

        reverse=True,
    )

    return anomalies