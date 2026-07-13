"""Engine factory functions for creating auto-hint engines.

Provides factory functions that create the appropriate auto-hint
engine based on CLI arguments: either a local AutoHintEngine,
a remote one via RemoteHintEngine, or a FallbackHintEngine that
tries remote first and falls back to local.
"""

from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from gatorgrade.hint.fallback import (
    FallbackHintEngine,
    RemoteEngineAdapter,
)
from gatorgrade.hint.local_engine import (
    DEFAULT_MODEL_ID,
    AutoHintEngine,
)
from gatorgrade.hint.remote_engine import (
    REMOTE_API_KEY_DEFAULT,
    REMOTE_MODEL_DEFAULT,
    RemoteHintEngine,
)
from gatorgrade.input.parse_config import get_auto_hint_model

# sentinel value used when the user does not specify --auto-hint-model;
# the CLI code passes this sentinel and the engine builder resolves
# the actual model from the config file or engine defaults.
AUTO_HINT_MODEL_DEFAULT = "__default_model__"


def create_auto_hint_engine(  # noqa: PLR0913
    filename: Path,
    auto_hint_model: str,
    auto_hint_url: Optional[str],
    auto_hint_api_key: Optional[str],
    system_prompt: str | None = None,
    validation_rules: dict[str, list[str]] | None = None,
    auto_hint_model_default: str | None = None,
    console: Console | None = None,
) -> Any:
    """Create the appropriate auto-hint engine based on CLI arguments.

    When --auto-hint-url is provided, a RemoteHintEngine is
    attempted first. If it succeeds, it is returned. If it
    fails (e.g., the URL is unreachable or the openai library is not
    installed), a warning is printed and the engine falls back
    to a local AutoHintEngine.

    When no URL is provided, a local AutoHintEngine is created
    directly, using the default configuration for auto-hinting.

    Args:
        filename: Path to the config file (for reading
            auto_hint_model from front matter).
        auto_hint_model: Model ID from the CLI, or a sentinel
            default value.
        auto_hint_url: URL of the remote API server, or None.
        auto_hint_api_key: API key for the remote server.
        system_prompt: Optional custom system prompt.
            If provided, this replaces the built-in default.
        validation_rules: Optional dict with must_contain
            and/or cannot_contain lists of phrases to
            check, in addition to the built-in quality rules.
        auto_hint_model_default: The sentinel value that indicates
            no explicit model was specified, so a default should
            be resolved from the config file or engine defaults.
        console: A Rich Console instance for printing warnings.
            If not provided, a new Console() is created.

    Returns:
        An AutoHintEngine instance, or None if creation fails.

    """
    effective_console = console or Console()
    effective_default = auto_hint_model_default or AUTO_HINT_MODEL_DEFAULT
    # resolve the model ID from the CLI, config file, or default;
    # the remote engine has its own default model, separate from
    # the local engine default
    model_id = auto_hint_model
    remote_model_id = auto_hint_model
    if not model_id or not model_id.strip() or model_id == effective_default:
        config_model = get_auto_hint_model(filename)
        model_id = config_model or DEFAULT_MODEL_ID
        remote_model_id = config_model or REMOTE_MODEL_DEFAULT
    # build the primary and fallback local engines
    primary_local_model = DEFAULT_MODEL_ID if auto_hint_url else model_id
    fallback_local_model = DEFAULT_MODEL_ID
    try:
        primary_engine = AutoHintEngine(
            model_id=primary_local_model,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
    except Exception:
        primary_engine = None
    try:
        fallback_engine = AutoHintEngine(
            model_id=fallback_local_model,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
    except Exception:
        fallback_engine = None
    if auto_hint_url:
        # attempt to create the remote engine
        remote_engine = try_create_remote_engine(
            auto_hint_url,
            auto_hint_api_key,
            remote_model_id,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
        if remote_engine is not None and fallback_engine is not None:
            return FallbackHintEngine(
                remote_engine,
                fallback_engine,
                auto_hint_url,
                console=effective_console,
            )
        if remote_engine is not None:
            return remote_engine
        if fallback_engine is not None:
            effective_console.print()
            effective_console.print(
                "[yellow]Warning: Could not create remote hint engine for"
                f" {auto_hint_url}. Using local model."
                "[/]"
            )
            effective_console.print()
        return fallback_engine
    # no remote URL: use primary local engine, with fallback if needed
    if primary_engine is not None and fallback_engine is not None:
        return FallbackHintEngine(
            primary_engine,
            fallback_engine,
            None,
            console=effective_console,
        )
    if primary_engine is not None:
        return primary_engine
    return fallback_engine


def try_create_remote_engine(
    url: str,
    api_key: Optional[str],
    model_id: str,
    system_prompt: str | None = None,
    validation_rules: dict[str, list[str]] | None = None,
) -> Any:
    """Attempt to create and verify a RemoteHintEngine.

    Returns the engine wrapped in an adapter that unifies the
    RemoteHintEngine interface (is_loaded, ensure_loaded, model_id,
    generate_hint) with the existing AutoHintEngine interface.

    Returns None if the engine cannot be created (missing deps,
    connection error, etc.).

    """
    try:
        remote = RemoteHintEngine(
            base_url=url,
            api_key=api_key or REMOTE_API_KEY_DEFAULT,
            model_id=model_id,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
        return RemoteEngineAdapter(remote, model_id)
    except Exception:
        return None
