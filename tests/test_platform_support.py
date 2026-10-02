"""Tests for platform-specific GatorGrade feature support."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import toml
from packaging.requirements import Requirement

from gatorgrade import platform_support

ARCH_ARM64 = "arm64"
SYSTEM_LINUX = "linux"
SUPPORTED_PLATFORM_CASES = (
    (platform_support.SYSTEM_DARWIN, ARCH_ARM64),
    (SYSTEM_LINUX, platform_support.ARCH_X86_64),
)
PYTHON_MAJOR = 3
PYTHON_MINORS = (10, 11, 12, 13, 14)
PYTHON_PATCHES = (0, 9)
OUT_OF_RANGE_PYTHON_MINORS = (9, 15, 16, 20)
SUPPORTED_PYTHON_VERSION = (3, 12)
PLATFORM_POLICY_CASES = (
    ("darwin", "x86_64", (False, False, False, False, False)),
    ("darwin", "arm64", (True, True, True, True, True)),
    ("win32", "AMD64", (True, True, True, True, True)),
    ("win32", "ARM64", (False, True, True, True, False)),
    ("linux", "x86_64", (True, True, True, True, True)),
    ("linux", "aarch64", (True, True, True, True, True)),
)
POLICY_MATRIX = tuple(
    (system, architecture, minor, supported)
    for system, architecture, outcomes in PLATFORM_POLICY_CASES
    for minor, supported in zip(PYTHON_MINORS, outcomes, strict=True)
) + tuple(
    (system, architecture, minor, False)
    for system, architecture, _ in PLATFORM_POLICY_CASES
    for minor in OUT_OF_RANGE_PYTHON_MINORS
)
POLICY_PARAMETERS = ("system", "architecture", "minor", "supported")
PYPROJECT_FILENAME = "pyproject.toml"
PROJECT_KEY = "project"
OPTIONAL_DEPENDENCIES_KEY = "optional-dependencies"
AUTO_HINT_EXTRA = "auto-hint"
TORCH_PACKAGE = "torch"
REMOTE_PACKAGE = "openai"
TRANSFORMERS_PACKAGE = "transformers"
SYS_PLATFORM_KEY = "sys_platform"
PLATFORM_MACHINE_KEY = "platform_machine"
PYTHON_VERSION_KEY = "python_version"
PYTHON_FULL_VERSION_KEY = "python_full_version"
EXTRA_KEY = "extra"
SYS_MODULE_ATTRIBUTE = "sys"
PLATFORM_MODULE_ATTRIBUTE = "platform"
FINAL_RELEASE_LEVEL = "final"
RELEASE_SERIAL = 0
TORCH_REQUIREMENT_COUNT = 1
FIRST_REQUIREMENT_INDEX = 0
FILE_ENCODING = "utf-8"


@pytest.fixture
def auto_hint_requirements() -> dict[str, Requirement]:
    """Read auto-hint requirements independently of runtime rules."""
    pyproject_path = (
        Path(__file__).resolve().parent.parent / PYPROJECT_FILENAME
    )
    data = toml.loads(pyproject_path.read_text(encoding=FILE_ENCODING))
    declarations = data[PROJECT_KEY][OPTIONAL_DEPENDENCIES_KEY][
        AUTO_HINT_EXTRA
    ]
    requirements = [Requirement(declaration) for declaration in declarations]
    torch_requirements = [
        requirement
        for requirement in requirements
        if requirement.name == TORCH_PACKAGE
    ]
    assert len(torch_requirements) == TORCH_REQUIREMENT_COUNT
    assert torch_requirements[FIRST_REQUIREMENT_INDEX].marker is not None
    return {requirement.name: requirement for requirement in requirements}


def test_supports_local_auto_hints_rejects_darwin_x86_64(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject local auto-hints on Darwin x86_64."""
    monkeypatch.setattr(
        platform_support.sys, "platform", platform_support.SYSTEM_DARWIN
    )
    monkeypatch.setattr(
        platform_support.platform,
        "machine",
        lambda: platform_support.ARCH_X86_64,
    )
    assert not platform_support.supports_local_auto_hints()


@pytest.mark.parametrize(("system", "architecture"), SUPPORTED_PLATFORM_CASES)
def test_supports_local_auto_hints_accepts_supported_platforms(
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    architecture: str,
) -> None:
    """Accept local auto-hints on supported platform combinations."""
    monkeypatch.setattr(
        platform_support,
        SYS_MODULE_ATTRIBUTE,
        SimpleNamespace(
            platform=system, version_info=SUPPORTED_PYTHON_VERSION
        ),
    )
    monkeypatch.setattr(
        platform_support.platform, "machine", lambda: architecture
    )
    assert platform_support.supports_local_auto_hints()


@pytest.mark.parametrize(POLICY_PARAMETERS, POLICY_MATRIX)
@pytest.mark.parametrize("patch", PYTHON_PATCHES)
def test_supports_local_auto_hints_matches_dependency_markers(  # noqa: PLR0913
    monkeypatch: pytest.MonkeyPatch,
    auto_hint_requirements: dict[str, Requirement],
    system: str,
    architecture: str,
    minor: int,
    supported: bool,
    patch: int,
) -> None:
    """Match independent policy outcomes and dependency markers."""
    version_info = (
        PYTHON_MAJOR,
        minor,
        patch,
        FINAL_RELEASE_LEVEL,
        RELEASE_SERIAL,
    )
    monkeypatch.setattr(
        platform_support,
        SYS_MODULE_ATTRIBUTE,
        SimpleNamespace(platform=system, version_info=version_info),
    )
    monkeypatch.setattr(
        platform_support,
        PLATFORM_MODULE_ATTRIBUTE,
        SimpleNamespace(machine=lambda: architecture),
    )
    marker_environment = {
        SYS_PLATFORM_KEY: system,
        PLATFORM_MACHINE_KEY: architecture,
        PYTHON_VERSION_KEY: f"{PYTHON_MAJOR}.{minor}",
        PYTHON_FULL_VERSION_KEY: f"{PYTHON_MAJOR}.{minor}.{patch}",
        EXTRA_KEY: AUTO_HINT_EXTRA,
    }
    torch_marker = auto_hint_requirements[TORCH_PACKAGE].marker
    assert torch_marker is not None
    assert platform_support.supports_local_auto_hints() is supported
    assert torch_marker.evaluate(marker_environment) is supported
    for package in (REMOTE_PACKAGE, TRANSFORMERS_PACKAGE):
        marker = auto_hint_requirements[package].marker
        assert marker is None or marker.evaluate(marker_environment)
