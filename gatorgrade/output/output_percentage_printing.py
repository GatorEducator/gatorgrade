"""Output with the percentage of checks that the student has met requirments."""
import colorama as color


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
            color.Fore.GREEN
            + "|=====================================|\n"
            + f"|Passing all GatorGrader Checks {percent}%|\n"
            + "|=====================================|"
            + color.Style.RESET_ALL
        )

    return (
        f"\n{color.Fore.RED}Passing {len(true_list)}/{len(results)}, "
        f"Grade is {percent}%.\n{color.Style.RESET_ALL}"
    )
