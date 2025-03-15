import webbrowser
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# Open a webpage
webbrowser.open('http://www.google.com')

# Wait for the browser to open
time.sleep(5)

# Automate form submission using Selenium
driver = webdriver.Chrome()  # Make sure you have the ChromeDriver installed and in your PATH
driver.get('http://www.google.com')

search_box = driver.find_element_by_name('q')
search_box.send_keys('GitHub Copilot')
search_box.send_keys(Keys.RETURN)

# Wait for the results to load
time.sleep(5)

driver.quit()