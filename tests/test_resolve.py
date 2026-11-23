"""Tests for the gatorgrade.resolve module."""

from pathlib import Path
from typing import Any

import pytest

from gatorgrade import resolve

CONFIG_FILENAME = "gatorgrade.yml"
WORKING_DIRECTORY = "working"
PROJECT_DIRECTORY = "project"
CONFIG_DIRECTORY = "config"
PROMPT_FILENAME = "myprompt.md"
PROMPT_CONTENT = "Custom system prompt content."
ALTERNATIVE_PROMPT_CONTENT = "Lower-priority system prompt."
RULES_FILENAME = "rules.json"
RULES_CONTENT = '{"cannot_contain": ["bad phrase"]}'
ALTERNATIVE_RULES_CONTENT = '{"must_contain": ["lower priority"]}'
EXPECTED_RULES = {"cannot_contain": ["bad phrase"]}
INVALID_JSON = "not valid json{{"
NON_OBJECT_JSON = '["must_contain", "x"]'
FILE_ENCODING = "utf-8"
READ_TEXT_OPERATION = "read_text"
STAT_OPERATION = "stat"
CONFIG_WITH_FILES = (
    f'system_prompt_file: "{PROMPT_FILENAME}"\n'
    f'validation_phrases_file: "{RULES_FILENAME}"\n'
    "---\n"
    "[]\n"
)


def _prepare_resolution_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Create separate working, project, and configuration directories."""
    working_dir = tmp_path / WORKING_DIRECTORY
    project_dir = tmp_path / PROJECT_DIRECTORY
    config_dir = tmp_path / CONFIG_DIRECTORY
    for directory in (working_dir, project_dir, config_dir):
        directory.mkdir()
    config_file = project_dir / CONFIG_FILENAME
    config_file.write_text(CONFIG_WITH_FILES, encoding=FILE_ENCODING)
    monkeypatch.chdir(working_dir)
    return config_file, config_dir


def _deny_path_access(
    blocked_file: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Simulate inaccessible files independently of filesystem permissions."""
    original_operation = getattr(Path, operation)

    def access_path(path: Path, *args: Any, **kwargs: Any) -> Any:
        """Access other files normally while rejecting the blocked file."""
        if path.absolute() == blocked_file.absolute():
            raise PermissionError(blocked_file)
        return original_operation(path, *args, **kwargs)

    monkeypatch.setattr(Path, operation, access_path)


def test_resolve_system_prompt_reads_file(tmp_path: Path) -> None:
    """resolve_system_prompt reads the system prompt file alongside config."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'system_prompt_file: "myprompt.md"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    prompt_file = tmp_path / "myprompt.md"
    prompt_file.write_text("Custom system prompt content.")
    result = resolve.resolve_system_prompt(config_file, None)
    assert result == "Custom system prompt content."


def test_resolve_system_prompt_returns_none_when_not_specified(
    tmp_path: Path,
) -> None:
    """resolve_system_prompt returns None when no system_prompt_file field."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    result = resolve.resolve_system_prompt(config_file, None)
    assert result is None


@pytest.mark.parametrize(
    "fallback_directory", [PROJECT_DIRECTORY, CONFIG_DIRECTORY]
)
def test_resolve_system_prompt_skips_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fallback_directory: str,
) -> None:
    """A directory must not hide a system prompt in a later search location."""
    config_file, config_dir = _prepare_resolution_paths(tmp_path, monkeypatch)
    Path(PROMPT_FILENAME).mkdir()
    (config_dir / PROMPT_FILENAME).write_text(
        ALTERNATIVE_PROMPT_CONTENT, encoding=FILE_ENCODING
    )
    prompt_file = tmp_path / fallback_directory / PROMPT_FILENAME
    prompt_file.write_text(PROMPT_CONTENT, encoding=FILE_ENCODING)
    result = resolve.resolve_system_prompt(config_file, config_dir)
    assert result == PROMPT_CONTENT


@pytest.mark.parametrize(
    "fallback_directory", [PROJECT_DIRECTORY, CONFIG_DIRECTORY]
)
@pytest.mark.parametrize("operation", [READ_TEXT_OPERATION, STAT_OPERATION])
def test_resolve_system_prompt_skips_inaccessible_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fallback_directory: str,
    operation: str,
) -> None:
    """An inaccessible prompt must not prevent searching later locations."""
    config_file, config_dir = _prepare_resolution_paths(tmp_path, monkeypatch)
    blocked_file = Path(PROMPT_FILENAME)
    blocked_file.touch()
    prompt_file = tmp_path / fallback_directory / PROMPT_FILENAME
    prompt_file.write_text(PROMPT_CONTENT, encoding=FILE_ENCODING)
    _deny_path_access(blocked_file, monkeypatch, operation)
    result = resolve.resolve_system_prompt(config_file, config_dir)
    assert result == PROMPT_CONTENT


def test_resolve_validation_rules_returns_none_when_not_specified(
    tmp_path: Path,
) -> None:
    """resolve_validation_rules returns None when no validation_phrases_file."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    result = resolve.resolve_validation_rules(config_file, None)
    assert result is None


def test_resolve_validation_rules_reads_json_file(
    tmp_path: Path,
) -> None:
    """resolve_validation_rules reads and parses a JSON validation file."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'validation_phrases_file: "quality.json"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    rules_file = tmp_path / "quality.json"
    rules_file.write_text(
        '{"cannot_contain": ["bad phrase"], "must_contain": ["good word"]}'
    )
    result = resolve.resolve_validation_rules(config_file, None)
    assert result is not None
    assert result["cannot_contain"] == ["bad phrase"]
    assert result["must_contain"] == ["good word"]


def test_resolve_validation_rules_returns_none_on_invalid_json(
    tmp_path: Path,
) -> None:
    """resolve_validation_rules returns None for unparseable JSON."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'validation_phrases_file: "bad.json"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    rules_file = tmp_path / "bad.json"
    rules_file.write_text("not valid json{{")
    result = resolve.resolve_validation_rules(config_file, None)
    assert result is None


def test_resolve_validation_rules_returns_none_for_non_dict_json(
    tmp_path: Path,
) -> None:
    """resolve_validation_rules returns None when JSON is valid but not a dict."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'validation_phrases_file: "items.json"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    rules_file = tmp_path / "items.json"
    rules_file.write_text('["must_contain", "x"]')
    result = resolve.resolve_validation_rules(config_file, None)
    assert result is None


def test_resolve_validation_rules_finds_file_alongside_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolves the validation file alongside the config file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "gatorgrade.yml"
    config_file.write_text(
        'validation_phrases_file: "rules.json"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    rules_file = config_dir / "rules.json"
    rules_file.write_text('{"cannot_contain": ["x"]}')
    monkeypatch.chdir(tmp_path)
    result = resolve.resolve_validation_rules(config_file, None)
    assert result == {"cannot_contain": ["x"]}


@pytest.mark.parametrize(
    "fallback_directory", [PROJECT_DIRECTORY, CONFIG_DIRECTORY]
)
def test_resolve_validation_rules_skips_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fallback_directory: str,
) -> None:
    """A directory must not hide validation rules in a later search location."""
    config_file, config_dir = _prepare_resolution_paths(tmp_path, monkeypatch)
    Path(RULES_FILENAME).mkdir()
    (config_dir / RULES_FILENAME).write_text(
        ALTERNATIVE_RULES_CONTENT, encoding=FILE_ENCODING
    )
    rules_file = tmp_path / fallback_directory / RULES_FILENAME
    rules_file.write_text(RULES_CONTENT, encoding=FILE_ENCODING)
    result = resolve.resolve_validation_rules(config_file, config_dir)
    assert result == EXPECTED_RULES


@pytest.mark.parametrize(
    "fallback_directory", [PROJECT_DIRECTORY, CONFIG_DIRECTORY]
)
@pytest.mark.parametrize("operation", [READ_TEXT_OPERATION, STAT_OPERATION])
def test_resolve_validation_rules_skips_inaccessible_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fallback_directory: str,
    operation: str,
) -> None:
    """Inaccessible rules must not prevent searching later locations."""
    config_file, config_dir = _prepare_resolution_paths(tmp_path, monkeypatch)
    blocked_file = Path(RULES_FILENAME)
    blocked_file.touch()
    rules_file = tmp_path / fallback_directory / RULES_FILENAME
    rules_file.write_text(RULES_CONTENT, encoding=FILE_ENCODING)
    _deny_path_access(blocked_file, monkeypatch, operation)
    result = resolve.resolve_validation_rules(config_file, config_dir)
    assert result == EXPECTED_RULES


@pytest.mark.parametrize("invalid_contents", [INVALID_JSON, NON_OBJECT_JSON])
def test_resolve_validation_rules_keeps_invalid_file_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_contents: str,
) -> None:
    """Readable invalid rules must not fall back to lower-priority rules."""
    config_file, config_dir = _prepare_resolution_paths(tmp_path, monkeypatch)
    Path(RULES_FILENAME).write_text(invalid_contents, encoding=FILE_ENCODING)
    rules_file = config_dir / RULES_FILENAME
    rules_file.write_text(RULES_CONTENT, encoding=FILE_ENCODING)
    assert resolve.resolve_validation_rules(config_file, config_dir) is None
