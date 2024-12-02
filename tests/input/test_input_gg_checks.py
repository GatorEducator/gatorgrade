"""Test suite for parse_config function."""

from pathlib import Path

from gatorgrade.input.checks import GatorGraderCheck
from gatorgrade.input.checks import ShellCheck
from gatorgrade.input.parse_config import parse_config


def test_parse_config_gg_check_in_file_context_contains_file():
    """Test to make sure that the file context is included in the GatorGrader arguments."""
    # Given a configuration file with a GatorGrader check within a file context
    config = Path("tests/input/yml_test_files/gatorgrade_one_gg_check_in_file.yml")
    # When parse_config is run
    output, deadline = parse_config(config)
    # Then the file path should be in the GatorGrader arguments
    assert "file.py" in output[0].gg_args


def test_parse_config_check_gg_matchfilefragment():
    """Test to make sure the description, check name, and options appear in the GatorGrader arguments."""
    # Given a configuration file with a GatorGrader check
    config = Path("tests/input/yml_test_files/gatorgrade_matchfilefragment.yml")
    # When parse_config is run
    output, deadline = parse_config(config)
    # Then the description, check name, and options appear in the GatorGrader arguments
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


def test_parse_config_gg_check_no_file_context_contains_no_file():
    """Test to make sure checks without a file context do not have a file path in GatorGrader arguments."""
    # Given a configuration file with a GatorGrader check without a file context
    config, deadline = Path(
        "tests/input/yml_test_files/gatorgrade_one_gg_check_no_file_context.yml"
    )
    # When parse_config is run
    output, deadline = parse_config(config)
    # Then the GatorGrader arguments do not contain a file path
    assert output[0].gg_args == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_parses_both_shell_and_gg_checks():
    """Test to make sure that both shell and GatorGrader checks are parsed."""
    # Given a configuration file that contains a shell check and GatorGrader check
    config = Path("tests/input/yml_test_files/gatorgrader_both_checks.yml")
    # When parse_config is run
    output, deadline = parse_config(config)
    # Then the output should contain a shell check and GatorGrader check
    assert isinstance(output[0], GatorGraderCheck)
    assert isinstance(output[1], ShellCheck)


def test_parse_config_yml_file_runs_setup_shell_checks():
    """Test to make sure that a configuration file without setup commands can be parsed."""
    # Given a configuration file without setup commands
    config = Path("tests/input/yml_test_files/gatorgrade_no_shell_setup_check.yml")
    # When parse_config run
    output, deadline = parse_config(config)
    # Then the output should contain the GatorGrader check
    assert output[0].gg_args == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_shell_check_contains_command():
    """Test to make sure that the command for a shell check is stored."""
    # Given a configuration file with a shell check
    config = Path("tests/input/yml_test_files/gatorgrade_one_shell_command_check.yml")
    # When the parse_config is run
    output, deadline = parse_config(config)
    # Then the command should be stored in the shell check
    assert output[0].command == "mdl ."
