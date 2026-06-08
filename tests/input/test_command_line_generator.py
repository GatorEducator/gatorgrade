"""Test suite for command_line_generator.py."""

import pytest

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.input.command_line_generator import generate_checks
from gatorgrade.input.in_file_path import CheckData


def test_generate_checks_with_shell_check() -> None:
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


def test_generate_checks_with_shell_check_no_description() -> None:
    """Test generate_checks creates ShellCheck without description."""
    check_data = CheckData(file_context=None, check={"command": "ls -la"})
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], ShellCheck)
    assert checks[0].command == "ls -la"
    assert checks[0].description == "ls -la"


def test_generate_checks_with_gatorgrader_check() -> None:
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


def test_generate_checks_with_file_context() -> None:
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


def test_generate_checks_with_file_context_no_directory() -> None:
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


def test_generate_checks_with_boolean_option_true() -> None:
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
    assert exact_index == len(gg_args) - 1 or not gg_args[
        exact_index + 1
    ].startswith("--")


def test_generate_checks_with_boolean_option_false() -> None:
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


def test_generate_checks_with_no_description() -> None:
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


def test_generate_checks_with_no_options() -> None:
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


def test_generate_checks_multiple_checks() -> None:
    """Test generate_checks handles multiple checks."""
    check_data_list = [
        CheckData(file_context=None, check={"command": "echo 'test'"}),
        CheckData(
            file_context=None,
            check={
                "check": "MatchFileFragment",
                "options": {"fragment": "TODO"},
            },
        ),
        CheckData(file_context=None, check={"command": "ls -la"}),
    ]
    checks = generate_checks(check_data_list)
    total_checks = 3
    assert len(checks) == total_checks
    assert isinstance(checks[0], ShellCheck)
    assert isinstance(checks[1], GatorGraderCheck)
    assert isinstance(checks[2], ShellCheck)


def test_generate_checks_empty_list() -> None:
    """Test generate_checks handles empty check data list."""
    checks = generate_checks([])
    assert len(checks) == 0
    assert checks == []


def test_generate_checks_with_shell_check_weight() -> None:
    """Test generate_checks parses weight for shell check."""
    check_data = CheckData(
        file_context=None,
        check={
            "command": "echo 'hello'",
            "description": "Echo hello",
            "weight": 10,
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], ShellCheck)
    assert checks[0].weight == 10  # noqa: PLR2004


def test_generate_checks_with_gatorgrader_check_weight() -> None:
    """Test generate_checks parses weight for GatorGrader check."""
    check_data = CheckData(
        file_context=None,
        check={
            "check": "MatchFileFragment",
            "description": "Check fragment",
            "weight": 5,
            "options": {"fragment": "TODO", "count": 0},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert checks[0].weight == 5  # noqa: PLR2004


def test_generate_checks_with_default_weight() -> None:
    """Test generate_checks defaults weight to 1 when not specified."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'"},
    )
    checks = generate_checks([check_data])
    assert checks[0].weight == 1


def test_generate_checks_with_invalid_weight_zero() -> None:
    """Test generate_checks raises ValueError for weight of 0."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'", "weight": 0},
    )
    with pytest.raises(ValueError) as exc_info:
        generate_checks([check_data])
    assert "Configuration error" in str(exc_info.value)
    assert "positive, non-zero integer" in str(exc_info.value)


def test_generate_checks_with_invalid_weight_negative() -> None:
    """Test generate_checks raises ValueError for negative weight."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'", "weight": -2},
    )
    with pytest.raises(ValueError) as exc_info:
        generate_checks([check_data])
    assert "Configuration error" in str(exc_info.value)
    assert "positive, non-zero integer" in str(exc_info.value)


def test_generate_checks_with_invalid_outputlimit_zero() -> None:
    """Test generate_checks raises ValueError for outputlimit of 0."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'", "outputlimit": 0},
    )
    with pytest.raises(ValueError) as exc_info:
        generate_checks([check_data])
    assert "Configuration error" in str(exc_info.value)
    assert "positive, non-zero integer" in str(exc_info.value)


def test_generate_checks_with_invalid_outputlimit_negative() -> None:
    """Test generate_checks raises ValueError for negative outputlimit."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'", "outputlimit": -5},
    )
    with pytest.raises(ValueError) as exc_info:
        generate_checks([check_data])
    assert "Configuration error" in str(exc_info.value)
    assert "positive, non-zero integer" in str(exc_info.value)


def test_generate_checks_with_string_count_option() -> None:
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


def test_generate_checks_with_shell_check_outputlimit() -> None:
    """Test generate_checks parses outputlimit for shell check."""
    check_data = CheckData(
        file_context=None,
        check={
            "command": "echo 'hello'",
            "outputlimit": 25,
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], ShellCheck)
    assert checks[0].outputlimit == 25  # noqa: PLR2004


def test_generate_checks_with_gatorgrader_check_outputlimit() -> None:
    """Test generate_checks parses outputlimit for GatorGrader check."""
    check_data = CheckData(
        file_context=None,
        check={
            "check": "MatchFileFragment",
            "outputlimit": 10,
            "options": {"fragment": "TODO", "count": 0},
        },
    )
    checks = generate_checks([check_data])
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert checks[0].outputlimit == 10  # noqa: PLR2004


def test_generate_checks_with_default_outputlimit() -> None:
    """Test generate_checks defaults outputlimit to None when not specified."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'"},
    )
    checks = generate_checks([check_data])
    assert checks[0].outputlimit is None


def test_generate_checks_with_baseline_weight() -> None:
    """Test generate_checks uses baseline_weight when check has no explicit weight."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'"},
    )
    checks = generate_checks([check_data], baseline_weight=5)
    assert len(checks) == 1
    assert checks[0].weight == 5  # noqa: PLR2004


def test_generate_checks_with_baseline_weight_and_explicit_weight() -> None:
    """Test generate_checks uses explicit weight over baseline_weight."""
    check_data = CheckData(
        file_context=None,
        check={"command": "echo 'hello'", "weight": 10},
    )
    checks = generate_checks([check_data], baseline_weight=5)
    assert len(checks) == 1
    assert checks[0].weight == 10  # noqa: PLR2004


def test_generate_checks_with_baseline_weight_for_gg_check() -> None:
    """Test generate_checks uses baseline_weight for GatorGrader checks."""
    check_data = CheckData(
        file_context=None,
        check={"check": "CountCommits", "options": {"count": 5}},
    )
    checks = generate_checks([check_data], baseline_weight=3)
    assert len(checks) == 1
    assert isinstance(checks[0], GatorGraderCheck)
    assert checks[0].weight == 3  # noqa: PLR2004
