"""Direct tests for the shared support functions (build_hint_messages, is_valid_hint)."""

import pytest

from gatorgrade.hint.support import (
    HINT_DIAG_TRUNCATE,
    HINT_FILE_LINES,
    build_hint_messages,
    is_valid_hint,
)

pytestmark = pytest.mark.autohint


class TestBuildHintMessages:
    """Direct tests for build_hint_messages."""

    def test_returns_list_of_two_dicts(self) -> None:
        """Returns a list containing a system and user message."""
        msgs = build_hint_messages(description="Check file exists")
        assert isinstance(msgs, list)
        assert len(msgs) == 2  # noqa: PLR2004
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_includes_description_in_user_message(self) -> None:
        """User message contains the check description."""
        msgs = build_hint_messages(description="Check file exists")
        assert "Check file exists" in msgs[1]["content"]

    def test_includes_command_when_provided(self) -> None:
        """User message includes the command when provided."""
        msgs = build_hint_messages(description="test", command="ls hello.py")
        assert "ls hello.py" in msgs[1]["content"]

    def test_includes_diagnostic_when_provided(self) -> None:
        """User message includes the diagnostic output."""
        msgs = build_hint_messages(
            description="test", diagnostic="File not found: hello.py"
        )
        assert "File not found: hello.py" in msgs[1]["content"]

    def test_truncates_long_diagnostic(self) -> None:
        """Diagnostic longer than HINT_DIAG_TRUNCATE is truncated."""
        long_diag = "x" * (HINT_DIAG_TRUNCATE + 100)
        msgs = build_hint_messages(description="test", diagnostic=long_diag)
        total = msgs[1]["content"]
        assert len(total) < len(long_diag) + 500

    def test_truncates_file_content_to_lines(self) -> None:
        """File content is truncated to HINT_FILE_LINES lines."""
        many_lines = "\n".join([f"line_{i}" for i in range(100)])
        msgs = build_hint_messages(description="test", file_content=many_lines)
        total = msgs[1]["content"]
        assert f"line_{HINT_FILE_LINES - 1}" in total
        assert f"line_{HINT_FILE_LINES}" not in total

    def test_includes_system_rules(self) -> None:
        """System prompt contains the CRITICAL RULES guidance."""
        msgs = build_hint_messages(description="test")
        system_content = msgs[0]["content"]
        assert "CRITICAL RULES" in system_content
        assert "NEVER suggest modifying tests" in system_content
        assert "INSTEAD say:" in system_content

    def test_works_with_all_parameters(self) -> None:
        """Works correctly when all parameters are provided."""
        msgs = build_hint_messages(
            description="Check output",
            diagnostic="Error found",
            command="python script.py",
            file_content="def foo():\n    pass",
        )
        total = msgs[1]["content"]
        assert "Check output" in total
        assert "python script.py" in total
        assert "Error found" in total
        assert "def foo():" in total

    def test_includes_details_when_provided(self) -> None:
        """User message includes the details when provided."""
        msgs = build_hint_messages(
            description="test",
            details="language: Python, count: 10",
        )
        assert "language: Python, count: 10" in msgs[1]["content"]

    def test_uses_custom_system_prompt(self) -> None:
        """A custom system prompt replaces the built-in one."""
        msgs = build_hint_messages(
            description="test",
            system_prompt="You are a helpful tutor.",
        )
        assert msgs[0]["content"] == "You are a helpful tutor."


class TestIsValidHint:
    """Direct tests for is_valid_hint."""

    def test_valid_hint_accepted(self) -> None:
        """A hint describing a code fix is accepted."""
        hint = (
            "Your function returns 1 but the test expects 2; check your logic."
        )
        assert is_valid_hint(hint)

    def test_test_incorrectly_rejected(self) -> None:
        """A hint suggesting the test is incorrect is rejected."""
        hint = "The test incorrectly asserts equality."
        assert not is_valid_hint(hint)

    def test_modify_the_test_rejected(self) -> None:
        """A hint suggesting modifying the test is rejected."""
        hint = "Modify the test to handle edge cases."
        assert not is_valid_hint(hint)

    def test_change_the_assertion_rejected(self) -> None:
        """A hint suggesting changing the assertion is rejected."""
        hint = "Change the assertion to expect None instead."
        assert not is_valid_hint(hint)

    def test_change_expected_rejected(self) -> None:
        """A hint suggesting changing expected results is rejected."""
        hint = "Change the expected result from 2 to 1."
        assert not is_valid_hint(hint)

    def test_case_insensitive(self) -> None:
        """Validation is case-insensitive."""
        hint = "The TEST INCORRECTLY asserts the value."
        assert not is_valid_hint(hint)

    def test_mentioning_test_name_is_ok(self) -> None:
        """Mentioning a test name without criticizing it is accepted."""
        hint = (
            "The test test_count_punctuation expects 2 but got 1; "
            "check the counting logic in count_punctuation."
        )
        assert is_valid_hint(hint)

    def test_custom_must_contain_replaces_builtin(self) -> None:
        """Custom must_contain rules replace the empty built-in list."""
        hint = "Check your code and verify the logic."
        rules = {"must_contain": ["verify"]}
        assert is_valid_hint(hint, custom_rules=rules)

    def test_custom_must_contain_rejects_when_missing(self) -> None:
        """Custom must_contain rejects a hint missing the required phrase."""
        hint = "Check your code and fix the logic."
        rules = {"must_contain": ["verify"]}
        assert not is_valid_hint(hint, custom_rules=rules)

    def test_custom_cannot_contain_replaces_builtin(self) -> None:
        """Custom cannot_contain replaces the built-in phrases."""
        hint = "Modify the test to handle edge cases."
        # with empty custom rules, the built-in would reject this,
        # but custom rules replace built-ins entirely
        rules = {"cannot_contain": ["something else"]}
        assert is_valid_hint(hint, custom_rules=rules)

    def test_custom_rules_with_both_keys(self) -> None:
        """Custom rules with both must_contain and cannot_contain."""
        hint = (
            "Your function returns 5 but the test expects 3; check your logic."
        )
        rules = {
            "must_contain": ["your"],
            "cannot_contain": ["plagiarize"],
        }
        assert is_valid_hint(hint, custom_rules=rules)

    def test_custom_rules_cannot_contain_rejects(self) -> None:
        """Custom cannot_contain rejects a hint with the forbidden phrase."""
        hint = "Your code has a bug; plagiarize a solution."
        rules = {
            "must_contain": ["your"],
            "cannot_contain": ["plagiarize"],
        }
        assert not is_valid_hint(hint, custom_rules=rules)
