"""Tests for the insights analysis built on saved report history."""

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade.insights import (
    CHECK_NAME_WIDTH,
    DIAGNOSTIC_KIND_CHECK,
    DIAGNOSTIC_KIND_FILE,
    DIAGNOSTIC_KIND_REPORT,
    FALLBACK_IDENTIFIER_PREFIX,
    HISTORY_SKIP_DIFFERENT_SCOPE,
    INSIGHTS_DUPLICATE_CHECK,
    INSIGHTS_INVALID_STATUS,
    INSIGHTS_MALFORMED_REPORT,
    INSIGHTS_MIN_RANK_OBS,
    INSIGHTS_MISSING_IDENTITY,
    INSIGHTS_SKIP_CHECK_ENTRY,
    NAME_WITH_PATH,
    NEWLINE,
    REPORT_SOURCE_PREFIX,
    TEXT_NO_CHECKS,
    TEXT_NO_FOCUS,
    TEXT_NO_REPORTS,
    TEXT_SKIPPED,
    TEXT_TITLE,
    TREND_DECLINING,
    TREND_IMPROVING,
    TREND_INSUFFICIENT_DATA,
    TREND_STABLE,
    CheckObservation,
    CheckSummary,
    HistoryDiagnostic,
    InsightsReport,
    _best_sort_key,
    _check_identifier,
    _check_name,
    _compute_trend,
    _current_streaks,
    _display_name,
    _file_diagnostics,
    _make_diagnostic,
    _merge_duplicate,
    _observe_report,
    _pass_rate,
    _rankable_checks,
    _render_check,
    _render_diagnostics,
    _render_focus,
    _render_row,
    _render_table,
    _report_source,
    _select_best_check,
    _select_worst_check,
    _status_label,
    _summarize_check,
    _worst_sort_key,
    build_insights_report,
    render_json,
    render_text,
    sort_checks_by_struggle,
    struggling_checks,
)

SCOPE = "project-scope"
CHECK_A = "check-a"
CHECK_B = "check-b"
CHECK_C = "check-c"
NAME_A = "Complete all TODOs"
NAME_B = "Use an if statement"
NAME_C = "Run the tests"
SAVED_AT_PREFIX = "2026-09-"
SAVED_AT_FIRST = "2026-09-01"
FILE_NAME = "gatorgrade-report-one.json"
FILE_REASON = "invalid_json"
FILE_PATH = "src/hello-world.py"
INVALID_STATUS = "yes"
ZERO = 0
ONE = 1
TWO = 2
THREE = 3
FOUR = 4
FIVE = 5
SIX = 6
SEVEN = 7
TWO_THIRDS = 0.6667
ONE_THIRD = 0.3333
HALF = 0.5
FULL = 1.0
NONE_RATE = 0.0
STABLE_OLDER_PASSES = 10
STABLE_NEWER_PASSES = 11
STABLE_HALF_SIZE = 20
IMPROVING_DELTA = 1.0
DECLINING_DELTA = -1.0
STABLE_DELTA = 0.05
ZERO_DELTA = 0.0
NEGATIVE_ONE = -1
THRESHOLD = 0.85
BELOW_THRESHOLD = 0.849
LONG_NAME = "Complete every required exercise " * THREE
UNICODE_NAME = "Review caf\u00e9 notes"
LONG_IDENTIFIER = "a" * 64
IDENTIFIER_PREFIX = "a" * 12
DELTA_TEXT = "+0.0000"
PASS_STREAK_TEXT = "2 passing"
FAIL_STREAK_TEXT = "2 failing"
INSUFFICIENT_TEXT = "insufficient"
CHECK_WARNING_TEXT = "Report/check diagnostics: 1"
TABLE_PIPE = "|"
LAST_CELL_INDEX = -2
TEXT_SPACE = " "
EMPTY_TEXT = ""
ASCII_ENCODING = "ascii"
ASCII_ERRORS = "backslashreplace"
LONG_TOKEN = "x" * (CHECK_NAME_WIDTH * THREE)


def _check(
    check_id: str | None,
    status: Any,
    description: str | None = None,
) -> dict[str, Any]:
    """Create one check entry as it appears inside a saved report."""
    entry: dict[str, Any] = {"status": status}
    if check_id is not None:
        entry["check_id"] = check_id
    if description is not None:
        entry["description"] = description
    return entry


def _payload(
    checks: Any,
    saved_at: str | None = SAVED_AT_FIRST,
) -> dict[str, Any]:
    """Create one history payload with the given checks value."""
    payload: dict[str, Any] = {
        "history_schema_version": 1,
        "history_scope": SCOPE,
        "report": {"checks": checks},
    }
    if saved_at is not None:
        payload["history_saved_at"] = saved_at
    return payload


def _build(
    reports_oldest_first: list[list[Any]],
    reports_available: int | None = None,
    file_diagnostics: list[tuple[Path, str]] | None = None,
) -> InsightsReport:
    """Build an insights report from chronologically ordered check lists."""
    payloads = [
        _payload(checks, saved_at=f"{SAVED_AT_PREFIX}{index + 1:02d}")
        for index, checks in enumerate(reports_oldest_first)
    ]
    payloads.reverse()
    available = (
        len(payloads) if reports_available is None else reports_available
    )
    return build_insights_report(
        payloads,
        reports_available=available,
        scope=SCOPE,
        file_diagnostics=file_diagnostics or [],
    )


def _summary_for(report: InsightsReport, identifier: str) -> CheckSummary:
    """Return the summary for one identifier from a report."""
    matches = [
        summary
        for summary in report.checks
        if summary.identifier == identifier
    ]
    assert len(matches) == ONE
    return matches[0]


def _summary(
    identifier: str,
    pass_rate: float,
    observations: int = TWO,
    pass_streak: int = ZERO,
    fail_streak: int = ZERO,
) -> CheckSummary:
    """Create a check summary for ranking tests."""
    return CheckSummary(
        identifier=identifier,
        name=identifier,
        observations=observations,
        passes=observations,
        pass_rate=pass_rate,
        latest_status=True,
        current_pass_streak=pass_streak,
        current_fail_streak=fail_streak,
        trend=TREND_INSUFFICIENT_DATA,
        trend_delta=None,
        status_history=[True] * observations,
    )


def _observation(passed: bool, name: str = NAME_A) -> CheckObservation:
    """Create one observation for aggregation helper tests."""
    return CheckObservation(
        identifier=CHECK_A,
        name=name,
        report_index=ZERO,
        source=SAVED_AT_FIRST,
        passed=passed,
        status_valid=True,
    )


def test_report_source_prefers_saved_at_then_index() -> None:
    """A report is labelled by its timestamp or by its position."""
    assert _report_source(_payload([]), ZERO) == SAVED_AT_FIRST
    assert (
        _report_source(_payload([], saved_at=None), TWO)
        == f"{REPORT_SOURCE_PREFIX}{THREE}"
    )
    payload = _payload([])
    payload["history_saved_at"] = 123
    assert _report_source(payload, ZERO) == f"{REPORT_SOURCE_PREFIX}{ONE}"


def test_check_identifier_uses_id_then_description_fallback() -> None:
    """Identity comes from check_id and falls back to the description."""
    assert _check_identifier(_check(CHECK_A, True, NAME_A)) == CHECK_A
    assert (
        _check_identifier(_check(None, True, NAME_A))
        == f"{FALLBACK_IDENTIFIER_PREFIX}{NAME_A}"
    )
    assert (
        _check_identifier({"check_id": "", "description": NAME_A})
        == f"{FALLBACK_IDENTIFIER_PREFIX}{NAME_A}"
    )
    assert _check_identifier({"check_id": 42, "status": True}) is None
    assert _check_identifier(_check(None, True)) is None


def test_check_name_prefers_description_then_check_then_identifier() -> None:
    """The display name uses the most readable field that is present."""
    assert _check_name(_check(CHECK_A, True, NAME_A), CHECK_A) == NAME_A
    assert _check_name({"check": NAME_C}, CHECK_C) == NAME_C
    assert _check_name({"description": ""}, CHECK_B) == CHECK_B


def test_check_name_appends_the_file_path_when_present() -> None:
    """Checks that target a file show the path so same names differ."""
    with_path = _check(CHECK_A, True, NAME_A)
    with_path["path"] = FILE_PATH
    assert _check_name(with_path, CHECK_A) == NAME_WITH_PATH.format(
        NAME_A, FILE_PATH
    )
    with_path["path"] = ""
    assert _check_name(with_path, CHECK_A) == NAME_A
    only_path = {"path": FILE_PATH}
    assert _check_name(only_path, CHECK_B) == NAME_WITH_PATH.format(
        CHECK_B, FILE_PATH
    )


def test_make_diagnostic_populates_every_field() -> None:
    """A diagnostic records its kind, source, reason, and detail."""
    diagnostic = _make_diagnostic(
        DIAGNOSTIC_KIND_CHECK, SAVED_AT_FIRST, FILE_REASON, NAME_A
    )
    assert diagnostic == HistoryDiagnostic(
        kind=DIAGNOSTIC_KIND_CHECK,
        source=SAVED_AT_FIRST,
        reason=FILE_REASON,
        detail=NAME_A,
    )


def test_file_diagnostics_keep_file_name_and_reason(tmp_path: Path) -> None:
    """Loader skip reasons become file diagnostics named by file."""
    diagnostics = _file_diagnostics([(tmp_path / FILE_NAME, FILE_REASON)])
    assert len(diagnostics) == ONE
    assert diagnostics[0].kind == DIAGNOSTIC_KIND_FILE
    assert diagnostics[0].source == FILE_NAME
    assert diagnostics[0].reason == FILE_REASON
    assert _file_diagnostics([]) == []


def test_merge_duplicate_requires_every_entry_to_pass() -> None:
    """A duplicated check passes only when all of its entries passed."""
    merged = _merge_duplicate(_observation(True), False, True)
    assert merged.passed is False
    assert merged.status_valid is True
    merged = _merge_duplicate(_observation(True), True, False)
    assert merged.passed is True
    assert merged.status_valid is False


def test_observe_report_reads_valid_entries() -> None:
    """Valid entries become observations in their original order."""
    payload = _payload(
        [_check(CHECK_B, True, NAME_B), _check(CHECK_A, False, NAME_A)]
    )
    observations, diagnostics = _observe_report(payload, ZERO)
    assert diagnostics == []
    assert [item.identifier for item in observations] == [CHECK_B, CHECK_A]
    assert [item.passed for item in observations] == [True, False]
    assert observations[0].name == NAME_B
    assert observations[0].source == SAVED_AT_FIRST
    assert observations[0].report_index == ZERO


def test_observe_report_flags_malformed_report() -> None:
    """A report without a list of checks yields one report diagnostic."""
    malformed_payloads: list[dict[str, Any]] = [
        {"history_saved_at": SAVED_AT_FIRST},
        {"report": {"checks": "nope"}},
        {"report": []},
    ]
    for payload in malformed_payloads:
        observations, diagnostics = _observe_report(payload, ZERO)
        assert observations == []
        assert len(diagnostics) == ONE
        assert diagnostics[0].kind == DIAGNOSTIC_KIND_REPORT
        assert diagnostics[0].reason == INSIGHTS_MALFORMED_REPORT


def test_observe_report_skips_bad_entries_with_diagnostics() -> None:
    """Non-object entries and unidentified checks are skipped."""
    payload = _payload([FIVE, _check(None, True), _check(CHECK_A, True)])
    observations, diagnostics = _observe_report(payload, ZERO)
    assert [item.identifier for item in observations] == [CHECK_A]
    assert [item.reason for item in diagnostics] == [
        INSIGHTS_SKIP_CHECK_ENTRY,
        INSIGHTS_MISSING_IDENTITY,
    ]
    assert all(item.kind == DIAGNOSTIC_KIND_CHECK for item in diagnostics)


def test_observe_report_treats_invalid_status_as_non_pass() -> None:
    """An unreadable status still counts as an observation that failed."""
    for status in (None, INVALID_STATUS, ONE):
        payload = _payload([_check(CHECK_A, status, NAME_A)])
        observations, diagnostics = _observe_report(payload, ZERO)
        assert len(observations) == ONE
        assert observations[0].passed is False
        assert observations[0].status_valid is False
        assert [item.reason for item in diagnostics] == [
            INSIGHTS_INVALID_STATUS
        ]
    payload = _payload([_check(CHECK_A, True, NAME_A)])
    observations, _ = _observe_report(payload, ZERO)
    assert observations[0].status_valid is True


def test_observe_report_merges_duplicates_within_one_report() -> None:
    """A check listed twice in one report is one conservative observation."""
    payload = _payload(
        [_check(CHECK_A, True, NAME_A), _check(CHECK_A, False, NAME_A)]
    )
    observations, diagnostics = _observe_report(payload, ZERO)
    assert len(observations) == ONE
    assert observations[0].passed is False
    assert [item.reason for item in diagnostics] == [INSIGHTS_DUPLICATE_CHECK]


def test_pass_rate_rounds_to_documented_precision() -> None:
    """Pass rates are rounded so output stays reproducible."""
    assert _pass_rate([True, True, False]) == TWO_THIRDS
    assert _pass_rate([True]) == FULL
    assert _pass_rate([False, False]) == NONE_RATE


def test_current_streaks_count_back_from_newest_observation() -> None:
    """Streaks measure the run of identical statuses ending at the newest."""
    assert _current_streaks([]) == (ZERO, ZERO)
    assert _current_streaks([True, True]) == (TWO, ZERO)
    assert _current_streaks([True, False, False]) == (ZERO, TWO)
    assert _current_streaks([False, True]) == (ONE, ZERO)


def test_compute_trend_needs_minimum_observations() -> None:
    """Fewer than the minimum observations gives insufficient data."""
    assert _compute_trend([True, False, True]) == (
        TREND_INSUFFICIENT_DATA,
        None,
    )


def test_compute_trend_classifies_improving_declining_and_stable() -> None:
    """The newer half is compared against the older half."""
    assert _compute_trend([False, False, True, True]) == (
        TREND_IMPROVING,
        IMPROVING_DELTA,
    )
    assert _compute_trend([True, True, False, False]) == (
        TREND_DECLINING,
        DECLINING_DELTA,
    )
    assert _compute_trend([True, False, True, False]) == (
        TREND_STABLE,
        ZERO_DELTA,
    )


def test_compute_trend_gives_newer_half_the_extra_observation() -> None:
    """With an odd count the newer half is the larger one."""
    trend, delta = _compute_trend([False, False, True, True, True])
    assert trend == TREND_IMPROVING
    assert delta == FULL


def test_compute_trend_treats_epsilon_boundary_as_stable() -> None:
    """A delta equal to the epsilon is stable, not improving."""
    older = [True] * STABLE_OLDER_PASSES + [False] * (
        STABLE_HALF_SIZE - STABLE_OLDER_PASSES
    )
    newer = [True] * STABLE_NEWER_PASSES + [False] * (
        STABLE_HALF_SIZE - STABLE_NEWER_PASSES
    )
    assert _compute_trend(older + newer) == (TREND_STABLE, STABLE_DELTA)


def test_display_name_prefers_newest_readable_name() -> None:
    """The newest observation with a real name wins, else the identifier."""
    observations = [
        _observation(True, name=NAME_B),
        _observation(True, name=NAME_A),
        _observation(True, name=CHECK_A),
    ]
    assert _display_name(CHECK_A, observations) == NAME_A
    assert _display_name(CHECK_A, [_observation(True, name=CHECK_A)]) == (
        CHECK_A
    )


def test_summarize_check_aggregates_chronological_observations() -> None:
    """A summary reports counts, latest status, streaks, and trend."""
    observations = [
        _observation(False, name=NAME_B),
        _observation(False),
        _observation(True),
        _observation(True, name=NAME_A),
    ]
    summary = _summarize_check(CHECK_A, observations)
    assert summary.identifier == CHECK_A
    assert summary.name == NAME_A
    assert summary.observations == FOUR
    assert summary.passes == TWO
    assert summary.pass_rate == HALF
    assert summary.latest_status is True
    assert summary.current_pass_streak == TWO
    assert summary.current_fail_streak == ZERO
    assert summary.trend == TREND_IMPROVING
    assert summary.trend_delta == IMPROVING_DELTA
    assert summary.status_history == [False, False, True, True]


def test_sort_keys_order_by_documented_tie_break_chain() -> None:
    """Sort keys encode pass rate, observations, streak, and identifier."""
    summary = _summary(
        CHECK_A, HALF, observations=THREE, pass_streak=ONE, fail_streak=ZERO
    )
    assert _best_sort_key(summary) == (-HALF, -THREE, NEGATIVE_ONE, CHECK_A)
    assert _worst_sort_key(summary) == (HALF, -THREE, ZERO, CHECK_A)


def test_rankable_checks_requires_minimum_observations() -> None:
    """Only checks with enough observations are ranked."""
    ranked = _summary(CHECK_A, FULL, observations=INSIGHTS_MIN_RANK_OBS)
    unranked = _summary(CHECK_B, FULL, observations=ONE)
    assert _rankable_checks([ranked, unranked]) == [ranked]
    assert _rankable_checks([]) == []


def test_select_best_and_worst_return_none_without_candidates() -> None:
    """No ranking is produced when nothing has enough observations."""
    checks = [_summary(CHECK_A, FULL, observations=ONE)]
    assert _select_best_check(checks) is None
    assert _select_worst_check(checks) is None


def test_select_best_check_breaks_ties_in_documented_order() -> None:
    """Best prefers pass rate, then observations, then streak, then id."""
    by_rate = [_summary(CHECK_B, HALF), _summary(CHECK_A, FULL)]
    assert _select_best_check(by_rate) == CHECK_A
    by_observations = [
        _summary(CHECK_A, FULL, observations=TWO),
        _summary(CHECK_B, FULL, observations=THREE),
    ]
    assert _select_best_check(by_observations) == CHECK_B
    by_streak = [
        _summary(CHECK_A, HALF, pass_streak=ONE),
        _summary(CHECK_B, HALF, pass_streak=TWO),
    ]
    assert _select_best_check(by_streak) == CHECK_B
    by_identifier = [_summary(CHECK_B, HALF), _summary(CHECK_A, HALF)]
    assert _select_best_check(by_identifier) == CHECK_A


def test_select_worst_check_breaks_ties_in_documented_order() -> None:
    """Worst prefers low pass rate, then observations, streak, then id."""
    by_rate = [_summary(CHECK_A, FULL), _summary(CHECK_B, HALF)]
    assert _select_worst_check(by_rate) == CHECK_B
    by_observations = [
        _summary(CHECK_A, HALF, observations=TWO),
        _summary(CHECK_B, HALF, observations=THREE),
    ]
    assert _select_worst_check(by_observations) == CHECK_B
    by_streak = [
        _summary(CHECK_A, HALF, fail_streak=ONE),
        _summary(CHECK_B, HALF, fail_streak=TWO),
    ]
    assert _select_worst_check(by_streak) == CHECK_B
    by_identifier = [_summary(CHECK_B, HALF), _summary(CHECK_A, HALF)]
    assert _select_worst_check(by_identifier) == CHECK_A


def test_build_insights_report_handles_empty_history(tmp_path: Path) -> None:
    """No payloads gives an empty report that still carries diagnostics."""
    report = build_insights_report(
        [],
        reports_available=ZERO,
        scope=SCOPE,
        file_diagnostics=[(tmp_path / FILE_NAME, FILE_REASON)],
    )
    assert report.scope == SCOPE
    assert report.reports_inspected == ZERO
    assert report.reports_available == ZERO
    assert report.checks == []
    assert report.best_check is None
    assert report.worst_check is None
    assert [item.reason for item in report.diagnostics] == [FILE_REASON]


def test_build_insights_report_handles_single_report() -> None:
    """One report gives one observation per check and no ranking."""
    report = _build(
        [[_check(CHECK_A, True, NAME_A), _check(CHECK_B, False, NAME_B)]]
    )
    assert report.reports_inspected == ONE
    assert [summary.observations for summary in report.checks] == [ONE, ONE]
    assert _summary_for(report, CHECK_A).latest_status is True
    assert _summary_for(report, CHECK_B).latest_status is False
    assert report.best_check is None
    assert report.worst_check is None
    assert report.diagnostics == []


def test_build_insights_report_aggregates_and_ranks_checks() -> None:
    """Repeated check ids aggregate into one ranked summary each."""
    report = _build(
        [
            [_check(CHECK_A, False, NAME_A), _check(CHECK_B, True, NAME_B)],
            [_check(CHECK_A, False, NAME_A), _check(CHECK_B, True, NAME_B)],
            [_check(CHECK_A, True, NAME_A), _check(CHECK_B, True, NAME_B)],
        ],
        reports_available=SEVEN,
    )
    assert report.reports_inspected == THREE
    assert report.reports_available == SEVEN
    assert len(report.checks) == TWO
    summary_a = _summary_for(report, CHECK_A)
    assert summary_a.observations == THREE
    assert summary_a.passes == ONE
    assert summary_a.pass_rate == ONE_THIRD
    assert summary_a.latest_status is True
    assert summary_a.current_pass_streak == ONE
    assert summary_a.trend == TREND_INSUFFICIENT_DATA
    assert report.best_check == CHECK_B
    assert report.worst_check == CHECK_A


def test_build_insights_report_consumes_payloads_newest_first() -> None:
    """The first payload is the newest and decides the latest status."""
    newest = _payload([_check(CHECK_A, True, NAME_A)], saved_at="newest")
    oldest = _payload([_check(CHECK_A, False, NAME_A)], saved_at="oldest")
    report = build_insights_report(
        [newest, oldest],
        reports_available=TWO,
        scope=SCOPE,
        file_diagnostics=[],
    )
    summary = _summary_for(report, CHECK_A)
    assert summary.status_history == [False, True]
    assert summary.latest_status is True


def test_build_insights_report_never_counts_absent_checks() -> None:
    """A check missing from a report is not an observation or a pass."""
    report = _build(
        [
            [_check(CHECK_A, True, NAME_A), _check(CHECK_B, False, NAME_B)],
            [_check(CHECK_B, False, NAME_B)],
            [_check(CHECK_A, True, NAME_A), _check(CHECK_B, True, NAME_B)],
            [_check(CHECK_B, True, NAME_B)],
        ]
    )
    assert report.reports_inspected == FOUR
    summary_a = _summary_for(report, CHECK_A)
    assert summary_a.observations == TWO
    assert summary_a.passes == TWO
    assert summary_a.pass_rate == FULL
    assert summary_a.current_pass_streak == TWO
    assert summary_a.status_history == [True, True]
    summary_b = _summary_for(report, CHECK_B)
    assert summary_b.observations == FOUR
    assert summary_b.trend == TREND_IMPROVING


def test_build_insights_report_orders_checks_by_identifier() -> None:
    """The per-check list is sorted by identifier regardless of input."""
    report = _build(
        [
            [
                _check(CHECK_C, True, NAME_C),
                _check(CHECK_A, True, NAME_A),
                _check(CHECK_B, True, NAME_B),
            ]
        ]
    )
    assert [summary.identifier for summary in report.checks] == [
        CHECK_A,
        CHECK_B,
        CHECK_C,
    ]


def test_build_insights_report_uses_description_fallback_identity() -> None:
    """Checks without a check_id aggregate by their description."""
    report = _build(
        [
            [_check(None, False, NAME_A)],
            [_check(None, True, NAME_A)],
        ]
    )
    fallback = f"{FALLBACK_IDENTIFIER_PREFIX}{NAME_A}"
    summary = _summary_for(report, fallback)
    assert summary.name == NAME_A
    assert summary.observations == TWO
    assert summary.passes == ONE


def test_build_insights_report_collects_diagnostics_in_order() -> None:
    """File diagnostics come first, then report diagnostics, oldest first."""
    report = _build(
        [
            [_check(CHECK_A, INVALID_STATUS, NAME_A)],
            [SIX, _check(CHECK_A, True, NAME_A)],
        ],
        file_diagnostics=[(Path(FILE_NAME), FILE_REASON)],
    )
    assert [item.reason for item in report.diagnostics] == [
        FILE_REASON,
        INSIGHTS_INVALID_STATUS,
        INSIGHTS_SKIP_CHECK_ENTRY,
    ]
    summary = _summary_for(report, CHECK_A)
    assert summary.observations == TWO
    assert summary.passes == ONE


def test_status_label_maps_booleans_to_words() -> None:
    """Statuses render as pass or fail."""
    assert _status_label(True) != _status_label(False)


def test_render_check_describes_pass_and_fail_streaks() -> None:
    """Each check renders its counts, streak, and trend lines."""
    passing = _summary(CHECK_A, FULL, observations=TWO, pass_streak=TWO)
    failing = _summary(CHECK_B, NONE_RATE, observations=TWO, fail_streak=TWO)
    passing_lines = _render_check(passing)
    failing_lines = _render_check(failing)
    assert CHECK_A in passing_lines
    assert passing_lines != failing_lines
    assert PASS_STREAK_TEXT in passing_lines
    assert FAIL_STREAK_TEXT in failing_lines
    assert INSUFFICIENT_TEXT in passing_lines
    with_delta = passing.model_copy(
        update={"trend": TREND_STABLE, "trend_delta": ZERO_DELTA}
    )
    assert TREND_STABLE in _render_check(with_delta)
    assert DELTA_TEXT in _render_check(with_delta, instructor=True)
    assert DELTA_TEXT not in _render_check(with_delta)


def test_render_diagnostics_keeps_other_scopes_quiet() -> None:
    """Different-scope skips are counted rather than listed."""
    report = build_insights_report(
        [],
        reports_available=ZERO,
        scope=SCOPE,
        file_diagnostics=[
            (Path(FILE_NAME), HISTORY_SKIP_DIFFERENT_SCOPE),
            (Path(FILE_NAME), FILE_REASON),
        ],
    )
    lines = _render_diagnostics(report)
    assert lines == [TEXT_SKIPPED.format(TWO, ONE, ONE)]
    detailed = _render_diagnostics(report, instructor=True)
    assert len(detailed) == THREE
    assert FILE_REASON in detailed[TWO]
    assert HISTORY_SKIP_DIFFERENT_SCOPE in detailed[ONE]
    assert _render_diagnostics(_build([])) == []


def test_render_text_reports_empty_history() -> None:
    """An empty history renders a clear message and no check section."""
    text = render_text(_build([]))
    assert text.startswith(NEWLINE + TEXT_TITLE + NEWLINE)
    assert SCOPE not in text
    assert TEXT_NO_REPORTS in text
    assert TEXT_NO_CHECKS not in text


def test_render_diagnostics_counts_check_warnings_without_skipped_files() -> (
    None
):
    """Check warnings are not mislabeled as skipped history files."""
    report = _build([[_check(CHECK_A, INVALID_STATUS, NAME_A)]])
    assert _render_diagnostics(report) == [CHECK_WARNING_TEXT]


def test_render_text_reports_history_without_checks() -> None:
    """Reports that contain no usable checks say so."""
    text = render_text(_build([[]]))
    assert TEXT_NO_CHECKS in text
    assert TEXT_NO_REPORTS not in text


def test_render_text_accepts_the_instructor_parameter() -> None:
    """The instructor parameter is accepted by the rendering contract."""
    report = _build([[_check(CHECK_A, True, NAME_A)]])
    assert render_text(report, instructor=True).startswith(
        NEWLINE + TEXT_TITLE + NEWLINE
    )


def test_render_text_lists_checks_ranking_and_diagnostics() -> None:
    """A full report renders every section in a fixed layout."""
    report = _build(
        [
            [_check(CHECK_A, False, NAME_A), _check(CHECK_B, True, NAME_B)],
            [_check(CHECK_A, True, NAME_A), _check(CHECK_B, INVALID_STATUS)],
        ],
        file_diagnostics=[(Path(FILE_NAME), HISTORY_SKIP_DIFFERENT_SCOPE)],
    )
    text = render_text(report)
    assert text.endswith("\n")
    assert NAME_A in text
    assert NAME_B in text
    assert CHECK_A not in text
    assert text.index(NAME_B) < text.index(NAME_A)
    assert TEXT_SKIPPED.format(ONE, ONE, ZERO) in text
    assert INSIGHTS_INVALID_STATUS not in text
    assert INSIGHTS_INVALID_STATUS in render_text(report, instructor=True)
    assert FILE_NAME not in text


def test_render_text_shows_no_focus_for_healthy_checks() -> None:
    """Healthy checks get an explicit message instead of an empty section."""
    text = render_text(_build([[_check(CHECK_A, True, NAME_A)]]))
    assert TEXT_NO_FOCUS in text


def test_render_json_round_trips_through_the_model() -> None:
    """JSON output is valid and reconstructs the same report."""
    report = _build(
        [
            [_check(CHECK_A, False, NAME_A)],
            [_check(CHECK_A, True, NAME_A)],
        ]
    )
    rendered = render_json(report)
    decoded = json.loads(rendered)
    assert decoded["scope"] == SCOPE
    assert decoded["checks"][0]["trend_delta"] is None
    assert InsightsReport.model_validate_json(rendered) == report


def test_sort_checks_by_struggle_preserves_input_and_breaks_ties() -> None:
    """Display sorting applies every tie breaker, including single runs."""
    checks = [
        _summary(CHECK_C, FULL),
        _summary(CHECK_C, HALF, observations=ONE),
        _summary(CHECK_C, HALF, observations=THREE),
        _summary(CHECK_B, HALF, observations=THREE, fail_streak=TWO),
        _summary(CHECK_A, HALF, observations=THREE, fail_streak=TWO),
    ]
    original = list(checks)
    assert sort_checks_by_struggle(checks) == list(reversed(checks))
    assert checks == original
    assert sort_checks_by_struggle([]) == []


def test_struggling_checks_excludes_exact_threshold() -> None:
    """Only rates strictly under 85 percent need focus."""
    below = _summary(CHECK_A, BELOW_THRESHOLD)
    boundary = _summary(CHECK_B, THRESHOLD)
    assert struggling_checks([boundary, below]) == [below]
    assert struggling_checks([]) == []


def test_render_text_instructor_details_and_json_are_independent() -> None:
    """Instructor details do not leak into student text or mutate JSON."""
    report = _build([[_check(LONG_IDENTIFIER, True, NAME_A)]])
    report.checks[ZERO].trend_delta = ZERO_DELTA
    before = render_json(report)
    student = render_text(report)
    instructor = render_text(report, instructor=True)
    for detail in (SCOPE, IDENTIFIER_PREFIX, DELTA_TEXT):
        assert detail not in student
        assert detail in instructor
    assert LONG_IDENTIFIER not in instructor
    assert render_json(report) == before


def test_render_check_aligns_long_names_and_double_digit_counts() -> None:
    """Names remain complete after aligned numeric columns."""
    short = _summary(CHECK_A, FULL, pass_streak=ONE)
    long = _summary(
        LONG_NAME,
        FULL,
        observations=STABLE_HALF_SIZE,
        pass_streak=STABLE_HALF_SIZE,
    )
    for instructor in (False, True):
        short_row = _render_check(short, instructor=instructor)
        long_row = _render_check(long, instructor=instructor)
        rows = long_row.splitlines()
        assert all(len(row) == len(short_row) for row in rows)
        name_parts = [
            row.split(TABLE_PIPE)[LAST_CELL_INDEX].strip() for row in rows
        ]
        assert TEXT_SPACE.join(name_parts) == LONG_NAME.strip()


def test_render_text_escapes_non_ascii_names() -> None:
    """Both text views remain safe for redirected Windows streams."""
    report = _build([[_check(CHECK_A, False, UNICODE_NAME)]])
    for instructor in (False, True):
        assert render_text(report, instructor=instructor).isascii()


@pytest.mark.parametrize("name", [EMPTY_TEXT, UNICODE_NAME, LONG_TOKEN])
def test_render_row_wraps_empty_unicode_and_unbroken_names(name: str) -> None:
    """All cells stay ASCII and names survive wrapping without truncation."""
    text = _render_row([], name)
    rows = text.splitlines()
    assert text.isascii()
    assert len({len(row) for row in rows}) == ONE
    recovered = EMPTY_TEXT.join(
        row.split(TABLE_PIPE)[LAST_CELL_INDEX].strip() for row in rows
    )
    assert recovered == name.encode(
        ASCII_ENCODING, errors=ASCII_ERRORS
    ).decode(ASCII_ENCODING)


def test_render_table_aligns_borders_with_wrapped_rows() -> None:
    """Header, borders, and wrapped data have the same width."""
    columns = (CHECK_A,)
    row = _render_row(list(columns), LONG_NAME)
    table = _render_table(columns, [row])
    physical_lines = NEWLINE.join(table).splitlines()
    assert len({len(line) for line in physical_lines}) == ONE
    assert table[ZERO] == table[TWO] == table[NEGATIVE_ONE]
    assert len(_render_table(columns, [])) == THREE


def test_render_focus_wraps_names_with_aligned_recent_details() -> None:
    """Focus rows keep a double-digit failing streak beside wrapped names."""
    summary = _summary(
        LONG_NAME,
        NONE_RATE,
        fail_streak=STABLE_HALF_SIZE,
    )
    rows = _render_focus(summary).splitlines()
    assert len({len(row) for row in rows}) == ONE
    assert (
        TEXT_SPACE.join(
            row.split(TABLE_PIPE)[LAST_CELL_INDEX].strip() for row in rows
        )
        == LONG_NAME.strip()
    )


def test_render_text_focus_describes_improvement() -> None:
    """An improving check has an actionable trend in the focus section."""
    report = _build(
        [
            [_check(CHECK_A, False, NAME_A)],
            [_check(CHECK_A, False, NAME_A)],
            [_check(CHECK_A, True, NAME_A)],
            [_check(CHECK_A, True, NAME_A)],
        ]
    )
    focus_row = next(
        line for line in render_text(report).splitlines() if NAME_A in line
    )
    assert TREND_IMPROVING in focus_row
    assert focus_row.split(TABLE_PIPE)[LAST_CELL_INDEX].strip() == NAME_A


def test_render_outputs_are_byte_identical_for_equal_inputs() -> None:
    """The same history always produces the same text and JSON."""
    history = [
        [_check(CHECK_A, False, NAME_A), _check(CHECK_B, True, NAME_B)],
        [_check(CHECK_A, True, NAME_A), _check(CHECK_B, False, NAME_B)],
        [_check(CHECK_A, True, NAME_A)],
    ]
    first = _build(history)
    second = _build(history)
    assert render_text(first) == render_text(second)
    assert render_json(first) == render_json(second)


@pytest.mark.propertybased
@given(st.lists(st.booleans(), min_size=1))
def test_streaks_and_rates_stay_consistent_property(
    statuses: list[bool],
) -> None:
    """Property: exactly one streak is active and it fits the history."""
    pass_streak, fail_streak = _current_streaks(statuses)
    assert (pass_streak == ZERO) != (fail_streak == ZERO)
    assert ZERO < pass_streak + fail_streak <= len(statuses)
    assert NONE_RATE <= _pass_rate(statuses) <= FULL
