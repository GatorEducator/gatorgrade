"""Auto-hint feature using Hugging Face transformers for local hint generation."""

from gatorgrade.hint.engine import (
    DEFAULT_MODEL_ID,
    ENV_CACHE_DIR,
    HINT_FILE_LINES,
    HINT_MAX_TOKENS,
    HINT_REPETITION_PENALTY,
    HINT_TEMPERATURE,
    HINT_TOP_P,
    AutoHintEngine,
)

__all__ = [
    "DEFAULT_MODEL_ID",
    "ENV_CACHE_DIR",
    "HINT_FILE_LINES",
    "HINT_MAX_TOKENS",
    "HINT_REPETITION_PENALTY",
    "HINT_TEMPERATURE",
    "HINT_TOP_P",
    "AutoHintEngine",
]
