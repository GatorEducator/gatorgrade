"""Generates a dictionary of shell and gator grader command options from a list of dict checks."""

import os
from typing import List, Union

from .checks import GatorGraderCheck, ShellCheck
from .in_file_path import CheckData


# pylint: disable=too-many-nested-blocks
def generate_checks(
    check_data_list: List[CheckData],
) -> List[Union[ShellCheck, GatorGraderCheck]]:
    """Generate a list of checks based on check data from the configuration file.

    Args:
        check_data_list: A list of CheckData that each represent a check from the
            configuration file.

    Returns:
        A list of ShellChecks and GatorGraderChecks.

    """
    checks: List[Union[ShellCheck, GatorGraderCheck]] = []
    for check_data in check_data_list:
        weight = check_data.check.get("weight", 1)
        outputlimit = check_data.check.get("outputlimit")
        try:
            # if the check has a `command` key, then it is a shell check
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
                        # if option should be a flag (i.e. its value is the `True` boolean),
                        # add only the option without a value
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
                    gg_args.extend(
                        ["--directory", dirname, "--file", filename]
                    )
                checks.append(
                    GatorGraderCheck(
                        gg_args=gg_args,
                        json_info=check_data.check,
                        weight=weight,
                        outputlimit=outputlimit,
                    )
                )
        except ValueError as validation_error:
            # when a check has an invalid weight or outputlimit,
            # create an error check that displays the diagnostic
            # instead of crashing the entire program
            check_desc = check_data.check.get("description", "unnamed check")
            error_msg = (
                f"Configuration error in check "
                f"'{check_desc}': {validation_error}"
            )
            checks.append(
                ShellCheck(
                    command="false",
                    description=error_msg,
                    json_info=check_data.check,
                    weight=1,
                )
            )
    return checks
