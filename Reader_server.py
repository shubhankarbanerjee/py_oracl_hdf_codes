import time

File_name="//tsclient/C/GIT/shared_comm.txt"
while True:
    msg = f"{'Remote: '} [{time.strftime('%Y-%m-%d %H:%M:%S')}] \n"
    with open(File_name, "a") as f:
        f.write(msg)
    if msg.lower() == "exit":
        break
    print("Writer: Message sent. Waiting for response...")
    while True:
        with open(File_name, "r") as f:
            # Ignore lines until we find the sent msg, then search for "Remote:" and display the rest of lines
            lines = f.readlines()
            try:
                idx = lines.index(msg)
                # Search for "Laptop:" after the sent msg
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
