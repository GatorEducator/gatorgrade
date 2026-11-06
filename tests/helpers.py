"""Helpers shared by the test suites that run or inspect shell commands."""

import sys


def python_command(code: str) -> str:
    """Return a shell command that runs Python code with this interpreter."""
    return f'"{sys.executable}" -c "{code}"'


def flatten(text: str) -> str:
    """Collapse all whitespace so rich line wrapping cannot split a phrase."""
    return " ".join(text.split())
