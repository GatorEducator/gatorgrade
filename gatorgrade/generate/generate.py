"""Generate a YAML file with default messages and specific paths."""
import os

def create_targeted_paths_list():
    """Generate a list of targeted paths by walking the paths."""
    targeted_paths = []
    key_word_list = ["writing", "src", "test", "deliverables"]
    # Go through the root repo, the sub dictionaries and files.
    # The os.walk will only scan the paths. So the empty folders containing nothing won't be gone through
    for dirpath, _, filenames in os.walk("."):

        # Split path string into multiple layers of directories
        path_dir_list = dirpath.split("/")
        # Ignore folder starting with __
        for path in path_dir_list:
            if path.startswith("__"):
                continue

        for filename in filenames:
            # The first directory is always dot. Skip it
            if len(path_dir_list) == 1:
                continue
            # Ignore the file starting with __
            if filename.startswith("__"):
                continue
            # Ignore hidden folders
            if path_dir_list[1].startswith("."):
                continue
            # Add paths only when they have the key words in the second and the third directories
            elif len(path_dir_list) == 2:
                for key in key_word_list:
                    # For the path with only two directories, check key words in the second directory folder name
                    if key in path_dir_list[1]:
                        targeted_paths.append(os.path.join(dirpath, filename))

            # For the other paths with more than 2 directories, check key words in the second and third directories
            else:
                for key in key_word_list:
                    if key in path_dir_list[1] or key in path_dir_list[2]:
                        targeted_paths.append(os.path.join(dirpath, filename))
    return targeted_paths

def write_yaml_of_paths_list(path_names):
    """Write YAML file to create gatorgrade file and set default messages."""
    # Create a new YAML file with PyYaml in the specific path.
    # write the default set up messages in YAML file.
    # List the file paths in specific format.
    pass

print(create_targeted_paths_list())