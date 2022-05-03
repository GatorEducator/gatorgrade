from colorama import Fore
import output_percentage_testing

def test_given_results_returns_percent_Incorrect():
    results = [('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or yayaya.py'), 
    ('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or module.py'), 
    ('Have a total of 8 commits, 5 of which were created by you', True, '')]
    True_list = [True,True,True]
    expected_result = f"\n{Fore.RED}Passing {len(True_list)} of {len(results)}, Grade is {Percent}%\n"     
    
    actual_result = output_percentage_testing.print_percentage(results)
    assert expected_result == actual_result

def test_given_results_returns_percent_correct():
    results = [('Complete all TODOs', True, ''), ('Use an if statement', True, 'Found 0 match(es) of the regular expression in output or yayaya.py'), 
    ('Complete all TODOs', True, ''), ('Use an if statement', True, 'Found 0 match(es) of the regular expression in output or module.py'), 
    ('Have a total of 8 commits, 5 of which were created by you', True, '')]
    Percent = 100.0
    expected_result = f"\n{Fore.GREEN}Passing all GatorGrader Checks {Percent}%\n"
    actual_result = output_percentage_testing.print_percentage(results)
    assert expected_result == actual_result