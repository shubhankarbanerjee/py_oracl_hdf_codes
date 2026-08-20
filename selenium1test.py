from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Launch browser
driver = webdriver.Edge()

def Process_Giact():
    # Open Giact portal
    driver.get("https://portal.giact.com/")

    # Accept cookies if prompted
    try:
        driver.find_element(By.ID, "L2AGLb").click()
    except:
        pass

    # Wait for user input before closing
    #input("Press Enter to next1 on the browser...")
    # Search for "Ishikas Magic"
    User_box = driver.find_element(By.ID, "UserName")
    User_box.send_keys("shubhankar.banerjee@fisglobal.com")
    time.sleep(2)
    pwd_box = driver.find_element(By.ID, "Password")
    pwd_box.send_keys("RadheKrishna@108times")
    time.sleep(2)
    # Locate the checkbox (by ID, name, XPath, CSS selector, etc.)
    checkbox = driver.find_element(By.ID, "isPerson")  # Replace with actual locator
    # Click to focus, then press space
    checkbox.click()
    #checkbox.send_keys(Keys.SPACE)

    pwd_box.send_keys(Keys.RETURN)

    # Wait for results to load
    time.sleep(2)

    # Wait for user input before closing
    input("Press Enter to next2 the browser...")

    # Wait for user input before closing
    input("Press Enter to close the browser...")

    # Close browser
    driver.quit()

def PayDirectAdmin():
    # Open PayDirect Admin portal
    driver.get("https://paydirectadmin.cus.fisfedcloud.com/ActivityFileGenerator2/Account/LogOn")

    # Accept cookies if prompted
    try:
        driver.find_element(By.ID, "L2AGLb").click()
    except:
        pass

    # Wait for user input before closing
    input("Press Enter to next1 on the browser...")
 
    User_box = driver.find_element(By.ID, "UserName")
    User_box.send_keys("mjennings")
    time.sleep(2)
    pwd_box = driver.find_element(By.ID, "Password")
    pwd_box.send_keys("Password10")
    time.sleep(2)
   
    pwd_box.send_keys(Keys.RETURN)

    # Wait for results to load
    time.sleep(2)

    # Wait for user input before closing
    input("Press Enter to next2 the browser...")


    # Wait for user input before closing
    input("Press Enter to close the browser...")

    # Close browser
    driver.quit()

if __name__ == "__main__":
    #Process_Giact() # Settle code from Giact
    PayDirectAdmin() # Work in PayDirect Admin