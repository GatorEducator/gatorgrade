"""Test suite for set_up_shell.py."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from typer import Exit

from gatorgrade.input.set_up_shell import run_setup


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


def test_run_setup_with_stderr_output() -> None:
    """Test run_setup captures stderr output."""
    front_matter = {
        "setup": "echo 'stdout message'\necho 'stderr message' >&2"
    }
    try:
        run_setup(front_matter)
    except Exception:
        pytest.fail(
            "Calling run_setup with stderr-producing commands raised an unexpected exception"
        )


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
def test_run_setup_with_commands_property(commands: str) -> None:
    """Property: run_setup with setup commands never raises outside of typer.Exit."""
    front_matter = {"setup": commands}
    try:
        run_setup(front_matter)
    except Exit:
        pass
    except Exception:
        pytest.fail("run_setup raised an unexpected exception")
