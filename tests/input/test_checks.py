"""Test suite for checks.py."""

from gatorgrade.input.checks import GatorGraderCheck
from gatorgrade.input.checks import ShellCheck


def test_shell_check_with_description():
    """Test ShellCheck construction with explicit description."""
    check = ShellCheck(
        command="echo 'test'",
        description="Test shell command",
        json_info={"command": "echo 'test'"},
    )
    assert check.command == "echo 'test'"
    assert check.description == "Test shell command"
    assert check.json_info == {"command": "echo 'test'"}


def test_shell_check_without_description():
    """Test ShellCheck construction without description uses command as description."""
    check = ShellCheck(
        command="echo 'test'",
        json_info={"command": "echo 'test'"},
    )
    assert check.command == "echo 'test'"
    assert check.description == "echo 'test'"
    assert check.json_info == {"command": "echo 'test'"}


def test_shell_check_with_none_description():
    """Test ShellCheck construction with None description uses command as description."""
    check = ShellCheck(
        command="pytest tests/",
        description=None,  # type: ignore
        json_info={"command": "pytest tests/"},
    )
    assert check.command == "pytest tests/"
    assert check.description == "pytest tests/"
    assert check.json_info == {"command": "pytest tests/"}


def test_shell_check_without_json_info():
    """Test ShellCheck construction without json_info."""
    check = ShellCheck(command="ls -la", description="List files")
    assert check.command == "ls -la"
    assert check.description == "List files"
    assert check.json_info is None


def test_gatorgrader_check_construction():
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


def test_gatorgrader_check_with_file_context():
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


def test_gatorgrader_check_empty_args():
    """Test GatorGraderCheck construction with empty arguments."""
    gg_args = []
    json_info = {"check": "EmptyCheck"}
    check = GatorGraderCheck(gg_args=gg_args, json_info=json_info)
    assert check.gg_args == []
    assert check.json_info == {"check": "EmptyCheck"}


def test_shell_check_empty_command():
    """Test ShellCheck construction with empty command."""
    check = ShellCheck(command="", description="Empty command")
    assert check.command == ""
    assert check.description == "Empty command"


def test_shell_check_complex_command():
    """Test ShellCheck construction with complex shell command."""
    command = "find . -name '*.py' | xargs grep -l 'TODO'"
    check = ShellCheck(command=command, description="Find TODOs")
    assert check.command == command
    assert check.description == "Find TODOs"
