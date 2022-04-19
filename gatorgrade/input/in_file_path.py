"""Allow customer to specify gator grader checks that do and do not correspond to a file path."""

# import yaml and other necessary libraries/packages


def generate_checks(tuple):
# iterate through the checks
    list_  = tuple[1]
    file_path = tuple[0]

    if tuple[0] is not None:
        for dicts in list_data:
            for keys in dicts:
                description = dicts['description']
                options = dicts['options']
                #creating a list that has description, check, and options in it.
                gator_grader_commands = ['--description', f'{description}']
                gator_grader_commands.append(data['check'])




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