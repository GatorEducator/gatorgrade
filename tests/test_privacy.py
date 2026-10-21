"""Tests for redacting sensitive values from persisted report data."""

import copy
import time
from typing import Any

import pytest

from gatorgrade.privacy import (
    MODE_DEFAULT,
    MODE_SAFE,
    REDACTED_VALUE,
    _is_sensitive_key,
    _redact_assignments,
    _sanitize_value,
    sanitize_report,
    sanitize_text,
)

CHECK_ID = "d030b0b15498fb3809f3825525998a29e2de253abc6bd3059357e0ff49ab80d5"
OPENAI_KEY = "sk-proj-ABCDEF1234567890abcdef"
GITHUB_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
GITHUB_FINE_GRAINED = "github_pat_11ABCDEFG0abcdefghijklmnop_qrstuvwxyz"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
SLACK_TOKEN = "xoxb-123456789012-abcdefghijkl"
BEARER_TOKEN = "abcdefghijklmnopqrstuvwxyz.0123456789"
PRIVATE_KEY = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEAexamplekeymaterial\n"
    "-----END RSA PRIVATE KEY-----"
)
PLAIN_SECRET = "hunter2-plain-value"
WEIGHT = 3
EXPECTED_AMOUNT_CORRECT = 2
EXPECTED_PERCENTAGE_SCORE = 100
OUTPUT_LIMIT = 5
LONG_TEXT_REPEATS = 20000
LONG_TEXT_SECONDS = 5


def _full_report() -> dict[str, Any]:
    """Create a report with secrets in every location that is persisted."""
    return {
        "amount_correct": 0,
        "percentage_score": 0,
        "project_name": "sample-project",
        "cli_args": {
            "--config": "config/gatorgrade.yml",
            "--report": ("file", "json", "reports/report.json"),
            "--auto-hint": True,
            "--auto-hint-url": f"https://user:{PLAIN_SECRET}@example.com/v1",
            "--auto-hint-key-env": "AUTO_HINT_KEY_ENV",
            "--auto-hint-api-key": PLAIN_SECRET,
            "--output-limit": OUTPUT_LIMIT,
        },
        "checks": [
            {
                "description": "Run the program without a crash",
                "command": f"curl -H 'Authorization: Bearer {BEARER_TOKEN}' x",
                "options": {
                    "fragment": "print(",
                    "directory": "src/project",
                    "token": PLAIN_SECRET,
                    "command": f"OPENAI_API_KEY={OPENAI_KEY} python main.py",
                },
                "status": False,
                "weight": WEIGHT,
                "outputlimit": OUTPUT_LIMIT,
                "diagnostic": f"pushed with {GITHUB_TOKEN} to origin",
                "hint": f"Remove {AWS_ACCESS_KEY} from src/project/main.py",
                "check_id": CHECK_ID,
            }
        ],
    }


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "API-KEY",
        "apiKey",
        "--auto-hint-api-key",
        "access_key",
        "private key",
        "github_token",
        "PASSWORD",
        "passwd",
        "client_secret",
        "credentials",
        "Authorization",
    ],
)
def test_is_sensitive_key_accepts_secret_names(key: str) -> None:
    """Keys that name a secret are detected despite case and separators."""
    assert _is_sensitive_key(key)


@pytest.mark.parametrize(
    "key",
    [
        "--auto-hint-key-env",
        "--auto-hint-url",
        "check_id",
        "description",
        "diagnostic",
        "command",
        "weight",
        0,
    ],
)
def test_is_sensitive_key_rejects_ordinary_names(key: object) -> None:
    """Keys for ordinary report fields are not treated as secrets."""
    assert not _is_sensitive_key(key)


@pytest.mark.parametrize(
    "secret",
    [
        OPENAI_KEY,
        GITHUB_TOKEN,
        GITHUB_FINE_GRAINED,
        AWS_ACCESS_KEY,
        SLACK_TOKEN,
        PRIVATE_KEY,
    ],
)
def test_sanitize_text_redacts_token_formats(secret: str) -> None:
    """Known credential formats are removed from the surrounding text."""
    sanitized = sanitize_text(f"before {secret} after")
    assert secret not in sanitized
    assert sanitized == f"before {REDACTED_VALUE} after"


def test_sanitize_text_redacts_unterminated_private_key() -> None:
    """A private key that was cut off by truncation is still removed."""
    truncated = PRIVATE_KEY.rsplit("\n", maxsplit=1)[0]
    sanitized = sanitize_text(f"output: {truncated}")
    assert "examplekeymaterial" not in sanitized
    assert sanitized == f"output: {REDACTED_VALUE}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            f"API_KEY={PLAIN_SECRET} python main.py",
            f"API_KEY={REDACTED_VALUE} python main.py",
        ),
        (
            f"export GITHUB_TOKEN='{PLAIN_SECRET}'; make",
            f"export GITHUB_TOKEN={REDACTED_VALUE}; make",
        ),
        (
            f'{{"password": "{PLAIN_SECRET}", "user": "ada"}}',
            f'{{"password": {REDACTED_VALUE}, "user": "ada"}}',
        ),
        (
            f"tool --client-secret={PLAIN_SECRET} --verbose",
            f"tool --client-secret={REDACTED_VALUE} --verbose",
        ),
        (
            f"Authorization: Bearer {BEARER_TOKEN}",
            f"Authorization: {REDACTED_VALUE}",
        ),
        (
            f"https://example.com/v1?api_key={PLAIN_SECRET}&page=2",
            f"https://example.com/v1?api_key={REDACTED_VALUE}&page=2",
        ),
    ],
)
def test_sanitize_text_redacts_named_assignments(
    text: str, expected: str
) -> None:
    """Values assigned to a secret name are removed and the name is kept."""
    assert sanitize_text(text) == expected


def test_sanitize_text_redacts_standalone_bearer_token() -> None:
    """A bearer token without a header name is removed."""
    sanitized = sanitize_text(f"sent bearer {BEARER_TOKEN} to server")
    assert sanitized == f"sent bearer {REDACTED_VALUE} to server"


def test_sanitize_text_redacts_url_credentials() -> None:
    """A user name and password inside a URL are removed."""
    sanitized = sanitize_text(f"git clone https://ada:{PLAIN_SECRET}@host/r")
    assert sanitized == f"git clone https://{REDACTED_VALUE}@host/r"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Complete all TODOs in src/project/main.py",
        "python -m pytest tests/test_main.py --maxfail=1",
        f"check {CHECK_ID} passed",
        "https://example.com/docs/index.html?page=2",
        "Found 3 of 5 required comments in writing/reflection.md",
        "Add a basic explanation and the bearer of the result",
        "The sk-learn package and mask-rcnn model are installed",
    ],
)
def test_sanitize_text_preserves_ordinary_text(text: str) -> None:
    """Text without credentials is returned without any change."""
    assert sanitize_text(text) == text


def test_sanitize_text_is_idempotent() -> None:
    """Sanitizing text a second time does not change the result."""
    once = sanitize_text(f"API_KEY={PLAIN_SECRET} and {GITHUB_TOKEN}")
    assert sanitize_text(once) == once


def test_sanitize_value_redacts_strings_under_sensitive_flag() -> None:
    """Every non-empty string is replaced when its parent key is sensitive."""
    value = {"list": ["one", ("two", "")], "count": 1, "none": None}
    assert _sanitize_value(value, True) == {
        "list": [REDACTED_VALUE, (REDACTED_VALUE, "")],
        "count": 1,
        "none": None,
    }


def test_sanitize_value_preserves_types_without_sensitive_flag() -> None:
    """Containers and scalar values keep their types and ordinary content."""
    value = {"tuple": ("a", 1), "list": [True, None, 2.5], "text": "plain"}
    sanitized = _sanitize_value(value, False)
    assert sanitized == value
    assert isinstance(sanitized["tuple"], tuple)
    assert sanitized["list"] is not value["list"]


def test_sanitize_report_removes_every_secret() -> None:
    """No secret from any report location survives sanitization."""
    sanitized = str(sanitize_report(_full_report()))
    for secret in (
        PLAIN_SECRET,
        OPENAI_KEY,
        GITHUB_TOKEN,
        AWS_ACCESS_KEY,
        BEARER_TOKEN,
    ):
        assert secret not in sanitized


def test_sanitize_report_redacts_cli_args() -> None:
    """Sensitive arguments are hidden and ordinary arguments are kept."""
    cli_args = sanitize_report(_full_report())["cli_args"]
    assert cli_args["--auto-hint-api-key"] == REDACTED_VALUE
    assert cli_args["--auto-hint-url"] == (
        f"https://{REDACTED_VALUE}@example.com/v1"
    )
    assert cli_args["--auto-hint-key-env"] == "AUTO_HINT_KEY_ENV"
    assert cli_args["--config"] == "config/gatorgrade.yml"
    assert cli_args["--report"] == ("file", "json", "reports/report.json")
    assert cli_args["--auto-hint"] is True
    assert cli_args["--output-limit"] == OUTPUT_LIMIT


def test_sanitize_report_redacts_check_fields() -> None:
    """Commands, options, diagnostics, and hints lose only their secrets."""
    check = sanitize_report(_full_report())["checks"][0]
    assert check["command"] == (f"curl -H 'Authorization: {REDACTED_VALUE}' x")
    assert check["options"]["token"] == REDACTED_VALUE
    assert check["options"]["command"] == (
        f"OPENAI_API_KEY={REDACTED_VALUE} python main.py"
    )
    assert check["diagnostic"] == f"pushed with {REDACTED_VALUE} to origin"
    assert check["hint"] == f"Remove {REDACTED_VALUE} from src/project/main.py"


def test_sanitize_report_preserves_fields_used_by_history() -> None:
    """Identifiers, statuses, paths, and numbers are left unchanged."""
    original = _full_report()
    sanitized = sanitize_report(original)
    check = sanitized["checks"][0]
    assert check["check_id"] == CHECK_ID
    assert check["status"] is False
    assert check["weight"] == WEIGHT
    assert check["outputlimit"] == OUTPUT_LIMIT
    assert check["description"] == "Run the program without a crash"
    assert check["options"]["fragment"] == "print("
    assert check["options"]["directory"] == "src/project"
    assert sanitized["project_name"] == "sample-project"
    assert sanitized.keys() == original.keys()
    assert check.keys() == original["checks"][0].keys()


def test_sanitize_report_does_not_mutate_input() -> None:
    """The report given to the sanitizer keeps its original values."""
    original = _full_report()
    snapshot = copy.deepcopy(original)
    sanitized = sanitize_report(original)
    assert original == snapshot
    assert sanitized is not original
    assert sanitized["checks"] is not original["checks"]
    assert sanitized["checks"][0] is not original["checks"][0]
    assert sanitized["cli_args"] is not original["cli_args"]


def test_sanitize_report_handles_empty_report() -> None:
    """An empty report produces a new empty report."""
    original: dict[str, Any] = {}
    sanitized = sanitize_report(original)
    assert sanitized == {}
    assert sanitized is not original


@pytest.mark.parametrize("mode", [MODE_DEFAULT, MODE_SAFE])
def test_sanitize_report_accepts_supported_modes(mode: str) -> None:
    """Both supported modes redact a sensitive value."""
    sanitized = sanitize_report({"api_key": PLAIN_SECRET}, mode=mode)
    assert sanitized == {"api_key": REDACTED_VALUE}


def test_sanitize_report_rejects_unsupported_mode() -> None:
    """An unknown mode raises an error that names the mode."""
    with pytest.raises(ValueError, match="Unsupported privacy mode: public"):
        sanitize_report({}, mode="public")


def test_redact_assignments_keeps_names_and_ordinary_values() -> None:
    """Only the value after a sensitive name is replaced."""
    text = f"name=ada token={PLAIN_SECRET} count: 3"
    assert _redact_assignments(text) == (
        f"name=ada token={REDACTED_VALUE} count: 3"
    )


def test_redact_assignments_handles_unterminated_quote() -> None:
    """A quoted value cut off by truncation is removed up to the line end."""
    text = f'password="{PLAIN_SECRET} with spaces\nnext line'
    assert _redact_assignments(text) == (
        f"password={REDACTED_VALUE}\nnext line"
    )


def test_redact_assignments_skips_name_without_value() -> None:
    """A sensitive name with no value on its line changes nothing."""
    text = "password:\nnext line\ntoken="
    assert _redact_assignments(text) == text


def test_redact_assignments_skips_name_inside_redacted_value() -> None:
    """A name that sits inside an already redacted value is not reused."""
    text = f"Authorization: 'token={PLAIN_SECRET}' done"
    assert _redact_assignments(text) == (
        f"Authorization: {REDACTED_VALUE} done"
    )


@pytest.mark.parametrize(
    "text",
    [
        "token" * LONG_TEXT_REPEATS,
        "a:" * LONG_TEXT_REPEATS,
        "line of output 123\n" * LONG_TEXT_REPEATS,
    ],
    ids=["repeated-token", "repeated-colon", "repeated-lines"],
)
def test_sanitize_text_handles_long_output_quickly(text: str) -> None:
    """Long diagnostic output is processed without slow backtracking."""
    started = time.perf_counter()
    sanitize_text(text)
    assert time.perf_counter() - started < LONG_TEXT_SECONDS


def test_safe_mode_hides_private_report_details() -> None:
    """Safe mode hides private details but preserves check results."""
    report = {
        "checks": [
            {
                "command": "python private_script.py",
                "diagnostic": "Student submitted private content",
                "hint": "Look at line 15 of the student's code",
                "path": "/Users/student/Documents/private_assignment.py",
                "status": True,
                "weight": WEIGHT,
            }
        ]
    }

    safe_report = sanitize_report(report, mode=MODE_SAFE)

    check = safe_report["checks"][0]

    assert check["command"] == REDACTED_VALUE
    assert check["diagnostic"] == REDACTED_VALUE
    assert check["hint"] == REDACTED_VALUE
    assert check["status"] is True
    assert check["weight"] == WEIGHT
    assert check["path"] == REDACTED_VALUE

    # the original report must remain unchanged.
    assert report["checks"][0]["command"] == "python private_script.py"

    default_report = sanitize_report(report, mode=MODE_DEFAULT)

    assert default_report["checks"][0]["path"] == (
        "/Users/student/Documents/private_assignment.py"
    )


def test_safe_mode_redacts_cli_paths() -> None:
    """Safe mode hides CLI paths while preserving report metadata."""
    report: dict[str, Any] = {
        "cli_args": {
            "--config": "/Users/student/private/gatorgrade.yml",
            "--config-dir": "/Users/student/private",
            "--report": [
                "FILE",
                "JSON",
                "/Users/student/private/report.json",
            ],
        },
        "amount_correct": EXPECTED_AMOUNT_CORRECT,
        "percentage_score": EXPECTED_PERCENTAGE_SCORE,
    }
    default_report = sanitize_report(report, mode=MODE_DEFAULT)
    safe_report = sanitize_report(report, mode=MODE_SAFE)
    default_args = default_report["cli_args"]
    safe_args = safe_report["cli_args"]
    assert default_args["--config"] == report["cli_args"]["--config"]
    assert default_args["--report"][2] == report["cli_args"]["--report"][2]
    assert safe_args["--config"] == REDACTED_VALUE
    assert safe_args["--config-dir"] == REDACTED_VALUE
    assert safe_args["--report"] == [
        "FILE",
        "JSON",
        REDACTED_VALUE,
    ]
    assert safe_report["amount_correct"] == EXPECTED_AMOUNT_CORRECT
    assert safe_report["percentage_score"] == EXPECTED_PERCENTAGE_SCORE
    assert report["cli_args"]["--report"][2] == (
        "/Users/student/private/report.json"
    )
