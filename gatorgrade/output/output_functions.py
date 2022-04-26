"""This module is used for storing the main functions requested from the Github Issue Tracker for the output team.
For instance, functions dealing with percentage output, description output, and colorization of text."""

import gator
import os
import output_tools

#Commands are received as list of tuples.
#Each tuple in the list is a string and list of strings <string, [strings]>
#The string is the path to the file or filename and the list is the commands for the file.
def receive_command(command_info : List[Tuple(str, List[str])]):
    """Main command function to pass commands and send results to other methods."""
    
    results = []
    #Loop through commands received, then format into string list, finally send commands to proper checking software
    for file_name, commands in command_info:
        split_commands = []
        results.append((file_name, []))

        for pre_command in commands:
            formatted_command = split_command_string(pre_command)
            
        for command in split_commands:
            #If command is formatted incorrectly in yaml files, catch the exception that would be returned and print
            try:
                result = gator.grader(command)
                results.get(file_name).append(result)
            except Exception as e:
                print("\033[91m \033[1m \033[4m An exception was detected when running the command : \033[0m \n\n \033[91m", output_tools.get_simple_command_string(command) , "\033[0m")
                print("Exception is as follows: \n ", e)
    #Send results to output methods
    #print_percentage(results)
    #print_description(results)
