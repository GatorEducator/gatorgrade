"""Run shell commands with a shared timeout and safe output decoding."""

import ctypes
import functools
import os
import signal
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import IO, Any, Tuple

# default and largest number of seconds a shell command may run before it is
# stopped; the largest value stays well below threading.TIMEOUT_MAX, which is
# about 49 days on Windows and raises an OverflowError when it is exceeded
DEFAULT_TIMEOUT_SECONDS = 300
MAX_TIMEOUT_SECONDS = 86400

# decoding policy applied to all captured output
OUTPUT_ENCODING = "utf-8"
DECODE_ERRORS = "replace"
EMPTY = ""

# largest amount of output kept in memory for each captured stream
MAX_CAPTURE_BYTES = 10 * 1024 * 1024
CAPTURE_HALVES = 2
TRUNCATION_MARKER_FMT = "\n... (output truncated: kept {} of {} bytes) ...\n"

# message reported when a command cannot be started at all
START_FAILURE_FMT = "Could not start command: {}"

# number of seconds to wait for a killed command to finish exiting
KILL_GRACE_SECONDS = 5

# command used to kill a process tree on Windows when a job is not available
TASKKILL_COMMAND = "taskkill"
TASKKILL_FORCE_FLAG = "/F"
TASKKILL_TREE_FLAG = "/T"
TASKKILL_PID_FLAG = "/PID"
TASKKILL_TIMEOUT_SECONDS = 10

# names and values used with the Windows job object functions
KERNEL32_DLL = "kernel32"
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001
JOB_TERMINATE_EXIT_CODE = 1


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


def _read_capped(file: IO[bytes]) -> Tuple[bytes, bool]:
    """Read a capture file, keeping its start and end when it is too large."""
    size = file.seek(0, os.SEEK_END)
    file.seek(0)
    if size <= MAX_CAPTURE_BYTES:
        return file.read(MAX_CAPTURE_BYTES), False
    half = MAX_CAPTURE_BYTES // CAPTURE_HALVES
    head = file.read(half)
    file.seek(size - half)
    tail = file.read(half)
    marker = TRUNCATION_MARKER_FMT.format(half * CAPTURE_HALVES, size)
    return head + marker.encode(OUTPUT_ENCODING) + tail, True


def _start_process(
    command: str, stdout_file: IO[bytes], stderr_file: IO[bytes] | None
) -> "subprocess.Popen[bytes]":
    """Start a shell command in its own process group so its tree can be killed."""
    # without a separate file, STDERR goes to STDOUT so that both streams
    # are captured together in the order the command wrote them; capturing
    # to files means a background process that keeps a stream open after
    # the command exits cannot delay the result, as it could with a pipe;
    # input is closed so a command that reads it fails instead of waiting
    stderr_target = subprocess.STDOUT if stderr_file is None else stderr_file
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


@functools.lru_cache(maxsize=1)
def _load_kernel32() -> Any:
    """Load the Windows functions that manage job objects."""
    if sys.platform == "win32":
        # a private library instance keeps these declarations from affecting
        # any other code in the process that also uses these functions
        kernel32 = ctypes.WinDLL(KERNEL32_DLL, use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [
            wintypes.LPVOID,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
        ]
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        return kernel32
    else:
        raise OSError(f"{KERNEL32_DLL} is only available on Windows")


def _assign_new_job(kernel32: Any, pid: int) -> int | None:
    """Return a new job object holding a process, or None if that fails."""
    job: int | None = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    handle = kernel32.OpenProcess(
        PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid
    )
    assigned = bool(handle) and kernel32.AssignProcessToJobObject(job, handle)
    if handle:
        kernel32.CloseHandle(handle)
    if not assigned:
        kernel32.CloseHandle(job)
        return None
    return job


def _create_job(pid: int) -> int | None:
    """Return a job object tracking a process tree on Windows, otherwise None."""
    # a job also reaches a process whose parent has already exited, which
    # taskkill cannot find; the job is not set to kill on close, so background
    # processes that outlive a command that finished in time are left running
    if sys.platform == "win32":
        job = _assign_new_job(_load_kernel32(), pid)
    else:
        job = None
    return job


def _close_job(job: int | None) -> None:
    """Release a job object handle without affecting the processes in it."""
    if job is None:
        return
    _load_kernel32().CloseHandle(job)


def _kill_process_tree(
    process: "subprocess.Popen[bytes]", job: int | None = None
) -> None:
    """Kill a process along with every process that it started."""
    # with shell=True the direct child is only the shell, so killing it
    # alone would leave grandchildren (e.g., pytest) running
    if sys.platform == "win32":
        killed = job is not None and _load_kernel32().TerminateJobObject(
            job, JOB_TERMINATE_EXIT_CODE
        )
        if not killed:
            _run_taskkill(process.pid)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # the process group already exited
            pass
    # make sure the shell itself is gone even if the tree kill missed it
    process.kill()
    try:
        process.wait(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        # the process could not be reaped, but it must not delay the result
        pass


def _run_taskkill(pid: int) -> None:
    """Kill a process tree with taskkill, ignoring any failure to do so."""
    try:
        subprocess.run(
            [
                TASKKILL_COMMAND,
                TASKKILL_FORCE_FLAG,
                TASKKILL_TREE_FLAG,
                TASKKILL_PID_FLAG,
                str(pid),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=TASKKILL_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        # the caller still kills the shell itself after this
        pass


def _start_failure_outcome(
    command: str,
    timeout: float,
    merge_stderr: bool,
    error: OSError,
) -> CommandOutcome:
    """Return the outcome of a command that could not be started."""
    # the message goes where the command's output would have gone so that
    # callers display it like any other output from a failed command
    message = START_FAILURE_FMT.format(error)
    return CommandOutcome(
        command=command,
        returncode=None,
        stdout=message if merge_stderr else EMPTY,
        stderr=EMPTY if merge_stderr else message,
        timed_out=False,
        timeout=timeout,
        start_error=message,
    )


def run_shell_command(
    command: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    merge_stderr: bool = True,
) -> CommandOutcome:
    """Run a shell command and return its outcome without raising on timeout.

    A command must finish within timeout seconds. If it is still running
    when that deadline passes, it is stopped along with every process that
    it started and the outcome is marked as timed out.

    Args:
        command: The command to run in a shell.
        timeout: The number of seconds the command may run.
        merge_stderr: Whether to capture STDERR together with STDOUT. When
            true, the merged output is in stdout and stderr is empty.

    Returns:
        The outcome of running the command, with all output decoded as UTF-8,
        any invalid bytes replaced, and very large output truncated.

    """
    try:
        stdout_file = tempfile.TemporaryFile()
        stderr_file = tempfile.TemporaryFile()
    except OSError as error:
        return _start_failure_outcome(command, timeout, merge_stderr, error)
    with stdout_file, stderr_file:
        try:
            process = _start_process(
                command, stdout_file, None if merge_stderr else stderr_file
            )
        except OSError as error:
            return _start_failure_outcome(
                command, timeout, merge_stderr, error
            )
        job = _create_job(process.pid)
        timed_out = False
        # the clock starts with the deadline, so a command that finishes in
        # time cannot report a duration longer than its timeout
        start_time = time.monotonic()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_tree(process, job)
        except BaseException:
            # the command runs in its own process group, so it does not
            # receive an interrupt itself and must be stopped before exiting
            _kill_process_tree(process, job)
            raise
        finally:
            _close_job(job)
        elapsed_seconds = time.monotonic() - start_time
        stdout_bytes, stdout_truncated = _read_capped(stdout_file)
        stderr_bytes, stderr_truncated = _read_capped(stderr_file)
    return CommandOutcome(
        command=command,
        returncode=None if timed_out else process.returncode,
        stdout=decode_output(stdout_bytes),
        stderr=decode_output(stderr_bytes),
        timed_out=timed_out,
        timeout=timeout,
        elapsed_seconds=elapsed_seconds,
        output_truncated=stdout_truncated or stderr_truncated,
    )
