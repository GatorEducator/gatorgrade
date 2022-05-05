"""Generate a YAML file with default messages and specific paths."""
import os
from typing import List

def create_targeted_paths_list(key_word_list: List[str], relative_run_path: str = ".") -> List[str]:
    """Generate a list of targeted paths by walking the paths."""
    targeted_paths = []
    # Go through the root repo, the sub dictionaries and files.
    # The os.walk will only scan the paths. So the empty folders containing nothing won't be gone through
    for dirpath, _, filenames in os.walk(relative_run_path):
        print(dirpath)
        # Split path string into multiple layers of directories
        path_dir_list = dirpath.split("/")
        # Ignore folder starting with double underscore
        if any(path.startswith("__") for path in path_dir_list):
            continue
        # Ignore hidden folders and first layer. the root repo is always dot
        # Keep double dot. It represents the returning sign
        if any(path.startswith(".") and not path.startswith("..") for path in path_dir_list[1:]):
            continue
        for filename in filenames:
            # Ignore the file starting with double underscore and hidden file
            if filename.startswith("__") or filename.startswith("."):
                continue
            # Add paths when they have the key words in the second and the third directories
            # For the path with only two directories, check key words in the second directory folder name
            if len(path_dir_list) == 2:
                if path_dir_list[1] in key_word_list:
                    targeted_paths.append(os.path.join(dirpath, filename))

            # For the other paths with more than 2 directories, check key words in the second and third directories
            elif len(path_dir_list) > 2:
                if path_dir_list[1] in key_word_list or path_dir_list[2] in key_word_list:
                    targeted_paths.append(os.path.join(dirpath, filename))

            if filename in key_word_list:
                targeted_paths.append(os.path.join(dirpath, filename))               
    return targeted_paths

def write_yaml_of_paths_list(path_names):
    """Write YAML file to create gatorgrade file and set default messages."""
    # Create a new YAML file with PyYaml in the specific path.
    # write the default set up messages in YAML file.
    # List the file paths in specific format.
    pass

print(create_targeted_paths_list(["tests"],"../.."))