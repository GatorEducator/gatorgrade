"""Tests for the gatorgrade.detect module."""

import platform as platform_module
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from gatorgrade import detect

ANSI_ESCAPE_PATTERN = __import__("re").compile(r"\x1b\[[0-9;]*m")

PLATFORM_INFO_PARTS = 3


def test_print_version_info_outputs_expected_info() -> None:
    """Test that print_version_info includes version, Python, and env info."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True)
    detect.print_version_info(console)
    plain_out = ANSI_ESCAPE_PATTERN.sub("", buffer.getvalue())
    assert "Gatorgrade" in plain_out
    assert "Python" in plain_out
    assert "GATORGRADE_MODELS_DIR" in plain_out
    assert "GATORGRADE_CONFIG_DIR" in plain_out


def test_gatorgrade_get_platform_info_format() -> None:
    """Test that the platform info function returns a uv-like format string."""
    platform_info = detect.get_platform_info()
    parts = platform_info.split("-")
    assert len(parts) == PLATFORM_INFO_PARTS
    assert all(parts)
    assert parts[1] == platform_module.system().lower()


def test_gatorgrade_get_platform_info_linux_musl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Linux system with musl libc."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Linux")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("musl", "1.2"))
    assert detect.get_platform_info() == "x86_64-linux-musl"


def test_gatorgrade_get_platform_info_linux_empty_libc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Linux system with unknown libc."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Linux")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    assert detect.get_platform_info() == "x86_64-linux-unknown"


def test_gatorgrade_get_platform_info_darwin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Darwin (macOS) system."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    assert detect.get_platform_info() == "arm64-darwin-none"


def test_gatorgrade_get_platform_info_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on a Windows system."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Windows")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    assert detect.get_platform_info() == "AMD64-windows-msvc"


def test_gatorgrade_get_platform_info_unknown_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string on an unknown system."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Plan9")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    assert detect.get_platform_info() == "x86_64-plan9-unknown"


def test_gatorgrade_get_platform_info_fallback_arch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the platform info string when machine returns an empty value."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "")
    monkeypatch.setattr(detect.platform, "system", lambda: "Linux")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("glibc", "2.40"))
    assert detect.get_platform_info() == "unknown-linux-gnu"


def test_gatorgrade_get_gatorgrade_info_format() -> None:
    """Test the gatorgrade info string contains the GatorGrader version."""
    gatorgrade_info = detect.get_gatorgrade_info()
    assert gatorgrade_info.startswith("GatorGrader ")
    assert any(char.isdigit() for char in gatorgrade_info)


def test_gatorgrade_get_python_info_format() -> None:
    """Test the python info string contains the expected fields."""
    python_info = detect.get_python_info()
    assert python_info.startswith("Python ")
    assert "(" in python_info
    assert python_info.endswith(")")


def test_gatorgrade_get_python_info_uses_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the python info string uses the platform module functions."""
    monkeypatch.setattr(detect.platform, "python_version", lambda: "3.12.0")
    monkeypatch.setattr(
        detect.platform, "python_build", lambda: ("v3.12.0", "Jan 1 2024")
    )
    monkeypatch.setattr(
        detect.platform, "python_compiler", lambda: "GCC 11.4 "
    )
    assert (
        detect.get_python_info()
        == "Python 3.12.0 (v3.12.0, Jan 1 2024, GCC 11.4)"
    )


def test_gatorgrade_get_os_release_darwin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on a Darwin (macOS) system."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        detect.platform,
        "mac_ver",
        lambda: ("14.5", (("", "", ""), ""), "arm64"),
    )
    assert detect.get_os_release() == "MacOS 14.5 (arm64-darwin-none)"


def test_gatorgrade_get_os_release_darwin_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on macOS when no release is available."""
    monkeypatch.setattr(detect.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        detect.platform, "mac_ver", lambda: ("", (("", "", ""), ""), "")
    )
    assert detect.get_os_release() == ""


def test_gatorgrade_get_os_release_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on a Windows system."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Windows")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("", ""))
    monkeypatch.setattr(
        detect.platform,
        "win32_ver",
        lambda: ("10", "10.0.19041", "", ""),
    )
    assert detect.get_os_release() == "Windows 10 (AMD64-windows-msvc)"


def test_gatorgrade_get_os_release_windows_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on Windows when no release is available."""
    monkeypatch.setattr(detect.platform, "system", lambda: "Windows")
    monkeypatch.setattr(detect.platform, "win32_ver", lambda: ("", "", "", ""))
    assert detect.get_os_release() == ""


def test_gatorgrade_get_os_release_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on Linux uses the kernel version."""
    monkeypatch.setattr(detect.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(detect.platform, "system", lambda: "Linux")
    monkeypatch.setattr(detect.platform, "libc_ver", lambda: ("glibc", "2.40"))
    monkeypatch.setattr(detect.platform, "release", lambda: "6.18.17")
    assert detect.get_os_release() == "Linux 6.18.17 (x86_64-linux-gnu)"


def test_gatorgrade_get_os_release_linux_no_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the os release string on Linux when no kernel is available."""
    monkeypatch.setattr(detect.platform, "system", lambda: "Linux")
    monkeypatch.setattr(detect.platform, "release", lambda: "")
    assert detect.get_os_release() == ""


def test__check_auto_hint_installed_returns_text() -> None:
    """_check_auto_hint_installed returns a Text object with expected content."""
    result = detect._check_auto_hint_installed()
    result_str = str(result)
    assert "Auto-hint extra:" in result_str
    # the status is either installed or not installed
    assert "installed" in result_str or "not installed" in result_str


def test_platform_model_cache_dir_returns_path() -> None:
    """platform_model_cache_dir returns a Path with expected properties."""
    cache_dir = detect.platform_model_cache_dir()
    assert isinstance(cache_dir, Path)
    assert cache_dir.name == "models"
    assert "gatorgrade" in str(cache_dir).lower()
