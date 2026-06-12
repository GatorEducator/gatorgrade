"""Test suite for checks.py."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade.input.checks import (
    GatorGraderCheck,
    ShellCheck,
    validate_positive_nonzero_int,
)


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
    assert "positive, non-zero integer" in str(exc_info.value)


def test_shell_check_invalid_weight_negative() -> None:
    """Test ShellCheck raises ValueError for negative weight."""
    with pytest.raises(ValueError) as exc_info:
        ShellCheck(command="echo test", weight=-1)
    assert "positive, non-zero integer" in str(exc_info.value)


def test_gatorgrader_check_invalid_weight_zero() -> None:
    """Test GatorGraderCheck raises ValueError for weight of 0."""
    with pytest.raises(ValueError) as exc_info:
        GatorGraderCheck(gg_args=["Test"], json_info={}, weight=0)
    assert "positive, non-zero integer" in str(exc_info.value)


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


def test_shell_check_with_outputlimit() -> None:
    """Test ShellCheck construction with explicit outputlimit."""
    check = ShellCheck(command="echo test", outputlimit=25)
    assert check.outputlimit == 25  # noqa: PLR2004


def test_gatorgrader_check_with_outputlimit() -> None:
    """Test GatorGraderCheck construction with explicit outputlimit."""
    check = GatorGraderCheck(
        gg_args=["Test"], json_info={"check": "Test"}, outputlimit=10
    )
    assert check.outputlimit == 10  # noqa: PLR2004


def test_shell_check_invalid_outputlimit_zero() -> None:
    """Test ShellCheck raises ValueError for outputlimit of 0."""
    with pytest.raises(ValueError) as exc_info:
        ShellCheck(command="echo test", outputlimit=0)
    assert "positive, non-zero integer" in str(exc_info.value)


def test_shell_check_invalid_outputlimit_negative() -> None:
    """Test ShellCheck raises ValueError for negative outputlimit."""
    with pytest.raises(ValueError) as exc_info:
        ShellCheck(command="echo test", outputlimit=-5)
    assert "positive, non-zero integer" in str(exc_info.value)


def test_gatorgrader_check_invalid_outputlimit_zero() -> None:
    """Test GatorGraderCheck raises ValueError for outputlimit of 0."""
    with pytest.raises(ValueError) as exc_info:
        GatorGraderCheck(gg_args=["Test"], json_info={}, outputlimit=0)
    assert "positive, non-zero integer" in str(exc_info.value)


@pytest.mark.propertybased
@given(st.integers(min_value=1, max_value=1000000), st.text(min_size=1))
def test_validate_positive_nonzero_int_valid_property(
    value: int, name: str
) -> None:
    """Property: valid positive integers always return None."""
    assert validate_positive_nonzero_int(value, name) is None


@pytest.mark.propertybased
@given(
    st.integers(max_value=0),
    st.text(min_size=1),
)
def test_validate_positive_nonzero_int_non_positive_property(
    value: int, name: str
) -> None:
    """Property: non-positive integers always return an error containing the field name."""
    result = validate_positive_nonzero_int(value, name)
    assert result is not None
    assert name in result
    assert str(value) in result


@pytest.mark.propertybased
@given(
    st.one_of(st.floats(allow_nan=False), st.text(), st.booleans()),
    st.text(min_size=1),
)
def test_validate_positive_nonzero_int_non_int_property(
    value: float | str | bool, name: str
) -> None:
    """Property: non-int types (including bools) always return an error containing the field name."""
    result = validate_positive_nonzero_int(value, name)  # type: ignore
    assert result is not None
    assert name in result


def test_validate_positive_nonzero_int_rejects_true() -> None:
    """Test that True is rejected even though isinstance(True, int) is True."""
    result = validate_positive_nonzero_int(True, "weight")
    assert result is not None
    assert "True" in result


def test_validate_positive_nonzero_int_rejects_false() -> None:
    """Test that False is rejected even though isinstance(False, int) is True."""
    result = validate_positive_nonzero_int(False, "outputlimit")
    assert result is not None
    assert "False" in result
