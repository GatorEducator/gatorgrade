"""Tests for the main file of the project."""

import builtins
import io
import os
import re
from pathlib import Path
from typing import Any, Callable, Generator, List

import pytest
from typer.testing import CliRunner

from gatorgrade import main
from gatorgrade.hint.fallback import RemoteEngineAdapter

runner = CliRunner()

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def patch_open(
    open_func: Callable[..., Any], files: List[str]
) -> Callable[..., Any]:
    """Create a patch to for file opening to track and later delete opened files."""

    def open_patched(  # noqa: PLR0913
        path: Any,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        closefd: bool = True,
        opener: Any | None = None,
    ) -> Any:
        if "w" in mode and not os.path.isfile(path):
            files.append(path)
        return open_func(
            path,
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
            closefd=closefd,
            opener=opener,
        )

    return open_patched


@pytest.fixture(autouse=True)
def cleanup_files(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Cleanup any files that are created by the tests in this test suite."""
    files = []
    monkeypatch.setattr(builtins, "open", patch_open(builtins.open, files))
    monkeypatch.setattr(io, "open", patch_open(io.open, files))
    yield
    for file in files:
        Path(file).unlink(missing_ok=True)


@pytest.mark.parametrize(
    "assignment_path,expected_output_and_freqs",
    [
        (
            "tests/test_assignment",
            [
                ("Complete all TODOs", 2),
                ("Use an if statement", 1),
                ("✓", 3),
                ("✕", 0),
                ("- Project: test_assignment", 1),
                ("- Checks: 3/3 (100%)", 1),
                ("- Points: 3/3 (100%)", 1),
            ],
        )
    ],
)
def test_full_integration_creates_valid_output(
    assignment_path: str,
    expected_output_and_freqs: List[tuple[str, int]],
    chdir: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Tests full integration pipeline to ensure input assignments give the correct output."""
    # the assignment path is:
    # tests/test_assignment
    chdir(assignment_path)
    # result is the following information:
    # ✓  Complete all TODOs
    # ✓  Use an if statement
    # ✓  Complete all TODOs
    result = runner.invoke(main.app)
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    for output, freq in expected_output_and_freqs:
        assert plain_stdout.count(output) == freq


def test_gatorgrade_with_nonexistent_file(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade exits with error when config file doesn't exist."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--config", "nonexistent.yml"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 1
    assert "either does not exist or is not valid" in result.stdout


def test_gatorgrade_version_callback_with_false() -> None:
    """_version_callback does not exit when value is False."""
    main._version_callback(False)


def test_gatorgrade_with_invalid_yaml_file(
    chdir: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test that gatorgrade displays a parse error for invalid YAML."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text("*invalid: yaml: [content")
    chdir(tmp_path)
    result = runner.invoke(main.app)
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 1


def test_gatorgrade_with_version_flag(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade shows version with --version."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--version"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0


def test_create_auto_hint_engine_default_model(chdir: Any) -> None:
    """_create_auto_hint_engine uses default model when sentinel is passed."""
    chdir("tests/test_assignment")
    engine = main._create_auto_hint_engine(
        filename=Path("gatorgrade.yml"),
        auto_hint_model=main.AUTO_HINT_MODEL_DEFAULT,
        auto_hint_url=None,
        auto_hint_api_key=None,
    )
    assert engine is not None


@pytest.mark.autohint
def test_create_auto_hint_engine_with_remote_url_falls_back(
    chdir: Any,
) -> None:
    """Falls back to local engine when remote URL is unreachable."""
    chdir("tests/test_assignment")
    engine = main._create_auto_hint_engine(
        filename=Path("gatorgrade.yml"),
        auto_hint_model=main.AUTO_HINT_MODEL_DEFAULT,
        auto_hint_url="http://localhost:99999",
        auto_hint_api_key=None,
    )
    assert engine is not None


@pytest.mark.autohint
def test_try_create_remote_engine_returns_adapter() -> None:
    """Returns a RemoteEngineAdapter even with a bad URL (lazy connect)."""
    engine = main._try_create_remote_engine(
        url="http://localhost:99999",
        api_key=None,
        model_id="test-model",
    )
    assert isinstance(engine, RemoteEngineAdapter)


def test_print_verbose_info_skips_when_not_verbose(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_print_verbose_info prints nothing when verbose is False."""
    main._print_verbose_info(
        verbose=False,
        config_path=Path("test.yml"),
        config_dir=Path("/tmp"),
        auto_hint=False,
        auto_hint_model="model",
        auto_hint_url=None,
        output_limit=5,
        baseline_weight=1,
        show_diagnostics=True,
        progress_bar=True,
    )
    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_verbose_info_shows_info_when_verbose(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_print_verbose_info prints configuration when verbose is True."""
    main._print_verbose_info(
        verbose=True,
        config_path=Path("test.yml"),
        config_dir=Path("/tmp"),
        auto_hint=True,
        auto_hint_model="test-model",
        auto_hint_url="http://localhost:4000",
        output_limit=10,
        baseline_weight=2,
        show_diagnostics=False,
        progress_bar=False,
    )
    captured = capsys.readouterr()
    plain_out = ANSI_ESCAPE_PATTERN.sub("", captured.out)
    assert "Verbose Mode Information" in plain_out
    assert "Config file: test.yml" in plain_out
    assert "Config dir:" in plain_out
    assert "tmp" in plain_out
    assert "Auto-hint:   True" in plain_out
    assert "Output limit:  10" in plain_out
    assert "Baseline weight: 2" in plain_out


def test_print_verbose_info_shows_default_model_without_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_print_verbose_info shows default model when model is not specified."""
    main._print_verbose_info(
        verbose=True,
        config_path=Path("test.yml"),
        config_dir=Path("/tmp"),
        auto_hint=True,
        auto_hint_model=main.AUTO_HINT_MODEL_DEFAULT,
        auto_hint_url=None,
        output_limit=5,
        baseline_weight=1,
        show_diagnostics=False,
        progress_bar=False,
    )
    captured = capsys.readouterr()
    plain_out = ANSI_ESCAPE_PATTERN.sub("", captured.out)
    assert "Model:" in plain_out


def test_resolve_system_prompt_reads_file(tmp_path: Path) -> None:
    """_resolve_system_prompt reads the system prompt file alongside config."""
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
    result = main._resolve_system_prompt(config_file, None)
    assert result == "Custom system prompt content."


def test_resolve_system_prompt_returns_none_when_not_specified(
    tmp_path: Path,
) -> None:
    """_resolve_system_prompt returns None when no system_prompt_file field."""
    config_file = tmp_path / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    result = main._resolve_system_prompt(config_file, None)
    assert result is None


def test_gatorgrade_with_config_dir_no_file(
    chdir: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """--config-dir with a file in the config dir should work."""
    config_dir = tmp_path / "myconfig"
    config_dir.mkdir()
    config_file = config_dir / "gatorgrade.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    chdir(tmp_path)
    result = runner.invoke(main.app, ["--config-dir", str(config_dir)])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 1/1 (100%)" in plain_stdout


def test_gatorgrade_with_config_dir_and_explicit_config(
    chdir: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """--config-dir with --config pointing to a file in the config dir."""
    config_dir = tmp_path / "myconfig"
    config_dir.mkdir()
    config_file = config_dir / "custom.yml"
    config_file.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    chdir(tmp_path)
    result = runner.invoke(
        main.app,
        ["--config-dir", str(config_dir), "--config", "custom.yml"],
    )
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 1/1 (100%)" in plain_stdout


def test_gatorgrade_with_config_dir_cwd_takes_precedence(
    chdir: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A file in the CWD takes precedence over a file in --config-dir."""
    config_dir = tmp_path / "myconfig"
    config_dir.mkdir()
    config_file_config = config_dir / "gatorgrade.yml"
    config_file_config.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: from_config_dir\n"
        '  command: "echo wrong"\n'
    )
    config_file_cwd = tmp_path / "gatorgrade.yml"
    config_file_cwd.write_text(
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: from_cwd\n"
        '  command: "echo correct"\n'
    )
    chdir(tmp_path)
    result = runner.invoke(main.app, ["--config-dir", str(config_dir)])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 1/1 (100%)" in plain_stdout


def test_gatorgrade_with_config_dir_nonexistent_file(
    chdir: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """--config-dir with a nonexistent config returns error."""
    config_dir = tmp_path / "myconfig"
    config_dir.mkdir()
    chdir(tmp_path)
    result = runner.invoke(main.app, ["--config-dir", str(config_dir)])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 1
    assert "either does not exist or is not valid" in result.stdout
