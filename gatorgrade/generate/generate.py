"""Generate a YAML file with default messages and specific paths."""
import os
# Import the necessary libraries

def create_targeted_paths_list():
    """Generate a list of targeted paths by walking the paths."""
    targeted_paths = []
    # Go through the root repo, the sub dictionaries and files.
    for dirpath, _, filenames in os.walk("."):

        # Select only files in the dictionaries with specific names.
        for filename in filenames:
            path_list = dirpath.split("/")
            # Check the key words only in the first and the second levels of paths
            if "writing" or "src" or "test" in path_list[1] or path_list[2]:

            # Add those qualified file paths into a list and returns it.
                targeted_paths.append(os.path.join(dirpath, filename))
    return targeted_paths



def write_yaml_of_paths_list(path_names):
    """Write YAML file to create gatorgrade file and set default messages."""
    # Create a new YAML file with PyYaml in the specific path.
    # write the default set up messages in YAML file.
    # List the file paths in specific format.
    pass