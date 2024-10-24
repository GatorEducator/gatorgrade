"""Test suite for output_functions.py."""

import datetime
import os

import pytest

from gatorgrade.input.checks import GatorGraderCheck
from gatorgrade.input.checks import ShellCheck
from gatorgrade.output import output

FAKE_TIME = datetime.datetime(2022, 1, 1, 10, 30, 0)


@pytest.fixture
def patch_datetime_now(monkeypatch):
    class mydatetime:
        @classmethod
        def now(cls):
            return FAKE_TIME

    monkeypatch.setattr(datetime, "datetime", mydatetime)


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
    # report = (None, None, None)
    report_location = None
    report_storing_type = None
    storing_location_name = None
    # When run_checks is called
    output.run_checks(
        [check], report_location, report_storing_type, storing_location_name
    )  # type: ignore
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
    # report = (None, None, None)
    report_location = None
    report_storing_type = None
    storing_location_name = None
    # When run_checks is called
    output.run_checks(
        checks, report_location, report_storing_type, storing_location_name
    )  # type: ignore
    # the output shows the correct fraction
    # and percentage of passed checks
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
    # report = (None, None, None)
    report_location = None
    report_storing_type = None
    storing_location_name = None
    # When run_checks is called
    output.run_checks(
        checks, report_location, report_storing_type, storing_location_name
    )  # type: ignore
    # Then the output shows the correct fraction and percentage of passed checks
    out, _ = capsys.readouterr()
    assert "Passed 3/3 (100%) of checks" in out


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
    # report = ("file", "md", "insights.md")
    report_location = "file"
    report_storing_type = "md"
    storing_location_name = "insights.md"
    output.run_checks(
        checks, report_location, report_storing_type, storing_location_name
    )
    # check to make sure the created file matches the expected output
    expected_file_contents = """# Gatorgrade Insights\n\n**Project Name:** gatorgrade\n**Amount Correct:** 1/3 (33%)\n\n## Passing Checks"""

    file = open("insights.md", "r")
    file_contents = file.read()
    file.close()

    os.remove("insights.md")

    # print("expected")
    # print(expected_file_contents)
    # print("\n")
    # print("file_contents")
    # print(file_contents)

    assert expected_file_contents in file_contents


def test_print_error_with_invalid_report_path():
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
    # report = ("file", "md", "invalid_path/insight.md")
    report_location = "file"
    report_storing_type = "md"
    storing_location_name = "invalid_path/insight.md"
    with pytest.raises(ValueError):
        output.run_checks(
            checks, report_location, report_storing_type, storing_location_name
        )
    # assert value == False


def test_throw_errors_if_report_type_not_md_nor_json():
    """Test the value error should be thrown if no md nor json is inputted."""
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
    # report = ("file", "not_md_nor_json", "invalid_path")
    report_location = "file"
    report_storing_type = "not_md_nor_json"
    storing_location_name = "invalid_path"

    with pytest.raises(ValueError):
        output.run_checks(
        checks, report_location, report_storing_type, storing_location_name
    )
    # assert value == False


def test_write_md_and_json_correctly(tmp_path):
    """Test process of writing is good for both json and md."""
    tmp_md = tmp_path / "test.md"
    tmp_json = tmp_path / "test.json"
    assert output.write_json_or_md_file(tmp_md, "md", "hello-world")
    assert output.write_json_or_md_file(tmp_json, "json", "hello-world")
