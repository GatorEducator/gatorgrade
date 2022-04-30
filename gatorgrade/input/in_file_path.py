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
    data.pop(0)  # Removes the setup commands
    loop_through_data(None, data[0], reformatted_data)
    return reformatted_data


def loop_through_data(path, data_list, reformatted_data):
    """Recursively loop through the data and add any checks that are found to the reformatted list."""
    current_path = path
    for dict in data_list:
        for item in dict:
            if str(type(dict[item])) == "<class 'list'>":
                if path == None:
                    path = item
                else:
                    path = f"{path}/{item}"
                loop_through_data(path, dict[item], reformatted_data)
                path = current_path
            else:
                reformatted_data.append({"file_context": path, "check": dict})
                break
