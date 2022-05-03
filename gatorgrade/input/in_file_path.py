"""Generates a list of commands to be run through gatorgrader."""
import yaml


def parse_yaml_file(file_path):
    """Parse a YAML file and return its contents as a list of dictionaries."""
    with open(file_path, encoding="utf8") as file:
        data = yaml.load_all(file, Loader=yaml.FullLoader)
        return list(data)


def reformat_yaml_data(data):
    """Reformat the raw data from a YAML file into a list of tuples."""
    reformatted_data = []
    if len(data) == 2:
        data.pop(0)  # Removes the setup commands
    add_checks_to_list(None, data[0], reformatted_data)
    return reformatted_data


def add_checks_to_list(path, data_list, reformatted_data):
    """Recursively loop through the data and add any checks that are found to the reformatted list."""
    current_path = path #Saves the current path to keep track of the location
    for dict in data_list:
        for item in dict:
            if isinstance(dict[item], list): #Checks if the current dictionary has another list as its value
                if not path:
                    path = item
                else:
                    path = f"{path}/{item}"
                add_checks_to_list(path, dict[item], reformatted_data) #Runs this same function on the list inside of a dictionary
                path = current_path
            else: #Adds the current check to the reformatted data list
                reformatted_data.append({"file_context": path, "check": dict})
                break
