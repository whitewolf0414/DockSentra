"""
CLI entry point for dockerfile-security-checker.

Usage::

    python -m app.cli.cli --file path/to/Dockerfile [--json] [--fail-under 70]

Exit codes:
    0 — score >= threshold AND no critical failures
    1 — score < threshold OR at least one critical failure exists
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from app.engine.parser import parse_dockerfile
from app.engine.rules import load_rules, evaluate_rules
from app.engine.scorer import calculate_score
from app.engine.reporter import print_table_report, dump_json_report

# Default path to rules config relative to the project root
_DEFAULT_RULES_PATH = os.path.join(
    os.path.dirname(__file__),  # app/cli/
    "..", "..", "config", "rules.yaml",  # → config/rules.yaml
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="dockerfile-security-checker",
        description=(
            "Scan a Dockerfile for common security misconfigurations "
            "and return a 0-100 security score."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m app.cli.cli --file Dockerfile\n"
            "  python -m app.cli.cli --file Dockerfile --json\n"
            "  python -m app.cli.cli --file Dockerfile --fail-under 80\n"
        ),
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        metavar="PATH",
        help="Path to the Dockerfile to scan.",
    )
    parser.add_argument(
        "--rules", "-r",
        default=_DEFAULT_RULES_PATH,
        metavar="PATH",
        help="Path to the rules YAML config (default: config/rules.yaml).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output the report as JSON instead of a terminal table.",
    )
    parser.add_argument(
        "--fail-under",
        type=int,
        default=0,
        metavar="SCORE",
        dest="fail_under",
        help=(
            "Exit with code 1 if the score is below this threshold "
            "(default: 0 — only fail on critical issues)."
        ),
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    """Execute the CLI scan and return an exit code.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        ``0`` on success, ``1`` if the score is below the threshold or a
        critical failure is present.
    """
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args(argv)

    # ── Parse ──────────────────────────────────────────────────────────────
    try:
        instructions = parse_dockerfile(args.file)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    # ── Load rules ─────────────────────────────────────────────────────────
    try:
        rules = load_rules(args.rules)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    # ── Evaluate ───────────────────────────────────────────────────────────
    results = evaluate_rules(instructions, rules)

    # ── Score ──────────────────────────────────────────────────────────────
    score_data = calculate_score(results)

    # ── Report ─────────────────────────────────────────────────────────────
    if args.output_json:
        print(dump_json_report(results, score_data))
    else:
        print_table_report(results, score_data)

    # ── Exit code (gates Jenkins pipeline) ────────────────────────────────
    score: int = score_data["score"]
    critical_failures: int = score_data["critical_failures"]

    should_fail = (score < args.fail_under) or (critical_failures > 0)
    return 1 if should_fail else 0


def main() -> None:
    """CLI entry point called by setuptools or ``python -m``."""
    sys.exit(run())


if __name__ == "__main__":
    main()
