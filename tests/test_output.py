""" Tests to ensure the output_functions.py functions work properly."""

from gatorgrade.output import output_functions


def test_passed_result_returns_check(capsys):
    """Verify that output contains a check mark for a passed check."""
    output_functions.output_passed_checks([("Remove All TODOs", True, "")])

    out, err = capsys.readouterr()
    assert "✔" in out
    assert err == ""


def test_failed_result_contains_diagnostic(capsys):
    """Verify that output contains a diagnostic for a failed check."""
    output_functions.output_failed_checks([("Remove All TODOs", False, "More TODOs")])

    out, err = capsys.readouterr()
    assert "→  More TODOs" in out
    assert err == ""


def test_failed_result_returns_cross(capsys):
    """Verify that output contains a cross mark for a failed check."""
    output_functions.output_failed_checks([("Remove All TODOs", False, "More TODOs")])

    out, err = capsys.readouterr()
    assert "✘" in out
    assert err == ""
