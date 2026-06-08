"""Generates a dictionary of shell and GatorGrader command options from a list of dictionary-based checks."""

import os
from typing import List, Union

from .checks import GatorGraderCheck, ShellCheck, validate_positive_nonzero_int
from .in_file_path import CheckData

EMPTY = ""
NEWLINE = "\n"
TAB = "  "

DEFAULT_DIRECTORY = "."

ARG_DESCRIPTION = "--description"
ARG_DIRECTORY = "--directory"
ARG_FILE = "--file"

DESCRIPTION_KEY = "description"
UNNAMED_CHECK = "unnamed check"
WEIGHT_KEY = "weight"
OUTPUTLIMIT_KEY = "outputlimit"
COMMAND_KEY = "command"
CHECK_KEY = "check"
OPTIONS_KEY = "options"

CONFIG_ERROR_FMT = "- Configuration error in check '{}': {}{}{}"


def generate_checks(  # noqa: PLR0912
    check_data_list: List[CheckData],
    baseline_weight: int = 1,
) -> List[Union[ShellCheck, GatorGraderCheck]]:
    """Generate a list of checks based on check data from the configuration file.

    Args:
        check_data_list: A list of CheckData that each represent a check from the
            configuration file.
        baseline_weight: Default weight applied to checks that do not specify
            an explicit weight.

    Returns:
        A list of ShellChecks and GatorGraderChecks.

    Raises:
        ValueError: If any check has an invalid weight or outputlimit.

    """
    errors: List[str] = []
    for check_data in check_data_list:
        desc = check_data.check.get("description", "unnamed check")
        weight = check_data.check.get("weight", baseline_weight)
        outputlimit = check_data.check.get("outputlimit")
        weight_error = validate_positive_nonzero_int(weight, "weight")
        if weight_error:
            errors.append(
                f"- Configuration error in check '{desc}': {NEWLINE}{TAB}{weight_error}"
            )
        if outputlimit is not None:
            ol_error = validate_positive_nonzero_int(
                outputlimit, "outputlimit"
            )
            if ol_error:
                errors.append(
                    f"- Configuration error in check '{desc}': {NEWLINE}{TAB}{ol_error}"
                )
    if errors:
        raise ValueError("\n".join(errors))
    checks: List[Union[ShellCheck, GatorGraderCheck]] = []
    for check_data in check_data_list:
        weight = check_data.check.get("weight", baseline_weight)
        outputlimit = check_data.check.get("outputlimit")
        # if the check has a command key, then it is a shell check
        # which means that it will be run by the computer's shell
        if "command" in check_data.check:
            checks.append(
                ShellCheck(
                    command=check_data.check.get("command"),
                    description=check_data.check.get("description"),
                    json_info=check_data.check,
                    weight=weight,
                    outputlimit=outputlimit,
                )
            )
        # otherwise, it is a GatorGrader check, which means that it
        # is one of the checks that will be directly run by GatorGrader
        else:
            gg_args = []
            # add description option if in data
            description = check_data.check.get("description")
            if description is not None:
                gg_args.extend(["--description", str(description)])
            # always add name of check, which should be in data
            gg_args.append(str(check_data.check.get("check")))
            # add any additional options
            options = check_data.check.get("options")
            if options is not None:
                for option in options:
                    # if option should be a flag (i.e., its value is the True boolean),
                    # then add only the option without a value
                    option_value = options[option]
                    if isinstance(option_value, bool):
                        if option_value:
                            gg_args.append(f"--{option}")
                    # otherwise, add both the option and its value
                    else:
                        gg_args.extend([f"--{option}", str(option_value)])
            # add directory and file if file context in data
            if check_data.file_context is not None:
                # get the file and directory using os
                dirname, filename = os.path.split(check_data.file_context)
                if dirname == "":
                    dirname = "."
                gg_args.extend(["--directory", dirname, "--file", filename])
            checks.append(
                GatorGraderCheck(
                    gg_args=gg_args,
                    json_info=check_data.check,
                    weight=weight,
                    outputlimit=outputlimit,
                )
            )
    return checks
