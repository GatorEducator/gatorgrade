"""Test suite for output_functions.py."""

import datetime
import os
from typing import List
from typing import Union

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
    report = (None, None, None)
    # When run_checks is called
    output.run_checks([check], report)  # type: ignore
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
    output.run_checks(checks, report)  # type: ignore
    # the output shows the correct fraction
    # and percentage of passed checks
    out, _ = capsys.readouterr()
    assert "Passed 2/3 (67%) of checks" in out
    capsys.readouterr()


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
    output.run_checks(checks, report)  # type: ignore
    # Then the output shows the correct fraction and percentage of passed checks
    out, _ = capsys.readouterr()
    assert "Passed 3/3 (100%) of checks" in out
    capsys.readouterr()


def test_md_report_file_created_correctly(capsys):
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
    capsys.readouterr()
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
    capsys.readouterr()


def test_throw_errors_if_report_type_not_md_nor_json(capsys):
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
    report = ("file", "not_md_nor_json", "invalid_path")
    with pytest.raises(ValueError):
        output.run_checks(checks, report)
    capsys.readouterr()


def test_write_md_and_json_correctly(tmp_path):
    """Test process of writing is good for both json and md."""
    tmp_md = tmp_path / "test.md"
    tmp_json = tmp_path / "test.json"
    assert output.write_json_or_md_file(tmp_md, "md", "hello-world")
    assert output.write_json_or_md_file(tmp_json, "json", "hello-world")


def test_create_report_json_with_passing_checks(patch_datetime_now):
    """Test that create_report_json correctly formats passing checks."""
    from gatorgrade.output.check_result import CheckResult

    _ = patch_datetime_now

    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test", "description": "Test check passed"},
        path="test/path.py",
    )
    result = output.create_report_json(1, [check_result], 100)
    assert result["amount_correct"] == 1
    assert result["percentage_score"] == 100
    assert result["report_time"] == "2022-01-01 10:30:00"
    assert len(result["checks"]) == 1
    assert result["checks"][0]["status"] is True
    assert result["checks"][0]["path"] == "test/path.py"


def test_create_report_json_with_failing_checks(patch_datetime_now):
    """Test that create_report_json correctly formats failing checks with diagnostics."""
    from gatorgrade.output.check_result import CheckResult

    _ = patch_datetime_now

    check_result = CheckResult(
        passed=False,
        description="Test check failed",
        json_info={"check": "test", "description": "Test check failed"},
        diagnostic="This is a diagnostic message",
    )
    result = output.create_report_json(0, [check_result], 0)
    assert result["amount_correct"] == 0
    assert result["percentage_score"] == 0
    assert len(result["checks"]) == 1
    assert result["checks"][0]["status"] is False
    assert result["checks"][0]["diagnostic"] == "This is a diagnostic message"


def test_create_markdown_report_file_with_all_passing():
    """Test markdown report creation with all passing checks."""
    json_data = {
        "amount_correct": 2,
        "percentage_score": 100,
        "checks": [
            {"status": True, "description": "First passing check"},
            {"status": True, "description": "Second passing check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "# Gatorgrade Insights" in markdown
    assert "**Amount Correct:** 2/2 (100%)" in markdown
    assert "## Passing Checks" in markdown
    assert "- [x] First passing check" in markdown
    assert "- [x] Second passing check" in markdown
    assert "## Failing Checks" in markdown


def test_create_markdown_report_file_with_failing_checks_and_options():
    """Test markdown report creation with failing checks that have options."""
    json_data = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {
                "status": False,
                "description": "Failing check",
                "options": {
                    "command": "pytest",
                    "fragment": "TODO",
                    "tag": "test",
                    "count": "5",
                    "directory": "src",
                    "file": "test.py",
                },
                "diagnostic": "Check failed",
            }
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- [ ] Failing check" in markdown
    assert "**command** pytest" in markdown
    assert "**fragment:** TODO" in markdown
    assert "**tag:** test" in markdown
    assert "**count:** 5" in markdown
    assert "**directory:** src" in markdown
    assert "**file:** test.py" in markdown
    assert "**diagnostic:** Check failed" in markdown


def test_create_markdown_report_file_with_failing_check_no_description():
    """Test markdown report creation with failing checks without description."""
    json_data = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {"status": False, "check": "MatchFileFragment", "command": "echo test"}
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- [ ] MatchFileFragment" in markdown
    assert "**command:** echo test" in markdown


def test_create_markdown_report_file_with_passing_check_no_description():
    """Test markdown report creation with passing checks without description."""
    json_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "check": "MatchFileFragment"}],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- [x] MatchFileFragment" in markdown


def test_configure_report_with_invalid_format():
    """Test that configure_report raises ValueError for invalid format."""
    report_params = ("invalid", "md", "test.md")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test"}],
    }
    with pytest.raises(ValueError) as exc_info:
        output.configure_report(report_params, report_data)
    assert "first argument of report has to be 'env' or 'file'" in str(exc_info.value)


def test_configure_report_env_github_step_summary_md(tmp_path, monkeypatch):
    """Test configure_report with GITHUB_STEP_SUMMARY environment variable for markdown."""
    tmp_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_file))
    report_params = ("env", "md", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    assert tmp_file.exists()
    content = tmp_file.read_text()
    assert "# Gatorgrade Insights" in content


def test_configure_report_env_github_step_summary_json(tmp_path, monkeypatch):
    """Test configure_report with GITHUB_STEP_SUMMARY environment variable for json."""
    tmp_file = tmp_path / "summary.json"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_file))
    report_params = ("env", "json", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    assert tmp_file.exists()


def test_configure_report_env_github_env(tmp_path, monkeypatch):
    """Test configure_report with GITHUB_ENV environment variable."""
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    report_params = ("env", "md", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    env_content = tmp_env_file.read_text()
    assert "JSON_REPORT=" in env_content


def test_run_checks_with_no_status_bar(capsys):
    """Test run_checks with no_status_bar flag enabled."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report, no_status_bar=True)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    assert "Passed 1/1 (100%) of checks" in out


def test_run_checks_with_running_mode(capsys):
    """Test run_checks with running_mode flag enabled."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report, running_mode=True)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    assert "Passed 1/1 (100%) of checks" in out


def test_run_checks_with_shell_check_command_display(capsys):
    """Test that failed shell check displays the command to run."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description="Failing shell check", command="false"),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report)  # type: ignore
    assert result is False
    out, _ = capsys.readouterr()
    assert "Run this command:" in out
    assert "false" in out


def test_run_checks_with_gg_check_command_display(capsys):
    """Test that failed GatorGrader check with command displays the command to run."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Check with command",
                "MatchFileFragment",
                "--command",
                "echo test",
                "--fragment",
                "nonexistent",
                "--count",
                "1",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ],
            json_info={"check": "test"},
        )
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report)  # type: ignore
    assert result is False
    out, _ = capsys.readouterr()
    assert "Run this command:" in out
    assert "echo test" in out


def test_run_checks_zero_checks_no_division_error(capsys):
    """Test run_checks with zero checks doesn't cause division by zero."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = []
    report = (None, None, None)
    result = output.run_checks(checks, report)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    assert "Passed 0/0 (0%) of checks" in out


def test_run_checks_with_report_file_json(tmp_path, capsys):
    """Test run_checks generates JSON report file correctly."""
    report_file = tmp_path / "report.json"
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "test", "command": 'echo "hello"'},
        ),
    ]
    report = ("file", "json", str(report_file))
    output.run_checks(checks, report)
    capsys.readouterr()
    assert report_file.exists()
    import json

    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["amount_correct"] == 1
    assert data["percentage_score"] == 100


def test_run_gg_check_extracts_correct_file_path():
    """Test that _run_gg_check correctly extracts file path from GatorGrader arguments."""
    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Test check with file path",
            "MatchFileFragment",
            "--fragment",
            "print(",
            "--count",
            "1",
            "--directory",
            "tests/test_assignment/src",
            "--file",
            "hello-world.py",
        ],
        json_info={"check": "test"},
    )
    result = output._run_gg_check(check)
    assert result.path == "tests/test_assignment/src/hello-world.py"


def test_run_gg_check_path_extraction_with_different_order():
    """Test that _run_gg_check extracts path correctly with directory flag earlier."""
    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Check imports exist",
            "MatchFileFragment",
            "--directory",
            "gatorgrade/input",
            "--file",
            "checks.py",
            "--fragment",
            "import",
            "--count",
            "2",
        ],
        json_info={"check": "test"},
    )
    result = output._run_gg_check(check)
    assert result.path == "gatorgrade/input/checks.py"


def test_create_markdown_report_file_includes_file_option_only_when_present():
    """Test that file option appears only for checks that have it, not for others."""
    json_data = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {
                "status": False,
                "description": "Check with file",
                "options": {
                    "directory": "src",
                    "file": "main.py",
                },
            },
            {
                "status": False,
                "description": "Check without file",
                "options": {
                    "directory": "tests",
                },
            },
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    lines = markdown.split("\n")
    check_with_file_index = -1
    check_without_file_index = -1
    for idx, line in enumerate(lines):
        if "Check with file" in line:
            check_with_file_index = idx
        if "Check without file" in line:
            check_without_file_index = idx
    assert check_with_file_index != -1
    assert check_without_file_index != -1
    check_with_file_section = "\n".join(
        lines[check_with_file_index : check_with_file_index + 5]
    )
    check_without_file_section = "\n".join(
        lines[check_without_file_index : check_without_file_index + 5]
    )
    assert "**file:** main.py" in check_with_file_section
    assert "**file:**" not in check_without_file_section
