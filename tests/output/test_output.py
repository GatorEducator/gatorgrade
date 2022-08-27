"""Test suite for output_functions.py."""

from gatorgrade.output import output
from gatorgrade.input.checks import ShellCheck, GatorGraderCheck


def test_run_checks_gg_check_should_show_passed(capsys):
    """Test that run_checks runs a GatorGrader check and prints that the check has passed."""

    # Given a GatorGrader check that should pass
    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Check TODOs",
            "MatchFileFragment",
            "--fragment",
            "TODO",
            "--count",
            "0",
            "--exact",
            "--directory",
            "tests/test_assignment/src",
            "--file",
            "hello-world.py",
        ]
    )

    # When run_checks is called
    output.run_checks([check])

    # Then the output shows that the check has passed
    out, _ = capsys.readouterr()
    assert "  Check TODOs" in out


def test_run_checks_invalid_gg_args_prints_exception(capsys):
    """Test that run_checks prints an exception when given an invalid GatorGrader argument."""

    # Given a GatorGrader check with invalid arguments
    check = GatorGraderCheck(
        gg_args=[
            "--description",
            "Have a total of 8 commits, 5 of which were created by you",
            "CountCommitts",  # Typo
            "--fragment",
            "TODO",
            "--count",
            "0",
            "--exact",
        ]
    )

    # When run_checks is called
    output.run_checks([check])

    # Then the output contains the exception
    out, _ = capsys.readouterr()
    assert "gator.exceptions" in out


def test_run_checks_some_failed_prints_correct_summary(capsys):
    """Test that run_checks, when given some checks that should fail, prints the correct summary."""
    # Given three checks with one check that should fail
    checks = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Complete all TODOs in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "0",
                "--exact",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ]
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Add a print statement to hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "print(",
                "--count",
                "2",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ]
        ),
    ]

    # When run_checks is called
    output.run_checks(checks)

    # Then the output shows the correct fraction and percentage of passed checks
    out, _ = capsys.readouterr()
    assert "Passed 2/3 (67%) of checks" in out


def test_run_checks_all_passed_prints_correct_summary(capsys):
    """Test that run_checks, when given checks that should all pass, prints the correct summary."""
    # Given three checks that should all pass
    checks = [
        ShellCheck(description='Echo "Hello!"', command='echo "hello"'),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Complete all TODOs in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "TODO",
                "--count",
                "0",
                "--exact",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ]
        ),
        GatorGraderCheck(
            gg_args=[
                "--description",
                "Call the 'greet' function in hello-world.py",
                "MatchFileFragment",
                "--fragment",
                "greet(",
                "--count",
                "2",
                "--directory",
                "tests/test_assignment/src",
                "--file",
                "hello-world.py",
            ]
        ),
    ]

    # When run_checks is called
    output.run_checks(checks)

    # Then the output shows the correct fraction and percentage of passed checks
    out, _ = capsys.readouterr()
    assert "Passed 3/3 (100%) of checks" in out
