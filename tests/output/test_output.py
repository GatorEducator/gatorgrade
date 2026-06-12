"""Test suite for output_functions.py."""

import datetime
import json
import os
import re
from pathlib import Path
from typing import Any, List, Union
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.output import output
from gatorgrade.output.check_result import CheckResult

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
FAKE_TIME = datetime.datetime(2022, 1, 1, 10, 30, 0)

# cross-platform shell commands for testing failing checks
FAILING_CMD = 'python -c "exit(1)"'
FAILING_CMD_WITH_LINES = (
    "python -c \"print('line1'); print('line2'); print('line3'); exit(1)\""
)


@pytest.fixture
def patch_datetime_now(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture to patch datetime.datetime.now() to return a fixed time."""

    class mydatetime:
        @classmethod
        def now(cls) -> datetime.datetime:
            return FAKE_TIME

    monkeypatch.setattr(datetime, "datetime", mydatetime)


def test_run_checks_invalid_gg_args_prints_exception(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that run_checks prints an exception when given an invalid GatorGrader argument."""
    # given a GatorGrader check with invalid arguments
    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Have a total of 8 commits, 5 of which were created by you",
            "CountCommitts",  # typo
            "--fragment",
            "TODO",
            "--count",
            "0",
            "--exact",
        ],
        json_info="test",
    )
    report = (None, None, None)
    # when run_checks is called
    output.run_checks([check], report)  # type: ignore
    # then the output contains a declaration
    # about the use of an Invalid GatorGrader check
    out, _ = capsys.readouterr()
    print("** ", out, " **")  # noqa: T201
    print()  # noqa: T201
    assert "Invalid GatorGrader check:" in out


def test_run_checks_some_failed_prints_correct_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that run_checks, when given some checks that should fail, prints the correct summary."""
    # given three checks with one check that should fail
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
    # when run_checks is called
    output.run_checks(checks, report)  # type: ignore
    # the output shows the correct fraction
    # and percentage of passed checks
    out, _ = capsys.readouterr()
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "- Project: gatorgrade" in plain_stdout
    assert "- Checks: 2/3 (67%)" in plain_stdout
    assert "- Points: 2/3 (67%)" in plain_stdout
    capsys.readouterr()


def test_run_checks_with_gg_check_no_command_status_bar_enabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test running mode with a GatorGrader check without --command."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Check without command in status_bar",
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
    result = output.run_checks(checks, report)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "- Project: gatorgrade" in plain_stdout
    assert "- Checks: 1/1 (100%)" in plain_stdout
    assert "- Points: 1/1 (100%)" in plain_stdout


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
    file = open("insights.md", "r")
    file_contents = file.read()
    file.close()
    Path("insights.md").unlink()
    assert "# Gatorgrade Report" in file_contents
    assert "**Project Name:** gatorgrade" in file_contents
    assert "**Amount Correct:** 1/3 (33%)" in file_contents
    assert "**Points:** 1/3 (33%)" in file_contents
    assert "## Passing Checks" in file_contents


def test_print_error_with_invalid_report_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that the terminal provides a decent error message if target path of report doesn't exist."""
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
    report = ("file", "md", str(Path("invalid_path") / "insight.md"))
    with pytest.raises(ValueError):
        output.run_checks(checks, report)
    capsys.readouterr()


def test_write_md_and_json_correctly(tmp_path: Path) -> None:
    """Test process of writing is good for both json and md."""
    tmp_md = tmp_path / "test.md"
    tmp_json = tmp_path / "test.json"
    assert output.write_json_or_md_file(tmp_md, "md", "hello-world")
    assert output.write_json_or_md_file(tmp_json, "json", "hello-world")


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_with_passing_checks() -> None:
    """Test that create_report_json correctly formats passing checks."""
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test", "description": "Test check passed"},
        path="test/path.py",
    )
    result = output.create_report_json(1, [check_result], 100)
    full_percentage = 100
    assert result["amount_correct"] == 1
    assert result["percentage_score"] == full_percentage
    assert result["report_time"] == "2022-01-01 10:30:00"
    assert len(result["checks"]) == 1
    assert result["checks"][0]["status"] is True
    assert result["checks"][0]["path"] == "test/path.py"
    assert result["checks"][0]["weight"] == 1


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_with_failing_checks() -> None:
    """Test that create_report_json correctly formats failing checks with diagnostics."""
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


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_with_weight_in_checks() -> None:
    """Test that create_report_json includes the resolved weight in each check entry."""
    check_result = CheckResult(
        passed=True,
        description="Weighted check",
        json_info={"check": "test", "description": "Weighted check"},
        weight=10,
    )
    result = output.create_report_json(1, [check_result], 100)
    assert result["checks"][0]["weight"] == 10  # noqa: PLR2004


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
    assert "# Gatorgrade Report" in markdown
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
    assert "**command:** pytest" in markdown
    assert "**fragment:** TODO" in markdown
    assert "**tag:** test" in markdown
    assert "**count:** 5" in markdown
    assert "**directory:** src" in markdown
    assert "**file:** test.py" in markdown
    assert "Check failed" in markdown


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
    assert "# Gatorgrade Report" in content


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
    expected_percentage = 100
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    report_params = ("env", "md", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": expected_percentage,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    env_content = tmp_env_file.read_text()
    json_value = env_content.split("JSON_REPORT=", 1)[1].strip()
    parsed = json.loads(json_value)
    assert parsed["amount_correct"] == 1
    assert parsed["percentage_score"] == expected_percentage
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
    result = output.run_checks(checks, report, no_progress_bar=True)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "Project: gatorgrade" in plain_stdout
    assert "Checks: 1/1 (100%)" in plain_stdout
    assert "Points: 1/1 (100%)" in plain_stdout


def test_run_checks_with_running_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_checks with running_mode flag enabled."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "Project: gatorgrade" in plain_stdout
    assert "Checks: 1/1 (100%)" in plain_stdout
    assert "Points: 1/1 (100%)" in plain_stdout


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_with_passing_check_excludes_diagnostic() -> None:
    """Test that passing checks do not include diagnostic in JSON output."""
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test", "description": "Test check passed"},
        diagnostic="This should not appear",
    )
    result = output.create_report_json(1, [check_result], 100)
    assert result["checks"][0]["status"] is True
    assert "diagnostic" not in result["checks"][0]


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_with_path_none() -> None:
    """Test that None path is excluded from JSON output."""
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test"},
        path=None,
    )
    result = output.create_report_json(1, [check_result], 100)
    assert "path" not in result["checks"][0]


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_with_non_dict_json_info() -> None:
    """Test that create_report_json handles json_info that is not a dictionary."""
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info="not a dict",
        path="test/path.py",
    )
    result = output.create_report_json(1, [check_result], 100)
    # the non-dict json_info should be appended to checks_list as is without modifications
    assert result["checks"][0] == "not a dict"


def test_create_markdown_report_file_with_zero_checks() -> None:
    """Test markdown report creation with zero checks."""
    json_data: dict[str, Any] = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "# Gatorgrade Report" in markdown
    assert "0/0 (0%)" in markdown


def test_configure_report_env_json_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test configure_report with env format and json type."""
    expected_amount = 2
    expected_percentage = 100
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    report_params = ("env", "json", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": expected_amount,
        "percentage_score": expected_percentage,
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
    assert parsed["amount_correct"] == expected_amount


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
        ShellCheck(description="Failing shell check", command=FAILING_CMD),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report)  # type: ignore
    assert result is False
    out, _ = capsys.readouterr()
    assert "Run this command:" in out
    assert "exit(1)" in out


def test_run_checks_failed_check_displays_weight() -> None:
    """Test that failed check displays its weight in the failure summary."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description="Failing check", command=FAILING_CMD, weight=10
        ),
    ]
    report = (None, None, None)
    with patch("gatorgrade.output.output.rich.print") as mock_print:
        result = output.run_checks(checks, report, no_progress_bar=True)  # type: ignore
        assert result is False
        calls = [
            str(call.args[0]) if call.args else ""
            for call in mock_print.call_args_list
        ]
        assert any("Weight:" in c and "10" in c for c in calls)


def test_run_checks_with_gg_check_command_status_bar_enabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test running mode with a GatorGrader check that has --command."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Check with command in status_bar",
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
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "Project: gatorgrade" in plain_stdout
    assert "Checks: 0/0 (0%)" in plain_stdout
    assert "Points: 0/0 (0%)" in plain_stdout


def test_run_checks_with_report_file_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test run_checks generates JSON report file correctly."""
    expected_percentage = 100
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
    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["amount_correct"] == 1
    assert data["percentage_score"] == expected_percentage


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
    assert "2 tests failed" in markdown


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
    assert "Something went wrong" in markdown
    assert "**command:**" not in markdown


def test_create_markdown_report_includes_report_time() -> None:
    """Test markdown report includes report time."""
    json_data: dict[str, Any] = {
        "amount_correct": 1,
        "percentage_score": 50,
        "report_time": "2026-06-11 12:00:00",
        "checks": [
            {"status": True, "description": "Passing check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "**Report Time:** 2026-06-11 12:00:00" in markdown


def test_create_markdown_report_includes_cli_args_block() -> None:
    """Test markdown report includes CLI arguments in a code block."""
    json_data: dict[str, Any] = {
        "amount_correct": 1,
        "percentage_score": 100,
        "cli_args": {"--config": "gatorgrade.yml", "--output-limit": 5},
        "checks": [
            {"status": True, "description": "Passing check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "## Command-Line Arguments" in markdown
    assert "```json" in markdown
    assert '"--config"' in markdown


def test_create_markdown_report_includes_version_info_block() -> None:
    """Test markdown report includes version information in a code block."""
    json_data: dict[str, Any] = {
        "amount_correct": 1,
        "percentage_score": 100,
        "version_info": {
            "gatorgrade_version": "0.9.0",
            "python_info": "Python 3.14.1",
        },
        "checks": [
            {"status": True, "description": "Passing check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "## Version Information" in markdown
    assert "```json" in markdown
    assert '"gatorgrade_version"' in markdown


def test_create_markdown_report_summary_is_list() -> None:
    """Test summary items are formatted as a Markdown list."""
    json_data: dict[str, Any] = {
        "amount_correct": 3,
        "percentage_score": 100,
        "weighted_amount_correct": 5,
        "weighted_total": 5,
        "weighted_percentage_score": 100,
        "checks": [
            {"status": True, "description": "Check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- **Project Name:**" in markdown
    assert "- **Amount Correct:**" in markdown
    assert "- **Points:**" in markdown
    assert "- **Amount Correct:** 3/1 (100%)" in markdown
    assert "- **Points:** 5/5 (100%)" in markdown


def test_create_markdown_report_failing_check_shows_weight_outputlimit_path() -> (
    None
):
    """Test failing checks show weight, outputlimit, and path."""
    json_data: dict[str, Any] = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {
                "status": False,
                "description": "Failing check",
                "weight": 3,
                "outputlimit": 5,
                "path": "src/file.py",
                "diagnostic": "error",
            }
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "- **weight:** 3" in markdown
    assert "- **outputlimit:** 5" in markdown
    assert "- **path:** src/file.py" in markdown


def test_create_markdown_report_failing_check_diagnostic_uses_text_fence() -> (
    None
):
    """Test diagnostic fence opens with ````text and closes with plain ````."""
    json_data: dict[str, Any] = {
        "amount_correct": 0,
        "percentage_score": 0,
        "checks": [
            {
                "status": False,
                "description": "Fail",
                "diagnostic": "line1\n    line2",
            }
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "````text" in markdown
    text_count = markdown.count("````text")
    close_count = markdown.count("````")
    # text_count for the opening, close_count includes both opening and closing
    # opening has ````text, closing is just ````
    assert close_count > text_count
    assert "line1" in markdown


def test_create_markdown_report_no_cli_args_omits_section() -> None:
    """Test CLI arguments section is omitted when cli_args is empty."""
    json_data: dict[str, Any] = {
        "amount_correct": 1,
        "percentage_score": 100,
        "cli_args": {},
        "checks": [
            {"status": True, "description": "Passing check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "## Command-Line Arguments" not in markdown


def test_create_markdown_report_no_version_info_omits_section() -> None:
    """Test Version Information section is omitted when version_info is empty."""
    json_data: dict[str, Any] = {
        "amount_correct": 1,
        "percentage_score": 100,
        "version_info": {},
        "checks": [
            {"status": True, "description": "Passing check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "## Version Information" not in markdown


def test_configure_report_env_not_github_step_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that GITHUB_ENV is written when report_name is not GITHUB_STEP_SUMMARY."""
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


def test_configure_report_file_json_uppercase() -> None:
    """Test configure_report accepts uppercase FILE and JSON."""
    report_params = ("FILE", "JSON", str(Path("test_report.json")))
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    with patch("gatorgrade.output.output.write_json_or_md_file") as mock_write:
        output.configure_report(report_params, report_data)
    mock_write.assert_called_once()


def test_configure_report_file_md_uppercase() -> None:
    """Test configure_report accepts uppercase FILE and MD."""
    report_params = ("FILE", "MD", str(Path("test_report.md")))
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    with patch(
        "gatorgrade.output.output.create_markdown_report_file"
    ) as mock_create:
        mock_create.return_value = "# Markdown"
        with patch(
            "gatorgrade.output.output.write_json_or_md_file"
        ) as mock_write:
            output.configure_report(report_params, report_data)
    mock_create.assert_called_once()
    mock_write.assert_called_once()


def test_configure_report_env_json_uppercase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test configure_report accepts uppercase ENV and JSON."""
    tmp_file = tmp_path / "summary.json"
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_file))
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    report_params = ("ENV", "JSON", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    assert tmp_file.exists()


def test_configure_report_env_md_uppercase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test configure_report accepts uppercase ENV and MD."""
    tmp_file = tmp_path / "summary.md"
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_file))
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    report_params = ("ENV", "MD", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    assert tmp_file.exists()
    content = tmp_file.read_text()
    assert "# Gatorgrade Report" in content


def test_write_json_or_md_file_accepts_lowercase(tmp_path: Path) -> None:
    """Test write_json_or_md_file accepts lowercase type for backwards compatibility."""
    tmp_md = tmp_path / "output.md"
    tmp_json = tmp_path / "output.json"
    assert output.write_json_or_md_file(tmp_md, "md", "# Hello")
    assert output.write_json_or_md_file(tmp_json, "json", {"key": "value"})


def test_write_json_or_md_file_accepts_uppercase(tmp_path: Path) -> None:
    """Test write_json_or_md_file accepts uppercase type."""
    tmp_md = tmp_path / "output.md"
    tmp_json = tmp_path / "output.json"
    assert output.write_json_or_md_file(tmp_md, "MD", "# Hello")
    assert output.write_json_or_md_file(tmp_json, "JSON", {"key": "value"})


def test_configure_report_file_json_backwards_compatible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test run_checks with lowercase file/json for backwards compatibility."""
    expected_percentage = 100
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
    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["amount_correct"] == 1
    assert data["percentage_score"] == expected_percentage


def test_configure_report_file_md_backwards_compatible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_checks with lowercase file/md for backwards compatibility."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
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
    ]
    report = ("file", "md", str(Path("invalid_path") / "insight.md"))
    with pytest.raises(ValueError):
        output.run_checks(checks, report)
    capsys.readouterr()


def test_run_checks_with_report_file_json_uppercase(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test run_checks generates JSON report with uppercase FILE JSON."""
    expected_percentage = 100
    report_file = tmp_path / "report.json"
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "test", "command": 'echo "hello"'},
        ),
    ]
    report = ("FILE", "JSON", str(report_file))
    output.run_checks(checks, report)
    capsys.readouterr()
    assert report_file.exists()
    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["amount_correct"] == 1
    assert data["percentage_score"] == expected_percentage


def test_run_checks_env_json_uppercase(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test run_checks with uppercase ENV JSON and GITHUB_STEP_SUMMARY."""
    tmp_file = tmp_path / "summary.json"
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_file))
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "test", "command": 'echo "hello"'},
        ),
    ]
    report = ("ENV", "JSON", "GITHUB_STEP_SUMMARY")
    output.run_checks(checks, report)
    capsys.readouterr()
    assert tmp_file.exists()


def test_run_checks_env_md_uppercase(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test run_checks with uppercase ENV MD and GITHUB_STEP_SUMMARY."""
    tmp_file = tmp_path / "summary.md"
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_file))
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "test", "command": 'echo "hello"'},
        ),
    ]
    report = ("ENV", "MD", "GITHUB_STEP_SUMMARY")
    output.run_checks(checks, report)
    capsys.readouterr()
    assert tmp_file.exists()
    content = tmp_file.read_text()
    assert "# Gatorgrade Report" in content


def test_run_checks_env_json_uppercase_other_var(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test run_checks with uppercase ENV JSON and a non-GITHUB_STEP_SUMMARY variable."""
    tmp_env_file = tmp_path / "github_env"
    tmp_env_file.write_text("")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_env_file))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "test", "command": 'echo "hello"'},
        ),
    ]
    report = ("ENV", "JSON", "MY_CUSTOM_VAR")
    output.run_checks(checks, report)
    capsys.readouterr()
    env_content = tmp_env_file.read_text()
    assert "JSON_REPORT=" in env_content


def test_configure_report_backwards_compatible_lowercase_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test configure_report with lowercase env for backwards compatibility."""
    tmp_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_file))
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "github_env"))
    report_params = ("env", "md", "GITHUB_STEP_SUMMARY")
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    output.configure_report(report_params, report_data)
    assert tmp_file.exists()
    content = tmp_file.read_text()
    assert "# Gatorgrade Report" in content


def test_configure_report_backwards_compatible_lowercase_file_json(
    tmp_path: Path,
) -> None:
    """Test configure_report with lowercase file/json for backwards compatibility."""
    tmp_file = tmp_path / "report.json"
    report_params = ("file", "json", str(tmp_file))
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    with patch("gatorgrade.output.output.write_json_or_md_file") as mock_write:
        output.configure_report(report_params, report_data)
    mock_write.assert_called_once()


def test_configure_report_backwards_compatible_lowercase_file_md(
    tmp_path: Path,
) -> None:
    """Test configure_report with lowercase file/md for backwards compatibility."""
    tmp_file = tmp_path / "report.md"
    report_params = ("file", "md", str(tmp_file))
    report_data = {
        "amount_correct": 1,
        "percentage_score": 100,
        "checks": [{"status": True, "description": "Test passed"}],
    }
    with patch(
        "gatorgrade.output.output.create_markdown_report_file"
    ) as mock_create:
        mock_create.return_value = "# Markdown"
        with patch(
            "gatorgrade.output.output.write_json_or_md_file"
        ) as mock_write:
            output.configure_report(report_params, report_data)
    mock_create.assert_called_once()
    mock_write.assert_called_once()


def test_run_gg_check_without_directory_flag() -> None:
    """Test _run_gg_check returns None path when no --directory flag."""
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
    result = output.run_checks(checks, report, no_progress_bar=True)  # type: ignore
    assert result is False
    out, _ = capsys.readouterr()
    assert "Run this command:" in out
    assert "echo test" in out


def test_run_checks_gg_check_no_command_no_status_bar_detailed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Force execution of the branch where GatorGraderCheck has no --command and no_status_bar is True."""
    # to ensure the check is considered "passed" so it doesn't hit the "Invalid" path,
    # we must provide a valid set of args or mock the grader.
    # since we want to test the logic in run_checks, mocking the grader is best.

    with patch("gatorgrade.output.output._run_gg_check") as mock_run:
        mock_run.return_value = CheckResult(
            passed=True,
            description="Mock Pass",
            json_info="test",
            diagnostic="",
        )
        checks: List[Union[ShellCheck, GatorGraderCheck]] = [
            GatorGraderCheck(
                gg_args=["No command here"],
                json_info="test",
            )
        ]
        report = (None, None, None)
        output.run_checks(checks, report, no_progress_bar=True)  # type: ignore
        out, _ = capsys.readouterr()
        plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
        assert "Checks: 1/1 (100%)" in plain_stdout


def test_run_checks_gg_check_no_command_status_bar_detailed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Force execution of the branch where GatorGraderCheck has no --command and status_bar is True."""
    with patch("gatorgrade.output.output._run_gg_check") as mock_run:
        mock_run.return_value = CheckResult(
            passed=True,
            description="Mock Pass",
            json_info="test",
            diagnostic="",
        )
        checks: List[Union[ShellCheck, GatorGraderCheck]] = [
            GatorGraderCheck(
                gg_args=["No command here"],
                json_info="test",
            )
        ]
        report = (None, None, None)
        output.run_checks(checks, report)  # type: ignore
        out, _ = capsys.readouterr()
        plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
        assert "Checks: 1/1 (100%)" in plain_stdout


def test_run_checks_weighted_score_displayed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that run_checks displays weighted score in summary."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"', command='echo "hello"', weight=10
        ),
        ShellCheck(description="Failing check", command=FAILING_CMD, weight=5),
    ]
    report = (None, None, None)
    output.run_checks(checks, report)  # type: ignore
    out, _ = capsys.readouterr()
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "Project: gatorgrade" in plain_stdout
    assert "Checks: 1/2 (50%)" in plain_stdout
    assert "Points: 10/15 (67%)" in plain_stdout


def test_run_checks_all_pass_weighted_score_100(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that run_checks shows 100% weighted score when all checks pass."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description="Pass 1", command="echo 1", weight=10),
        ShellCheck(description="Pass 2", command="echo 2", weight=5),
    ]
    report = (None, None, None)
    result = output.run_checks(checks, report)  # type: ignore
    assert result is True
    out, _ = capsys.readouterr()
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "- Project: gatorgrade" in plain_stdout
    assert "- Checks: 2/2 (100%)" in plain_stdout
    assert "- Points: 15/15 (100%)" in plain_stdout


def test_run_checks_zero_checks_weighted_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that run_checks shows 0% weighted score with no checks."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = []
    report = (None, None, None)
    output.run_checks(checks, report)  # type: ignore
    out, _ = capsys.readouterr()
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "- Project: gatorgrade" in plain_stdout
    assert "- Checks: 0/0 (0%)" in plain_stdout
    assert "- Points: 0/0 (0%)" in plain_stdout


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_with_weighted_percent() -> None:
    """Test that create_report_json includes weighted percentage score."""
    check_result = CheckResult(
        passed=True,
        description="Test check passed",
        json_info={"check": "test"},
    )
    result = output.create_report_json(1, [check_result], 100, 75)
    assert result["weighted_percentage_score"] == 75  # noqa: PLR2004


def test_create_markdown_report_file_includes_weighted_score() -> None:
    """Test markdown report includes weighted score line."""
    json_data = {
        "amount_correct": 1,
        "percentage_score": 50,
        "weighted_amount_correct": 1,
        "weighted_total": 1,
        "weighted_percentage_score": 100,
        "checks": [
            {"status": True, "description": "Passing check"},
        ],
    }
    markdown = output.create_markdown_report_file(json_data)
    assert "**Points:** 1/1 (100%)" in markdown


def test_run_checks_gg_check_with_command_status_bar_detailed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Force execution of the branch where GatorGraderCheck has --command and status_bar is True."""
    with patch("gatorgrade.output.output._run_gg_check") as mock_run:
        mock_run.return_value = CheckResult(
            passed=True,
            description="Mock Pass",
            json_info="test",
            diagnostic="",
        )
        checks: List[Union[ShellCheck, GatorGraderCheck]] = [
            GatorGraderCheck(
                gg_args=["--command", "echo test"],
                json_info="test",
            )
        ]
        report = (None, None, None)
        output.run_checks(checks, report)  # type: ignore
        out, _ = capsys.readouterr()
        plain_stdout = ANSI_ESCAPE_PATTERN.sub("", out)
        assert "Checks: 1/1 (100%)" in plain_stdout


def test_truncate_diagnostic_no_limit() -> None:
    """Test _truncate_diagnostic returns full text when limit is None."""
    diagnostic = "line1\nline2\nline3"
    result = output._truncate_diagnostic(diagnostic, None)
    assert result == diagnostic


def test_truncate_diagnostic_within_limit() -> None:
    """Test _truncate_diagnostic returns full text when under limit."""
    diagnostic = "line1\nline2"
    result = output._truncate_diagnostic(diagnostic, 5)
    assert result == diagnostic


def test_truncate_diagnostic_exceeds_limit() -> None:
    """Test _truncate_diagnostic truncates when exceeding limit."""
    diagnostic = "line1\nline2\nline3\nline4\nline5"
    result = output._truncate_diagnostic(diagnostic, 3)
    assert "line1" in result
    assert "line3" in result
    assert "line4" not in result
    assert "... (output truncated from 5 to 3 line(s))" in result


def test_run_checks_global_output_limit_truncates_diagnostic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test global output_limit truncates diagnostic in terminal output."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description="Failing check",
            command=FAILING_CMD_WITH_LINES,
        ),
    ]
    report = (None, None, None)
    output.run_checks(checks, report, output_limit=1)  # type: ignore
    out, _ = capsys.readouterr()
    assert "... (output truncated from 3 to 1 line(s))" in out


def test_run_checks_check_outputlimit_overrides_global(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test per-check outputlimit overrides global output_limit."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description="Failing check",
            command=FAILING_CMD_WITH_LINES,
            outputlimit=1,
        ),
    ]
    report = (None, None, None)
    output.run_checks(checks, report, output_limit=100)  # type: ignore
    out, _ = capsys.readouterr()
    assert "... (output truncated from 3 to 1 line(s))" in out


def test_run_checks_no_output_limit_shows_full_diagnostic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that no output_limit shows full diagnostic without truncation."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(description="Failing check", command=FAILING_CMD),
    ]
    report = (None, None, None)
    output.run_checks(checks, report)  # type: ignore
    out, _ = capsys.readouterr()
    assert "... (output truncated)" not in out


def test_run_gg_check_global_output_limit_truncates_diagnostic() -> None:
    """Test _run_gg_check applies global output_limit to truncate diagnostic."""
    check = GatorGraderCheck(
        gg_args=["--description", "Failing", "MatchFileFragment"],
        json_info={"check": "test"},
    )
    with patch("gator.grader") as mock_grader:
        mock_grader.return_value = (
            "Failing check",
            False,
            "line1\nline2\nline3\nline4",
        )
        result = output._run_gg_check(check, output_limit=2)
    assert "... (output truncated from 4 to 2 line(s))" in result.diagnostic


def test_run_gg_check_check_outputlimit_overrides_global() -> None:
    """Test per-check outputlimit overrides global output_limit in _run_gg_check."""
    check = GatorGraderCheck(
        gg_args=["--description", "Failing", "MatchFileFragment"],
        json_info={"check": "test"},
        outputlimit=1,
    )
    with patch("gator.grader") as mock_grader:
        mock_grader.return_value = (
            "Failing check",
            False,
            "line1\nline2\nline3\nline4",
        )
        result = output._run_gg_check(check, output_limit=100)
    assert "... (output truncated from 4 to 1 line(s))" in result.diagnostic


def test_run_checks_mixed_checks_use_correct_output_limit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test run_checks applies correct limit to each check independently."""
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description="Check with per-check limit",
            command=FAILING_CMD_WITH_LINES,
            outputlimit=2,
        ),
        ShellCheck(
            description="Check using global limit",
            command=FAILING_CMD_WITH_LINES,
        ),
    ]
    report = (None, None, None)
    output.run_checks(checks, report, output_limit=3)  # type: ignore
    out, _ = capsys.readouterr()
    plain_out = ANSI_ESCAPE_PATTERN.sub("", out)
    assert "... (output truncated from 3 to 2 line(s))" in plain_out
    assert "... (output truncated from 3 to 3 line(s))" not in plain_out


@pytest.mark.usefixtures("patch_datetime_now")
def test_create_report_json_respects_output_limit() -> None:
    """Test that create_report_json uses truncated diagnostic."""
    check_result = CheckResult(
        passed=False,
        description="Test check failed",
        json_info={"check": "test", "description": "Test check failed"},
        diagnostic="line1\nline2\nline3\nline4",
    )
    result = output.create_report_json(0, [check_result], 0, 0)
    assert result["checks"][0]["diagnostic"] == "line1\nline2\nline3\nline4"


def test_create_report_json_includes_outputlimit_for_every_check() -> None:
    """Test that outputlimit is present for every check in JSON report."""
    check_result_1 = CheckResult(
        passed=True,
        description="Check one",
        json_info={"check": "test1"},
        outputlimit=5,
    )
    check_result_2 = CheckResult(
        passed=False,
        description="Check two",
        json_info={"check": "test2"},
        outputlimit=10,
    )
    result = output.create_report_json(1, [check_result_1, check_result_2], 50)
    assert result["checks"][0]["outputlimit"] == 5  # noqa: PLR2004
    assert result["checks"][1]["outputlimit"] == 10  # noqa: PLR2004


def test_create_report_json_includes_explicit_outputlimit() -> None:
    """Test that explicit per-check outputlimit is saved in JSON report."""
    expected_limit = 15
    check_result = CheckResult(
        passed=True,
        description="Explicit limit check",
        json_info={"check": "test"},
        outputlimit=expected_limit,
    )
    result = output.create_report_json(1, [check_result], 100)
    assert result["checks"][0]["outputlimit"] == expected_limit


def test_create_report_json_includes_global_outputlimit() -> None:
    """Test that global default outputlimit is saved when no explicit limit."""
    check_result = CheckResult(
        passed=True,
        description="No explicit limit",
        json_info={"check": "test"},
        outputlimit=5,
    )
    result = output.create_report_json(1, [check_result], 100)
    assert result["checks"][0]["outputlimit"] == 5  # noqa: PLR2004


def test_run_checks_includes_outputlimit_in_json_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that run_checks saves outputlimit in JSON report for every check."""
    report_file = tmp_path / "report.json"
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "test", "command": 'echo "hello"'},
            weight=1,
        ),
    ]
    global_limit = 3
    report = ("file", "json", str(report_file))
    output.run_checks(checks, report, output_limit=global_limit)
    capsys.readouterr()
    assert report_file.exists()
    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["checks"][0]["outputlimit"] == global_limit


def test_run_checks_includes_per_check_outputlimit_in_json_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that per-check outputlimit overrides global and is saved in JSON report."""
    report_file = tmp_path / "report.json"
    per_check_limit = 7
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        ShellCheck(
            description='Echo "Hello!"',
            command='echo "hello"',
            json_info={"description": "test", "command": 'echo "hello"'},
            outputlimit=per_check_limit,
            weight=1,
        ),
    ]
    report = ("file", "json", str(report_file))
    output.run_checks(checks, report, output_limit=3)
    capsys.readouterr()
    assert report_file.exists()
    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["checks"][0]["outputlimit"] == per_check_limit


def test_run_checks_includes_outputlimit_for_gg_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that GatorGraderCheck outputlimit is saved in JSON report."""
    report_file = tmp_path / "report.json"
    per_check_limit = 4
    checks: List[Union[ShellCheck, GatorGraderCheck]] = [
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Test check",
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
            json_info={"check": "test"},
            outputlimit=per_check_limit,
        ),
    ]
    report = ("file", "json", str(report_file))
    output.run_checks(checks, report)
    capsys.readouterr()
    assert report_file.exists()
    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["checks"][0]["outputlimit"] == per_check_limit


@pytest.mark.propertybased
@given(
    st.text(
        max_size=200,
        alphabet=st.characters(
            whitelist_categories=["L", "N", "P", "Z"],
            whitelist_characters="\n\t",
        ),
    ),
    st.integers(min_value=1, max_value=50),
)
def test_truncate_diagnostic_respects_limit_property(
    diagnostic: str, limit: int
) -> None:
    """Property: truncated output never exceeds the specified line limit."""
    truncated = output._truncate_diagnostic(diagnostic, limit)
    result_lines = truncated.splitlines()
    content_lines = [
        line
        for line in result_lines
        if not line.startswith("   ... (output truncated")
    ]
    assert len(content_lines) <= limit


@pytest.mark.propertybased
@given(
    st.lists(
        st.text(
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=["L", "N", "P", "Z"],
                whitelist_characters="\t ",
            ),
        ),
        min_size=0,
        max_size=5,
    ).map("\n".join),
    st.integers(min_value=6, max_value=50),
)
def test_truncate_diagnostic_within_limit_preserves_input_property(
    diagnostic: str, limit: int
) -> None:
    """Property: when input has fewer lines than the limit, output equals input."""
    truncated = output._truncate_diagnostic(diagnostic, limit)
    assert truncated == diagnostic


@pytest.mark.propertybased
@given(st.text(max_size=200))
def test_truncate_diagnostic_no_limit_property(diagnostic: str) -> None:
    """Property: when limit is None, output always equals input."""
    assert output._truncate_diagnostic(diagnostic, None) == diagnostic


def test_elide_report_path_short_path_unchanged() -> None:
    """Test _elide_report_path keeps short paths as-is."""
    path = "report.json"
    result = output._elide_report_path(path)
    assert result == path


def test_elide_report_path_elides_long_path() -> None:
    """Test _elide_report_path shows start and filename with ellipsis."""
    S = os.sep
    path = S + S.join(
        [
            "this",
            "is",
            "a",
            "very",
            "long",
            "path",
            "name",
            "extra",
            "to",
            "some",
            "report.json",
        ]
    )
    expected = S + S.join(["this", "is", "...", "report.json"])
    result = output._elide_report_path(path)
    assert result == expected


def test_elide_report_path_absolute_no_double_slash() -> None:
    """Test _elide_report_path does not double the root slash."""
    S = os.sep
    path = S + S.join(
        [
            "home",
            "gkapfham",
            "projects",
            "gatorgrade",
            "reports",
            "report.json",
        ]
    )
    result = output._elide_report_path(path)
    assert os.sep + os.sep not in result
    expected_prefix = S + S.join(["home", "gkapfham"])
    assert result.startswith(expected_prefix)


def test_elide_report_path_keeps_two_part_path() -> None:
    """Test _elide_report_path keeps paths with only two parts."""
    path = os.sep.join(["reports", "report.json"])
    result = output._elide_report_path(path)
    assert result == path


def test_elide_report_path_short_boundary_not_elided() -> None:
    """Test _elide_report_path does not elide path at exactly 50 chars."""
    path = "a" * 50
    result = output._elide_report_path(path)
    assert result == path


def test_elide_report_path_long_single_file_unchanged() -> None:
    """Test _elide_report_path returns single file path as-is."""
    path = "a" * 60 + ".json"
    result = output._elide_report_path(path)
    assert result == path


@pytest.mark.propertybased
@given(
    st.lists(
        st.builds(
            CheckResult,
            passed=st.booleans(),
            description=st.text(max_size=50),
            json_info=st.just({"check": "test"}),
            weight=st.integers(min_value=1, max_value=10),
            outputlimit=st.one_of(
                st.none(), st.integers(min_value=1, max_value=20)
            ),
        ),
        min_size=0,
        max_size=30,
    )
)
def test_create_report_json_checks_count_matches_property(
    checks: List[CheckResult],
) -> None:
    """Property: JSON report check count matches input and amount_correct is correct."""
    passed_count = sum(1 for c in checks if c.passed)
    total = len(checks)
    percent = round(passed_count / total * 100) if total > 0 else 0
    result = output.create_report_json(passed_count, checks, percent)
    assert len(result["checks"]) == total
    assert result["amount_correct"] == passed_count


@pytest.mark.propertybased
@given(
    st.lists(
        st.builds(
            CheckResult,
            passed=st.booleans(),
            description=st.text(max_size=50),
            json_info=st.just({"check": "test"}),
            weight=st.integers(min_value=1, max_value=10),
            outputlimit=st.one_of(
                st.none(), st.integers(min_value=1, max_value=20)
            ),
        ),
        min_size=1,
        max_size=30,
    )
)
def test_create_report_json_every_check_has_expected_keys_property(
    checks: List[CheckResult],
) -> None:
    """Property: every check entry in JSON report has status, weight, and outputlimit."""
    passed_count = sum(1 for c in checks if c.passed)
    total = len(checks)
    percent = round(passed_count / total * 100) if total > 0 else 0
    result = output.create_report_json(passed_count, checks, percent)
    for entry in result["checks"]:
        assert "status" in entry
        assert "weight" in entry
        assert "outputlimit" in entry
        assert isinstance(entry["status"], bool)
        assert isinstance(entry["weight"], int)
        assert entry["outputlimit"] is None or isinstance(
            entry["outputlimit"], int
        )


@pytest.mark.propertybased
@given(
    st.lists(
        st.builds(
            CheckResult,
            passed=st.booleans(),
            description=st.text(max_size=50),
            json_info=st.just({"check": "test"}),
            weight=st.integers(min_value=1, max_value=10),
            outputlimit=st.one_of(
                st.none(), st.integers(min_value=1, max_value=20)
            ),
        ),
        min_size=0,
        max_size=30,
    )
)
def test_create_report_json_expected_keys_present_property(
    checks: List[CheckResult],
) -> None:
    """Property: the top-level JSON report dict always has all expected keys."""
    passed_count = sum(1 for c in checks if c.passed)
    total = len(checks)
    percent = round(passed_count / total * 100) if total > 0 else 0
    result = output.create_report_json(passed_count, checks, percent)
    expected_keys = {
        "amount_correct",
        "percentage_score",
        "weighted_amount_correct",
        "weighted_total",
        "weighted_percentage_score",
        "cli_args",
        "version_info",
        "report_time",
        "checks",
    }
    assert expected_keys.issubset(result.keys())
