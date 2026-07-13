"""Auto-hint feature using local or remote LLMs for hint generation."""

from gatorgrade.hint.local_engine import (
    DEFAULT_MODEL_ID,
    ENV_CACHE_DIR,
    HINT_MAX_TOKENS,
    HINT_REPETITION_PENALTY,
    HINT_TEMPERATURE,
    HINT_TOP_P,
    AutoHintEngine,
)
from gatorgrade.hint.remote_engine import (
    REMOTE_API_KEY_DEFAULT,
    REMOTE_HINT_MAX_TOKENS,
    REMOTE_HINT_TEMPERATURE,
    REMOTE_HINT_TIMEOUT_MS,
    REMOTE_MODEL_DEFAULT,
    RemoteHintEngine,
)
from gatorgrade.hint.support import (
    HINT_DIAG_TRUNCATE,
    HINT_FILE_LINES,
)

__all__ = [
    "DEFAULT_MODEL_ID",
    "ENV_CACHE_DIR",
    "HINT_DIAG_TRUNCATE",
    "HINT_FILE_LINES",
    "HINT_MAX_TOKENS",
    "HINT_REPETITION_PENALTY",
    "HINT_TEMPERATURE",
    "HINT_TOP_P",
    "REMOTE_API_KEY_DEFAULT",
    "REMOTE_HINT_MAX_TOKENS",
    "REMOTE_HINT_TEMPERATURE",
    "REMOTE_HINT_TIMEOUT_MS",
    "REMOTE_MODEL_DEFAULT",
    "AutoHintEngine",
    "RemoteHintEngine",
]
