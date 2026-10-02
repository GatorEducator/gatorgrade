"""Test version-specific exclusions through real auto-hint support callers."""

import builtins
import sys
from collections.abc import Callable
from functools import partial
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from rich.console import Console

from gatorgrade import detect, engine, platform_support
from gatorgrade.hint.local_engine import (
    UNSUPPORTED_LOCAL_AUTO_HINT_MESSAGE,
    LocalAutoHintEngine,
    UnsupportedLocalAutoHintPlatformError,
)

EXCLUDED_ENVIRONMENTS = (
    ("win32", "ARM64", (3, 10)),
    ("win32", "ARM64", (3, 14)),
    ("darwin", "x86_64", (3, 15)),
    ("darwin", "arm64", (3, 15)),
    ("win32", "AMD64", (3, 15)),
    ("win32", "ARM64", (3, 15)),
    ("linux", "x86_64", (3, 15)),
    ("linux", "aarch64", (3, 15)),
)
SYS_MODULE_ATTRIBUTE = "sys"
PLATFORM_MODULE_ATTRIBUTE = "platform"
LOCAL_ENGINE_ATTRIBUTE = "LocalAutoHintEngine"
REMOTE_FACTORY_ATTRIBUTE = "try_create_remote_engine"
IMPORT_ATTRIBUTE = "__import__"
DISTRIBUTION_ATTRIBUTE = "distribution"
CONFIG_FILENAME = "gatorgrade.yml"
MODEL_ID = "custom/model"
REMOTE_URL = "http://localhost:9999"
REMOTE_PACKAGE = "openai"
LOCAL_PACKAGES = frozenset({"torch", "transformers"})
IMPORT_SEPARATOR = "."
LOCAL_FACTORY_ERROR = (
    "An excluded environment must not construct local engines."
)
LOCAL_IMPORT_ERROR = "The platform guard must run before local imports."
FACTORY_SCENARIOS = ("local-only", "remote-success", "remote-missing")
LOCAL_ONLY_SCENARIO = "local-only"
REMOTE_SUCCESS_SCENARIO = "remote-success"
SPACE = " "
FIRST_COMPONENT_INDEX = 0


def reject_local_engine(**kwargs: Any) -> None:
    """Fail if the factory constructs a local engine."""
    pytest.fail(LOCAL_FACTORY_ERROR)


def reject_local_import(
    original_import: Callable[..., Any],
    name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Fail if a local inference dependency is imported."""
    if name.split(IMPORT_SEPARATOR)[FIRST_COMPONENT_INDEX] in LOCAL_PACKAGES:
        pytest.fail(LOCAL_IMPORT_ERROR)
    return original_import(name, *args, **kwargs)


def record_distribution(checked_packages: list[str], package: str) -> object:
    """Record each dependency without importing optional packages."""
    checked_packages.append(package)
    return object()


@pytest.fixture(params=EXCLUDED_ENVIRONMENTS)
def excluded_environment(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Select an excluded environment without changing global sys."""
    system, architecture, version_info = request.param
    monkeypatch.setattr(
        platform_support,
        SYS_MODULE_ATTRIBUTE,
        SimpleNamespace(
            platform=system,
            version_info=version_info,
        ),
    )
    monkeypatch.setattr(
        platform_support,
        PLATFORM_MODULE_ATTRIBUTE,
        SimpleNamespace(machine=lambda: architecture),
    )
    assert not platform_support.supports_local_auto_hints()


@pytest.mark.parametrize("scenario", FACTORY_SCENARIOS)
def test_excluded_environment_routes_engines(
    excluded_environment: None,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
) -> None:
    """Warn for unavailable engines and keep successful remote use quiet."""
    console_output = StringIO()
    console = Console(file=console_output, color_system=None)
    remote_engine = object()
    monkeypatch.setattr(engine, LOCAL_ENGINE_ATTRIBUTE, reject_local_engine)
    if scenario == REMOTE_SUCCESS_SCENARIO:
        monkeypatch.setattr(
            engine,
            REMOTE_FACTORY_ATTRIBUTE,
            lambda *args, **kwargs: remote_engine,
        )
    else:
        monkeypatch.setitem(sys.modules, REMOTE_PACKAGE, None)
    remote_url = None if scenario == LOCAL_ONLY_SCENARIO else REMOTE_URL
    result = engine.create_auto_hint_engine(
        filename=Path(CONFIG_FILENAME),
        auto_hint_model=MODEL_ID,
        auto_hint_url=remote_url,
        auto_hint_api_key=None,
        console=console,
    )
    if scenario == REMOTE_SUCCESS_SCENARIO:
        assert result is remote_engine
        assert not console_output.getvalue()
    else:
        warning = (
            engine.LOCAL_AUTO_HINT_UNSUPPORTED_WARNING
            if scenario == LOCAL_ONLY_SCENARIO
            else engine.REMOTE_AUTO_HINT_UNAVAILABLE_WARNING
        )
        assert result is None
        assert warning in SPACE.join(console_output.getvalue().split())


def test_excluded_environment_rejects_loading_before_imports(
    excluded_environment: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Reject local loading before optional imports or cache creation."""
    original_import = builtins.__import__
    cache_dir = tmp_path / MODEL_ID
    local_engine = LocalAutoHintEngine(cache_dir=cache_dir)
    monkeypatch.setattr(
        builtins,
        IMPORT_ATTRIBUTE,
        partial(reject_local_import, original_import),
    )
    with pytest.raises(UnsupportedLocalAutoHintPlatformError) as exc_info:
        local_engine.ensure_loaded()
    assert str(exc_info.value) == UNSUPPORTED_LOCAL_AUTO_HINT_MESSAGE
    assert not cache_dir.exists()


def test_excluded_environment_reports_remote_only_installation(
    excluded_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omit torch from installation checks on excluded environments."""
    checked_packages: list[str] = []
    monkeypatch.setattr(
        detect.importlib.metadata,
        DISTRIBUTION_ATTRIBUTE,
        partial(record_distribution, checked_packages),
    )
    result = str(detect._check_auto_hint_installed())
    assert detect.TORCH_PACKAGE not in checked_packages
    assert REMOTE_PACKAGE in checked_packages
    assert detect.REMOTE_AUTO_HINTS_AVAILABLE_STATUS in result
