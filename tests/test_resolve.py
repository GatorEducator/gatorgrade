"""Tests for the gatorgrade.resolve module."""

from pathlib import Path

import pytest

from gatorgrade import resolve


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
