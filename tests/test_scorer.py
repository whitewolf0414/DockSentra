"""
Unit tests for app.engine.scorer.

Tests cover:
- Perfect score (all PASSes)
- Zero score (enough critical failures)
- Exact penalty arithmetic for each severity
- Grade boundary conditions
- Critical-failure counting
- End-to-end scoring against both sample Dockerfiles
"""

from __future__ import annotations

import os

import pytest

from app.engine.parser import parse_dockerfile
from app.engine.rules import load_rules, evaluate_rules
from app.engine.scorer import calculate_score


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "sample")
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
RULES_YAML = os.path.abspath(os.path.join(CONFIG_DIR, "rules.yaml"))

GOOD_DOCKERFILE = os.path.abspath(os.path.join(SAMPLE_DIR, "Dockerfile.good"))
BAD_DOCKERFILE  = os.path.abspath(os.path.join(SAMPLE_DIR, "Dockerfile.bad"))


def _make_result(severity: str, status: str = "FAIL") -> dict:
    return {"id": f"test_{severity}", "description": "test", "severity": severity, "status": status}


# ── Tests: score arithmetic ───────────────────────────────────────────────────

class TestScoreArithmetic:
    def test_all_pass_returns_100(self):
        results = [
            _make_result("critical", "PASS"),
            _make_result("high", "PASS"),
            _make_result("medium", "PASS"),
        ]
        data = calculate_score(results)
        assert data["score"] == 100

    def test_single_critical_fail_subtracts_30(self):
        results = [_make_result("critical", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 70

    def test_single_high_fail_subtracts_20(self):
        results = [_make_result("high", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 80

    def test_single_medium_fail_subtracts_10(self):
        results = [_make_result("medium", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 90

    def test_single_low_fail_subtracts_5(self):
        results = [_make_result("low", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 95

    def test_multiple_severities_cumulative(self):
        # critical(-30) + high(-20) + medium(-10) + low(-5) = -65 → 35
        results = [
            _make_result("critical", "FAIL"),
            _make_result("high", "FAIL"),
            _make_result("medium", "FAIL"),
            _make_result("low", "FAIL"),
        ]
        data = calculate_score(results)
        assert data["score"] == 35

    def test_score_floors_at_zero(self):
        # 4 critical failures → -120, must floor at 0
        results = [_make_result("critical", "FAIL") for _ in range(4)]
        data = calculate_score(results)
        assert data["score"] == 0

    def test_empty_results_returns_100(self):
        data = calculate_score([])
        assert data["score"] == 100


# ── Tests: grades ─────────────────────────────────────────────────────────────

class TestGrades:
    """Verify grade boundaries exactly."""

    def test_grade_a_at_100(self):
        data = calculate_score([])
        assert data["grade"] == "A"

    def test_grade_a_at_90(self):
        # 2 medium fails → 100-10-10 = 80 → B; need 1 medium → 90 → A
        results = [_make_result("medium", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 90
        assert data["grade"] == "A"

    def test_grade_b_at_80(self):
        results = [_make_result("high", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 80
        assert data["grade"] == "B"

    def test_grade_c_at_70(self):
        # 1 critical(-30) = 70 → C
        results = [_make_result("critical", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 70
        assert data["grade"] == "C"

    def test_grade_d_at_60(self):
        # 1 critical(-30) + 1 medium(-10) = 60 → D
        results = [_make_result("critical", "FAIL"), _make_result("medium", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 60
        assert data["grade"] == "D"

    def test_grade_f_below_60(self):
        # 2 critical(-60) = 40 → F
        results = [_make_result("critical", "FAIL"), _make_result("critical", "FAIL")]
        data = calculate_score(results)
        assert data["score"] == 40
        assert data["grade"] == "F"

    def test_grade_f_at_zero(self):
        results = [_make_result("critical", "FAIL") for _ in range(10)]
        data = calculate_score(results)
        assert data["score"] == 0
        assert data["grade"] == "F"


# ── Tests: critical_failures count ───────────────────────────────────────────

class TestCriticalFailures:
    def test_no_critical_failures(self):
        results = [_make_result("high", "FAIL"), _make_result("medium", "FAIL")]
        data = calculate_score(results)
        assert data["critical_failures"] == 0

    def test_one_critical_failure(self):
        results = [_make_result("critical", "FAIL"), _make_result("high", "PASS")]
        data = calculate_score(results)
        assert data["critical_failures"] == 1

    def test_multiple_critical_failures(self):
        results = [_make_result("critical", "FAIL") for _ in range(3)]
        data = calculate_score(results)
        assert data["critical_failures"] == 3

    def test_critical_pass_not_counted(self):
        results = [_make_result("critical", "PASS")]
        data = calculate_score(results)
        assert data["critical_failures"] == 0


# ── Tests: return structure ───────────────────────────────────────────────────

class TestReturnStructure:
    def test_returns_required_keys(self):
        data = calculate_score([])
        assert set(data.keys()) == {"score", "grade", "critical_failures"}

    def test_score_is_int(self):
        data = calculate_score([_make_result("high", "FAIL")])
        assert isinstance(data["score"], int)

    def test_grade_is_string(self):
        data = calculate_score([])
        assert isinstance(data["grade"], str)


# ── Tests: end-to-end scoring ─────────────────────────────────────────────────

class TestEndToEndScoring:
    def test_good_dockerfile_scores_100(self):
        instructions = parse_dockerfile(GOOD_DOCKERFILE)
        rules = load_rules(RULES_YAML)
        results = evaluate_rules(instructions, rules)
        data = calculate_score(results)
        assert data["score"] == 100
        assert data["grade"] == "A"
        assert data["critical_failures"] == 0

    def test_bad_dockerfile_score_math(self):
        # Expected failures: critical×2(-60) + high×1(-20) + medium×1(-10) + low×1(-5) = -95 → 5
        instructions = parse_dockerfile(BAD_DOCKERFILE)
        rules = load_rules(RULES_YAML)
        results = evaluate_rules(instructions, rules)
        data = calculate_score(results)
        assert data["score"] == 5
        assert data["grade"] == "F"
        assert data["critical_failures"] == 2

    def test_bad_dockerfile_has_critical_failures(self):
        instructions = parse_dockerfile(BAD_DOCKERFILE)
        rules = load_rules(RULES_YAML)
        results = evaluate_rules(instructions, rules)
        data = calculate_score(results)
        assert data["critical_failures"] > 0
