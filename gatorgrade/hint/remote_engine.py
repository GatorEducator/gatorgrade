"""Remote auto-hint engine using OpenAI-compatible APIs."""

import os
from typing import Optional, cast

from gatorgrade.hint.support import (
    EXTRA_AUTO_HINTS_INSTALLATION_INSTRUCTIONS,
    build_hint_messages,
    is_valid_hint,
)
from gatorgrade.version import GATORGRADE_VERSION

# basic constants
EMPTY = ""

# constants for the remote hint engine
REMOTE_MODEL_DEFAULT = "Qwen/Qwen3.6-35B-A3B"
REMOTE_KEY_ENV_DEFAULT = "AUTO_HINT_KEY_ENV"
REMOTE_API_KEY_DEFAULT = "not-needed"
MISSING_KEY_ENV_ERROR = (
    "API key environment variable {} is not set. Save it in your shell "
    "startup file or Windows user environment for future sessions, then "
    "restart your terminal or IDE; see README."
)

# the openai client rejects an empty API key, so keyless servers receive
# a non-secret placeholder when the default environment variable is unset.
REMOTE_HINT_TIMEOUT_MS = 180000

# retain these public constants for import compatibility; remote requests
# now use server defaults instead of forcing these generation settings.
REMOTE_HINT_MAX_TOKENS = 1200
REMOTE_HINT_TEMPERATURE = 0.1

# custom user-agent header sent with every request to the remote API
# server; some reverse proxies, such as cloudflare WAF, block the
# default user-agent string that the openai Python library sends
# (e.g., "OpenAI/Python 2.44.0"), causing a silent 403 response;
# overriding the user-agent with a project-specific value avoids
# these false-positive blocks while still identifying the client
USER_AGENT_KEY = "User-Agent"
USER_AGENT_VALUE = f"gatorgrade/{GATORGRADE_VERSION}"

# constants for the remote hint engine
REASONING_CONTENT_KEY = "reasoning_content"


class RemoteHintEngine:
    """Engine that generates hints via an OpenAI-compatible remote API.

    Uses the OpenAI package to talk to any server that
    exposes an OpenAI-compatible chat completions endpoint.

    Wraps the call in a try/except so failures (connection refused,
    timeout, etc.) are surfaced to the caller, which can then fall
    back to the local engine. That is, if the remote engine does
    not work, this information is logged and displayed and then there
    is an attempt to automatically generate the hints with a local model.

    The engine overrides the default user-agent header sent by the
    openai python library; some reverse proxies and WAFs, such as
    cloudflare, block the default openai/python user-agent string
    (e.g. OpenAI/Python 2.44.0) and respond with HTTP 403; using
    a project-specific user-agent (e.g., gatorgrade/0.11.0) avoids these
    false-positive blocks while still identifying the client.

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
        api_key_env: str | None = None,
        model_id: str = REMOTE_MODEL_DEFAULT,
        system_prompt: str | None = None,
        validation_rules: dict[str, list[str]] | None = None,
    ) -> None:
        """Initialize the remote hint engine.

        Args:
            base_url: Base URL of an OpenAI-compatible API server.
                The /v1 path suffix is appended by the provider.
            api_key_env: API key environment variable name. When omitted,
                AUTO_HINT_KEY_ENV is used when set, otherwise a placeholder
                supports servers that do not require authentication.
            model_id: Name of the model exposed at the server.
            system_prompt: Optional custom system prompt.
                If provided, this replaces the built-in default.
            validation_rules: Optional dict with must_contain
                and/or cannot_contain lists of phrases to
                check, in addition to the built-in quality rules.

        """
        self._base_url = base_url
        self._api_key_env = (
            api_key_env if api_key_env is not None else REMOTE_KEY_ENV_DEFAULT
        )
        self._api_key = self._get_env_val_from_var(self._api_key_env)
        if api_key_env is None and not self._api_key:
            self._api_key = REMOTE_API_KEY_DEFAULT
        self._model_id = model_id
        self._system_prompt = system_prompt
        self._validation_rules = validation_rules
        self.last_error: str | None = None

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
    def _get_env_val_from_var(env_variable: str) -> str | None:
        """Return the value of an environment variable.

        Args:
            env_variable: Name of the variable where API key is stored.

        Returns:
            The variable value, or None when it is unset.

        """
        return os.environ.get(env_variable)

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
            file_content: Source file content.
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
                EXTRA_AUTO_HINTS_INSTALLATION_INSTRUCTIONS
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

        Safe to call even when the openai library is missing; in this case
        it will return (None, False) for graceful degradation.

        Args:
            description: Human-readable description of the check.
            diagnostic: Diagnostic output from the failing check.
            command: The shell / GatorGrader command that was run.
            file_content: The contents of the source file being
                checked, if available.
            system_prompt: Optional custom system prompt.
            details: Structured details about the check
                configuration (e.g., options and expected values).

        Returns:
            A tuple (hint, is_low_quality) where:

            - hint: The generated hint string, or None if generation
              failed.
            - is_low_quality: True when the hint suggests modifying
              tests or assertions.

        """
        if not self._api_key:
            self.last_error = MISSING_KEY_ENV_ERROR.format(self._api_key_env)
            return None, False
        # lazily import the openai client only when needed.
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError:
            self.last_error = EXTRA_AUTO_HINTS_INSTALLATION_INSTRUCTIONS
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
            # reasoning_content rather than content; the user-agent is
            # overridden because some reverse proxies and WAFs, like
            # cloudflare, block the default openai/python user-agent string
            client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                default_headers={USER_AGENT_KEY: USER_AGENT_VALUE},
            )
            from openai.types.chat import (  # noqa: PLC0415
                ChatCompletionMessageParam,
            )

            typed_messages: list[ChatCompletionMessageParam] = cast(
                list[ChatCompletionMessageParam], messages
            )
            # send only the required chat completion fields; optional token,
            # sampling, and thinking controls vary by model and provider.
            # use server defaults rather than inferring support from a name.
            response = client.chat.completions.create(
                model=self._model_id,
                messages=typed_messages,
                timeout=REMOTE_HINT_TIMEOUT_MS / 1000,
            )
            # extract the content from the response; for reasoning
            # models this may be empty and the actual answer may be
            # in reasoning_content, so fall back to that
            choice = response.choices[0]
            msg = choice.message
            hint = (msg.content or EMPTY).strip()
            if not hint:
                # some servers put the answer in reasoning_content,
                # so preserve this fallback when content is empty.
                rc = getattr(msg, REASONING_CONTENT_KEY, None)
                if rc:
                    hint = rc.strip()
            if not hint:
                return None, False
            if not self._is_valid_hint(
                hint, custom_rules=self._validation_rules
            ):
                return hint, True
            return hint, False
        except Exception as exc:  # pylint: disable=broad-except
            self.last_error = str(exc)[:300]
            # return None so the caller's fallback engine can
            # try the local model instead, using the default
            # local model which should always install and run
            return None, False
