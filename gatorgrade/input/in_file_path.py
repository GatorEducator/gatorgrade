"""Allow customer to specify gator grader checks that do and do not correspond to a file path."""

import os
# import yaml and other necessary libraries/packages
txt = ("the_file_path", [{'description': 'Complete all TODOs', 'check': 'MatchFileFragment', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}])

shell = (None, [{'description': 'Pass HTMLHint', 'command': 'htmlhint'},{'description': 'Pass HTMLHint', 'command': 'htmlhint'}])

non_file = (None, [{'description': 'Have a total of 8 commits, 5 of which were created by you', 'check': 'CountCommitts', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}])

a_list_of_tuples = [("the_file_path", [{'description': 'Complete all TODOs', 'check': 'MatchFileFragment', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}]),
                     (None, [{'description': 'Have a total of 8 commits, 5 of which were created by you', 'check': 'CountCommitts', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}]),
                     (None, [{'description': 'Pass HTMLHint', 'command': 'htmlhint'},{'description': 'Pass HTMLHint', 'command': 'htmlhint'}])]


def generate_command_lines(tuple_of_file):
# iterate through the checks
# for tuples inside the list || TODO Add a loop here to iterate over the list of tuples
    list_of_dict_checks  = tuple_of_file[1]
    file_path = tuple_of_file[0]
    # The final output for the checks
    gator_grader_checks = []
    #if file_path is not None: #check is in file context
    for parsed_data in list_of_dict_checks:
        #check the shell check here TODO
        temp_gator_grader_commands = []
        for stuff in parsed_data:
            description = parsed_data['description']
            options = parsed_data['options']
            #creating a temp list that has description, check, and options in it for every check.
            temp_gator_grader_commands = ['--description', f'{description}']
            temp_gator_grader_commands.append(parsed_data['check'])
            #if options exist, then add all the keys and the values inside the command list
            if options:
                for keys in options:
                    if type(options[keys]) == bool:
                        if options[keys] == True:
                            temp_gator_grader_commands.append(f'--{keys}')
                    else:
                        temp_gator_grader_commands.append(f'--{keys}')
                        temp_gator_grader_commands.append(f'{options[keys]}')
        gator_grader_checks.append(temp_gator_grader_commands)

    #if the file_path does not exist
'''
    elif file_path is None:
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
                    #removes the True value of exact if exact is present
                    if options['exact'] == True:
                        temp_gator_grader_commands.remove('True')
            gator_grader_checks.append(temp_gator_grader_commands)


    #returning list of lists// the final output
    return gator_grader_checks
'''


#checks = parse_config(txt)
#print(checks)



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


a_list_of_tuples = [("the_file_path", [{'description': 'Complete all TODOs', 'check': 'MatchFileFragment', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}]),
                     (None, [{'description': 'Have a total of 8 commits, 5 of which were created by you', 'check': 'CountCommitts', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}]),
                     (None, [{'description': 'Pass HTMLHint', 'command': 'htmlhint'},{'description': 'Pass HTMLHint', 'command': 'htmlhint'}])]
'''
print(a_list_of_tuples[0][0])
print(a_list_of_tuples[1][0])
print(a_list_of_tuples[2][0])
'''

#function for working on a list of tuples

def command_line_generator(a_list_of_tuples):
    """Generate a list of gator grader and shell command lines using the parsed data."""
    for tuple_check in a_list_of_tuples:
        print(tuple_check)
        list_of_dict_checks  = tuple_check[1]
        file_path = tuple_check[0]
        #Declaring final output for the checks
        gator_grader_checks = []
        shell_checks = []
        for parsed_dict_check in list_of_dict_checks:
            # Creating temporary lists for every check in the dictionary
            # We need description to be declared differently because every check has it
            description = parsed_dict_check['description']
            # If the check has a 'command', then it is a shell check
            if 'command' in parsed_dict_check:
                temp_shell_checks = []
                temp_shell_checks.append(parsed_dict_check)
                # Add the temporary shell check raw dictionary into the final shell check list
                shell_checks.append(temp_shell_checks)
            else:
                temp_gator_grader_commands = []
                options = parsed_dict_check['options']
                # Creating a temp list that has description, check, and options in it for every check.
                temp_gator_grader_commands = ['--description', f'{description}']
                temp_gator_grader_commands.append(parsed_dict_check['check'])
                # If options exist, then add all the keys and the values inside the temp command list
                if options:
                    for key in options:
                        # if the type of the value is boolean, only add the key not the boolean value
                        if type(options[key]) == bool:
                            if options[key] == True:
                                temp_gator_grader_commands.append(f'--{key}')
                        else:
                            temp_gator_grader_commands.append(f'--{key}')
                            temp_gator_grader_commands.append(f'{options[key]}')
                # If it is a gator grade check with a file, then add the directory and the file name
                if file_path is not None:
                    # Get the file directory using os
                    cwd = os.getcwd()
                    temp_gator_grader_commands.append(f'--directory')
                    temp_gator_grader_commands.append(f'{cwd}')
                    temp_gator_grader_commands.append(f'--file')
                    temp_gator_grader_commands.append(f'{file_path}')
                # Add the contents inside the temporary list into the final gator grader list.
                gator_grader_checks.append(temp_gator_grader_commands)

    return gator_grader_checks, shell_checks


final_gator_grader_commands, final_shell_commands = command_line_generator(shell)
print(final_gator_grader_commands, final_shell_commands)
