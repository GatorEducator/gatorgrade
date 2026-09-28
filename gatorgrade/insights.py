"""Analyze saved report history to produce deterministic check insights."""

from pathlib import Path
from textwrap import wrap
from typing import Any

from pydantic import BaseModel

from gatorgrade.report_history import (
    CHECK_ID_KEY,
    CHECKS_KEY,
    HISTORY_REPORT_KEY,
    HISTORY_SAVED_AT_KEY,
    HISTORY_SKIP_DIFFERENT_SCOPE,
    STATUS_KEY,
)

# keys read from the check dictionaries stored inside a history report
DESCRIPTION_KEY = "description"
CHECK_NAME_KEY = "check"
PATH_KEY = "path"
FALLBACK_IDENTIFIER_PREFIX = "description::"
NAME_WITH_PATH = "{} ({})"

# aggregation rules, documented here so the output is reproducible
INSIGHTS_RATE_PRECISION = 4
INSIGHTS_MIN_TREND_OBS = 4
INSIGHTS_TREND_EPS = 0.05
INSIGHTS_MIN_RANK_OBS = 2

# trend labels attached to every emitted check summary
TREND_IMPROVING = "improving"
TREND_DECLINING = "declining"
TREND_STABLE = "stable"
TREND_INSUFFICIENT_DATA = "insufficient-data"

# diagnostic reasons produced by this module for check-level problems
INSIGHTS_SKIP_CHECK_ENTRY = "skip_check_entry"
INSIGHTS_MISSING_IDENTITY = "missing_identity"
INSIGHTS_INVALID_STATUS = "invalid_status"
INSIGHTS_DUPLICATE_CHECK = "duplicate_check"
INSIGHTS_MALFORMED_REPORT = "malformed_report"

# diagnostic kinds that say which layer of the data a diagnostic is about
DIAGNOSTIC_KIND_FILE = "file"
DIAGNOSTIC_KIND_REPORT = "report"
DIAGNOSTIC_KIND_CHECK = "check"

# labels used when building diagnostic sources and details
REPORT_SOURCE_PREFIX = "report "
FILE_SKIPPED_DETAIL = "history file skipped by the loader"
MALFORMED_REPORT_DETAIL = "report does not contain a list of checks"
SKIP_CHECK_ENTRY_DETAIL = "check entry {} is not an object"
MISSING_IDENTITY_DETAIL = "check entry {} has no check_id or description"
INVALID_STATUS_DETAIL = (
    "check '{}' has an unreadable status and counts as a non-pass"
)
DUPLICATE_CHECK_DETAIL = (
    "check '{}' appears more than once and passes only if every entry passed"
)

# text rendering pieces
JSON_INDENT = 2
NEWLINE = "\n"
TEXT_SCOPE = "Scope: {}"
TEXT_REPORTS = "Reports inspected: {} of {} available"
TEXT_NO_REPORTS = "No valid history reports were found for this project."
TEXT_NO_CHECKS = "No checks were observed in the inspected reports."
TEXT_STATUS_PASS = "pass"
TEXT_STATUS_FAIL = "fail"
TEXT_STREAK_PASSING = "passing"
TEXT_STREAK_FAILING = "failing"
TEXT_DIAGNOSTICS_HEADER = "Diagnostics ({}):"
TEXT_DIAGNOSTIC = "- {} {}: {} ({})"
TEXT_EMPTY = ""
STRUGGLE_THRESHOLD = 0.85
COLUMN_WIDTHS = (4, 6, 6, 10, 12, 12, 7)
FOCUS_COLUMN_WIDTHS = (4, 6, 20)
CHECK_NAME_WIDTH = 48
TABLE_PADDING = 2
TABLE_CORNER = "+"
TABLE_HORIZONTAL = "-"
TABLE_CELL_SEPARATOR = " | "
TABLE_ROW_START = "| "
TABLE_ROW_END = " |"
IDENTIFIER_WIDTH = 12
# every heading rule and the threshold wording are derived rather than
# typed out, so that a reworded heading cannot drift out of alignment and
# a changed threshold cannot leave the text claiming the old percentage
TITLE_WORDS = "GatorGrade Insights"
TITLE_RULE_WIDTH = 33
TEXT_TITLE = (
    f"{TABLE_HORIZONTAL * TITLE_RULE_WIDTH} {TITLE_WORDS} "
    f"{TABLE_HORIZONTAL * TITLE_RULE_WIDTH}"
)
STRUGGLE_PERCENT = f"{STRUGGLE_THRESHOLD:.0%}"
TEXT_FOCUS_HEADER = f"FOCUS ON THESE (passing under {STRUGGLE_PERCENT})"
TEXT_FOCUS_UNDERLINE = TABLE_HORIZONTAL * len(TEXT_FOCUS_HEADER)
TEXT_NO_FOCUS = (
    f"Nothing to focus on: all checks are passing at least {STRUGGLE_PERCENT}."
)
TEXT_ALL_HEADER = "ALL CHECKS (worst first)"
TEXT_ALL_UNDERLINE = TABLE_HORIZONTAL * len(TEXT_ALL_HEADER)
TEXT_COLUMNS = ("RATE", "PASSED", "LATEST", "STREAK", "TREND")
TEXT_DETAIL_COLUMNS = ("ID", "DELTA")
TEXT_NAME_COLUMN = "CHECK"
TEXT_COUNTS = "{}/{}"
TEXT_RATE = "{:.0%}"
TEXT_STREAK = "{} {}"
TEXT_FOCUS_COLUMNS = ("RATE", "PASSED", "RECENT")
TEXT_FAILING = "{} failing in a row"
TEXT_LATEST = "latest {}"
TEXT_DELTA = "{:+.4f}"
TEXT_NO_DELTA = "-"
TEXT_INSUFFICIENT = "insufficient"
TEXT_SKIPPED = "Skipped {} history files ({} from other projects, {} other)"
TEXT_WARNINGS = "Report/check diagnostics: {}"
ASCII_ENCODING = "ascii"
ASCII_ERRORS = "backslashreplace"


class CheckObservation(BaseModel):
    """Record one observation of a check inside one saved report."""

    identifier: str
    name: str
    report_index: int
    source: str
    passed: bool
    status_valid: bool


class CheckSummary(BaseModel):
    """Summarize every observation of one check across the history."""

    identifier: str
    name: str
    observations: int
    passes: int
    pass_rate: float
    latest_status: bool
    current_pass_streak: int
    current_fail_streak: int
    trend: str
    trend_delta: float | None
    status_history: list[bool]


class HistoryDiagnostic(BaseModel):
    """Explain why a file, report, or check entry was skipped or flagged."""

    kind: str
    source: str
    reason: str
    detail: str


class InsightsReport(BaseModel):
    """Hold the complete deterministic insights for one project scope."""

    scope: str
    reports_inspected: int
    reports_available: int
    checks: list[CheckSummary]
    best_check: str | None
    worst_check: str | None
    diagnostics: list[HistoryDiagnostic]


def _report_source(payload: dict[str, Any], report_index: int) -> str:
    """Return a human-readable label for one chronological report."""
    saved_at = payload.get(HISTORY_SAVED_AT_KEY)
    if isinstance(saved_at, str) and saved_at:
        return saved_at
    return f"{REPORT_SOURCE_PREFIX}{report_index + 1}"


def _check_identifier(check: dict[Any, Any]) -> str | None:
    """Return the stable identity of a check entry, or None when absent."""
    check_id = check.get(CHECK_ID_KEY)
    if isinstance(check_id, str) and check_id:
        return check_id
    description = check.get(DESCRIPTION_KEY)
    if isinstance(description, str) and description:
        return f"{FALLBACK_IDENTIFIER_PREFIX}{description}"
    return None


def _check_name(check: dict[Any, Any], identifier: str) -> str:
    """Return a human-readable name for a check entry, with its path."""
    name = identifier
    for key in (DESCRIPTION_KEY, CHECK_NAME_KEY):
        value = check.get(key)
        if isinstance(value, str) and value:
            name = value
            break
    path = check.get(PATH_KEY)
    if isinstance(path, str) and path:
        return NAME_WITH_PATH.format(name, path)
    return name


def _make_diagnostic(
    kind: str,
    source: str,
    reason: str,
    detail: str,
) -> HistoryDiagnostic:
    """Create one structured diagnostic."""
    return HistoryDiagnostic(
        kind=kind,
        source=source,
        reason=reason,
        detail=detail,
    )


def _file_diagnostics(
    file_diagnostics: list[tuple[Path, str]],
) -> list[HistoryDiagnostic]:
    """Convert loader skip reasons into structured diagnostics."""
    return [
        _make_diagnostic(
            DIAGNOSTIC_KIND_FILE,
            path.name,
            reason,
            FILE_SKIPPED_DETAIL,
        )
        for path, reason in file_diagnostics
    ]


def _merge_duplicate(
    existing: CheckObservation,
    passed: bool,
    status_valid: bool,
) -> CheckObservation:
    """Merge a repeated entry so the check passes only if every entry passed."""
    return existing.model_copy(
        update={
            "passed": existing.passed and passed,
            "status_valid": existing.status_valid and status_valid,
        }
    )


def _observe_report(
    payload: dict[str, Any],
    report_index: int,
) -> tuple[list[CheckObservation], list[HistoryDiagnostic]]:
    """Convert the check entries of one report into observations."""
    source = _report_source(payload, report_index)
    report = payload.get(HISTORY_REPORT_KEY)
    checks = report.get(CHECKS_KEY) if isinstance(report, dict) else None
    if not isinstance(checks, list):
        diagnostic = _make_diagnostic(
            DIAGNOSTIC_KIND_REPORT,
            source,
            INSIGHTS_MALFORMED_REPORT,
            MALFORMED_REPORT_DETAIL,
        )
        return [], [diagnostic]
    observations: dict[str, CheckObservation] = {}
    diagnostics: list[HistoryDiagnostic] = []
    for entry_index, entry in enumerate(checks):
        if not isinstance(entry, dict):
            diagnostics.append(
                _make_diagnostic(
                    DIAGNOSTIC_KIND_CHECK,
                    source,
                    INSIGHTS_SKIP_CHECK_ENTRY,
                    SKIP_CHECK_ENTRY_DETAIL.format(entry_index),
                )
            )
            continue
        identifier = _check_identifier(entry)
        if identifier is None:
            diagnostics.append(
                _make_diagnostic(
                    DIAGNOSTIC_KIND_CHECK,
                    source,
                    INSIGHTS_MISSING_IDENTITY,
                    MISSING_IDENTITY_DETAIL.format(entry_index),
                )
            )
            continue
        name = _check_name(entry, identifier)
        status = entry.get(STATUS_KEY)
        status_valid = isinstance(status, bool)
        passed = status is True
        if not status_valid:
            diagnostics.append(
                _make_diagnostic(
                    DIAGNOSTIC_KIND_CHECK,
                    source,
                    INSIGHTS_INVALID_STATUS,
                    INVALID_STATUS_DETAIL.format(name),
                )
            )
        existing = observations.get(identifier)
        if existing is None:
            observations[identifier] = CheckObservation(
                identifier=identifier,
                name=name,
                report_index=report_index,
                source=source,
                passed=passed,
                status_valid=status_valid,
            )
            continue
        diagnostics.append(
            _make_diagnostic(
                DIAGNOSTIC_KIND_CHECK,
                source,
                INSIGHTS_DUPLICATE_CHECK,
                DUPLICATE_CHECK_DETAIL.format(name),
            )
        )
        observations[identifier] = _merge_duplicate(
            existing, passed, status_valid
        )
    return list(observations.values()), diagnostics


def _pass_rate(status_history: list[bool]) -> float:
    """Return the rounded fraction of passing statuses in a sequence."""
    return round(
        sum(status_history) / len(status_history),
        INSIGHTS_RATE_PRECISION,
    )


def _current_streaks(status_history: list[bool]) -> tuple[int, int]:
    """Return the current pass and fail streaks from the newest observation."""
    if not status_history:
        return 0, 0
    latest = status_history[-1]
    streak = 0
    for status in reversed(status_history):
        if status != latest:
            break
        streak += 1
    if latest:
        return streak, 0
    return 0, streak


def _compute_trend(status_history: list[bool]) -> tuple[str, float | None]:
    """Classify the trend by comparing older and newer observation halves."""
    if len(status_history) < INSIGHTS_MIN_TREND_OBS:
        return TREND_INSUFFICIENT_DATA, None
    split_index = len(status_history) // 2
    older_rate = _pass_rate(status_history[:split_index])
    newer_rate = _pass_rate(status_history[split_index:])
    trend_delta = round(newer_rate - older_rate, INSIGHTS_RATE_PRECISION)
    if trend_delta > INSIGHTS_TREND_EPS:
        return TREND_IMPROVING, trend_delta
    if trend_delta < -INSIGHTS_TREND_EPS:
        return TREND_DECLINING, trend_delta
    return TREND_STABLE, trend_delta


def _display_name(
    identifier: str,
    observations: list[CheckObservation],
) -> str:
    """Return the newest readable name recorded for a check."""
    for observation in reversed(observations):
        if observation.name != identifier:
            return observation.name
    return identifier


def _summarize_check(
    identifier: str,
    observations: list[CheckObservation],
) -> CheckSummary:
    """Aggregate the chronological observations of one check."""
    status_history = [observation.passed for observation in observations]
    pass_streak, fail_streak = _current_streaks(status_history)
    trend, trend_delta = _compute_trend(status_history)
    return CheckSummary(
        identifier=identifier,
        name=_display_name(identifier, observations),
        observations=len(status_history),
        passes=sum(status_history),
        pass_rate=_pass_rate(status_history),
        latest_status=status_history[-1],
        current_pass_streak=pass_streak,
        current_fail_streak=fail_streak,
        trend=trend,
        trend_delta=trend_delta,
        status_history=status_history,
    )


def _best_sort_key(summary: CheckSummary) -> tuple[float, int, int, str]:
    """Return the ordering key that puts the best check first."""
    return (
        -summary.pass_rate,
        -summary.observations,
        -summary.current_pass_streak,
        summary.identifier,
    )


def _worst_sort_key(summary: CheckSummary) -> tuple[float, int, int, str]:
    """Return the ordering key that puts the worst check first."""
    return (
        summary.pass_rate,
        -summary.observations,
        -summary.current_fail_streak,
        summary.identifier,
    )


def _rankable_checks(checks: list[CheckSummary]) -> list[CheckSummary]:
    """Return the checks with enough observations to be ranked."""
    return [
        summary
        for summary in checks
        if summary.observations >= INSIGHTS_MIN_RANK_OBS
    ]


def _select_best_check(checks: list[CheckSummary]) -> str | None:
    """Return the identifier of the best-performing check, if any."""
    candidates = _rankable_checks(checks)
    if not candidates:
        return None
    return min(candidates, key=_best_sort_key).identifier


def _select_worst_check(checks: list[CheckSummary]) -> str | None:
    """Return the identifier of the worst-performing check, if any."""
    candidates = _rankable_checks(checks)
    if not candidates:
        return None
    return min(candidates, key=_worst_sort_key).identifier


def build_insights_report(
    payloads: list[dict[str, Any]],
    *,
    reports_available: int,
    scope: str,
    file_diagnostics: list[tuple[Path, str]],
) -> InsightsReport:
    """Aggregate newest-first history payloads into an insights report."""
    diagnostics = _file_diagnostics(file_diagnostics)
    observations_by_check: dict[str, list[CheckObservation]] = {}
    for report_index, payload in enumerate(reversed(payloads)):
        observations, report_diagnostics = _observe_report(
            payload, report_index
        )
        diagnostics.extend(report_diagnostics)
        for observation in observations:
            observations_by_check.setdefault(
                observation.identifier, []
            ).append(observation)
    checks = [
        _summarize_check(identifier, observations_by_check[identifier])
        for identifier in sorted(observations_by_check)
    ]
    return InsightsReport(
        scope=scope,
        reports_inspected=len(payloads),
        reports_available=reports_available,
        checks=checks,
        best_check=_select_best_check(checks),
        worst_check=_select_worst_check(checks),
        diagnostics=diagnostics,
    )


def _status_label(status: bool) -> str:
    """Return the text label for a boolean status."""
    return TEXT_STATUS_PASS if status else TEXT_STATUS_FAIL


def sort_checks_by_struggle(checks: list[CheckSummary]) -> list[CheckSummary]:
    """Return checks in worst-first order without changing the input."""
    return sorted(checks, key=_worst_sort_key)


def struggling_checks(checks: list[CheckSummary]) -> list[CheckSummary]:
    """Return checks passing strictly below the struggle threshold."""
    return [check for check in checks if check.pass_rate < STRUGGLE_THRESHOLD]


def _render_row(
    fields: list[str],
    name: str,
    *,
    widths: tuple[int, ...] = COLUMN_WIDTHS,
) -> str:
    """Wrap ASCII cells within aligned borders without truncating names."""
    cell_widths = (*widths[: len(fields)], CHECK_NAME_WIDTH)
    cells = [
        wrap(
            value.encode(ASCII_ENCODING, errors=ASCII_ERRORS).decode(
                ASCII_ENCODING
            ),
            width=width,
            break_on_hyphens=False,
        )
        or [TEXT_EMPTY]
        for value, width in zip([*fields, name], cell_widths, strict=True)
    ]
    return NEWLINE.join(
        TABLE_ROW_START
        + TABLE_CELL_SEPARATOR.join(
            (cell[index] if index < len(cell) else TEXT_EMPTY).ljust(width)
            for cell, width in zip(cells, cell_widths, strict=True)
        )
        + TABLE_ROW_END
        for index in range(max(len(cell) for cell in cells))
    )


def _render_table(
    columns: tuple[str, ...],
    rows: list[str],
    *,
    widths: tuple[int, ...] = COLUMN_WIDTHS,
) -> list[str]:
    """Add ASCII borders and a heading to wrapped table rows."""
    border = (
        TABLE_CORNER
        + TABLE_CORNER.join(
            TABLE_HORIZONTAL * (width + TABLE_PADDING)
            for width in (*widths[: len(columns)], CHECK_NAME_WIDTH)
        )
        + TABLE_CORNER
    )
    lines = [
        border,
        _render_row(list(columns), TEXT_NAME_COLUMN, widths=widths),
        border,
    ]
    for row in rows:
        lines.extend([row, border])
    return lines


def _render_check(summary: CheckSummary, *, instructor: bool = False) -> str:
    """Render one aligned row with the complete check name last."""
    streak_length = summary.current_pass_streak or summary.current_fail_streak
    streak_label = (
        TEXT_STREAK_PASSING
        if summary.current_pass_streak
        else TEXT_STREAK_FAILING
    )
    trend = (
        TEXT_INSUFFICIENT
        if summary.trend == TREND_INSUFFICIENT_DATA
        else summary.trend
    )
    fields = [
        TEXT_RATE.format(summary.pass_rate),
        TEXT_COUNTS.format(summary.passes, summary.observations),
        _status_label(summary.latest_status),
        TEXT_STREAK.format(streak_length, streak_label),
        trend,
    ]
    if instructor:
        delta = (
            TEXT_NO_DELTA
            if summary.trend_delta is None
            else TEXT_DELTA.format(summary.trend_delta)
        )
        fields.extend([summary.identifier[:IDENTIFIER_WIDTH], delta])
    return _render_row(fields, summary.name)


def _render_focus(summary: CheckSummary) -> str:
    """Render one actionable focus entry."""
    detail = TEXT_LATEST.format(_status_label(summary.latest_status))
    if summary.current_fail_streak:
        detail = TEXT_FAILING.format(summary.current_fail_streak)
    elif summary.trend == TREND_IMPROVING:
        detail = TREND_IMPROVING
    return _render_row(
        [
            TEXT_RATE.format(summary.pass_rate),
            TEXT_COUNTS.format(summary.passes, summary.observations),
            detail,
        ],
        summary.name,
        widths=FOCUS_COLUMN_WIDTHS,
    )


def _render_diagnostics(
    report: InsightsReport,
    *,
    instructor: bool = False,
) -> list[str]:
    """Render concise student counts or complete instructor diagnostics."""
    if not report.diagnostics:
        return []
    if instructor:
        return [TEXT_DIAGNOSTICS_HEADER.format(len(report.diagnostics))] + [
            TEXT_DIAGNOSTIC.format(
                diagnostic.kind,
                diagnostic.source,
                diagnostic.detail,
                diagnostic.reason,
            )
            for diagnostic in report.diagnostics
        ]
    files = [
        diagnostic
        for diagnostic in report.diagnostics
        if diagnostic.kind == DIAGNOSTIC_KIND_FILE
    ]
    other_scope = sum(
        diagnostic.reason == HISTORY_SKIP_DIFFERENT_SCOPE
        for diagnostic in files
    )
    lines = []
    if files:
        lines.append(
            TEXT_SKIPPED.format(
                len(files),
                other_scope,
                len(files) - other_scope,
            )
        )
    warnings = len(report.diagnostics) - len(files)
    if warnings:
        lines.append(TEXT_WARNINGS.format(warnings))
    return lines


def render_text(
    report: InsightsReport,
    *,
    instructor: bool = False,
) -> str:
    """Render an insights report as deterministic ASCII plain text."""
    lines = [
        TEXT_EMPTY,
        TEXT_TITLE,
        TEXT_REPORTS.format(report.reports_inspected, report.reports_available)
        .center(len(TEXT_TITLE))
        .rstrip(),
    ]
    if instructor:
        lines.append(TEXT_SCOPE.format(report.scope))
    lines.append(TEXT_EMPTY)
    if report.reports_inspected == 0:
        lines.append(TEXT_NO_REPORTS)
    elif not report.checks:
        lines.append(TEXT_NO_CHECKS)
    else:
        checks = sort_checks_by_struggle(report.checks)
        focus = struggling_checks(checks)
        if focus:
            lines.append(TEXT_FOCUS_HEADER)
            lines.append(TEXT_FOCUS_UNDERLINE)
            lines.extend(
                _render_table(
                    TEXT_FOCUS_COLUMNS,
                    [_render_focus(summary) for summary in focus],
                    widths=FOCUS_COLUMN_WIDTHS,
                )
            )
        else:
            lines.append(TEXT_NO_FOCUS)
        columns = list(TEXT_COLUMNS)
        if instructor:
            columns.extend(TEXT_DETAIL_COLUMNS)
        lines.extend(
            [
                TEXT_EMPTY,
                TEXT_ALL_HEADER,
                TEXT_ALL_UNDERLINE,
            ]
        )
        lines.extend(
            _render_table(
                tuple(columns),
                [
                    _render_check(summary, instructor=instructor)
                    for summary in checks
                ],
            )
        )
    diagnostic_lines = _render_diagnostics(report, instructor=instructor)
    if diagnostic_lines:
        lines.append(TEXT_EMPTY)
        lines.extend(diagnostic_lines)
    text = NEWLINE.join(lines) + NEWLINE
    return text.encode(ASCII_ENCODING, errors=ASCII_ERRORS).decode(
        ASCII_ENCODING
    )


def render_json(report: InsightsReport) -> str:
    """Render an insights report as deterministic JSON."""
    return report.model_dump_json(indent=JSON_INDENT)
