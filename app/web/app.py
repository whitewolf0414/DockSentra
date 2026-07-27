"""
Flask web application for dockerfile-security-checker.

Single-page, stateless: accepts pasted Dockerfile content via a textarea,
runs the full scan pipeline in-process, and renders the results as styled HTML.

No database. No authentication. No state between requests.
"""

from __future__ import annotations

import os
import tempfile

from flask import Flask, render_template, request

from app.engine.parser import parse_dockerfile
from app.engine.rules import load_rules, evaluate_rules
from app.engine.scorer import calculate_score
from app.engine.reporter import to_json_report

app = Flask(__name__)

# Resolve rules config relative to this file
_RULES_PATH = os.path.join(
    os.path.dirname(__file__),   # app/web/
    "..", "..", "config", "rules.yaml",
)


@app.route("/", methods=["GET", "POST"])
def index():
    """Render the scanner page and process submitted Dockerfile content.

    GET  — renders the empty form.
    POST — runs the full scan pipeline and returns results in the same template.

    Returns:
        Rendered HTML string.
    """
    report = None
    error: str | None = None
    dockerfile_content: str = ""

    if request.method == "POST":
        dockerfile_content = request.form.get("dockerfile_content", "").strip()

        if not dockerfile_content:
            error = "Please paste some Dockerfile content before scanning."
        else:
            try:
                report = _run_scan(dockerfile_content)
            except Exception as exc:  # noqa: BLE001
                error = f"Scan failed: {exc}"

    return render_template(
        "index.html",
        report=report,
        error=error,
        dockerfile_content=dockerfile_content,
    )


@app.route("/health")
def health():
    """Liveness probe endpoint used by Docker HEALTHCHECK.

    Returns:
        JSON-like plain-text OK response with 200 status.
    """
    return {"status": "ok"}, 200


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _run_scan(content: str) -> dict:
    """Run the full scan pipeline on raw Dockerfile text.

    Writes the content to a temporary file so the parser can operate on it,
    then cleans up before returning.

    Args:
        content: Raw Dockerfile text pasted by the user.

    Returns:
        Full report dict as produced by :func:`app.engine.reporter.to_json_report`.

    Raises:
        FileNotFoundError: If the rules config cannot be found.
        ValueError: If the YAML is malformed or Dockerfile cannot be decoded.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".dockerfile",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        instructions = parse_dockerfile(tmp_path)
        rules = load_rules(_RULES_PATH)
        results = evaluate_rules(instructions, rules)
        score_data = calculate_score(results)
        return to_json_report(results, score_data)
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
