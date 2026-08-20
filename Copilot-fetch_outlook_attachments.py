import win32com.client

def fetch_attachments_from_outlook(folder_name="Inbox"):
    # Connect to Outlook
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    # Access the specified folder
    inbox = outlook.Folders.Item(1).Folders[folder_name]
    messages = inbox.Items

    # Iterate through messages
    for message in messages:
        if message.Attachments.Count > 0:
            print(f"Email Subject: {message.Subject}")
            for attachment in message.Attachments:
                print(f"Downloading attachment: {attachment.FileName}")
                attachment.SaveAsFile(f"./{attachment.FileName}")  # Save to current directory
                print(f"Attachment saved: {attachment.FileName}")

if __name__ == "__main__":
    fetch_attachments_from_outlook()