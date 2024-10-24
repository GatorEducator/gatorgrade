"""Generate a YAML file with default messages and specific paths."""

import os
from typing import Dict
from typing import List

import typer
import yaml


def input_correct(initial_path_list: List[str], run_path: str) -> Dict:
    """Correct user-written paths."""
    # Recognize the paths users provide are the concise versions.
    # Unify the ending format to avoid different users' different input
    corrected_path = []
    # Run_path unify
    if run_path.endswith(os.path.sep) is False:
        run_path += os.path.sep
    for path in initial_path_list:
        # Combine the running path with the target path
        # To make sure the target path starts from the running directory
        path = run_path + path
        # Treat the last unit of the path as a concise name unit
        if path.endswith(os.path.sep) is False:
            path += os.path.sep
        corrected_path.append(path)
    # Convert list to dictionary for faster iteration
    return dict.fromkeys(corrected_path, "")


def create_targeted_paths_list(
    target_path_list: List[str], relative_run_path: str = "."
) -> List[str]:
    """Generate a list of targeted paths by walking the paths."""
    targeted_paths = []
    corrected_paths = input_correct(target_path_list, relative_run_path)
    # Go through the root repo, the sub dictionaries and files
    # The os.walk will only scan the paths
    # So the empty folders containing nothing won't be gone through
    for dirpath, _, filenames in os.walk(relative_run_path):
        # Split path string into multiple layers of directories
        path_dir_list = dirpath.split(os.path.sep)
        # Ignore folder starting with double underscore
        if any(path.startswith("__") for path in path_dir_list):
            continue
        # Ignore hidden folders and first layer. the root repo is always dot
        # Keep double dot. It means going back to the parent folder
        if any(
            path.startswith(".") and not path.startswith("..")
            for path in path_dir_list[1:]
        ):
            continue
        for filename in filenames:
            # Ignore special files
            if filename.startswith("__") or filename.startswith("."):
                continue
            # Combine the path with file name to get a complete path
            complete_actual_path = os.path.join(dirpath, filename) + os.path.sep
            for target in corrected_paths:
                if target in complete_actual_path:
                    polished_paths = complete_actual_path.replace(
                        f"{relative_run_path}{os.path.sep}", ""
                    )
                    targeted_paths.append(polished_paths)

    # If any of the user inputted file does not exist in any directory,
    # throw an exception indicating failure
    if not targeted_paths:
        typer.secho(
            "FAILURE: None of the user-provided file paths are"
            " found in the provided directory and the 'gatorgrade.yml' is NOT generated",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    # If some of the files are found and some are not found,
    # output a warning message saying which files were not found
    targeted_paths_string = " ".join(targeted_paths)
    for key in target_path_list:
        if key not in targeted_paths_string:
            typer.secho(
                f"WARNING \u26a0: '{key}' file path is not FOUND!"
                f"\nAll file paths except '{key}' are successfully"
                " generated in the 'gatorgrade.yml' file",
                fg=typer.colors.YELLOW,
            )
            return targeted_paths

    # If all the files exist in the root directory, print out a success message
    if targeted_paths:
        typer.secho(
            "SUCCESS \U0001f525: All the file paths were"
            " successfully generated in the 'gatorgrade.yml' file!",
            fg=typer.colors.GREEN,
        )

    return targeted_paths


def write_yaml_of_paths_list(
    path_names: List[str], search_root: str
):  # expected input: A path list
    """Write YAML file to create gatorgrade file and set default messages."""
    files_list = []
    # Create an empty list to store dictionaries
    for file_path in path_names:
        # Iterate through items in path_names
        if file_path.endswith(os.path.sep):
            file_path = file_path[0:-1]
        # Convert file separators to '/'
        file_path_fixed = file_path.replace(os.path.sep, "/")
        # Make file_path easier to read by removing unnecessary characters
        file_path_dict = {
            # Dictionary to store the file paths
            file_path_fixed: [
                # List which stores strings which will be in gatorgrade.yml file
                {
                    "description": f"Complete all TODOs in {file_path_fixed}",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        }
        # Append files_list with the values stored inside file_path_dict
        files_list.append(file_path_dict)

    with open(
        f"{search_root}{os.path.sep}gatorgrade.yml", "w", encoding="utf-8"
    ) as file:
        # Write a new YAML file named gatorgrade
        yaml.dump(files_list, file, sort_keys=False)
        # Dump strings stored in files_list into a new YAML file


def generate_config(target_path_list: List[str], search_root: str = "."):
    """Generate config by creating targeted paths in a list of strings, then create a YAML file."""
    targeted_paths = create_targeted_paths_list(target_path_list, search_root)
    write_yaml_of_paths_list(targeted_paths, search_root)
