"""Tests for bounded JSON report history and historical filtering."""

import datetime
import json
from pathlib import Path
from typing import Any

import pytest

from gatorgrade.input.checks import ShellCheck
from gatorgrade.report_history import (
    BYTES_PER_MIB,
    CHECK_ID_KEY,
    CHECKS_KEY,
    HISTORY_FILE_PREFIX,
    HISTORY_FILE_SUFFIX,
    _history_filename,
    _history_files,
    _load_history_file,
    _make_history_directory,
    _make_history_payload,
    _normalise_timestamp,
    _validate_positive_limit,
    _write_json_atomically,
    filter_checks_by_failed_ids,
    get_all_check_ids,
    get_failed_check_ids,
    get_history_scope,
    load_history_reports,
    prune_report_history,
    save_report_history,
)

UTC = datetime.timezone.utc
EXPECTED_RETAINED_REPORTS = 2
EXPECTED_INSPECTED_REPORTS = 2


def _report(
    check_id: str,
    status: bool,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Create a minimal report for history tests."""
    report: dict[str, Any] = {
        "checks": [{"check_id": check_id, "status": status}],
    }
    if api_key is not None:
        report["cli_args"] = {"--auto-hint-api-key": api_key}
    return report


def test_history_internal_helpers_handle_files_and_timestamps(
    tmp_path: Path,
) -> None:
    """History helpers normalize timestamps and manage owned files."""
    naive_timestamp = datetime.datetime(2026, 1, 1)
    normalized_timestamp = _normalise_timestamp(naive_timestamp)
    assert normalized_timestamp.tzinfo == UTC
    filename = _history_filename(normalized_timestamp)
    assert filename.startswith(HISTORY_FILE_PREFIX)
    assert filename.endswith(HISTORY_FILE_SUFFIX)
    _make_history_directory(tmp_path)
    destination = tmp_path / "helper.json"
    payload = _make_history_payload(
        _report("helper", False, api_key="secret"),
        "project-one",
        normalized_timestamp,
    )
    _write_json_atomically(destination, payload)
    assert _history_files(tmp_path) == []
    owned_path = tmp_path / filename
    _write_json_atomically(owned_path, payload)
    assert _history_files(tmp_path) == [owned_path]
    assert _load_history_file(owned_path, "project-one") == payload
    assert _load_history_file(owned_path, "other-project") is None
    _validate_positive_limit(1, "test limit")


def test_prune_report_history_can_be_called_directly(tmp_path: Path) -> None:
    """Direct pruning removes the oldest owned file when needed."""
    save_report_history(
        _report("old", False),
        scope="project-one",
        history_directory=tmp_path,
        current_time=datetime.datetime(2026, 1, 1, tzinfo=UTC),
    )
    save_report_history(
        _report("new", False),
        scope="project-one",
        history_directory=tmp_path,
        current_time=datetime.datetime(2026, 1, 2, tzinfo=UTC),
        max_report_count=2,
    )
    deleted = prune_report_history(
        tmp_path,
        max_report_count=1,
        max_size_mib=1,
    )
    assert len(deleted) == 1


def test_save_and_load_history_redacts_api_key(tmp_path: Path) -> None:
    """History saves a report and redacts sensitive CLI arguments."""
    path = save_report_history(
        _report("check-one", False, api_key="secret-key"),
        scope="project-one",
        history_directory=tmp_path,
        current_time=datetime.datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert path.exists()
    reports = load_history_reports(tmp_path, "project-one")
    assert len(reports) == 1
    saved_report = reports[0]["report"]
    assert saved_report["cli_args"]["--auto-hint-api-key"] == "[redacted]"
    assert "secret-key" not in path.read_text(encoding="utf-8")


def test_history_retains_newest_reports_by_count(tmp_path: Path) -> None:
    """History pruning removes the oldest reports beyond the count limit."""
    for day in range(3):
        save_report_history(
            _report(f"check-{day}", False),
            scope="project-one",
            history_directory=tmp_path,
            max_report_count=2,
            current_time=datetime.datetime(2026, 1, day + 1, tzinfo=UTC),
        )
    files = sorted(
        tmp_path.glob(f"{HISTORY_FILE_PREFIX}*{HISTORY_FILE_SUFFIX}")
    )
    assert len(files) == EXPECTED_RETAINED_REPORTS
    reports = load_history_reports(tmp_path, "project-one")
    assert [
        report["report"]["checks"][0]["check_id"] for report in reports
    ] == ["check-2", "check-1"]


def test_history_pruning_removes_older_oversized_report(
    tmp_path: Path,
) -> None:
    """History keeps the newest report when an older report exceeds the size limit."""
    large_report = _report("large", False)
    large_report["diagnostic"] = "x" * (BYTES_PER_MIB + 100)
    save_report_history(
        large_report,
        scope="project-one",
        history_directory=tmp_path,
        max_size_mib=1,
        current_time=datetime.datetime(2026, 1, 1, tzinfo=UTC),
    )
    save_report_history(
        _report("small", True),
        scope="project-one",
        history_directory=tmp_path,
        max_size_mib=1,
        current_time=datetime.datetime(2026, 1, 2, tzinfo=UTC),
    )
    reports = load_history_reports(tmp_path, "project-one")
    assert len(reports) == 1
    assert reports[0]["report"]["checks"][0]["check_id"] == "small"


def test_failed_ids_use_union_of_newest_reports_and_scope(
    tmp_path: Path,
) -> None:
    """Historical failures use the newest reports from the requested scope."""
    for day, check_id, status, scope in [
        (1, "old", False, "project-one"),
        (2, "first", False, "project-one"),
        (3, "second", False, "project-one"),
        (4, "other-project", False, "project-two"),
    ]:
        save_report_history(
            _report(check_id, status),
            scope=scope,
            history_directory=tmp_path,
            current_time=datetime.datetime(2026, 1, day, tzinfo=UTC),
        )
    failed_ids, reports_inspected, _reports_total = get_failed_check_ids(
        tmp_path,
        "project-one",
        report_count=2,
    )
    assert failed_ids == {"first", "second"}
    assert reports_inspected == EXPECTED_INSPECTED_REPORTS


def test_history_skips_malformed_files(tmp_path: Path) -> None:
    """Malformed history files do not prevent valid reports from loading."""
    malformed = tmp_path / f"{HISTORY_FILE_PREFIX}000{HISTORY_FILE_SUFFIX}"
    malformed.write_text("not json", encoding="utf-8")
    wrong_shape = tmp_path / f"{HISTORY_FILE_PREFIX}001{HISTORY_FILE_SUFFIX}"
    wrong_shape.write_text(
        json.dumps(
            {
                "history_schema_version": 1,
                "history_scope": "project-one",
                "report": {},
            }
        ),
        encoding="utf-8",
    )
    save_report_history(
        _report("valid", False),
        scope="project-one",
        history_directory=tmp_path,
        current_time=datetime.datetime(2026, 1, 2, tzinfo=UTC),
    )
    reports = load_history_reports(tmp_path, "project-one")
    assert len(reports) == 1
    assert reports[0]["report"]["checks"][0]["check_id"] == "valid"


def test_history_scope_is_stable_for_same_inputs(tmp_path: Path) -> None:
    """The same configuration and project produce the same scope."""
    config_path = tmp_path / "gatorgrade.yml"
    first_scope = get_history_scope(config_path, "project-one")
    second_scope = get_history_scope(config_path, "project-one")
    different_scope = get_history_scope(config_path, "project-two")
    assert first_scope == second_scope
    assert first_scope != different_scope


def test_filter_checks_by_failed_ids() -> None:
    """Historical IDs select only matching current checks."""
    checks = [
        ShellCheck(command="echo one", check_id="one"),
        ShellCheck(command="echo two", check_id="two"),
    ]
    selected = filter_checks_by_failed_ids(checks, {"two"})
    assert selected == [checks[1]]


def test_save_history_rejects_non_positive_limits(tmp_path: Path) -> None:
    """History rejects invalid retention limits."""
    with pytest.raises(ValueError, match="positive integer"):
        save_report_history(
            _report("check-one", False),
            scope="project-one",
            history_directory=tmp_path,
            max_report_count=0,
        )
    with pytest.raises(ValueError, match="positive integer"):
        save_report_history(
            _report("check-one", False),
            scope="project-one",
            history_directory=tmp_path,
            max_size_mib=0,
        )


def test_history_file_is_json(tmp_path: Path) -> None:
    """Saved history files contain valid JSON."""
    path = save_report_history(
        _report("check-one", True),
        scope="project-one",
        history_directory=tmp_path,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["history_scope"] == "project-one"


def test_get_all_check_ids_returns_distinct_ids(tmp_path: Path) -> None:
    """get_all_check_ids returns distinct check IDs from reports."""
    scope = get_history_scope(tmp_path / "config.yml")
    for day, check_id in [(1, "alpha"), (2, "beta"), (3, "alpha")]:
        report = {
            CHECKS_KEY: [
                {CHECK_ID_KEY: check_id, "status": True, "description": "test"}
            ]
        }
        save_report_history(
            report,
            scope=scope,
            history_directory=tmp_path,
            current_time=datetime.datetime(2026, 1, day, tzinfo=UTC),
        )
    result = get_all_check_ids(tmp_path, scope, report_count=5)
    assert result == {"alpha", "beta"}


def test_get_all_check_ids_empty_directory(tmp_path: Path) -> None:
    """get_all_check_ids returns empty set for empty directory."""
    result = get_all_check_ids(tmp_path, "any-scope", report_count=5)
    assert result == set()


def test_write_json_atomically_chmod_failure_is_harmless(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chmod failure in _write_json_atomically is silently ignored."""

    def _broken_chmod(*args: Any, **kwargs: Any) -> None:  # type: ignore[misc]
        raise OSError("chmod not allowed")

    monkeypatch.setattr(Path, "chmod", _broken_chmod)
    destination = tmp_path / "report.json"
    _write_json_atomically(destination, {"key": "value"})
    assert destination.exists()


def test_load_history_file_returns_none_on_os_error(tmp_path: Path) -> None:
    """_load_history_file returns None when file cannot be read."""
    path = tmp_path / "nonexistent.json"
    result = _load_history_file(path, "scope")
    assert result is None


def test_load_history_file_returns_none_on_bad_json(tmp_path: Path) -> None:
    """_load_history_file returns None for invalid JSON content."""
    path = tmp_path / "bad.json"
    path.write_text("not valid json{", encoding="utf-8")
    result = _load_history_file(path, "scope")
    assert result is None


def test_load_history_file_returns_none_on_wrong_schema(
    tmp_path: Path,
) -> None:
    """_load_history_file returns None for wrong schema version."""
    path = tmp_path / "bad_schema.json"
    path.write_text(
        json.dumps({"history_schema_version": 999, "history_scope": "s"}),
        encoding="utf-8",
    )
    result = _load_history_file(path, "s")
    assert result is None


def test_load_history_file_returns_none_for_wrong_scope(
    tmp_path: Path,
) -> None:
    """_load_history_file returns None when scope does not match."""
    path = tmp_path / "wrong_scope.json"
    path.write_text(
        json.dumps(
            {
                "history_schema_version": 1,
                "history_scope": "project-a",
                "report": {"checks": []},
            }
        ),
        encoding="utf-8",
    )
    result = _load_history_file(path, "project-b")
    assert result is None


def test_load_history_file_returns_none_for_non_dict_payload(
    tmp_path: Path,
) -> None:
    """_load_history_file returns None for non-dict payload."""
    path = tmp_path / "bad_payload.json"
    path.write_text(
        json.dumps(
            {
                "history_schema_version": 1,
                "history_scope": "s",
                "report": "not a dict",
            }
        ),
        encoding="utf-8",
    )
    result = _load_history_file(path, "s")
    assert result is None


def test_load_history_file_returns_none_for_non_list_checks(
    tmp_path: Path,
) -> None:
    """_load_history_file returns None when checks is not a list."""
    path = tmp_path / "bad_checks.json"
    path.write_text(
        json.dumps(
            {
                "history_schema_version": 1,
                "history_scope": "s",
                "report": {"checks": "not a list"},
            }
        ),
        encoding="utf-8",
    )
    result = _load_history_file(path, "s")
    assert result is None
