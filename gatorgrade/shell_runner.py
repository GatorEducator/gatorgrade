"""Run shell commands with a shared timeout and safe output decoding."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import BinaryIO

# default number of seconds a shell command may run before it is stopped
DEFAULT_TIMEOUT_SECONDS = 300
MAX_TIMEOUT_SECONDS = 86400
MAX_CAPTURE_BYTES = 10 * 1024 * 1024
TRUNCATION_MARKER_FMT = "\n... output truncated ...\n"
START_FAILURE_FMT = "Could not start command: {}"

# decoding policy applied to all captured output
OUTPUT_ENCODING = "utf-8"
DECODE_ERRORS = "replace"
EMPTY = ""

# number of seconds to wait for output after killing a timed-out command
KILL_GRACE_SECONDS = 5

# command used to kill a process tree on Windows
TASKKILL_COMMAND = "taskkill"
TASKKILL_FORCE_FLAG = "/F"
TASKKILL_TREE_FLAG = "/T"
TASKKILL_PID_FLAG = "/PID"


@dataclass(frozen=True)
class CommandOutcome:
    """Represent the outcome of running a shell command."""

    command: str
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    timeout: float
    elapsed_seconds: float = 0.0
    output_truncated: bool = False
    start_error: str | None = None


def decode_output(data: bytes | None) -> str:
    """Decode captured output as UTF-8, replacing any invalid bytes."""
    if data is None:
        return EMPTY
    return data.decode(OUTPUT_ENCODING, errors=DECODE_ERRORS)


def _read_capped(file_obj: BinaryIO) -> tuple[str, bool]:
    """Read a temporary output file, keeping only the first and last halves."""
    file_obj.seek(0)
    data = file_obj.read()
    if not data:
        return EMPTY, False
    if len(data) <= MAX_CAPTURE_BYTES:
        return decode_output(data), False
    half = MAX_CAPTURE_BYTES // 2
    marker = TRUNCATION_MARKER_FMT.encode(
        OUTPUT_ENCODING, errors=DECODE_ERRORS
    )
    truncated = data[:half] + marker + data[-half:]
    return decode_output(truncated), True


def _read_output_files(
    stdout_file: BinaryIO,
    stderr_file: BinaryIO,
    merge_stderr: bool,
) -> tuple[str, str, bool]:
    """Read both captured files and report if the output was truncated."""
    stdout_text, stdout_truncated = _read_capped(stdout_file)
    if merge_stderr:
        return stdout_text, EMPTY, stdout_truncated
    stderr_text, stderr_truncated = _read_capped(stderr_file)
    return stdout_text, stderr_text, stdout_truncated or stderr_truncated


def _start_process(
    command: str,
    merge_stderr: bool,
    stdout_file: BinaryIO,
    stderr_file: BinaryIO,
) -> "subprocess.Popen[bytes]":
    """Start a shell command in its own process group so its tree can be killed."""
    stderr_target = stdout_file if merge_stderr else stderr_file
    # the platform check uses a literal so that type checkers can tell
    # which platform-specific subprocess and os names are available
    if sys.platform == "win32":
        process = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_target,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        process = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_target,
            start_new_session=True,
        )
    return process


def _kill_process_tree(process: "subprocess.Popen[bytes]") -> None:
    """Kill a process along with every process that it started."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                [
                    TASKKILL_COMMAND,
                    TASKKILL_FORCE_FLAG,
                    TASKKILL_TREE_FLAG,
                    TASKKILL_PID_FLAG,
                    str(process.pid),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=KILL_GRACE_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=KILL_GRACE_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        pass


def run_shell_command(
    command: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    merge_stderr: bool = True,
) -> CommandOutcome:
    """Run a shell command and return its outcome without raising on timeout.

    Args:
        command: The command to run in a shell.
        timeout: The number of seconds the command may run before it is
            stopped along with every process that it started.
        merge_stderr: Whether to capture STDERR together with STDOUT. When
            true, the merged output is in stdout and stderr is empty.

    Returns:
        The outcome of running the command, with all output decoded as UTF-8
        and any invalid bytes replaced.

    """
    timeout_seconds = float(timeout)
    start_time = time.monotonic()
    stdout_file = tempfile.TemporaryFile()
    stderr_file = tempfile.TemporaryFile()
    process: subprocess.Popen[bytes] | None = None
    try:
        try:
            process = _start_process(
                command,
                merge_stderr,
                stdout_file,
                stderr_file,
            )
        except OSError as error:
            return CommandOutcome(
                command=command,
                returncode=None,
                stdout=EMPTY,
                stderr=EMPTY,
                timed_out=False,
                timeout=timeout_seconds,
                elapsed_seconds=time.monotonic() - start_time,
                output_truncated=False,
                start_error=START_FAILURE_FMT.format(error),
            )
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _kill_process_tree(process)
            stdout_text, stderr_text, truncated = _read_output_files(
                stdout_file,
                stderr_file,
                merge_stderr,
            )
            return CommandOutcome(
                command=command,
                returncode=None,
                stdout=stdout_text,
                stderr=stderr_text,
                timed_out=True,
                timeout=timeout_seconds,
                elapsed_seconds=time.monotonic() - start_time,
                output_truncated=truncated,
            )
        except BaseException:
            _kill_process_tree(process)
            raise
        stdout_text, stderr_text, truncated = _read_output_files(
            stdout_file,
            stderr_file,
            merge_stderr,
        )
        return CommandOutcome(
            command=command,
            returncode=returncode,
            stdout=stdout_text,
            stderr=stderr_text,
            timed_out=False,
            timeout=timeout_seconds,
            elapsed_seconds=time.monotonic() - start_time,
            output_truncated=truncated,
        )
    except BaseException:
        if process is not None:
            _kill_process_tree(process)
        raise
    finally:
        stdout_file.close()
        stderr_file.close()
