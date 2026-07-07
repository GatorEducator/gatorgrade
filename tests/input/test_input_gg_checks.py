"""Test suite for parse_config function."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.input.in_file_path import reformat_yaml_data
from gatorgrade.input.parse_config import (
    get_auto_hint_model,
    get_config_dir,
    get_due_date,
    get_due_date_aliases_present,
    get_project_name,
    get_system_prompt_file,
    get_validation_phrases_file,
    has_due_date_field,
    parse_config,
    resolve_config_path,
)


def test_parse_config_returns_error_for_invalid_yaml(tmp_path: Path) -> None:
    """Test parse_config returns an error message for invalid YAML content."""
    # given an invalid YAML file
    invalid_yaml = tmp_path / "invalid.yml"
    invalid_yaml.write_text("*invalid: yaml: [content")
    # when parse_config is run
    checks, error = parse_config(invalid_yaml)
    # then checks is empty and error contains details
    assert checks == []
    assert error is not None


def test_get_due_date_returns_datetime_when_specified(tmp_path: Path) -> None:
    """Test get_due_date returns a datetime from the front matter."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'due_date: "2026-12-15T23:59:00"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is not None
    assert result.year == 2026  # noqa: PLR2004
    assert result.month == 12  # noqa: PLR2004
    assert result.day == 15  # noqa: PLR2004
    assert result.hour == 23  # noqa: PLR2004
    assert result.minute == 59  # noqa: PLR2004


def test_get_due_date_accepts_date_only(tmp_path: Path) -> None:
    """Test get_due_date accepts date-only format (no time)."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'due_date: "2026-12-15"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is not None
    assert result.year == 2026  # noqa: PLR2004
    assert result.month == 12  # noqa: PLR2004
    assert result.day == 15  # noqa: PLR2004
    assert result.hour == 0
    assert result.minute == 0


def test_get_due_date_returns_none_when_missing(tmp_path: Path) -> None:
    """Test get_due_date returns None when no due_date field."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is None


def test_get_due_date_handles_invalid_format(tmp_path: Path) -> None:
    """Test get_due_date returns None for unparseable date strings."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'due_date: "not-a-date"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is None


def test_has_due_date_field_returns_true_when_present(tmp_path: Path) -> None:
    """Test has_due_date_field returns True when due_date is in the config."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'due_date: "2026-12-15"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = has_due_date_field(config_file)
    assert result is True


def test_get_system_prompt_file_returns_filename_when_specified(
    tmp_path: Path,
) -> None:
    """get_system_prompt_file returns the filename from the front matter."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'system_prompt_file: "my_prompt.md"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    result = get_system_prompt_file(config_file)
    assert result == "my_prompt.md"


def test_get_system_prompt_file_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    """get_system_prompt_file returns None when no system_prompt_file field."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    result = get_system_prompt_file(config_file)
    assert result is None


def test_get_validation_phrases_file_returns_filename_when_specified(
    tmp_path: Path,
) -> None:
    """get_validation_phrases_file returns the filename from the front matter."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'validation_phrases_file: "quality.json"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    result = get_validation_phrases_file(config_file)
    assert result == "quality.json"


def test_get_validation_phrases_file_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    """get_validation_phrases_file returns None when not specified."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    result = get_validation_phrases_file(config_file)
    assert result is None


class TestGetConfigDir:
    """Tests for the get_config_dir function."""

    def test_returns_path(self) -> None:
        """get_config_dir always returns a Path."""
        result = get_config_dir()
        assert isinstance(result, Path)

    def test_env_var_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """$GATORGRADE_CONFIG_DIR overrides the default config dir."""
        monkeypatch.setenv("GATORGRADE_CONFIG_DIR", "/tmp/my-config")
        result = get_config_dir()
        assert result == Path("/tmp/my-config")


class TestResolveConfigPath:
    """Tests for the resolve_config_path function."""

    def test_absolute_path_returned_as_is(self) -> None:
        """Absolute paths are returned unchanged."""
        result = resolve_config_path(Path("/etc/gatorgrade.yml"))
        assert result == Path("/etc/gatorgrade.yml")

    def test_file_in_cwd_is_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the file exists in the CWD, it is returned."""
        config_file = tmp_path / "gatorgrade.yml"
        config_file.write_text("name: test\n")
        monkeypatch.chdir(tmp_path)
        name = Path("gatorgrade.yml")
        result = resolve_config_path(name)
        assert result == name
        assert result.resolve() == config_file.resolve()

    def test_file_in_config_dir_is_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the file exists in the config dir, it is returned."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "gatorgrade.yml"
        config_file.write_text("name: test\n")
        monkeypatch.chdir(tmp_path)
        result = resolve_config_path(Path("gatorgrade.yml"), config_dir)
        assert result == config_file

    def test_cwd_takes_precedence_over_config_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file in the CWD takes precedence over the config dir."""
        cwd_file = tmp_path / "gatorgrade.yml"
        cwd_file.write_text("name: cwd\n")
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "gatorgrade.yml"
        config_file.write_text("name: config\n")
        monkeypatch.chdir(tmp_path)
        name = Path("gatorgrade.yml")
        result = resolve_config_path(name, config_dir)
        assert result == name
        assert result.resolve() == cwd_file.resolve()

    def test_file_not_found_returns_original(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the file is not found anywhere, the original name is returned."""
        monkeypatch.chdir(tmp_path)
        result = resolve_config_path(Path("nonexistent.yml"))
        assert result == Path("nonexistent.yml")

    def test_file_not_found_in_cwd_or_config_dir_returns_original(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns original when not in CWD or config dir."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        result = resolve_config_path(Path("nonexistent.yml"), config_dir)
        assert result == Path("nonexistent.yml")


def test_get_auto_hint_model_returns_model_id(tmp_path: Path) -> None:
    """Return the auto_hint_model value from the config front matter."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'auto_hint_model: "custom/model"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = get_auto_hint_model(config_file)
    assert result == "custom/model"


def test_get_auto_hint_model_returns_none_when_missing(tmp_path: Path) -> None:
    """Return None when the config front matter has no auto_hint_model."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = get_auto_hint_model(config_file)
    assert result is None


def test_get_due_date_handles_os_error(tmp_path: Path) -> None:
    """Test get_due_date returns an error when the path is a directory."""
    result, error = get_due_date(tmp_path)
    # tmp_path is a directory, so opening it as a file raises an error
    assert result is None
    assert error is not None
    assert "Could not read" in error or "Could not parse" in error


def test_get_due_date_handles_yaml_error(tmp_path: Path) -> None:
    """Test get_due_date returns an error for invalid YAML content."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text("*invalid: yaml: [content")
    result, error = get_due_date(config_file)
    assert result is None
    assert error is not None
    assert "Could not parse" in error


def test_get_due_date_accepts_timezone_aware(tmp_path: Path) -> None:
    """Test get_due_date handles timezone-aware ISO 8601 strings."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'due_date: "2026-12-15T23:59:00-05:00"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is not None
    # should be converted to naive local time (no tzinfo)
    assert result.tzinfo is None


def test_get_project_name_returns_none_on_unreadable(tmp_path: Path) -> None:
    """Test get_project_name returns None when the file cannot be read."""
    missing_file = tmp_path / "nonexistent.yml"
    result = get_project_name(missing_file)
    assert result is None


def test_get_project_name_with_yaml_error(tmp_path: Path) -> None:
    """Test get_project_name returns None for invalid YAML content."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text("*invalid: yaml: [content")
    result = get_project_name(config_file)
    assert result is None


def test_get_due_date_with_unquoted_yaml_date(tmp_path: Path) -> None:
    """Test get_due_date accepts an unquoted YAML date value."""
    config_file = tmp_path / "gatorgrade.yml"
    # an unquoted YAML date is parsed as a datetime.date object
    config_file.write_text(
        "due_date: 2026-12-15\n"
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is not None
    assert result.year == 2026  # noqa: PLR2004
    assert result.month == 12  # noqa: PLR2004
    assert result.day == 15  # noqa: PLR2004


def test_get_due_date_with_non_string_value(tmp_path: Path) -> None:
    """Test get_due_date returns error for non-string, non-date values."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "due_date: 12345\n"
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, error = get_due_date(config_file)
    assert result is None
    assert error is not None
    assert "Unsupported due date type" in error


def test_get_due_date_with_unquoted_yaml_datetime(tmp_path: Path) -> None:
    """Test get_due_date accepts an unquoted YAML datetime value."""
    config_file = tmp_path / "gatorgrade.yml"
    # unquoted ISO datetime is parsed by PyYAML as datetime.datetime
    config_file.write_text(
        "due_date: 2026-12-15T23:59:00\n"
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is not None
    assert result.year == 2026  # noqa: PLR2004
    assert result.month == 12  # noqa: PLR2004
    assert result.day == 15  # noqa: PLR2004
    assert result.hour == 23  # noqa: PLR2004
    assert result.minute == 59  # noqa: PLR2004


@pytest.mark.parametrize(
    ("fields", "count", "first"),
    [
        (["due_date"], 1, "due_date"),
        (["due_date", "due"], 2, "due_date"),
        (["date", "due"], 2, "due"),
        (["duedate", "date", "due"], 3, "duedate"),
        (["name"], 0, None),
    ],
)
def test_get_due_date_aliases_present(
    tmp_path: Path, fields: list[str], count: int, first: str | None
) -> None:
    """Test get_due_date_aliases_present detects multiple aliases correctly."""
    config_file = tmp_path / "gatorgrade.yml"
    front_matter = "\n".join(f'{f}: "2026-12-15"' for f in fields)
    config_file.write_text(
        f"{front_matter}\n"
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = get_due_date_aliases_present(config_file)
    assert len(result) == count
    if first is not None:
        assert result[0] == first


def test_has_due_date_field_returns_false_when_missing(tmp_path: Path) -> None:
    """Test has_due_date_field returns False when due_date is not in the config."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = has_due_date_field(config_file)
    assert result is False


def test_get_due_date_still_returns_none_on_invalid(tmp_path: Path) -> None:
    """Test get_due_date returns None for unparseable dates (no warning)."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'due_date: "not-a-date"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is None


def test_parse_config_gg_check_in_file_context_contains_file() -> None:
    """Test to make sure that the file context is included in the GatorGrader arguments."""
    # given a configuration file with a GatorGrader check within a file context
    config = Path(
        "tests/input/yml_test_files/gatorgrade_one_gg_check_in_file.yml"
    )
    # when parse_config is run
    output, _ = parse_config(config)
    # then the file path should be in the GatorGrader arguments
    assert isinstance(output[0], GatorGraderCheck)
    assert "file.py" in output[0].gg_args


def test_parse_config_check_gg_matchfilefragment() -> None:
    """Test to make sure the description, check name, and options appear in the GatorGrader arguments."""
    # given a configuration file with a GatorGrader check
    config = Path(
        "tests/input/yml_test_files/gatorgrade_matchfilefragment.yml"
    )
    # when parse_config is run
    output, _ = parse_config(config)
    # then the description, check name, and options appear in the GatorGrader arguments
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].gg_args == [
        "--description",
        "Complete all TODOs",
        "MatchFileFragment",
        "--fragment",
        "TODO",
        "--count",
        "0",
        "--exact",
        "--directory",
        "path/to",
        "--file",
        "file.py",
    ]


def test_parse_config_gg_check_no_file_context_contains_no_file() -> None:
    """Test to make sure checks without a file context do not have a file path in GatorGrader arguments."""
    # given a configuration file with a GatorGrader check without a file context
    config = Path(
        "tests/input/yml_test_files/gatorgrade_one_gg_check_no_file_context.yml"
    )
    # when parse_config is run
    output, _ = parse_config(config)
    # then the GatorGrader arguments do not contain a file path
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].gg_args == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_parses_both_shell_and_gg_checks() -> None:
    """Test to make sure that both shell and GatorGrader checks are parsed."""
    # given a configuration file that contains a shell check and GatorGrader check
    config = Path("tests/input/yml_test_files/gatorgrader_both_checks.yml")
    # when parse_config is run
    output, _ = parse_config(config)
    # then the output should contain a shell check and GatorGrader check
    assert isinstance(output[0], GatorGraderCheck)
    assert isinstance(output[1], ShellCheck)


def test_parse_config_yml_file_runs_setup_shell_checks() -> None:
    """Test to make sure that a configuration file without setup commands can be parsed."""
    # given a configuration file without setup commands
    config = Path(
        "tests/input/yml_test_files/gatorgrade_no_shell_setup_check.yml"
    )
    # when parse_config run
    output, _ = parse_config(config)
    # then the output should contain the GatorGrader check
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].gg_args == [
        "--description",
        "Have 8 commits",
        "CountCommits",
        "--count",
        "8",
    ]


def test_parse_config_shell_check_contains_command() -> None:
    """Test to make sure that the command for a shell check is stored."""
    # given a configuration file with a shell check
    config = Path(
        "tests/input/yml_test_files/gatorgrade_one_shell_command_check.yml"
    )
    # when the parse_config is run
    output, _ = parse_config(config)
    # then the command should be stored in the shell check
    assert isinstance(output[0], ShellCheck)
    assert output[0].command == "mdl ."


def test_parse_config_parses_weighted_checks() -> None:
    """Test to make sure that weighted checks are parsed correctly."""
    # given a configuration file with weighted checks
    config = Path("tests/input/yml_test_files/gatorgrade_weighted_checks.yml")
    # when parse_config is run
    output, _ = parse_config(config)
    # then the weights should be parsed correctly
    assert isinstance(output[0], GatorGraderCheck)
    assert output[0].weight == 10  # noqa: PLR2004
    assert isinstance(output[1], ShellCheck)
    assert output[1].weight == 5  # noqa: PLR2004


def test_parse_config_parses_outputlimit_checks() -> None:
    """Test to make sure that checks with outputlimit are parsed correctly."""
    # given a configuration file with outputlimit checks
    config = Path("tests/input/yml_test_files/gatorgrade_outputlimit.yml")
    # when parse_config is run
    output, _ = parse_config(config)
    # then the outputlimits should be parsed correctly
    assert isinstance(output[0], ShellCheck)
    assert output[0].outputlimit == 5  # noqa: PLR2004
    assert output[0].weight == 10  # noqa: PLR2004
    assert isinstance(output[1], GatorGraderCheck)
    assert output[1].outputlimit == 25  # noqa: PLR2004


def test_parse_config_with_baseline_weight() -> None:
    """Test that baseline_weight affects checks without explicit weight."""
    # given a configuration file with checks that have no explicit weight
    config = Path("tests/test_assignment/gatorgrade.yml")
    # when parse_config is run with a non-default baseline weight
    output, _ = parse_config(config, baseline_weight=4)
    # then all checks should have weight 4
    for check in output:
        assert check.weight == 4  # noqa: PLR2004


def test_parse_config_with_baseline_weight_and_explicit_weight() -> None:
    """Test that explicit weight overrides baseline_weight."""
    # given a configuration file where some checks have explicit weights
    config = Path("tests/input/yml_test_files/gatorgrade_outputlimit.yml")
    # when parse_config is run with a non-default baseline weight
    output, _ = parse_config(config, baseline_weight=2)
    # then the check with explicit weight 10 retains it
    assert isinstance(output[0], ShellCheck)
    assert output[0].weight == 10  # noqa: PLR2004
    # and the check without explicit weight gets the baseline weight
    assert isinstance(output[1], GatorGraderCheck)
    assert output[1].weight == 2  # noqa: PLR2004


@pytest.mark.parametrize(
    "invalid_weight",
    [
        0,
        -1,
        -5,
        -100,
    ],
)
def test_parse_config_rejects_invalid_baseline_weight(
    invalid_weight: int,
) -> None:
    """Test parse_config returns error for non-positive baseline_weight."""
    config = Path("tests/test_assignment/gatorgrade.yml")
    checks, error = parse_config(config, baseline_weight=invalid_weight)
    assert checks == []
    assert error is not None
    assert "baseline_weight" in error


@pytest.mark.propertybased
@given(st.text(min_size=1, max_size=100))
def test_parse_config_invalid_yaml_returns_error_property(
    yaml_content: str,
) -> None:
    """Property: any non-empty string written as YAML returns checks+message or error."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_content)
        temp_path = f.name
    try:
        checks, error = parse_config(Path(temp_path))
        if error is not None:
            assert checks == []
            assert isinstance(error, str)
            assert len(error) > 0
        else:
            assert len(checks) >= 0
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_reformat_yaml_data_with_empty_list() -> None:
    """Test reformat_yaml_data raises IndexError with an empty list."""
    with pytest.raises(IndexError):
        reformat_yaml_data([])


def test_get_project_name_returns_name_when_specified(tmp_path: Path) -> None:
    """Test get_project_name returns the name from the config front matter."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'name: "Custom Project Name"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = get_project_name(config_file)
    assert result == "Custom Project Name"


def test_get_project_name_returns_none_when_missing(tmp_path: Path) -> None:
    """Test get_project_name returns None when no name field."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = get_project_name(config_file)
    assert result is None


def test_get_project_name_returns_none_when_file_missing(
    tmp_path: Path,
) -> None:
    """Test get_project_name returns None when the file does not exist."""
    missing_file = tmp_path / "nonexistent.yml"
    result = get_project_name(missing_file)
    assert result is None


def test_get_project_name_handles_malformed_front_matter(
    tmp_path: Path,
) -> None:
    """Test get_project_name returns None for YAML with a missing closing quote."""
    config_file = tmp_path / "gatorgrade.yml"
    # name value starts with a double-quote but has no closing quote
    config_file.write_text(
        'name: "unclosed string\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = get_project_name(config_file)
    assert result is None


def test_parse_config_rejects_malformed_front_matter(
    tmp_path: Path,
) -> None:
    """Test parse_config returns error for YAML with a missing closing quote."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        'name: "unclosed string\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    checks, error = parse_config(config_file)
    assert checks == []
    assert error is not None


@pytest.mark.parametrize(
    "field_name",
    [
        "due_date",
        "duedate",
        "due",
        "date",
    ],
)
def test_get_due_date_accepts_all_aliases(
    tmp_path: Path, field_name: str
) -> None:
    """Test get_due_date accepts all supported alias field names."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        f'{field_name}: "2026-12-15"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result, _ = get_due_date(config_file)
    assert result is not None
    assert result.year == 2026  # noqa: PLR2004
    assert result.month == 12  # noqa: PLR2004
    assert result.day == 15  # noqa: PLR2004


@pytest.mark.parametrize(
    "field_name",
    [
        "due_date",
        "duedate",
        "due",
        "date",
    ],
)
def test_has_due_date_field_detects_all_aliases(
    tmp_path: Path, field_name: str
) -> None:
    """Test has_due_date_field detects all supported alias field names."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        f'{field_name}: "2026-12-15"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = has_due_date_field(config_file)
    assert result is True
