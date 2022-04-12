# This class is used for storing the main functions requested from the Github Issue Tracker for the output team.
# For instance, functions dealing with percentage output, description output, and colorization of text.

import gator

# Commands are received as list of tuples.
# Each tuple in the list is a string and list of strings <string, [strings]>
# The string is the path to the file or filename and the list is the commands for the file.
def receive_command(command_info):
    results = []

    for file_name, commands in command_info:
        split_commands = []
        results.append((file_name, []))

        for pre_command in commands:

            formatted_command = split_command_string(pre_command)
            # 3 types -- /blah1/blah2/blah3.py
            # /blah1/blah2 and blah3.py
            # /blah1/blah2 
            # blah3.py
            if "--file" not in formatted_command:
                formatted_command.append('--file')
                formatted_command.append(file_name)
            if "--directory" not in formated_command:
                formatted_command.append('--file')
                formatted_command.append(file_name)
            split_commands.append(fomatted_command)

        for command in split_commands:

            result = gator.grader(command)
            results.get(file_name).append(result)

    # Here will be the code to send results to output functions ex:)
    # print_percentage(results)
    # print_description(results)