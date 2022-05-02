# This class is used for storing the main functions requested from the Github Issue Tracker for the output team.
# For instance, functions dealing with percentage output, description output, and colorization of text.

import gator
import os
from gatorgrade.output.output_percentage_testing import print_percetage
import output_tools

# Commands are received as list of tuples.
# Each tuple in the list is a string and list of strings <string, [strings]>
# The string is the path to the file or filename and the list is the commands for the file.
def receive_command(command_info):
    results = [('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or yayaya.py'), 
    ('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or module.py'), 
    ('Have a total of 8 commits, 5 of which were created by you', True, '')]


    for file_name, commands in command_info:
        split_commands = []
        results.append((file_name, []))

        for pre_command in commands:

            formatted_command = split_command_string(pre_command)
            
        for command in split_commands:

            try:
                result = gator.grader(command)
                results.get(file_name).append(result)
            except:
                print("\033[91m \033[1m \033[4m An exception was detected when running the command : \033[0m \n\n \033[91m", output_tools.get_simple_command_string(command) , "\033[0m")


    # Here will be the code to send results to output functions ex:)
    print_percetage(results)
    # print_description(results)
