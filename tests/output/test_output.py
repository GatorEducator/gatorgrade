"""Test suite for output_functions.py."""

import datetime
import json
import os
from pathlib import Path
from typing import Any, List, Union

import pytest

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.output import output
from gatorgrade.output.check_result import CheckResult

FAKE_TIME = datetime.datetime(2022, 1, 1, 10, 30, 0)


@pytest.fixture
def patch_datetime_now(monkeypatch: pytest.MonkeyPatch) -> None:
    class mydatetime:
        @classmethod
        def now(cls) -> datetime.datetime:
            return FAKE_TIME

    monkeypatch.setattr(datetime, "datetime", mydatetime)


def test_run_checks_invalid_gg_args_prints_exception(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_run_checks_some_failed_prints_correct_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_run_checks_all_passed_prints_correct_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_md_report_file_created_correctly(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_print_error_with_invalid_report_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the terminal should provide a decent error message if target path of report doesn't exist"""
    checks = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={
                "description": "Echo 'Hello!'",
                "command": 'echo "hello"',
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


def test_throw_errors_if_report_type_not_md_nor_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the value error should be thrown if no md nor json is inputted."""
    checks = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={
                "description": "Echo 'Hello!'",
                "command": 'echo "hello"',
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


def test_write_md_and_json_correctly(tmp_path: Path) -> None:
    """Test process of writing is good for both json and md."""
    tmp_md = tmp_path / "test.md"
    tmp_json = tmp_path / "test.json"
    assert output.write_json_or_md_file(tmp_md, "md", "hello-world")
    assert output.write_json_or_md_file(tmp_json, "json", "hello-world")


def test_create_report_json_with_passing_checks(
    patch_datetime_now: None,
) -> None:
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


def test_create_report_json_with_failing_checks(
    patch_datetime_now: None,
) -> None:
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


def test_create_markdown_report_file_with_all_passing() -> None:
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


def test_create_markdown_report_file_with_failing_checks_and_options() -> None:
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


def test_create_markdown_report_file_with_failing_check_no_description() -> (
    None
):
    """Test markdown report creation with failing checks without description."""
    json_data = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {
                "status": False,
                "check": "MatchFileFragment",
                "command": "echo test",
            }
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- [ ] MatchFileFragment" in markdown
    assert "**command:** echo test" in markdown


def test_create_markdown_report_file_with_passing_check_no_description() -> (
    None
):
    """Test markdown report creation with passing checks without description."""
    json_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "check": "MatchFileFragment"}],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- [x] MatchFileFragment" in markdown


def test_configure_report_with_invalid_format() -> None:
    """Test that configure_report raises ValueError for invalid format."""
    report_params = ("invalid", "md", "test.md")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test"}],
    }
    with pytest.raises(ValueError) as exc_info:
        output.configure_report(report_params, report_data)
    assert "first argument of report has to be 'env' or 'file'" in str(
        exc_info.value
    )


def test_configure_report_env_github_step_summary_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_configure_report_env_github_step_summary_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_configure_report_env_github_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_configure_report_env_github_env_writes_valid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that GITHUB_ENV receives valid JSON after the JSON_REPORT key."""
    import json

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
    json_value = env_content.split("JSON_REPORT=", 1)[1].strip()
    parsed = json.loads(json_value)
    assert parsed["amount_correct"] == 1
    assert parsed["percentage_score"] == 100
    assert len(parsed["checks"]) == 1
    assert parsed["checks"][0]["status"] is True


def test_configure_report_env_github_env_appends_not_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that GITHUB_ENV file content is preserved when appending."""
    tmp_env_file = tmp_path / "github_env"
    existing_content = "EXISTING_VAR=existing_value\n"
    tmp_env_file.write_text(existing_content)
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
    assert env_content.startswith(existing_content)
    assert "JSON_REPORT=" in env_content


def test_configure_report_env_missing_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that configure_report does not crash when env vars are missing."""
    monkeypatch.delenv("GITHUB_ENV", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    report_params = ("env", "md", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)


def test_run_checks_with_no_status_bar(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_checks with no_status_bar flag enabled."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report, no_status_bar=True)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    assert "Passed 1/1 (100%) of checks" in out


def test_run_checks_with_running_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_checks with running_mode flag enabled."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report, running_mode=True)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    assert "Passed 1/1 (100%) of checks" in out


def test_create_report_json_with_passing_check_excludes_diagnostic(
    patch_datetime_now: None,
) -> None:
    """Test that passing checks do not include diagnostic in JSON output."""
    _ = patch_datetime_now
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test", "description": "Test check passed"},
        diagnostic="This should not appear",
    )
    result = output.create_report_json(1, [check_result], 100)
    assert result["checks"][0]["status"] is True
    assert "diagnostic" not in result["checks"][0]


def test_create_report_json_with_path_none(patch_datetime_now: None) -> None:
    """Test that None path is excluded from JSON output."""
    _ = patch_datetime_now
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test"},
        path=None,
    )
    result = output.create_report_json(1, [check_result], 100)
    assert "path" not in result["checks"][0]


def test_create_report_json_with_empty_path(patch_datetime_now: None) -> None:
    """Test that empty string path is excluded from JSON output."""
    _ = patch_datetime_now
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test"},
        path="",
    )
    result = output.create_report_json(1, [check_result], 100)
    assert "path" not in result["checks"][0]


def test_create_markdown_report_file_with_zero_checks() -> None:
    """Test markdown report creation with zero checks."""
    json_data: dict[str, Any] = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "# Gatorgrade Insights" in markdown
    assert "0/0 (0%)" in markdown


def test_configure_report_env_json_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test configure_report with env format and json type."""
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    report_params = ("env", "json", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 2,
        "percentage_score": 100,
        "checks": [
            {"status": True, "description": "Check 1"},
            {"status": True, "description": "Check 2"},
        ],
    }
    output.configure_report(report_params, report_data)
    env_content = tmp_env_file.read_text()
    assert "JSON_REPORT=" in env_content
    json_value = env_content.split("JSON_REPORT=", 1)[1].strip()
    parsed = json.loads(json_value)
    assert parsed["amount_correct"] == 2


def test_write_json_or_md_file_creates_md_file(tmp_path: Path) -> None:
    """Test that write_json_or_md_file creates a markdown file."""
    tmp_md = tmp_path / "output.md"
    content = "# Test Report\n\nSome content here."
    result = output.write_json_or_md_file(tmp_md, "md", content)
    assert result is True
    assert tmp_md.exists()
    assert content in tmp_md.read_text()


def test_run_checks_with_shell_check_command_display(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_run_checks_with_gg_check_command_display(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_run_checks_zero_checks_no_division_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_checks with zero checks doesn't cause division by zero."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = []
    report = (None, None, None)
    result = output.run_checks(checks, report)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    assert "Passed 0/0 (0%) of checks" in out


def test_run_checks_with_report_file_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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


def test_run_gg_check_extracts_correct_file_path() -> None:
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


def test_run_gg_check_path_extraction_with_different_order() -> None:
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


def test_create_markdown_report_file_includes_file_option_only_when_present() -> (
    None
):
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


def test_create_markdown_report_file_with_command_and_diagnostic() -> None:
    """Test markdown report with failing check that has command and diagnostic."""
    json_data = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {
                "status": False,
                "description": "Run tests",
                "command": "pytest",
                "diagnostic": "2 tests failed",
            }
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- [ ] Run tests" in markdown
    assert "**command:** pytest" in markdown
    assert "**diagnostic:** 2 tests failed" in markdown


def test_create_markdown_report_file_failing_check_no_options_no_command() -> (
    None
):
    """Test markdown report with failing check that has neither options nor command."""
    json_data = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {
                "status": False,
                "description": "Some check",
                "diagnostic": "Something went wrong",
            }
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- [ ] Some check" in markdown
    assert "**diagnostic:** Something went wrong" in markdown
    assert "**command:**" not in markdown


def test_configure_report_env_not_github_step_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that GITHUB_ENV is written when report_name is not GITHUB_STEP_SUMMARY."""
    import json

    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    report_params = ("env", "json", "OTHER_VAR")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    env_content = tmp_env_file.read_text()
    assert "JSON_REPORT=" in env_content
    json_value = env_content.split("JSON_REPORT=", 1)[1].strip()
    parsed = json.loads(json_value)
    assert parsed["amount_correct"] == 1


def test_run_gg_check_without_directory_flag() -> None:
    """Test _run_gg_check returns None path when no --directory flag."""
    from unittest.mock import patch

    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Check without directory",
            "MatchFileFragment",
            "--fragment",
            "TODO",
            "--count",
            "0",
            "--exact",
        ],
        json_info={"check": "test"},
    )
    with patch("gator.grader") as mock_grader:
        mock_grader.return_value = ("Check without directory", True, "")
        result = output._run_gg_check(check)
    assert result.path is None


def test_run_checks_no_status_bar_with_gg_check_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test no_status_bar path with GatorGrader check that has --command."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Check with command in no_status_bar",
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
    result = output.run_checks(checks, report, no_status_bar=True)  # type: ignore
    assert result is False
    out, _ = capsys.readouterr()
    assert "Run this command:" in out
    assert "echo test" in out


def test_run_checks_no_status_bar_gg_check_without_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test no_status_bar path with GatorGrader check without --command."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
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
        )
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report, no_status_bar=True)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    assert "Passed 1/1 (100%) of checks" in out
