"""Run shell commands with a shared timeout and safe output decoding."""

import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Tuple

# default number of seconds a shell command may run before it is stopped
DEFAULT_TIMEOUT_SECONDS = 300

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
    timeout: int


def decode_output(data: bytes | None) -> str:
    """Decode captured output as UTF-8, replacing any invalid bytes."""
    if data is None:
        return EMPTY
    return data.decode(OUTPUT_ENCODING, errors=DECODE_ERRORS)


def _start_process(
    command: str, merge_stderr: bool
) -> "subprocess.Popen[bytes]":
    """Start a shell command in its own process group so its tree can be killed."""
    # redirect STDERR to STDOUT when merging so that both streams
    # are captured together in the order the command wrote them
    stderr_target = subprocess.STDOUT if merge_stderr else subprocess.PIPE
    # the platform check uses a literal so that type checkers can tell
    # which platform-specific subprocess and os names are available
    if sys.platform == "win32":
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=stderr_target,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=stderr_target,
            start_new_session=True,
        )
    return process


def _kill_process_tree(process: "subprocess.Popen[bytes]") -> None:
    """Kill a process along with every process that it started."""
    # with shell=True the direct child is only the shell, so killing it
    # alone would leave grandchildren (e.g., pytest) running and holding
    # the output pipes open, which can make the final read hang
    if sys.platform == "win32":
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
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # the process group already exited
            pass
    # make sure the shell itself is gone even if the tree kill missed it
    process.kill()


def _drain_after_kill(
    process: "subprocess.Popen[bytes]",
) -> Tuple[Any, Any]:
    """Collect any output that a killed process wrote before it stopped."""
    try:
        return process.communicate(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        # a stray process is still holding the pipes open, so give up
        # on the partial output instead of waiting forever
        return None, None


def run_shell_command(
    command: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
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
    process = _start_process(command, merge_stderr)
    try:
        stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        _kill_process_tree(process)
        partial_stdout, partial_stderr = _drain_after_kill(process)
        return CommandOutcome(
            command=command,
            returncode=None,
            stdout=decode_output(partial_stdout or error.stdout),
            stderr=decode_output(partial_stderr or error.stderr),
            timed_out=True,
            timeout=timeout,
        )
    except KeyboardInterrupt:
        # the command runs in its own process group, so it does not receive
        # the interrupt itself and must be stopped before exiting
        _kill_process_tree(process)
        raise
    return CommandOutcome(
        command=command,
        returncode=process.returncode,
        stdout=decode_output(stdout_bytes),
        stderr=decode_output(stderr_bytes),
        timed_out=False,
        timeout=timeout,
    )
