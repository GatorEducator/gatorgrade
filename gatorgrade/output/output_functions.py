# This class is used for storing the main functions requested from the Github Issue Tracker for the output team.
# For instance, functions dealing with percentage output, description output, and colorization of text.
from colorama import init, Fore, Back, Style
init()
'''
Show an example of what the the green check mark in output would look like
Won't work until Poetry is in the project
'''
def sample_output_passing_check():
    print(Style.RESET_ALL)
    print("\n Green Check Mark: " + Fore.GREEN + "\u2714")

'''
Show an example of what the the red "X" mark in output would look like
Won't work until Poetry is in the project
'''
def sample_output_failing_check():
    print(Style.RESET_ALL)
    print("\n Red \"X\" Mark: " + Fore.RED + "\u2718")


# Print outputs
sample_output_passing_check()
sample_output_failing_check()