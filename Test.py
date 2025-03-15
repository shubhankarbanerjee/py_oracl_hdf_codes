print("Test")

import PyPDF2
pdfReader = PyPDF2.PdfFileReader(open('D:\\Downloads\\20180624_NDLS_MZP-2.pdf', 'rb'))
if pdfReader.isEncrypted :
    while not pdfReader.decrypt(i
nput("Please Enter a new password")):
        pass
P = pdfReader.getPage(0)
s = P.extractText()
print(s)
#pdfReader.close()

import openpyxl
wb = openpyxl.load_workbook('D:\\Downloads\\Train Route from Gurgaon.xlsx')
sheet1= wb.sheetnames[0]
