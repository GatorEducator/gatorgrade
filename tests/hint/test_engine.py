"""Test suite for the auto-hint engine (gatorgrade/hint/engine.py)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gatorgrade.hint.engine import (
    DEFAULT_MODEL_ID,
    HINT_DIAG_TRUNCATE,
    HINT_FILE_LINES,
    HINT_REPETITION_PENALTY,
    HINT_SUPPRESSED_MESSAGE,
    HINT_TOP_P,
    AutoHintEngine,
    _model_cache_dir,
)

pytestmark = pytest.mark.autohint


class TestHfCacheDir:
    """Tests for the _model_cache_dir helper."""

    def test_returns_path(self) -> None:
        """The cache dir function returns a Path object."""
        assert isinstance(_model_cache_dir(), Path)

    def test_ends_with_models(self) -> None:
        """The cache dir ends with 'models' by default."""
        assert _model_cache_dir().name == "models"

    def test_override_is_honoured(self, tmp_path: Path) -> None:
        """Explicit override is returned as-is."""
        custom = tmp_path / "custom"
        assert _model_cache_dir(override=custom) == custom


class TestAutoHintEngineConstruction:
    """Tests for AutoHintEngine construction and basic properties."""

    def test_default_construction(self) -> None:
        """Engine constructed with defaults uses the correct model ID."""
        engine = AutoHintEngine()
        assert engine.model_id == DEFAULT_MODEL_ID
        assert not engine.is_loaded

    def test_custom_construction(self) -> None:
        """Engine constructed with a custom model ID."""
        engine = AutoHintEngine(model_id="custom/model")
        assert engine.model_id == "custom/model"
        assert not engine.is_loaded

    def test_model_id_property(self) -> None:
        """Return the model_id passed to the constructor."""
        engine = AutoHintEngine(model_id="custom/model")
        assert engine.model_id == "custom/model"

    def test_is_loaded_property(self) -> None:
        """Return False before the model is loaded."""
        engine = AutoHintEngine()
        assert engine.is_loaded is False


class TestAutoHintEngineGenerateHint:
    """Tests for AutoHintEngine.generate_hint with mocked pipeline."""

    def test_generate_hint_with_mocked_pipeline(self) -> None:
        """Generate hint returns the assistant's reply from the pipeline."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"generated_text": "Check your file path and try again."}
        ]
        engine._pipe = mock_pipe

        hint = engine.generate_hint(
            description="Check that hello.py exists",
            diagnostic="File not found",
            command="ls hello.py",
        )

        assert hint == "Check your file path and try again."
        mock_pipe.assert_called_once()

    def test_generate_hint_passes_correct_messages(self) -> None:
        """Verify the messages sent to the pipeline contain expected content."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = [{"generated_text": "A hint."}]
        engine._pipe = mock_pipe

        engine.generate_hint(
            description="Check imports",
            diagnostic="ModuleNotFoundError",
            command="python script.py",
        )

        call_kwargs = mock_pipe.call_args
        messages = call_kwargs[0][0]
        user_msg = messages[1]["content"]
        assert "Check imports" in user_msg
        assert "ModuleNotFoundError" in user_msg
        assert "python script.py" in user_msg

    def test_generate_hint_returns_safely_when_not_loaded(self) -> None:
        """Returns safely when engine not loaded — None or a hint string."""
        engine = AutoHintEngine()
        # must not raise regardless of whether deps are installed
        hint = engine.generate_hint(description="test", diagnostic="error")
        assert hint is None or (isinstance(hint, str) and len(hint) > 0)

    def test_generate_hint_returns_none_on_pipeline_exception(self) -> None:
        """Returns None when the pipeline raises."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.side_effect = RuntimeError("OOM")
        engine._pipe = mock_pipe

        hint = engine.generate_hint(description="test", diagnostic="error")
        assert hint is None

    def test_generate_hint_returns_none_for_empty_reply(self) -> None:
        """Returns None when the assistant reply is empty."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = [{"generated_text": "   "}]
        engine._pipe = mock_pipe

        hint = engine.generate_hint(description="test", diagnostic="error")
        assert hint is None

    def test_generate_hint_returns_none_for_empty_list(self) -> None:
        """Returns None when the pipeline returns an empty list."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = []
        engine._pipe = mock_pipe

        hint = engine.generate_hint(description="test", diagnostic="error")
        assert hint is None

    def test_generate_hint_uses_repetition_penalty(self) -> None:
        """Pipeline is called with repetition_penalty parameter."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = [{"generated_text": "A hint."}]
        engine._pipe = mock_pipe

        engine.generate_hint(description="test", diagnostic="error")

        call_kwargs = mock_pipe.call_args[1]
        assert call_kwargs["repetition_penalty"] == HINT_REPETITION_PENALTY

    def test_generate_hint_uses_top_p(self) -> None:
        """Pipeline is called with top_p parameter."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = [{"generated_text": "A hint."}]
        engine._pipe = mock_pipe

        engine.generate_hint(description="test", diagnostic="error")

        call_kwargs = mock_pipe.call_args[1]
        assert call_kwargs["top_p"] == HINT_TOP_P

    def test_generate_hint_handles_hint_suggesting_test_change(self) -> None:
        """Return a suppression message when the hint suggests modifying tests.

        When the generated hint suggests modifying tests, a suppression
        message is returned instead of the model's output.
        """
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {"generated_text": "The test incorrectly asserts equality."}
        ]
        engine._pipe = mock_pipe

        hint = engine.generate_hint(description="test", diagnostic="error")
        assert hint == HINT_SUPPRESSED_MESSAGE

    def test_generate_hint_accepts_valid_hint(self) -> None:
        """Returns the hint when it correctly describes a code fix."""
        engine = AutoHintEngine()
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            {
                "generated_text": "The function count returns 1 but the test expects 2; check the loop logic."
            }
        ]
        engine._pipe = mock_pipe

        hint = engine.generate_hint(description="test", diagnostic="error")
        assert hint is not None
        assert "count returns 1" in hint


class TestIsValidHint:
    """Tests for the _is_valid_hint static validation method."""

    def test_valid_hint_accepted(self) -> None:
        """A hint describing a code fix is accepted."""
        hint = (
            "The function returns 1 but the test expects 2; check the logic."
        )
        assert AutoHintEngine._is_valid_hint(hint)

    def test_test_incorrectly_rejected(self) -> None:
        """A hint suggesting the test is incorrect is rejected."""
        hint = "The test incorrectly asserts equality."
        assert not AutoHintEngine._is_valid_hint(hint)

    def test_modify_the_test_rejected(self) -> None:
        """A hint suggesting modifying the test is rejected."""
        hint = "Modify the test to handle edge cases."
        assert not AutoHintEngine._is_valid_hint(hint)

    def test_change_the_assertion_rejected(self) -> None:
        """A hint suggesting changing the assertion is rejected."""
        hint = "Change the assertion to expect None instead."
        assert not AutoHintEngine._is_valid_hint(hint)

    def test_change_expected_rejected(self) -> None:
        """A hint suggesting changing expected results is rejected."""
        hint = "Change the expected result from 2 to 1."
        assert not AutoHintEngine._is_valid_hint(hint)

    def test_case_insensitive(self) -> None:
        """Validation is case-insensitive."""
        hint = "The TEST INCORRECTLY asserts the value."
        assert not AutoHintEngine._is_valid_hint(hint)

    def test_mentioning_test_name_is_ok(self) -> None:
        """Mentioning a test name without criticizing it is accepted."""
        hint = (
            "The test test_count_punctuation expects 2 but got 1; "
            "check the counting logic in count_punctuation."
        )
        assert AutoHintEngine._is_valid_hint(hint)


class TestAutoHintEngineLazyLoading:
    """Tests for the lazy-loading behaviour."""

    def test_not_loaded_after_construction(self) -> None:
        """Engine is not loaded immediately after construction."""
        engine = AutoHintEngine()
        assert not engine.is_loaded

    def test_ensure_loaded_stays_lazy(self) -> None:
        """Engine stays lazy until _ensure_loaded is called."""
        engine = AutoHintEngine()
        assert not engine.is_loaded

    def test_ensure_loaded_passes_trust_remote_code_for_gemma4(
        self,
    ) -> None:
        """Load Gemma 4 checkpoints with trust_remote_code=True."""
        engine = AutoHintEngine(model_id="google/gemma-4-test")
        mock_config = MagicMock()
        mock_config.model_type = "gemma4"
        with (
            patch(
                "transformers.AutoConfig.from_pretrained",
                return_value=mock_config,
            ) as mock_from_pretrained,
            patch("transformers.pipeline") as mock_pipeline,
        ):
            engine._ensure_loaded()
        mock_from_pretrained.assert_called_once()
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs.get("trust_remote_code") is True

    def test_ensure_loaded_raises_helpful_error_on_old_transformers(
        self,
    ) -> None:
        """Raise a clear error when transformers is too old for Gemma 4."""
        engine = AutoHintEngine(model_id="google/gemma-4-test")
        error = ValueError(
            "The checkpoint you are trying to load has model type `gemma4`"
        )
        with patch(
            "transformers.AutoConfig.from_pretrained",
            side_effect=error,
        ):
            with pytest.raises(RuntimeError, match="transformers >= 5"):
                engine._ensure_loaded()

    def test_generate_hint_survives_ensure_loaded_error(
        self,
    ) -> None:
        """Return None gracefully when _ensure_loaded raises unexpectedly."""
        engine = AutoHintEngine()
        with patch.object(
            engine,
            "_ensure_loaded",
            side_effect=RuntimeError("boom"),
        ):
            hint = engine.generate_hint(description="test", diagnostic="error")
        assert hint is None


class TestAutoHintEngineMessageBuilding:
    """Tests for the message building logic."""

    def test_build_messages_includes_system_role(self) -> None:
        """Messages include a system prompt."""
        msgs = AutoHintEngine()._build_messages(
            description="Check file exists"
        )
        assert msgs[0]["role"] == "system"
        assert "short, direct hints" in msgs[0]["content"]

    def test_build_messages_includes_description(self) -> None:
        """User message contains the check description."""
        msgs = AutoHintEngine()._build_messages(
            description="Check file exists"
        )
        assert "Check file exists" in msgs[1]["content"]

    def test_build_messages_includes_command(self) -> None:
        """User message includes the command when provided."""
        msgs = AutoHintEngine()._build_messages(
            description="test",
            command="ls hello.py",
        )
        assert "ls hello.py" in msgs[1]["content"]

    def test_build_messages_includes_diagnostic(self) -> None:
        """User message includes the diagnostic output."""
        msgs = AutoHintEngine()._build_messages(
            description="test",
            diagnostic="File not found: hello.py",
        )
        assert "File not found: hello.py" in msgs[1]["content"]

    def test_build_messages_truncates_long_diagnostic(self) -> None:
        """Diagnostic longer than HINT_DIAG_TRUNCATE is truncated."""
        long_diag = "x" * (HINT_DIAG_TRUNCATE + 100)
        msgs = AutoHintEngine()._build_messages(
            description="test",
            diagnostic=long_diag,
        )
        assert len(msgs[1]["content"]) < len(long_diag) + 500

    def test_build_messages_truncates_file_to_lines(self) -> None:
        """File content is truncated to HINT_FILE_LINES complete lines."""
        # create 100 lines of content
        many_lines = "\n".join([f"line_{i}" for i in range(100)])
        msgs = AutoHintEngine()._build_messages(
            description="test",
            file_content=many_lines,
        )
        # the user message should contain the first HINT_FILE_LINES lines
        # but NOT line_HINT_FILE_LINES (which would be the 21st line)
        assert f"line_{HINT_FILE_LINES - 1}" in msgs[1]["content"]
        assert f"line_{HINT_FILE_LINES}" not in msgs[1]["content"]

    def test_build_messages_includes_rules(self) -> None:
        """System prompt includes NEVER/INSTEAD guidance for the model."""
        msgs = AutoHintEngine()._build_messages(description="test")
        system_content = msgs[0]["content"]
        assert "NEVER suggest modifying tests" in system_content
        assert "INSTEAD say:" in system_content

    def test_build_messages_empty_diagnostic(self) -> None:
        """Messages are still valid when diagnostic is empty."""
        msgs = AutoHintEngine()._build_messages(description="test")
        assert "test" in msgs[1]["content"]
        assert "diagnostic" not in msgs[1]["content"].lower()

    def test_build_messages_includes_file_content(self) -> None:
        """User message includes file content when provided."""
        msgs = AutoHintEngine()._build_messages(
            description="test",
            file_content="def hello():\n    pass",
        )
        assert "def hello():" in msgs[1]["content"]
        assert "pass" in msgs[1]["content"]


class TestAutoHintEngineGracefulDegradation:
    """Tests that generate_hint returns None gracefully when deps missing."""

    def test_default_engine_not_loaded(self) -> None:
        """Engine is not loaded by default (lazy)."""
        engine = AutoHintEngine()
        assert not engine.is_loaded

    def test_generate_hint_never_crashes(self) -> None:
        """generate_hint never crashes — returns None or a string.

        When the optional deps are not installed, generate_hint
        returns None.  When they are installed, it returns a hint
        string.  Either way it must not raise.

        """
        engine = AutoHintEngine()
        # this must not raise even when deps are missing.
        hint = engine.generate_hint(description="test", diagnostic="error")
        # either None (graceful degradation) or a non-empty string
        assert hint is None or (isinstance(hint, str) and len(hint) > 0)


class TestAutoHintEngineCacheDir:
    """Tests for the model cache directory resolution."""

    def test_cache_dir_property_uses_default(self) -> None:
        """The cache_dir property returns a path ending in 'models'."""
        engine = AutoHintEngine()
        result = engine.cache_dir
        assert isinstance(result, Path)
        assert "gatorgrade" in str(result)
        assert result.name == "models"

    def test_cache_dir_constructor_override(self, tmp_path: Path) -> None:
        """Explicit cache_dir in the constructor is honoured."""
        custom = tmp_path / "my-models"
        engine = AutoHintEngine(cache_dir=custom)
        assert engine.cache_dir == custom

    def test_cache_dir_env_var_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """$GATORGRADE_MODELS_DIR overrides the default."""
        custom = tmp_path / "env-models"
        monkeypatch.setenv("GATORGRADE_MODELS_DIR", str(custom))
        engine = AutoHintEngine()
        assert engine.cache_dir == custom

    def test_cache_dir_constructor_beats_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Constructor cache_dir takes precedence over env var."""
        env_dir = tmp_path / "env-dir"
        con_dir = tmp_path / "con-dir"
        monkeypatch.setenv("GATORGRADE_MODELS_DIR", str(env_dir))
        engine = AutoHintEngine(cache_dir=con_dir)
        assert engine.cache_dir == con_dir


class TestModelCacheDirFallback:
    """Tests for the _model_cache_dir fallback path."""

    def test_fallback_when_platformdirs_missing(self) -> None:
        """_model_cache_dir falls back when platformdirs is not available."""
        with patch.dict("sys.modules", {"platformdirs": None}, clear=False):
            result = _model_cache_dir()
        assert "gatorgrade" in str(result)
        assert result.name == "models"

    def test_env_var_override(self, tmp_path: Path) -> None:
        """$GATORGRADE_MODELS_DIR overrides the cache dir."""
        with patch.dict(
            "os.environ", {"GATORGRADE_MODELS_DIR": str(tmp_path)}
        ):
            result = _model_cache_dir()
        assert result == tmp_path


class TestAutoHintEngineDeps:
    """Tests for dependency checking via patches."""

    def test_check_deps_raises_when_transformers_missing(self) -> None:
        """check_deps raises ImportError when transformers is missing."""
        with patch.dict("sys.modules", {"transformers": None}, clear=False):
            with pytest.raises(ImportError, match="auto-hint"):
                AutoHintEngine.check_deps()

    def test_check_deps_raises_when_torch_missing(self) -> None:
        """check_deps raises ImportError when torch is missing."""
        with patch.dict("sys.modules", {"torch": None}, clear=False):
            with pytest.raises(ImportError, match="auto-hint"):
                AutoHintEngine.check_deps()

    def test_check_deps_raises_when_both_missing(self) -> None:
        """check_deps raises ImportError when both extras are missing."""
        with patch.dict(
            "sys.modules",
            {"transformers": None, "torch": None},
            clear=False,
        ):
            with pytest.raises(ImportError, match="auto-hint"):
                AutoHintEngine.check_deps()

    def test_ensure_loaded_raises_when_transformers_missing(self) -> None:
        """_ensure_loaded raises ImportError when transformers missing."""
        with patch.dict("sys.modules", {"transformers": None}, clear=False):
            engine = AutoHintEngine()
            with pytest.raises(ImportError, match="auto-hint"):
                engine._ensure_loaded()
