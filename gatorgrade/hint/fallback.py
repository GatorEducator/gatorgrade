"""Fallback hint engine and remote engine adapter for auto-hinting.

Provides two classes:

- FallbackHintEngine: wraps a primary and fallback engine, trying the
  primary first and falling back on failure.
- RemoteEngineAdapter: adapts the RemoteHintEngine interface to match
  the AutoHintEngine interface expected by the display code.
"""

from typing import Any, Optional

from rich.console import Console

from gatorgrade.hint.remote_engine import RemoteHintEngine

NEWLINE = "\n"

# create a default console for printing diagnostic messages; callers
# may pass their own console instance to FallbackHintEngine.
DEFAULT_CONSOLE = Console()


class FallbackHintEngine:
    """Engine that tries a primary engine first, then falls back on failure.

    Wraps two engines. On each call to generate_hint, the primary
    engine is tried first. If it fails (returns None), a one-time
    warning is printed and the fallback engine is used instead.

    The remote_url field tracks whether the primary was a remote
    server (set to a URL string) or a local model (set to None).

    """

    def __init__(
        self,
        primary_engine: Any,
        fallback_engine: Any,
        remote_url: str | None,
        console: Console | None = None,
    ) -> None:
        """Initialise the fallback engine.

        Args:
            primary_engine: The engine to try first.
            fallback_engine: The engine to fall back to.
            remote_url: The remote URL for display, or None if
                the primary is a local model.
            console: A Rich Console instance for printing warning
                messages. Defaults to a new Console() if not provided.

        """
        self._primary = primary_engine
        self._fallback_eng = fallback_engine
        self._remote_url = remote_url
        self._fallback_warned = False
        self._console = console or DEFAULT_CONSOLE
        # stores the last error when both engines fail.
        self.last_error: str | None = None

    @property
    def model_id(self) -> str:
        """Return the model identifier for the active engine."""
        if self._fallback_warned:
            fb_id: str = self._fallback_eng.model_id
            return fb_id
        pri_id: str = self._primary.model_id
        return pri_id

    @property
    def has_fallback(self) -> bool:
        """Whether a fallback to the secondary engine has occurred."""
        return self._fallback_warned

    @property
    def remote_url(self) -> str | None:
        """The remote URL that was attempted, or None for local."""
        return self._remote_url

    @property
    def primary_model_id(self) -> str:
        """The model identifier of the primary engine (before any fallback)."""
        pri_id: str = self._primary.model_id
        return pri_id

    @property
    def is_loaded(self) -> bool:
        """Return whether the primary engine is loaded."""
        result: bool = self._primary.is_loaded
        return result

    def ensure_loaded(self) -> None:
        """Ensure the primary engine is loaded."""
        try:
            self._primary.ensure_loaded()
        except Exception:  # pylint: disable=broad-except
            pass

    def generate_hint(  # noqa: PLR0913
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
        system_prompt: str | None = None,
        details: str = "",
    ) -> tuple[Optional[str], bool]:
        """Generate a hint, falling back to the secondary engine on error.

        Args:
            description: Check description.
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
        hint: str | None
        is_low: bool
        hint, is_low = self._primary.generate_hint(
            description=description,
            diagnostic=diagnostic,
            command=command,
            file_content=file_content,
            system_prompt=system_prompt,
            details=details,
        )
        if hint is not None:
            return hint, is_low
        # primary failed; warn once and fall back
        if not self._fallback_warned:
            self._console.print()
            if self._remote_url:
                remote_error = getattr(self._primary, "last_error", None)
                if remote_error:
                    self._console.print(
                        "[yellow]Warning: Remote hint server at"
                        f" {self._remote_url} failed:"
                        f" {remote_error}[/]"
                    )
                else:
                    self._console.print(
                        "[yellow]Warning: Remote hint server at"
                        f" {self._remote_url} failed."
                        "[/]"
                    )
            else:
                self._console.print(
                    "[yellow]Warning: The specified local model"
                    f" ({self._primary.model_id}) was not"
                    f" available. Using the default model."
                    "[/]"
                )
            self._fallback_warned = True
        hint2: str | None
        is_low2: bool
        hint2, is_low2 = self._fallback_eng.generate_hint(
            description=description,
            diagnostic=diagnostic,
            command=command,
            file_content=file_content,
            system_prompt=system_prompt,
            details=details,
        )
        if hint2 is None:
            pri_err = getattr(self._primary, "last_error", None)
            fb_err = getattr(self._fallback_eng, "last_error", None)
            parts: list[str] = []
            if pri_err:
                parts.append(f"Primary: {pri_err}")
            if fb_err:
                parts.append(f"{NEWLINE}Fallback: {fb_err}")
            if parts:
                self.last_error = "; ".join(parts)
            else:
                self.last_error = "All hint engines failed."
        return hint2, is_low2


class RemoteEngineAdapter:
    """Adapter for wrapping RemoteHintEngine with the AutoHintEngine interface.

    The display logic in output.py calls:
    - engine.is_loaded
    - engine.ensure_loaded()
    - engine.model_id
    - engine.generate_hint(...)

    All of these are forwarded to the wrapped remote engine.

    """

    def __init__(self, remote_engine: RemoteHintEngine, model_id: str):
        """Initialise the adapter.

        Args:
            remote_engine: The RemoteHintEngine instance to wrap.
            model_id: The model identifier string for display.

        """
        self._remote = remote_engine
        self._model_id = model_id

    @property
    def is_loaded(self) -> bool:
        """The remote engine is always considered loaded."""
        return True

    def ensure_loaded(self) -> None:
        """No-op for the remote engine."""

    @property
    def model_id(self) -> str:
        """Return the model identifier for display."""
        return f"{self._model_id}"

    def generate_hint(  # noqa: PLR0913
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
        system_prompt: str | None = None,
        details: str = "",
    ) -> tuple[Optional[str], bool]:
        """Delegate hint generation to the remote engine.

        Args:
            description: Check description.
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
        return self._remote.generate_hint(
            description=description,
            diagnostic=diagnostic,
            command=command,
            file_content=file_content,
            system_prompt=system_prompt,
            details=details,
        )
