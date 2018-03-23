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
# Here we need len * len iterations
def iterate(n):
    global current_list
    for i in range(name_len): #0 to < name_len
        current_list.append(i)
        #print(current_list)
        if n>0 :
            if check_if_distinct_list(current_list):
                iterate(n-1)
        elif n==0 :
            if check_if_distinct_list(current_list):
                print_name();
        current_list.pop()

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

print ("\n" *10)
name_str=input ("Please enter any value:")
print(str(datetime.datetime.now()))
t=time.time()
name_lst=list (name_str)
name_len= len (name_str)
current_list =[]
counter=0;
num_of_permuitations =math.factorial(name_len)

print("Characters distinct ? ->" + str(check_if_distinct_list(name_str) ) )
print (str(num_of_permuitations)+" Permuitations of the name "+name_str+" are :-")
iterate(name_len-1)
print(str(datetime.datetime.now()))
print(str(time.time()-t) + "  seconds")
