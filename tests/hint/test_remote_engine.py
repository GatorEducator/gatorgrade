"""Test suite for the remote auto-hint engine (remote_engine.py)."""

from unittest.mock import MagicMock, patch

import pytest

from gatorgrade.hint.remote_engine import (
    EXTRA_BODY_DISABLE_THINKING,
    REMOTE_HINT_DIAG_TRUNCATE,
    REMOTE_HINT_FILE_LINES,
    REMOTE_HINT_MAX_TOKENS,
    REMOTE_HINT_TEMPERATURE,
    REMOTE_HINT_TOP_P,
    REMOTE_MODEL_DEFAULT,
    RemoteHintEngine,
)

pytestmark = pytest.mark.autohint


class TestRemoteHintEngineConstruction:
    """Tests for RemoteHintEngine construction and basic properties."""

    def test_default_construction(self) -> None:
        """Engine constructed with defaults stores correct values."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
        )
        assert engine.model_id == REMOTE_MODEL_DEFAULT

    def test_custom_construction(self) -> None:
        """Engine constructed with custom values."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            api_key="my-key",
            model_id="custom-model",
        )
        assert engine.model_id == "custom-model"

    def test_is_loaded_always_true(self) -> None:
        """Remote engine is always considered loaded."""
        engine = RemoteHintEngine(base_url="http://test.url:4160")
        assert engine.is_loaded is True

    def test_ensure_loaded_is_noop(self) -> None:
        """ensure_loaded does not raise."""
        engine = RemoteHintEngine(base_url="http://test.url:4160")
        engine.ensure_loaded()  # must not raise

    def test_model_id_property(self) -> None:
        """model_id returns the configured model."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            model_id="Qwen-3.6-35B-A3B",
        )
        assert engine.model_id == "Qwen-3.6-35B-A3B"


class TestRemoteHintEngineGenerateHint:
    """Tests for RemoteHintEngine.generate_hint with mocked openai."""

    def _mock_choice(
        self, content: str = "", reasoning_content: str = ""
    ) -> MagicMock:
        """Create a mocked chat completion choice."""
        mock_msg = MagicMock()
        mock_msg.content = content
        mock_msg.reasoning_content = reasoning_content
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        return mock_choice

    def _mock_response(self, choices: list) -> MagicMock:
        """Create a mocked chat completion response."""
        mock_resp = MagicMock()
        mock_resp.choices = choices
        return mock_resp

    def _run_with_fake_openai(
        self,
        engine: RemoteHintEngine,
        mock_choice: MagicMock,
    ) -> tuple:
        """Run generate_hint with a fake openai module inserted.

        Since openai is not a declared project dependency and may not
        be installed in the test environment, we insert a fake module
        into sys.modules so the lazy import inside generate_hint
        succeeds.

        """
        import sys  # noqa: PLC0415
        import types  # noqa: PLC0415
        from typing import Any  # noqa: PLC0415

        # build a real module hierarchy so the import
        # ``from openai.types.chat import ChatCompletionMessageParam``
        # succeeds inside generate_hint.
        fake_openai: Any = types.ModuleType("openai")
        fake_openai.__path__ = []  # make it a package
        types_mod: Any = types.ModuleType("openai.types")
        types_mod.__path__ = []
        chat_mod: Any = types.ModuleType("openai.types.chat")
        fake_openai.types = types_mod
        fake_openai.types.chat = chat_mod
        fake_openai.types.chat.ChatCompletionMessageParam = dict
        fake_openai.OpenAI = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        fake_openai.OpenAI.return_value = mock_client
        # register submodules so python's import machinery finds them
        sys.modules["openai.types"] = types_mod
        sys.modules["openai.types.chat"] = chat_mod

        was_present = "openai" in sys.modules
        old_module = sys.modules.get("openai")
        sys.modules["openai"] = fake_openai
        try:
            hint, is_low_quality = engine.generate_hint(
                description="test", diagnostic="error"
            )
        finally:
            if was_present:
                assert old_module is not None
                sys.modules["openai"] = old_module
            else:
                del sys.modules["openai"]
            # clean up submodule entries we injected
            for sub in ("openai.types", "openai.types.chat"):
                sys.modules.pop(sub, None)
        return hint, is_low_quality, mock_client

    def test_generate_hint_returns_content(self) -> None:
        """Return the hint from the message content field."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            api_key="not-needed",
            model_id="test-model",
        )
        mock_choice = self._mock_choice(
            content="Check your file path and try again."
        )
        hint, is_low_quality, _ = self._run_with_fake_openai(
            engine, mock_choice
        )
        assert hint == "Check your file path and try again."
        assert not is_low_quality

    def test_generate_hint_falls_back_to_reasoning_content(
        self,
    ) -> None:
        """Fall back to reasoning_content when content is empty."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            api_key="not-needed",
            model_id="test-model",
        )
        mock_choice = self._mock_choice(
            content="",
            reasoning_content="The hint derived from your reasoning.",
        )
        hint, is_low_quality, _ = self._run_with_fake_openai(
            engine, mock_choice
        )
        assert hint == "The hint derived from your reasoning."
        assert not is_low_quality

    def test_generate_hint_returns_none_on_import_error(self) -> None:
        """Returns None when openai is not installed."""
        engine = RemoteHintEngine(base_url="http://test.url:4160")
        with patch.dict(
            "sys.modules",
            {"openai": None},
            clear=False,
        ):
            hint, _ = engine.generate_hint(
                description="test", diagnostic="error"
            )
        assert hint is None

    def test_generate_hint_returns_none_on_exception(self) -> None:
        """Returns None when the API raises."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            api_key="not-needed",
            model_id="test-model",
        )
        import sys  # noqa: PLC0415

        fake_openai = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError(
            "Connection refused"
        )
        fake_openai.OpenAI.return_value = mock_client

        was_present = "openai" in sys.modules
        old_module = sys.modules.get("openai")
        sys.modules["openai"] = fake_openai
        try:
            hint, _ = engine.generate_hint(
                description="test", diagnostic="error"
            )
        finally:
            if was_present:
                assert old_module is not None
                sys.modules["openai"] = old_module
                del sys.modules["openai"]

        assert hint is None

    def test_generate_hint_returns_none_for_empty_reply(self) -> None:
        """Returns None when both content and reasoning are empty."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            api_key="not-needed",
            model_id="test-model",
        )
        mock_choice = self._mock_choice(content="   ")
        hint, _is_low, _ = self._run_with_fake_openai(engine, mock_choice)
        assert hint is None

    def test_generate_hint_passes_correct_params(self) -> None:
        """OpenAI client is called with the correct parameters."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            api_key="not-needed",
            model_id="test-model",
        )
        mock_choice = self._mock_choice(content="A hint.")
        _, _, mock_client = self._run_with_fake_openai(engine, mock_choice)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["max_tokens"] == REMOTE_HINT_MAX_TOKENS
        assert call_kwargs["temperature"] == REMOTE_HINT_TEMPERATURE
        assert call_kwargs["top_p"] == REMOTE_HINT_TOP_P
        assert "extra_body" in call_kwargs
        assert call_kwargs["extra_body"] == EXTRA_BODY_DISABLE_THINKING

    def test_generate_hint_handles_suggesting_test_change(self) -> None:
        """Return hint flagged as low quality when it suggests modifying tests."""
        engine = RemoteHintEngine(
            base_url="http://test.url:4160",
            api_key="not-needed",
            model_id="test-model",
        )
        mock_choice = self._mock_choice(
            content="The test incorrectly asserts equality."
        )
        hint, is_low_quality, _ = self._run_with_fake_openai(
            engine, mock_choice
        )
        assert hint == "The test incorrectly asserts equality."
        assert is_low_quality


class TestRemoteHintEngineMessageBuilding:
    """Tests for the message building logic."""

    def test_build_messages_includes_system_role(self) -> None:
        """Messages include a system prompt."""
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(description="Check file exists")
        assert msgs[0]["role"] == "system"
        assert "short, direct hints" in msgs[0]["content"]

    def test_build_messages_includes_description(self) -> None:
        """User message contains the check description."""
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(description="Check file exists")
        assert "Check file exists" in msgs[1]["content"]

    def test_build_messages_includes_command(self) -> None:
        """User message includes the command when provided."""
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(description="test", command="ls hello.py")
        assert "ls hello.py" in msgs[1]["content"]

    def test_build_messages_includes_diagnostic(self) -> None:
        """User message includes the diagnostic output."""
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(
            description="test", diagnostic="File not found: hello.py"
        )
        assert "File not found: hello.py" in msgs[1]["content"]

    def test_build_messages_truncates_long_diagnostic(self) -> None:
        """Diagnostic longer than REMOTE_HINT_DIAG_TRUNCATE is truncated."""
        long_diag = "x" * (REMOTE_HINT_DIAG_TRUNCATE + 100)
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(description="test", diagnostic=long_diag)
        assert len(msgs[1]["content"]) < len(long_diag) + 500

    def test_build_messages_truncates_file_to_lines(self) -> None:
        """File content is truncated to REMOTE_HINT_FILE_LINES complete lines."""
        many_lines = "\n".join([f"line_{i}" for i in range(100)])
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(description="test", file_content=many_lines)
        assert f"line_{REMOTE_HINT_FILE_LINES - 1}" in msgs[1]["content"]
        assert f"line_{REMOTE_HINT_FILE_LINES}" not in msgs[1]["content"]

    def test_build_messages_includes_rules(self) -> None:
        """System prompt includes NEVER/INSTEAD guidance."""
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(description="test")
        system_content = msgs[0]["content"]
        assert "NEVER suggest modifying tests" in system_content
        assert "INSTEAD say:" in system_content

    def test_build_messages_empty_diagnostic(self) -> None:
        """Messages are still valid when diagnostic is empty."""
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(description="test")
        assert "test" in msgs[1]["content"]

    def test_build_messages_includes_file_content(self) -> None:
        """User message includes file content when provided."""
        msgs = RemoteHintEngine(
            base_url="http://test.url:4160"
        )._build_messages(
            description="test", file_content="def hello():\n    pass"
        )
        assert "def hello():" in msgs[1]["content"]
        assert "pass" in msgs[1]["content"]


class TestRemoteHintEngineDepCheck:
    """Tests for dependency checking."""

    def test_check_deps_raises_when_openai_missing(self) -> None:
        """check_deps raises ImportError when openai is missing."""
        with patch.dict(
            "sys.modules",
            {"openai": None},
            clear=False,
        ):
            with pytest.raises(ImportError, match="auto-hint"):
                RemoteHintEngine.check_deps()

    def test_check_deps_succeeds_when_present(self) -> None:
        """check_deps does not raise when openai is importable."""
        import sys  # noqa: PLC0415

        fake_openai = MagicMock()
        was_present = "openai" in sys.modules
        old_module = sys.modules.get("openai")
        sys.modules["openai"] = fake_openai
        try:
            RemoteHintEngine.check_deps()  # should not raise
        finally:
            if was_present:
                assert old_module is not None
                sys.modules["openai"] = old_module
                del sys.modules["openai"]


class TestRemoteHintEngineGracefulDegradation:
    """Tests that generate_hint returns None gracefully."""

    def test_generate_hint_never_crashes(self) -> None:
        """generate_hint never crashes — returns (None, False) or (hint, bool).

        When pydantic_ai is not installed, generate_hint returns
        (None, False).  When it is installed with mocks, it returns
        a hint string.

        """
        engine = RemoteHintEngine(base_url="http://test.url:4160")
        hint, is_low_quality = engine.generate_hint(
            description="test", diagnostic="error"
        )
        if hint is not None:
            assert isinstance(hint, str) and len(hint) > 0
            assert isinstance(is_low_quality, bool)


class TestRemoteHintEngineHintValidation:
    """Tests for the _is_valid_hint static validation method."""

    def test_valid_hint_accepted(self) -> None:
        """A hint describing a code fix is accepted."""
        hint = (
            "Your function returns 1 but the test expects 2; check your logic."
        )
        assert RemoteHintEngine._is_valid_hint(hint)

    def test_test_incorrectly_rejected(self) -> None:
        """A hint suggesting the test is incorrect is rejected."""
        hint = "The test incorrectly asserts equality."
        assert not RemoteHintEngine._is_valid_hint(hint)

    def test_modify_the_test_rejected(self) -> None:
        """A hint suggesting modifying the test is rejected."""
        hint = "Modify the test to handle edge cases."
        assert not RemoteHintEngine._is_valid_hint(hint)

    def test_change_the_assertion_rejected(self) -> None:
        """A hint suggesting changing the assertion is rejected."""
        hint = "Change the assertion to expect None instead."
        assert not RemoteHintEngine._is_valid_hint(hint)

    def test_change_expected_rejected(self) -> None:
        """A hint suggesting changing expected results is rejected."""
        hint = "Change the expected result from 2 to 1."
        assert not RemoteHintEngine._is_valid_hint(hint)

    def test_case_insensitive(self) -> None:
        """Validation is case-insensitive."""
        hint = "The TEST INCORRECTLY asserts the value."
        assert not RemoteHintEngine._is_valid_hint(hint)

    def test_mentioning_test_name_is_ok(self) -> None:
        """Mentioning a test name without criticizing it is accepted."""
        hint = (
            "Your test test_count_punctuation expects 2 but got 1; "
            "check your counting logic in count_punctuation."
        )
        assert RemoteHintEngine._is_valid_hint(hint)
