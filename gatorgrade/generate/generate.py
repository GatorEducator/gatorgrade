"""Generate a YAML file with default messages and specific paths."""
import os

def create_targeted_paths_list(key_word_list):
    """Generate a list of targeted paths by walking the paths."""
    # Warning: User should provide precise names of folders or files and provide correct character case as input
    # Warning: The empty folder or the folders only containing files starting with __ or . will be ignore
    # Warning: Don't name folder or file starting with dot or double underscore. They will be ignore   
    # If you input a folder name, all the sub-dirs and files will be reserved except the ones starting with . or __
    # Warning: Only folder names in root dir or the one after root will be checked. Don't put the target folders too deep
    # The file names have no above problem. You can put it in any dir.
    targeted_paths = []
    # Go through the root repo, the sub dictionaries and files.
    # The os.walk will only scan the paths. So the empty folders containing nothing won't be gone through
    for dirpath, _, filenames in os.walk("."):

        # Split path string into multiple layers of directories
        path_dir_list = dirpath.split("/")
        # Ignore folder starting with double underscore
        if any(path.startswith("__") for path in path_dir_list):
            continue
        # Ignore hidden folders, the first layer is always dot
        if any(path.startswith(".") for path in path_dir_list[1:]):
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

print(create_targeted_paths_list(["test_temp.py"]))