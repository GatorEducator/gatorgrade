""" Tests to ensure the output_functions.py functions work properly. """

from gatorgrade.output import output_functions


def test_description_in_fail_message(capsys):
    """Testing the failed check will show diagnostic yellow message in output."""
    output_functions.output_failed_checks(
        [("Implement this with an if.", False, "No if statements found")]
    )
    out, err = capsys.readouterr()
    expected_output = f"→  No if statements found"
    actual_output = out
    assert expected_output in actual_output
    assert "" in err


def test_false_result_returns_x(capsys):
    """Test will result a X mark in the output for the failed check."""
    output_functions.output_failed_checks(
        [("Implement this with an if.", False, "No if statements found")]
    )
    out, err = capsys.readouterr()
    unicode_x = "\u2718"
    expected_output = unicode_x
    actual_output = out

    assert expected_output in actual_output
    assert err == ""
