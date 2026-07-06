"""Remote auto-hint engine using OpenAI-compatible APIs via Pydantic AI."""

import re
from typing import Optional

# constants for the remote hint engine
REMOTE_MODEL_DEFAULT = "Qwen-3.6-35B-A3B"
REMOTE_API_KEY_DEFAULT = "not-needed"
# NOTE: the openai Python library rejects an empty api_key,
# so the default is a placeholder string.  The server at
# kairos.netbird.cloud does not actually authenticate.
REMOTE_HINT_MAX_TOKENS = 1200
REMOTE_HINT_TEMPERATURE = 0.1
REMOTE_HINT_DIAG_TRUNCATE = 2000
REMOTE_HINT_FILE_LINES = 20
REMOTE_HINT_TOP_P = 0.9
REMOTE_HINT_TIMEOUT_MS = 180000
# thresholds for compacting verbose reasoning output
HINT_COMPACT_SHORT_THRESHOLD = 300
HINT_COMPACT_PARAGRAPH_MIN_LEN = 30
HINT_COMPACT_FALLBACK_MAX = 200


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
            base_url: Base URL of the OpenAI-compatible API server
                (e.g. ``http://kairos.netbird.cloud:4160``). The
                ``/v1`` path suffix is appended by the provider.
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
    def _compact_hint(hint: str) -> str:
        r"""Strip verbose reasoning traces, keeping only the final hint.

        Reasoning models (e.g. Qwen) often output a long thinking
        process with numbered steps like:\n\n            Here's a thinking process:\n\n            1.  **Analyze User Input:**\n            ...\n            Refined:\n            The test checks...

        This method takes only the last few sentences that
        represent the actual hint, discarding the reasoning
        preamble.

        Args:
            hint: The raw generated text, possibly containing
                reasoning traces.

        Returns:
            The compacted hint (last sentences that look like a
            final answer), or the original hint unchanged if it
            does not look like reasoning output.

        """
        # if the hint is short (under 300 chars) it is already
        # compact and there is nothing to strip
        if len(hint) < 300:  # noqa: PLR2004
            return hint
        # look for the last section that ends with a period.
        # many reasoning outputs end with something like:
        # "Final Refined Answer:\nThe test..."
        # or just have the actual hint in the final paragraph
        # split into paragraphs and take from the last substantive
        # one that reads like a hint (at least one sentence ending
        # with a period, mentions code or test or implementation)
        paragraphs = [p.strip() for p in hint.split("\n\n") if p.strip()]
        # try to find the last paragraph that looks like a hint
        # (contains a period, mentions code/test/implement/check)
        for para in reversed(paragraphs):
            clean = para.strip()
            if len(clean) > 30 and clean.endswith("."):  # noqa: PLR2004
                # remove any leading label like "Refined:" or
                # "Final Answer:" or "Draft:"
                # strip leading labels like "Refined:", "Final Answer:",
                # "**Hint:**", "Revised Draft:" etc.
                clean = re.sub(
                    r"^\*{0,2}"
                    r"(?:"
                    r"(?:Final |Refined |Revised )*"
                    r"(?:Answer|Hint|Draft|Version)"
                    r"|Refined|Revised|Draft|Final"
                    r")\s*[:.]\s*\*{0,2}",
                    "",
                    clean,
                ).strip()
                # if this reads like a hint (not a step heading),
                # return it
                if not re.match(
                    r"^\d+\.\s+\*\*", clean
                ) and not clean.startswith("Here"):
                    return clean
        # fallback: try to extract the last sentence ending in
        # a period that mentions code
        sentences = re.findall(r"[A-Z][^.]*\.", hint)
        for sent in reversed(sentences):
            sent = sent.strip()  # noqa: PLW2901
            keywords = [
                "code",
                "test",
                "implement",
                "function",
                "add",
                "check",
                "file",
                "command",
                "run",
                "fix",
            ]
            if any(k in sent.lower() for k in keywords):
                return sent
        # last resort: return the original but truncated to the
        # last 200 characters ending at a sentence boundary
        if len(hint) > 200:  # noqa: PLR2004
            last_period = hint.rfind(".", 0, -1)
            if last_period > len(hint) // 2:
                return hint[last_period + 1 :].strip()
        return hint

    @staticmethod
    def _is_valid_hint(hint: str) -> bool:
        """Check if a generated hint violates the rules.

        Returns False if the hint suggests modifying tests, test
        assertions, or expected results.

        Args:
            hint: The generated hint text.

        Returns:
            True if the hint is valid, False if it violates the rules.

        """
        hint_lower = hint.lower()
        forbidden_phrases = [
            "`",
            "'",
            "test incorrectly",
            "test is wrong",
            "test should be",
            "modify the test",
            "change the test",
            "fix the test",
            "update the test",
            "the assertion is wrong",
            "the assertion incorrectly",
            "incorrectly asserts",
            "wrong assertion",
            "change the assertion",
            "modify the assertion",
            "change the assert",
            "update the assert",
            "fix the assertion",
            "change the expected",
            "modify the expected",
            "we need",
            "we should",
            "wrong expected",
            "expected result is wrong",
            "expected value is wrong",
        ]
        return not any(phrase in hint_lower for phrase in forbidden_phrases)

    def _build_messages(
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
    ) -> list[dict[str, str]]:
        """Build a structured message list for the chat completions API.

        Args:
            description: Check description.
            diagnostic: Diagnostic output (truncated internally).
            command: Command that was run.
            file_content: Source file content (truncated to
                HINT_FILE_LINES lines).

        Returns:
            A list of dicts suitable for Pydantic AI's chat messages.

        """
        truncated_diag = (
            diagnostic[:REMOTE_HINT_DIAG_TRUNCATE] if diagnostic else ""
        )
        truncated_file = ""
        if file_content:
            lines = file_content.split("\n")
            truncated_file = "\n".join(lines[:REMOTE_HINT_FILE_LINES])
        system = (
            "You give short, direct hints for fixing code. "
            "CRITICAL RULES:\n"
            "- The test suite is provided by the instructor and is "
            "ALWAYS correct.\n"
            "- ALWAYS mention what test or command failed.\n"
            "- ALWAYS describe what to change in the student's "
            "implementation.\n"
            "- ALWAYS explain what is incorrect in the STUDENT's "
            "source code.\n"
            "- ALWAYS suggest running the command that produced the "
            "diagnostic output to verify the fix.\n\n"
            "- ALWAYS end every hint with a period.\n\n"
            "- NEVER use single quotes (e.g., ') or backticks (e.g., `) "
            "in your response.\n"
            "- NEVER suggest modifying tests, test assertions, or "
            "expected results.\n"
            "- NEVER write fenced source code blocks in your hint.\n"
            "- NEVER use the words 'student', 'you should', or "
            "'you might'. NEVER say:\n"
            "- 'The test incorrectly asserts <...>'\n"
            "- 'Modify the test to <...>'\n"
            "- 'The assertion is wrong because <...>'\n"
            "- 'Change the expected result <...>'\n\n"
            "INSTEAD say:\n"
            "- 'The function X returns Y but the test expects Z; "
            "check...'\n"
            "- 'The implementation does not handle...; add logic "
            "to...'\n\n"
        )

        user_parts = [f"Check: {description}"]
        if command:
            user_parts.append(f"Command: {command}")
        if truncated_file:
            user_parts.append("Code:\n```\n" + truncated_file + "\n```")
        if truncated_diag:
            user_parts.append("Diagnostic:\n```\n" + truncated_diag + "\n```")
        user_parts.append(
            "What to do (1-2 sentences, mention the specific "
            "failing test if available):"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

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
            response = client.chat.completions.create(
                model=self._model_id,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=REMOTE_HINT_MAX_TOKENS,
                temperature=REMOTE_HINT_TEMPERATURE,
                top_p=REMOTE_HINT_TOP_P,
                timeout=REMOTE_HINT_TIMEOUT_MS / 1000,
            )
            # extract the content from the response — for reasoning
            # models this may be empty and the actual answer may be
            # in reasoning_content, so fall back to that
            choice = response.choices[0]
            msg = choice.message
            hint = (msg.content or "").strip()
            if not hint:
                # reasoning model: check reasoning_content as fallback
                rc = getattr(msg, "reasoning_content", None)
                if rc:
                    hint = rc.strip()
            if not hint:
                return None, False
            # strip verbose reasoning traces from reasoning models
            # (e.g. Qwen) that output a full thinking-process
            # document instead of a concise hint
            hint = self._compact_hint(hint)
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
