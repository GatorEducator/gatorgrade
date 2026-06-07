"""Test suite for parse_config function."""

from pathlib import Path

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.input.parse_config import parse_config


def test_parse_config_gg_check_in_file_context_contains_file() -> None:
    """Test to make sure that the file context is included in the GatorGrader arguments."""
    # given a configuration file with a GatorGrader check within a file context
    config = Path(
        "tests/input/yml_test_files/gatorgrade_one_gg_check_in_file.yml"
    )
    # when parse_config is run
    output = parse_config(config)
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
    output = parse_config(config)
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
    output = parse_config(config)
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
    output = parse_config(config)
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
    output = parse_config(config)
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
    output = parse_config(config)
    # then the command should be stored in the shell check
    assert isinstance(output[0], ShellCheck)
    assert output[0].command == "mdl ."


def test_parse_config_parses_weighted_checks() -> None:
    """Test to make sure that weighted checks are parsed correctly."""
    # given a configuration file with weighted checks
    config = Path("tests/input/yml_test_files/gatorgrade_weighted_checks.yml")
    # when parse_config is run
    output = parse_config(config)
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
    output = parse_config(config)
    # then the outputlimits should be parsed correctly
    assert isinstance(output[0], ShellCheck)
    assert output[0].outputlimit == 5  # noqa: PLR2004
    assert output[0].weight == 10  # noqa: PLR2004
    assert isinstance(output[1], GatorGraderCheck)
    assert output[1].outputlimit == 25  # noqa: PLR2004
