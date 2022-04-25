import yaml

def parse_yaml_file(file_path):
    """Parses a YAML file and returns its contents as a list of dictionaries"""
    with open(file_path) as f:
        data = yaml.load_all(f, Loader=yaml.FullLoader)
        return list(data)
