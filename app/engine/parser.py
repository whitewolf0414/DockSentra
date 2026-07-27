"""
Dockerfile parser module.

Reads a Dockerfile line by line, handles comments, blank lines,
and multi-line (backslash-continuation) instructions.
"""

from __future__ import annotations

import os
from typing import List, Dict


def parse_dockerfile(filepath: str) -> List[Dict[str, str]]:
    """Parse a Dockerfile and return a list of instruction dicts.

    Each dict has the form::

        {"instruction": "FROM", "args": "python:3.11-slim"}

    Comment lines (starting with ``#``) and blank lines are ignored.
    Multi-line instructions joined with a trailing backslash are merged
    into a single entry before parsing.

    Args:
        filepath: Absolute or relative path to the Dockerfile.

    Returns:
        Ordered list of parsed instruction dicts.

    Raises:
        FileNotFoundError: If *filepath* does not exist.
        ValueError: If the file cannot be decoded as UTF-8.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dockerfile not found: {filepath!r}")

    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            raw_lines = fh.readlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"Cannot decode {filepath!r} as UTF-8: {exc}") from exc

    logical_lines = _join_continuations(raw_lines)
    instructions: List[Dict[str, str]] = []

    for line in logical_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = _parse_line(stripped)
        if parsed:
            instructions.append(parsed)

    return instructions


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _join_continuations(raw_lines: List[str]) -> List[str]:
    """Merge lines that end with a backslash continuation character.

    Args:
        raw_lines: Raw lines from the file (may include newline chars).

    Returns:
        List of logical lines with continuations joined.
    """
    logical: List[str] = []
    buffer = ""

    for raw in raw_lines:
        line = raw.rstrip("\n").rstrip("\r")
        if line.rstrip().endswith("\\"):
            # Strip the trailing backslash and accumulate
            buffer += line.rstrip()[:-1] + " "
        else:
            buffer += line
            logical.append(buffer)
            buffer = ""

    # Handle a file that ends mid-continuation (malformed but tolerated)
    if buffer:
        logical.append(buffer)

    return logical


def _parse_line(line: str) -> Dict[str, str] | None:
    """Split a single logical Dockerfile line into instruction + args.

    Args:
        line: A stripped, non-empty, non-comment logical line.

    Returns:
        Dict with ``instruction`` and ``args`` keys, or ``None`` if the
        line cannot be split (e.g. bare instruction with no args).
    """
    parts = line.split(None, 1)  # split on first whitespace
    if not parts:
        return None

    instruction = parts[0].upper()
    args = parts[1].strip() if len(parts) > 1 else ""
    return {"instruction": instruction, "args": args}
