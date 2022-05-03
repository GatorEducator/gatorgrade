from colorama import Fore


results = [('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or yayaya.py'), 
    ('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or module.py'), 
    ('Have a total of 8 commits, 5 of which were created by you', True, '')]



def print_percentage(results):
#iterate through results tuples
    True_list = []
    for i in results:
        for j in i:
            if isinstance(j, bool):
                if j == True:
                    True_list.append(i)
    math = (len(True_list)/len(results))       
    Percent = math * 100
    if Percent == 100.0:
        print(f"{Fore.GREEN}|=====================================|\n|Passing all GatorGrader Checks {Percent}%|\n|=====================================|")
    else:
        print(f"\n{Fore.RED}Passing {len(True_list)}/{len(results)}, Grade is {Percent}%.\n")

print_percentage(results)


