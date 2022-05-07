"""Output of percent printing is to show the percentage
of checks that the student has met requirments.
"""
from colorama import Fore


def print_percentage(results):
    """Print percentage of passing and failing
    checks to console for user understanding.
    """
    # iterate through results tuples
    true_list = []
    for i in results:
        for j in i:
            if isinstance(j, bool):
                if j is True:
                    true_list.append(i)
    decimal_for_percent_true = len(true_list) / len(results)
    percent = decimal_for_percent_true * 100
    if percent == 100.0:
        print(
            f"{Fore.GREEN}|=====================================|\n|",
            "Passing all GatorGrader Checks {Percent}%|\n|",
            "=====================================|",
        )
    else:
        print(
            f"\n{Fore.RED}Passing {len(true_list)}/{len(results)}, Grade is {percent}%.\n"
        )
