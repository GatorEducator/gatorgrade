"""Pytest fixtures for testing various functions in GatorGrade."""

import io
import os
import subprocess
import sys

import pytest


@pytest.fixture(autouse=True)
def redirect_output_streams(monkeypatch):
    """Redirect output streams to capture application output without affecting pytest."""
    captured_buffer = io.StringIO()

    class QuietStream:
        """A stream that captures output silently."""

        def __init__(self, original, buffer):
            self.original = original
            self.buffer = buffer

        def write(self, text):
            self.buffer.write(text)
            return len(text)

        def flush(self):
            pass

        def isatty(self):
            return False

        def __getattr__(self, name):
            return getattr(self.original, name)

    monkeypatch.setattr(sys, "stdout", QuietStream(sys.stdout, captured_buffer))
    monkeypatch.setattr(sys, "stderr", QuietStream(sys.stderr, captured_buffer))
    import typer

    def quiet_echo(message=None, **kwargs):
        _ = message
        _ = kwargs
        pass

    monkeypatch.setattr(typer, "echo", quiet_echo)
    original_run = subprocess.run

    def quiet_run(*args, **kwargs):
        if "stdout" not in kwargs:
            kwargs["stdout"] = subprocess.PIPE
        if "stderr" not in kwargs:
            kwargs["stderr"] = subprocess.PIPE
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", quiet_run)


@pytest.fixture
def chdir():
    """Change working directory to a specified directory then changes back to base directory."""
    prev_dir = os.getcwd()

    def do_change(change_to):
        os.chdir(change_to)

    yield do_change

    os.chdir(prev_dir)
