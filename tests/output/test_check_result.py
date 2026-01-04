"""Test suite for check_result.py."""

from gatorgrade.output.check_result import CheckResult


def test_check_result_str_method_without_diagnostic():
    """Test the __str__ method for a passing CheckResult."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
    )
    result_str = str(check_result)
    assert "✓" in result_str
    assert "Test passed" in result_str


def test_check_result_str_method_with_diagnostic():
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


def test_check_result_repr_method():
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


def test_check_result_display_result_passing():
    """Test display_result method for passing check."""
    check_result = CheckResult(
        passed=True,
        description="Test passed",
        json_info={"check": "test"},
    )
    result = check_result.display_result()
    assert "✓" in result
    assert "Test passed" in result


def test_check_result_display_result_failing_with_diagnostic():
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


def test_check_result_display_result_failing_without_diagnostic():
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


def test_check_result_display_result_default_hides_diagnostic():
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
