import datetime
import time
x=0
print(str(datetime.datetime.now()))
t=time.time()
for i in range(999):
	pass
	x+=1
print(str(datetime.datetime.now()),x)
print(str(time.time()-t) + "  seconds")

print(str(datetime.datetime.now()))
t=time.time()
r=list(range(999))
for i in r:
	pass
	x-=1
print(str(datetime.datetime.now()),x)
print(str(time.time()-t) + "  seconds")
