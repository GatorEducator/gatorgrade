"""Output with the percentage of checks that the student has met requirments."""
import typer


def print_percentage(results):
    """Print percentage acts as fuction that will produce the output."""
    # iterate through results tuples
    true_list = []  # empty list for storing true results
    for result in results:
        if result[1] is True:
            true_list.append(result)
    math = len(true_list) / len(results)  # procedure of math right/total
    percent = math * 100  # get the percent to non decimal.
    result = ""
    if percent == 100.0:
        result += typer.style(
            "|=====================================|\n",
            fg=typer.colors.GREEN,
            reset=False,
        )
        result += typer.style(
            f"|Passing all GatorGrader Checks {percent}%|\n", reset=False
        )
        result += typer.style("|=====================================|")
    else:
        result += typer.style(
            f"Passing {len(true_list)}/{len(results)}, Grade is {percent}%.",
            fg=typer.colors.RED,
        )

    return result
