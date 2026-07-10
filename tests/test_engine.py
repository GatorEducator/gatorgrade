"""Tests for the gatorgrade.engine module."""

from pathlib import Path
from typing import Any

import pytest

from gatorgrade.engine import (
    create_auto_hint_engine,
    try_create_remote_engine,
)
from gatorgrade.hint.fallback import RemoteEngineAdapter


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
    chdir: Any,
) -> None:
    """Falls back to local engine when remote URL is unreachable."""
    chdir("tests/test_assignment")
    engine = create_auto_hint_engine(
        filename=Path("gatorgrade.yml"),
        auto_hint_model="__default_model__",
        auto_hint_url="http://localhost:99999",
        auto_hint_api_key=None,
    )
    assert engine is not None


@pytest.mark.autohint
def test_try_create_remote_engine_returns_adapter() -> None:
    """Returns a RemoteEngineAdapter even with a bad URL (lazy connect)."""
    engine = try_create_remote_engine(
        url="http://localhost:99999",
        api_key=None,
        model_id="test-model",
    )
    assert isinstance(engine, RemoteEngineAdapter)
