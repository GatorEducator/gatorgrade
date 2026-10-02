"""Tests for the gatorgrade.engine module."""

import sys
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from rich.console import Console

import gatorgrade.engine as engine_module
from gatorgrade.engine import (
    create_auto_hint_engine,
    try_create_remote_engine,
)
from gatorgrade.hint.fallback import RemoteEngineAdapter
from gatorgrade.platform_support import supports_local_auto_hints

CONFIG_PATH = Path("gatorgrade.yml")
CUSTOM_MODEL_ID = "custom/model"
LOCAL_UNSUPPORTED_WARNING = (
    "Local auto-hints are not supported on this device."
)
REMOTE_UNAVAILABLE_WARNING = "The remote auto-hint engine could not be created"
REMOTE_URL = "http://localhost:9999"
REMOTE_DEPENDENCY_MODULE = "openai"


@pytest.mark.skipif(
    not supports_local_auto_hints(),
    reason="Local auto-hint engine is not supported on this platform.",
)
def test_create_auto_hint_engine_default_model(chdir: Any) -> None:
    """create_auto_hint_engine uses default model when sentinel is passed."""
    chdir("tests/test_assignment")
    engine = create_auto_hint_engine(
        filename=Path("gatorgrade.yml"),
        auto_hint_model="__default_model__",
        auto_hint_url=None,
        auto_hint_api_key=None,
    )
    assert engine is not None


@pytest.mark.autohint
def test_create_auto_hint_engine_with_remote_url_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the local fallback when remote engine creation fails."""
    console = Console(file=StringIO(), color_system=None)
    primary_engine = MagicMock()
    fallback_engine = MagicMock()
    local_factory = MagicMock(side_effect=[primary_engine, fallback_engine])
    remote_factory = MagicMock(return_value=None)
    monkeypatch.setattr(
        engine_module, "supports_local_auto_hints", lambda: True
    )
    monkeypatch.setattr(engine_module, "LocalAutoHintEngine", local_factory)
    monkeypatch.setattr(
        engine_module, "try_create_remote_engine", remote_factory
    )
    engine = create_auto_hint_engine(
        filename=CONFIG_PATH,
        auto_hint_model=CUSTOM_MODEL_ID,
        auto_hint_url=REMOTE_URL,
        auto_hint_api_key=None,
        console=console,
    )
    assert engine is fallback_engine
    remote_factory.assert_called_once_with(
        REMOTE_URL,
        None,
        CUSTOM_MODEL_ID,
        system_prompt=None,
        validation_rules=None,
    )


@pytest.mark.autohint
def test_create_auto_hint_engine_uses_remote_when_local_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the remote engine when the local platform is unsupported."""
    console_output = StringIO()
    console = Console(file=console_output, color_system=None)
    remote_engine = MagicMock()
    remote_factory = MagicMock(return_value=remote_engine)
    local_factory = MagicMock()
    monkeypatch.setattr(
        engine_module, "supports_local_auto_hints", lambda: False
    )
    monkeypatch.setattr(engine_module, "LocalAutoHintEngine", local_factory)
    monkeypatch.setattr(
        engine_module, "try_create_remote_engine", remote_factory
    )
    result = create_auto_hint_engine(
        filename=CONFIG_PATH,
        auto_hint_model=CUSTOM_MODEL_ID,
        auto_hint_url=REMOTE_URL,
        auto_hint_api_key=None,
        console=console,
    )
    assert result is remote_engine
    assert not console_output.getvalue()
    local_factory.assert_not_called()


@pytest.mark.autohint
def test_create_auto_hint_engine_warns_without_supported_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Warn when neither remote nor local auto-hints are available."""
    console_output = StringIO()
    console = Console(file=console_output, color_system=None)
    remote_factory = MagicMock(return_value=None)
    local_factory = MagicMock()
    monkeypatch.setattr(
        engine_module, "supports_local_auto_hints", lambda: False
    )
    monkeypatch.setattr(engine_module, "LocalAutoHintEngine", local_factory)
    monkeypatch.setattr(
        engine_module, "try_create_remote_engine", remote_factory
    )
    result = create_auto_hint_engine(
        filename=CONFIG_PATH,
        auto_hint_model=CUSTOM_MODEL_ID,
        auto_hint_url=REMOTE_URL,
        auto_hint_api_key=None,
        console=console,
    )
    assert result is None
    assert REMOTE_UNAVAILABLE_WARNING in console_output.getvalue()
    local_factory.assert_not_called()


def test_create_auto_hint_engine_warns_when_remote_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Warn when remote dependencies and local platform support are absent."""
    console_output = StringIO()
    console = Console(file=console_output, color_system=None)
    local_factory = MagicMock()
    monkeypatch.setitem(sys.modules, REMOTE_DEPENDENCY_MODULE, None)
    monkeypatch.setattr(
        engine_module, "supports_local_auto_hints", lambda: False
    )
    monkeypatch.setattr(engine_module, "LocalAutoHintEngine", local_factory)
    result = create_auto_hint_engine(
        filename=CONFIG_PATH,
        auto_hint_model=CUSTOM_MODEL_ID,
        auto_hint_url=REMOTE_URL,
        auto_hint_api_key=None,
        console=console,
    )
    assert result is None
    assert REMOTE_UNAVAILABLE_WARNING in console_output.getvalue()
    local_factory.assert_not_called()


def test_create_auto_hint_engine_warns_when_local_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Warn and continue when local auto-hints are unsupported."""
    console_output = StringIO()
    console = Console(file=console_output, color_system=None)
    local_factory = MagicMock()
    monkeypatch.setattr(
        engine_module, "supports_local_auto_hints", lambda: False
    )
    monkeypatch.setattr(engine_module, "LocalAutoHintEngine", local_factory)
    result = create_auto_hint_engine(
        filename=CONFIG_PATH,
        auto_hint_model=CUSTOM_MODEL_ID,
        auto_hint_url=None,
        auto_hint_api_key=None,
        console=console,
    )
    assert result is None
    assert LOCAL_UNSUPPORTED_WARNING in console_output.getvalue()
    local_factory.assert_not_called()


@pytest.mark.autohint
def test_try_create_remote_engine_returns_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return an adapter after checking dependencies without connecting."""
    dependency_check = MagicMock(return_value=None)
    monkeypatch.setattr(
        engine_module.RemoteHintEngine, "check_deps", dependency_check
    )
    engine = try_create_remote_engine(
        url=REMOTE_URL,
        api_key=None,
        model_id=CUSTOM_MODEL_ID,
    )
    assert isinstance(engine, RemoteEngineAdapter)
    assert engine.model_id == CUSTOM_MODEL_ID
    dependency_check.assert_called_once_with()
