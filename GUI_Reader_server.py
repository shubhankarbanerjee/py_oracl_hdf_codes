import time
from tkinter import Tk, filedialog

# Hide the root window
root = Tk()
root.withdraw()

# Ask user to select the file
File_name = filedialog.askopenfilename(title="Select the shared communication file")

if not File_name:
    print("No file selected. Exiting.")
    exit()
    
print(f"Opening the file : {File_name}")
while True:
    msg = f"{'Remote: '} [{time.strftime('%Y-%m-%d %H:%M:%S')}] \n"
    with open(File_name, "a") as f:
        f.write(msg)
    if msg.lower() == "exit":
        break
    print("Writer: Message sent. Waiting for response...")
    while True:
        with open(File_name, "r") as f:
            # ...existing code...
            lines = f.readlines()
            try:
                idx = lines.index(msg)
                response = ""
                for line in lines[idx + 1:]:
                    if line.startswith("Laptop:"):
                        response = "".join(lines[lines.index(line):]).strip()
                        break
            except ValueError:
                response = ""
        start_time = time.time()
        if response.startswith("Laptop:"):
            print("Writer: Received response:", response[6:])
            break
        if time.time() - start_time > 120:
            print("No Response")
            break
        time.sleep(1)