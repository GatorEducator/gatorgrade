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
    loc = "" # File location
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
    
'''
Process results and determine if the check passed or failed.

Argument `result` is: list[FILENAME, [(check_result_element1, check_result_element2),(...)]]
'''
def determine_result_by_file(result):
    file_name = result[0]
    for i in result[1]:
        output_check_result(file_name, i)

'''
Produce the output for the console for each check.

Argument: take check from determine_result_by_file()
as a tuple in the (REQUIREMENT, PASS/FAIL, RESULT-optional) format.
'''
def output_check_result(file, check):
    # Store the check elements as variables for the output statement.
    requirement = check[0]
    result = check[1]
    # Print message with green check for passing checks
    if result == True:
        # Use colorama to style "X"
        print(f"{Fore.GREEN}\u2714  {Style.RESET_ALL}{file} {requirement}")
    # Print message with X for failing checks
    elif result == False:
        # Use colorama to style "X"
        print(f"{Fore.RED}\u2718  {Style.RESET_ALL}{file} {requirement}")
        # Use output_fail_description to give a description for why it failed
        output_fail_description(check[2])

            

'''
Produce output explaining why a check failed when it failed

Arguments: desc - the string describing why a check failed
'''
def output_fail_description(desc):
    # Use colorama to print a colored fail description
    print(f"    {Fore.YELLOW}\u2192  {desc}")



# Display a sample output of how the function could display a result object from GatorGrader
sample_result = ["file.txt", [('No TODOS in text', True), ('Has an if statement', False, "No if statements found")]]
determine_result_by_file(sample_result)
