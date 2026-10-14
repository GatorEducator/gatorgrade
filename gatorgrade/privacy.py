"""Redact sensitive values from report data before it is persisted.

The functions in this module are a best-effort filter. They remove
values stored under names that suggest a secret and text that matches
the format of common credentials. They cannot recognize every secret,
so a sanitized report may still contain private content.
"""

import copy
import re
from typing import Any

# marker that replaces every redacted value
REDACTED_VALUE = "[redacted]"

# supported privacy modes; safe mode is reserved for public reports
# and currently applies the same redaction as the default mode
MODE_DEFAULT = "default"
MODE_SAFE = "safe"
SUPPORTED_MODES = frozenset({MODE_DEFAULT, MODE_SAFE})
# fields that may expose source code, student data, or private details
# when a report is shared publicly.
SAFE_MODE_FIELDS = frozenset(
    {
        "command",
        "options",
        "diagnostic",
        "diagnostics",
        "hint",
        "hints",
        "stdout",
        "stderr",
        "output",
        "setup_output",
        "source",
        "source_code",
        "path",
        "file_path",
        "directory",
        "cwd",
    }
)
UNSUPPORTED_MODE_ERROR = "Unsupported privacy mode: {}"

# basic string constants
EMPTY = ""

# the number of parts in a report destination path
REPORT_DESTINATION_PARTS = 3

# separators removed from a key before it is compared, which means
# that api_key, api-key, and apiKey are all treated in the same way
KEY_SEPARATOR_PATTERN = re.compile(r"[-_\s]")

# fragments that mark a key as sensitive once separators are removed
SENSITIVE_KEY_FRAGMENTS = (
    "apikey",
    "accesskey",
    "privatekey",
    "token",
    "password",
    "passwd",
    "secret",
    "credential",
    "authorization",
)

# replacement templates that keep the non-secret part of a match
KEEP_FIRST_GROUP = rf"\g<1>{REDACTED_VALUE}"
KEEP_URL_SCHEME = rf"\g<1>{REDACTED_VALUE}@"

# a private key block in the PEM format
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r".*?"
    r"(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
    re.DOTALL,
)

# a name followed by a separator, such as API_KEY= or "password": ; the
# lookbehind makes a name start at a word boundary, which keeps the
# search fast for long output that does not contain any spaces
ASSIGNMENT_NAME_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"([A-Za-z0-9_.-]+)"
    r"""["']?[ \t]*[=:][ \t]*""",
)

# the value of an assignment, which may be quoted or follow a scheme
ASSIGNMENT_VALUE_PATTERN = re.compile(
    r"(?:(?:Bearer|Basic)[ \t]+)?"
    r"""(?:"[^"\n]*"?|'[^'\n]*'?|[^\s&"',;]+)""",
    re.IGNORECASE,
)

# a bearer token that is not part of a named assignment
BEARER_TOKEN_PATTERN = re.compile(
    r"\b(Bearer\s+)[A-Za-z0-9._~+/=-]{16,}",
    re.IGNORECASE,
)

# a user name and password embedded in a URL
URL_CREDENTIAL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9+.-])"
    r"([A-Za-z][A-Za-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@",
)

# provider-specific token formats
OPENAI_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")
GITHUB_TOKEN_PATTERN = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")
GITHUB_FINE_GRAINED_PATTERN = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")
AWS_ACCESS_KEY_PATTERN = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
SLACK_TOKEN_PATTERN = re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")

# ordered pairs of a pattern and its replacement; the order matters
# because broader patterns run before the provider-specific patterns;
# named assignments are handled separately by _redact_assignments
TEXT_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (PRIVATE_KEY_PATTERN, REDACTED_VALUE),
    (BEARER_TOKEN_PATTERN, KEEP_FIRST_GROUP),
    (URL_CREDENTIAL_PATTERN, KEEP_URL_SCHEME),
    (OPENAI_KEY_PATTERN, REDACTED_VALUE),
    (GITHUB_TOKEN_PATTERN, REDACTED_VALUE),
    (GITHUB_FINE_GRAINED_PATTERN, REDACTED_VALUE),
    (AWS_ACCESS_KEY_PATTERN, REDACTED_VALUE),
    (SLACK_TOKEN_PATTERN, REDACTED_VALUE),
)


def _is_sensitive_key(key: object) -> bool:
    """Return whether a dictionary key names a value that must be hidden."""
    normalized = KEY_SEPARATOR_PATTERN.sub(EMPTY, str(key)).lower()
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def _redact_assignments(text: str) -> str:
    """Return text with the values assigned to sensitive names replaced."""
    parts: list[str] = []
    position = 0
    for name in ASSIGNMENT_NAME_PATTERN.finditer(text):
        if name.start() < position or not _is_sensitive_key(name.group(1)):
            continue
        value = ASSIGNMENT_VALUE_PATTERN.match(text, name.end())
        if value is None:
            continue
        parts.append(text[position : name.end()])
        parts.append(REDACTED_VALUE)
        position = value.end()
    parts.append(text[position:])
    return EMPTY.join(parts)


def sanitize_text(text: str) -> str:
    """Return text with recognizable credentials replaced by a marker."""
    text = _redact_assignments(text)
    for pattern, replacement in TEXT_REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def _sanitize_value(value: Any, sensitive: bool) -> Any:
    """Return a redacted copy of a value nested anywhere inside a report."""
    if isinstance(value, dict):
        return {
            key: _sanitize_value(item, sensitive or _is_sensitive_key(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_value(item, sensitive) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item, sensitive) for item in value)
    if isinstance(value, str):
        if sensitive and value:
            return REDACTED_VALUE
        return sanitize_text(value)
    return copy.deepcopy(value)


def _sanitize_safe_mode(value: Any) -> Any:
    """Hide potentially private report fields in public reports."""
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_VALUE
                if str(key).lower() in SAFE_MODE_FIELDS
                else _sanitize_safe_mode(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_safe_mode(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_safe_mode(item) for item in value)
    return value


def sanitize_report(
    report: dict[str, Any],
    mode: str = MODE_DEFAULT,
) -> dict[str, Any]:
    """Return a redacted deep copy of a report and leave the input unchanged."""
    if mode not in SUPPORTED_MODES:
        raise ValueError(UNSUPPORTED_MODE_ERROR.format(mode))
    sanitized = {
        key: _sanitize_value(item, _is_sensitive_key(key))
        for key, item in report.items()
    }

    if mode == MODE_SAFE:
        safe_report = {
            key: _sanitize_safe_mode(value) for key, value in sanitized.items()
        }
        cli_args = safe_report.get("cli_args")
        if isinstance(cli_args, dict):
            for flag in ("--config", "--config-dir"):
                if cli_args.get(flag):
                    cli_args[flag] = REDACTED_VALUE
            report_destination = cli_args.get("--report")
            if (
                isinstance(report_destination, list)
                and len(report_destination) == REPORT_DESTINATION_PARTS
                and report_destination[2]
            ):
                report_destination[2] = REDACTED_VALUE
        return safe_report
    return sanitized
