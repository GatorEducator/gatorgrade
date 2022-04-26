"""Allow customer to specify gator grader checks that do and do not correspond to a file path."""

# import yaml and other necessary libraries/packages
txt = ("the_file_path", [{'description': 'Complete all TODOs', 'check': 'MatchFileFragment', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}])

def parse_config(tuple_of_file):
# iterate through the checks
    list_of_dict_checks  = tuple_of_file[1]
    file_path = tuple_of_file[0]
    # The final output for the checks
    gator_grader_checks = []

    if file_path is not None:
        for dicts in list_of_dict_checks:
            temp_gator_grader_commands = []
            for keys in dicts:
                description = dicts['description']
                options = dicts['options']
                #creating a temp list that has description, check, and options in it for every check.
                temp_gator_grader_commands = ['--description', f'{description}']
                temp_gator_grader_commands.append(dicts['check'])
                #if options exist, then add all the keys and the values inside the command list
                if options:
                    for keys in options:
                        temp_gator_grader_commands.append(f'--{keys}')
                        temp_gator_grader_commands.append(f'{options[keys]}')
        #
            gator_grader_checks.append(temp_gator_grader_commands)
    

    #returning list of lists// the final output
    return gator_grader_checks



checks = parse_config(txt)

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