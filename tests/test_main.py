"""Tests for the main file of the project."""

import builtins
import io
import os
import platform
import re
from pathlib import Path
from typing import Any, Callable, Generator, List
from unittest.mock import patch

import pytest
from click import BadParameter
from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner

from gatorgrade import main
from gatorgrade.hint.remote_engine import RemoteHintEngine

runner = CliRunner()

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
PLATFORM_INFO_PARTS = 3


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
    assert "Fix these error(s) before running gatorgrade." in result.stdout


def test_gatorgrade_with_invalid_config_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that gatorgrade exits with error when config file is not valid."""
    invalid_config = Path("invalid_main_test.yml")
    invalid_config.write_text("this is not valid yaml: [")
    result = runner.invoke(main.app, ["--config", "invalid_main_test.yml"])
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


def test_gatorgrade_with_invalid_due_date_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test gatorgrade warns about an unparseable due_date in the config."""
    config = Path("bad_due_date.yml")
    config.write_text(
        'due_date: "not-a-date"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = runner.invoke(main.app, ["--config", "bad_due_date.yml"])
    capsys.readouterr()
    assert result.exit_code == 0
    assert "Invalid Due Date Configuration" in result.output


def test_gatorgrade_with_multiple_due_date_aliases(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test gatorgrade warns when multiple due date fields are present."""
    config = Path("multi_due_date.yml")
    config.write_text(
        'due_date: "2026-12-15"\n'
        'due: "2026-12-20"\n'
        "setup: |\n"
        "  echo setup\n"
        "---\n"
        "- description: test\n"
        "  command: echo hello\n"
    )
    result = runner.invoke(main.app, ["--config", "multi_due_date.yml"])
    capsys.readouterr()
    assert result.exit_code == 0
    assert "Multiple Due Date Fields" in result.output


def test_gatorgrade_with_report_env_invalid_name(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that an invalid env var name in --report ENV is rejected."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--report", "ENV", "json", "BAD NAME!"])
    capsys.readouterr()
    assert result.exit_code != 0


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


def test_gatorgrade_with_version_flag(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade displays the version when --version is provided."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--version"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    # strip ANSI escape codes that Rich may add when stdout is a TTY
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    # the output should include the program name, version, and platform info
    assert f"gatorgrade {main.GATORGRADE_VERSION} (" in plain_stdout
    # the output should also include the python version
    assert "Python" in plain_stdout
    # the output should include the python version number
    assert platform.python_version() in plain_stdout


def test_gatorgrade_with_version_flag_on_macos(
    chdir: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the version output includes the macOS release on Darwin systems."""
    monkeypatch.setattr(main.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(main.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        main.platform, "mac_ver", lambda: ("14.5", (("", "", ""), ""), "arm64")
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
    monkeypatch.setattr(main.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(main.platform, "system", lambda: "Windows")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        main.platform, "win32_ver", lambda: ("10", "10.0.19041", "", "")
    )
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--version"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    plain_stdout = ANSI_ESCAPE_PATTERN.sub("", result.stdout)
    assert "Windows 10" in plain_stdout


def test_gatorgrade_version_callback_with_false() -> None:
    """Test that the version callback does not exit when value is False."""
    main._version_callback(False)


def test_gatorgrade_get_platform_info_format() -> None:
    """Test that the platform info function returns a uv-like format string."""
    platform_info = main._get_platform_info()
    # the format is arch-os-libc with exactly three parts
    parts = platform_info.split("-")
    assert len(parts) == PLATFORM_INFO_PARTS
    # no part should be empty
    assert all(parts)
    # the second part is the operating system
    assert parts[1] == platform.system().lower()


def test_gatorgrade_get_platform_info_linux_musl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Linux system with musl libc."""
    monkeypatch.setattr(main.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(main.platform, "system", lambda: "Linux")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("musl", "1.2"))
    assert main._get_platform_info() == "x86_64-linux-musl"


def test_gatorgrade_get_platform_info_linux_empty_libc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Linux system with unknown libc."""
    monkeypatch.setattr(main.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(main.platform, "system", lambda: "Linux")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    assert main._get_platform_info() == "x86_64-linux-unknown"


def test_gatorgrade_get_platform_info_darwin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Darwin (macOS) system."""
    monkeypatch.setattr(main.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(main.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    assert main._get_platform_info() == "arm64-darwin-none"


def test_gatorgrade_get_platform_info_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Windows system."""
    monkeypatch.setattr(main.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(main.platform, "system", lambda: "Windows")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    assert main._get_platform_info() == "AMD64-windows-msvc"


def test_gatorgrade_get_platform_info_unknown_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on an unknown system."""
    monkeypatch.setattr(main.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(main.platform, "system", lambda: "Plan9")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    assert main._get_platform_info() == "x86_64-plan9-unknown"


def test_gatorgrade_get_platform_info_fallback_arch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string when machine returns an empty value."""
    monkeypatch.setattr(main.platform, "machine", lambda: "")
    monkeypatch.setattr(main.platform, "system", lambda: "Linux")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("glibc", "2.40"))
    assert main._get_platform_info() == "unknown-linux-gnu"


def test_gatorgrade_get_gatorgrade_info_format() -> None:
    """Test the gatorgrade info string contains the GatorGrader version."""
    gatorgrade_info = main._get_gatorgrade_info()
    # the format is GatorGrader {version}
    assert gatorgrade_info.startswith("GatorGrader ")
    # it should contain a version number
    assert any(char.isdigit() for char in gatorgrade_info)


def test_gatorgrade_get_python_info_format() -> None:
    """Test the python info string contains the expected fields."""
    python_info = main._get_python_info()
    # the format is Python {version} ({build_no}, {build_date}, {compiler})
    assert python_info.startswith("Python ")
    # it should contain a version in parentheses
    assert "(" in python_info
    assert python_info.endswith(")")


def test_gatorgrade_get_python_info_uses_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the python info string uses the platform module functions."""
    monkeypatch.setattr(main.platform, "python_version", lambda: "3.12.0")
    monkeypatch.setattr(
        main.platform, "python_build", lambda: ("v3.12.0", "Jan 1 2024")
    )
    monkeypatch.setattr(main.platform, "python_compiler", lambda: "GCC 11.4 ")
    assert (
        main._get_python_info()
        == "Python 3.12.0 (v3.12.0, Jan 1 2024, GCC 11.4)"
    )


def test_gatorgrade_get_os_release_darwin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on a Darwin (macOS) system."""
    monkeypatch.setattr(main.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(main.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        main.platform, "mac_ver", lambda: ("14.5", (("", "", ""), ""), "arm64")
    )
    assert main._get_os_release() == "MacOS 14.5 (arm64-darwin-none)"


def test_gatorgrade_get_os_release_darwin_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on macOS when no release is available."""
    monkeypatch.setattr(main.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        main.platform, "mac_ver", lambda: ("", (("", "", ""), ""), "")
    )
    assert main._get_os_release() == ""


def test_gatorgrade_get_os_release_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on a Windows system."""
    monkeypatch.setattr(main.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(main.platform, "system", lambda: "Windows")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        main.platform, "win32_ver", lambda: ("10", "10.0.19041", "", "")
    )
    assert main._get_os_release() == "Windows 10 (AMD64-windows-msvc)"


def test_gatorgrade_get_os_release_windows_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on Windows when no release is available."""
    monkeypatch.setattr(main.platform, "system", lambda: "Windows")
    monkeypatch.setattr(main.platform, "win32_ver", lambda: ("", "", "", ""))
    assert main._get_os_release() == ""


def test_gatorgrade_get_os_release_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on Linux uses the kernel version."""
    monkeypatch.setattr(main.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(main.platform, "system", lambda: "Linux")
    monkeypatch.setattr(main.platform, "libc_ver", lambda: ("glibc", "2.40"))
    monkeypatch.setattr(main.platform, "release", lambda: "6.18.17")
    assert main._get_os_release() == "Linux 6.18.17 (x86_64-linux-gnu)"


def test_gatorgrade_get_os_release_linux_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on Linux when no kernel is available."""
    monkeypatch.setattr(main.platform, "system", lambda: "Linux")
    monkeypatch.setattr(main.platform, "release", lambda: "")
    assert main._get_os_release() == ""


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


@pytest.mark.propertybased
@given(st.integers(min_value=1, max_value=1000))
def test_validate_output_limit_valid_property(value: int) -> None:
    """Property: positive ints pass through validation unchanged."""
    result = main._validate_output_limit(value)
    assert result == value


@pytest.mark.propertybased
@given(st.integers(max_value=0))
def test_validate_output_limit_invalid_property(value: int) -> None:
    """Property: non-positive ints cause BadParameter."""
    with pytest.raises(BadParameter):
        main._validate_output_limit(value)


@pytest.mark.propertybased
@given(st.integers(min_value=1, max_value=1000))
def test_validate_baseline_weight_valid_property(value: int) -> None:
    """Property: positive ints pass through validation unchanged."""
    result = main._validate_baseline_weight(value)
    assert result == value


@pytest.mark.propertybased
@given(st.integers(max_value=0))
def test_validate_baseline_weight_invalid_property(value: int) -> None:
    """Property: non-positive ints cause BadParameter."""
    with pytest.raises(BadParameter):
        main._validate_baseline_weight(value)


@pytest.mark.propertybased
@given(st.data())
def test_platform_info_format_property(_: st.DataObject) -> None:
    """Property: platform info is a non-empty string with at least one dash."""
    info = main._get_platform_info()
    assert isinstance(info, str)
    assert len(info) > 0
    assert "-" in info


@pytest.mark.propertybased
@given(st.data())
def test_python_info_starts_with_python_property(_: st.DataObject) -> None:
    """Property: python info starts with 'Python'."""
    info = main._get_python_info()
    assert info.startswith("Python")


@pytest.mark.propertybased
@given(st.data())
def test_gatorgrade_info_contains_gatorgrader_property(
    _: st.DataObject,
) -> None:
    """Property: gatorgrade info contains 'GatorGrader'."""
    info = main._get_gatorgrade_info()
    assert "GatorGrader" in info


@pytest.mark.propertybased
@given(st.data())
def test_os_release_format_property(_: st.DataObject) -> None:
    """Property: os release is non-empty with parens or empty string."""
    info = main._get_os_release()
    assert isinstance(info, str)
    if info:
        assert "(" in info and ")" in info


@pytest.mark.propertybased
@given(st.from_regex(r"^[A-Za-z_][A-Za-z0-9_]*$"))
def test_valid_env_var_names_match_property(value: str) -> None:
    """Property: valid env var names match the VALID_ENV_VAR_NAME pattern."""
    assert main.VALID_ENV_VAR_NAME.match(value) is not None


@pytest.mark.propertybased
@given(
    st.one_of(
        # names starting with a digit are invalid
        st.from_regex(r"^[0-9].*$", fullmatch=True),
        # names containing spaces are invalid
        st.from_regex(r"^.*\\s+.*$", fullmatch=True),
        # names containing special characters (not underscore) are invalid
        st.from_regex(r"^.*[^A-Za-z0-9_].*$", fullmatch=True),
    )
)
def test_invalid_env_var_names_do_not_match_property(value: str) -> None:
    """Property: invalid env var names do not match the VALID_ENV_VAR_NAME pattern."""
    assert main.VALID_ENV_VAR_NAME.match(value) is None


def test_validate_report_passes_for_invalid_destination() -> None:
    """_validate_report rejects an invalid destination."""
    with pytest.raises(BadParameter, match="First report argument"):
        main._validate_report(("html", "json", "report.json"))


def test_validate_report_passes_for_invalid_type() -> None:
    """_validate_report rejects an invalid report type."""
    with pytest.raises(BadParameter, match="Second report argument"):
        main._validate_report(("file", "html", "report.json"))


def test_validate_github_env_passes_for_invalid_format() -> None:
    """_validate_github_env rejects an invalid format."""
    with pytest.raises(BadParameter, match="First github-env argument"):
        main._validate_github_env(("html", "JSON_REPORT"))


def test_validate_github_env_passes_for_invalid_name() -> None:
    """_validate_github_env rejects an invalid environment variable name."""
    with pytest.raises(BadParameter, match="Second github-env argument"):
        main._validate_github_env(("json", "1invalid!"))


def test_validate_github_env_passes_for_none_values() -> None:
    """_validate_github_env passes through None values."""
    result = main._validate_github_env((None, None))
    assert result == (None, None)


def test_validate_report_passes_for_none_values() -> None:
    """_validate_report passes through None values."""
    result = main._validate_report((None, None, None))
    assert result == (None, None, None)


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
    # should succeed (engine creation failure is caught by the except
    # clause, but the engine is optional)
    assert result.exit_code == 0


@pytest.mark.autohint
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
    assert isinstance(engine, main.RemoteEngineAdapter)


class TestRemoteEngineAdapter:
    """Direct tests for RemoteEngineAdapter."""

    @pytest.mark.autohint
    def test_is_loaded_returns_true(self) -> None:
        """is_loaded always returns True."""
        remote = RemoteHintEngine(base_url="http://test.url:4160")
        adapter = main.RemoteEngineAdapter(remote, "test-model")
        assert adapter.is_loaded is True

    @pytest.mark.autohint
    def test_model_id_returns_remote_prefix(self) -> None:
        """model_id returns the model identifier with remote: prefix."""
        remote = RemoteHintEngine(base_url="http://test.url:4160")
        adapter = main.RemoteEngineAdapter(remote, "Qwen-3.6-35B-A3B")
        assert adapter.model_id == "remote:Qwen-3.6-35B-A3B"

    @pytest.mark.autohint
    def test_ensure_loaded_is_noop(self) -> None:
        """ensure_loaded does not raise."""
        remote = RemoteHintEngine(base_url="http://test.url:4160")
        adapter = main.RemoteEngineAdapter(remote, "test-model")
        adapter.ensure_loaded()  # must not raise

    @pytest.mark.autohint
    def test_generate_hint_with_mocked_remote(self) -> None:
        """generate_hint delegates to the remote engine."""
        remote = RemoteHintEngine(base_url="http://test.url:4160")
        adapter = main.RemoteEngineAdapter(remote, "test-model")
        with patch(
            "gatorgrade.hint.remote_engine.RemoteHintEngine.generate_hint",
            return_value=("A useful hint.", False),
        ):
            hint, is_low = adapter.generate_hint(
                description="test", diagnostic="error"
            )
        assert hint == "A useful hint."
        assert not is_low
