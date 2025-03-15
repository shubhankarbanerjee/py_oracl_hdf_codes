l=[]
#a=
#print (a)
for j in range(int(input())):
    i=input()
#    l.append(i)
#    print (j,i)
#for i in l:
    c_eng = c_num = r =0
    b = len(i)==10      #There must be exactly 10 characters in a valid UID.
    b = b and i.isalnum()     #It should only contain alphanumeric characters ( a-z , A -Z & 0 - 9).
    b = b and len(set(list(i)))==10     #No character should repeat.
    while b and (c_eng<2 or c_num<3) and r <len(i):
        if c_eng<2  and  i[r] >='A' and i[r] <= 'Z':        #It must contain at least 2 uppercase English alphabet characters.
            c_eng +=1
        elif c_num<3 and  i[r] >='0' and i[r] <= '9':       #It must contain at least 3 digits ( 0- 9).
            c_num +=1
        r +=1
    if b and not (c_eng<2 or c_num<3) :
        print ('Valid')
    else :
        print ('Invalid')
