"""SHA-256 hashing for gatorgrade checks, working for both shell checks and GatorGrader checks.

Provides a deterministic check identifier based on the canonical
representation of a check's configuration fields. The same check
definition always produces the same hash, making it suitable as a
globally unique identifier across runs and across machines.
"""

import hashlib
import json as json_module
from typing import Any

# JSON serialisation constants for canonical check representation
INDENT_JSON = 4
SORT_KEYS = True
FILE_ENCODING = "utf-8"

# default values for optional check fields used when hashing
DEFAULT_WEIGHT = 1
DEFAULT_OUTPUTLIMIT = None
DEFAULT_HINT = None

# field keys used in the canonical representation
FILE_KEY = "file"
DESCRIPTION_KEY = "description"
CHECK_KEY = "check"
COMMAND_KEY = "command"
OPTIONS_KEY = "options"
WEIGHT_KEY = "weight"
OUTPUTLIMIT_KEY = "outputlimit"
HINT_KEY = "hint"


def compute_check_id(  # noqa: PLR0913
    description: str,
    check_data: dict[str, Any],
    file_context: str | None = None,
    weight: int = DEFAULT_WEIGHT,
    outputlimit: int | None = DEFAULT_OUTPUTLIMIT,
    hint: str | None = DEFAULT_HINT,
) -> str:
    """Compute a deterministic SHA-256 identifier for a check.

    The hash is computed from a canonical JSON representation of
    the check's identifying fields. Same fields → same hash,
    every time, across machines and runs. This is helpful for
    determining easily which checks pass/fail across runs or
    across machines. It is also helpful when debugging the
    auto-hinting feature so that it is easy to determine the
    specific checks for which it is generating hints.

    For shell checks (those with a command key), the canonical
    input includes description, command, weight, outputlimit, and
    hint. For GatorGrader checks, it includes description, check
    name, options, file path, weight, outputlimit, and hint.

    Args:
        description: The human-readable description of the check.
        check_data: The raw dictionary from the YAML config file.
        file_context: The file path associated with the check
            (e.g., questions/question_one.py), or None for
            checks not tied to a file.
        weight: The weight of the check.
        outputlimit: The maximum number of diagnostic lines.
        hint: An optional hint message.

    Returns:
        A 64-character hexadecimal SHA-256 digest.

    """
    canonical: dict[str, Any] = {
        DESCRIPTION_KEY: description,
        WEIGHT_KEY: weight,
        OUTPUTLIMIT_KEY: outputlimit,
        HINT_KEY: hint,
    }
    if COMMAND_KEY in check_data:
        # shell check: command is the primary identifier
        canonical[COMMAND_KEY] = check_data[COMMAND_KEY]
    else:
        # GatorGrader check: check name + options + file path
        if CHECK_KEY in check_data:
            canonical[CHECK_KEY] = check_data[CHECK_KEY]
        if OPTIONS_KEY in check_data:
            canonical[OPTIONS_KEY] = check_data[OPTIONS_KEY]
    # include the file path for all check types that have one
    if file_context is not None:
        canonical[FILE_KEY] = file_context
    # serialise to canonical JSON with sorted keys for determinism
    raw = json_module.dumps(
        canonical,
        indent=INDENT_JSON,
        sort_keys=SORT_KEYS,
        ensure_ascii=False,
    )
    # compute the SHA-256 digest
    return hashlib.sha256(raw.encode(FILE_ENCODING)).hexdigest()
