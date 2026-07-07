"""Remote auto-hint engine using OpenAI-compatible APIs."""

from typing import Optional, cast

from gatorgrade.hint.support import build_hint_messages, is_valid_hint

# constants for the remote hint engine
REMOTE_MODEL_DEFAULT = "Qwen/Qwen3.6-35B-A3B"
REMOTE_API_KEY_DEFAULT = "not-needed"

# the openai Python library rejects an empty api_key, so
# the default is a placeholder string for servers that do
# not require authentication.
REMOTE_HINT_MAX_TOKENS = 1200
REMOTE_HINT_TEMPERATURE = 0.1
REMOTE_HINT_DIAG_TRUNCATE = 2000
REMOTE_HINT_FILE_LINES = 20
REMOTE_HINT_TOP_P = 0.9
REMOTE_HINT_TIMEOUT_MS = 180000

# extra_body sent to disable visible thinking traces on Qwen
# reasoning models; the model still reasons internally but the
# response contains only the final answer in the content field.
ENABLE_THINKING_KEYWORD = "enable_thinking"
CHAT_TEMPLATE_KWARGS_KEYWORD = "chat_template_kwargs"
THINKING_DEFAULT_VALUE = False
ENABLE_THINKING_DEFAULT = {
    CHAT_TEMPLATE_KWARGS_KEYWORD: {
        ENABLE_THINKING_KEYWORD: THINKING_DEFAULT_VALUE
    }
}


class RemoteHintEngine:
    """Engine that generates hints via an OpenAI-compatible remote API.

    Uses the OpenAI package to talk to any server that
    exposes an OpenAI-compatible chat completions endpoint.

    Wraps the call in a try/except so failures (connection refused,
    timeout, etc.) are surfaced to the caller, which can then fall
    back to the local engine. That is, if the remote engine does
    not work, this information is logged and displayed and then there
    is an attempt to automatically generate the hints with a local model.

    Usage:

        engine = RemoteHintEngine(
            base_url="http://<server name>:<port>",
            model_id="Qwen/Qwen3.6-35B-A3B",
        )
        hint, is_low = engine.generate_hint(
            description="Check that hello.py exists",
            diagnostic="File not found",
            command="ls hello.py",
        )
    """

    def __init__(
        self,
        base_url: str,
        api_key: str = REMOTE_API_KEY_DEFAULT,
        model_id: str = REMOTE_MODEL_DEFAULT,
        system_prompt: str | None = None,
        validation_rules: dict[str, list[str]] | None = None,
    ) -> None:
        """Initialize the remote hint engine.

        Args:
            base_url: Base URL of an OpenAI-compatible API server.
                The /v1 path suffix is appended by the provider.
            api_key: API key for the server, if required.
            model_id: Name of the model exposed at the server.
            system_prompt: Optional custom system prompt.
                If provided, this replaces the built-in default.
            validation_rules: Optional dict with must_contain
                and/or cannot_contain lists of phrases to
                check, in addition to the built-in quality rules.

        """
        self._base_url = base_url
        self._api_key = api_key
        self._model_id = model_id
        self._system_prompt = system_prompt
        self._validation_rules = validation_rules

    @property
    def model_id(self) -> str:
        """Return the model identifier."""
        return self._model_id

    @property
    def is_loaded(self) -> bool:
        """Remote engine is always considered "loaded" (no download).

        There is no heavyweight local model to download, so the
        engine is immediately ready.  The first call may still
        fail due to network issues.

        """
        return True

    def ensure_loaded(self) -> None:
        """No-op for the remote engine.

        The remote model is served by the API server and does not
        need to be downloaded or loaded locally.
        """

    @staticmethod
    def _is_valid_hint(
        hint: str,
        custom_rules: dict[str, list[str]] | None = None,
    ) -> bool:
        """Check if a generated hint passes the quality rules.

        Static so it can be called without an instance (e.g., in
        tests). Pass custom_rules to augment the built-in
        rules.

        Args:
            hint: The generated hint text.
            custom_rules: Optional custom rules in addition to
                the built-in rules.

        Returns:
            True if the hint passes all quality checks, False if
            it fails any check.

        """
        return is_valid_hint(hint, custom_rules=custom_rules)

    def _build_messages(  # noqa: PLR0913
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
        system_prompt: str | None = None,
        details: str = "",
    ) -> list[dict[str, str]]:
        """Build a structured message list for the chat completions API.

        Delegates to the shared implementation.

        Args:
            description: Check description.
            diagnostic: Diagnostic output (truncated internally).
            command: Command that was run.
            file_content: Source file content (truncated to
                HINT_FILE_LINES lines).
            system_prompt: Optional custom system prompt.
            details: Structured details about the check
                configuration.

        Returns:
            A list of dicts suitable for chat-based inference.

        """
        return build_hint_messages(
            description=description,
            diagnostic=diagnostic,
            command=command,
            file_content=file_content,
            system_prompt=system_prompt,
            details=details,
        )

    @staticmethod
    def check_deps() -> None:
        """Verify that openai is importable.

        Raises:
            ImportError: If openai is not installed.

        """
        try:
            import openai as _openai_check  # noqa: PLC0415,F401
        except ImportError as e:
            raise ImportError(
                "The 'auto-hint' extra is required to generate hints.\n\n"
                "Install it with one of these commands:\n\n"
                "  uv tool install --from 'gatorgrade[auto-hint]'"
                " gatorgrade\n"
                "  uvx --from 'gatorgrade[auto-hint]'"
                " gatorgrade --auto-hint\n"
                "  pip install 'gatorgrade[auto-hint]'\n"
            ) from e

    def generate_hint(  # noqa: PLR0913
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
        system_prompt: str | None = None,
        details: str = "",
    ) -> tuple[Optional[str], bool]:
        """Generate a short hint by calling the remote OpenAI-compatible API.

        Safe to call even when pydantic_ai is missing; in this case
        it will return (None, False) for graceful degradation.

        Args:
            description: Human-readable description of the check.
            diagnostic: Diagnostic output from the failing check.
            command: The shell / GatorGrader command that was run.
            file_content: The contents of the source file being
                checked, if available.
            system_prompt: Optional custom system prompt.
            details: Structured details about the check
                configuration (e.g. options and expected values).

        Returns:
            A tuple (hint, is_low_quality) where:

            - hint: The generated hint string, or None if generation
              failed.
            - is_low_quality: True when the hint suggests modifying
              tests or assertions.

        """
        try:
            # lazily import the openai client only when needed.
            from openai import OpenAI  # noqa: PLC0415
        except ImportError:
            return None, False

        # use the per-call system_prompt if provided, otherwise
        # fall back to the engine-level prompt or the built-in default
        effective_prompt = system_prompt or self._system_prompt
        messages = self._build_messages(
            description,
            diagnostic,
            command,
            file_content,
            system_prompt=effective_prompt,
            details=details,
        )

        try:
            # call the OpenAI-compatible API directly using the
            # raw Chat Completions format, which handles reasoning
            # models (e.g., Qwen and others) that put their response in
            # reasoning_content rather than content
            client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
            )
            from openai.types.chat import (  # noqa: PLC0415
                ChatCompletionMessageParam,
            )

            typed_messages: list[ChatCompletionMessageParam] = cast(
                list[ChatCompletionMessageParam], messages
            )
            response = client.chat.completions.create(
                model=self._model_id,
                messages=typed_messages,
                max_tokens=REMOTE_HINT_MAX_TOKENS,
                temperature=REMOTE_HINT_TEMPERATURE,
                top_p=REMOTE_HINT_TOP_P,
                timeout=REMOTE_HINT_TIMEOUT_MS / 1000,
                extra_body=ENABLE_THINKING_DEFAULT,
            )
            # extract the content from the response — for reasoning
            # models this may be empty and the actual answer may be
            # in reasoning_content, so fall back to that
            choice = response.choices[0]
            msg = choice.message
            hint = (msg.content or "").strip()
            if not hint:
                # note: with enable_thinking=False the model should
                # produce content directly. however, some servers
                # may still put the answer in reasoning_content,
                # so fall back to that.
                rc = getattr(msg, "reasoning_content", None)
                if rc:
                    hint = rc.strip()
            if not hint:
                return None, False
            if not self._is_valid_hint(
                hint, custom_rules=self._validation_rules
            ):
                return hint, True
            return hint, False
        except Exception:  # pylint: disable=broad-except
            # return None so the caller's fallback engine can
            # try the local model instead
            return None, False
