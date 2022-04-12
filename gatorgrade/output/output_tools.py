# This file is used for storing supporting functions and tools that are used by the methods in output_functions.
# The main use of this class is to de-clutter output_functions.py for better readability.
# One example of a function to be written here is the splitting of strings retrieved from the input team, at spaces, into lists.

# Splits a command into individual strings to be run through gatorgrader
def split_command_string(command: str) :
    # loop through the full string and find individual parts to separate
    # separation is based on spaces with exceptions
    command_lines = command.split(" ")

    return  command_lines

command = "MatchFileFragment --fragment 'TODO' --count 0 --exact --description '[nodejs] server.js contains no TODO markers'"

split_lines = []

split_lines = split_command_string(command)

for line in split_lines :
    print(line)

