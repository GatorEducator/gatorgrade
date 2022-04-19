"""Allow customer to specify gator grader checks that do and do not correspond to a file path."""

# import yaml and other necessary libraries/packages


def generate_checks(tuple_of_file):
# iterate through the checks
    list_of_dict_checks  = tuple[1]
    file_path = tuple[0]

    if file_path is not None:
        for dicts in list_data:
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