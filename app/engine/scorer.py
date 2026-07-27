"""
Scoring module.

Converts rule evaluation results into a numeric security score (0-100),
a letter grade, and a count of critical failures.
"""

from __future__ import annotations

from typing import Dict, List


# Penalty deducted from 100 for each FAIL at the given severity level
_SEVERITY_PENALTIES: Dict[str, int] = {
    "critical": 30,
    "high": 20,
    "medium": 10,
    "low": 5,
}

# Grade thresholds — highest matching threshold wins
_GRADE_THRESHOLDS: List[tuple[int, str]] = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
]


def calculate_score(results: List[Dict[str, str]]) -> Dict[str, object]:
    """Calculate a security score from rule evaluation results.

    Scoring algorithm:
    - Start at **100**.
    - For every rule that **FAILed**, subtract the penalty for its severity:
      ``critical → -30``, ``high → -20``, ``medium → -10``, ``low → -5``.
    - Floor the score at **0**.

    Grade mapping:
    - ``A`` ≥ 90, ``B`` ≥ 80, ``C`` ≥ 70, ``D`` ≥ 60, ``F`` < 60.

    Args:
        results: List of result dicts as returned by
            :func:`app.engine.rules.evaluate_rules`.

    Returns:
        Dict with keys:

        - ``score`` (int): 0–100 numeric score.
        - ``grade`` (str): Letter grade A–F.
        - ``critical_failures`` (int): Number of critical-severity FAILs.
    """
    score = 100
    critical_failures = 0

    for result in results:
        if result["status"] != "FAIL":
            continue

        severity = result["severity"].lower()
        penalty = _SEVERITY_PENALTIES.get(severity, 0)
        score -= penalty

        if severity == "critical":
            critical_failures += 1

    score = max(0, score)
    grade = _letter_grade(score)

    return {
        "score": score,
        "grade": grade,
        "critical_failures": critical_failures,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _letter_grade(score: int) -> str:
    """Map a numeric score to a letter grade.

    Args:
        score: Integer score between 0 and 100.

    Returns:
        Letter grade string: ``"A"``, ``"B"``, ``"C"``, ``"D"``, or ``"F"``.
    """
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"
