"""
Unit tests for app.engine.parser.

Tests cover:
- Correct parsing of a clean (good) Dockerfile
- Correct parsing of a deliberately insecure (bad) Dockerfile
- Multi-line instruction joining
- Comment and blank-line filtering
- FileNotFoundError on missing file
"""

from __future__ import annotations

import os
import textwrap

import pytest

from app.engine.parser import parse_dockerfile


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "sample")
GOOD_DOCKERFILE = os.path.abspath(os.path.join(SAMPLE_DIR, "Dockerfile.good"))
BAD_DOCKERFILE  = os.path.abspath(os.path.join(SAMPLE_DIR, "Dockerfile.bad"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _instructions_for(path: str) -> list[dict]:
    return parse_dockerfile(path)


def _instruction_types(instructions: list[dict]) -> list[str]:
    return [i["instruction"] for i in instructions]


# ── Tests: good Dockerfile ────────────────────────────────────────────────────

class TestGoodDockerfile:
    def test_returns_list_of_dicts(self):
        result = _instructions_for(GOOD_DOCKERFILE)
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_each_dict_has_required_keys(self):
        result = _instructions_for(GOOD_DOCKERFILE)
        for item in result:
            assert "instruction" in item, f"Missing 'instruction' key: {item}"
            assert "args" in item, f"Missing 'args' key: {item}"

    def test_instructions_are_uppercased(self):
        result = _instructions_for(GOOD_DOCKERFILE)
        for item in result:
            assert item["instruction"] == item["instruction"].upper()

    def test_from_instruction_present(self):
        types = _instruction_types(_instructions_for(GOOD_DOCKERFILE))
        assert "FROM" in types

    def test_user_instruction_present(self):
        types = _instruction_types(_instructions_for(GOOD_DOCKERFILE))
        assert "USER" in types, "Dockerfile.good must contain a USER instruction"

    def test_healthcheck_present(self):
        types = _instruction_types(_instructions_for(GOOD_DOCKERFILE))
        assert "HEALTHCHECK" in types

    def test_no_add_instruction(self):
        types = _instruction_types(_instructions_for(GOOD_DOCKERFILE))
        assert "ADD" not in types, "Dockerfile.good must not use ADD"

    def test_from_image_is_pinned(self):
        instructions = _instructions_for(GOOD_DOCKERFILE)
        from_instrs = [i for i in instructions if i["instruction"] == "FROM"]
        assert from_instrs, "Expected at least one FROM instruction"
        image = from_instrs[0]["args"].split()[0]
        tag = image.split(":")[-1] if ":" in image else "latest"
        assert tag != "latest", f"Expected a pinned tag, got '{tag}'"

    def test_no_comments_or_blank_lines(self):
        result = _instructions_for(GOOD_DOCKERFILE)
        for item in result:
            # Comments start with '#' — they must be filtered out
            assert not item["instruction"].startswith("#")
            # Blank args may be valid (e.g. FROM scratch) but instruction is never empty
            assert item["instruction"].strip() != ""


# ── Tests: bad Dockerfile ─────────────────────────────────────────────────────

class TestBadDockerfile:
    def test_from_is_latest(self):
        instructions = _instructions_for(BAD_DOCKERFILE)
        from_instrs = [i for i in instructions if i["instruction"] == "FROM"]
        assert from_instrs, "Expected FROM instruction"
        image = from_instrs[0]["args"].split()[0]
        tag = image.split(":")[-1] if ":" in image else "latest"
        assert tag == "latest", f"Expected ':latest' tag in bad Dockerfile, got '{tag}'"

    def test_add_instruction_present(self):
        types = _instruction_types(_instructions_for(BAD_DOCKERFILE))
        assert "ADD" in types, "Dockerfile.bad must contain ADD"

    def test_env_with_secret_present(self):
        instructions = _instructions_for(BAD_DOCKERFILE)
        env_instrs = [i for i in instructions if i["instruction"] == "ENV"]
        assert env_instrs, "Expected ENV instructions in bad Dockerfile"
        env_args = " ".join(i["args"] for i in env_instrs)
        assert any(
            kw in env_args.lower()
            for kw in ("api_key", "password", "secret", "token")
        ), f"Expected secret-like ENV vars, got: {env_args}"

    def test_no_user_instruction(self):
        types = _instruction_types(_instructions_for(BAD_DOCKERFILE))
        assert "USER" not in types

    def test_no_healthcheck_instruction(self):
        types = _instruction_types(_instructions_for(BAD_DOCKERFILE))
        assert "HEALTHCHECK" not in types


# ── Tests: edge cases ─────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_dockerfile("/nonexistent/path/Dockerfile")

    def test_multiline_continuation(self, tmp_path):
        content = textwrap.dedent("""\
            FROM python:3.11-slim
            RUN apt-get update && \\
                apt-get install -y curl && \\
                rm -rf /var/lib/apt/lists/*
            USER appuser
        """)
        df = tmp_path / "Dockerfile"
        df.write_text(content, encoding="utf-8")
        result = parse_dockerfile(str(df))
        types = _instruction_types(result)
        assert types == ["FROM", "RUN", "USER"]
        # The RUN instruction args should be joined
        run_instr = next(i for i in result if i["instruction"] == "RUN")
        assert "apt-get install" in run_instr["args"]
        assert "\\" not in run_instr["args"]

    def test_comments_stripped(self, tmp_path):
        content = textwrap.dedent("""\
            # This is a comment
            FROM python:3.11-slim
            # Another comment
            USER app
        """)
        df = tmp_path / "Dockerfile"
        df.write_text(content, encoding="utf-8")
        result = parse_dockerfile(str(df))
        assert len(result) == 2
        assert result[0]["instruction"] == "FROM"
        assert result[1]["instruction"] == "USER"

    def test_empty_dockerfile(self, tmp_path):
        df = tmp_path / "Dockerfile"
        df.write_text("# just a comment\n\n# another\n", encoding="utf-8")
        result = parse_dockerfile(str(df))
        assert result == []
