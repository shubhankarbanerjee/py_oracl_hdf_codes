def factorial(a,*inp):
	x = [a]
	for i in inp:
		x.append(i)
	
	try:
		x=[int(i) for i in x]
		y=[1]*len(x)
		for i in range(len(x)):
			for j in range(1,x[i]+1):
				y[i] *=j
		return y
	except:
		return [0] *len(x)
	
	
def printlft2rt(str="Shubhankar",num=7):
	j =0
	str=''.join(['*'  if x==' ' else x for x in str ])
	while j <len(str):
		for i in range (num):
			print(str[:i+1])
			j+=1
		for i in range(num):
			print(str[:-i])
			j+=1
	for i in range(num):
		print(' '*i+str[i])
	print(str)
	for i in range(len(str)//2):
		print(' '*i+str[i]+' '*(len(str)-2*i -2) +str[-i-1]   )
	print(''.join([str[a] if a%2 else ' ' for a in range(len(str))]))
	print(''.join([str[a] if (a%2-1) else ' ' for a in range(len(str))]))
	s=len(set(list(str)) )
	print("Number of permuitations of this %s of %d chararters is %d"%(str,s,factorial(s)[0]))
	
def print_rangoli(size):
    s=size*4 - 3
    l = [chr(ord('a')+a-1) for a in range(size,0,-1)]
    for i in range(size):
        x='-'.join(l[:i]) +('-' if i else '')+ '-'.join(l[i::-1])
        print(x.center(s,'-'))
    for i in range(size-2,-1,-1):
        x='-'.join(l[:i]) +('-' if i else '')+ '-'.join(l[i::-1])
        print(x.center(s,'-'))
	    
	    
print("Factorial of 5,4,10,12 = ",factorial(5,4,10,12) )
printlft2rt()
printlft2rt("Shubhankar Banerjee")

a_list=[2,3,4]
b=a_list
c=a_list[:]
print(a_list,b,c)
a_list.append(20)
print(a_list,b,c)
a_list=35.34
print(a_list,b,c)
print_rangoli(8)