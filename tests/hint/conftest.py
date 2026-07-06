"""Pytest configuration for auto-hint engine tests.

Mock the transformers.pipeline callable so that the real
transformers, torch, and numpy packages are never loaded
during testing.  These packages are heavyweight (seconds of import
time) and are not needed for any unit test -- every test uses mocks
or tests the graceful-degradation path where loading fails.

"""

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True, scope="module")
def _mock_transformers_pipeline() -> Generator[None, None, None]:
    """Replace transformers.pipeline with a mock before any test runs.

    The lazy from transformers import pipeline inside
    AutoHintEngine.ensure_loaded triggers the full
    transformers / torch / numpy dependency chain (a
    several-second hit per test).  By inserting a fake transformers
    module into sys.modules we prevent the real packages from ever
    loading.

    Tests that specifically need to verify behaviour when
    transformers is missing (the check_deps tests) already use
    patch.dict(sys.modules, {transformers: None}) to remove the
    mock before they run, so they are unaffected.

    """
    import sys  # noqa: PLC0415

    if "transformers" not in sys.modules:
        fake_transformers = MagicMock()
        fake_transformers.pipeline = MagicMock()
        fake_transformers.AutoConfig = MagicMock()
        fake_transformers.logging = MagicMock()
        fake_transformers.logging.set_verbosity_error = MagicMock()
        fake_transformers.logging.disable_progress_bar = MagicMock()
        sys.modules["transformers"] = fake_transformers
    yield
