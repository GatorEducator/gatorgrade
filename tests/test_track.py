"""Tests for the gatorgrade.track module."""

import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from gatorgrade.output.check_result import CheckResult
from gatorgrade.track import (
    AUTO_HINTS_FILENAME,
    HINT_COMMAND_KEY,
    HINT_DESCRIPTION_KEY,
    HINT_DETAILS_KEY,
    HINT_DIAGNOSTIC_KEY,
    HINT_HINT_KEY,
    HINT_WEIGHT_KEY,
    TRACK_CLI_ARGS_KEY,
    TRACK_DUE_DATE_KEY,
    TRACK_HINTS_KEY,
    TRACK_PROJECT_NAME_KEY,
    TRACK_TIMESTAMP_KEY,
    TRACK_VERSION_INFO_KEY,
    append_track_entry,
    build_track_entry,
)


def _make_hinted_result(  # noqa: PLR0913
    description: str = "test check",
    weight: int = 1,
    hint: str | None = "auto hint",
    diagnostic: str = "failure output",
    details: str = "",
    command: str = "",
) -> CheckResult:
    """Create a CheckResult with is_auto_hint set to True."""
    result = CheckResult(
        passed=False,
        description=description,
        json_info={},
        diagnostic=diagnostic,
        weight=weight,
        hint=hint,
    )
    result.is_auto_hint = True
    result.raw_diagnostic = diagnostic
    result.details = details
    result.run_command = command
    return result


def test_build_track_entry_empty_when_no_hints() -> None:
    """build_track_entry returns empty dict when no auto-hints."""
    result = CheckResult(passed=False, description="no hint", json_info={})
    entry = build_track_entry([result])
    assert entry == {}


def test_build_track_entry_includes_timestamp() -> None:
    """Entry includes a timestamp key."""
    result = _make_hinted_result()
    entry = build_track_entry([result])
    assert TRACK_TIMESTAMP_KEY in entry
    assert isinstance(entry[TRACK_TIMESTAMP_KEY], str)


def test_build_track_entry_includes_project_name() -> None:
    """Entry includes the project name."""
    result = _make_hinted_result()
    entry = build_track_entry([result], project_name="my-project")
    assert entry[TRACK_PROJECT_NAME_KEY] == "my-project"


def test_build_track_entry_uses_cwd_fallback() -> None:
    """Entry uses cwd name when no project name provided."""
    result = _make_hinted_result()
    entry = build_track_entry([result])
    assert entry[TRACK_PROJECT_NAME_KEY] == Path.cwd().name


def test_build_track_entry_includes_hints_list() -> None:
    """Entry includes a hints list with the right number of items."""
    r1 = _make_hinted_result(description="check one", hint="hint one")
    r2 = _make_hinted_result(description="check two", hint="hint two")
    entry = build_track_entry([r1, r2])
    assert TRACK_HINTS_KEY in entry
    assert len(entry[TRACK_HINTS_KEY]) == 2  # noqa: PLR2004


def test_build_track_entry_hint_contents() -> None:
    """Each hint entry contains the expected fields."""
    result = _make_hinted_result(
        description="test check",
        weight=3,
        hint="this is a hint",
        diagnostic="failure output",
        details="check: CountCommands",
        command="echo hello",
    )
    entry = build_track_entry([result])
    hint = entry[TRACK_HINTS_KEY][0]
    assert hint[HINT_DESCRIPTION_KEY] == "test check"
    assert hint[HINT_DIAGNOSTIC_KEY] == "failure output"
    assert hint[HINT_HINT_KEY] == "this is a hint"
    assert hint[HINT_WEIGHT_KEY] == 3  # noqa: PLR2004
    assert hint[HINT_COMMAND_KEY] == "echo hello"


def test_build_track_entry_skips_non_auto_hints() -> None:
    """Checks without is_auto_hint are excluded."""
    r1 = _make_hinted_result(description="auto", hint="hint1")
    r2 = CheckResult(
        passed=False, description="manual", json_info={}, hint="hint2"
    )
    # r2 has a hint but is_auto_hint defaults to False
    entry = build_track_entry([r1, r2])
    assert len(entry[TRACK_HINTS_KEY]) == 1


def test_build_track_entry_includes_version_info() -> None:
    """Version info dict is included when provided."""
    result = _make_hinted_result()
    version_info = {"python": "3.12", "platform": "x86_64-linux-gnu"}
    entry = build_track_entry([result], version_info=version_info)
    assert entry[TRACK_VERSION_INFO_KEY] == version_info


def test_build_track_entry_includes_cli_args() -> None:
    """CLI args dict is included when provided."""
    result = _make_hinted_result()
    cli_args = {"--auto-hint": True, "--auto-hint-track": True}
    entry = build_track_entry([result], cli_args=cli_args)
    assert entry[TRACK_CLI_ARGS_KEY] == cli_args


def test_append_track_entry_creates_file(tmp_path: Path) -> None:
    """append_track_entry creates autohints.json in cwd."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        result = _make_hinted_result()
        entry = build_track_entry([result], project_name="test")
        assert append_track_entry(entry)
        target = tmp_path / AUTO_HINTS_FILENAME
        assert target.exists()
        data = json.loads(target.read_text())
        assert len(data) == 1
        assert data[0][TRACK_PROJECT_NAME_KEY] == "test"
    finally:
        os.chdir(orig_cwd)


def test_append_track_entry_appends(tmp_path: Path) -> None:
    """Calling append_track_entry twice adds two entries."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        r1 = _make_hinted_result(description="first", hint="hint1")
        r2 = _make_hinted_result(description="second", hint="hint2")
        assert append_track_entry(build_track_entry([r1], project_name="p"))
        assert append_track_entry(build_track_entry([r2], project_name="p"))
        data = json.loads((tmp_path / AUTO_HINTS_FILENAME).read_text())
        assert len(data) == 2  # noqa: PLR2004
        assert data[0][TRACK_HINTS_KEY][0][HINT_DESCRIPTION_KEY] == "first"
        assert data[1][TRACK_HINTS_KEY][0][HINT_DESCRIPTION_KEY] == "second"
    finally:
        os.chdir(orig_cwd)


def test_append_track_entry_empty_returns_false() -> None:
    """append_track_entry returns False for empty entry."""
    assert not append_track_entry({})


def test_append_track_entry_recovers_corrupt_file(
    tmp_path: Path,
) -> None:
    """A corrupt autohints.json is replaced rather than failing."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        # write corrupt data
        bad_file = tmp_path / AUTO_HINTS_FILENAME
        bad_file.write_text("not valid json{{{{")
        result = _make_hinted_result(description="recovery")
        entry = build_track_entry([result], project_name="test")
        assert append_track_entry(entry)
        data = json.loads(bad_file.read_text())
        assert len(data) == 1
    finally:
        os.chdir(orig_cwd)


@pytest.mark.autohint
def test_append_track_entry_returns_false_on_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """append_track_entry returns False when the atomic write fails."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        original_mkstemp = tempfile.mkstemp
        call_count = [0]

        def _failing_mkstemp(**kwargs: Any) -> Any:
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("Disk full")
            return original_mkstemp(**kwargs)

        monkeypatch.setattr(tempfile, "mkstemp", _failing_mkstemp)
        result = _make_hinted_result(description="write fail")
        entry = build_track_entry([result], project_name="test")
        assert not append_track_entry(entry)
        assert not (tmp_path / AUTO_HINTS_FILENAME).exists()
    finally:
        os.chdir(orig_cwd)


def test_append_track_entry_cleanup_on_failed_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """append_track_entry cleans up temp file when os.replace fails."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        original_replace = os.replace

        def _failing_replace(src: str, dst: str) -> None:
            if dst.endswith(AUTO_HINTS_FILENAME):
                raise OSError("Replace failed")
            original_replace(src, dst)

        monkeypatch.setattr(os, "replace", _failing_replace)
        result = _make_hinted_result(description="replace fail")
        entry = build_track_entry([result], project_name="test")
        assert not append_track_entry(entry)
        # temp file should have been cleaned up
        tmp_files = list(tmp_path.glob(f".{AUTO_HINTS_FILENAME}.*.tmp"))
        assert len(tmp_files) == 0
    finally:
        os.chdir(orig_cwd)


def test_append_track_entry_unlink_also_fails_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When os.replace fails AND temp file cleanup also fails, no crash."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        original_replace = os.replace
        original_unlink = os.unlink

        def _failing_replace(src: str, dst: str) -> None:
            if dst.endswith(AUTO_HINTS_FILENAME):
                raise OSError("Replace failed")
            original_replace(src, dst)

        def _failing_unlink(path: str) -> None:
            if AUTO_HINTS_FILENAME in path:
                raise OSError("Unlink also failed")
            original_unlink(path)

        monkeypatch.setattr(os, "replace", _failing_replace)
        monkeypatch.setattr(os, "unlink", _failing_unlink)
        result = _make_hinted_result(description="double fail")
        entry = build_track_entry([result], project_name="test")
        assert not append_track_entry(entry)
    finally:
        os.chdir(orig_cwd)


@pytest.mark.autohint
def test_append_track_entry_empty_list_when_no_hints(
    tmp_path: Path,
) -> None:
    """No file is written when there are no auto-hints."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        result = CheckResult(passed=False, description="no hint", json_info={})
        entry = build_track_entry([result])
        # entry should be empty because no auto-hints
        assert entry == {}
        target = tmp_path / AUTO_HINTS_FILENAME
        assert not target.exists()
    finally:
        os.chdir(orig_cwd)


def test_build_track_entry_with_due_date() -> None:
    """Entry includes due_date when provided."""
    result = _make_hinted_result()
    due = datetime.datetime(2026, 12, 15, 23, 59)
    entry = build_track_entry([result], due_date=due)
    assert TRACK_DUE_DATE_KEY in entry
    assert entry[TRACK_DUE_DATE_KEY] == "2026-12-15 23:59"


def test_build_track_entry_omits_due_date_when_none() -> None:
    """Entry does not include due_date key when not provided."""
    result = _make_hinted_result()
    entry = build_track_entry([result])
    assert TRACK_DUE_DATE_KEY not in entry


def test_build_track_entry_handles_auto_hint_without_hint_text() -> None:
    """Auto-hinted result without actual hint text still produces entry."""
    result = CheckResult(
        passed=False,
        description="no hint text",
        json_info={},
        diagnostic="fail",
        weight=1,
        hint=None,
    )
    result.is_auto_hint = True
    result.raw_diagnostic = "fail"
    entry = build_track_entry([result], project_name="test")
    assert TRACK_HINTS_KEY in entry
    assert len(entry[TRACK_HINTS_KEY]) == 1
    assert HINT_HINT_KEY not in entry[TRACK_HINTS_KEY][0]


def test_build_track_entry_omits_diagnostic_when_empty() -> None:
    """Hint entry omits diagnostic key when raw_diagnostic is empty."""
    result = _make_hinted_result(diagnostic="", hint="hint")
    result.raw_diagnostic = ""
    entry = build_track_entry([result])
    hint = entry[TRACK_HINTS_KEY][0]
    assert HINT_DIAGNOSTIC_KEY not in hint


def test_build_track_entry_omits_details_when_empty() -> None:
    """Hint entry omits details key when details is empty."""
    result = _make_hinted_result(details="", hint="hint")
    result.details = ""
    entry = build_track_entry([result])
    hint = entry[TRACK_HINTS_KEY][0]
    assert HINT_DETAILS_KEY not in hint


def test_build_track_entry_omits_command_when_empty() -> None:
    """Hint entry omits command key when run_command is empty."""
    result = _make_hinted_result(command="", hint="hint")
    result.run_command = ""
    entry = build_track_entry([result])
    hint = entry[TRACK_HINTS_KEY][0]
    assert HINT_COMMAND_KEY not in hint


def test_append_track_entry_recovers_empty_file_whitespace(
    tmp_path: Path,
) -> None:
    """A file with only whitespace is treated as empty and replaced."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        empty_file = tmp_path / AUTO_HINTS_FILENAME
        empty_file.write_text("   \n   ")
        result = _make_hinted_result(description="whitespace")
        entry = build_track_entry([result], project_name="test")
        assert append_track_entry(entry)
        data = json.loads(empty_file.read_text())
        assert len(data) == 1
        assert (
            data[0][TRACK_HINTS_KEY][0][HINT_DESCRIPTION_KEY] == "whitespace"
        )
    finally:
        os.chdir(orig_cwd)


def test_append_track_entry_oserror_on_read_triggers_fresh_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OSError when reading existing file is handled gracefully."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        target = tmp_path / AUTO_HINTS_FILENAME
        target.write_text('[{"existing": true}]')
        # monkeypatch read_text to raise OSError only on the first call
        call_count = [0]

        original_read = Path.read_text

        def _broken_read(self: Path, **kwargs: Any) -> str:
            if self.name == AUTO_HINTS_FILENAME and call_count[0] == 0:
                call_count[0] += 1
                raise OSError("Permission denied")
            return original_read(self, **kwargs)

        monkeypatch.setattr(Path, "read_text", _broken_read)
        result = _make_hinted_result(description="recovered")
        entry = build_track_entry([result], project_name="test")
        assert append_track_entry(entry)
        data = json.loads(target.read_text())
        # should have only the new entry, not the existing one
        assert len(data) == 1
        assert data[0][TRACK_HINTS_KEY][0][HINT_DESCRIPTION_KEY] == "recovered"
    finally:
        os.chdir(orig_cwd)


def test_append_track_entry_non_list_json_file(
    tmp_path: Path,
) -> None:
    """A file with valid JSON that is not a list is replaced."""
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        bad_file = tmp_path / AUTO_HINTS_FILENAME
        bad_file.write_text('{"not": "a list"}')
        result = _make_hinted_result(description="replaced")
        entry = build_track_entry([result], project_name="test")
        assert append_track_entry(entry)
        data = json.loads(bad_file.read_text())
        assert len(data) == 1
        assert data[0][TRACK_HINTS_KEY][0][HINT_DESCRIPTION_KEY] == "replaced"
    finally:
        os.chdir(orig_cwd)
