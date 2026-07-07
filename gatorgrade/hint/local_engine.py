"""Auto-hint engine for generating hints with local transformers models."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

from gatorgrade.hint.support import build_hint_messages, is_valid_hint

if TYPE_CHECKING:
    import transformers  # noqa: F401

# default model for auto-hinting (note that this names,
# and those accepted on the command-line, are expected to be
# the same as those provided on Hugging Face)
DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"

# default values for running the local LLMs
# with the transformers package
HINT_MAX_TOKENS = 80
HINT_TEMPERATURE = 0.1
HINT_DIAG_TRUNCATE = 2000
HINT_FILE_LINES = 20
HINT_REPETITION_PENALTY = 1.2
HINT_TOP_P = 0.9

# default task for the local LLM
TEXT_GENERATION_TASK: Literal["text-generation"] = "text-generation"

# default locations in the file system
CACHE_DIR_KEY = "cache_dir"
ENV_CACHE_DIR = "GATORGRADE_MODELS_DIR"
GENERATED_TEXT_KEY = "generated_text"


def _model_cache_dir(override: Optional[Path] = None) -> Path:
    """Return the gatorgrade-specific directory where models are cached.

    Precedence for the gatorgrade-specific directory:

    1. override parameter
    2. $GATORGRADE_MODELS_DIR environment variable
    3. platformdirs.user_cache_dir("gatorgrade") / "models"

    """
    if override is not None:
        return override
    env_dir = os.environ.get(ENV_CACHE_DIR)
    if env_dir:
        return Path(env_dir)
    import platformdirs  # noqa: PLC0415

    return (
        Path(platformdirs.user_cache_dir("gatorgrade", appauthor=False))
        / "models"
    )


def _platform_model_cache_dir() -> Path:
    """Return the platform-level default model cache directory.

    Unlike _model_cache_dir, this ignores the $GATORGRADE_MODELS_DIR
    environment variable and always returns the platformdirs-based
    default. This is useful for display purposes (e.g., --version)
    so users can see the underlying default even when an override is
    active.

    Returns:
        The platform-level default model cache directory path.

    """
    import platformdirs  # noqa: PLC0415

    return (
        Path(platformdirs.user_cache_dir("gatorgrade", appauthor=False))
        / "models"
    )


class AutoHintEngine:
    """Lazy-loading engine that generates hints for failing checks.

    The model is not downloaded or loaded when the engine is
    constructed.  That happens on the first call to
    generate_hint.  If transformers is missing,
    generate_hint returns None (graceful degradation).

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
        system_prompt: str | None = None,
        validation_rules: dict[str, list[str]] | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            model_id: Hugging Face model ID.
            cache_dir: Optional path for the model cache.
                Can also be set via $GATORGRADE_MODELS_DIR.
            system_prompt: Optional custom system prompt.
                If provided, this replaces the built-in default.
            validation_rules: Optional dict with must_contain
                and/or cannot_contain lists of phrases to
                check, in addition to the built-in quality rules.

        """
        self._model_id = model_id
        self._cache_dir_override = cache_dir
        self._system_prompt = system_prompt
        self._validation_rules = validation_rules
        # the text-generation pipeline, populated by _ensure_loaded().
        self._pipe: Any = None
        # path to the cached model directory (set after loading).
        self._model_path: Optional[Path] = None

    @staticmethod
    def check_deps() -> None:
        """Verify that transformers and torch are importable.

        This is an eager check (no model download) so callers
        can give the user a clear error message right away instead
        of discovering the missing dependency silently later.

        Raises:
            ImportError: If transformers or torch is not
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

        Uses platformdirs.user_cache_dir("gatorgrade") / "models"
        so models live in the standard per-user cache location.
        """
        return _model_cache_dir(override=self._cache_dir_override)

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been downloaded and loaded into memory."""
        return self._pipe is not None

    def ensure_loaded(self) -> None:
        """Download (if needed) and load the model into memory.

        This is the public entry point for loading the model, with
        all chatty Hugging Face progress bars and diagnostic output
        suppressed.  Safe to call multiple times.  Subsequent calls
        are a no-op once the model is already loaded.

        Raises:
            ImportError: If transformers is not installed.
            Exception: Any exception from the download or load process
                (caught by generate_hint and turned into None).

        """
        if self._pipe is not None:
            return
        # ensure the cache directory exists.
        cache_dir = self.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        # lazily import the optional dependency.
        try:
            from transformers import pipeline  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(
                "The 'auto-hint' extra is required to generate hints.\n\n"
                "Install it with one of these commands:\n\n"
                "  uv tool install --from 'gatorgrade[auto-hint]' gatorgrade\n"
                "  uvx --from 'gatorgrade[auto-hint]' gatorgrade --auto-hint\n"
                "  pip install 'gatorgrade[auto-hint]'\n"
            ) from e
        # suppress all chatty Hugging Face output: logging messages,
        # progress bars for downloading, and progress bars for loading
        # weights; these would appear inline during the standard
        # gatorgrade output and confuse students
        import transformers as _tf_mod  # noqa: PLC0415

        _tf_mod.logging.set_verbosity_error()
        _tf_mod.logging.disable_progress_bar()
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        # also suppress any stray output that prints to stderr
        # during the pipeline construction (e.g."Device set to use
        # cpu" messages or other low-level diagnostics)
        pipe_kwargs: dict[str, Any] = {
            "model_kwargs": {CACHE_DIR_KEY: str(cache_dir)}
        }
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        os.dup2(devnull_fd, 2)
        try:
            # download and load the model via the text-generation pipeline
            self._pipe = pipeline(
                TEXT_GENERATION_TASK,
                model=self._model_id,
                **pipe_kwargs,
            )
        finally:
            os.dup2(old_stderr, 2)
            os.close(old_stderr)
            os.close(devnull_fd)

    def _ensure_loaded(self) -> None:
        """Delegate to the public ensure_loaded method.

        Kept for backward compatibility; new code should call
        ensure_loaded directly.

        """
        self.ensure_loaded()

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

    def generate_hint(  # noqa: PLR0911, PLR0913
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
        system_prompt: str | None = None,
        details: str = "",
    ) -> tuple[Optional[str], bool]:
        """Generate a short hint for a failing check.

        Safe to call even when transformers is missing; in this
        case it will return (None, False) as a means of
        supporting graceful degradation.

        Args:
            description: Human-readable description of the check.
            diagnostic: Diagnostic output from the failing check.
                May be truncated to HINT_DIAG_TRUNCATE characters.
            command: The shell / GatorGrader command that was run, if
                available.
            file_content: The contents of the source file being
                checked, if available. Truncated to HINT_FILE_LINES
                lines.
            system_prompt: Optional custom system prompt. If
                provided, overrides both the engine-level default
                and the built-in prompt.
            details: Structured details about the check
                configuration (e.g. options and expected values).

        Returns:
            A tuple (hint, is_low_quality):

            - hint: The generated hint string, or None if
              generation failed or transformers is not installed;
              (note that transformers is only installed when
              the extra auto-hinting dependency is installed).
            - is_low_quality: True when the generated hint
              suggests modifying tests/assertions (it is still returned
              so the caller can decide how to present it).

        """
        try:
            self._ensure_loaded()
        except ImportError:
            return None, False
        except Exception as exc:  # pylint: disable=broad-except
            print(
                f"   → Auto-hint error (loading): {exc}",
                file=__import__("sys").stderr,
            )
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
            # the pipeline applies the model's chat template internally,
            # formats the messages, and generates the assistant's reply;
            # with return_full_text=False we get back *only* the newly
            # generated text (the hint) as a plain string
            result = self._pipe(
                messages,
                max_new_tokens=HINT_MAX_TOKENS,
                temperature=HINT_TEMPERATURE,
                top_p=HINT_TOP_P,
                repetition_penalty=HINT_REPETITION_PENALTY,
                do_sample=True,
                return_full_text=False,
            )
            # result is a list of dicts, one per conversation;
            # each dict has a "generated_text" key with the raw string
            if not result:
                return None, False
            # extract the generated hint that will be displayed
            # as the auto-hint near the failing check's details
            hint = str(result[0][GENERATED_TEXT_KEY]).strip()
            if not hint:
                return None, False
            # validate the hint does not suggest, for instance,
            # modifying tests, or other types of changes that
            # are not connected to achieving learning objectives;
            # still return the hint so the caller can choose how to
            # display it (e.g., dimmed with a quality warning)
            if not self._is_valid_hint(
                hint, custom_rules=self._validation_rules
            ):
                return hint, True
            return hint, False
        except Exception as exc:  # pylint: disable=broad-except
            print(
                f"   → Auto-hint error (generation): {exc}",
                file=__import__("sys").stderr,
            )
            return None, False

    def _build_messages(  # noqa: PLR0913
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
        system_prompt: str | None = None,
        details: str = "",
    ) -> list[dict[str, str]]:
        """Build a structured message list for the chat pipeline.

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
            A list of dicts suitable for the chat pipeline.

        """
        return build_hint_messages(
            description=description,
            diagnostic=diagnostic,
            command=command,
            file_content=file_content,
            system_prompt=system_prompt,
            details=details,
        )
