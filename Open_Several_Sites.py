from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Launch browser


def Process_Giact(site_list):
    
    for url in site_list:
        # Launch a new tab in the browser
        driver = webdriver.Chrome()
        driver.execute_script("window.open('');")
        time.sleep(2)
        # Display address bar by switching to normal mode (Edge usually shows address bar by default)
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(url)
        # Take screenshot of each URL
        screenshot_filename = f"screenshot_{url.split('/')[-2]}.png"
        driver.save_screenshot(screenshot_filename)
        time.sleep(10)

    # Wait for results to load
    time.sleep(2)

    # Wait for user input before closing
    input("Press Enter to next2 the browser...")

    # Wait for user input before closing
    input("Press Enter to close the browser...")

    # Close browser
    driver.quit()

if __name__ == "__main__":
    biller_list = ['act','nap','npp','sph','mcc','mrc','pbl','pfm','cab']
    site_list = [f'https://secure3.billerweb.com/{biller}/billerconsole.html' for biller in biller_list]
    #Process_Giact(site_list)
    print(site_list)
    print("All tasks completed.")
    