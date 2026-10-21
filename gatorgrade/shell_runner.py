"""Run shell commands with a shared timeout and safe output decoding."""

import os
import signal
import subprocess
from dataclasses import dataclass
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 300
OUTPUT_ENCODING = "utf-8"
DECODE_ERRORS = "replace"


@dataclass(frozen=True)
class CommandOutcome:
    """The result of running a shell command."""

    command: str
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    timeout: int


def decode_output(data: bytes | str | None) -> str:
    """Decode subprocess output safely across platforms and encodings."""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode(OUTPUT_ENCODING, DECODE_ERRORS)
    return str(data)


def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Stop a shell process and its child process tree when it times out."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                [
                    "taskkill",
                    "/F",
                    "/T",
                    "/PID",
                    str(process.pid),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def run_shell_command(
    command: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    merge_stderr: bool = True,
) -> CommandOutcome:
    """Run a shell command and return decoded output with timeout metadata."""
    popen_kwargs: dict[str, Any] = {
        "shell": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT if merge_stderr else subprocess.PIPE,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        popen_kwargs["start_new_session"] = True
    process: subprocess.Popen[Any] | None = None
    stdout_bytes: bytes | str | None = None
    stderr_bytes: bytes | str | None = None
    try:
        process = subprocess.Popen(command, **popen_kwargs)
        assert process is not None
        stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
        stdout = decode_output(stdout_bytes)
        stderr = decode_output(stderr_bytes)
        return CommandOutcome(
            command=command,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        if process is not None:
            _kill_process_tree(process)
            try:
                stdout_bytes, stderr_bytes = process.communicate()
            except ValueError:
                stdout_bytes = exc.stdout
                stderr_bytes = exc.stderr
        else:
            stdout_bytes = exc.stdout
            stderr_bytes = exc.stderr
        stdout = decode_output(stdout_bytes)
        stderr = decode_output(stderr_bytes)
        if merge_stderr:
            return CommandOutcome(
                command=command,
                returncode=None,
                stdout=stdout,
                stderr="",
                timed_out=True,
                timeout=timeout,
            )
        return CommandOutcome(
            command=command,
            returncode=None,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            timeout=timeout,
        )
