"""
PayDirect Admin Merchant Data Extractor
Fetches all form field names and values from PayDirect Merchant Edit pages
and exports them to a CSV file.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import csv
import time
from datetime import datetime

# Global variables
driver = None
logged_in = False
BASE_URL = "http://p5zlgintc01:16020"


def get_browser_choice():
    """Ask user which browser to use."""
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


def get_merchant_id_range():
    """Ask user for merchant ID range to fetch."""
    print("\n" + "="*60)
    print("Enter Merchant ID Range:")
    print("="*60)
    print("Default: 5200-5246 (47 merchants)")
    print("="*60)
    
    start_id = input("▶ Enter start Merchant ID (default 5200): ").strip()
    end_id = input("▶ Enter end Merchant ID (default 5246): ").strip()
    
    try:
        start_id = int(start_id) if start_id else 5200
        end_id = int(end_id) if end_id else 5246
        
        if start_id > end_id:
            print("✗ Invalid range: start ID cannot be greater than end ID")
            return None
        
        return range(start_id, end_id + 1)
    except ValueError:
        print("✗ Invalid input: please enter valid integers")
        return None


def initialize_driver(browser_type='chrome'):
    """Initialize WebDriver for Chrome or Edge."""
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


def login_to_paydirect():
    """Login to PayDirect portal."""
    global logged_in
    
    if logged_in:
        print("✓ Already logged in")
        return True
    
    try:
        print("\n▶ Navigating to PayDirect portal...")
        driver.get(f"{BASE_URL}/PayDirect/")
        
        wait = WebDriverWait(driver, 15)
        print("  Waiting for login form...")
        
        # Wait for UserName field
        print("  Waiting for UserName field...")
        user_box = wait.until(EC.presence_of_element_located((By.ID, "UserName")))
        print("  ✓ UserName field found")
        
        # Enter username
        user_box.clear()
        user_box.send_keys("sbanerjee@fisfedcloud.com")
        time.sleep(1)
        print("  ✓ Entered username")
        
        # Wait for Password field
        print("  Waiting for Password field...")
        pwd_box = wait.until(EC.presence_of_element_located((By.ID, "Password")))
        print("  ✓ Password field found")
        
        # Enter password
        pwd_box.clear()
        pwd_box.send_keys("RadheKrishna@108times")
        time.sleep(1)
        print("  ✓ Entered password")
        
        # Submit login
        print("  Submitting login form...")
        pwd_box.send_keys(Keys.RETURN)
        
        # Wait for login to complete
        print("  Waiting for login to complete...")
        time.sleep(5)
        
        print(f"  Current URL: {driver.current_url}")
        print(f"  Page title: {driver.title}")
        
        print("✓ Successfully logged in to PayDirect portal")
        logged_in = True
        return True
    
    except Exception as e:
        print(f"✗ Error logging in: {str(e)}")
        print(f"  Current URL: {driver.current_url}")
        print(f"  Page title: {driver.title}")
        return False


def should_skip_field(field_id, field_name):
    """
    Check if a field should be skipped based on pattern matching.
    
    Args:
        field_id: The field ID attribute
        field_name: The field name attribute
    
    Returns:
        bool: True if field should be skipped, False otherwise
    """
    skip_patterns = [
        'CustomizableTextPreferences',
        'IsDescriptionMultilineOtherSelected',
        'MultilineDescription',
        'UserPartPreferences',
        '__IsActive',
        '__Index'
    ]
    
    combined = f"{field_id}_{field_name}".lower()
    for pattern in skip_patterns:
        if pattern.lower() in combined:
            return True
    
    return False


def flatten_value(value):
    """
    Clean field value by removing semicolons, newlines, and carriage returns.
    
    Args:
        value: The value to clean
    
    Returns:
        str: Cleaned value
    """
    if not value:
        return ""
    
    # Convert to string if needed
    value_str = str(value)
    
    # Remove semicolons, newlines, and carriage returns
    value_str = value_str.replace(";", " ")
    value_str = value_str.replace("\n", " ")
    value_str = value_str.replace("\r", " ")
    
    # Clean up multiple spaces
    value_str = " ".join(value_str.split())
    
    return value_str.strip()


def extract_form_fields():
    """
    Extract all form field names and values from the current page.
    - Only captures selected dropdown values
    - Removes specific field patterns
    - Flattens values by removing special characters
    - Uses form labels as field headers
    
    Returns:
        dict: Field labels and their cleaned values
    """
    field_data = {}
    label_map = {}  # Maps field IDs to their labels
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # Wait for form to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        time.sleep(2)  # Additional wait for dynamic content
        
        # Find all form elements
        form = driver.find_element(By.TAG_NAME, "form")
        
        # First, build a map of field IDs to their labels
        try:
            labels = form.find_elements(By.TAG_NAME, "label")
            for label in labels:
                label_text = label.text.strip()
                label_for = label.get_attribute("for")
                if label_text and label_for:
                    label_map[label_for] = label_text
        except:
            pass
        
        # Extract input fields (text, email, number, hidden, etc.)
        inputs = form.find_elements(By.TAG_NAME, "input")
        for input_elem in inputs:
            input_type = input_elem.get_attribute("type")
            input_id = input_elem.get_attribute("id")
            input_name = input_elem.get_attribute("name")
            input_value = input_elem.get_attribute("value")
            
            # Skip hidden fields and RequestVerificationToken
            if input_type == "hidden":
                continue
            
            # Skip fields matching exclusion patterns
            if should_skip_field(input_id or "", input_name or ""):
                continue
            
            field_key = input_id if input_id else input_name
            if field_key and input_value:
                # Get label if available, otherwise use field key
                display_name = label_map.get(input_id, field_key)
                cleaned_value = flatten_value(input_value)
                if cleaned_value:
                    field_data[display_name] = cleaned_value
        
        # Extract select/dropdown fields (only selected values)
        selects = form.find_elements(By.TAG_NAME, "select")
        for select_elem in selects:
            select_id = select_elem.get_attribute("id")
            select_name = select_elem.get_attribute("name")
            
            # Skip fields matching exclusion patterns
            if should_skip_field(select_id or "", select_name or ""):
                continue
            
            field_key = select_id if select_id else select_name
            
            try:
                select_obj = Select(select_elem)
                selected_option = select_obj.first_selected_option
                selected_text = selected_option.text.strip()
                
                # Get label if available, otherwise use field key
                display_name = label_map.get(select_id, field_key)
                cleaned_value = flatten_value(selected_text)
                if cleaned_value:
                    field_data[display_name] = cleaned_value
            except Exception as e:
                # Silent fail for select fields with no selected option
                pass
        
        # Extract textarea fields
        textareas = form.find_elements(By.TAG_NAME, "textarea")
        for textarea in textareas:
            textarea_id = textarea.get_attribute("id")
            textarea_name = textarea.get_attribute("name")
            textarea_value = textarea.text
            
            # Skip fields matching exclusion patterns
            if should_skip_field(textarea_id or "", textarea_name or ""):
                continue
            
            field_key = textarea_id if textarea_id else textarea_name
            if field_key and textarea_value:
                # Get label if available, otherwise use field key
                display_name = label_map.get(textarea_id, field_key)
                cleaned_value = flatten_value(textarea_value)
                if cleaned_value:
                    field_data[display_name] = cleaned_value[:100]  # Truncate long values
        
        return field_data
    
    except Exception as e:
        print(f"  ✗ Error extracting form fields: {str(e)}")
        return {}


def fetch_merchant_data(merchant_ids):
    """
    Fetch data for merchant IDs in the specified range.
    
    Args:
        merchant_ids: range object or list of merchant IDs to fetch
    
    Returns:
        tuple: (list of dictionaries containing merchant data, list of all field names)
    """
    all_merchants_data = []
    all_field_names = set()
    
    total_merchants = len(merchant_ids)
    
    for index, merchant_id in enumerate(merchant_ids, 1):
        try:
            print(f"\n{'='*60}")
            print(f"Processing Merchant {index}/{total_merchants} (ID: {merchant_id})")
            print(f"{'='*60}")
            
            # Navigate to merchant edit page
            url = f"{BASE_URL}/PayDirect/Merchant/Edit/{merchant_id}"
            print(f"▶ Navigating to: {url}")
            driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            print(f"  Current URL: {driver.current_url}")
            print(f"  Page title: {driver.title}")
            
            # Extract form fields
            merchant_data = extract_form_fields()
            
            if merchant_data:
                merchant_data['MerchantID'] = str(merchant_id)
                all_merchants_data.append(merchant_data)
                all_field_names.update(merchant_data.keys())
                print(f"✓ Extracted {len(merchant_data)} fields for merchant {merchant_id}")
            else:
                print(f"⚠ No data extracted for merchant {merchant_id}")
        
        except Exception as e:
            print(f"✗ Error processing merchant {merchant_id}: {str(e)}")
            continue
    
    return all_merchants_data, sorted(list(all_field_names))


def save_to_csv(merchants_data, field_names, filename=None):
    """
    Save extracted merchant data to CSV file with semicolon delimiter.
    
    Args:
        merchants_data: List of merchant data dictionaries
        field_names: List of all field names (column headers)
        filename: Output filename (default: auto-generated)
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"PayDirect_Merchants_{timestamp}.csv"
    
    try:
        print(f"\n{'='*60}")
        print(f"Saving data to CSV: {filename}")
        print(f"{'='*60}")
        
        # Ensure MerchantID is first column
        if 'MerchantID' in field_names:
            field_names.remove('MerchantID')
        field_names = ['MerchantID'] + field_names
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names, delimiter=';')
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            for merchant in merchants_data:
                # Fill missing values with empty string
                row = {field: merchant.get(field, '') for field in field_names}
                writer.writerow(row)
        
        print(f"✓ Successfully saved {len(merchants_data)} merchants to {filename}")
        print(f"  Total columns: {len(field_names)}")
        print(f"  Columns: {'; '.join(field_names[:10])}{'...' if len(field_names) > 10 else ''}")
        
        return filename
    
    except Exception as e:
        print(f"✗ Error saving CSV file: {str(e)}")
        return None


def main():
    """Main execution function."""
    global driver
    
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  PayDirect Merchant Data Extractor".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        # Select browser
        browser_choice = get_browser_choice()
        
        # Initialize driver
        driver = initialize_driver(browser_choice)
        if not driver:
            print("✗ Failed to initialize WebDriver. Exiting...")
            return
        
        # Manual login instruction
        print("\n" + "="*60)
        print("IMPORTANT: Manual Login Required")
        print("="*60)
        print("1. A browser window will open to the PayDirect portal")
        print("2. ▶ Please log in manually with your credentials")
        print("3. Once logged in, return to this console and press Enter")
        print("="*60)
        
        # Open portal for manual login
        print(f"\n▶ Opening PayDirect portal for manual login...")
        driver.get(f"{BASE_URL}/PayDirect/")
        
        input("\n▶ Press Enter once you have logged in successfully...")
        
        print("✓ Proceeding with data extraction...\n")
        
        # Main loop for fetching different ranges
        while True:
            # Get merchant ID range
            merchant_ids = get_merchant_id_range()
            if not merchant_ids:
                response = input("▶ Try again? (press Enter for yes, 'n' for no): ").strip().lower()
                if response == 'n':
                    break
                continue
            
            # Calculate range info
            range_start = list(merchant_ids)[0]
            range_end = list(merchant_ids)[-1]
            total_count = len(merchant_ids)
            
            print(f"\n{'='*60}")
            print(f"Processing merchant range: {range_start} to {range_end} ({total_count} merchants)")
            print(f"{'='*60}")
            
            # Fetch merchant data
            print(f"\n▶ Starting to fetch merchant data...")
            merchants_data, field_names = fetch_merchant_data(merchant_ids)
            
            if merchants_data:
                print(f"\n✓ Successfully extracted data for {len(merchants_data)} merchants")
                
                # Save to CSV
                csv_filename = save_to_csv(merchants_data, field_names)
                
                if csv_filename:
                    print(f"\n✓ Data export completed successfully!")
                    print(f"  File: {csv_filename}")
            else:
                print(f"\n✗ No merchant data was extracted")
            
            # Ask if user wants to process another range
            print(f"\n{'='*60}")
            response = input("▶ Do you want to fetch another range? (press Enter for yes, 'n' for no): ").strip().lower()
            
            if response == 'n':
                break
        
        # Close browser
        print(f"\n▶ Closing browser...")
        input("\nPress Enter to close the browser...")
        driver.quit()
        print("✓ Browser closed")
        print("\n✓ All tasks completed!")
    
    except Exception as e:
        print(f"✗ Fatal error: {str(e)}")
        if driver:
            driver.quit()


# Main entry point
if __name__ == "__main__":
    main()
