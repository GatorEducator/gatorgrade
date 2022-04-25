"""Allow customer to specify gator grader checks that do and do not correspond to a file path."""

# import yaml and other necessary libraries/packages
txt = [{'description': 'Complete all TODOs', 'check': 'MatchFileFragment', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}]

def generate_checks(tuple_of_file):
# iterate through the checks
    list_of_dict_checks  = tuple_of_file
    #file_path = tuple_of_file[0]

    #if file_path is not None:
    for dicts in list_of_dict_checks:
        for keys in dicts:
            description = dicts['description']
            options = dicts['options']
            #creating a list that has description, check, and options in it.
            gator_grader_commands = ['--description', f'{description}']
            gator_grader_commands.append(dicts['check'])
            #if options exist, then add all the keys and the values inside the command list
            if options:
                for keys in options:
                    gator_grader_commands.append(f'--{keys}')
                    gator_grader_commands.append(f'{options[keys]}')
    return gator_grader_commands



checks = generate_checks(txt)

print(checks)



# if check corresponds to file path print the string

# description = data['description']
#       options = data['options']
#       arguments = ['--description', f'{description}']
#       arguments.append(data['check'])
#       for key, value in options.items():
#         arguments.append(f'--{key}')
#         arguments.append(f'{value}')

# else check does not correspond to file path print the string needed


# for options:arguments.append(f'--{key}')
#arguments.append(f'{dicts[key]}')