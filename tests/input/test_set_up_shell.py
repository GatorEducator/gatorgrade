"""Test suite for set_up_shell.py."""

import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from typer import Exit

from gatorgrade.input import set_up_shell
from gatorgrade.input.set_up_shell import run_setup
from gatorgrade.shell_runner import DEFAULT_TIMEOUT_SECONDS, CommandOutcome

PYTHON = f'"{sys.executable}"'
SLEEP_CMD = f'{PYTHON} -c "import time; time.sleep(5)"'
INVALID_BYTES_CMD = (
    f'{PYTHON} -c "import sys; '
    "sys.stdout.buffer.write(b'out\\xffbytes'); sys.stdout.flush(); "
    "sys.stderr.buffer.write(b'err\\xffbytes'); sys.exit(1)\""
)
SHORT_TIMEOUT = 1
CUSTOM_TIMEOUT = 42


def _outcome(  # noqa: PLR0913
    command: str,
    returncode: int | None,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> CommandOutcome:
    """Create a CommandOutcome for a faked setup command."""
    return CommandOutcome(
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        timeout=timeout,
    )


def _flatten(text: str) -> str:
    """Collapse all whitespace so rich line wrapping cannot split a phrase."""
    return " ".join(text.split())


def test_run_setup_with_no_setup_commands() -> None:
    """Test run_setup with empty front matter."""
    front_matter = {}
    try:
        run_setup(front_matter)
    except Exception:
        pytest.fail("Calling run_setup raised an unexpected exception")


def test_run_setup_with_successful_commands() -> None:
    """Test run_setup with successful shell commands."""
    front_matter = {"setup": "echo 'Hello World'\necho 'Test Command'"}
    try:
        run_setup(front_matter)
    except Exception:
        pytest.fail(
            "Calling run_setup with non-empty front matter raised an unexpected exception"
        )


def test_run_setup_with_stderr_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_setup captures and displays stderr output."""
    front_matter = {
        "setup": "echo 'stdout message'\necho 'stderr message' >&2"
    }
    try:
        run_setup(front_matter)
    except Exception:
        pytest.fail(
            "Calling run_setup with stderr-producing commands raised an unexpected exception"
        )
    out, _ = capsys.readouterr()
    assert "stderr message" in out


def test_run_setup_with_whitespace_in_commands() -> None:
    """Test run_setup handles commands with whitespace correctly."""
    front_matter = {"setup": "  echo 'Test'  \n  echo 'Another test'  "}
    try:
        run_setup(front_matter)
    except Exception:
        pytest.fail(
            "Calling run_setup with non-empty front matter raised an unexpected exception"
        )


def test_run_setup_with_failing_command() -> None:
    """Test run_setup with a failing shell command."""
    front_matter = {"setup": "false"}
    with pytest.raises(Exit) as exc_info:
        run_setup(front_matter)
    assert exc_info.value.exit_code == 1


def test_run_setup_with_mixed_commands() -> None:
    """Test run_setup with mix of successful and failing commands."""
    front_matter = {"setup": "echo 'First command'\nfalse"}
    with pytest.raises(Exit) as exc_info:
        run_setup(front_matter)
    assert exc_info.value.exit_code == 1


def test_run_setup_timeout_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Setup timeouts stop setup without a traceback and report the command."""
    outcome = _outcome("sleep 301", None, timed_out=True)
    monkeypatch.setattr(
        set_up_shell, "run_shell_command", lambda *_a, **_k: outcome
    )
    with pytest.raises(Exit) as exc_info:
        run_setup({"setup": "sleep 301", "setup_timeout": 300})
    assert exc_info.value.exit_code == 1
    out = _flatten(capsys.readouterr().out)
    assert "sleep 301" in out
    assert "timed out after 300 second(s)" in out


def test_run_setup_timeout_shows_partial_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Output written before a setup timeout is shown above the message."""
    outcome = _outcome(
        "slow", None, stdout="installing\n", stderr="warn\n", timed_out=True
    )
    monkeypatch.setattr(
        set_up_shell, "run_shell_command", lambda *_a, **_k: outcome
    )
    with pytest.raises(Exit):
        run_setup({"setup": "slow"})
    out = _flatten(capsys.readouterr().out)
    assert "installing" in out
    assert "warn" in out
    assert out.index("installing") < out.index("timed out after")


def test_run_setup_real_timeout_exits_cleanly(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A real slow setup command is stopped after setup_timeout seconds."""
    with pytest.raises(Exit) as exc_info:
        run_setup({"setup": SLEEP_CMD, "setup_timeout": SHORT_TIMEOUT})
    assert exc_info.value.exit_code == 1
    out = _flatten(capsys.readouterr().out)
    assert f"timed out after {SHORT_TIMEOUT} second(s)" in out


def test_run_setup_passes_timeout_to_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The setup_timeout value reaches the runner with STDERR kept separate."""
    calls: list[dict] = []

    def fake_runner(command: str, **kwargs: object) -> CommandOutcome:
        calls.append({"command": command, **kwargs})
        return _outcome(command, 0)

    monkeypatch.setattr(set_up_shell, "run_shell_command", fake_runner)
    run_setup({"setup": "first\nsecond", "setup_timeout": CUSTOM_TIMEOUT})
    assert calls == [
        {"command": "first", "timeout": CUSTOM_TIMEOUT, "merge_stderr": False},
        {
            "command": "second",
            "timeout": CUSTOM_TIMEOUT,
            "merge_stderr": False,
        },
    ]


def test_run_setup_uses_default_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setup commands use the default timeout when none is configured."""
    timeouts: list[object] = []

    def fake_runner(command: str, **kwargs: object) -> CommandOutcome:
        timeouts.append(kwargs["timeout"])
        return _outcome(command, 0)

    monkeypatch.setattr(set_up_shell, "run_shell_command", fake_runner)
    run_setup({"setup": "first"})
    assert timeouts == [DEFAULT_TIMEOUT_SECONDS]


def test_run_setup_skips_blank_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank lines in the setup block are not run as commands."""
    commands: list[str] = []

    def fake_runner(command: str, **_kwargs: object) -> CommandOutcome:
        commands.append(command)
        return _outcome(command, 0)

    monkeypatch.setattr(set_up_shell, "run_shell_command", fake_runner)
    run_setup({"setup": "first\n\n   \nsecond"})
    assert commands == ["first", "second"]


@pytest.mark.parametrize("bad_timeout", [0, -5, True, "60", 1.5])
def test_run_setup_invalid_setup_timeout_raises(bad_timeout: object) -> None:
    """An invalid setup_timeout is rejected before any command runs."""
    with pytest.raises(ValueError, match="setup_timeout"):
        run_setup({"setup": "echo hi", "setup_timeout": bad_timeout})


def test_run_setup_invalid_bytes_do_not_crash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid UTF-8 in STDOUT and STDERR is replaced instead of crashing."""
    with pytest.raises(Exit):
        run_setup({"setup": INVALID_BYTES_CMD})
    out, _ = capsys.readouterr()
    assert "out�bytes" in out
    assert "err�bytes" in out


@pytest.mark.propertybased
@given(st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=20)))
def test_run_setup_no_setup_key_property(front_matter: dict) -> None:
    """Property: front matter without a 'setup' key never crashes."""
    if "setup" not in front_matter:
        try:
            run_setup(front_matter)
        except Exception:
            pytest.fail("run_setup raised an unexpected exception")


@pytest.mark.propertybased
@given(
    st.lists(
        st.sampled_from(["true", "false", "echo hello", "echo test"]),
        min_size=1,
        max_size=4,
    ).map("\n".join),
)
# each example starts up to four real processes, which can take longer than
# the default per-example deadline on a slow or busy machine
@settings(deadline=None)
def test_run_setup_with_commands_property(commands: str) -> None:
    """Property: run_setup with setup commands never raises outside of typer.Exit."""
    front_matter = {"setup": commands}
    try:
        run_setup(front_matter)
    except Exit:
        pass
    except Exception:
        pytest.fail("run_setup raised an unexpected exception")
