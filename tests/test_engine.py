"""Tests for the gatorgrade.engine module."""

from pathlib import Path
from typing import Any

import pytest

from gatorgrade.engine import (
    create_auto_hint_engine,
    try_create_remote_engine,
)
from gatorgrade.hint.fallback import RemoteEngineAdapter
from gatorgrade.hint.remote_engine import REMOTE_KEY_ENV_DEFAULT

TEST_DEFAULT_KEY = "default-test-key"
TEST_CUSTOM_KEY = "custom-test-key"
TEST_CUSTOM_KEY_ENV = "TEST_AUTO_HINT_API_KEY"


def test_create_auto_hint_engine_default_model(chdir: Any) -> None:
    """create_auto_hint_engine uses default model when sentinel is passed."""
    chdir("tests/test_assignment")
    engine = create_auto_hint_engine(
        filename=Path("gatorgrade.yml"),
        auto_hint_model="__default_model__",
        auto_hint_url=None,
        auto_hint_key_env=None,
    )
    assert engine is not None


@pytest.mark.autohint
def test_create_auto_hint_engine_with_remote_url_falls_back(
    chdir: Any,
) -> None:
    """Falls back to local engine when remote URL is unreachable."""
    chdir("tests/test_assignment")
    engine = create_auto_hint_engine(
        filename=Path("gatorgrade.yml"),
        auto_hint_model="__default_model__",
        auto_hint_url="http://localhost:99999",
        auto_hint_key_env=None,
    )
    assert engine is not None


@pytest.mark.autohint
def test_try_create_remote_engine_returns_adapter() -> None:
    """Returns a RemoteEngineAdapter even with a bad URL (lazy connect)."""
    engine = try_create_remote_engine(
        url="http://localhost:99999",
        api_key_env=None,
        model_id="test-model",
    )
    assert isinstance(engine, RemoteEngineAdapter)


@pytest.mark.autohint
def test_try_create_remote_engine_uses_default_key_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remote factory resolves the default environment variable."""
    monkeypatch.setenv(REMOTE_KEY_ENV_DEFAULT, TEST_DEFAULT_KEY)
    engine = try_create_remote_engine(
        url="http://localhost:99999",
        api_key_env=None,
        model_id="test-model",
    )
    assert isinstance(engine, RemoteEngineAdapter)
    assert engine._remote._api_key == TEST_DEFAULT_KEY


@pytest.mark.autohint
def test_try_create_remote_engine_uses_custom_key_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remote factory resolves the requested environment variable."""
    monkeypatch.setenv(REMOTE_KEY_ENV_DEFAULT, TEST_DEFAULT_KEY)
    monkeypatch.setenv(TEST_CUSTOM_KEY_ENV, TEST_CUSTOM_KEY)
    engine = try_create_remote_engine(
        url="http://localhost:99999",
        api_key_env=TEST_CUSTOM_KEY_ENV,
        model_id="test-model",
    )
    assert isinstance(engine, RemoteEngineAdapter)
    assert engine._remote._api_key == TEST_CUSTOM_KEY
