"""Generates a list of commands to be run through gatorgrader"""
import yaml


def parse_yaml_file(file_path):
    """Parses a YAML file and returns its contents as a list of dictionaries"""
    with open(file_path, encoding="utf8") as file:
        data = yaml.load_all(file, Loader=yaml.FullLoader)
        return list(data)
