"""Test suite for check_result.py."""

import unittest
from unittest.mock import patch

# from your_module import CheckResult  # Replace 'your_module' with the actual module name where CheckResult is defined.
from gatorgrade.output.check_result import CheckResult


class TestCheckResult(unittest.TestCase):
    def test_initialization(self):
        """Test if the CheckResult object is correctly initialized."""
        check = CheckResult(
            passed=True,
            description="Check passed successfully",
            json_info={"key": "value"},
            path="test/path",
            diagnostic="All tests passed",
        )

        self.assertEqual(check.passed, True)
        self.assertEqual(check.description, "Check passed successfully")
        self.assertEqual(check.json_info, {"key": "value"})
        self.assertEqual(check.path, "test/path")
        self.assertEqual(check.diagnostic, "All tests passed")

    def test_default_diagnostic_message(self):
        """Test if default diagnostic message is used when not provided."""
        check = CheckResult(
            passed=False, description="Check failed", json_info={"key": "value"}
        )

        self.assertEqual(check.diagnostic, "No diagnostic message available")

    def test_display_result_passed(self):
        """Test the display_result method when the check has passed."""
        check = CheckResult(
            passed=True,
            description="Check passed successfully",
            json_info={"key": "value"},
        )

        expected_output = "[green]✓[/]  Check passed successfully"
        self.assertEqual(check.display_result(), expected_output)

    def test_display_result_failed_no_diagnostic(self):
        """Test the display_result method when the check has failed and no diagnostic is shown."""
        check = CheckResult(
            passed=False, description="Check failed", json_info={"key": "value"}
        )

        expected_output = "[red]✕[/]  Check failed"
        self.assertEqual(check.display_result(), expected_output)

    def test_display_result_failed_with_diagnostic(self):
        """Test the display_result method when the check has failed and diagnostic is shown."""
        check = CheckResult(
            passed=False,
            description="Check failed",
            json_info={"key": "value"},
            diagnostic="Test failed due to XYZ",
        )

        expected_output = "[red]✕[/]  Check failed\n[yellow]   → Test failed due to XYZ"
        self.assertEqual(check.display_result(show_diagnostic=True), expected_output)

    def test_repr(self):
        """Test the __repr__ method."""
        check = CheckResult(
            passed=True,
            description="Check passed successfully",
            json_info={"key": "value"},
            path="test/path",
            diagnostic="All tests passed",
        )

        expected_repr = (
            "CheckResult(passed=True, description='Check passed successfully', "
            "json_info={'key': 'value'}, path='test/path', "
            "diagnostic='All tests passed', run_command='')"
        )
        self.assertEqual(repr(check), expected_repr)

    @patch("rich.print")
    def test_print(self, mock_print):
        """Test the print method."""
        check = CheckResult(
            passed=False,
            description="Check failed",
            json_info={"key": "value"},
            diagnostic="Test failed due to XYZ",
        )

        # Call the print method, which internally calls rich.print
        check.print(show_diagnostic=True)

        # Verify if rich.print was called with the expected message
        expected_message = (
            "[red]✕[/]  Check failed\n[yellow]   → Test failed due to XYZ"
        )
        mock_print.assert_called_once_with(expected_message)


if __name__ == "__main__":
    unittest.main()
