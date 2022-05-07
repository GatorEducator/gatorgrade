""" Tests to ensure the output_functions.py functions work properly. """

import pytest
import colorama as color
from gatorgrade.output import output_functions

color.init()


@pytest.fixture()
def test_output_shows_green(capsys):
    """Test for ouput of a passed check will show green check."""
    output_functions.output_passed_checks(passed_checks=("Remove All TODOs", True, ""))
    out, err = capsys.readouterr()
    expected_output = f"{color.Fore.GREEN}\u2714"
    actual_output = out
    assert expected_output in actual_output
    assert err == ""


def test_output_shows_red(capsys):
    """Test for output of failed check to show red color using Colorama."""
    output_functions.output_failed_checks(
        failed_checks=("Remove all TODOs", False, "3 TODOs found in example.py")
    )
    out, err = capsys.readouterr()

    expected_output = f"{color.Fore.RED}"
    actual_output = out
    assert expected_output in actual_output
    assert err == ""


def test_output_shows_yellow(capsys):
    """Testing the failed check will show a yellow message in output."""
    output_functions.output_failed_checks(
        failed_checks=("Remove all TODOs", False, "3 TODOs found in example.py")
    )
    out, err = capsys.readouterr()
    expected_output = f"{color.Fore.YELLOW}\u2192"
    actual_output = out
    assert expected_output in actual_output
    assert err == ""


def test_descrition_in_fail_message(capsys):
    """Testing the failed check will show diagnostic yellow message in output."""
    output_functions.output_failed_checks(
        failed_checks=("Implement this with an if.", False, "No if statements found")
    )
    out, err = capsys.readouterr()
    expected_output = "\x1b[31m✘  \x1b[0mI\n    \x1b[33m→  p\n"
    actual_output = out
    assert expected_output in actual_output
    assert "" in err


def test_false_result_returns_x(capsys):
    """Test will result a X mark in the output for the failed check."""
    output_functions.output_failed_checks(
        failed_checks=("Implement this with an if.", False, "No if statements found")
    )
    out, err = capsys.readouterr()
    expected_output = "\u2718"
    actual_output = out

    assert expected_output in actual_output
    assert err == ""
