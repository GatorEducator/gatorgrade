"""Generates a dictionary of shell and GatorGrader command options from a list of dictionary-based checks."""

import os
from typing import List, Union

from gatorgrade.hash import compute_check_id

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
HINT_KEY = "hint"

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
        desc = check_data.check.get(DESCRIPTION_KEY, UNNAMED_CHECK)
        weight = check_data.check.get(WEIGHT_KEY, baseline_weight)
        outputlimit = check_data.check.get(OUTPUTLIMIT_KEY)
        weight_error = validate_positive_nonzero_int(weight, WEIGHT_KEY)
        if weight_error:
            errors.append(
                CONFIG_ERROR_FMT.format(desc, NEWLINE, TAB, weight_error)
            )
        if outputlimit is not None:
            ol_error = validate_positive_nonzero_int(
                outputlimit, OUTPUTLIMIT_KEY
            )
            if ol_error:
                errors.append(
                    CONFIG_ERROR_FMT.format(desc, NEWLINE, TAB, ol_error)
                )
    if errors:
        raise ValueError(NEWLINE.join(errors))
    checks: List[Union[ShellCheck, GatorGraderCheck]] = []
    for check_data in check_data_list:
        weight = check_data.check.get(WEIGHT_KEY, baseline_weight)
        outputlimit = check_data.check.get(OUTPUTLIMIT_KEY)
        # if the check has a command key, then it is a shell check
        # which means that it will be run by the computer's shell
        if COMMAND_KEY in check_data.check:
            description = check_data.check.get(DESCRIPTION_KEY)
            effective_desc = (
                description if description is not None else UNNAMED_CHECK
            )
            # compute the check identifier using a SHA256 hash,
            # this helps to uniquely identifier each of these
            # checks across runs, across JSON reports, and across
            # any of the auto-hint tracking files
            check_id = compute_check_id(
                description=effective_desc,
                check_data=check_data.check,
                file_context=check_data.file_context,
                weight=weight,
                outputlimit=outputlimit,
                hint=check_data.check.get(HINT_KEY),
            )
            checks.append(
                ShellCheck(
                    command=check_data.check.get(COMMAND_KEY),
                    description=description,
                    json_info=check_data.check,
                    weight=weight,
                    outputlimit=outputlimit,
                    hint=check_data.check.get(HINT_KEY),
                    check_id=check_id,
                )
            )
        # otherwise, it is a GatorGrader check, which means that it
        # is one of the checks that will be directly run by GatorGrader
        else:
            gg_args = []
            # add description option if in data
            description = check_data.check.get(DESCRIPTION_KEY)
            if description is not None:
                gg_args.extend([ARG_DESCRIPTION, str(description)])
            # always add name of check, which should be in data
            gg_args.append(str(check_data.check.get(CHECK_KEY)))
            # add any additional options
            options = check_data.check.get(OPTIONS_KEY)
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
                if dirname == EMPTY:
                    dirname = DEFAULT_DIRECTORY
                gg_args.extend([ARG_DIRECTORY, dirname, ARG_FILE, filename])
            description = check_data.check.get(DESCRIPTION_KEY, UNNAMED_CHECK)
            # compute the check identifier using a SHA256 hash,
            # this helps to uniquely identifier each of these
            # checks across runs, across JSON reports, and across
            # any of the auto-hint tracking files
            check_id = compute_check_id(
                description=description,
                check_data=check_data.check,
                file_context=check_data.file_context,
                weight=weight,
                outputlimit=outputlimit,
                hint=check_data.check.get(HINT_KEY),
            )
            checks.append(
                GatorGraderCheck(
                    gg_args=gg_args,
                    json_info=check_data.check,
                    weight=weight,
                    outputlimit=outputlimit,
                    hint=check_data.check.get(HINT_KEY),
                    check_id=check_id,
                )
            )
    return checks
