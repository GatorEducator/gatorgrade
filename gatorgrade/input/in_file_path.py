"""Allow customer to specify gator grader checks that do and do not correspond to a file path."""

import os
# import yaml and other necessary libraries/packages
txt = ("the_file_path", [{'description': 'Complete all TODOs', 'check': 'MatchFileFragment', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}])

shell = (None, [{'description': 'Pass HTMLHint', 'command': 'htmlhint'},{'description': 'Pass HTMLHint', 'command': 'htmlhint'}])

non_file = (None, [{'description': 'Have a total of 8 commits, 5 of which were created by you', 'check': 'CountCommitts', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}])

a_list_of_tuples = [("the_file_path", [{'description': 'Complete all TODOs', 'check': 'MatchFileFragment', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}]),
                     (None, [{'description': 'Have a total of 8 commits, 5 of which were created by you', 'check': 'CountCommitts', 'options': {'fragment': 'TODO', 'count': 0, 'exact': True}}, {'description': 'Use an if statement', 'check': 'MatchFileRegex', 'options': {'regex': 'if .*?:', 'count': 1, 'exact': False}}]),
                     (None, [{'description': 'Pass HTMLHint', 'command': 'htmlhint'},{'description': 'Pass HTMLHint', 'command': 'htmlhint'}])]
'''
print(a_list_of_tuples[0][0])
print(a_list_of_tuples[1][0])
print(a_list_of_tuples[2][0])
'''

#function for working on a list of tuples

def command_line_generator_list(a_list_of_tuples):
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


#final_gator_grader_commands, final_shell_commands = command_line_generator(shell)
#print(final_gator_grader_commands, final_shell_commands)

def command_line_generator(tuple_check):
    """Generate a list of gator grader and shell command lines using the parsed data."""
    file_path = tuple_check[0]
    list_of_dict_checks  = tuple_check[1]
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
            
    #If gator grader check is not empty, then we will return it.
    if gator_grader_checks:
        return gator_grader_checks
    #If the gator grader check is empty, then we will return the shell commands.
    else:
        return shell_checks


command_line =  command_line_generator(shell)
print(command_line)










#final_gator_grader_commands, final_shell_commands = command_line_generator(shell)
#print(final_gator_grader_commands, final_shell_commands)
