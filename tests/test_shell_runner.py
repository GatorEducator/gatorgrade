"""Test suite for the shared shell command runner."""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from gatorgrade import shell_runner
from gatorgrade.shell_runner import (
    DEFAULT_TIMEOUT_SECONDS,
    KILL_GRACE_SECONDS,
    CommandOutcome,
    decode_output,
    run_shell_command,
)

PYTHON = f'"{sys.executable}"'
SLEEP_CMD = f'{PYTHON} -c "import time; time.sleep(5)"'
PARTIAL_THEN_SLEEP_CMD = (
    f"{PYTHON} -c \"import time; print('started', flush=True); time.sleep(5)\""
)
MIXED_CMD = (
    f"{PYTHON} -c \"import sys; print('to-out'); "
    "print('to-err', file=sys.stderr); sys.exit(3)\""
)
INVALID_BYTES_CMD = (
    f"{PYTHON} -c \"import sys; sys.stdout.buffer.write(b'valid\\xffoutput')\""
)
SHORT_TIMEOUT = 1
CUSTOM_TIMEOUT = 42
NONZERO_EXIT = 3
FAKE_PID = 12345
INVALID_BYTES = b"valid\xffoutput"
REPLACEMENT_CHAR = "�"
POPEN_TARGET = "gatorgrade.shell_runner.subprocess.Popen"
KILL_TARGET = "gatorgrade.shell_runner._kill_process_tree"


def _fake_process(communicate_effects: list) -> MagicMock:
    """Create a fake Popen object whose communicate calls follow the given effects."""
    process = MagicMock()
    process.pid = FAKE_PID
    process.returncode = 0
    process.communicate.side_effect = communicate_effects
    return process


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


def test_run_shell_command_success() -> None:
    """Test that a successful command returns its output and exit code."""
    outcome = run_shell_command('echo "hello"')
    assert outcome.returncode == 0
    assert "hello" in outcome.stdout
    assert outcome.stderr == ""
    assert outcome.timed_out is False
    assert outcome.timeout == DEFAULT_TIMEOUT_SECONDS
    assert outcome.command == 'echo "hello"'


def test_run_shell_command_nonzero_exit() -> None:
    """Test that a failing command reports its nonzero exit code."""
    outcome = run_shell_command(f'{PYTHON} -c "exit({NONZERO_EXIT})"')
    assert outcome.returncode == NONZERO_EXIT
    assert outcome.timed_out is False


def test_run_shell_command_empty_output() -> None:
    """Test that a command without output produces empty strings."""
    outcome = run_shell_command(f'{PYTHON} -c "pass"')
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


def test_run_shell_command_real_timeout() -> None:
    """Test that a real slow command is stopped and reported as timed out."""
    outcome = run_shell_command(SLEEP_CMD, timeout=SHORT_TIMEOUT)
    assert outcome.timed_out is True
    assert outcome.returncode is None
    assert outcome.timeout == SHORT_TIMEOUT


def test_run_shell_command_real_timeout_keeps_partial_output() -> None:
    """Test that output written before a real timeout is kept."""
    outcome = run_shell_command(PARTIAL_THEN_SLEEP_CMD, timeout=SHORT_TIMEOUT)
    assert outcome.timed_out is True
    assert "started" in outcome.stdout


def test_run_shell_command_timeout_with_partial_output() -> None:
    """Test that partial output collected after the kill is decoded."""
    process = _fake_process(
        [
            subprocess.TimeoutExpired(cmd="slow", timeout=CUSTOM_TIMEOUT),
            (INVALID_BYTES, b"err"),
        ]
    )
    with (
        patch(POPEN_TARGET, return_value=process),
        patch(KILL_TARGET) as mock_kill,
    ):
        outcome = run_shell_command(
            "slow", timeout=CUSTOM_TIMEOUT, merge_stderr=False
        )
    mock_kill.assert_called_once_with(process)
    assert outcome.timed_out is True
    assert outcome.returncode is None
    assert outcome.timeout == CUSTOM_TIMEOUT
    assert outcome.stdout == f"valid{REPLACEMENT_CHAR}output"
    assert outcome.stderr == "err"


def test_run_shell_command_timeout_falls_back_to_exception_output() -> None:
    """Test that output stored on the timeout exception is used as a fallback."""
    timeout_error = subprocess.TimeoutExpired(
        cmd="slow", timeout=CUSTOM_TIMEOUT, output=b"early", stderr=b"oops"
    )
    process = _fake_process([timeout_error, (None, None)])
    with patch(POPEN_TARGET, return_value=process), patch(KILL_TARGET):
        outcome = run_shell_command("slow", timeout=CUSTOM_TIMEOUT)
    assert outcome.timed_out is True
    assert outcome.stdout == "early"
    assert outcome.stderr == "oops"


def test_run_shell_command_timeout_without_partial_output() -> None:
    """Test that a timeout with no output produces empty strings."""
    process = _fake_process(
        [
            subprocess.TimeoutExpired(cmd="slow", timeout=CUSTOM_TIMEOUT),
            (None, None),
        ]
    )
    with patch(POPEN_TARGET, return_value=process), patch(KILL_TARGET):
        outcome = run_shell_command("slow", timeout=CUSTOM_TIMEOUT)
    assert outcome.timed_out is True
    assert outcome.stdout == ""
    assert outcome.stderr == ""


def test_run_shell_command_timeout_when_drain_hangs() -> None:
    """Test that a hung read after the kill gives up instead of waiting forever."""
    process = _fake_process(
        [
            subprocess.TimeoutExpired(cmd="slow", timeout=CUSTOM_TIMEOUT),
            subprocess.TimeoutExpired(cmd="slow", timeout=KILL_GRACE_SECONDS),
        ]
    )
    with patch(POPEN_TARGET, return_value=process), patch(KILL_TARGET):
        outcome = run_shell_command("slow", timeout=CUSTOM_TIMEOUT)
    assert outcome.timed_out is True
    assert outcome.stdout == ""
    process.communicate.assert_called_with(timeout=KILL_GRACE_SECONDS)


def test_run_shell_command_keyboard_interrupt_kills_tree() -> None:
    """Test that an interrupt stops the command tree and is re-raised."""
    process = _fake_process([KeyboardInterrupt()])
    with (
        patch(POPEN_TARGET, return_value=process),
        patch(KILL_TARGET) as mock_kill,
        pytest.raises(KeyboardInterrupt),
    ):
        run_shell_command("slow")
    mock_kill.assert_called_once_with(process)


def test_start_process_uses_new_process_group() -> None:
    """Test that the command starts in its own process group or session."""
    with patch(POPEN_TARGET) as mock_popen:
        shell_runner._start_process("cmd", merge_stderr=True)
    kwargs = mock_popen.call_args.kwargs
    assert kwargs["shell"] is True
    assert kwargs["stderr"] == subprocess.STDOUT
    if sys.platform == "win32":
        assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        assert kwargs["start_new_session"] is True


def test_start_process_pipes_stderr_when_not_merged() -> None:
    """Test that STDERR gets its own pipe when merging is disabled."""
    with patch(POPEN_TARGET) as mock_popen:
        shell_runner._start_process("cmd", merge_stderr=False)
    assert mock_popen.call_args.kwargs["stderr"] == subprocess.PIPE


def test_kill_process_tree_kills_tree_and_shell() -> None:
    """Test that both the whole process tree and the shell are killed."""
    process = MagicMock()
    process.pid = FAKE_PID
    if sys.platform == "win32":
        with patch("gatorgrade.shell_runner.subprocess.run") as mock_run:
            shell_runner._kill_process_tree(process)
        command = mock_run.call_args.args[0]
        assert command[0] == shell_runner.TASKKILL_COMMAND
        assert shell_runner.TASKKILL_TREE_FLAG in command
        assert str(FAKE_PID) in command
    else:
        with patch("gatorgrade.shell_runner.os.killpg") as mock_killpg:
            shell_runner._kill_process_tree(process)
        mock_killpg.assert_called_once()
        assert mock_killpg.call_args.args[0] == FAKE_PID
    process.kill.assert_called_once()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only kill path")
def test_kill_process_tree_ignores_missing_group() -> None:
    """Test that a process group that already exited is ignored."""
    process = MagicMock()
    process.pid = FAKE_PID
    with patch(
        "gatorgrade.shell_runner.os.killpg", side_effect=ProcessLookupError
    ):
        shell_runner._kill_process_tree(process)
    process.kill.assert_called_once()
