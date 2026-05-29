"""Pytest fixtures for testing various functions in GatorGrade."""

import io
import os
import subprocess
import sys
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def redirect_output_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect output streams to capture application output without affecting pytest."""
    captured_buffer = io.StringIO()

    class QuietStream:
        """A stream that captures output silently."""

        def __init__(self, original: Any, buffer: io.StringIO) -> None:
            self.original = original
            self.buffer = buffer

        def write(self, text: str) -> int:
            self.buffer.write(text)
            return len(text)

        def flush(self) -> None:
            pass

        def isatty(self) -> bool:
            return False

        def __getattr__(self, name: str) -> Any:
            return getattr(self.original, name)

    monkeypatch.setattr(
        sys, "stdout", QuietStream(sys.stdout, captured_buffer)
    )
    monkeypatch.setattr(
        sys, "stderr", QuietStream(sys.stderr, captured_buffer)
    )
    import typer  # noqa: PLC0415

    def quiet_echo(_message: Any = None, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr(typer, "echo", quiet_echo)
    original_run = subprocess.run

    def quiet_run(*args: Any, **kwargs: Any) -> Any:
        if "stdout" not in kwargs:
            kwargs["stdout"] = subprocess.PIPE
        if "stderr" not in kwargs:
            kwargs["stderr"] = subprocess.PIPE
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", quiet_run)


@pytest.fixture
def chdir() -> Any:
    """Change working directory to a specified directory then changes back to base directory."""
    prev_dir = os.getcwd()

    def do_change(change_to: str) -> None:
        os.chdir(change_to)

    yield do_change
    os.chdir(prev_dir)
