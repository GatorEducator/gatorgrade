"""Test suite for check_result.py."""

import pytest

from gatorgrade.output.check_result import CheckResult


def test_check_result_str_method_without_diagnostic() -> None:
    """Test the __str__ method for a passing CheckResult."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
    )
    result_str = str(check_result)
    assert "✓" in result_str
    assert "Test passed" in result_str


def test_check_result_str_method_with_diagnostic() -> None:
    """Test the __str__ method for a failing CheckResult with diagnostic."""
    check_result = CheckResult(
        passed=False,
        description="Test failed",
        json_info={"check": "test"},
        diagnostic="This is a diagnostic message",
    )
    result_str = check_result.__str__(show_diagnostic=True)
    assert "✕" in result_str
    assert "Test failed" in result_str
    assert "This is a diagnostic message" in result_str


def test_check_result_repr_method() -> None:
    """Test the __repr__ method for CheckResult."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
        path="test/path.py",
        diagnostic="No issues",
    )
    check_result.run_command = "echo test"
    repr_str = repr(check_result)
    assert "CheckResult(" in repr_str
    assert "passed=True" in repr_str
    assert "description='Test passed'" in repr_str
    assert "path='test/path.py'" in repr_str
    assert "run_command='echo test'" in repr_str


def test_check_result_display_result_passing() -> None:
    """Test display_result method for passing check."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
    )
    result = check_result.display_result()
    assert "✓" in result
    assert "Test passed" in result


def test_check_result_display_result_failing_with_diagnostic() -> None:
    """Test display_result method for failing check with diagnostic."""
    check_result = CheckResult(
        passed=False,
        description="Test failed",
        json_info={"check": "test"},
        diagnostic="Error occurred",
    )
    result = check_result.display_result(show_diagnostic=True)
    assert "✕" in result
    assert "Test failed" in result
    assert "Error occurred" in result


def test_check_result_display_result_failing_without_diagnostic() -> None:
    """Test display_result method for failing check without showing diagnostic."""
    check_result = CheckResult(
        passed=False,
        description="Test failed",
        json_info={"check": "test"},
        diagnostic="Error occurred",
    )
    result = check_result.display_result(show_diagnostic=False)
    assert "✕" in result
    assert "Test failed" in result
    assert "Error occurred" not in result


def test_check_result_display_result_default_hides_diagnostic() -> None:
    """Test that display_result defaults to NOT showing diagnostic when called without arguments."""
    check_result = CheckResult(
        passed=False,
        description="Test failed",
        json_info={"check": "test"},
        diagnostic="This should be hidden by default",
    )
    result = check_result.display_result()
    assert "✕" in result
    assert "Test failed" in result
    assert "This should be hidden by default" not in result
    assert "→" not in result


def test_check_result_display_result_passing_ignores_show_diagnostic() -> None:
    """Test that a passing check never shows diagnostic even with show_diagnostic=True."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
        diagnostic="This should not appear",
    )
    result = check_result.display_result(show_diagnostic=True)
    assert "✓" in result
    assert "Test passed" in result
    assert "This should not appear" not in result
    assert "→" not in result


def test_check_result_with_empty_path() -> None:
    """Test CheckResult with an empty string path."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
        path="",
    )
    assert check_result.path == ""


def test_check_result_with_explicit_empty_diagnostic() -> None:
    """Test CheckResult with an explicitly empty diagnostic string."""
    check_result = CheckResult(
        passed=False,
        description="Test failed",
        json_info={"check": "test"},
        diagnostic="",
    )
    result = check_result.display_result(show_diagnostic=True)
    assert "✕" in result
    assert "Test failed" in result


def test_check_result_with_outputlimit_default() -> None:
    """Test CheckResult with default outputlimit (None)."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
    )
    assert check_result.outputlimit is None


def test_check_result_with_explicit_outputlimit() -> None:
    """Test CheckResult with an explicit outputlimit value."""
    expected_limit = 10
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
        outputlimit=expected_limit,
    )
    assert check_result.outputlimit == expected_limit


def test_check_result_repr_includes_outputlimit() -> None:
    """Test that __repr__ includes outputlimit field."""
    check_result = CheckResult(
        passed=True,
        description="Test",
        json_info={"check": "test"},
        outputlimit=5,
    )
    repr_str = repr(check_result)
    assert "outputlimit=5" in repr_str


def test_check_result_print_does_not_crash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that the print method executes without crashing."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
    )
    check_result.print()
    out, _ = capsys.readouterr()
    assert "Test passed" in out
