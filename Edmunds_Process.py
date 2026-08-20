import win32com.client
from docx import Document
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader, PdfWriter
import os
import shutil
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options

def fetch_attachments_from_outlook(folder_name="Inbox"):
    # Ask user to enter the path to the .msg file
    current_path = os.getcwd()
    print(f"Current working directory: {current_path}")
    msg_file_path = input("Enter the full path to the .msg file: ").strip()
    # List all .msg files in the specified folder
    if os.path.isdir(msg_file_path):
        msg_files = [f for f in os.listdir(msg_file_path) if f.endswith('.msg')]
        if not msg_files:
            raise FileNotFoundError(f"No .msg files found in the folder {msg_file_path}.")
        
        print("Available .msg files:")
        for idx, file in enumerate(msg_files, start=1):
            print(f"{idx}: {file}")
        
        # Ask the user to select a file
        selected_idx = int(input("Enter the number corresponding to the .msg file you want to process: ").strip())
        if selected_idx < 1 or selected_idx > len(msg_files):
            raise ValueError("Invalid selection.")
        
        msg_file_path = os.path.join(msg_file_path, msg_files[selected_idx - 1])
    # Confirm the file exists
    if not os.path.exists(msg_file_path):
        raise FileNotFoundError(f"The file {msg_file_path} does not exist.")

    # Create a folder to store the extracted attachments and body
    output_folder = os.path.join(os.path.dirname(msg_file_path), "Extracted_Content")
    os.makedirs(output_folder, exist_ok=True)

    print("File selected is :", msg_file_path)
    # Open the .msg file and extract attachments and body
    outlook = win32com.client.Dispatch("Outlook.Application")
    msg = outlook.CreateItemFromTemplate(msg_file_path)

    # Save the email body
    body_file = os.path.join(output_folder, "email_body.txt")
    with open(body_file, "w", encoding="utf-8") as f:
        f.write(msg.Body)

    # Save attachments
    for attachment in msg.Attachments:
        attachment_path = os.path.join(output_folder, attachment.FileName)
        attachment.SaveAsFile(attachment_path)

    print(f"Attachments and email body have been saved to {output_folder}")
    file = output_folder
    return file

def summarize_word_documents(word_files):
    summaries = []
    for file in word_files:
        doc = Document(file)
        text = "\n".join([p.text for p in doc.paragraphs])
        summaries.append(text[:500])  # Extract the first 500 characters as a summary
    return summaries

def extract_fields_from_xml(xml_file, fields):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    extracted_data = {field: root.find(field).text for field in fields if root.find(field) is not None}
    return extracted_data

def modify_pdf(existing_pdf, output_pdf, fields):
    reader = PdfReader(existing_pdf)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Add metadata or fields (if supported by the PDF structure)
    writer.add_metadata(fields)
    with open(output_pdf, "wb") as f:
        writer.write(f)

def send_email_with_attachment(subject, body, attachment_path):
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.Subject = subject
    mail.Body = body
    mail.Attachments.Add(attachment_path)
    mail.Send()

if __name__ == "__main__":
    # Step 1: Fetch Word document attachments
    # word_files = fetch_attachments_from_outlook()

    # Step 2: Summarize Word documents

    # Step 3: Extract fields from XML
    #xml_file = "large_data.xml"  # Replace with the actual XML file path
  

    # Step 4: Modify an existing PDF
  

    # Step 5: Send an email with the modified PDF
    #subject = "Summary and Extracted Data"
    
    # Step 6: Access a website using Selenium and Microsoft Edge browser
    edge_options = Options()
    edge_options.add_argument("--start-maximized")  # Open browser in maximized mode
    service = Service("path_to_msedgedriver")  # Replace with the actual path to msedgedriver executable
    driver = webdriver.Edge(service=service, options=edge_options)

    try:
        # Navigate to the website
        website_url = "https://www.google.com"  # Replace with the desired URL
        driver.get(website_url)

        # Perform actions on the website
        print("Website title:", driver.title)

        # Example: Search for a term (if the website has a search bar)
        search_box = driver.find_element(By.NAME, "q")  # Replace "q" with the actual name of the search box element
        search_box.send_keys("Selenium WebDriver")
        search_box.send_keys(Keys.RETURN)

        # Wait for results and print the current URL
        driver.implicitly_wait(10)
        print("Current URL after search:", driver.current_url)

    finally:
        # Close the browser
        driver.quit()