"""Persist bounded JSON report history for filtering and analysis."""

import copy
import datetime
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Sequence

import platformdirs

HISTORY_APPLICATION_NAME = "gatorgrade"
HISTORY_DIRECTORY_NAME = "reports"
HISTORY_FILE_PREFIX = "gatorgrade-report-"
HISTORY_FILE_SUFFIX = ".json"
HISTORY_SCHEMA_VERSION = 1
HISTORY_SCHEMA_KEY = "history_schema_version"
HISTORY_SAVED_AT_KEY = "history_saved_at"
HISTORY_SCOPE_KEY = "history_scope"
HISTORY_REPORT_KEY = "report"
CHECKS_KEY = "checks"
CHECK_ID_KEY = "check_id"
STATUS_KEY = "status"
CLI_ARGS_KEY = "cli_args"
SENSITIVE_CLI_ARGUMENTS = frozenset({"--auto-hint-api-key"})
REDACTED_VALUE = "[redacted]"
DEFAULT_HISTORY_QUERY_COUNT = 5
DEFAULT_HISTORY_REPORT_COUNT = 100
DEFAULT_HISTORY_SIZE_MIB = 100
BYTES_PER_MIB = 1024 * 1024
HISTORY_FILENAME_TIME_FORMAT = "%Y%m%dT%H%M%S.%fZ"
UTC = datetime.timezone.utc
PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
SCOPE_SEPARATOR = "\n"
SCOPE_EMPTY_NAME = ""
HISTORY_FILE_MODE_WRITE = "w"
HISTORY_FILE_ENCODING = "utf-8"
HISTORY_JSON_INDENT = 4
HISTORY_TEMPORARY_SUFFIX = ".tmp"


def get_report_history_directory() -> Path:
    """Return the platform-specific directory for report history."""
    data_directory = platformdirs.user_data_dir(
        HISTORY_APPLICATION_NAME,
        appauthor=False,
    )
    return Path(data_directory) / HISTORY_DIRECTORY_NAME


def get_history_scope(
    config_path: Path,
    project_name: str | None = None,
) -> str:
    """Return a stable scope identifier for a configuration and project."""
    resolved_path = config_path.expanduser().resolve(strict=False)
    scope_source = (
        f"{resolved_path}{SCOPE_SEPARATOR}{project_name or SCOPE_EMPTY_NAME}"
    )
    return hashlib.sha256(scope_source.encode("utf-8")).hexdigest()


def _normalise_timestamp(
    current_time: datetime.datetime | None,
) -> datetime.datetime:
    """Return a timezone-aware UTC timestamp."""
    timestamp = current_time or datetime.datetime.now(UTC)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _history_filename(current_time: datetime.datetime) -> str:
    """Return a unique, chronologically sortable history filename."""
    timestamp = current_time.strftime(HISTORY_FILENAME_TIME_FORMAT)
    return f"{HISTORY_FILE_PREFIX}{timestamp}-{uuid.uuid4().hex}{HISTORY_FILE_SUFFIX}"


def _make_history_payload(
    report: dict[str, Any],
    scope: str,
    current_time: datetime.datetime,
) -> dict[str, Any]:
    """Return a versioned and privacy-filtered history payload."""
    history_report = copy.deepcopy(report)
    cli_args = history_report.get(CLI_ARGS_KEY)
    if isinstance(cli_args, dict):
        for argument in SENSITIVE_CLI_ARGUMENTS:
            if cli_args.get(argument) is not None:
                cli_args[argument] = REDACTED_VALUE
    return {
        HISTORY_SCHEMA_KEY: HISTORY_SCHEMA_VERSION,
        HISTORY_SAVED_AT_KEY: current_time.isoformat(),
        HISTORY_SCOPE_KEY: scope,
        HISTORY_REPORT_KEY: history_report,
    }


def _make_history_directory(history_directory: Path) -> None:
    """Create the history directory with private permissions where possible."""
    history_directory.mkdir(
        parents=True,
        exist_ok=True,
        mode=PRIVATE_DIRECTORY_MODE,
    )
    try:
        history_directory.chmod(PRIVATE_DIRECTORY_MODE)
    except OSError:
        pass


def _write_json_atomically(
    destination: Path,
    payload: dict[str, Any],
) -> None:
    """Write a JSON payload through a temporary file and atomic replacement."""
    temporary_path = destination.with_name(
        f".{destination.name}.{uuid.uuid4().hex}{HISTORY_TEMPORARY_SUFFIX}"
    )
    try:
        with temporary_path.open(
            HISTORY_FILE_MODE_WRITE, encoding=HISTORY_FILE_ENCODING
        ) as file:
            json.dump(payload, file, indent=HISTORY_JSON_INDENT)
            file.write(SCOPE_SEPARATOR)
            file.flush()
            os.fsync(file.fileno())
        try:
            temporary_path.chmod(PRIVATE_FILE_MODE)
        except OSError:
            pass
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def _history_files(history_directory: Path) -> list[Path]:
    """Return owned history files in chronological order."""
    if not history_directory.exists():
        return []
    return sorted(
        path
        for path in history_directory.iterdir()
        if path.is_file()
        and path.name.startswith(HISTORY_FILE_PREFIX)
        and path.name.endswith(HISTORY_FILE_SUFFIX)
    )


def _validate_positive_limit(value: int, label: str) -> None:
    """Raise ValueError when a retention limit is not a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer, got {value}")


def prune_report_history(
    history_directory: Path,
    max_report_count: int = DEFAULT_HISTORY_REPORT_COUNT,
    max_size_mib: int = DEFAULT_HISTORY_SIZE_MIB,
) -> list[Path]:
    """Delete oldest history files until both retention limits are met."""
    _validate_positive_limit(max_report_count, "Maximum report count")
    _validate_positive_limit(max_size_mib, "Maximum report size")
    history_files = _history_files(history_directory)
    file_sizes = [path.stat().st_size for path in history_files]
    total_size = sum(file_sizes)
    maximum_size = max_size_mib * BYTES_PER_MIB
    deleted_files: list[Path] = []
    while (
        len(history_files) > max_report_count or total_size > maximum_size
    ) and len(history_files) > 1:
        oldest_file = history_files.pop(0)
        oldest_size = file_sizes.pop(0)
        oldest_file.unlink()
        deleted_files.append(oldest_file)
        total_size -= oldest_size
    return deleted_files


def save_report_history(  # noqa: PLR0913
    report: dict[str, Any],
    scope: str,
    history_directory: Path | None = None,
    max_report_count: int = DEFAULT_HISTORY_REPORT_COUNT,
    max_size_mib: int = DEFAULT_HISTORY_SIZE_MIB,
    current_time: datetime.datetime | None = None,
) -> Path:
    """Save one report and prune older reports according to both limits."""
    _validate_positive_limit(max_report_count, "Maximum report count")
    _validate_positive_limit(max_size_mib, "Maximum report size")
    destination_directory = (
        history_directory
        if history_directory is not None
        else get_report_history_directory()
    )
    _make_history_directory(destination_directory)
    timestamp = _normalise_timestamp(current_time)
    destination = destination_directory / _history_filename(timestamp)
    payload = _make_history_payload(report, scope, timestamp)
    _write_json_atomically(destination, payload)
    prune_report_history(
        destination_directory,
        max_report_count=max_report_count,
        max_size_mib=max_size_mib,
    )
    return destination


def _load_history_file(  # noqa: PLR0911
    path: Path, scope: str
) -> dict[str, Any] | None:
    """Load one valid in-scope history file, or return None."""
    try:
        payload = json.loads(path.read_text(encoding=HISTORY_FILE_ENCODING))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get(HISTORY_SCHEMA_KEY) != HISTORY_SCHEMA_VERSION:
        return None
    if payload.get(HISTORY_SCOPE_KEY) != scope:
        return None
    report = payload.get(HISTORY_REPORT_KEY)
    if not isinstance(report, dict):
        return None
    if not isinstance(report.get(CHECKS_KEY), list):
        return None
    return payload


def load_history_reports(
    history_directory: Path,
    scope: str,
    maximum_reports: int | None = None,
) -> list[dict[str, Any]]:
    """Load valid in-scope reports, newest first."""
    if maximum_reports is not None:
        _validate_positive_limit(maximum_reports, "Maximum reports to load")
    reports: list[dict[str, Any]] = []
    for path in reversed(_history_files(history_directory)):
        payload = _load_history_file(path, scope)
        if payload is not None:
            reports.append(payload)
            if maximum_reports is not None and len(reports) >= maximum_reports:
                break
    return reports


def get_failed_check_ids(
    history_directory: Path,
    scope: str,
    report_count: int,
) -> tuple[set[str], int]:
    """Return failed IDs and the number of valid reports inspected."""
    reports = load_history_reports(
        history_directory,
        scope,
        maximum_reports=report_count,
    )
    failed_check_ids: set[str] = set()
    for history_payload in reports:
        report = history_payload[HISTORY_REPORT_KEY]
        checks = report.get(CHECKS_KEY)
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, dict):
                continue
            check_id = check.get(CHECK_ID_KEY)
            if (
                isinstance(check_id, str)
                and check_id
                and check.get(STATUS_KEY) is False
            ):
                failed_check_ids.add(check_id)
    return failed_check_ids, len(reports)


def filter_checks_by_failed_ids(
    checks: Sequence[Any],
    failed_check_ids: set[str],
) -> list[Any]:
    """Return checks whose IDs appear in a historical failure set."""
    return [
        check
        for check in checks
        if getattr(check, CHECK_ID_KEY, None) in failed_check_ids
    ]
