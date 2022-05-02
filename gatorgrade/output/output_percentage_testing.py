
from turtle import right

from sympy import total_degree
from output_functions import receive_command


results = [('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or yayaya.py'), 
    ('Complete all TODOs', True, ''), ('Use an if statement', False, 'Found 0 match(es) of the regular expression in output or module.py'), 
    ('Have a total of 8 commits, 5 of which were created by you', True, '')]

T_list = []
Total = []
for result in results:
   checks = result[1]
   for checks in checks:
        T_list.append(checks)

    
    
        if checks == True:
            Total.append(checks)
    




print(len(T_list))
print(len(Total))

'''
def find_total():
    total = 0
    for () in results:
        total = +1
    
    yield total


def find_amount_right():
    right = 0
    for i in results(i[1]) == True:
        right = +1
    yield right    
'''
'''
print(f"{find_amount_right}{find_total}")


def print_percentage():
    find_total()
    find_amount_right()


def print_all():
    print(f"\n\t\tPassing {find_amount_right(right)}/")

            

    


def percentage_from_check():
    for each command 
        look through the list of tuples 
        check bool 
        take ones that are true 
        append to list 
        take ones false append to list 
        do math of number true vs total 
        bool / total len
        def math()



total = 0
for data, value in tuple1:
      total += value     #get the total
for data,value in tuple1:
      print float(value) / total * 100

tuple1 = [('Data1', 33), ('Data2', 52), ('Data3', 85)]
total = (sum(t[1] for t in tuple1))
for a, b in tuple1:
    y = b * 100 / total
    a_percent = a, y
    print(a_percent)



list = []
take the list  
index list to take the str bool str 1,2,3 bc 0 is the file path/name
list is made up of total command tuple with desc bool diagnostic if bool = false 


'''
