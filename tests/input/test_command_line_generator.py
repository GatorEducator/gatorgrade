"""Test suite for command_line_generator.py."""

from gatorgrade.input.checks import GatorGraderCheck
from gatorgrade.input.checks import ShellCheck
from gatorgrade.input.command_line_generator import generate_checks
from gatorgrade.input.in_file_path import CheckData


def test_generate_checks_with_shell_check():
    """Test generate_checks creates ShellCheck from check data."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'", "description": "Echo hello"},
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], ShellCheck)
    assert checks[0].command == "echo 'hello'"
    assert checks[0].description == "Echo hello"


def test_generate_checks_with_shell_check_no_description():
    """Test generate_checks creates ShellCheck without description."""
    check_data = CheckData(file_context=None, check={"command": "ls -la"})
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], ShellCheck)
    assert checks[0].command == "ls -la"
    assert checks[0].description == "ls -la"


def test_generate_checks_with_gatorgrader_check():
    """Test generate_checks creates GatorGraderCheck from check data."""
    check_data = CheckData(
        file_context=None,
        check={
            "check": "MatchFileFragment",
            "description": "Check fragment",
            "options": {"fragment": "TODO", "count": 0},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "--description" in checks[0].gg_args
    assert "Check fragment" in checks[0].gg_args
    assert "MatchFileFragment" in checks[0].gg_args
    assert "--fragment" in checks[0].gg_args
    assert "TODO" in checks[0].gg_args


def test_generate_checks_with_file_context():
    """Test generate_checks adds directory and file to GatorGrader check."""
    check_data = CheckData(
        file_context="src/main.py",
        check={
            "check": "MatchFileFragment",
            "description": "Check file",
            "options": {"fragment": "print(", "count": 1},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "--directory" in checks[0].gg_args
    assert "src" in checks[0].gg_args
    assert "--file" in checks[0].gg_args
    assert "main.py" in checks[0].gg_args


def test_generate_checks_with_file_context_no_directory():
    """Test generate_checks handles file with no directory path."""
    check_data = CheckData(
        file_context="README.md",
        check={
            "check": "MatchFileFragment",
            "options": {"fragment": "TODO", "count": 0},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "--directory" in checks[0].gg_args
    assert "." in checks[0].gg_args
    assert "--file" in checks[0].gg_args
    assert "README.md" in checks[0].gg_args


def test_generate_checks_with_boolean_option_true():
    """Test generate_checks handles boolean option set to True."""
    check_data = CheckData(
        file_context=None,
        check={
            "check": "MatchFileFragment",
            "options": {"fragment": "TODO", "count": 0, "exact": True},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "--exact" in checks[0].gg_args
    gg_args = checks[0].gg_args
    exact_index = gg_args.index("--exact")
    assert exact_index == len(gg_args) - 1 or not gg_args[exact_index + 1].startswith(
        "--"
    )


def test_generate_checks_with_boolean_option_false():
    """Test generate_checks handles boolean option set to False."""
    check_data = CheckData(
        file_context=None,
        check={
            "check": "MatchFileFragment",
            "options": {"fragment": "TODO", "count": 0, "exact": False},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "--exact" not in checks[0].gg_args


def test_generate_checks_with_no_description():
    """Test generate_checks creates GatorGrader check without description."""
    check_data = CheckData(
        file_context=None,
        check={"check": "CountCommits", "options": {"count": 5}},
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "--description" not in checks[0].gg_args
    assert "CountCommits" in checks[0].gg_args


def test_generate_checks_with_no_options():
    """Test generate_checks creates GatorGrader check without options."""
    check_data = CheckData(
        file_context=None,
        check={"check": "CountCommits", "description": "Check commits"},
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "CountCommits" in checks[0].gg_args
    assert "--description" in checks[0].gg_args


def test_generate_checks_multiple_checks():
    """Test generate_checks handles multiple checks."""
    check_data_list = [
        CheckData(file_context=None, check={"command": "echo 'test'"}),
        CheckData(
            file_context=None,
            check={"check": "MatchFileFragment", "options": {"fragment": "TODO"}},
        ),
        CheckData(file_context=None, check={"command": "ls -la"}),
    ]
    checks = generate_checks(check_data_list)
    assert len(checks) == 3
    assert isinstance(checks[0], ShellCheck)
    assert isinstance(checks[1], GatorGraderCheck)
    assert isinstance(checks[2], ShellCheck)


def test_generate_checks_empty_list():
    """Test generate_checks handles empty check data list."""
    checks = generate_checks([])
    assert len(checks) == 0
    assert checks == []


def test_generate_checks_with_string_count_option():
    """Test generate_checks converts numeric option values to strings."""
    check_data = CheckData(
        file_context=None,
        check={
            "check": "MatchFileFragment",
            "options": {"fragment": "TODO", "count": 5},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert "--count" in checks[0].gg_args
    count_index = checks[0].gg_args.index("--count")
    assert checks[0].gg_args[count_index + 1] == "5"
