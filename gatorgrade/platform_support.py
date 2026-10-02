"""Platform support checks for GatorGrade features."""

import platform
import sys

# match the values used by the dependency marker in pyproject.toml
ARCH_X86_64 = "x86_64"
ARCH_WINDOWS_ARM64 = "ARM64"
SYSTEM_DARWIN = "darwin"
SYSTEM_WINDOWS = "win32"
PYTHON_3_10 = (3, 10)
PYTHON_3_14 = (3, 14)
PYTHON_VERSION_COMPONENTS = 2
# enable newer Python versions only after reviewing dependencies and loading
LOCAL_AUTO_HINT_PYTHON_MIN = (3, 10)
LOCAL_AUTO_HINT_PYTHON_MAX_EXCLUSIVE = (3, 15)
# torch 2.13 has no Intel macOS wheel, regardless of Python version
UNSUPPORTED_LOCAL_AUTO_HINT_PLATFORMS = frozenset(
    {(SYSTEM_DARWIN, ARCH_X86_64)}
)
# native Windows ARM64 Python 3.10 has no official interpreter build;
# torch 2.13 also lacks 3.14 wheels, with build-runner cost cited upstream:
# https://github.com/pytorch/pytorch/issues/161516
# review the Python bounds, both collections, and the TOML marker together
UNSUPPORTED_LOCAL_AUTO_HINT_ENVIRONMENTS = frozenset(
    {
        (SYSTEM_WINDOWS, ARCH_WINDOWS_ARM64, PYTHON_3_10),
        (SYSTEM_WINDOWS, ARCH_WINDOWS_ARM64, PYTHON_3_14),
    }
)


def supports_local_auto_hints() -> bool:
    """Return whether the current platform supports local auto-hints."""
    current_platform = (sys.platform, platform.machine())
    python_version = sys.version_info[:PYTHON_VERSION_COMPONENTS]
    current_environment = (*current_platform, python_version)
    return (
        LOCAL_AUTO_HINT_PYTHON_MIN
        <= python_version
        < LOCAL_AUTO_HINT_PYTHON_MAX_EXCLUSIVE
        and current_platform not in UNSUPPORTED_LOCAL_AUTO_HINT_PLATFORMS
        and current_environment not in UNSUPPORTED_LOCAL_AUTO_HINT_ENVIRONMENTS
    )
