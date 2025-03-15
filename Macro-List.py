import sys
import os
Welcome_Message="----FIS Macro finder tool V1----"
Author="Shubhankar Banerjee, 05-02-2019"
print ("#"*len(Welcome_Message))
print (Welcome_Message)
print ("#"*len(Welcome_Message))
try :
    with open("./Macro.txt","a+") as log:
        if len(sys.argv) >= 3:
            file1=sys.argv[1]
        else :
            file1 = input("Enter the path of file or 'tla' wrt: "+sys.argv[0]+": ")
        if len(file1)==3:
            tla=file1
            lst=['D:\\ITS\\its_' + tla + '\\impl\\' + tla + '\\config\\b2c-cc\\fmtmpls\\cc-II\\application.ftl',
                 'D:\\ITS\\its_' + tla + '\\impl\\' + tla + '\\config\\b2c-cc\\fmtmpls\\common\\application.ftl',
                 'D:\\ITS\\its_' + tla + '\\impl\\' + tla + '\\config\\b2c-bc\\fmtmpls\\bc-II\\application.ftl',
                 'D:\\ITS\\its_' + tla + '\\impl\\' + tla + '\\config\\b2c-bc\\fmtmpls\\common\\application.ftl',
                 'D:\\ITS\\its_' + tla + '\\impl\\' + tla + '\\config\\b2c-qpay\\fmtmpls\\qp-II\\application.ftl',
                 'D:\\ITS\\its_' + tla + '\\impl\\' + tla + '\\config\\b2c-qpay\\fmtmpls\\common\\application.ftl'
                 ]
            for file1 in lst:
                if not os.path.exists(file1):
                    continue;
                print("\n\n Checking  file :" + file1 + " . \n")
                log.write("\n\rChecking  file :" + file1 + " . \n\r")
                file1_txt = [line.strip() for line in open(file1, 'r')]
                for i in file1_txt:
                    if "<#macro" in i:
                        print(list(i.split())[1] )
                        log.write("Macro defined in : " + i + "\n\r")
        else:
            print("Checking  file :" + file1 +" . \n")
            log.write("Checking  file :" + file1 +" . \n\r")
            file1_txt = [line.strip() for line in open(file1, 'r')]
            for i in file1_txt:
                if "<#macro" in i :
                    print(list(i.split())[1] )
                    log.write("Macro defined in : "+i +"\n\r")
except BaseException as e:
    print(str(e))
    with open("./Macro.txt","a+") as log:
        log.write(str(e)+"\n\r")
    pass
finally:
    input("Ok, Thanks. Now press Enter key...")