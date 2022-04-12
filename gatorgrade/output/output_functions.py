# This class is used for storing the main functions requested from the Github Issue Tracker for the output team.
# For instance, functions dealing with percentage output, description output, and colorization of text.
from colorama import init, Fore, Back, Style
init()
'''
Show an example of what the the green check mark in output would look like
Won't work until Poetry is in the project
'''
def sample_output_passing_check():
    req = "REQUIREMENT" # Description of test requirement
    loc = "LOCATION" # File location
    num = "NUMBER" # Number of elements required
    print(Style.RESET_ALL)
    if len(loc) > 0:
        print(Fore.GREEN + "\u2714 " + req + " in " + loc)
    else:
        print(Fore.GREEN + "\u2714 " + req)

'''
Show an example of what the the red "X" mark in output would look like
Won't work until Poetry is in the project
'''
def sample_output_failing_check():
    req = "REQUIREMENT" # Description of test requirement
    loc = "LOCATION" # File location
    num = "NUMBER" # Number of elements required
    print(Style.RESET_ALL)
    if len(loc) > 0:
        print(Fore.RED + "\u2718 " + req + " in " + loc)
    else:
        print(Fore.RED + "\u2718 " + req)
    


# Print outputs
sample_output_passing_check()
sample_output_failing_check()