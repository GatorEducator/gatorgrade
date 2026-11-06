"""Test suite for the shared shell command runner."""

import io
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterator, List, Tuple
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade import shell_runner
from gatorgrade.shell_runner import (
    DEFAULT_TIMEOUT_SECONDS,
    KILL_GRACE_SECONDS,
    MAX_CAPTURE_BYTES,
    MAX_TIMEOUT_SECONDS,
    TASKKILL_TIMEOUT_SECONDS,
    CommandOutcome,
    decode_output,
    run_shell_command,
)
from tests.helpers import python_command

PYTHON = f'"{sys.executable}"'
MIXED_CMD = (
    f"{PYTHON} -c \"import sys; print('to-out'); "
    "print('to-err', file=sys.stderr); sys.exit(3)\""
)
INVALID_BYTES_CMD = (
    f"{PYTHON} -c \"import sys; sys.stdout.buffer.write(b'valid\\xffoutput')\""
)
NONZERO_EXIT = 3
KILLED_EXIT = -9
CUSTOM_TIMEOUT = 42
FAKE_PID = 12345
FAKE_JOB = 777
FAKE_HANDLE = 888
INVALID_BYTES = b"valid\xffoutput"
REPLACEMENT_CHAR = "�"
POPEN_TARGET = "gatorgrade.shell_runner.subprocess.Popen"
RUN_TARGET = "gatorgrade.shell_runner.subprocess.run"
TEMPFILE_TARGET = "gatorgrade.shell_runner.tempfile.TemporaryFile"
KILL_TARGET = "gatorgrade.shell_runner._kill_process_tree"
CREATE_JOB_TARGET = "gatorgrade.shell_runner._create_job"
CLOSE_JOB_TARGET = "gatorgrade.shell_runner._close_job"
LOAD_KERNEL32_TARGET = "gatorgrade.shell_runner._load_kernel32"
CAP_TARGET = "gatorgrade.shell_runner.MAX_CAPTURE_BYTES"

# a small capture limit so that the capture boundaries can be tested directly
SMALL_CAP = 10
MARKER_ROOM = 80

# limits for real commands: each limit leaves enough margin for a new Python
# process to start on a slow or busy machine, such as during a coverage run
OVER_LIMIT_TIMEOUTS = [0.5, 1]
MINIMUM_TIMEOUT = 1
UNDER_LIMIT_TIMEOUT = 3
UNDER_LIMIT_SLEEP = 0.1
NEAR_LIMIT_TIMEOUT = 3
NEAR_LIMIT_SLEEP = 1.5
PARTIAL_OUTPUT_TIMEOUT = 3
TREE_TIMEOUT = 4
BACKGROUND_TIMEOUT = 30
INPUT_TIMEOUT = 30
LONG_SLEEP = 60

# a command is never stopped before its limit, apart from clock resolution,
# and it is stopped promptly after it, apart from the time a busy machine takes
CLOCK_TOLERANCE = 0.05
TIMING_SLACK = 5
DEAD_POLL_SECONDS = 10
DEAD_POLL_INTERVAL = 0.1

# when this variable is set during a coverage run, every new Python process
# measures itself and takes about ten times longer to start
COVERAGE_SUBPROCESS_VARIABLE = "COV_CORE_SOURCE"

# a child that records its process identifier and then outlives the test
CHILD_SCRIPT = """\
import os
import sys
import time
from pathlib import Path

Path(sys.argv[1]).write_text(str(os.getpid()))
time.sleep(60)
"""

# a parent that stays alive for as long as its child does
WAITING_PARENT_SCRIPT = """\
import subprocess
import sys

subprocess.run([sys.executable, sys.argv[1], sys.argv[2]])
"""

# a parent that starts a child, waits for it to be running, and then exits
# while the child keeps its output streams open
SPAWNER_SCRIPT = """\
import subprocess
import sys
import time
from pathlib import Path

subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])
deadline = time.monotonic() + 20
while not Path(sys.argv[2]).exists() and time.monotonic() < deadline:
    time.sleep(0.05)
print("done", flush=True)
"""


def _sleep_command(seconds: float) -> str:
    """Return a shell command that sleeps and then prints a final message."""
    return python_command(
        f"import time; time.sleep({seconds}); print('finished')"
    )


def _fake_popen(
    wait_effects: List[Any],
    stdout: bytes = b"",
    stderr: bytes = b"",
    returncode: int = 0,
) -> Tuple[Callable[..., MagicMock], MagicMock]:
    """Return a Popen stand-in that writes output and a scripted fake process."""
    process = MagicMock()
    process.pid = FAKE_PID
    process.returncode = returncode
    process.wait.side_effect = wait_effects

    def start(*_args: Any, **kwargs: Any) -> MagicMock:
        kwargs["stdout"].write(stdout)
        kwargs["stdout"].flush()
        if kwargs["stderr"] != subprocess.STDOUT:
            kwargs["stderr"].write(stderr)
            kwargs["stderr"].flush()
        return process

    return start, process


def _deadline_passed() -> subprocess.TimeoutExpired:
    """Return the error that Popen.wait raises when a deadline passes."""
    return subprocess.TimeoutExpired(cmd="slow", timeout=CUSTOM_TIMEOUT)


@pytest.fixture(autouse=True)
def uninstrumented_child_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep coverage out of child processes so that timing bands stay accurate."""
    monkeypatch.delenv(COVERAGE_SUBPROCESS_VARIABLE, raising=False)


@pytest.fixture
def mock_kill() -> Iterator[MagicMock]:
    """Replace the job and tree kill steps so that fake processes can be used."""
    with (
        patch(CREATE_JOB_TARGET, return_value=None),
        patch(KILL_TARGET) as kill,
    ):
        yield kill


def _process_is_alive(pid: int) -> bool:
    """Return whether a process is running, without affecting it."""
    if sys.platform == "win32":
        listing = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        ).stdout
        alive = str(pid) in listing.split()
    else:
        try:
            os.kill(pid, 0)
            alive = True
        except ProcessLookupError:
            alive = False
    return alive


def _wait_until_dead(pid: int) -> bool:
    """Return whether a process exits soon, since a kill is not instantaneous."""
    deadline = time.monotonic() + DEAD_POLL_SECONDS
    while time.monotonic() < deadline:
        if not _process_is_alive(pid):
            return True
        time.sleep(DEAD_POLL_INTERVAL)
    return False


def _kill_pid(pid: int) -> None:
    """Stop a process that a test deliberately left running."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _write_scripts(tmp_path: Path) -> Tuple[Path, Path, Path, Path]:
    """Write the helper scripts and return their paths and the PID file path."""
    child = tmp_path / "child.py"
    child.write_text(CHILD_SCRIPT)
    waiting_parent = tmp_path / "waiting_parent.py"
    waiting_parent.write_text(WAITING_PARENT_SCRIPT)
    spawner = tmp_path / "spawner.py"
    spawner.write_text(SPAWNER_SCRIPT)
    return child, waiting_parent, spawner, tmp_path / "child.pid"


def test_decode_output_none_returns_empty() -> None:
    """Test that missing output decodes to an empty string."""
    assert decode_output(None) == ""


def test_decode_output_valid_utf8() -> None:
    """Test that valid UTF-8 bytes decode unchanged."""
    assert decode_output("héllo".encode("utf-8")) == "héllo"


def test_decode_output_replaces_invalid_bytes() -> None:
    """Test that invalid bytes are replaced instead of raising an error."""
    decoded = decode_output(INVALID_BYTES)
    assert decoded == f"valid{REPLACEMENT_CHAR}output"


@pytest.mark.propertybased
@given(st.binary())
def test_decode_output_never_raises_property(data: bytes) -> None:
    """Property: any bytes at all decode to a string."""
    assert isinstance(decode_output(data), str)


def test_command_outcome_is_frozen() -> None:
    """Test that a CommandOutcome cannot be changed after it is created."""
    outcome = CommandOutcome(
        command="echo",
        returncode=0,
        stdout="",
        stderr="",
        timed_out=False,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    with pytest.raises(AttributeError):
        setattr(outcome, "returncode", 1)


def test_command_outcome_optional_field_defaults() -> None:
    """Test that the optional outcome fields default to a clean run."""
    outcome = CommandOutcome(
        command="echo",
        returncode=0,
        stdout="",
        stderr="",
        timed_out=False,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    assert outcome.elapsed_seconds == 0.0
    assert outcome.output_truncated is False
    assert outcome.start_error is None


def test_max_timeout_stays_below_platform_limit() -> None:
    """Test that the largest timeout cannot overflow the platform wait limit."""
    assert MAX_TIMEOUT_SECONDS < threading.TIMEOUT_MAX


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"", b""),
        (b"a" * (SMALL_CAP - 1), b"a" * (SMALL_CAP - 1)),
        (b"a" * SMALL_CAP, b"a" * SMALL_CAP),
    ],
)
def test_read_capped_keeps_output_at_or_under_the_cap(
    content: bytes, expected: bytes
) -> None:
    """Test that output no larger than the cap is returned unchanged."""
    with patch(CAP_TARGET, SMALL_CAP):
        data, truncated = shell_runner._read_capped(io.BytesIO(content))
    assert data == expected
    assert truncated is False


@pytest.mark.parametrize("extra", [1, 2, 1000])
def test_read_capped_truncates_output_over_the_cap(extra: int) -> None:
    """Test that output over the cap keeps its start and end around a marker."""
    half = SMALL_CAP // 2
    middle = b"m" * extra
    content = b"H" * half + middle + b"T" * half
    with patch(CAP_TARGET, SMALL_CAP):
        data, truncated = shell_runner._read_capped(io.BytesIO(content))
    assert truncated is True
    assert data.startswith(b"H" * half)
    assert data.endswith(b"T" * half)
    assert b"m" not in data
    assert b"kept %d of %d bytes" % (SMALL_CAP, len(content)) in data


@pytest.mark.propertybased
@given(st.binary(max_size=200))
def test_read_capped_never_exceeds_cap_property(content: bytes) -> None:
    """Property: the kept output is never larger than the cap plus a marker."""
    with patch(CAP_TARGET, SMALL_CAP):
        data, truncated = shell_runner._read_capped(io.BytesIO(content))
    assert len(data) <= SMALL_CAP + MARKER_ROOM
    assert truncated is (len(content) > SMALL_CAP)


def test_start_process_starts_in_new_process_group() -> None:
    """Test that the command starts in its own process group or session."""
    with patch(POPEN_TARGET) as mock_popen:
        shell_runner._start_process("cmd", io.BytesIO(), None)
    kwargs = mock_popen.call_args.kwargs
    assert kwargs["shell"] is True
    if sys.platform == "win32":
        assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        assert kwargs["start_new_session"] is True


def test_start_process_closes_input() -> None:
    """Test that a command cannot read from the input of GatorGrade."""
    with patch(POPEN_TARGET) as mock_popen:
        shell_runner._start_process("cmd", io.BytesIO(), None)
    assert mock_popen.call_args.kwargs["stdin"] == subprocess.DEVNULL


def test_start_process_merges_stderr_without_a_separate_file() -> None:
    """Test that STDERR joins STDOUT when it has no capture file of its own."""
    stdout_file = io.BytesIO()
    with patch(POPEN_TARGET) as mock_popen:
        shell_runner._start_process("cmd", stdout_file, None)
    assert mock_popen.call_args.kwargs["stdout"] is stdout_file
    assert mock_popen.call_args.kwargs["stderr"] == subprocess.STDOUT


def test_start_process_separates_stderr_with_a_separate_file() -> None:
    """Test that STDERR goes to its own capture file when it has one."""
    stderr_file = io.BytesIO()
    with patch(POPEN_TARGET) as mock_popen:
        shell_runner._start_process("cmd", io.BytesIO(), stderr_file)
    assert mock_popen.call_args.kwargs["stderr"] is stderr_file


def test_assign_new_job_returns_job_and_closes_process_handle() -> None:
    """Test that a successful assignment keeps the job and closes the handle."""
    kernel32 = MagicMock()
    kernel32.CreateJobObjectW.return_value = FAKE_JOB
    kernel32.OpenProcess.return_value = FAKE_HANDLE
    kernel32.AssignProcessToJobObject.return_value = 1
    assert shell_runner._assign_new_job(kernel32, FAKE_PID) == FAKE_JOB
    kernel32.AssignProcessToJobObject.assert_called_once_with(
        FAKE_JOB, FAKE_HANDLE
    )
    kernel32.CloseHandle.assert_called_once_with(FAKE_HANDLE)


def test_assign_new_job_returns_none_when_job_cannot_be_created() -> None:
    """Test that a failure to create a job leaves nothing to clean up."""
    kernel32 = MagicMock()
    kernel32.CreateJobObjectW.return_value = None
    assert shell_runner._assign_new_job(kernel32, FAKE_PID) is None
    kernel32.OpenProcess.assert_not_called()
    kernel32.CloseHandle.assert_not_called()


def test_assign_new_job_closes_job_when_process_cannot_be_opened() -> None:
    """Test that the job is released when the process cannot be opened."""
    kernel32 = MagicMock()
    kernel32.CreateJobObjectW.return_value = FAKE_JOB
    kernel32.OpenProcess.return_value = None
    assert shell_runner._assign_new_job(kernel32, FAKE_PID) is None
    kernel32.AssignProcessToJobObject.assert_not_called()
    kernel32.CloseHandle.assert_called_once_with(FAKE_JOB)


def test_assign_new_job_closes_both_handles_when_assignment_fails() -> None:
    """Test that both handles are released when the assignment is refused."""
    kernel32 = MagicMock()
    kernel32.CreateJobObjectW.return_value = FAKE_JOB
    kernel32.OpenProcess.return_value = FAKE_HANDLE
    kernel32.AssignProcessToJobObject.return_value = 0
    assert shell_runner._assign_new_job(kernel32, FAKE_PID) is None
    closed = [call.args[0] for call in kernel32.CloseHandle.call_args_list]
    assert closed == [FAKE_HANDLE, FAKE_JOB]


def test_close_job_ignores_missing_job() -> None:
    """Test that closing nothing does not load any Windows functions."""
    with patch(LOAD_KERNEL32_TARGET) as mock_load:
        shell_runner._close_job(None)
    mock_load.assert_not_called()


def test_close_job_closes_the_handle() -> None:
    """Test that closing a job releases its handle."""
    with patch(LOAD_KERNEL32_TARGET) as mock_load:
        shell_runner._close_job(FAKE_JOB)
    mock_load.return_value.CloseHandle.assert_called_once_with(FAKE_JOB)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only functions")
def test_load_kernel32_provides_job_functions() -> None:
    """Test that the Windows job functions can be loaded."""
    kernel32 = shell_runner._load_kernel32()
    assert kernel32.CreateJobObjectW.restype is not None


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only behavior")
def test_load_kernel32_is_unavailable_on_posix() -> None:
    """Test that loading the Windows functions fails clearly elsewhere."""
    with pytest.raises(OSError, match="only available on Windows"):
        shell_runner._load_kernel32()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only behavior")
def test_create_job_returns_none_on_posix() -> None:
    """Test that a job object is not used outside of Windows."""
    assert shell_runner._create_job(FAKE_PID) is None


def test_run_taskkill_targets_the_whole_tree_with_a_timeout() -> None:
    """Test that taskkill is asked to force a tree kill without blocking forever."""
    with patch(RUN_TARGET) as mock_run:
        shell_runner._run_taskkill(FAKE_PID)
    command = mock_run.call_args.args[0]
    assert command[0] == shell_runner.TASKKILL_COMMAND
    assert shell_runner.TASKKILL_FORCE_FLAG in command
    assert shell_runner.TASKKILL_TREE_FLAG in command
    assert str(FAKE_PID) in command
    assert mock_run.call_args.kwargs["timeout"] == TASKKILL_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError("taskkill"),
        PermissionError("taskkill"),
        subprocess.TimeoutExpired(cmd="taskkill", timeout=1),
    ],
)
def test_run_taskkill_ignores_failures(failure: Exception) -> None:
    """Test that a missing or hanging taskkill does not raise an error."""
    with patch(RUN_TARGET, side_effect=failure):
        shell_runner._run_taskkill(FAKE_PID)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only kill path")
def test_kill_process_tree_uses_job_without_taskkill() -> None:
    """Test that a job that terminates makes taskkill unnecessary."""
    process = MagicMock()
    with (
        patch(LOAD_KERNEL32_TARGET) as mock_load,
        patch(RUN_TARGET) as mock_run,
    ):
        mock_load.return_value.TerminateJobObject.return_value = 1
        shell_runner._kill_process_tree(process, FAKE_JOB)
    mock_load.return_value.TerminateJobObject.assert_called_once()
    mock_run.assert_not_called()
    process.kill.assert_called_once()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only kill path")
def test_kill_process_tree_falls_back_to_taskkill_without_a_job() -> None:
    """Test that taskkill is used when no job could be created."""
    process = MagicMock()
    process.pid = FAKE_PID
    with patch(RUN_TARGET) as mock_run:
        shell_runner._kill_process_tree(process, None)
    assert str(FAKE_PID) in mock_run.call_args.args[0]
    process.kill.assert_called_once()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only kill path")
def test_kill_process_tree_falls_back_to_taskkill_when_job_fails() -> None:
    """Test that taskkill is used when the job cannot be terminated."""
    process = MagicMock()
    process.pid = FAKE_PID
    with (
        patch(LOAD_KERNEL32_TARGET) as mock_load,
        patch(RUN_TARGET) as mock_run,
    ):
        mock_load.return_value.TerminateJobObject.return_value = 0
        shell_runner._kill_process_tree(process, FAKE_JOB)
    assert str(FAKE_PID) in mock_run.call_args.args[0]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only kill path")
def test_kill_process_tree_kills_process_group() -> None:
    """Test that the whole process group and the shell are killed."""
    process = MagicMock()
    process.pid = FAKE_PID
    with patch("gatorgrade.shell_runner.os.killpg") as mock_killpg:
        shell_runner._kill_process_tree(process)
    assert mock_killpg.call_args.args[0] == FAKE_PID
    process.kill.assert_called_once()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only kill path")
@pytest.mark.parametrize("failure", [ProcessLookupError, PermissionError])
def test_kill_process_tree_ignores_missing_group(
    failure: type[OSError],
) -> None:
    """Test that a process group that already exited is ignored."""
    process = MagicMock()
    process.pid = FAKE_PID
    with patch("gatorgrade.shell_runner.os.killpg", side_effect=failure):
        shell_runner._kill_process_tree(process)
    process.kill.assert_called_once()


def test_kill_process_tree_reaps_with_the_grace_period() -> None:
    """Test that a killed process is reaped using the grace period."""
    process = MagicMock()
    process.pid = FAKE_PID
    with (
        patch(RUN_TARGET),
        patch("gatorgrade.shell_runner.os.killpg", create=True),
    ):
        shell_runner._kill_process_tree(process)
    process.wait.assert_called_once_with(timeout=KILL_GRACE_SECONDS)


def test_kill_process_tree_does_not_block_on_unkillable_process() -> None:
    """Test that a process that cannot be reaped does not raise an error."""
    process = MagicMock()
    process.pid = FAKE_PID
    process.wait.side_effect = _deadline_passed()
    with (
        patch(RUN_TARGET),
        patch("gatorgrade.shell_runner.os.killpg", create=True),
    ):
        shell_runner._kill_process_tree(process)
    process.kill.assert_called_once()


@pytest.mark.parametrize(
    "timeout",
    [0.5, 1, CUSTOM_TIMEOUT, DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS],
)
def test_run_shell_command_waits_for_exactly_the_timeout(
    timeout: float, mock_kill: MagicMock
) -> None:
    """Test that the deadline is exactly the timeout, with nothing added or removed."""
    start, process = _fake_popen([0])
    with patch(POPEN_TARGET, side_effect=start):
        outcome = run_shell_command("cmd", timeout=timeout)
    process.wait.assert_called_once_with(timeout=timeout)
    assert outcome.timeout == timeout
    mock_kill.assert_not_called()


def test_run_shell_command_uses_default_timeout(mock_kill: MagicMock) -> None:
    """Test that a command with no timeout gets the default deadline."""
    start, process = _fake_popen([0])
    with patch(POPEN_TARGET, side_effect=start):
        outcome = run_shell_command("cmd")
    process.wait.assert_called_once_with(timeout=DEFAULT_TIMEOUT_SECONDS)
    assert outcome.timeout == DEFAULT_TIMEOUT_SECONDS
    mock_kill.assert_not_called()


def test_run_shell_command_finishing_by_deadline_is_not_timed_out(
    mock_kill: MagicMock,
) -> None:
    """Test that a command that finishes by the deadline keeps its exit code."""
    start, _ = _fake_popen([NONZERO_EXIT], returncode=NONZERO_EXIT)
    with patch(POPEN_TARGET, side_effect=start):
        outcome = run_shell_command("cmd", timeout=CUSTOM_TIMEOUT)
    assert outcome.timed_out is False
    assert outcome.returncode == NONZERO_EXIT
    mock_kill.assert_not_called()


def test_run_shell_command_running_past_deadline_is_timed_out(
    mock_kill: MagicMock,
) -> None:
    """Test that a command past the deadline is killed and has no exit code."""
    start, process = _fake_popen([_deadline_passed()], returncode=KILLED_EXIT)
    with patch(POPEN_TARGET, side_effect=start):
        outcome = run_shell_command("cmd", timeout=CUSTOM_TIMEOUT)
    assert outcome.timed_out is True
    assert outcome.returncode is None
    assert outcome.timeout == CUSTOM_TIMEOUT
    mock_kill.assert_called_once_with(process, None)


def test_run_shell_command_timeout_keeps_partial_output(
    mock_kill: MagicMock,
) -> None:
    """Test that output written before the deadline is kept and decoded."""
    start, _ = _fake_popen(
        [_deadline_passed()], stdout=INVALID_BYTES, stderr=b"err"
    )
    with patch(POPEN_TARGET, side_effect=start):
        outcome = run_shell_command(
            "cmd", timeout=CUSTOM_TIMEOUT, merge_stderr=False
        )
    assert outcome.timed_out is True
    assert outcome.stdout == f"valid{REPLACEMENT_CHAR}output"
    assert outcome.stderr == "err"
    mock_kill.assert_called_once()


def test_run_shell_command_timeout_without_output_is_empty(
    mock_kill: MagicMock,
) -> None:
    """Test that a timeout with no output produces empty strings."""
    start, _ = _fake_popen([_deadline_passed()])
    with patch(POPEN_TARGET, side_effect=start):
        outcome = run_shell_command("cmd", timeout=CUSTOM_TIMEOUT)
    assert outcome.timed_out is True
    assert outcome.stdout == ""
    assert outcome.stderr == ""
    mock_kill.assert_called_once()


def test_run_shell_command_records_elapsed_time(mock_kill: MagicMock) -> None:
    """Test that the outcome reports the time measured around the command."""
    start, _ = _fake_popen([0])
    with (
        patch(POPEN_TARGET, side_effect=start),
        patch("gatorgrade.shell_runner.time") as mock_time,
    ):
        mock_time.monotonic.side_effect = [100.0, 102.5]
        outcome = run_shell_command("cmd")
    assert outcome.elapsed_seconds == pytest.approx(2.5)
    mock_kill.assert_not_called()


def test_run_shell_command_reports_truncated_output(
    mock_kill: MagicMock,
) -> None:
    """Test that the outcome reports when captured output was cut down."""
    start, _ = _fake_popen([0], stdout=b"x" * (SMALL_CAP + 1))
    with patch(POPEN_TARGET, side_effect=start), patch(CAP_TARGET, SMALL_CAP):
        outcome = run_shell_command("cmd")
    assert outcome.output_truncated is True
    assert "output truncated" in outcome.stdout
    mock_kill.assert_not_called()


def test_run_shell_command_reports_truncated_stderr(
    mock_kill: MagicMock,
) -> None:
    """Test that truncation of STDERR alone is also reported."""
    start, _ = _fake_popen([0], stderr=b"x" * (SMALL_CAP + 1))
    with patch(POPEN_TARGET, side_effect=start), patch(CAP_TARGET, SMALL_CAP):
        outcome = run_shell_command("cmd", merge_stderr=False)
    assert outcome.output_truncated is True
    assert "output truncated" in outcome.stderr
    assert "output truncated" not in outcome.stdout
    mock_kill.assert_not_called()


@pytest.mark.parametrize(
    ("merge_stderr", "field", "other_field"),
    [(True, "stdout", "stderr"), (False, "stderr", "stdout")],
)
def test_run_shell_command_start_failure_is_reported(
    merge_stderr: bool, field: str, other_field: str
) -> None:
    """Test that a command that cannot start is reported, not raised."""
    with patch(POPEN_TARGET, side_effect=OSError("too long")):
        outcome = run_shell_command("cmd", merge_stderr=merge_stderr)
    assert outcome.returncode is None
    assert outcome.timed_out is False
    assert outcome.start_error == "Could not start command: too long"
    assert getattr(outcome, field) == outcome.start_error
    assert getattr(outcome, other_field) == ""


def test_run_shell_command_capture_file_failure_is_reported() -> None:
    """Test that being unable to create a capture file is reported, not raised."""
    with patch(TEMPFILE_TARGET, side_effect=OSError("disk full")):
        outcome = run_shell_command("cmd")
    assert outcome.start_error == "Could not start command: disk full"
    assert outcome.returncode is None


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit])
def test_run_shell_command_interruption_kills_tree_and_is_raised(
    interruption: type[BaseException], mock_kill: MagicMock
) -> None:
    """Test that any interruption stops the command tree and is re-raised."""
    start, process = _fake_popen([interruption()])
    with (
        patch(POPEN_TARGET, side_effect=start),
        pytest.raises(interruption),
    ):
        run_shell_command("cmd")
    mock_kill.assert_called_once_with(process, None)


@pytest.mark.parametrize(
    ("wait_effect", "expect_kill"),
    [(0, False), (_deadline_passed(), True)],
)
def test_run_shell_command_closes_job_after_every_result(
    wait_effect: Any, expect_kill: bool
) -> None:
    """Test that the job handle is released and passed to the tree kill."""
    start, process = _fake_popen([wait_effect])
    with (
        patch(POPEN_TARGET, side_effect=start),
        patch(CREATE_JOB_TARGET, return_value=FAKE_JOB) as mock_create,
        patch(CLOSE_JOB_TARGET) as mock_close,
        patch(KILL_TARGET) as mock_kill,
    ):
        run_shell_command("cmd")
    mock_create.assert_called_once_with(FAKE_PID)
    mock_close.assert_called_once_with(FAKE_JOB)
    if expect_kill:
        mock_kill.assert_called_once_with(process, FAKE_JOB)
    else:
        mock_kill.assert_not_called()


def test_run_shell_command_closes_job_after_interruption() -> None:
    """Test that the job handle is released when a run is interrupted."""
    start, _ = _fake_popen([KeyboardInterrupt()])
    with (
        patch(POPEN_TARGET, side_effect=start),
        patch(CREATE_JOB_TARGET, return_value=FAKE_JOB),
        patch(CLOSE_JOB_TARGET) as mock_close,
        patch(KILL_TARGET),
        pytest.raises(KeyboardInterrupt),
    ):
        run_shell_command("cmd")
    mock_close.assert_called_once_with(FAKE_JOB)


def test_run_shell_command_success() -> None:
    """Test that a successful command returns its output and exit code."""
    outcome = run_shell_command('echo "hello"')
    assert outcome.returncode == 0
    assert "hello" in outcome.stdout
    assert outcome.stderr == ""
    assert outcome.timed_out is False
    assert outcome.timeout == DEFAULT_TIMEOUT_SECONDS
    assert outcome.command == 'echo "hello"'
    assert outcome.start_error is None


def test_run_shell_command_nonzero_exit() -> None:
    """Test that a failing command reports its nonzero exit code."""
    outcome = run_shell_command(python_command(f"exit({NONZERO_EXIT})"))
    assert outcome.returncode == NONZERO_EXIT
    assert outcome.timed_out is False


def test_run_shell_command_empty_output() -> None:
    """Test that a command without output produces empty strings."""
    outcome = run_shell_command(python_command("pass"))
    assert outcome.returncode == 0
    assert outcome.stdout == ""
    assert outcome.stderr == ""


def test_run_shell_command_merges_stderr_by_default() -> None:
    """Test that STDERR is captured together with STDOUT by default."""
    outcome = run_shell_command(MIXED_CMD)
    assert outcome.returncode == NONZERO_EXIT
    assert "to-out" in outcome.stdout
    assert "to-err" in outcome.stdout
    assert outcome.stderr == ""


def test_run_shell_command_separates_stderr_when_not_merged() -> None:
    """Test that STDERR is captured separately when merging is disabled."""
    outcome = run_shell_command(MIXED_CMD, merge_stderr=False)
    assert outcome.returncode == NONZERO_EXIT
    assert "to-out" in outcome.stdout
    assert "to-err" not in outcome.stdout
    assert "to-err" in outcome.stderr


def test_run_shell_command_replaces_invalid_bytes() -> None:
    """Test that a command writing invalid UTF-8 does not crash decoding."""
    outcome = run_shell_command(INVALID_BYTES_CMD)
    assert outcome.returncode == 0
    assert outcome.stdout == f"valid{REPLACEMENT_CHAR}output"


def test_run_shell_command_large_output_is_capped() -> None:
    """Test that very large real output keeps its start and end within the cap."""
    size = MAX_CAPTURE_BYTES * 3
    outcome = run_shell_command(
        python_command(
            "import sys; w = sys.stdout.buffer.write; "
            f"w(b'H'); w(b'x' * {size}); w(b'T')"
        )
    )
    assert outcome.returncode == 0
    assert outcome.output_truncated is True
    assert len(outcome.stdout) <= MAX_CAPTURE_BYTES + MARKER_ROOM
    assert outcome.stdout.startswith("H")
    assert outcome.stdout.endswith("T")
    assert "output truncated" in outcome.stdout


def test_run_shell_command_input_is_closed() -> None:
    """Test that a command that reads input fails at once instead of waiting."""
    outcome = run_shell_command(
        python_command("input()"), timeout=INPUT_TIMEOUT
    )
    assert outcome.timed_out is False
    assert outcome.returncode != 0
    assert "EOFError" in outcome.stdout
    assert outcome.elapsed_seconds < INPUT_TIMEOUT


@pytest.mark.timing
@pytest.mark.parametrize("timeout", OVER_LIMIT_TIMEOUTS)
def test_real_command_over_limit_is_not_stopped_early_or_late(
    timeout: float,
) -> None:
    """Test that a slow command runs until its limit and is then stopped promptly."""
    start_time = time.monotonic()
    outcome = run_shell_command(_sleep_command(LONG_SLEEP), timeout=timeout)
    measured = time.monotonic() - start_time
    assert outcome.timed_out is True
    assert outcome.returncode is None
    assert outcome.timeout == timeout
    assert measured >= timeout - CLOCK_TOLERANCE
    assert outcome.elapsed_seconds >= timeout - CLOCK_TOLERANCE
    assert measured <= timeout + KILL_GRACE_SECONDS + TIMING_SLACK


@pytest.mark.timing
def test_real_command_under_limit_passes() -> None:
    """Test that a command well under its limit finishes normally."""
    outcome = run_shell_command(
        _sleep_command(UNDER_LIMIT_SLEEP), timeout=UNDER_LIMIT_TIMEOUT
    )
    assert outcome.timed_out is False
    assert outcome.returncode == 0
    assert "finished" in outcome.stdout


@pytest.mark.timing
def test_real_command_near_limit_passes() -> None:
    """Test that a command close to its limit is allowed to finish."""
    outcome = run_shell_command(
        _sleep_command(NEAR_LIMIT_SLEEP), timeout=NEAR_LIMIT_TIMEOUT
    )
    assert outcome.timed_out is False
    assert outcome.returncode == 0
    assert "finished" in outcome.stdout
    assert outcome.elapsed_seconds >= NEAR_LIMIT_SLEEP - CLOCK_TOLERANCE


@pytest.mark.timing
def test_real_command_within_minimum_timeout_passes() -> None:
    """Test that the smallest allowed timeout still lets a quick command finish."""
    outcome = run_shell_command('echo "quick"', timeout=MINIMUM_TIMEOUT)
    assert outcome.timed_out is False
    assert outcome.returncode == 0
    assert "quick" in outcome.stdout


@pytest.mark.timing
def test_real_command_over_limit_keeps_partial_output() -> None:
    """Test that output written before a real timeout is kept."""
    outcome = run_shell_command(
        python_command(
            "import time; print('started', flush=True); "
            f"time.sleep({LONG_SLEEP})"
        ),
        timeout=PARTIAL_OUTPUT_TIMEOUT,
    )
    assert outcome.timed_out is True
    assert "started" in outcome.stdout


@pytest.mark.timing
def test_real_timeout_kills_child_processes(tmp_path: Path) -> None:
    """Test that a timeout stops a child that the command started."""
    child, waiting_parent, _, pid_file = _write_scripts(tmp_path)
    command = f'{PYTHON} "{waiting_parent}" "{child}" "{pid_file}"'
    outcome = run_shell_command(command, timeout=TREE_TIMEOUT)
    pid = int(pid_file.read_text())
    try:
        assert outcome.timed_out is True
        assert _wait_until_dead(pid) is True
    finally:
        _kill_pid(pid)


@pytest.mark.timing
def test_real_timeout_kills_orphaned_processes(tmp_path: Path) -> None:
    """Test that a timeout stops a process whose own parent has already exited."""
    child, _, spawner, pid_file = _write_scripts(tmp_path)
    command = (
        f'{PYTHON} "{spawner}" "{child}" "{pid_file}" && '
        f"{_sleep_command(LONG_SLEEP)}"
    )
    outcome = run_shell_command(command, timeout=TREE_TIMEOUT)
    pid = int(pid_file.read_text())
    try:
        assert outcome.timed_out is True
        assert _wait_until_dead(pid) is True
    finally:
        _kill_pid(pid)


@pytest.mark.timing
def test_real_background_process_does_not_cause_false_timeout(
    tmp_path: Path,
) -> None:
    """Test that a command that exits while a background process runs still passes."""
    child, _, spawner, pid_file = _write_scripts(tmp_path)
    command = f'{PYTHON} "{spawner}" "{child}" "{pid_file}"'
    outcome = run_shell_command(command, timeout=BACKGROUND_TIMEOUT)
    pid = int(pid_file.read_text())
    try:
        assert outcome.timed_out is False
        assert outcome.returncode == 0
        assert "done" in outcome.stdout
        assert outcome.elapsed_seconds < BACKGROUND_TIMEOUT
        # background processes are only stopped when a command times out,
        # since set up commands may start a server that later checks need
        assert _process_is_alive(pid) is True
    finally:
        _kill_pid(pid)
