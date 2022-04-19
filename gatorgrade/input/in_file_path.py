import yaml

#Parses a YAML file and returns its contents as a list of dictionaries
def parse_yaml_file(file_path):
    with open(file_path) as f:
        data = yaml.load_all(f, Loader=yaml.FullLoader)
        data_holder = []
        for item in data: #Transfers the data from the file's generator to a list for later access
            data_holder.append(item)
        return data_holder

text = parse_yaml_file('demo_yaml_file.yml')
print(text)