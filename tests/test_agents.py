"""Tests for repository guidance in AGENTS.md."""

from pathlib import Path

AGENTS_PATH = Path(__file__).resolve().parents[1] / "AGENTS.md"


def _read_agents() -> str:
    """Read the AGENTS.md file for the current repository."""
    text = AGENTS_PATH.read_text(encoding="utf-8")
    return " ".join(text.split())


def test_agents_recommends_uv_for_environment_and_tasks() -> None:
    """The repository must require uv for dependency and task management."""
    content = _read_agents()

    assert "uv" in content
    assert "Do not use" in content
    assert "pip" in content
    assert "venv" in content
    assert "task all" in content


def test_agents_requires_verification_before_completion() -> None:
    """Agents must validate their changes before finishing work."""
    content = _read_agents()

    assert "Before committing any changes" in content
    assert "linters" in content
    assert "tests" in content
    assert "task all" in content


def test_agents_lists_windows_notification_setup() -> None:
    """The notification instructions must include the Windows BurntToast flow."""
    content = _read_agents()

    assert "BurntToast" in content
    assert "Install-Module" in content
    assert "New-BurntToastNotification" in content
    assert "Windows" in content


def test_agents_mentions_zellij_notification_support() -> None:
    """The repository must mention the optional Zellij notification flow."""
    content = _read_agents()

    assert "zellij" in content
    assert "pipe" in content
    assert "Agent finished" in content
    assert "desktop notification" in content


def test_agents_defines_repo_structure_and_testing_expectations() -> None:
    """The AGENTS.md instructions should describe source, tests, and validation."""
    content = _read_agents()

    assert "gatorgrade/" in content
    assert "tests/" in content
    assert "All test cases should follow these standards" in content


def test_agents_forbids_git_stash() -> None:
    """The repo guidance should explicitly warn against destructive git stash use."""
    content = _read_agents()

    assert "git stash" in content
    assert "Never run" in content


def test_agents_reinforces_uv_task_invocation() -> None:
    """AGENTS.md should reinforce running commands through uv task wrappers."""
    content = _read_agents()

    assert "uv run task all" in content
    assert "uv run task lint" in content
    assert "uv run task test" in content
