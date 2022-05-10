"""Generate a YAML file with default messages and specific paths."""
import os
from typing import List, Dict
import yaml

# Define colors for terminal output
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"


def input_correct(initial_path_list: List[str]) -> Dict:
    """Correct user-written paths."""
    # Recognize the paths users provide are the concise versions.
    # Unify the ending format to avoid different users' different input
    corrected_path = []
    for path in initial_path_list:
        if path.endswith("/") is False:
            path += "/"
        corrected_path.append(path)
    # Convert list to dictionary for faster iteration
    return dict.fromkeys(corrected_path, "")


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
            for target in corrected_paths:
                if target in complete_actual_path:
                    polished_paths = complete_actual_path.replace("../", "")
                    targeted_paths.append(polished_paths)

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


def write_yaml_of_paths_list(path_names):  # expected input: A path list
    """Write YAML file to create gatorgrade file and set default messages."""
    files_list = []
    # Create an empty list to store dictionaries
    for file_path in path_names:
        # Iterate through items in path_names
        file_path_fixed = file_path.replace("./", "")
        # Make file_path easier to read by removing unnecessary characters
        file_path_dict = {
            # Dictionary to store the file paths
            file_path_fixed: [
                # List which stores strings which will be in gatorgrade.yml file
                {
                    "description": "Complete all TODOs",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        }
        # Append files_list with the values stored inside file_path_dict
        files_list.append(file_path_dict)

    with open("gatorgrade.yml", "w", encoding="utf-8") as file:
        # Write a new YAML file named gatorgrade
        yaml.dump(files_list, file, sort_keys=False)
        # Dump strings stored in files_list into a new YAML file
