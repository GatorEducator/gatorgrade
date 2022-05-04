""" Tests to ensure the output_functions.py functions work properly. """

import pytest
from colorama import init, Fore
from output import output_functions

init()


@pytest.fixture()
def test_output_shows_green(capsys):
    """Test for ouput of a passed check will show green check."""
    output_functions.output_passed_checks()
    out, err = capsys.readouterr()
    expected_output = f"{Fore.GREEN}\u2714"
    actual_output = out
    assert expected_output in actual_output
    assert err == ""


def test_output_shows_red(capsys):
    """Test for output of failed check to show red color using Colorama."""
    output_functions.output_failed_checks()
    out, err = capsys.readouterr()

    expected_output = f"{Fore.RED}"
    actual_output = out
    assert expected_output in actual_output
    assert err == ""


def test_output_shows_yellow(capsys):
    """Testing the failed check will show a yellow message in output."""
    output_functions.output_failed_checks(
        failed_checks=("Implement this with an if.", False, "No if statements found")
    )
    out, err = capsys.readouterr()
    expected_output = f"{Fore.YELLOW}\u2192"
    actual_output = out
    assert expected_output in actual_output
    assert err == ""


def test_descrition_in_fail_message(capsys):
    """Testing the failed check will show diagnostic yellow message in output."""
    output_functions.output_failed_checks(
        failed_checks=("Implement this with an if.", False, "No if statements found")
    )
    out, err = capsys.readouterr()
    expected_output = "No if"
    actual_output = out
    assert expected_output in actual_output
    assert "" in err


def test_false_result_returns_x(capsys):
    """Test for the X will appear in the output for the failed check."""
    output_functions.output_failed_checks(
        failed_checks=("Implement this with an if.", False, "No if statements found")
    )
    out, err = capsys.readouterr()
    expected_output = "\u2718"
    actual_output = out

    assert expected_output in actual_output
    assert err == ""
