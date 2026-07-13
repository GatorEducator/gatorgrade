"""Tests for the main file of the project."""

import builtins
import io
import os
import re
from pathlib import Path
from typing import Any, Callable, Generator, List

import pytest
from typer.testing import CliRunner

from gatorgrade import detect, main

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


def test_gatorgrade_with_invalid_due_date_format(
    chdir: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test gatorgrade warns about an unparseable due_date in the config."""
    config_file = tmp_path / "bad_due_date.yml"
    config_file.write_text(
        'due_date: "not-a-date"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    chdir(tmp_path)
    result = runner.invoke(main.app, ["--config", "bad_due_date.yml"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0


def test_gatorgrade_with_multiple_due_date_aliases(
    chdir: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test gatorgrade warns when both due_date and duedate are present."""
    config_file = tmp_path / "multi_due_date.yml"
    config_file.write_text(
        'due_date: "2026-12-15"\n'
        'duedate: "2026-12-16"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        '  command: "echo hello"\n'
    )
    chdir(tmp_path)
    result = runner.invoke(main.app, ["--config", "multi_due_date.yml"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0


def test_gatorgrade_with_auto_hint_model_requires_auto_hint(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Using --auto-hint-model without --auto-hint exits with an error."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--auto-hint-model", "custom/model"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_auto_hint_creates_engine(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Using --auto-hint creates an engine and runs checks."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--auto-hint"])
    capsys.readouterr()
    assert result.exit_code == 0


def test_gatorgrade_with_auto_hint_url_requires_auto_hint(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Using --auto-hint-url without --auto-hint exits with an error."""
    chdir("tests/test_assignment")
    result = runner.invoke(
        main.app, ["--auto-hint-url", "http://localhost:4000"]
    )
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_auto_hint_api_key_requires_auto_hint(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Using --auto-hint-api-key without --auto-hint exits with an error."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--auto-hint-api-key", "sk-test-key"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_auto_hint_api_key_requires_url(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Using --auto-hint-api-key without --auto-hint-url exits with an error."""
    chdir("tests/test_assignment")
    result = runner.invoke(
        main.app,
        ["--auto-hint", "--auto-hint-api-key", "sk-test-key"],
    )
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_output_limit_zero(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that output limit of zero is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--output-limit", "0"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_output_limit_negative(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that negative output limit is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--output-limit", "-5"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_output_limit_one(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that output limit of one is accepted."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--output-limit", "1"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0


def test_gatorgrade_with_output_limit_valid(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that a valid output limit is accepted."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--output-limit", "5"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 3/3 (100%)" in plain_stdout
    assert "- Points: 3/3 (100%)" in plain_stdout


def test_gatorgrade_with_baseline_weight_zero(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that baseline weight of zero is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--baseline-weight", "0"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_baseline_weight_negative(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that negative baseline weight is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--baseline-weight", "-2"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_baseline_weight_default(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that baseline weight of 1 is accepted and shows correct points."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--baseline-weight", "1"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Points: 3/3 (100%)" in plain_stdout


def test_gatorgrade_with_baseline_weight_custom(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that a custom baseline weight affects the points calculation."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--baseline-weight", "5"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Points: 15/15 (100%)" in plain_stdout


def test_gatorgrade_with_show_diagnostics_default(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that show diagnostics is the default and runs successfully."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, [])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0


def test_gatorgrade_with_show_diagnostics_explicit(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that --show-diagnostics flag is accepted."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--show-diagnostics"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 3/3 (100%)" in plain_stdout
    assert "- Points: 3/3 (100%)" in plain_stdout


def test_gatorgrade_with_no_show_diagnostics(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that --no-show-diagnostics hides diagnostic output."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--no-show-diagnostics"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 3/3 (100%)" in plain_stdout
    assert "- Points: 3/3 (100%)" in plain_stdout


def test_gatorgrade_with_report_option(
    chdir: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade works with report option."""
    chdir("tests/test_assignment")
    report_file = tmp_path / "report.json"
    result = runner.invoke(
        main.app, ["--report", "file", "json", str(report_file)]
    )
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    assert report_file.exists()


def test_gatorgrade_with_report_invalid_destination(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that an invalid report destination is rejected up front."""
    chdir("tests/test_assignment")
    result = runner.invoke(
        main.app, ["--report", "FILe111", "json", "report.json"]
    )
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_report_invalid_type(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that an invalid report type is rejected up front."""
    chdir("tests/test_assignment")
    result = runner.invoke(
        main.app, ["--report", "file", "html", "report.json"]
    )
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_report_uppercase_valid(
    chdir: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that uppercase FILE/JSON is accepted."""
    chdir("tests/test_assignment")
    report_file = tmp_path / "report.json"
    result = runner.invoke(
        main.app, ["--report", "FILE", "JSON", str(report_file)]
    )
    capsys.readouterr()
    assert result.exit_code == 0
    assert report_file.exists()


def test_gatorgrade_with_report_invalid_file_path(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that a report file path with a non-existent directory is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(
        main.app,
        ["--report", "file", "json", "nonexistent_dir/report.json"],
    )
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_report_env_invalid_name(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that an invalid env var name in --report ENV is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--report", "ENV", "json", "BAD NAME!"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_github_env_invalid_format(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that an invalid github-env format is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--github-env", "html", "JSON_REPORT"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_github_env_valid_json(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that valid github-env format passes validation."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--github-env", "json", "JSON_REPORT"])
    capsys.readouterr()
    assert result.exit_code == 0


def test_gatorgrade_with_github_env_invalid_name(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that an invalid github-env key name is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--github-env", "json", "1invalid"])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_invalid_config_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test that gatorgrade exits with error when config file is not valid."""
    config_file = tmp_path / "invalid_main_test.yml"
    config_file.write_text("this is not valid yaml: [")
    result = runner.invoke(main.app, ["--config", str(config_file)])
    capsys.readouterr()
    assert result.exit_code != 0


def test_gatorgrade_with_subcommand() -> None:
    """Test that gatorgrade skips core logic if a subcommand is invoked."""
    result = runner.invoke(main.app, ["nonexistent-command"])
    assert result.exit_code != 0


def test_gatorgrade_with_custom_config_name(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade works with custom config file name."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--config", "gatorgrade.yml"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 3/3 (100%)" in plain_stdout
    assert "- Points: 3/3 (100%)" in plain_stdout


def test_gatorgrade_with_no_status_bar(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade works with no status bar."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--no-progress-bar"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 3/3 (100%)" in plain_stdout
    assert "- Points: 3/3 (100%)" in plain_stdout


def test_gatorgrade_with_progress_bar_default(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade shows progress bar by default."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, [])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "- Checks: 3/3 (100%)" in plain_stdout
    assert "- Points: 3/3 (100%)" in plain_stdout


def test_gatorgrade_with_version_flag_on_macos(
    chdir: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the version output includes the macOS release on Darwin systems."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        detect.platform,
        "mac_ver",
        lambda: ("14.5", (("", "", ""), ""), "arm64"),
    )
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--version"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "MacOS 14.5" in plain_stdout


def test_gatorgrade_with_version_flag_on_windows(
    chdir: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the version output includes the Windows release on Windows systems."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Windows")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        detect.platform, "win32_ver", lambda: ("10", "10.0.19041", "", "")
    )
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--version"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "Windows 10" in plain_stdout


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
