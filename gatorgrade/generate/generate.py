"""Generate a YAML file with default messages and specific paths."""
from dataclasses import replace
import os
from typing import List

# Define colors for terminal output
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"

def input_correct(initial_path_list: List[str]) -> List[str]:
    """Correct user-written paths."""
    # Recognize the paths users provide are the concise versions.
    # Unify the ending format to avoid different users' different input
    corrected_path = []
    for path in initial_path_list:
        if path.endswith("/") is False:
            path += "/"
        corrected_path.append(path)
    return corrected_path



def create_targeted_paths_list(
    target_path_list: List[str], relative_run_path: str = "."
) -> List[str]:
    """Generate a list of targeted paths by walking the paths."""
    targeted_paths = []
    corrected_paths = input_correct(target_path_list)
    # Go through the root repo, the sub dictionaries and files
    # The os.walk will only scan the paths
    # So the empty folders containing nothing won't be gone through
    for dirpath, _, filenames in os.walk(relative_run_path):
        # Split path string into multiple layers of directories
        path_dir_list = dirpath.split("/")
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
            complete_actual_path = os.path.join(dirpath, filename) + "/"
            # Align the 
            for target in corrected_paths:
                if target in complete_actual_path:
                    targeted_paths.append(complete_actual_path)

    # If any of the user inputted file does not exist in any directory,
    # throw an exception indicating failure
    if not targeted_paths:
        raise FileNotFoundError(
            f"{FAIL}FAILURE: None of the user-provided file paths are"
            + " found in the provided directory and the 'gatorgrade.yml' is NOT generated"
        )

    # If some of the files are found and some are not found,
    # output a warning message saying which files were not found
    targeted_paths_string = " ".join(targeted_paths)
    for key in target_path_list:
        if key not in targeted_paths_string:
            print(
                f"{WARNING}WARNING \N{Warning Sign}: '{key}' file path is not FOUND!"
                + f"\nAll file paths except '{key}' are successfully"
                + " generated in the 'gatorgrade.yml' file"
            )
            return targeted_paths

    # If all the files exist in the root directory, print out a success message
    if targeted_paths:
        print(
            f"{OKGREEN}SUCCESS \N{Fire}: All the file paths were"
            + " successfully generated in the 'gatorgrade.yml' file!"
        )

    return targeted_paths

