# Dockerfile Security Checker

> **Catch Dockerfile security issues before they reach production.**

A CLI + web tool that statically analyses Dockerfiles for common security misconfigurations and produces a 0–100 security score with severity-rated findings. Rules are entirely data-driven — add or modify checks in `config/rules.yaml` without touching Python code.

Built as a portfolio-grade DevSecOps project demonstrating: static analysis, data-driven rule engines, Flask web applications, pytest test suites, containerisation best practices, and a Jenkins CI/CD pipeline with automated security gating.

---

## Table of Contents

- [Project Purpose](#project-purpose)
- [Architecture](#architecture)
- [Setup](#setup)
- [CLI Usage](#cli-usage)
- [Web Usage](#web-usage)
- [Running Tests](#running-tests)
- [Jenkins Pipeline](#jenkins-pipeline)
- [Implemented Rules](#implemented-rules)
- [Example Output](#example-output)
- [Extending Rules](#extending-rules)

---

## Project Purpose

Insecure Dockerfiles are one of the most common sources of container vulnerabilities in CI/CD pipelines: running as root, using unpinned base images, and embedding secrets as environment variables are mistakes that appear even in production codebases. **Dockerfile Security Checker** gives developers an immediate feedback loop — either in the terminal or a browser — to catch these issues at authoring time, before a single byte reaches a registry or a production cluster.

The tool integrates directly into Jenkins pipelines via its exit-code contract (exit 1 = fail) and can be paired with a Trivy container scan for defence-in-depth.

---

## Architecture

```
app/
├── engine/
│   ├── parser.py    # Reads Dockerfiles → list of instruction dicts
│   ├── rules.py     # Loads config/rules.yaml, evaluates each rule
│   ├── scorer.py    # Converts results → numeric score + grade
│   └── reporter.py  # Rich terminal table + JSON serialiser
├── cli/
│   └── cli.py       # argparse CLI, exit-code gate
└── web/
    └── app.py       # Stateless Flask app
config/
└── rules.yaml       # ALL rule definitions live here
```

---

## Setup

**Requirements:** Python 3.11+

```bash
# 1. Clone the repository
git clone https://github.com/example/dockerfile-security-checker.git
cd dockerfile-security-checker

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## CLI Usage

```bash
# Basic scan — prints a Rich table to the terminal
python -m app.cli.cli --file path/to/Dockerfile

# Output as JSON
python -m app.cli.cli --file path/to/Dockerfile --json

# Gate on a minimum score (exit code 1 if score < 80)
python -m app.cli.cli --file path/to/Dockerfile --fail-under 80

# Use a custom rules file
python -m app.cli.cli --file path/to/Dockerfile --rules my-rules.yaml

# Scan the project's own Dockerfile (self-attestation / dogfooding)
python -m app.cli.cli --file Dockerfile
```

**Exit codes:**
| Code | Meaning |
|------|---------|
| `0`  | Score ≥ threshold AND no critical failures |
| `1`  | Score < threshold OR ≥ 1 critical failure  |

---

## Web Usage

```bash
# Start the Flask development server
python -m app.web.app

# Navigate to http://localhost:5000
# Paste your Dockerfile content into the textarea and click "Run Security Scan"
```

The web interface shows:
- A circular gauge with the numeric score and letter grade
- A colour-coded findings table with severity badges
- A built-in rules reference panel

No data is stored between requests — the app is fully stateless.

---

## Running Tests

```bash
# Run the full test suite
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Run a single test file
pytest tests/test_parser.py -v
```

Test coverage:
| File | Tests |
|------|-------|
| `test_parser.py` | Parsing correctness, multi-line joining, error conditions |
| `test_rules.py`  | All 4 check types in isolation + end-to-end fixture tests |
| `test_scorer.py` | Penalty math, grade boundaries, critical-failure counting |

---

## Jenkins Pipeline

The `Jenkinsfile` defines a declarative pipeline with 6 stages:

| Stage | What it does | Fails build if… |
|-------|-------------|-----------------|
| **Checkout** | `checkout scm` | SCM unavailable |
| **Build** | `pip install -r requirements.txt` in a venv | Install fails |
| **Test** | `pytest tests/` with JUnit XML output | Any test fails |
| **Security Scan** | Runs the CLI against the project's root `Dockerfile` with `--fail-under 70` | Exit code 1 (score < 70 or critical failure) |
| **Container Scan** | `docker build` + `trivy image --exit-code 1 --severity CRITICAL,HIGH` | Trivy finds CRITICAL or HIGH CVEs |
| **Archive Reports** | Publishes `reports/` as a Jenkins build artifact | — |

> **Note:** The Security Scan stage also runs the CLI against `app/sample/Dockerfile.bad` for verification, but does **not** gate the build on that result (it's expected to fail). Only the project's own `Dockerfile` gates the pipeline.

```groovy
// Override the fail threshold from the Jenkins UI or a parameterised build:
environment {
    FAIL_UNDER = "80"
}
```

---

## Implemented Rules

All rules live in `config/rules.yaml`. No Python code changes are needed to add, modify, or disable a rule.

| Rule ID | Check Type | Severity | Description |
|---------|-----------|----------|-------------|
| `no_root_user` | `missing_instruction` | **Critical** | Container must have a `USER` instruction to run as non-root |
| `hardcoded_secret` | `pattern_match` | **Critical** | `ENV`/`ARG` must not contain password, secret, api_key, or token |
| `unpinned_base_image` | `tag_equals` | **High** | `FROM` image must not use the `:latest` tag |
| `missing_healthcheck` | `missing_instruction` | **Medium** | A `HEALTHCHECK` instruction must be present |
| `add_instead_of_copy` | `instruction_used` | **Low** | `ADD` should not be used — prefer `COPY` |

**Scoring penalties:**

| Severity | Penalty |
|----------|---------|
| Critical | −30 |
| High     | −20 |
| Medium   | −10 |
| Low      | −5  |

**Grade thresholds:** A (≥90), B (≥80), C (≥70), D (≥60), F (<60)

---

## Example Output

### Dockerfile.good (score: 100 / grade: A)

```
────────────────── Dockerfile Security Report ──────────────────

  Score : 100/100   Grade : A   Critical Failures : 0

╭──────────────────────────┬────────────┬────────┬───────────────────────────────────────────╮
│ Rule ID                  │ Severity   │ Status │ Description                               │
├──────────────────────────┼────────────┼────────┼───────────────────────────────────────────┤
│ no_root_user             │  CRITICAL  │  PASS  │ Container runs as root. Add a USER …      │
│ unpinned_base_image      │    HIGH    │  PASS  │ Base image uses the ':latest' tag. …      │
│ hardcoded_secret         │  CRITICAL  │  PASS  │ A potential secret appears to be …        │
│ missing_healthcheck      │   MEDIUM   │  PASS  │ No HEALTHCHECK instruction found. …       │
│ add_instead_of_copy      │    LOW     │  PASS  │ ADD is used instead of COPY. …            │
╰──────────────────────────┴────────────┴────────┴───────────────────────────────────────────╯
```

### Dockerfile.bad (score: 5 / grade: F)

```
────────────────── Dockerfile Security Report ──────────────────

  Score : 5/100   Grade : F   Critical Failures : 2

╭──────────────────────────┬────────────┬────────┬───────────────────────────────────────────╮
│ Rule ID                  │ Severity   │ Status │ Description                               │
├──────────────────────────┼────────────┼────────┼───────────────────────────────────────────┤
│ no_root_user             │  CRITICAL  │  FAIL  │ Container runs as root. Add a USER …      │
│ unpinned_base_image      │    HIGH    │  FAIL  │ Base image uses the ':latest' tag. …      │
│ hardcoded_secret         │  CRITICAL  │  FAIL  │ A potential secret appears to be …        │
│ missing_healthcheck      │   MEDIUM   │  FAIL  │ No HEALTHCHECK instruction found. …       │
│ add_instead_of_copy      │    LOW     │  FAIL  │ ADD is used instead of COPY. …            │
╰──────────────────────────┴────────────┴────────┴───────────────────────────────────────────╯
```

Score calculation for Dockerfile.bad:
`100 − 30 (critical) − 30 (critical) − 20 (high) − 10 (medium) − 5 (low) = 5`

---

## Extending Rules

To add a new rule, append an entry to `config/rules.yaml`:

```yaml
- id: expose_privileged_port
  description: >
    A privileged port (< 1024) is exposed. Use a port >= 1024 and
    remap at the load-balancer level.
  severity: medium
  check_type: pattern_match
  instructions:
    - EXPOSE
  pattern: "^([1-9][0-9]{0,2}|10[01][0-9]|102[0-3])$"
```

No Python changes required. The new rule will appear in every scan immediately.

**Supported `check_type` values:**

| Type | Fails when… |
|------|------------|
| `missing_instruction` | The specified `instruction` never appears |
| `tag_equals` | The instruction's image tag equals `tag` (e.g. `latest`) |
| `pattern_match` | The regex `pattern` matches any `instructions` arg |
| `instruction_used` | The specified `instruction` appears at all |

---

## License

MIT — see [LICENSE](LICENSE).
