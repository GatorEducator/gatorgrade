# This file is used for storing supporting functions and tools that are used by the methods in output_functions.
# The main use of this class is to de-clutter output_functions.py for better readability.
# One example of a function to be written here is the splitting of strings retrieved from the input team, at spaces, into lists.

import re
# Splits a command into individual strings to be run through gatorgrader
def split_command_string(command: str) :
    # separation is based on a space using .split

    try :
        formatted_command = remove_excess_spaces(command)
        command_lines = formatted_command.split(" ")

    except : 
        return("an error has occurred.  Please make sure your command is in the proper format")    

    return  command_lines

def remove_excess_spaces(str: str) :
    # removes excess spaces from a string

    formatted_string = re.sub(' +', ' ', str)
    formatted_string = formatted_string.strip()
    return formatted_string


def remove_empty_strings(list: list) :
    # removes empty strings from a list
    formatted_list = []

    

    return formatted_list

