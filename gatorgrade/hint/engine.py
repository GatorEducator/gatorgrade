"""Auto-hint engine using Hugging Face ``transformers`` for local hint generation."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

# type-checking-only import — never executed at runtime.
if TYPE_CHECKING:
    import transformers  # noqa: F401

# default model for auto-hinting (note that these
# names are the same as those provided on Hugging Face)
DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"

# default values for running the local LLMs
# with the transformers package
HINT_MAX_TOKENS = 80
HINT_TEMPERATURE = 0.1
HINT_DIAG_TRUNCATE = 2000
HINT_FILE_LINES = 20
HINT_REPETITION_PENALTY = 1.2
HINT_TOP_P = 0.9

HINT_SUPPRESSED_MESSAGE = (
    "Auto-hint suppressed: the generated hint suggested modifying tests, "
    "assertions, or expected results and was not displayed."
)

TEXT_GENERATION_TASK: Literal["text-generation"] = "text-generation"

CACHE_DIR_KEY = "cache_dir"
ENV_CACHE_DIR = "GATORGRADE_MODELS_DIR"

GEMMA4_MODEL_TYPE = "gemma4"
GEMMA4_TRANSFORMERS_ERROR = (
    "Model '{model_id}' requires transformers >= 5.x, which supports the "
    "'gemma4' architecture. Upgrade with: uv pip install -U transformers"
)


def _model_cache_dir(override: Optional[Path] = None) -> Path:
    """Return the gatorgrade-specific directory where models are cached.

    Precedence:

    1. ``override`` parameter
    2. ``$GATORGRADE_MODELS_DIR`` environment variable
    3. ``platformdirs.user_cache_dir("gatorgrade") / "models"``
    4. ``~/.cache/gatorgrade/models/`` (fallback)

    """
    if override is not None:
        return override
    env_dir = os.environ.get(ENV_CACHE_DIR)
    if env_dir:
        return Path(env_dir)
    try:
        import platformdirs  # noqa: PLC0415

        return (
            Path(platformdirs.user_cache_dir("gatorgrade", appauthor=False))
            / "models"
        )
    except ImportError:
        pass
    return Path.home() / ".cache" / "gatorgrade" / "models"


class AutoHintEngine:
    """Lazy-loading engine that generates hints for failing checks.

    The model is **not** downloaded or loaded when the engine is
    constructed — that happens on the first call to
    :meth:`generate_hint`.  If ``transformers`` is missing,
    :meth:`generate_hint` returns ``None`` (graceful degradation).

    Usage::

        engine = AutoHintEngine()
        hint = engine.generate_hint(
            description="Check that hello.py exists",
            diagnostic="File not found",
            command="ls hello.py",
        )
        if hint:
            print(f"  Hint: {hint}")
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        cache_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the engine.

        Args:
            model_id: Hugging Face model ID (e.g.
                ``HuggingFaceTB/SmolLM2-135M-Instruct``).
            cache_dir: Optional path for the model cache.
                Can also be set via ``$GATORGRADE_MODELS_DIR``.

        """
        self._model_id = model_id
        self._cache_dir_override = cache_dir
        # the text-generation pipeline, populated by _ensure_loaded().
        self._pipe: Any = None
        # path to the cached model directory (set after loading).
        self._model_path: Optional[Path] = None

    @staticmethod
    def check_deps() -> None:
        """Verify that ``transformers`` and ``torch`` are importable.

        This is an **eager** check (no model download) so callers
        can give the user a clear error message right away instead
        of discovering the missing dependency silently later.

        Raises:
            ImportError: If ``transformers`` or ``torch`` is not
                installed.

        """
        missing = []
        try:
            import transformers  # noqa: PLC0415, F401
        except ImportError:
            missing.append("transformers")
        try:
            import torch  # noqa: PLC0415, F401
        except ImportError:
            missing.append("torch")

        if missing:
            names = " and ".join(missing)
            raise ImportError(
                f"The 'auto-hint' extra is required to generate hints "
                f"({names} not found).\n\n"
            ) from None

    @property
    def model_id(self) -> str:
        """Hugging Face model ID."""
        return self._model_id

    @property
    def cache_dir(self) -> Path:
        """Return the gatorgrade-specific directory for caching models.

        Uses ``platformdirs.user_cache_dir("gatorgrade") / "models"``
        so models live in the standard per-user cache location.
        """
        return _model_cache_dir(override=self._cache_dir_override)

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been downloaded and loaded into memory."""
        return self._pipe is not None

    def _ensure_loaded(self) -> None:
        """Download (if needed) and load the model into memory.

        Raises:
            ImportError: If ``transformers`` is not installed.
            Exception: Any exception from the download or load process
                (caught by :meth:`generate_hint` and turned into
                ``None``).

        """
        if self._pipe is not None:
            return
        # ensure the cache directory exists.
        cache_dir = self.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        # lazily import the optional dependency.
        try:
            from transformers import AutoConfig, pipeline  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(
                "The 'auto-hint' extra is required to generate hints.\n\n"
                "Install it with one of these commands:\n\n"
                "  uv tool install --from 'gatorgrade[auto-hint]' gatorgrade\n"
                "  uvx --from 'gatorgrade[auto-hint]' gatorgrade --auto-hint\n"
                "  pip install 'gatorgrade[auto-hint]'\n"
            ) from e
        # suppress the chatty "Device set to use cpu" message that
        # transformers prints to stderr and would garble our progress bar.
        import transformers as _tf_mod  # noqa: PLC0415

        _tf_mod.logging.set_verbosity_error()
        # inspect the model config before downloading weights; this only
        # fetches the small config.json file and lets us pick the right
        # loader for multimodal checkpoints such as Gemma 4.
        try:
            config = AutoConfig.from_pretrained(
                self._model_id, **{CACHE_DIR_KEY: str(cache_dir)}
            )
            model_type = getattr(config, "model_type", None)
        except ValueError as exc:
            # transformers < 5.x does not know the gemma4 architecture,
            # so surface a clear, actionable message instead of the raw
            # "architecture not recognized" error.
            if GEMMA4_MODEL_TYPE in str(exc).lower():
                raise RuntimeError(
                    GEMMA4_TRANSFORMERS_ERROR.format(model_id=self._model_id)
                ) from exc
            raise

        pipe_kwargs: dict[str, Any] = {
            "model_kwargs": {CACHE_DIR_KEY: str(cache_dir)}
        }
        if model_type == GEMMA4_MODEL_TYPE:
            # gemma 4 checkpoints are multimodal and require the
            # trust_remote_code flag for the text-generation pipeline.
            pipe_kwargs["trust_remote_code"] = True

        # download and load the model via the text-generation pipeline.
        # (model is cached after first download — subsequent runs are fast.)
        self._pipe = pipeline(
            TEXT_GENERATION_TASK,
            model=self._model_id,
            **pipe_kwargs,
        )

    # -- hint generation --------------------------------------------------

    @staticmethod
    def _is_valid_hint(hint: str) -> bool:
        """Check if a generated hint violates the rules.

        Returns False if the hint suggests modifying tests, test assertions,
        or expected results.  Uses fuzzy matching to catch near-matches
        (e.g. "Update the `assert` statement ...").

        Args:
            hint: The generated hint text.

        Returns:
            True if the hint is valid, False if it violates the rules.

        """
        hint_lower = hint.lower()
        # phrases that suggest modifying the test itself
        forbidden_phrases = [
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

    def generate_hint(  # noqa: PLR0911
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
    ) -> Optional[str]:
        """Generate a short hint for a failing check.

        Safe to call even when ``transformers`` is missing — returns
        ``None`` (graceful degradation).

        Args:
            description: Human-readable description of the check.
            diagnostic: Diagnostic output from the failing check.
                May be truncated to ``HINT_DIAG_TRUNCATE`` characters.
            command: The shell / GatorGrader command that was run, if
                available.
            file_content: The contents of the source file being
                checked, if available. Truncated to ``HINT_FILE_LINES``
                lines.

        Returns:
            A short hint string, or ``None`` if generation failed or
            ``transformers`` is not installed.

        """
        try:
            self._ensure_loaded()
        except ImportError:
            return None
        except Exception as exc:  # pylint: disable=broad-except
            print(
                f"   → Auto-hint error (loading): {exc}",
                file=__import__("sys").stderr,
            )
            return None

        messages = self._build_messages(
            description, diagnostic, command, file_content
        )

        try:
            # the pipeline applies the model's chat template internally,
            # formats the messages, and generates the assistant's reply.
            # with return_full_text=False we get back *only* the newly
            # generated text (the hint) as a plain string.
            result = self._pipe(
                messages,
                max_new_tokens=HINT_MAX_TOKENS,
                temperature=HINT_TEMPERATURE,
                top_p=HINT_TOP_P,
                repetition_penalty=HINT_REPETITION_PENALTY,
                do_sample=True,
                return_full_text=False,
            )
            # result is a list of dicts, one per conversation.
            # each dict has a "generated_text" key with the raw string.
            if not result:
                return None
            hint = str(result[0]["generated_text"]).strip()
            if not hint:
                return None
            # validate the hint does not suggest modifying tests
            if not self._is_valid_hint(hint):
                # return a friendly suppression message so the CLI displays
                # an informative placeholder instead of the model's output.
                return HINT_SUPPRESSED_MESSAGE
            return hint
        except Exception as exc:  # pylint: disable=broad-except
            print(
                f"   → Auto-hint error (generation): {exc}",
                file=__import__("sys").stderr,
            )
            return None

    # -- message building -------------------------------------------------

    def _build_messages(
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
    ) -> list[dict[str, str]]:
        """Build a structured message list for the chat pipeline.

        Args:
            description: Check description.
            diagnostic: Diagnostic output (truncated internally).
            command: Command that was run.
            file_content: Source file content (truncated to HINT_FILE_LINES lines).

        Returns:
            A list of ``{"role": …, "content": …}`` dicts suitable for
            ``transformers`` pipeline's chat template handling.

        """
        truncated_diag = diagnostic[:HINT_DIAG_TRUNCATE] if diagnostic else ""
        # truncate file content to HINT_FILE_LINES complete lines
        truncated_file = ""
        if file_content:
            lines = file_content.split("\n")
            truncated_file = "\n".join(lines[:HINT_FILE_LINES])

        system = (
            "You give short, direct hints for fixing code. "
            "CRITICAL RULES:\n"
            "- The test suite is provided by the instructor and is ALWAYS correct.\n"
            "- ALWAYS mention what test or command failed.\n"
            "- ALWAYS describe what to change in the student's implementation.\n"
            "- ALWAYS explain what is incorrect in the STUDENT's source code.\n"
            "- ALWAYS suggest running the command that produced the diagnostic output to verify the fix.\n\n"
            "- ALWAYS end every hint with a period.\n\n"
            "- NEVER suggest modifying tests, test assertions, or expected results.\n"
            "- NEVER write fenced source code blocks in your hint.\n"
            "- NEVER use the words 'student', 'you should', or 'you might'. "
            "NEVER say:\n"
            "- 'The test incorrectly asserts <...>'\n"
            "- 'Modify the test to <...>'\n"
            "- 'The assertion is wrong because <...>'\n"
            "- 'Change the expected result <...>'\n\n"
            "INSTEAD say:\n"
            "- 'The function X returns Y but the test expects Z; check...'\n"
            "- 'The implementation does not handle...; add logic to...'\n\n"
            # "Examples:\n"
            # "- 'The test test_run_machine_max_steps expects 10 steps but the program produces 9; check the loop counter in the max_steps function.'\n"
            # "- 'The function count_punctuation returns 1 for \"Hello, world!\" but the test expects 2; ensure both comma and exclamation mark are counted.'\n"
            # "- 'The test test_calculate_average expects 5.0 but got ZeroDivisionError; check that calculate_average handles an empty list before dividing.'"
        )

        user_parts = [f"Check: {description}"]
        if command:
            user_parts.append(f"Command: {command}")
        if truncated_file:
            user_parts.append("Code:\n```\n" + truncated_file + "\n```")
        if truncated_diag:
            user_parts.append(f"Diagnostic:\n```\n{truncated_diag}\n```")
        user_parts.append(
            "What to do (1-2 sentences, mention the specific "
            "failing test if available):"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]
