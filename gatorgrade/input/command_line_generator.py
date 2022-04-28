"""Generates a dictionary of shell and gator grader command lines from the list of tuples."""

# import necessary libraries/packages
import os

# Function to generate command lines from a list of tuples

def command_line_generator_list(a_list_of_tuples):
    """Generate a list of gator grader and shell command lines using the parsed data."""
    gator_grader_checks = []
    shell_checks = []
    for tuple_check in a_list_of_tuples:
        file_path = tuple_check[0]
        list_of_dict_checks  = tuple_check[1]
        #Declaring final output for the checks
        for parsed_dict_check in list_of_dict_checks:
            # Creating temporary lists for every check in the dictionary
            # We need description to be declared differently because every check has it
            # If the check has a 'command', then it is a shell check
            if 'command' in parsed_dict_check:
                # Add the shell checks
                shell_checks.append(parsed_dict_check)
            else:
                temp_gator_grader_commands = []
                # Defining the description and option
                description = parsed_dict_check['description']
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
                    # Get the file and directory using os
                    dirname, filename = os.path.split(file_path)
                    temp_gator_grader_commands.append(f'--directory')
                    temp_gator_grader_commands.append(f'{dirname}')
                    temp_gator_grader_commands.append(f'--file')
                    temp_gator_grader_commands.append(f'{filename}')
                # Add the contents inside the temporary list into the final gator grader list.
                gator_grader_checks.append(temp_gator_grader_commands)

    return {"shell": shell_checks,"gatorgrader": gator_grader_checks}
