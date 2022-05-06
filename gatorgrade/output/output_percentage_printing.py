"""Output of percent printing is to show the percentage of checks that the student has met requirments."""
from colorama import Fore


def print_percentage(results):
    """Print percentage of passing and failing checks to console for user understanding."""
    # iterate through results tuples
    True_list = []
    for i in results:
        for j in i:
            if isinstance(j, bool):
                if j == True:
                    True_list.append(i)
    decimal_for_percent_true = len(True_list) / len(results)
    Percent = decimal_for_percent_true * 100
    if Percent == 100.0:
        print(
            f"{Fore.GREEN}|=====================================|\n|Passing all GatorGrader Checks {Percent}%|\n|=====================================|"
        )
    else:
        print(
            f"\n{Fore.RED}Passing {len(True_list)}/{len(results)}, Grade is {Percent}%.\n"
        )
