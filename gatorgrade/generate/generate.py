"""Generate a GatorGrade configuration file.

Gatorgrade file will include paths to whitelisted files
and default GatorGrader checks.
"""

# Import the necessary libraries


def create_targeted_paths_list():
    """Generate a list of targeted paths by walking the paths."""
    # Go through the root repo, the sub dictionaries and files.
    # Select only files in the dictionaries with specific names.
    # Add those targeted file paths into a list and returns it.


def write_yaml_of_paths_list(path_names):  # expected input: A path list
    """Write YAML file to create gatorgrade file and set default messages."""

    setup_dict = {
        "setup": "# add setup commands here\n",
    }
    # Write the default set up messages in YAML file.

    path_names = create_targeted_paths_list(["test"])
    # Set path_names to the create_targeted_paths_list function with the parameter "test"

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
        files_list.append(file_path_dict)
        # Append files_list with the values stored inside file_path_dict

    with open("gatorgrade.yml", "w") as file:
        # Write a new YAML file named gatorgrade
        data = yaml.dump(files_list, file, sort_keys=False)
        # Dump strings stored in files_list into a new YAML file
    pass
