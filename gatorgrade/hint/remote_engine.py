"""Remote auto-hint engine using OpenAI-compatible APIs."""

from typing import Optional, cast

from gatorgrade.hint.support import build_hint_messages, is_valid_hint

# constants for the remote hint engine
REMOTE_MODEL_DEFAULT = "Qwen-3.6-35B-A3B"
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
# reasoning models.  The model still reasons internally but the
# response contains only the final answer in the content field.
EXTRA_BODY_DISABLE_THINKING: dict = {
    "chat_template_kwargs": {"enable_thinking": False},
}


class RemoteHintEngine:
    """Engine that generates hints via an OpenAI-compatible remote API.

    Uses Pydantic AI's OpenAIChatModel to talk to any server that
    exposes an OpenAI-compatible chat completions endpoint.

    Wraps the call in a try/except so failures (connection refused,
    timeout, etc.) are surfaced to the caller, which can then fall
    back to the local engine.

    Usage::

        engine = RemoteHintEngine(
            base_url="http://kairos.netbird.cloud:4160",
            model_id="Qwen-3.6-35B-A3B",
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
    ) -> None:
        """Initialise the remote hint engine.

        Args:
            base_url: Base URL of an OpenAI-compatible API server.
                The /v1 path suffix is appended by the provider.
            api_key: API key for the server, if required.
            model_id: Name of the model exposed at the server.

        """
        self._base_url = base_url
        self._api_key = api_key
        self._model_id = model_id

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
    def _is_valid_hint(hint: str) -> bool:
        """Check if a generated hint violates the rules.

        Delegates to the shared implementation.

        Args:
            hint: The generated hint text.

        Returns:
            True if the hint is valid, False if it violates.

        """
        return is_valid_hint(hint)

    def _build_messages(
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
    ) -> list[dict[str, str]]:
        """Build a structured message list for the chat completions API.

        Delegates to the shared implementation.

        Args:
            description: Check description.
            diagnostic: Diagnostic output (truncated internally).
            command: Command that was run.
            file_content: Source file content (truncated to
                HINT_FILE_LINES lines).

        Returns:
            A list of dicts suitable for chat-based inference.

        """
        return build_hint_messages(
            description=description,
            diagnostic=diagnostic,
            command=command,
            file_content=file_content,
        )

    @staticmethod
    def check_deps() -> None:
        """Verify that openai is importable.

        Raises:
            ImportError: If openai is not installed.

        """
        try:
            import openai as _openai_check  # noqa: PLC0415,F401
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for remote hint "
                "generation. Install it with one of these commands:\n\n"
                "  pip install openai\n"
                "  uv add openai\n"
            ) from None

    def generate_hint(
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
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

        Returns:
            A tuple (hint, is_low_quality) where:

            - hint: The generated hint string, or None if generation
              failed.
            - is_low_quality: True when the hint suggests modifying
              tests or assertions.

        """
        try:
            # lazily import the openai client only when needed.
            # pydantic-ai-slim[openai] is NOT a declared project
            # dependency — users must install it separately if they
            # want remote hinting.  When it is missing, generate_hint
            # returns None and the caller falls back to the local
            # hugging Face engine.
            from openai import OpenAI  # noqa: PLC0415
        except ImportError:
            return None, False

        messages = self._build_messages(
            description, diagnostic, command, file_content
        )

        try:
            # call the OpenAI-compatible API directly using the
            # raw Chat Completions format, which handles reasoning
            # models (e.g. Qwen) that put their response in
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
                extra_body=EXTRA_BODY_DISABLE_THINKING,
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
            if not self._is_valid_hint(hint):
                return hint, True
            return hint, False
        except Exception as exc:  # pylint: disable=broad-except
            # print a useful warning so the caller knows
            # the remote attempt failed and can fall back
            print(
                f"   → Remote hint error: {exc}",
                file=__import__("sys").stderr,
            )
            return None, False
