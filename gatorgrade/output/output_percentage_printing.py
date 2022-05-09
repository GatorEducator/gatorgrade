"""Output with the percentage of checks that the student has met requirments."""
from colorama import Fore


def print_percentage(results):
    """Print percentage acts as fuction that will produce the output."""
    # iterate through results tuples
    true_list = []  # empty list for storing true results
    for result in results:
        if result[1] is True:
            true_list.append(result)
    math = len(true_list) / len(results)  # procedure of math right/total
    percent = math * 100  # get the percent to non decimal.
    if percent == 100.0:
        return (
            f"{Fore.GREEN}|=====================================|\n"
            + f"|Passing all GatorGrader Checks {percent}%|\n"
            + "|=====================================|"
        )

    return (
        f"\n{Fore.RED}Passing {len(true_list)}/{len(results)}, Grade is {percent}%.\n"
    )
