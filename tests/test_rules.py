"""
Unit tests for app.engine.rules.

Tests cover:
- load_rules: happy path and error conditions
- evaluate_rules: each of the 4 check types
- Full end-to-end evaluation against sample Dockerfiles
"""

from __future__ import annotations

import os

import pytest

from app.engine.parser import parse_dockerfile
from app.engine.rules import load_rules, evaluate_rules


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_DIR  = os.path.join(os.path.dirname(__file__), "..", "app", "sample")
CONFIG_DIR  = os.path.join(os.path.dirname(__file__), "..", "config")
RULES_YAML  = os.path.abspath(os.path.join(CONFIG_DIR, "rules.yaml"))

GOOD_DOCKERFILE = os.path.abspath(os.path.join(SAMPLE_DIR, "Dockerfile.good"))
BAD_DOCKERFILE  = os.path.abspath(os.path.join(SAMPLE_DIR, "Dockerfile.bad"))


def _results_by_id(results: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in results}


# ── Tests: load_rules ─────────────────────────────────────────────────────────

class TestLoadRules:
    def test_loads_yaml_returns_list(self):
        rules = load_rules(RULES_YAML)
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_each_rule_has_required_keys(self):
        rules = load_rules(RULES_YAML)
        required = {"id", "description", "severity", "check_type"}
        for rule in rules:
            assert required.issubset(rule.keys()), f"Rule missing keys: {rule}"

    def test_severity_values_are_valid(self):
        valid = {"critical", "high", "medium", "low"}
        rules = load_rules(RULES_YAML)
        for rule in rules:
            assert rule["severity"] in valid, f"Invalid severity in rule {rule['id']}"

    def test_five_starter_rules_present(self):
        rules = load_rules(RULES_YAML)
        ids = {r["id"] for r in rules}
        expected = {
            "no_root_user",
            "unpinned_base_image",
            "hardcoded_secret",
            "missing_healthcheck",
            "add_instead_of_copy",
        }
        assert expected.issubset(ids), f"Missing rules: {expected - ids}"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_rules("/nonexistent/rules.yaml")

    def test_malformed_yaml_raises_value_error(self, tmp_path):
        bad_yaml = tmp_path / "rules.yaml"
        bad_yaml.write_text("rules: [{ id: broken,", encoding="utf-8")
        with pytest.raises(ValueError, match="Malformed YAML"):
            load_rules(str(bad_yaml))

    def test_missing_rules_key_raises(self, tmp_path):
        bad_yaml = tmp_path / "rules.yaml"
        bad_yaml.write_text("not_rules:\n  - foo\n", encoding="utf-8")
        with pytest.raises(ValueError, match="'rules' key"):
            load_rules(str(bad_yaml))


# ── Tests: evaluate_rules — check types ──────────────────────────────────────

class TestCheckTypes:
    """Test each check_type handler in isolation using minimal rule fixtures."""

    # missing_instruction
    def test_missing_instruction_fail_when_absent(self):
        instructions = [{"instruction": "FROM", "args": "python:3.11"}]
        rules = [{
            "id": "test_user",
            "description": "needs USER",
            "severity": "critical",
            "check_type": "missing_instruction",
            "instruction": "USER",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_user"]["status"] == "FAIL"

    def test_missing_instruction_pass_when_present(self):
        instructions = [
            {"instruction": "FROM", "args": "python:3.11"},
            {"instruction": "USER", "args": "appuser"},
        ]
        rules = [{
            "id": "test_user",
            "description": "needs USER",
            "severity": "critical",
            "check_type": "missing_instruction",
            "instruction": "USER",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_user"]["status"] == "PASS"

    # tag_equals
    def test_tag_equals_fail_on_latest(self):
        instructions = [{"instruction": "FROM", "args": "python:latest"}]
        rules = [{
            "id": "test_tag",
            "description": "no latest",
            "severity": "high",
            "check_type": "tag_equals",
            "instruction": "FROM",
            "tag": "latest",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_tag"]["status"] == "FAIL"

    def test_tag_equals_pass_on_pinned_version(self):
        instructions = [{"instruction": "FROM", "args": "python:3.11.9-slim"}]
        rules = [{
            "id": "test_tag",
            "description": "no latest",
            "severity": "high",
            "check_type": "tag_equals",
            "instruction": "FROM",
            "tag": "latest",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_tag"]["status"] == "PASS"

    def test_tag_equals_fails_on_no_tag_defaults_to_latest(self):
        # "FROM python" with no tag is implicitly :latest
        instructions = [{"instruction": "FROM", "args": "python"}]
        rules = [{
            "id": "test_tag",
            "description": "no latest",
            "severity": "high",
            "check_type": "tag_equals",
            "instruction": "FROM",
            "tag": "latest",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_tag"]["status"] == "FAIL"

    # pattern_match
    def test_pattern_match_fail_on_secret_env(self):
        instructions = [{"instruction": "ENV", "args": "API_KEY=abc123"}]
        rules = [{
            "id": "test_secret",
            "description": "no secrets",
            "severity": "critical",
            "check_type": "pattern_match",
            "instructions": ["ENV", "ARG"],
            "pattern": "(?i)(password|secret|api_key|token)",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_secret"]["status"] == "FAIL"

    def test_pattern_match_pass_on_clean_env(self):
        instructions = [{"instruction": "ENV", "args": "PORT=5000"}]
        rules = [{
            "id": "test_secret",
            "description": "no secrets",
            "severity": "critical",
            "check_type": "pattern_match",
            "instructions": ["ENV", "ARG"],
            "pattern": "(?i)(password|secret|api_key|token)",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_secret"]["status"] == "PASS"

    # instruction_used
    def test_instruction_used_fail_when_add_present(self):
        instructions = [{"instruction": "ADD", "args": ". /app"}]
        rules = [{
            "id": "test_add",
            "description": "no ADD",
            "severity": "low",
            "check_type": "instruction_used",
            "instruction": "ADD",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_add"]["status"] == "FAIL"

    def test_instruction_used_pass_when_add_absent(self):
        instructions = [{"instruction": "COPY", "args": ". /app"}]
        rules = [{
            "id": "test_add",
            "description": "no ADD",
            "severity": "low",
            "check_type": "instruction_used",
            "instruction": "ADD",
        }]
        results = _results_by_id(evaluate_rules(instructions, rules))
        assert results["test_add"]["status"] == "PASS"


# ── Tests: end-to-end against sample Dockerfiles ─────────────────────────────

class TestEndToEnd:
    def test_bad_dockerfile_fails_all_five_rules(self):
        instructions = parse_dockerfile(BAD_DOCKERFILE)
        rules = load_rules(RULES_YAML)
        results = _results_by_id(evaluate_rules(instructions, rules))

        assert results["no_root_user"]["status"]        == "FAIL"
        assert results["unpinned_base_image"]["status"] == "FAIL"
        assert results["hardcoded_secret"]["status"]    == "FAIL"
        assert results["missing_healthcheck"]["status"] == "FAIL"
        assert results["add_instead_of_copy"]["status"] == "FAIL"

    def test_good_dockerfile_passes_all_five_rules(self):
        instructions = parse_dockerfile(GOOD_DOCKERFILE)
        rules = load_rules(RULES_YAML)
        results = _results_by_id(evaluate_rules(instructions, rules))

        assert results["no_root_user"]["status"]        == "PASS"
        assert results["unpinned_base_image"]["status"] == "PASS"
        assert results["hardcoded_secret"]["status"]    == "PASS"
        assert results["missing_healthcheck"]["status"] == "PASS"
        assert results["add_instead_of_copy"]["status"] == "PASS"

    def test_result_structure_is_correct(self):
        instructions = parse_dockerfile(BAD_DOCKERFILE)
        rules = load_rules(RULES_YAML)
        results = evaluate_rules(instructions, rules)

        assert isinstance(results, list)
        for r in results:
            assert set(r.keys()) == {"id", "description", "severity", "status"}
            assert r["status"] in {"PASS", "FAIL"}
            assert r["severity"] in {"critical", "high", "medium", "low"}
