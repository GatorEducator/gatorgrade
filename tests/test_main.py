"""Tests for the main file of the project."""

import builtins
import io
import os
import platform
import re
from pathlib import Path
from typing import Any, Callable, Generator, List

import pytest
from typer.testing import CliRunner

from gatorgrade import main

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
        os.remove(file)


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
                ("Passed 3/3 (100%) of checks", 1),
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
    for output, freq in expected_output_and_freqs:
        assert result.stdout.count(output) == freq


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
    assert "Exiting now!" in result.stdout


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
    assert "Passed 3/3 (100%) of checks" in result.stdout


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


def test_gatorgrade_with_status_bar(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade works with status bar enabled."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--status-bar"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    assert "Passed 3/3 (100%) of checks" in result.stdout


def test_gatorgrade_with_no_status_bar(
    chdir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that gatorgrade works with no status bar."""
    chdir("tests/test_assignment")
    result = runner.invoke(main.app, ["--no-status-bar"])
    capsys.readouterr()
    print(result.stdout)  # noqa: T201
    assert result.exit_code == 0
    assert "Passed 3/3 (100%) of checks" in result.stdout


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
    # the output should include the linux kernel release
    assert "Linux" in plain_stdout


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
