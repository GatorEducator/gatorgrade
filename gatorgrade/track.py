"""Hint tracking: save auto-hint generation details to autohints.json.

This module manages a JSON file called autohints.json in the current
working directory. Each time gatorgrade runs with --auto-hint-track
and at least one hint was generated, an entry is appended to this file.

The file is a top-level JSON array. If the file does not exist, it is
created. If it exists, new data is appended safely without corruption
(atomic read-write via a temporary file + rename).
"""

import datetime
import json as json_module
import os
import tempfile
from pathlib import Path
from typing import Any

# filename for the tracking file
AUTO_HINTS_FILENAME = "autohints.json"

# JSON key constants for tracking entries
TRACK_TIMESTAMP_KEY = "timestamp"
TRACK_PROJECT_NAME_KEY = "project_name"
TRACK_DUE_DATE_KEY = "due_date"
TRACK_VERSION_INFO_KEY = "version_info"
TRACK_CLI_ARGS_KEY = "cli_args"
TRACK_HINTS_KEY = "hints"

# per-hint keys
HINT_DESCRIPTION_KEY = "description"
HINT_DIAGNOSTIC_KEY = "diagnostic"
HINT_DETAILS_KEY = "details"
HINT_HINT_KEY = "hint"
HINT_WEIGHT_KEY = "weight"
HINT_COMMAND_KEY = "command"
HINT_CHECK_ID_KEY = "check_id"

# timestamp format matching the report
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
DATETIME_FMT_HUMAN = "%Y-%m-%d %H:%M"

# file operation constants
FILE_ENCODING = "utf-8"
INDENT_JSON = 4


def build_track_entry(
    failed_results: list[Any],
    project_name: str | None = None,
    due_date: datetime.datetime | None = None,
    version_info: dict | None = None,
    cli_args: dict | None = None,
) -> dict[str, Any]:
    """Build a tracking entry dict from failing check results.

    Only includes checks that have an auto-generated hint
    (result.is_auto_hint is True). This keeps the tracking
    file focused on hints rather than every check.

    Args:
        failed_results: List of CheckResult objects for failing
            checks.
        project_name: Optional project name from the config file.
        due_date: Optional due date from the config file.
        version_info: Version and platform information dict.
        cli_args: Command-line arguments dict.

    Returns:
        A dict with timestamp, project info, version info, CLI
        args, and a hints list. Returns an empty dict if no
        auto-hints were generated.

    """
    # collect only the results that have auto-generated hints
    hinted_results = [r for r in failed_results if r.is_auto_hint]
    if not hinted_results:
        return {}
    # build the hints list
    hints_list = []
    for result in hinted_results:
        hint_entry: dict[str, Any] = {
            HINT_DESCRIPTION_KEY: result.description,
        }
        if result.raw_diagnostic:
            hint_entry[HINT_DIAGNOSTIC_KEY] = result.raw_diagnostic
        if result.details:
            hint_entry[HINT_DETAILS_KEY] = result.details
        if result.hint:
            hint_entry[HINT_HINT_KEY] = result.hint
        hint_entry[HINT_WEIGHT_KEY] = result.weight
        if result.run_command:
            hint_entry[HINT_COMMAND_KEY] = result.run_command
        if result.check_id:
            hint_entry[HINT_CHECK_ID_KEY] = result.check_id
        hints_list.append(hint_entry)
    # build the overall entry
    now = datetime.datetime.now()
    entry: dict[str, Any] = {
        TRACK_TIMESTAMP_KEY: now.strftime(DATETIME_FMT),
        TRACK_PROJECT_NAME_KEY: project_name or Path.cwd().name,
    }
    if due_date is not None:
        entry[TRACK_DUE_DATE_KEY] = due_date.strftime(DATETIME_FMT_HUMAN)
    if version_info:
        entry[TRACK_VERSION_INFO_KEY] = version_info
    if cli_args:
        entry[TRACK_CLI_ARGS_KEY] = cli_args
    entry[TRACK_HINTS_KEY] = hints_list
    return entry


def append_track_entry(entry: dict[str, Any]) -> bool:
    """Append a single tracking entry to autohints.json.

    Creates the file if it does not exist. Uses an atomic write
    (temp file + rename) so concurrent runs cannot corrupt the file.

    Args:
        entry: A tracking entry dict as built by build_track_entry.

    Returns:
        True if the entry was written, False if it was empty or
        the write failed.

    """
    if not entry:
        return False
    target = Path.cwd() / AUTO_HINTS_FILENAME
    # read existing entries if the file exists
    existing: list[dict[str, Any]] = []
    if target.exists():
        try:
            raw = target.read_text(encoding=FILE_ENCODING)
            if raw.strip():
                parsed = json_module.loads(raw)
                if isinstance(parsed, list):
                    existing = parsed
        except (json_module.JSONDecodeError, OSError):
            # if the file is corrupt, start fresh
            existing = []
    # append the new entry
    existing.append(entry)
    # write atomically: temp file in the same directory, then rename
    try:
        fd, tmp_path_str = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{AUTO_HINTS_FILENAME}.",
            suffix=".tmp",
        )
        with os.fdopen(fd, "w", encoding=FILE_ENCODING) as tmp_file:
            json_module.dump(existing, tmp_file, indent=INDENT_JSON)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path_str, str(target))
        return True
    except OSError:
        # clean up the temp file on failure if it still exists
        if "tmp_path_str" in locals():
            try:
                os.unlink(tmp_path_str)
            except OSError:
                pass
        return False
