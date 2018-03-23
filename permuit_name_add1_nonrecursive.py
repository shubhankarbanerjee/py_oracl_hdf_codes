# python program to print all permuitations in a name.
import os, sys, math
import datetime,time

def check_if_distinct_list(current_list):
    current_list=list(current_list)
    for i in range(len(current_list)-1):
        for j in range(i+1,len(current_list)):
            if current_list[i]==current_list[j] and i!=j :
                return False
                break;
    return True;

# program specific code:
def print_name():
    global counter
    counter=counter+1
    st=''
    for i in range(name_len):
        try:
            #print ( str(name_lst[current_list[i]]),end='')
            st=st+str(name_lst[current_list[i]])
        except:
            print ("Error "+current_list +sys.exc_info()[0])
    print (str(counter) + ".\t"+st)

def add_one(limit):
    global current_list
    for i in range(len(current_list)):
        current_list[i]=current_list[i]+1
        if current_list[i]==limit :
            current_list[i]=0
            if i==(len(current_list)-1):
                return False
        else:
            break;
    return True
    
print ("\n" *10)
name_str=input ("Please enter any value:")
print(str(datetime.datetime.now()))
t=time.time()
name_lst=list (name_str)
name_len= len (name_str)
current_list =[0]*name_len
counter=0;

num_of_permuitations =math.factorial(name_len)

print("Characters distinct ? ->" + str(check_if_distinct_list(name_str) ) )
print("Number of permuitations =" + str( num_of_permuitations ) )
print ("Permuitations of the name "+name_str+" are :-")

for i in range(name_len):
    current_list[i]=name_len - i -1
current_list[0]=name_len -2
i=0
while counter<(num_of_permuitations+1):
    i=i+1
    if(add_one(name_len)):
        #print ('-+-'+''.join(str(a) for a in current_list), end=' -')
        if check_if_distinct_list(current_list):
                print_name();
    else:
        print(str(i) + "  !", end='')
        break;
print(str(datetime.datetime.now()))
print(str(time.time()-t) + "  seconds")
