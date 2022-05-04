"""Generates a dictionary of shell and gator grader command options from a list of dict checks."""

import os

# pylint: disable=too-many-nested-blocks
def generate_checks(file_context_checks):
    """Generate a dictionary of checks based on the configuration file.

        This dictionary will have the format:
        {
            "shell": List of shell checks,
            "gatorgrader": List of GatorGrader checks
        },
    Args:
        file_context_checks: List containing dictionaries that contain file contexts
            (either a file path or None if no file context) and checks in another dictionary
            (can be either GatorGrader or shell checks).
            The input list is generated based on the configuration file.
    """
    gatorgrader_checks = []
    shell_checks = []
    for file_context_check in file_context_checks:
        # assigning the check from the dict object
        check = file_context_check["check"]
        # If the check has a 'command', then it is a shell check
        if "command" in check:
            shell_checks.append(check)
        # Else it's a GatorGrader check
        else:
            gatorgrader_command_options = []
            # Defining the description and option
            description = check.get("description")
            options = check.get("options")
            if description is not None:
                # Creating a list that has description, check, and options for the check
                gatorgrader_command_options = ["--description", f"{description}"]
            gatorgrader_command_options.append(check["check"])
            # If options exist add all the keys and the values into GatorGrader command options
            if options is not None:
                for key in options:
                    # Checking if the key is a flag
                    if isinstance(options[key], bool):
                        if options[key] is True:
                            gatorgrader_command_options.append(f"--{key}")
                    # Else if it's not a flag, then adding both key and values
                    else:
                        gatorgrader_command_options.append(f"--{key}")
                        gatorgrader_command_options.append(f"{options[key]}")
            # assigning the file context from the dict object
            file_context = file_context_check["file_context"]
            # If it is a gator grade check with a file context,
            # then add the directory and the file name into the command options
            if file_context is not None:
                # Get the file and directory using os
                dirname, filename = os.path.split(file_context)
                if dirname == "":
                    dirname = "."
                gatorgrader_command_options.append("--directory")
                gatorgrader_command_options.append(f"{dirname}")
                gatorgrader_command_options.append("--file")
                gatorgrader_command_options.append(f"{filename}")
            # Add the contents inside the temporary list into the final GatorGrader list.
            gatorgrader_checks.append(gatorgrader_command_options)

    return {"shell": shell_checks, "gatorgrader": gatorgrader_checks}
