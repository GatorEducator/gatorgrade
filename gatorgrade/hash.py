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
JSON_INFO_KEY = "json_info"


def _ensure_json_safe(obj: Any) -> Any:
    """Recursively convert a Python object to a JSON-safe form.

    Real YAML data is always JSON-serialisable, but hypothesis
    property-based tests may generate dicts with non-serialisable
    keys (e.g., strategy objects). This helper converts every key
    to its string representation and every non-basic value to its
    string representation, ensuring that json.dumps never crashes.

    Args:
        obj: The object to convert.

    Returns:
        A JSON-safe value (dict, list, str, int, float, bool, or
        None).

    """
    if isinstance(obj, dict):
        return {str(k): _ensure_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_ensure_json_safe(i) for i in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


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
    every identifying field of the check. Same fields produce the
    same hash every time, across machines and across runs. This
    makes it possible to correlate checks across runs, across JSON
    reports, and across auto-hint tracking files.

    All of the following are included in the hash input so that no
    attribute of the check is left out:

    - description (from the explicit parameter)
    - file context (the file path, if any)
    - the full json_info / check_data dict from the YAML config
      (which covers check name, options, command, and any other
      custom keys present in the configuration)
    - weight
    - outputlimit
    - hint

    Because the full check_data dict is included rather than
    cherry-picked keys, two checks whose YAML entries differ in
    any way will always produce different hashes.

    Args:
        description: The human-readable description of the check.
        check_data: The raw dictionary from the YAML config file
            (i.e., the json_info of the check).
        file_context: The file path associated with the check
            (e.g., questions/question_one.py), or None for
            checks not tied to a file.
        weight: The weight of the check.
        outputlimit: The maximum number of diagnostic lines.
        hint: An optional hint message.

    Returns:
        A 64-character hexadecimal SHA-256 digest.

    """
    # build the canonical representation from every identifying field
    # of the check.  Each of the check object's own attributes is
    # included explicitly so that the hash captures the resolved/
    # effective values after defaults have been applied.
    canonical: dict[str, Any] = {
        DESCRIPTION_KEY: description,
        WEIGHT_KEY: weight,
        OUTPUTLIMIT_KEY: outputlimit,
        HINT_KEY: hint,
    }
    if COMMAND_KEY in check_data:
        canonical[COMMAND_KEY] = check_data[COMMAND_KEY]
    else:
        if CHECK_KEY in check_data:
            canonical[CHECK_KEY] = check_data[CHECK_KEY]
        if OPTIONS_KEY in check_data:
            canonical[OPTIONS_KEY] = check_data[OPTIONS_KEY]
    # include the full raw check_data as a nested value so that no
    # yAML-level attribute is excluded from the hash, even custom
    # keys that might be added in future configuration files.
    # use _ensure_json_safe-converted value so that non-serialisable
    # keys (e.g. from hypothesis property tests) don't crash.
    canonical[JSON_INFO_KEY] = _ensure_json_safe(check_data)
    # include the file path for all check types that have one
    if file_context is not None:
        canonical[FILE_KEY] = file_context
    # serialise to canonical JSON with sorted keys for determinism.
    raw = json_module.dumps(
        canonical,
        indent=INDENT_JSON,
        sort_keys=SORT_KEYS,
    )
    # compute the SHA-256 digest
    return hashlib.sha256(raw.encode(FILE_ENCODING)).hexdigest()
