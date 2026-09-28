"""Tests for the insights and analyze commands in the GatorGrade CLI."""

import datetime
import json
import re
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from typing import Any, Literal

import pytest
import typer
from click import BadParameter
from rich.console import Console
from typer.testing import CliRunner

from gatorgrade import main
from gatorgrade.insights import InsightsReport
from gatorgrade.main import (
    InsightsFormat,
    _build_history_insights,
    _insights_destination,
    _load_insights_report,
    _resolve_insights_config,
    _write_insights_file,
    app,
)
from gatorgrade.report_history import (
    HISTORY_REPORT_KEY,
    get_history_scope,
    save_report_history,
)
from gatorgrade.validate import (
    validate_insights_input,
    validate_insights_last,
    validate_insights_output,
)

runner = CliRunner()

UTC = datetime.timezone.utc
ENCODING = "utf-8"
PROJECT_NAME = "Demo Project"
CONFIG_NAME = "gatorgrade.yml"
CONFIG_TEXT = "name: Demo Project\n---\n- check: ConfirmFileExists\n"
HISTORY_DIR_NAME = "h"
MISSING_CONFIG_NAME = "missing.yml"
OUTPUT_NAME = "insights-out.json"

INSIGHTS_COMMAND = "insights"
ANALYZE_COMMAND = "analyze"
CONFIG_FLAG = "--config"
HISTORY_DIR_FLAG = "--history-dir"
LAST_FLAG = "--last"
FORMAT_FLAG = "--format"
OUTPUT_FLAG = "--output"
HELP_FLAG = "--help"
INPUT_FLAG = "--input"
INSTRUCTOR_FLAG = "--instructor"
SAVE_FLAG = "--save"
OUTPUT_DIR_FLAG = "--output-dir"
SAVE_DIR_NAME = "insights"
NESTED_DIR_NAME = "nested"
SAVED_JSON_NAME = "insights.json"
SAVED_TEXT_NAME = "insights.txt"
ALIAS_HELP_TEXT = "Alias for the insights command."

SAVED_REPORT_NAME = "saved.json"
UNPARSABLE_JSON = "{broken"
NOT_AN_OBJECT_JSON = "[]"
MISSING_FIELD_JSON = '{"scope": "only-a-scope"}'
WRONG_TYPE_JSON = (
    '{"scope": 1, "reports_inspected": "many", "reports_available": 0,'
    ' "checks": [], "best_check": null, "worst_check": null,'
    ' "diagnostics": []}'
)
BAD_CHECK_ENTRY_JSON = (
    '{"scope": "s", "reports_inspected": 1, "reports_available": 1,'
    ' "checks": [{"identifier": "a"}], "best_check": null,'
    ' "worst_check": null, "diagnostics": []}'
)
NOT_A_REPORT_TEXT = "not a valid insights report"
CANNOT_COMBINE_TEXT = "cannot be combined"
NO_SUCH_OPTION_TEXT = "No such option"

CHECK_ALPHA = "check-alpha"
CHECK_BETA = "check-beta"
NAME_ALPHA = "Complete all TODOs"
NAME_BETA = "Use an if statement"
CHECKS_KEY = "checks"
CHECK_ID_KEY = "check_id"
STATUS_KEY = "status"
DESCRIPTION_KEY = "description"

HISTORY_YEAR = 2026
HISTORY_MONTH = 9
MALFORMED_FILE_NAME = "gatorgrade-report-20260930T000000.000000Z-bad.json"
MALFORMED_CONTENTS = "{not valid json"

ONE = 1
TWO = 2
THREE = 3
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
INVALID_LAST = 0
NEGATIVE_LAST = -3

TITLE_TEXT = "GatorGrade Insights"
NO_REPORTS_TEXT = "No valid history reports were found"
WROTE_TEXT = "Wrote"
MISSING_CONFIG_TEXT = "does not exist"
POSITIVE_INTEGER_TEXT = "must be a positive integer"
IS_DIRECTORY_TEXT = "is a directory"
BOOM_MESSAGE = "insights must never run this"


ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
BORDER_PATTERN = re.compile("[─-╿|]")
WHITESPACE_PATTERN = re.compile(r"\s+")
SPACE = " "
EMPTY_TEXT = ""
WINDOWS_ENCODING = "cp1252"
# an empty newline setting stops the wrapper from translating a line feed
# into the platform line ending, which would otherwise make this
# comparison pass on Linux and fail on Windows
UNTRANSLATED_NEWLINE = ""
NARROW_TERMINAL_WIDTH = 40
COLOR_SYSTEM: Literal["standard"] = "standard"
CONSOLE_ATTRIBUTE = "console"
MARKUP_NAME = "[bold]Review caf\u00e9 notes[/bold] :smile:"
GREEN_TITLE = "\x1b[1;32mGatorGrade"
YELLOW_TITLE = "\x1b[1;33mInsights"
GREEN_PASS = "\x1b[1;32mpass"
RED_FAIL = "\x1b[1;31mfail"


def _display_report() -> InsightsReport:
    """Create a report with pass, fail, Unicode, and markup-like text."""
    return main.build_insights_report(
        [
            {
                HISTORY_REPORT_KEY: {
                    CHECKS_KEY: [
                        _check(CHECK_ALPHA, False, MARKUP_NAME),
                        _check(CHECK_BETA, True, NAME_BETA),
                    ]
                }
            }
        ],
        reports_available=ONE,
        scope=PROJECT_NAME,
        file_diagnostics=[],
    )


@pytest.mark.parametrize("instructor", [False, True])
def test_echo_insights_redirects_tables_to_cp1252_without_styling(
    monkeypatch: pytest.MonkeyPatch,
    instructor: bool,
) -> None:
    """Narrow redirected Windows streams preserve the exact ASCII report."""
    payload = main.render_text(_display_report(), instructor=instructor)
    buffer = BytesIO()
    with TextIOWrapper(
        buffer,
        encoding=WINDOWS_ENCODING,
        newline=UNTRANSLATED_NEWLINE,
    ) as stream:
        monkeypatch.setattr(
            main,
            CONSOLE_ATTRIBUTE,
            Console(
                file=stream,
                force_terminal=False,
                width=NARROW_TERMINAL_WIDTH,
            ),
        )
        main._echo_insights(payload)
        stream.flush()
        assert buffer.getvalue() == payload.encode(WINDOWS_ENCODING)


def test_echo_insights_colors_tables_without_changing_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Terminal styling colors titles and statuses without interpreting names."""
    payload = main.render_text(_display_report())
    stream = StringIO()
    monkeypatch.setattr(
        main,
        CONSOLE_ATTRIBUTE,
        Console(
            file=stream,
            force_terminal=True,
            no_color=False,
            color_system=COLOR_SYSTEM,
            width=NARROW_TERMINAL_WIDTH,
        ),
    )
    main._echo_insights(payload)
    output = stream.getvalue()
    assert ANSI_PATTERN.sub(EMPTY_TEXT, output) == payload
    for colored_text in (GREEN_TITLE, YELLOW_TITLE, GREEN_PASS, RED_FAIL):
        assert colored_text in output


def test_echo_insights_keeps_json_raw_in_color_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Color support never adds ANSI codes or wrapping to JSON."""
    payload = main.render_json(_display_report())
    stream = StringIO()
    monkeypatch.setattr(
        main,
        CONSOLE_ATTRIBUTE,
        Console(
            file=stream,
            force_terminal=True,
            no_color=False,
            color_system=COLOR_SYSTEM,
            width=NARROW_TERMINAL_WIDTH,
        ),
    )
    main._echo_insights(payload)
    assert stream.getvalue().rstrip() == payload


def _plain(text: str) -> str:
    """Return CLI output without styling, borders, or wrapped line breaks."""
    without_styling = ANSI_PATTERN.sub(EMPTY_TEXT, text)
    without_borders = BORDER_PATTERN.sub(SPACE, without_styling)
    return WHITESPACE_PATTERN.sub(SPACE, without_borders)


def _write_config(tmp_path: Path) -> Path:
    """Create a configuration file carrying a project name in front matter."""
    config_path = tmp_path / CONFIG_NAME
    config_path.write_text(CONFIG_TEXT, encoding=ENCODING)
    return config_path


def _check(check_id: str, status: bool, description: str) -> dict[str, Any]:
    """Create one check entry as it appears inside a saved report."""
    return {
        CHECK_ID_KEY: check_id,
        STATUS_KEY: status,
        DESCRIPTION_KEY: description,
    }


def _seed_history(
    config_path: Path,
    history_dir: Path,
    runs: list[list[dict[str, Any]]],
) -> Path:
    """Save one history report per run, oldest first, for this config."""
    scope = get_history_scope(config_path, PROJECT_NAME)
    for day, checks in enumerate(runs, start=ONE):
        save_report_history(
            {CHECKS_KEY: checks},
            scope=scope,
            history_directory=history_dir,
            current_time=datetime.datetime(
                HISTORY_YEAR, HISTORY_MONTH, day, tzinfo=UTC
            ),
        )
    return history_dir


def _project(tmp_path: Path) -> tuple[Path, Path]:
    """Create a config plus a three-report history and return both paths."""
    config_path = _write_config(tmp_path)
    history_dir = tmp_path / HISTORY_DIR_NAME
    _seed_history(
        config_path,
        history_dir,
        [
            [
                _check(CHECK_ALPHA, False, NAME_ALPHA),
                _check(CHECK_BETA, True, NAME_BETA),
            ],
            [
                _check(CHECK_ALPHA, False, NAME_ALPHA),
                _check(CHECK_BETA, True, NAME_BETA),
            ],
            [_check(CHECK_ALPHA, True, NAME_ALPHA)],
        ],
    )
    return config_path, history_dir


def _invoke(command: str, *arguments: str) -> Any:
    """Invoke one CLI command with the given arguments."""
    return runner.invoke(app, [command, *arguments])


def test_validate_insights_last_accepts_positive_integers() -> None:
    """A positive report count passes validation unchanged."""
    assert validate_insights_last(ONE) == ONE
    assert validate_insights_last(THREE) == THREE


def test_validate_insights_last_rejects_zero_and_negative() -> None:
    """A non-positive report count raises BadParameter."""
    with pytest.raises(BadParameter):
        validate_insights_last(INVALID_LAST)
    with pytest.raises(BadParameter):
        validate_insights_last(NEGATIVE_LAST)


def test_validate_insights_last_rejects_boolean_values() -> None:
    """A boolean is not accepted even though it is an integer subclass."""
    with pytest.raises(BadParameter):
        validate_insights_last(True)


def test_validate_insights_output_allows_none_and_valid_paths(
    tmp_path: Path,
) -> None:
    """An omitted path is allowed and a writable path passes unchanged."""
    assert validate_insights_output(None) is None
    destination = tmp_path / OUTPUT_NAME
    assert validate_insights_output(destination) == destination


def test_validate_insights_output_rejects_a_directory(tmp_path: Path) -> None:
    """An existing directory is not a valid output file."""
    with pytest.raises(BadParameter):
        validate_insights_output(tmp_path)


def test_validate_insights_output_allows_a_missing_parent(
    tmp_path: Path,
) -> None:
    """A path inside a missing directory is allowed and created on write."""
    destination = tmp_path / HISTORY_DIR_NAME / OUTPUT_NAME
    assert validate_insights_output(destination) == destination


def test_insights_destination_prefers_an_explicit_output_path(
    tmp_path: Path,
) -> None:
    """An explicit output path is used ahead of the save directory."""
    explicit = tmp_path / OUTPUT_NAME
    assert (
        _insights_destination(explicit, True, InsightsFormat.JSON) == explicit
    )


def test_insights_destination_names_the_file_for_the_format() -> None:
    """Saving chooses a filename inside the fixed insights directory."""
    assert (
        _insights_destination(None, True, InsightsFormat.JSON)
        == Path(SAVE_DIR_NAME) / SAVED_JSON_NAME
    )
    assert (
        _insights_destination(None, True, InsightsFormat.TEXT)
        == Path(SAVE_DIR_NAME) / SAVED_TEXT_NAME
    )


def test_insights_destination_is_none_without_saving() -> None:
    """Displaying the analysis alone writes no file at all."""
    assert _insights_destination(None, False, InsightsFormat.TEXT) is None


def test_resolve_insights_config_returns_an_existing_file(
    tmp_path: Path,
) -> None:
    """An existing configuration file resolves to its own path."""
    config_path = _write_config(tmp_path)
    assert _resolve_insights_config(config_path, None) == config_path


def test_resolve_insights_config_exits_when_the_file_is_missing(
    tmp_path: Path,
) -> None:
    """A missing configuration file exits instead of raising a traceback."""
    with pytest.raises(typer.Exit):
        _resolve_insights_config(tmp_path / MISSING_CONFIG_NAME, None)


def test_write_insights_file_reports_an_unwritable_destination(
    tmp_path: Path,
) -> None:
    """A destination that cannot be written exits without a traceback."""
    with pytest.raises(typer.Exit):
        _write_insights_file(tmp_path, TITLE_TEXT, InsightsFormat.TEXT)


def test_build_history_insights_analyzes_the_saved_history(
    tmp_path: Path,
) -> None:
    """The history helper aggregates the saved reports for this project."""
    config_path, history_dir = _project(tmp_path)
    report = _build_history_insights(config_path, None, THREE, history_dir)
    assert report.reports_inspected == THREE
    assert report.reports_available == THREE


def test_insights_command_renders_a_text_summary(tmp_path: Path) -> None:
    """The insights command prints a readable summary of the history."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
    )
    assert result.exit_code == EXIT_SUCCESS
    assert TITLE_TEXT in _plain(result.stdout)
    assert NAME_ALPHA in _plain(result.stdout)
    assert NAME_BETA in _plain(result.stdout)


def test_analyze_alias_matches_the_insights_command(tmp_path: Path) -> None:
    """The analyze alias produces exactly the same output as insights."""
    config_path, history_dir = _project(tmp_path)
    arguments = (
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
    )
    insights_result = _invoke(INSIGHTS_COMMAND, *arguments)
    analyze_result = _invoke(ANALYZE_COMMAND, *arguments)
    assert insights_result.exit_code == EXIT_SUCCESS
    assert analyze_result.exit_code == EXIT_SUCCESS
    assert analyze_result.stdout == insights_result.stdout


def test_analyze_is_presented_as_an_alias_in_the_help() -> None:
    """The help menu lists analyze as an alias rather than a second command."""
    result = runner.invoke(app, [HELP_FLAG])
    plain_help = _plain(result.stdout)
    assert INSIGHTS_COMMAND in plain_help
    assert ANALYZE_COMMAND in plain_help
    assert ALIAS_HELP_TEXT in plain_help


def test_analyze_help_still_documents_every_option() -> None:
    """The alias exposes the same options as the insights command."""
    insights_help = _plain(_invoke(INSIGHTS_COMMAND, HELP_FLAG).stdout)
    analyze_help = _plain(_invoke(ANALYZE_COMMAND, HELP_FLAG).stdout)
    for flag in (CONFIG_FLAG, LAST_FLAG, FORMAT_FLAG, OUTPUT_FLAG):
        assert flag in insights_help
        assert flag in analyze_help


def test_insights_command_emits_valid_json(tmp_path: Path) -> None:
    """The JSON format round-trips through the insights report model."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
    )
    assert result.exit_code == EXIT_SUCCESS
    report = InsightsReport.model_validate_json(result.stdout)
    assert report.reports_inspected == THREE
    assert report.best_check == CHECK_BETA
    assert report.worst_check == CHECK_ALPHA


def test_insights_command_never_counts_an_absent_check(
    tmp_path: Path,
) -> None:
    """A check missing from the newest report is not counted as a pass."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
    )
    report = InsightsReport.model_validate_json(result.stdout)
    summaries = {summary.identifier: summary for summary in report.checks}
    assert summaries[CHECK_BETA].observations == TWO
    assert summaries[CHECK_ALPHA].observations == THREE


def test_insights_command_limits_the_inspected_reports(
    tmp_path: Path,
) -> None:
    """The last option restricts how many recent reports are analyzed."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        LAST_FLAG,
        str(ONE),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
    )
    report = InsightsReport.model_validate_json(result.stdout)
    assert report.reports_inspected == ONE
    assert report.reports_available == THREE


@pytest.mark.parametrize("enable_color", [False, True])
def test_insights_command_writes_a_file_and_keeps_terminal_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enable_color: bool,
) -> None:
    """Writing a file still prints the summary and a confirmation line."""
    monkeypatch.setattr(
        main,
        CONSOLE_ATTRIBUTE,
        Console(force_terminal=enable_color, no_color=not enable_color),
    )
    config_path, history_dir = _project(tmp_path)
    destination = tmp_path / OUTPUT_NAME
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
        OUTPUT_FLAG,
        str(destination),
    )
    assert result.exit_code == EXIT_SUCCESS
    assert TITLE_TEXT in _plain(result.stdout)
    assert WROTE_TEXT in _plain(result.stdout)
    written = json.loads(destination.read_text(encoding=ENCODING))
    assert written["reports_inspected"] == THREE


def test_insights_command_handles_an_empty_history(tmp_path: Path) -> None:
    """An empty history reports nothing to analyze and still succeeds."""
    config_path = _write_config(tmp_path)
    history_dir = tmp_path / HISTORY_DIR_NAME
    history_dir.mkdir()
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
    )
    assert result.exit_code == EXIT_SUCCESS
    assert NO_REPORTS_TEXT in _plain(result.stdout)


def test_insights_command_handles_a_missing_history_directory(
    tmp_path: Path,
) -> None:
    """A history directory that does not exist is not an error."""
    config_path = _write_config(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(tmp_path / HISTORY_DIR_NAME),
    )
    assert result.exit_code == EXIT_SUCCESS
    assert NO_REPORTS_TEXT in _plain(result.stdout)


def test_insights_command_skips_a_malformed_history_file(
    tmp_path: Path,
) -> None:
    """A malformed history file is reported rather than raising an error."""
    config_path, history_dir = _project(tmp_path)
    malformed = history_dir / MALFORMED_FILE_NAME
    malformed.write_text(MALFORMED_CONTENTS, encoding=ENCODING)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
    )
    assert result.exit_code == EXIT_SUCCESS
    report = InsightsReport.model_validate_json(result.stdout)
    assert report.reports_inspected == THREE
    assert len(report.diagnostics) == ONE


def test_insights_command_ignores_another_projects_history(
    tmp_path: Path,
) -> None:
    """Reports saved under a different scope are not analyzed."""
    config_path, history_dir = _project(tmp_path)
    other_config = tmp_path / MISSING_CONFIG_NAME
    save_report_history(
        {CHECKS_KEY: [_check(CHECK_BETA, False, NAME_BETA)]},
        scope=get_history_scope(other_config, None),
        history_directory=history_dir,
        current_time=datetime.datetime(
            HISTORY_YEAR, HISTORY_MONTH, THREE, tzinfo=UTC
        ),
    )
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
    )
    report = InsightsReport.model_validate_json(result.stdout)
    assert report.reports_inspected == THREE
    assert report.reports_available == THREE


def test_insights_command_reports_a_missing_configuration(
    tmp_path: Path,
) -> None:
    """A missing configuration file fails cleanly with a useful message."""
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(tmp_path / MISSING_CONFIG_NAME),
        HISTORY_DIR_FLAG,
        str(tmp_path),
    )
    assert result.exit_code == EXIT_FAILURE
    assert MISSING_CONFIG_TEXT in _plain(result.stdout)


def test_insights_command_rejects_a_non_positive_last(tmp_path: Path) -> None:
    """A zero value for the last option is rejected before any analysis."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        LAST_FLAG,
        str(INVALID_LAST),
    )
    assert result.exit_code != EXIT_SUCCESS
    assert POSITIVE_INTEGER_TEXT in _plain(result.output)


def test_insights_command_rejects_a_directory_output(tmp_path: Path) -> None:
    """An output path that names a directory is rejected."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        OUTPUT_FLAG,
        str(history_dir),
    )
    assert result.exit_code != EXIT_SUCCESS
    assert IS_DIRECTORY_TEXT in _plain(result.output)


def test_insights_command_creates_a_missing_output_directory(
    tmp_path: Path,
) -> None:
    """An output path inside a missing directory creates that directory."""
    config_path, history_dir = _project(tmp_path)
    destination = tmp_path / SAVE_DIR_NAME / NESTED_DIR_NAME / OUTPUT_NAME
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        OUTPUT_FLAG,
        str(destination),
    )
    assert result.exit_code == EXIT_SUCCESS
    assert destination.is_file()


def test_insights_command_saves_into_the_insights_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saving writes a named report into the fixed insights directory."""
    monkeypatch.chdir(tmp_path)
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
        SAVE_FLAG,
    )
    assert result.exit_code == EXIT_SUCCESS
    saved = tmp_path / SAVE_DIR_NAME / SAVED_JSON_NAME
    assert saved.is_file()
    assert (
        json.loads(saved.read_text(encoding=ENCODING))["reports_inspected"]
        == THREE
    )


def test_insights_command_saves_text_under_a_text_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saving a text analysis names the file for the text format."""
    monkeypatch.chdir(tmp_path)
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        SAVE_FLAG,
    )
    assert result.exit_code == EXIT_SUCCESS
    assert (tmp_path / SAVE_DIR_NAME / SAVED_TEXT_NAME).is_file()


def test_insights_command_rejects_an_output_directory_option(
    tmp_path: Path,
) -> None:
    """A custom output directory is rejected so checks keep one path."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        SAVE_FLAG,
        OUTPUT_DIR_FLAG,
        str(tmp_path / SAVE_DIR_NAME),
    )
    assert result.exit_code != EXIT_SUCCESS
    assert NO_SUCH_OPTION_TEXT in result.output
    assert not (tmp_path / SAVE_DIR_NAME / SAVED_JSON_NAME).exists()


def test_insights_command_rejects_saving_with_an_output_path(
    tmp_path: Path,
) -> None:
    """Choosing both a saved directory and an output path is rejected."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        SAVE_FLAG,
        OUTPUT_FLAG,
        str(tmp_path / OUTPUT_NAME),
    )
    assert result.exit_code == EXIT_FAILURE
    assert CANNOT_COMBINE_TEXT in _plain(result.stdout)


def test_validate_insights_input_allows_none_and_existing_files(
    tmp_path: Path,
) -> None:
    """An omitted path is allowed and an existing file passes unchanged."""
    assert validate_insights_input(None) is None
    saved = tmp_path / SAVED_REPORT_NAME
    saved.write_text(NOT_AN_OBJECT_JSON, encoding=ENCODING)
    assert validate_insights_input(saved) == saved


def test_validate_insights_input_rejects_a_directory(tmp_path: Path) -> None:
    """A directory is not a saved report."""
    with pytest.raises(BadParameter):
        validate_insights_input(tmp_path)


def test_validate_insights_input_rejects_a_missing_file(
    tmp_path: Path,
) -> None:
    """A path that does not exist is rejected before any reading happens."""
    with pytest.raises(BadParameter):
        validate_insights_input(tmp_path / SAVED_REPORT_NAME)


def test_load_insights_report_reads_a_saved_report(tmp_path: Path) -> None:
    """A report written by the command loads back into the same model."""
    config_path, history_dir = _project(tmp_path)
    report = _build_history_insights(config_path, None, THREE, history_dir)
    saved = tmp_path / SAVED_REPORT_NAME
    saved.write_text(report.model_dump_json(), encoding=ENCODING)
    assert _load_insights_report(saved) == report


@pytest.mark.parametrize(
    "contents",
    [
        UNPARSABLE_JSON,
        NOT_AN_OBJECT_JSON,
        MISSING_FIELD_JSON,
        WRONG_TYPE_JSON,
        BAD_CHECK_ENTRY_JSON,
    ],
)
def test_load_insights_report_rejects_malformed_files(
    tmp_path: Path,
    contents: str,
) -> None:
    """Every structurally invalid report exits instead of raising."""
    saved = tmp_path / SAVED_REPORT_NAME
    saved.write_text(contents, encoding=ENCODING)
    with pytest.raises(typer.Exit):
        _load_insights_report(saved)


def test_load_insights_report_reports_an_unreadable_file(
    tmp_path: Path,
) -> None:
    """A path that cannot be read exits without a traceback."""
    with pytest.raises(typer.Exit):
        _load_insights_report(tmp_path)


def test_insights_command_replays_a_saved_report(tmp_path: Path) -> None:
    """A report written with output can be rendered again with input."""
    config_path, history_dir = _project(tmp_path)
    saved = tmp_path / SAVED_REPORT_NAME
    written = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
        OUTPUT_FLAG,
        str(saved),
    )
    assert written.exit_code == EXIT_SUCCESS
    replayed = _invoke(INSIGHTS_COMMAND, INPUT_FLAG, str(saved))
    assert replayed.exit_code == EXIT_SUCCESS
    assert TITLE_TEXT in _plain(replayed.stdout)
    assert NAME_ALPHA in _plain(replayed.stdout)


def test_insights_command_replays_a_saved_report_as_json(
    tmp_path: Path,
) -> None:
    """Replaying with JSON output reproduces the saved report exactly."""
    config_path, history_dir = _project(tmp_path)
    saved = tmp_path / SAVED_REPORT_NAME
    _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
        OUTPUT_FLAG,
        str(saved),
    )
    result = _invoke(
        INSIGHTS_COMMAND,
        INPUT_FLAG,
        str(saved),
        FORMAT_FLAG,
        InsightsFormat.JSON.value,
    )
    assert result.exit_code == EXIT_SUCCESS
    original = InsightsReport.model_validate_json(
        saved.read_text(encoding=ENCODING)
    )
    assert InsightsReport.model_validate_json(result.stdout) == original


def test_insights_command_rejects_a_malformed_saved_report(
    tmp_path: Path,
) -> None:
    """A corrupt saved report fails with a message and no traceback."""
    saved = tmp_path / SAVED_REPORT_NAME
    saved.write_text(UNPARSABLE_JSON, encoding=ENCODING)
    result = _invoke(INSIGHTS_COMMAND, INPUT_FLAG, str(saved))
    assert result.exit_code == EXIT_FAILURE
    assert NOT_A_REPORT_TEXT in _plain(result.stdout)


def test_insights_command_rejects_input_combined_with_last(
    tmp_path: Path,
) -> None:
    """Analyzing a saved report cannot be narrowed by a history option."""
    config_path, history_dir = _project(tmp_path)
    saved = tmp_path / SAVED_REPORT_NAME
    saved.write_text(
        _build_history_insights(
            config_path, None, THREE, history_dir
        ).model_dump_json(),
        encoding=ENCODING,
    )
    result = _invoke(
        INSIGHTS_COMMAND,
        INPUT_FLAG,
        str(saved),
        LAST_FLAG,
        str(ONE),
    )
    assert result.exit_code == EXIT_FAILURE
    assert CANNOT_COMBINE_TEXT in _plain(result.stdout)


def test_insights_command_rejects_input_combined_with_history_dir(
    tmp_path: Path,
) -> None:
    """Analyzing a saved report cannot be pointed at a history directory."""
    config_path, history_dir = _project(tmp_path)
    saved = tmp_path / SAVED_REPORT_NAME
    saved.write_text(
        _build_history_insights(
            config_path, None, THREE, history_dir
        ).model_dump_json(),
        encoding=ENCODING,
    )
    result = _invoke(
        INSIGHTS_COMMAND,
        INPUT_FLAG,
        str(saved),
        HISTORY_DIR_FLAG,
        str(history_dir),
    )
    assert result.exit_code == EXIT_FAILURE
    assert CANNOT_COMBINE_TEXT in _plain(result.stdout)


def test_insights_command_accepts_the_instructor_flag(tmp_path: Path) -> None:
    """The instructor flag is accepted and the command still succeeds."""
    config_path, history_dir = _project(tmp_path)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
        INSTRUCTOR_FLAG,
    )
    assert result.exit_code == EXIT_SUCCESS
    assert TITLE_TEXT in _plain(result.stdout)


def test_insights_command_runs_no_checks_or_configuration_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The command never parses checks, runs them, or hints while analyzing."""

    def _explode(*arguments: Any, **keywords: Any) -> Any:
        """Fail loudly when a check-running code path is reached."""
        raise AssertionError(BOOM_MESSAGE)

    config_path, history_dir = _project(tmp_path)
    monkeypatch.setattr(main, "parse_config", _explode)
    monkeypatch.setattr(main, "run_checks", _explode)
    monkeypatch.setattr(main, "create_auto_hint_engine", _explode)
    result = _invoke(
        INSIGHTS_COMMAND,
        CONFIG_FLAG,
        str(config_path),
        HISTORY_DIR_FLAG,
        str(history_dir),
    )
    assert result.exit_code == EXIT_SUCCESS
    assert TITLE_TEXT in _plain(result.stdout)
