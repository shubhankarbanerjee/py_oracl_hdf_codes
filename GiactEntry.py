from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Launch browser
driver = None
logged_in = False


def get_browser_choice():
    """
    Ask user which browser to use.
    
    Returns:
        str: 'chrome' or 'edge'
    """
    print("\n" + "="*60)
    print("Select browser:")
    print("="*60)
    print("1. Chrome (default)")
    print("2. Microsoft Edge")
    print("="*60)
    
    choice = input("▶ Enter choice (1 or 2, default is 1): ").strip()
    
    if choice == '2':
        return 'edge'
    return 'chrome'


def initialize_driver(browser_type='chrome'):
    """
    Initialize WebDriver for Chrome or Edge.
    
    Args:
        browser_type: 'chrome' or 'edge'
    
    Returns:
        WebDriver instance
    """
    try:
        if browser_type == 'edge':
            print("\n▶ Initializing Microsoft Edge WebDriver...")
            service = Service(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service)
            print("✓ Microsoft Edge WebDriver initialized successfully")
        else:
            print("\n▶ Initializing Google Chrome WebDriver...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service)
            print("✓ Google Chrome WebDriver initialized successfully")
        
        return driver
    except Exception as e:
        print(f"✗ Error initializing WebDriver: {str(e)}")
        return None


def parse_data_paragraph(paragraph):
    """
    Parse data from paragraph format (key=value pairs, one per line).
    
    Expected format:
    AgencyLegalName=City of Cambridge
    FederalTaxID=526000780
    Routing=056001066
    ...
    
    Returns:
        dict: Parsed key-value pairs, or None if paragraph is empty
    """
    if not paragraph or not paragraph.strip():
        return None
    
    form_data = {}
    lines = paragraph.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if '=' in line and line:
            key, value = line.split('=', 1)
            form_data[key.strip()] = value.strip()
    
    if not form_data:
        return None
    
    return form_data


def get_user_input():
    """
    Prompt user for data in paragraph format.
    
    Returns:
        dict: Parsed form data, or None if no data provided
    """
    print("\n" + "="*60)
    print("Enter agency/account data in the following format:")
    print("="*60)
    print("AgencyLegalName=City of Cambridge")
    print("FederalTaxID=526000780")
    print("Routing=056001066")
    print("Account=060000296")
    print("UniqueID=35EDM-CAMUC-UTILI-00")
    print("\nPress Enter twice when done (or just Enter to skip):")
    print("="*60 + "\n")
    
    lines = []
    while True:
        line = input()
        if not line:
            if lines:
                # Two enters = done
                break
            else:
                # First enter with no data = skip
                return None
        lines.append(line)
    
    paragraph = '\n'.join(lines)
    return parse_data_paragraph(paragraph)


def login_to_giact():
    """Login to Giact portal with credentials."""
    global logged_in
    
    if logged_in:
        print("✓ Already logged in")
        return True
    
    try:
        # Open Giact portal login page
        print("\n▶ Navigating to Giact portal...")
        driver.get("https://portal.giact.com/")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        print(f"  Waiting for login form...")
        
        # Accept cookies if prompted
        try:
            driver.find_element(By.ID, "L2AGLb").click()
            time.sleep(1)
            print("  ✓ Accepted cookies")
        except:
            pass
        
        # Wait for UserName field
        print("  Waiting for UserName field...")
        user_box = wait.until(EC.presence_of_element_located((By.ID, "UserName")))
        print("  ✓ UserName field found")
        
        # Enter username
        user_box.clear()
        user_box.send_keys("shubhankar.banerjee@fisglobal.com")
        time.sleep(2)
        print("  ✓ Entered username")
        
        # Wait for Password field
        print("  Waiting for Password field...")
        pwd_box = wait.until(EC.presence_of_element_located((By.ID, "Password")))
        print("  ✓ Password field found")
        
        # Enter password
        pwd_box.clear()
        pwd_box.send_keys("RadheKrishna$108times")
        time.sleep(2)
        print("  ✓ Entered password")
        
        # Click isPerson checkbox
        print("  Clicking isPerson checkbox...")
        try:
            checkbox = wait.until(EC.presence_of_element_located((By.ID, "isPerson")))
            checkbox.click()
            time.sleep(1)
            print("  ✓ Checkbox clicked")
        except Exception as e:
            print(f"  ⚠ Could not click checkbox: {str(e)}")
        
        # Press RETURN to submit login
        print("  Submitting login form...")
        pwd_box.send_keys(Keys.RETURN)
        
        # Wait for login to complete
        print("  Waiting for login to complete...")
        time.sleep(5)
        
        print(f"  Current URL: {driver.current_url}")
        print(f"  Page title: {driver.title}")
        
        print("✓ Successfully logged in to Giact portal")
        logged_in = True
        return True
    
    except Exception as e:
        print(f"✗ Error logging in: {str(e)}")
        print(f"  Current URL: {driver.current_url}")
        print(f"  Page title: {driver.title}")
        return False


def fill_giact_form(form_data):
    """
    Fill and submit the gAuthenticate form with provided data.
    
    Expected form_data dict keys:
    - AgencyLegalName (maps to Business Name)
    - FederalTaxID (maps to Tax ID)
    - Routing (maps to Routing Number)
    - Account (maps to Account Number)
    - UniqueID (maps to UniqueID)
    - CheckNumber (optional)
    - Amount (optional)
    """
    try:
        # Wait for form to load with explicit waits
        print("▶ Waiting for form to load...")
        wait = WebDriverWait(driver, 15)  # 15 second wait
        
        # Wait for at least one form field to be present
        wait.until(EC.presence_of_element_located((By.ID, "routingNumber")))
        print("✓ Form loaded successfully")
        time.sleep(2)
        
        print(f"  Current URL: {driver.current_url}")
        print(f"  Page title: {driver.title}")
        
        # Fill Routing Number
        if 'Routing' in form_data:
            try:
                routing_field = wait.until(EC.presence_of_element_located((By.ID, "routingNumber")))
                routing_field.clear()
                routing_field.send_keys(form_data['Routing'])
                time.sleep(3)
                print(f"✓ Filled Routing Number: {form_data['Routing']}")
            except Exception as e:
                print(f"⚠ Could not fill Routing Number: {str(e)}")
        
        # Fill Account Number
        if 'Account' in form_data:
            try:
                account_field = wait.until(EC.presence_of_element_located((By.ID, "accountNumber")))
                account_field.clear()
                account_field.send_keys(form_data['Account'])
                time.sleep(3)
                print(f"✓ Filled Account Number: {form_data['Account']}")
            except Exception as e:
                print(f"⚠ Could not fill Account Number: {str(e)}")
        
        # Fill Check Number (optional)
        if 'CheckNumber' in form_data and form_data['CheckNumber']:
            try:
                check_field = wait.until(EC.presence_of_element_located((By.ID, "checkNumber")))
                check_field.clear()
                check_field.send_keys(form_data['CheckNumber'])
                time.sleep(3)
                print(f"✓ Filled Check Number: {form_data['CheckNumber']}")
            except Exception as e:
                print(f"⚠ Could not fill Check Number: {str(e)}")
        
        # Fill Amount (optional)
        if 'Amount' in form_data and form_data['Amount']:
            try:
                amount_field = wait.until(EC.presence_of_element_located((By.ID, "amount")))
                amount_field.clear()
                amount_field.send_keys(form_data['Amount'])
                time.sleep(3)
                print(f"✓ Filled Amount: {form_data['Amount']}")
            except Exception as e:
                print(f"⚠ Could not fill Amount: {str(e)}")
        
        # Fill UniqueID
        if 'UniqueID' in form_data:
            try:
                uniqueid_field = wait.until(EC.presence_of_element_located((By.ID, "uniqueID")))
                uniqueid_field.clear()
                uniqueid_field.send_keys(form_data['UniqueID'])
                time.sleep(3)
                print(f"✓ Filled UniqueID: {form_data['UniqueID']}")
            except Exception as e:
                print(f"⚠ Could not fill UniqueID: {str(e)}")
        
        # Fill Business Name (from AgencyLegalName)
        if 'AgencyLegalName' in form_data:
            try:
                business_field = wait.until(EC.presence_of_element_located((By.ID, "businessName")))
                business_field.clear()
                business_field.send_keys(form_data['AgencyLegalName'])
                time.sleep(3)
                print(f"✓ Filled Business Name: {form_data['AgencyLegalName']}")
            except Exception as e:
                print(f"⚠ Could not fill Business Name: {str(e)}")
        
        # Fill Tax ID (from FederalTaxID)
        if 'FederalTaxID' in form_data:
            try:
                taxid_field = wait.until(EC.presence_of_element_located((By.ID, "taxID")))
                taxid_field.clear()
                taxid_field.send_keys(form_data['FederalTaxID'])
                time.sleep(3)
                print(f"✓ Filled Tax ID: {form_data['FederalTaxID']}")
            except Exception as e:
                print(f"⚠ Could not fill Tax ID: {str(e)}")
        
        # Additional optional fields
        if 'FirstName' in form_data and form_data['FirstName']:
            try:
                firstName_field = wait.until(EC.presence_of_element_located((By.ID, "firstName")))
                firstName_field.clear()
                firstName_field.send_keys(form_data['FirstName'])
                time.sleep(3)
                print(f"✓ Filled First Name: {form_data['FirstName']}")
            except Exception as e:
                print(f"⚠ Could not fill First Name: {str(e)}")
        
        if 'LastName' in form_data and form_data['LastName']:
            try:
                lastName_field = wait.until(EC.presence_of_element_located((By.ID, "lastName")))
                lastName_field.clear()
                lastName_field.send_keys(form_data['LastName'])
                time.sleep(3)
                print(f"✓ Filled Last Name: {form_data['LastName']}")
            except Exception as e:
                print(f"⚠ Could not fill Last Name: {str(e)}")
        
        if 'AddressLine1' in form_data and form_data['AddressLine1']:
            try:
                address_field = wait.until(EC.presence_of_element_located((By.ID, "addressLine1")))
                address_field.clear()
                address_field.send_keys(form_data['AddressLine1'])
                time.sleep(3)
                print(f"✓ Filled Address Line 1: {form_data['AddressLine1']}")
            except Exception as e:
                print(f"⚠ Could not fill Address Line 1: {str(e)}")
        
        if 'City' in form_data and form_data['City']:
            try:
                city_field = wait.until(EC.presence_of_element_located((By.ID, "city")))
                city_field.clear()
                city_field.send_keys(form_data['City'])
                time.sleep(3)
                print(f"✓ Filled City: {form_data['City']}")
            except Exception as e:
                print(f"⚠ Could not fill City: {str(e)}")
        
        if 'State' in form_data and form_data['State']:
            try:
                state_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "state"))))
                state_dropdown.select_by_value(form_data['State'])
                time.sleep(3)
                print(f"✓ Selected State: {form_data['State']}")
            except Exception as e:
                print(f"⚠ Could not select State: {str(e)}")
        
        if 'ZipCode' in form_data and form_data['ZipCode']:
            try:
                zipcode_field = wait.until(EC.presence_of_element_located((By.ID, "zipCode")))
                zipcode_field.clear()
                zipcode_field.send_keys(form_data['ZipCode'])
                time.sleep(3)
                print(f"✓ Filled Zip Code: {form_data['ZipCode']}")
            except Exception as e:
                print(f"⚠ Could not fill Zip Code: {str(e)}")
        
        if 'PhoneNumber' in form_data and form_data['PhoneNumber']:
            try:
                phone_field = wait.until(EC.presence_of_element_located((By.ID, "phoneNumber")))
                phone_field.clear()
                phone_field.send_keys(form_data['PhoneNumber'])
                time.sleep(3)
                print(f"✓ Filled Phone Number: {form_data['PhoneNumber']}")
            except Exception as e:
                print(f"⚠ Could not fill Phone Number: {str(e)}")
        
        return True
    
    except Exception as e:
        print(f"✗ Error filling form: {str(e)}")
        print(f"  Current URL: {driver.current_url}")
        print(f"  Page title: {driver.title}")
        return False


def submit_giact_form():
    """Submit the gAuthenticate form."""
    try:
        submit_button = driver.find_element(By.ID, "gAuthenticateSubmit")
        submit_button.click()
        print("✓ Form submitted")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"✗ Error submitting form: {str(e)}")
        return False


def Process_Giact_Entry():
    """
    Main interactive loop to process Giact entries.
    Asks user for data, validates, logs in once, and processes entries.
    """
    global driver
    
    try:
        # Ask user which browser to use
        browser_choice = get_browser_choice()
        
        # Initialize driver
        driver = initialize_driver(browser_choice)
        if not driver:
            print("✗ Failed to initialize WebDriver. Exiting...")
            return
        
        entry_count = 0
        
        while True:
            # Get user input
            form_data = get_user_input()
            
            if not form_data:
                print("\n⊘ No data provided. Exiting...")
                break
            
            print(f"\n{'='*60}")
            print(f"Processing Entry #{entry_count + 1}")
            print(f"{'='*60}")
            print(f"Parsed data: {form_data}")
            
            # Login on first entry
            if not logged_in:
                if not login_to_giact():
                    print("✗ Failed to login. Cannot proceed.")
                    break
            
            # Navigate to form
            try:
                print("\n▶ Navigating to gAuthenticate form...")
                driver.get("https://portal.giact.com/VerificationServices/SingleEntry/gAuthenticate")
                print(f"  Waiting for page to load...")
                time.sleep(5)  # Give the page time to load
                print(f"  Current URL: {driver.current_url}")
                print(f"  Page title: {driver.title}")
            except Exception as e:
                print(f"✗ Error navigating to form: {str(e)}")
                continue
            
            # Fill and submit the form
            if fill_giact_form(form_data):
                if submit_giact_form():
                    entry_count += 1
                    print(f"✓ Entry #{entry_count} submitted successfully")
                    
                    # Ask if there's another entry
                    print("\n" + "="*60)
                    response = input("▶ Do you have another entry? (press Enter for yes, 'n' for no): ").strip().lower()
                    
                    if response == 'n':
                        print("Processing stopped by user")
                        break
                    
                    # Refresh for next entry
                    time.sleep(1)
                    driver.refresh()
                    time.sleep(2)
                else:
                    print(f"✗ Failed to submit entry")
                    response = input("▶ Try another entry? (press Enter for yes, 'n' for no): ").strip().lower()
                    if response == 'n':
                        break
            else:
                print(f"✗ Failed to fill form")
                response = input("▶ Try again? (press Enter for yes, 'n' for no): ").strip().lower()
                if response == 'n':
                    break
        
        print(f"\n{'='*60}")
        print(f"Processing Complete: {entry_count} entries submitted")
        print(f"{'='*60}")
        
        # Wait for user input before closing
        input("\n▶ Press Enter to close the browser...")
        if driver:
            driver.quit()
    
    except Exception as e:
        print(f"✗ Fatal error: {str(e)}")
        if driver:
            driver.quit()


# Main entry point
if __name__ == "__main__":
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  GIACT Single Entry Form Processor".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    Process_Giact_Entry()
