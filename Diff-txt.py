import sys
Welcome_Message="----FIS Text file Diff tool V1----"
Author="Shubhankar Banerjee, 18-05-2018"
print ("#"*len(Welcome_Message))
print (Welcome_Message)
print ("#"*len(Welcome_Message))
try :
	with open("./DiffFile.txt","a+") as log:
		if len(sys.argv) >= 3:
			file1=sys.argv[1]
			file2=sys.argv[2]
		else :
			file1 = input("Enter the path of 1st file wrt "+sys.argv[0]+": ")
			file2 = input("Enter the path of 2nd file wrt " + sys.argv[0]+": ")
		print("Checking diff between files :" + file1 +" and " + file2)
		log.write("Checking diff between files :" + file1 +" and " + file2 +"\n\r")
		file1_txt = [line.strip() for line in open(file1, 'r')]
		file2_txt = [line.strip() for line in open(file2, 'r')]
		print("-"*20+file1+"-"*20)
		log.write("-"*20+file1+"-"*20 +"\n\r")
		for i in file1_txt:
			if i not in file2_txt:
				print(i)
				log.write(i +"\n\r")
		print("-"*20+file2+"-"*20)
		log.write("-"*20+file2+"-"*20 +"\n\r")
		for i in file2_txt:
			if i not in file1_txt:
				print(i)
				log.write(i +"\n\r")
		print("-"*20+"*Done*"+"-"*20)
		log.write("-"*20+"*Done*"+"-"*20 +"\n\r")
		
	print ("#"*len(Welcome_Message))
	print (Welcome_Message)
	print ("#"*len(Welcome_Message))
except BaseException as e:
	print(str(e))
	with open("./DiffFile.txt","a+") as log:
		log.write(str(e)+"\n\r")
finally:
	input("Ok, Thanks. Now press Enter key...")