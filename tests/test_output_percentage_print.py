from colorama import Fore, Style
from gatorgrade.output import output_percentage_printing


def test_given_results_returns_percent_Incorrect():
    results = [
        ("Complete all TODOs", True, ""),
        (
            "Use an if statement",
            False,
            "Found 0 match(es) of the regular expression in output or yayaya.py",
        ),
        ("Complete all TODOs", True, ""),
        (
            "Use an if statement",
            False,
            "Found 0 match(es) of the regular expression in output or module.py",
        ),
        ("Have a total of 8 commits, 5 of which were created by you", True, ""),
    ]
   
    expected_result = (
        f"\n\x1b[31mPassing 3/5, Grade is 60.0%.\n"
    )

    actual_result = output_percentage_printing.print_percentage(results)
    assert expected_result in actual_result


def test_given_results_returns_percent_correct():
    results = [
        ("Complete all TODOs", True, ""),
        (
            "Use an if statement",
            True,
            "Found 0 match(es) of the regular expression in output or yayaya.py",
        ),
        ("Complete all TODOs", True, ""),
        (
            "Use an if statement",
            True,
            "Found 0 match(es) of the regular expression in output or module.py",
        ),
        ("Have a total of 8 commits, 5 of which were created by you", True, ""),
    ]
    expected_result = f"\x1b[32m|=====================================|\n|Passing all GatorGrader Checks 100.0%|\n|=====================================|"
    actual_result = output_percentage_printing.print_percentage(results)
    assert expected_result in actual_result
