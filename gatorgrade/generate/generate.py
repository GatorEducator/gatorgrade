"""Generate a YAML file with default messages and specific paths."""
import os
# Import the necessary libraries


def create_targeted_paths_list():
    """Generate a list of targeted paths by walking the paths."""
    targeted_paths = []
    key_word_list = ["writing", "src", "test"]
    # Go through the root repo, the sub dictionaries and files.
    for dirpath, _, filenames in os.walk("."):
        # Select only files in the dictionaries with specific names.
        for filename in filenames:
            path_list = dirpath.split("/")

            # Add paths only when they have the key words in the first and the second levels
            # The first path will always be dot, so skip it.
            if len(path_list) < 2:
                continue
            elif len(path_list) == 2:
                for key in key_word_list:
                    if key in path_list[1]:
                        targeted_paths.append(os.path.join(dirpath, filename))

            else:
                for key in key_word_list:
                    if key in path_list[1] or key in path_list[2]:
                        targeted_paths.append(os.path.join(dirpath, filename))
    return targeted_paths

def write_yaml_of_paths_list(path_names):
    """Write YAML file to create gatorgrade file and set default messages."""
    # Create a new YAML file with PyYaml in the specific path.
    # write the default set up messages in YAML file.
    # List the file paths in specific format.
    pass