"""Test suite for parse_config function."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.input.in_file_path import reformat_yaml_data
from gatorgrade.input.parse_config import parse_config


def test_parse_config_returns_error_for_invalid_yaml(tmp_path: Path) -> None:
    """Test parse_config returns an error message for invalid YAML content."""
    # given an invalid YAML file
    invalid_yaml = tmp_path / "invalid.yml"
    invalid_yaml.write_text("*invalid: yaml: [content")
    # when parse_config is run
    checks, error = parse_config(invalid_yaml)
    # then checks is empty and error contains details
    assert checks == []
    assert error is not None
    assert isinstance(error, str)
    assert len(error) > 0


def test_parse_config_gg_check_in_file_context_contains_file() -> None:
    """Test to make sure that the file context is included in the GatorGrader arguments."""
    # given a configuration file with a GatorGrader check within a file context
    config = Path(
        "tests/input/yml_test_files/gatorgrade_one_gg_check_in_file.yml"
    )
    # when parse_config is run
    output, _ = parse_config(config)
    # then the file path should be in the GatorGrader arguments
    assert isinstance(output[0], GatorGraderCheck)
    assert "file.py" in output[0].gg_args


def test_parse_config_check_gg_matchfilefragment() -> None:
    """Test to make sure the description, check name, and options appear in the GatorGrader arguments."""
    # given a configuration file with a GatorGrader check
    config = Path(
        "tests/input/yml_test_files/gatorgrade_matchfilefragment.yml"
    )
    # when parse_config is run
    output, _ = parse_config(config)
    # then the description, check name, and options appear in the GatorGrader arguments
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].gg_args == [
        "--description",
        "Complete all TODOs",
        "MatchFileFragment",
        "--fragment",
        "TODO",
        "--count",
        "0",
        "--exact",
        "--directory",
        "path/to",
        "--file",
        "file.py",
    ]


def test_parse_config_gg_check_no_file_context_contains_no_file() -> None:
    """Test to make sure checks without a file context do not have a file path in GatorGrader arguments."""
    # given a configuration file with a GatorGrader check without a file context
    config = Path(
        "tests/input/yml_test_files/gatorgrade_one_gg_check_no_file_context.yml"
    )
    # when parse_config is run
    output, _ = parse_config(config)
    # then the GatorGrader arguments do not contain a file path
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].gg_args == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_parses_both_shell_and_gg_checks() -> None:
    """Test to make sure that both shell and GatorGrader checks are parsed."""
    # given a configuration file that contains a shell check and GatorGrader check
    config = Path("tests/input/yml_test_files/gatorgrader_both_checks.yml")
    # when parse_config is run
    output, _ = parse_config(config)
    # then the output should contain a shell check and GatorGrader check
    assert isinstance(output[0], GatorGraderCheck)
    assert isinstance(output[1], ShellCheck)


def test_parse_config_yml_file_runs_setup_shell_checks() -> None:
    """Test to make sure that a configuration file without setup commands can be parsed."""
    # given a configuration file without setup commands
    config = Path(
        "tests/input/yml_test_files/gatorgrade_no_shell_setup_check.yml"
    )
    # when parse_config run
    output, _ = parse_config(config)
    # then the output should contain the GatorGrader check
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].gg_args == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_shell_check_contains_command() -> None:
    """Test to make sure that the command for a shell check is stored."""
    # given a configuration file with a shell check
    config = Path(
        "tests/input/yml_test_files/gatorgrade_one_shell_command_check.yml"
    )
    # when the parse_config is run
    output, _ = parse_config(config)
    # then the command should be stored in the shell check
    assert isinstance(output[0], ShellCheck)
    assert output[0].command == "mdl ."


def test_parse_config_parses_weighted_checks() -> None:
    """Test to make sure that weighted checks are parsed correctly."""
    # given a configuration file with weighted checks
    config = Path("tests/input/yml_test_files/gatorgrade_weighted_checks.yml")
    # when parse_config is run
    output, _ = parse_config(config)
    # then the weights should be parsed correctly
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].weight == 10  # noqa: PLR2004
    assert isinstance(output[1], ShellCheck)
    assert output[1].weight == 5  # noqa: PLR2004


def test_parse_config_parses_outputlimit_checks() -> None:
    """Test to make sure that checks with outputlimit are parsed correctly."""
    # given a configuration file with outputlimit checks
    config = Path("tests/input/yml_test_files/gatorgrade_outputlimit.yml")
    # when parse_config is run
    output, _ = parse_config(config)
    # then the outputlimits should be parsed correctly
    assert isinstance(output[0], ShellCheck)
    assert output[0].outputlimit == 5  # noqa: PLR2004
    assert output[0].weight == 10  # noqa: PLR2004
    assert isinstance(output[1], GatorGraderCheck)
    assert output[1].outputlimit == 25  # noqa: PLR2004


def test_parse_config_with_baseline_weight() -> None:
    """Test that baseline_weight affects checks without explicit weight."""
    # given a configuration file with checks that have no explicit weight
    config = Path("tests/test_assignment/gatorgrade.yml")
    # when parse_config is run with a non-default baseline weight
    output, _ = parse_config(config, baseline_weight=4)
    # then all checks should have weight 4
    for check in output:
        assert check.weight == 4  # noqa: PLR2004


def test_parse_config_with_baseline_weight_and_explicit_weight() -> None:
    """Test that explicit weight overrides baseline_weight."""
    # given a configuration file where some checks have explicit weights
    config = Path("tests/input/yml_test_files/gatorgrade_outputlimit.yml")
    # when parse_config is run with a non-default baseline weight
    output, _ = parse_config(config, baseline_weight=2)
    # then the check with explicit weight 10 retains it
    assert isinstance(output[0], ShellCheck)
    assert output[0].weight == 10  # noqa: PLR2004
    # and the check without explicit weight gets the baseline weight
    assert isinstance(output[1], GatorGraderCheck)
    assert output[1].weight == 2  # noqa: PLR2004


@pytest.mark.parametrize(
    "invalid_weight",
    [
        0,
        -1,
        -5,
        -100,
    ],
)
def test_parse_config_rejects_invalid_baseline_weight(
    invalid_weight: int,
) -> None:
    """Test parse_config returns error for non-positive baseline_weight."""
    config = Path("tests/test_assignment/gatorgrade.yml")
    checks, error = parse_config(config, baseline_weight=invalid_weight)
    assert checks == []
    assert error is not None
    assert "baseline_weight" in error


@pytest.mark.propertybased
@given(st.text(min_size=1, max_size=100))
def test_parse_config_invalid_yaml_returns_error_property(
    yaml_content: str,
) -> None:
    """Property: any non-empty string written as YAML returns checks+message or error."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_content)
        temp_path = f.name
    try:
        checks, error = parse_config(Path(temp_path))
        if error is not None:
            assert checks == []
            assert isinstance(error, str)
            assert len(error) > 0
        else:
            assert len(checks) >= 0
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_reformat_yaml_data_with_empty_list() -> None:
    """Test reformat_yaml_data raises IndexError with an empty list."""
    with pytest.raises(IndexError):
        reformat_yaml_data([])
