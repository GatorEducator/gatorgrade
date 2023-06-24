"""Test suite for output_functions.py."""

import json
import os
import subprocess

import pytest

from gatorgrade.input.checks import GatorGraderCheck
from gatorgrade.input.checks import ShellCheck
from gatorgrade.output import output


def test_run_checks_gg_check_should_show_passed(capsys):
    """Test that run_checks runs a GatorGrader check and prints that the check has passed."""
    # Given a GatorGrader check that should pass
    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Check TODOs",
            "MatchFileFragment",
            "--fragment",
            "TODO",
            "--count",
            "0",
            "--exact",
            "--directory",
            "tests/test_assignment/src",
            "--file",
            "hello-world.py",
        ],
        json_info="test",
    )
    report = (None, None, None)
    # When run_checks is called
    output.run_checks([check], report)
    # Then the output shows that the check has passed
    out, _ = capsys.readouterr()
    assert "✓  Check TODOs" in out


def test_run_checks_invalid_gg_args_prints_exception(capsys):
    """Test that run_checks prints an exception when given an invalid GatorGrader argument."""
    # Given a GatorGrader check with invalid arguments
    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Have a total of 8 commits, 5 of which were created by you",
            "CountCommitts",  # Typo
            "--fragment",
            "TODO",
            "--count",
            "0",
            "--exact",
        ],
        json_info="test",
    )
    report = (None, None, None)
    # When run_checks is called
    output.run_checks([check], report)
    # Then the output contains a declaration
    # about the use of an Invalid GatorGrader check
    out, _ = capsys.readouterr()
    print("** ", out, " **")
    print()
    assert "Invalid GatorGrader check:" in out


def test_run_checks_some_failed_prints_correct_summary(capsys):
    """Test that run_checks, when given some checks that should fail, prints the correct summary."""
    # Given three checks with one check that should fail
    checks = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Complete all TODOs in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "0",
                "--exact",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info="test",
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Add a print statement to hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "print(",
                "--count",
                "2",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info="test",
        ),
    ]
    report = (None, None, None)
    # When run_checks is called
    output.run_checks(checks, report)
    # Then the output shows the correct fraction and percentage of passed checks
    out, _ = capsys.readouterr()
    assert "Passed 2/3 (67%) of checks" in out


def test_run_checks_all_passed_prints_correct_summary(capsys):
    """Test that run_checks, when given checks that should all pass, prints the correct summary."""
    # Given three checks that should all pass
    checks = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Complete all TODOs in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "0",
                "--exact",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info="test",
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Call the 'greet' function in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "greet(",
                "--count",
                "2",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info="test",
        ),
    ]
    report = (None, None, None)
    # When run_checks is called
    output.run_checks(checks, report)
    # Then the output shows the correct fraction and percentage of passed checks
    out, _ = capsys.readouterr()
    assert "Passed 3/3 (100%) of checks" in out


def test_json_report_file_created_correctly():
    """Test that with the cli input '--report file json insights.json' the file is created correctly."""
    # given the following checks
    checks = [
        ShellCheck(
            description="Echo 'Hello!'",
            command="echo 'hello'",
            json_info={
                "description": "Echo'Hello!'",
                "options": {
                    "command ": "echo 'hello'",
                },
            },
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Complete all TODOs in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "1",
                "--exact",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info={
                "description ": "Complete all TODOs in hello - world.py ",
                "options": {
                    "Fragment ": "TODO ",
                    "Count ": "1",
                    "Directory": "tests/test_assignment/src",
                    "File": "hello-world.py",
                },
            },
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                'Call the "greet" function in hello-world.py',
                "MatchFileFragment",
                "--fragment",
                "greet(",
                "--count",
                "2",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info={
                "description": 'Invalid GatorGrader check: "--description Call the "greet" function in hello - world.py MatchFileFragment--fragment greet(--count 2 E--directory tests / test_assignment / src--file hello - world.py\ ',
                "options": {
                    "Fragment": "greet(",
                    "Count": "2",
                    "Directory": "tests/test_assignment/src",
                    "File": "hello-world.py",
                },
            },
        ),
    ]
    # run them with the wanted report config
    report = ("file", "json", "insights.json")
    output.run_checks(checks, report)
    # check to make sure the created file matches the expected output
    expected_file_contents_dict = {
        "amount_correct": 1,
        "percentage_score": 33,
        "checks": [
            {
                "description": "Echo'Hello!'",
                "options": {
                    "command ": "echo 'hello'",
                },
                "status": True,
            },
            {
                "description ": "Complete all TODOs in hello - world.py ",
                "options": {
                    "Fragment ": "TODO ",
                    "Count ": "1",
                    "Directory": "tests/test_assignment/src",
                    "File": "hello-world.py",
                },
                "status": False,
                "diagnostic": "Found 0 fragment(s) in the hello-world.py or the output while expecting exactly 1",
            },
            {
                "description": 'Invalid GatorGrader check: "--description Call the "greet" function in hello - world.py MatchFileFragment--fragment greet(--count 2 E--directory tests / test_assignment / src--file hello - world.py\ ',
                "options": {
                    "Fragment": "greet(",
                    "Count": "2",
                    "Directory": "tests/test_assignment/src",
                    "File": "hello-world.py",
                },
                "status": False,
                "diagnostic": "\"<class 'gator.exceptions.InvalidSystemArgumentsError'>\" thrown by GatorGrader",
            },
        ],
    }
    expected_file_contents = expected_file_contents_dict
    file = open("insights.json", "r")
    file_contents = json.load(file)
    file.close()
    os.remove("insights.json")

    assert file_contents == expected_file_contents


def test_md_report_file_created_correctly():
    """Test that with the cli input '--report file md insights.md' the file is created correctly."""
    # given the following checks
    checks = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={
                "description": "test",
                "options": {
                    "file": "test.txt",
                    "directory": "tests/test_assignment/src",
                },
            },
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Complete all TODOs in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "1",
                "--exact",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info={
                "description": "Complete all TODOs in hello-world.py",
                "options": {
                    "file": "test.txt",
                    "directory": "tests/test_assignment/src",
                },
            },
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                'Call the "greet" function in hello-world.py',
                "MatchFileFragment",
                "--fragment",
                "greet(",
                "--count",
                "2",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info={
                "description": 'Call the "greet" function in hello-world.py',
                "options": {
                    "file": "test.txt",
                    "directory": "tests/test_assignment/src",
                },
            },
        ),
    ]
    # run them with the wanted report config
    report = ("file", "md", "insights.md")
    output.run_checks(checks, report)
    # check to make sure the created file matches the expected output
    expected_file_contents = """# Gatorgrade Insights\n\n**Project Name:** gatorgrade\n**Amount Correct:** 1/3 (33%)\n\n## Passing Checks"""

    file = open("insights.md", "r")
    file_contents = file.read()
    file.close()

    os.remove("insights.md")

    assert expected_file_contents in file_contents


def test_print_error_with_invalid_report_path(capsys):
    """Test the terminal should provide a decent error message if target path of report doesn't exist"""
    checks = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "Echo 'Hello!'", "command": 'echo "hello"'},
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Complete all TODOs in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "1",
                "--exact",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info={
                "description": "test",
                "status": True,
                "options": {
                    "file": "test.txt",
                    "directory": "tests/test_assignment/src",
                },
            },
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                'Call the "greet" function in hello-world.py',
                "MatchFileFragment",
                "--fragment",
                "greet(",
                "--count",
                "2",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info={
                "description": "test",
                "status": True,
                "options": {
                    "file": "test.txt",
                    "directory": "tests/test_assignment/src",
                },
            },
        ),
    ]
    report = ("file", "md", "invalid_path/insight.md")
    with pytest.raises(ValueError):
        output.run_checks(checks, report)
