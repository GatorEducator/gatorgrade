"""Tests for the gatorgrade.hash module."""

import json

from gatorgrade.hash import _ensure_json_safe, compute_check_id

# well-known hex string length
SHA256_HEX_LENGTH = 64

SAMPLE_INT = 42
SAMPLE_FLOAT = 3.14


def test_hash_is_64_hex_chars() -> None:
    """The hash is a 64-character hexadecimal string."""
    cid = compute_check_id(
        description="test check",
        check_data={"check": "ConfirmFileExists"},
        file_context="test.py",
    )
    assert len(cid) == SHA256_HEX_LENGTH
    assert all(c in "0123456789abcdef" for c in cid)


def test_hash_is_deterministic() -> None:
    """Same input always produces the same hash."""
    cid1 = compute_check_id(
        description="check the file",
        check_data={
            "check": "MatchFileFragment",
            "options": {"fragment": "TODO", "count": 0, "exact": True},
        },
        file_context="src/main.py",
    )
    cid2 = compute_check_id(
        description="check the file",
        check_data={
            "check": "MatchFileFragment",
            "options": {"fragment": "TODO", "count": 0, "exact": True},
        },
        file_context="src/main.py",
    )
    assert cid1 == cid2


def test_hash_changes_with_file() -> None:
    """Different file produces a different hash."""
    cid1 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        file_context="file_a.py",
    )
    cid2 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        file_context="file_b.py",
    )
    assert cid1 != cid2


def test_hash_changes_with_description() -> None:
    """Different description produces a different hash."""
    cid1 = compute_check_id(
        description="first description",
        check_data={"check": "ConfirmFileExists"},
    )
    cid2 = compute_check_id(
        description="second description",
        check_data={"check": "ConfirmFileExists"},
    )
    assert cid1 != cid2


def test_hash_changes_with_check_name() -> None:
    """Different check name produces a different hash."""
    cid1 = compute_check_id(
        description="test",
        check_data={
            "check": "MatchFileFragment",
            "options": {"fragment": "A"},
        },
        file_context="f.py",
    )
    cid2 = compute_check_id(
        description="test",
        check_data={
            "check": "CountSingleLineComments",
            "options": {"language": "Python", "count": 10},
        },
        file_context="f.py",
    )
    assert cid1 != cid2


def test_hash_changes_with_options() -> None:
    """Different options produce a different hash."""
    cid1 = compute_check_id(
        description="test",
        check_data={
            "check": "MatchFileFragment",
            "options": {"fragment": "TODO", "count": 0, "exact": True},
        },
    )
    cid2 = compute_check_id(
        description="test",
        check_data={
            "check": "MatchFileFragment",
            "options": {"fragment": "FIXME", "count": 0, "exact": True},
        },
    )
    assert cid1 != cid2


def test_hash_changes_with_weight() -> None:
    """Different weight produces a different hash."""
    cid1 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        weight=1,
    )
    cid2 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        weight=5,
    )
    assert cid1 != cid2


def test_hash_shell_check_includes_command() -> None:
    """Shell check hash includes the command field."""
    cid = compute_check_id(
        description="Run pytest for Part A",
        check_data={"command": "uv run pytest -m part_a"},
    )
    assert len(cid) == SHA256_HEX_LENGTH


def test_hash_shell_check_changes_with_command() -> None:
    """Different command produces a different hash for shell checks."""
    cid1 = compute_check_id(
        description="Run pytest",
        check_data={"command": "uv run pytest -m part_a"},
    )
    cid2 = compute_check_id(
        description="Run pytest",
        check_data={"command": "uv run pytest -m part_b"},
    )
    assert cid1 != cid2


def test_hash_shell_check_no_file_context() -> None:
    """Shell check hash works without a file context."""
    cid = compute_check_id(
        description="shell test",
        check_data={"command": "echo hello"},
        weight=2,
    )
    assert len(cid) == SHA256_HEX_LENGTH


def test_hash_with_outputlimit() -> None:
    """Hash includes outputlimit in its input."""
    cid1 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        outputlimit=10,
    )
    cid2 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        outputlimit=20,
    )
    assert cid1 != cid2


def test_hash_with_hint() -> None:
    """Hash includes hint in its input."""
    cid1 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        hint="You need to create this file.",
    )
    cid2 = compute_check_id(
        description="test",
        check_data={"check": "ConfirmFileExists"},
        hint="A different hint.",
    )
    assert cid1 != cid2


def test_hash_gg_check_without_options() -> None:
    """GatorGrader check without options still produces a hash."""
    cid = compute_check_id(
        description="simple check",
        check_data={"check": "ConfirmFileExists"},
        file_context="README.md",
    )
    assert len(cid) == SHA256_HEX_LENGTH


def test_hash_gg_check_with_complex_options() -> None:
    """GatorGrader check with many options produces a stable hash."""
    cid1 = compute_check_id(
        description="Ensure Question 3 implements iteration over language elements",
        check_data={
            "check": "MatchFileFragment",
            "options": {
                "fragment": "for ",
                "count": 15,
                "exact": False,
            },
        },
        file_context="questions/question_three.py",
        weight=1,
    )
    cid2 = compute_check_id(
        description="Ensure Question 3 implements iteration over language elements",
        check_data={
            "check": "MatchFileFragment",
            "options": {
                "fragment": "for ",
                "count": 15,
                "exact": False,
            },
        },
        file_context="questions/question_three.py",
        weight=1,
    )
    assert cid1 == cid2


def test_hash_can_be_serialised_as_string() -> None:
    """The hash is a plain string suitable for JSON serialisation."""
    cid = compute_check_id(
        description="serialisable",
        check_data={"check": "ConfirmFileExists"},
    )
    serialised = json.dumps({"id": cid})
    assert isinstance(serialised, str)
    deserialised = json.loads(serialised)
    assert deserialised["id"] == cid


def test_hash_accepts_non_ascii_characters() -> None:
    """Hash handles descriptions with Unicode characters."""
    cid = compute_check_id(
        description="Théorie de l'informatique 🐊",
        check_data={"check": "ConfirmFileExists"},
    )
    assert len(cid) == SHA256_HEX_LENGTH


def test_hash_with_no_description_provided() -> None:
    """Hash works when description is passed as a string (not from check_data)."""
    cid = compute_check_id(
        description="unnamed check",
        check_data={"command": "echo test"},
    )
    assert len(cid) == SHA256_HEX_LENGTH


def test__ensure_json_safe_preserves_primitives() -> None:
    """_ensure_json_safe returns primitives unchanged."""
    assert _ensure_json_safe("hello") == "hello"
    assert _ensure_json_safe(SAMPLE_INT) == SAMPLE_INT
    assert _ensure_json_safe(SAMPLE_FLOAT) == SAMPLE_FLOAT
    assert _ensure_json_safe(True) is True
    assert _ensure_json_safe(None) is None


def test__ensure_json_safe_converts_dict_keys_to_strings() -> None:
    """_ensure_json_safe converts non-string dict keys to strings."""
    result = _ensure_json_safe({1: "one", 2: "two"})
    assert result == {"1": "one", "2": "two"}


def test__ensure_json_safe_converts_nested_structures() -> None:
    """_ensure_json_safe recursively converts nested dicts and lists."""
    result = _ensure_json_safe({"items": [{"id": 1}, {"id": 2}]})
    assert result == {"items": [{"id": 1}, {"id": 2}]}


def test__ensure_json_safe_converts_non_serialisable_to_str() -> None:
    """_ensure_json_safe converts arbitrary objects to strings."""
    result = _ensure_json_safe({"key": object()})
    assert isinstance(result["key"], str)
