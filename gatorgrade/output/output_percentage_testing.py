
from turtle import right
from output_functions import receive_command

global right
results = [(2,True),(2,False),(4,True)] 
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
    

print(f"{find_amount_right}{find_total}")


def print_percentage():
    find_total()
    find_amount_right()


def print_all():
    print(f"\n\t\tPassing {find_amount_right(right)}/")

            

    

    '''
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
'''


'''
total = 0
for data, value in tuple1:
      total += value     #get the total
for data,value in tuple1:
      print float(value) / total * 100
'''
'''
tuple1 = [('Data1', 33), ('Data2', 52), ('Data3', 85)]
total = (sum(t[1] for t in tuple1))
for a, b in tuple1:
    y = b * 100 / total
    a_percent = a, y
    print(a_percent)
'''

'''
list = []
take the list  
index list to take the str bool str 1,2,3 bc 0 is the file path/name
list is made up of total command tuple with desc bool diagnostic if bool = false 
'''


def return_command_full_tuple():   
    list = []
    str1 = "no todos"
    bool = False
    str2 = "still have 3 todos"
    tuple1 = (str1,bool,str2)
    if bool == False: 
        list.append(tuple1)
        
    print(list)
return_command_full_tuple()
