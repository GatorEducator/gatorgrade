"""System detection functions for GatorGrade.

Provides functions that detect platform information, operating system
release details, Python version details, and GatorGrader dependency
version. These are used by the --version and --verbose CLI options.

The detection functions separate platform-detection logic from the
main CLI module, making both easier to test and maintain.
"""

import importlib.metadata
import platform
import socket
from typing import Any

from rich.text import Text

from gatorgrade.hint.local_engine import (
    ENV_CACHE_DIR,
    platform_model_cache_dir,
)
from gatorgrade.input.parse_config import (
    ENV_CONFIG_DIR,
    _platform_config_dir,
)
from gatorgrade.version import GATORGRADE_VERSION

# constants for the platform information that is displayed
# by the --version option, mirroring the format used by uv; the
# arch and system combination is already unique across platforms
# (e.g., x86_64 + linux, arm64 + darwin, AMD64 + windows), so the
# vendor field from Rust's target triple is omitted because Python
# cannot determine it and it would always be "unknown"
UNKNOWN_PLATFORM = "unknown"
GATORGRADER_DEPENDENCY = "gatorgrader"

# constants related to platform details
LIBC_GNU = "gnu"
LIBC_MUSL = "musl"
LIBC_NONE = "none"
LIBC_MSVC = "msvc"
SYSTEM_DARWIN = "darwin"
SYSTEM_LINUX = "linux"
SYSTEM_WINDOWS = "windows"
_LIBC_BY_SYSTEM = {
    SYSTEM_DARWIN: LIBC_NONE,
    SYSTEM_WINDOWS: LIBC_MSVC,
}

# operating system display names for version output
OS_DARWIN = "Darwin"
OS_LINUX = "Linux"
OS_MACOS = "MacOS"
OS_WINDOWS = "Windows"

# program and language display names for version output
GATORGRADE_NAME = "Gatorgrade"
GATORGRADER_NAME = "GatorGrader"
PYTHON_NAME = "Python"

# packages included in the optional auto-hint extra; note
# that the reason for adding these to an extras package
# that is not instaslled by default is that they could
# take a long time to install and they are only needed
# if the person wants to use auto-hinting for failing checks;
# if the dependencies for extra packages change, then this
# variable should be updated to match the new set of packages
AUTO_HINT_PACKAGES = [
    "openai",
    "torch",
    "transformers",
]


def get_platform_info() -> str:
    """Get the platform information string for any platform.

    Mirrors the format used by uv: arch-os-libc with exactly
    three parts (e.g., x86_64-linux-gnu, arm64-darwin-none).

    Returns:
        A string in the format arch-os-libc.

    """
    arch = platform.machine() or UNKNOWN_PLATFORM
    system = platform.system().lower() or UNKNOWN_PLATFORM
    libc_name, _ = platform.libc_ver()
    if system == SYSTEM_LINUX:
        libc_lower = libc_name.lower()
        libc = (
            LIBC_MUSL
            if LIBC_MUSL in libc_lower
            else LIBC_GNU
            if libc_name
            else UNKNOWN_PLATFORM
        )
    elif system in _LIBC_BY_SYSTEM:
        libc = _LIBC_BY_SYSTEM[system]
    else:
        libc = UNKNOWN_PLATFORM
    return f"{arch}-{system}-{libc}"


def get_python_info() -> str:
    """Get the Python version, build, and compiler information string.

    Returns:
        A string such as
        "Python 3.12.0 (v3.12.0, Jan 1 2024, GCC 11.4)".

    """
    version = platform.python_version()
    build_no, build_date = platform.python_build()
    compiler = platform.python_compiler().strip()
    return f"{PYTHON_NAME} {version} ({build_no}, {build_date}, {compiler})"


def get_gatorgrade_info() -> str:
    """Get the parenthetic GatorGrade info string with the GatorGrader version.

    Uses importlib.metadata to get the installed version of the
    gatorgrader dependency.

    Returns:
        A string such as "GatorGrader 1.2.3".

    """
    gatorgrader_version = importlib.metadata.version(GATORGRADER_DEPENDENCY)
    return f"{GATORGRADER_NAME} {gatorgrader_version}"


def get_os_release() -> str:
    """Get the operating system release string for Linux, macOS, or Windows.

    Returns:
        A string such as "MacOS 14.5 (arm64-darwin-none)" or an
        empty string if the release cannot be determined.

    """
    parenthetic_platform_string = f"({get_platform_info()})"
    if platform.system() == OS_LINUX:
        kernel = platform.release()
        if kernel:
            return f"{OS_LINUX} {kernel} {parenthetic_platform_string}"
    elif platform.system() == OS_DARWIN:
        release, _, _ = platform.mac_ver()
        if release:
            return f"{OS_MACOS} {release} {parenthetic_platform_string}"
    elif platform.system() == OS_WINDOWS:
        release, _, _, _ = platform.win32_ver()
        if release:
            return f"{OS_WINDOWS} {release} {parenthetic_platform_string}"
    return ""


def _check_auto_hint_installed() -> Text:
    """Check if the optional auto-hint extra is installed.

    Attempts to import each package in the auto-hint extra. Returns a
    Rich Text showing which packages are present and which are missing.

    Returns:
        A Rich Text object suitable for printing.

    """
    result = Text()
    result.append("Auto-hint extra: ")
    missing: list[str] = []
    present: list[str] = []
    for pkg in AUTO_HINT_PACKAGES:
        try:
            importlib.import_module(pkg)
            present.append(pkg)
        except (ImportError, OSError):
            missing.append(pkg)
    if not missing:
        result.append("installed", style="green")
    else:
        result.append("not installed", style="bright_red")
        result.append(f" ({', '.join(missing)})", style="dim")
    return result


def print_version_info(console: Any) -> None:
    """Print gatorgrade version, platform, and environment information.

    Used by both --version and --verbose to display diagnostic
    information about the current environment.

    Args:
        console: A Rich Console instance for printing output.

    """
    console.print(
        f"{GATORGRADE_NAME} {GATORGRADE_VERSION} ({get_gatorgrade_info()})"
    )
    # show whether the optional auto-hint extra is installed right
    # after the version line so users can quickly diagnose whether
    # the extra is available
    auto_hint_status = _check_auto_hint_installed()
    console.print(auto_hint_status)
    console.print(get_python_info())
    os_release = get_os_release()
    if os_release:
        console.print(os_release)
    # show the path-related environment variables and resolved
    # defaults so users know which paths affect gatorgrade
    import os  # noqa: PLC0415

    models_override = os.environ.get(ENV_CACHE_DIR)
    config_override = os.environ.get(ENV_CONFIG_DIR)
    models_default = str(platform_model_cache_dir())
    config_default = str(_platform_config_dir())

    def _fmt_env(name: str, override: str | None, default: str) -> Text:
        """Format a single environment variable line for display."""
        result = Text()
        result.append(f"{name}=")
        result.append(
            override if override else "(unset)",
            style="" if override else "dim",
        )
        result.append(
            f" (default: {default})",
            style="dim",
        )
        return result

    for env_line in [
        _fmt_env(ENV_CACHE_DIR, models_override, models_default),
        _fmt_env(ENV_CONFIG_DIR, config_override, config_default),
    ]:
        console.print(env_line)
    # show the computer's hostname for debugging
    # network-related problems; this is a best-effort
    # call and will not cause a crash if it fails
    hostname = socket.gethostname()
    console.print(f"Hostname: {hostname}")
