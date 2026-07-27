"""
Reporter module.

Formats rule evaluation results and score data for human (terminal table)
and machine (JSON) consumption. This module only formats — it never
evaluates rules or calculates scores.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

# Shared console — importers can capture output by passing their own Console
_console = Console()

# Severity → rich style mapping
_SEVERITY_STYLE: Dict[str, str] = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
}

# Grade → rich style mapping
_GRADE_STYLE: Dict[str, str] = {
    "A": "bold green",
    "B": "green",
    "C": "yellow",
    "D": "orange3",
    "F": "bold red",
}


def print_table_report(
    results: List[Dict[str, str]],
    score_data: Dict[str, Any],
    console: Console | None = None,
) -> None:
    """Print a formatted security report to the terminal using Rich.

    Renders two panels:
    1. A summary panel with score, grade, and critical-failure count.
    2. A findings table with one row per rule (ID, severity, status, description).

    Args:
        results: Rule evaluation results from :func:`app.engine.rules.evaluate_rules`.
        score_data: Score dict from :func:`app.engine.scorer.calculate_score`.
        console: Optional Rich Console instance (defaults to stdout console).
    """
    con = console or _console

    # ── Summary panel ──────────────────────────────────────────────────────
    score: int = score_data["score"]
    grade: str = score_data["grade"]
    critical_failures: int = score_data["critical_failures"]
    grade_style = _GRADE_STYLE.get(grade, "white")

    con.rule("[bold]Dockerfile Security Report[/bold]")
    con.print()
    con.print(
        f"  Score : [bold]{score}/100[/bold]   "
        f"Grade : [{grade_style}]{grade}[/{grade_style}]   "
        f"Critical Failures : [{'bold red' if critical_failures else 'green'}]{critical_failures}[/{'bold red' if critical_failures else 'green'}]"
    )
    con.print()

    # ── Findings table ─────────────────────────────────────────────────────
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on grey23",
        expand=True,
    )
    table.add_column("Rule ID", style="bold", min_width=22)
    table.add_column("Severity", min_width=10, justify="center")
    table.add_column("Status", min_width=6, justify="center")
    table.add_column("Description")

    for result in results:
        sev = result["severity"]
        sev_style = _SEVERITY_STYLE.get(sev, "white")
        status = result["status"]
        status_text = Text(status, style="bold green" if status == "PASS" else "bold red")

        table.add_row(
            result["id"],
            Text(sev.upper(), style=sev_style),
            status_text,
            result["description"].strip(),
        )

    con.print(table)
    con.print()


def to_json_report(
    results: List[Dict[str, str]],
    score_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a JSON-serialisable report dict.

    Args:
        results: Rule evaluation results from :func:`app.engine.rules.evaluate_rules`.
        score_data: Score dict from :func:`app.engine.scorer.calculate_score`.

    Returns:
        Dict with ``meta``, ``score``, and ``findings`` keys, safe to pass
        to :func:`json.dumps`.
    """
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool": "dockerfile-security-checker",
            "version": "1.0.0",
        },
        "score": {
            "value": score_data["score"],
            "grade": score_data["grade"],
            "critical_failures": score_data["critical_failures"],
        },
        "findings": [
            {
                "id": r["id"],
                "description": r["description"].strip(),
                "severity": r["severity"],
                "status": r["status"],
            }
            for r in results
        ],
    }


def dump_json_report(
    results: List[Dict[str, str]],
    score_data: Dict[str, Any],
) -> str:
    """Serialise the report as a pretty-printed JSON string.

    Args:
        results: Rule evaluation results.
        score_data: Score dict.

    Returns:
        Indented JSON string.
    """
    return json.dumps(to_json_report(results, score_data), indent=2)
