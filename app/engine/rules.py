"""
Rule loader and evaluator module.

All rule logic is entirely data-driven from ``config/rules.yaml``.
No rule conditions are hardcoded here — the check_type field in each
YAML rule selects the appropriate generic evaluator function.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import yaml


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_rules(config_path: str) -> List[Dict[str, Any]]:
    """Load security rules from a YAML configuration file.

    Args:
        config_path: Path to the YAML rules file (e.g. ``config/rules.yaml``).

    Returns:
        List of rule dicts as defined in the YAML file.

    Raises:
        FileNotFoundError: If *config_path* does not exist.
        ValueError: If the YAML is malformed or the ``rules`` key is missing.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        raise FileNotFoundError(f"Rules config not found: {config_path!r}")
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML in {config_path!r}: {exc}") from exc

    if not isinstance(data, dict) or "rules" not in data:
        raise ValueError(
            f"Expected a mapping with a top-level 'rules' key in {config_path!r}"
        )

    rules = data["rules"]
    if not isinstance(rules, list):
        raise ValueError(f"'rules' must be a list in {config_path!r}")

    _validate_rules(rules, config_path)
    return rules


def evaluate_rules(
    instructions: List[Dict[str, str]],
    rules: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Evaluate a list of parsed Dockerfile instructions against security rules.

    Args:
        instructions: Output of :func:`app.engine.parser.parse_dockerfile`.
        rules: Output of :func:`load_rules`.

    Returns:
        List of result dicts, one per rule::

            {
                "id": "no_root_user",
                "description": "...",
                "severity": "critical",
                "status": "PASS" | "FAIL",
            }
    """
    results: List[Dict[str, str]] = []

    for rule in rules:
        check_type: str = rule["check_type"]
        handler = _HANDLERS.get(check_type)

        if handler is None:
            # Unknown check type — treat as PASS with a warning description
            results.append(
                _make_result(
                    rule,
                    passed=True,
                    description=f"[unknown check_type '{check_type}'] {rule['description']}",
                )
            )
            continue

        passed = handler(instructions, rule)
        results.append(_make_result(rule, passed=passed))

    return results


# ---------------------------------------------------------------------------
# Check-type handlers  (private)
# ---------------------------------------------------------------------------

def _check_missing_instruction(
    instructions: List[Dict[str, str]],
    rule: Dict[str, Any],
) -> bool:
    """Return True (PASS) if the required instruction appears at least once."""
    required: str = rule["instruction"].upper()
    return any(i["instruction"] == required for i in instructions)


def _check_tag_equals(
    instructions: List[Dict[str, str]],
    rule: Dict[str, Any],
) -> bool:
    """Return True (PASS) if no matching instruction uses the forbidden tag."""
    target_instruction: str = rule["instruction"].upper()
    bad_tag: str = rule["tag"].lower()

    for instr in instructions:
        if instr["instruction"] != target_instruction:
            continue
        # args for FROM can be: "image:tag", "image:tag AS alias", "image"
        args = instr["args"].split()[0]  # grab image[:tag] part before AS alias
        tag = args.split(":")[-1].lower() if ":" in args else "latest"
        if tag == bad_tag:
            return False  # FAIL — found the bad tag

    return True  # PASS


def _check_pattern_match(
    instructions: List[Dict[str, str]],
    rule: Dict[str, Any],
) -> bool:
    """Return True (PASS) if the regex does NOT match any relevant instruction."""
    target_instructions: List[str] = [i.upper() for i in rule.get("instructions", [])]
    pattern: re.Pattern[str] = re.compile(rule["pattern"], re.IGNORECASE)

    for instr in instructions:
        if instr["instruction"] not in target_instructions:
            continue
        if pattern.search(instr["args"]):
            return False  # FAIL — secret-like pattern detected

    return True  # PASS


def _check_instruction_used(
    instructions: List[Dict[str, str]],
    rule: Dict[str, Any],
) -> bool:
    """Return True (PASS) if the forbidden instruction is NOT present."""
    forbidden: str = rule["instruction"].upper()
    return not any(i["instruction"] == forbidden for i in instructions)


# Map check_type strings → handler functions
_HANDLERS = {
    "missing_instruction": _check_missing_instruction,
    "tag_equals": _check_tag_equals,
    "pattern_match": _check_pattern_match,
    "instruction_used": _check_instruction_used,
}

# ---------------------------------------------------------------------------
# Shared helpers  (private)
# ---------------------------------------------------------------------------

_REQUIRED_RULE_KEYS = {"id", "description", "severity", "check_type"}
_VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def _validate_rules(rules: List[Any], config_path: str) -> None:
    """Validate basic structure of each rule; raise ValueError on problems."""
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(
                f"Rule at index {idx} in {config_path!r} must be a mapping, got {type(rule).__name__}"
            )
        missing = _REQUIRED_RULE_KEYS - rule.keys()
        if missing:
            raise ValueError(
                f"Rule '{rule.get('id', idx)}' in {config_path!r} is missing keys: {missing}"
            )
        if rule["severity"] not in _VALID_SEVERITIES:
            raise ValueError(
                f"Rule '{rule['id']}' has invalid severity '{rule['severity']}'. "
                f"Must be one of {_VALID_SEVERITIES}."
            )


def _make_result(
    rule: Dict[str, Any],
    passed: bool,
    description: str | None = None,
) -> Dict[str, str]:
    """Build a standardised result dict from a rule and its pass/fail status."""
    return {
        "id": rule["id"],
        "description": description if description is not None else rule["description"],
        "severity": rule["severity"],
        "status": "PASS" if passed else "FAIL",
    }
