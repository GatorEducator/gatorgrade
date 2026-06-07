"""Test suite for checks.py."""

import pytest

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck


def test_shell_check_with_description() -> None:
    """Test ShellCheck construction with explicit description."""
    check = ShellCheck(
        command="echo 'test'",
        description="Test shell command",
        json_info={"command": "echo 'test'"},
    )
    assert check.command == "echo 'test'"
    assert check.description == "Test shell command"
    assert check.json_info == {"command": "echo 'test'"}


def test_shell_check_without_description() -> None:
    """Test ShellCheck construction without description uses command as description."""
    check = ShellCheck(
        command="echo 'test'",
        json_info={"command": "echo 'test'"},
    )
    assert check.command == "echo 'test'"
    assert check.description == "echo 'test'"
    assert check.json_info == {"command": "echo 'test'"}


def test_shell_check_with_none_description() -> None:
    """Test ShellCheck construction with None description uses command as description."""
    check = ShellCheck(
        command="pytest tests/",
        description=None,
        json_info={"command": "pytest tests/"},
    )
    assert check.command == "pytest tests/"
    assert check.description == "pytest tests/"
    assert check.json_info == {"command": "pytest tests/"}


def test_shell_check_without_json_info() -> None:
    """Test ShellCheck construction without json_info."""
    check = ShellCheck(command="ls -la", description="List files")
    assert check.command == "ls -la"
    assert check.description == "List files"
    assert check.json_info is None


def test_gatorgrader_check_construction() -> None:
    """Test GatorGraderCheck construction with arguments."""
    gg_args = [
        "--description",
        "Test check",
        "MatchFileFragment",
        "--fragment",
        "TODO",
        "--count",
        "0",
    ]
    json_info = {"check": "MatchFileFragment", "description": "Test check"}
    check = GatorGraderCheck(gg_args=gg_args, json_info=json_info)
    assert check.gg_args == gg_args
    assert check.json_info == json_info


def test_gatorgrader_check_with_file_context() -> None:
    """Test GatorGraderCheck construction with file context."""
    gg_args = [
        "--description",
        "Check file",
        "MatchFileFragment",
        "--fragment",
        "print(",
        "--count",
        "1",
        "--directory",
        "src",
        "--file",
        "main.py",
    ]
    json_info = {
        "check": "MatchFileFragment",
        "description": "Check file",
        "options": {"fragment": "print(", "count": 1},
    }
    check = GatorGraderCheck(gg_args=gg_args, json_info=json_info)
    assert check.gg_args == gg_args
    assert check.json_info == json_info
    assert "--directory" in check.gg_args
    assert "--file" in check.gg_args


def test_gatorgrader_check_empty_args() -> None:
    """Test GatorGraderCheck construction with empty arguments."""
    gg_args = []
    json_info = {"check": "EmptyCheck"}
    check = GatorGraderCheck(gg_args=gg_args, json_info=json_info)
    assert check.gg_args == []
    assert check.json_info == {"check": "EmptyCheck"}


def test_shell_check_with_weight() -> None:
    """Test ShellCheck construction with explicit weight."""
    check = ShellCheck(
        command="echo test",
        description="Test shell command",
        weight=10,
    )
    assert check.weight == 10  # noqa: PLR2004


def test_gatorgrader_check_with_weight() -> None:
    """Test GatorGraderCheck construction with explicit weight."""
    gg_args = ["MatchFileFragment"]
    json_info = {"check": "MatchFileFragment"}
    check = GatorGraderCheck(gg_args=gg_args, json_info=json_info, weight=5)
    assert check.weight == 5  # noqa: PLR2004


def test_shell_check_invalid_weight_zero() -> None:
    """Test ShellCheck raises ValueError for weight of 0."""
    with pytest.raises(ValueError) as exc_info:
        ShellCheck(command="echo test", weight=0)
    assert "greater than 0" in str(exc_info.value)


def test_shell_check_invalid_weight_negative() -> None:
    """Test ShellCheck raises ValueError for negative weight."""
    with pytest.raises(ValueError) as exc_info:
        ShellCheck(command="echo test", weight=-1)
    assert "greater than 0" in str(exc_info.value)


def test_gatorgrader_check_invalid_weight_zero() -> None:
    """Test GatorGraderCheck raises ValueError for weight of 0."""
    with pytest.raises(ValueError) as exc_info:
        GatorGraderCheck(gg_args=["Test"], json_info={}, weight=0)
    assert "greater than 0" in str(exc_info.value)


def test_shell_check_empty_command() -> None:
    """Test ShellCheck construction with empty command."""
    check = ShellCheck(command="", description="Empty command")
    assert check.command == ""
    assert check.description == "Empty command"


def test_shell_check_complex_command() -> None:
    """Test ShellCheck construction with complex shell command."""
    command = "find . -name '*.py' | xargs grep -l 'TODO'"
    check = ShellCheck(command=command, description="Find TODOs")
    assert check.command == command
    assert check.description == "Find TODOs"


def test_shell_check_empty_string_description_uses_empty_string() -> None:
    """Test that ShellCheck with empty string description keeps the empty string."""
    check = ShellCheck(
        command="echo test",
        description="",
        json_info={"command": "echo test"},
    )
    assert check.command == "echo test"
    assert check.description == ""


def test_shell_check_with_dict_json_info() -> None:
    """Test ShellCheck with dictionary json_info preserves all data."""
    json_data = {
        "command": "echo test",
        "description": "Test",
        "extra": "data",
    }
    check = ShellCheck(command="echo test", json_info=json_data)
    assert check.json_info == json_data


def test_gatorgrader_check_with_single_arg() -> None:
    """Test GatorGraderCheck construction with a single argument."""
    check = GatorGraderCheck(
        gg_args=["MatchFileFragment"],
        json_info={"check": "MatchFileFragment"},
    )
    assert check.gg_args == ["MatchFileFragment"]
    assert len(check.gg_args) == 1
