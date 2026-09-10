import builtins
import base64
import csv
from datetime import datetime
from io import BytesIO
import json
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, NoSuchWindowException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from pathlib import Path
import re
import time
from urllib.parse import urljoin

MULTIPAY_URL = "https://app.multipayadmin.cus.prod.comm.fisfedcloud.com/"
MULTIPAY_MERCHANTS_URL = urljoin(MULTIPAY_URL, "multipay-web-admin/merchants")
PAYDIRECT_URL = "http://p5zlgintc01:16020/PayDirect/"
PAYDIRECT_DEFAULT_RETURN_URL = "https://wipp.edmundsassoc.com"
LOG_FILE_PATH = Path(__file__).with_name("PayDirAdminMig2Mulpay.log")
CSS_BACKUP_LOG_PATH = Path(__file__).with_name("PayDirAdminMig2Mulpay.SiteCssBackup.log")
SWIPE_BACKUP_LOG_PATH = Path(__file__).with_name("PayDirAdminMig2Mulpay.SwipeBackup.log")
SESSION_CONTEXT_PATH = Path(__file__).with_name("PayDirAdminMig2Mulpay.session.json")
COOKIE_STORE_PATH = Path(__file__).with_name("PayDirAdminMig2Mulpay.cookies.json")
SCREENSHOTS_DIR = Path(__file__).with_name("screenshots")
BATCH_SIZE = 50
RUN_ISSUES = []
PAYDIRECT_PROFILE_CACHE = {}
PAYDIRECT_PROFILE_CACHE_LOADED = False
STATUS_ROWS = {}
STATUS_CSV_PATH = None
STATUS_CSV_COLUMNS = [
    "SITE_NAME",
    "Swipe_Checkbox?",
    "Imported count",
    "Screenshot name",
    "LOGO Replaced",
    "CSS saved",
    "Redirect done",
    "Undo Swipe",
    "Undo CSS",
    "Undo Redirect",
    "PD_Site_URL",
    "Merchant Code",
]
PAYDIRECT_CSS_TEXT = """#submitButton allowAutoDisable{ color: red; } input.submitButton {color: red !important; } #SubmitButton { color: red !important; }

 .multipay-font {
          font-family: Arial, sans-serif;
        } 

        .multipay-header {
          background: #2a62b1;
        } 

        .multipay-breadcrumbs {
          background: #F5F6F7;
        } 

        .multipay-breadcrumbs .active {
          color: #2a62b1;
          font-weight: 800;
        }
	.multipay-edit-button {
          color: #FFFFFF !important;
          background: #2a62b1 !important;
        }

         .multipay-button {
          background: #2a62b1;
        } 

        .multipay-button-hover {
          background: #0D2E47;
        } 

        .multipay-button-disabled {
          background: #C7CDD4 !important;
        }    

        .multipay-input-focused {
          color: #2a62b1 !important;
          border-color: #2a62b1 !important;
        } 

        .multipay-input-error {
          color: #red !important;
          border-color: #red !important;
        } 

        .multipay-input-disabled {
          color: #7A7A7A !important;
          border-color: #C7CDD4 !important;
        } 

        .multipay-payment-icon {
          width: 40px !important;
          height: 40px !important;
        }

        .multipay-icon {
          color: #fff !important;
        } 

        .multipay-tooltip {
          font-family: "Times New Roman", Times, serif;
        } 

        .multipay-checkbox {
          border-color: #000000 !important;
          background-color: #fff !important;
        }

#userParts {
  display: flex;
  flex-direction: column;
}
        .multipay-checkbox-checked {
          background-color: #000000 !important;
          border-color: #ffffff !important;
        }

 

        .multipay-checkbox-label {
          background-color: #ffffff;
        }  """


def get_log_status(message):
    """Infer a log status from the console message prefix/content."""
    stripped_message = message.strip()
    if not stripped_message:
        return None
    if stripped_message.startswith("✗") or "fatal error" in stripped_message.lower():
        return "ERROR"
    if stripped_message.startswith("▶"):
        return "STARTED"
    if stripped_message.startswith("✓"):
        return "DONE"
    return "INFO"


def prepend_log_entry(message, status=None):
    """Write log entries with newest messages at the top of the file."""
    lines = [line.strip() for line in str(message).splitlines() if line.strip()]
    if not lines:
        return

    existing_content = ""
    if LOG_FILE_PATH.exists():
        existing_content = LOG_FILE_PATH.read_text(encoding="utf-8")

    new_entries = []
    for line in lines:
        line_status = status or get_log_status(line)
        if not line_status:
            continue
        timestamp = datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        new_entries.append(f"{timestamp} - {line_status} - {line}")

    if not new_entries:
        return

    new_content = "\n".join(new_entries)
    if existing_content:
        new_content = new_content + "\n" + existing_content

    LOG_FILE_PATH.write_text(new_content, encoding="utf-8")


def print(*args, sep=" ", end="\n", file=None, flush=False):
    """Mirror console output to the log file using the requested format."""
    message = sep.join(str(arg) for arg in args)
    prepend_log_entry(message)
    builtins.print(*args, sep=sep, end=end, file=file, flush=flush)


def prompt_input(prompt):
    """Display and log an input prompt before reading user input."""
    print(prompt, end="")
    return input()


def prompt_yes_no(prompt, default=False):
    """Prompt for yes/no input and return a boolean answer."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        value = prompt_input(prompt + suffix).strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("✗ Please answer with y or n.")


def record_run_issue(site_name, step_label, message):
    """Record a site-level issue for end-of-run reporting."""
    RUN_ISSUES.append(
        {
            "site": site_name,
            "step": step_label,
            "message": str(message),
        }
    )
    mark_status_error_for_step(site_name, step_label)


def get_status_row(site_name):
    """Return the per-site status row, creating it when needed."""
    if site_name not in STATUS_ROWS:
        STATUS_ROWS[site_name] = {column: "NA" for column in STATUS_CSV_COLUMNS}
        STATUS_ROWS[site_name]["SITE_NAME"] = site_name
    return STATUS_ROWS[site_name]


def initialize_status_rows(site_list):
    """Ensure all requested sites appear in the final status CSV."""
    for site_name in site_list:
        get_status_row(site_name)


def update_site_status(site_name, **updates):
    """Update one or more final CSV status values for a site."""
    status_row = get_status_row(site_name)
    for key, value in updates.items():
        status_row[key] = value


def mark_status_error_for_step(site_name, step_label):
    """Mark final CSV status columns as Error for failed workflow steps."""
    step_text = str(step_label)
    step_to_column = {
        "Step 2": "LOGO Replaced",
        "Step 3": "CSS saved",
        "Step 4": "Redirect done",
        "Step 5": "Swipe_Checkbox?",
        "Step 6": "CSS saved",
        "Step 7": "Undo CSS",
        "Step 8": "Undo Swipe",
        "Step 9": "Undo Redirect",
    }
    updates = {}
    for step_name, column_name in step_to_column.items():
        if step_name in step_text:
            updates[column_name] = "Error"
    if updates:
        update_site_status(site_name, **updates)


def get_status_csv_path():
    """Return the single status CSV path for this run."""
    global STATUS_CSV_PATH

    if STATUS_CSV_PATH is None:
        STATUS_CSV_PATH = Path(__file__).with_name(
            f"PayDirAdminMig2Mulpay_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    return STATUS_CSV_PATH


def write_status_csv(reason="update"):
    """Write the current per-site run status CSV."""
    if not STATUS_ROWS:
        print("  No site status rows to write.")
        return None

    status_csv_path = get_status_csv_path()
    with status_csv_path.open("w", newline="", encoding="utf-8-sig") as status_file:
        writer = csv.DictWriter(status_file, fieldnames=STATUS_CSV_COLUMNS)
        writer.writeheader()
        for status_row in STATUS_ROWS.values():
            writer.writerow(status_row)

    print(f"✓ Status CSV {reason}: {status_csv_path}")
    return status_csv_path


def display_run_issues():
    """Print all incomplete/error sites collected during this run."""
    if not RUN_ISSUES:
        print("\n✓ No incomplete/error sites recorded during this execution.")
        return

    print("\n" + "=" * 60)
    print("INCOMPLETE / ERROR SITES")
    print("=" * 60)
    for index, issue in enumerate(RUN_ISSUES, start=1):
        print(
            f"{index}. Site: {issue['site']} | "
            f"Step: {issue['step']} | Issue: {issue['message']}"
        )
    print("=" * 60)


def get_site_preview(site_list, max_items=20):
    """Return a compact preview string for large site lists."""
    if len(site_list) <= max_items:
        return ", ".join(site_list)
    preview = ", ".join(site_list[:max_items])
    return f"{preview}, ... ({len(site_list) - max_items} more)"


def get_browser_choice():
    """Ask user which browser to use and return the selected browser type."""
    print("\n" + "=" * 60)
    print("Select browser:")
    print("=" * 60)
    print("1. Chrome (default)")
    print("2. Microsoft Edge")
    print("=" * 60)

    choice = prompt_input("▶ Enter choice (1 or 2, default is 1): ").strip()
    if choice == "2":
        return "edge"
    return "chrome"


def get_persistent_profile_dir(browser_type):
    """Return a dedicated browser profile folder for persistent login sessions."""
    profile_root = Path(__file__).with_name(".paydir_browser_profile")
    target = profile_root / browser_type
    target.mkdir(parents=True, exist_ok=True)
    return str(target.resolve())


def initialize_driver(browser_type="chrome", profile_dir=None):
    """Initialize and return WebDriver for Chrome or Edge."""
    try:
        if browser_type == "edge":
            print("\n▶ Initializing Microsoft Edge WebDriver...")
            edge_options = webdriver.EdgeOptions()
            if profile_dir:
                edge_options.add_argument(f"--user-data-dir={profile_dir}")
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=edge_options)
            print("✓ Microsoft Edge WebDriver initialized successfully")
        else:
            print("\n▶ Initializing Google Chrome WebDriver...")
            chrome_options = webdriver.ChromeOptions()
            if profile_dir:
                chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✓ Google Chrome WebDriver initialized successfully")

        driver.maximize_window()
        return driver
    except Exception as exc:
        print(f"✗ Error initializing WebDriver: {exc}")
        return None


def open_required_sites(driver, open_multipay=True, open_paydirect=False):
    """
    Open required sites in browser tabs.

    Returns:
        dict: Handles for opened tabs with keys 'multipay' and optionally 'paydirect'
    """
    handles = {}

    if open_multipay:
        print("\n▶ Opening MultiPay Admin site...")
        driver.get(MULTIPAY_URL)
        handles["multipay"] = driver.current_window_handle
        print(f"✓ MultiPay Admin opened: {MULTIPAY_URL}")
    else:
        print("✓ MultiPay Admin tab skipped (not required for selected steps)")

    if open_paydirect:
        if handles:
            print("\n▶ Opening PayDirect Admin site in a new tab...")
            driver.switch_to.new_window("tab")
        else:
            print("\n▶ Opening PayDirect Admin site...")
        driver.get(PAYDIRECT_URL)
        handles["paydirect"] = driver.current_window_handle
        print(f"✓ PayDirect Admin opened: {PAYDIRECT_URL}")
    else:
        print("✓ PayDirect Admin tab skipped (not required for selected steps)")

    return handles


def save_site_cookies(driver, handles):
    """Save cookies for MultiPay and PayDirect tabs to disk."""
    cookie_data = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "multipay": [],
        "paydirect": [],
    }

    for site_key in ["multipay", "paydirect"]:
        if site_key not in handles:
            continue
        driver.switch_to.window(handles[site_key])
        cookie_data[site_key] = driver.get_cookies()

    COOKIE_STORE_PATH.write_text(json.dumps(cookie_data, indent=2), encoding="utf-8")
    print(
        "✓ Cookies saved: "
        f"multipay={len(cookie_data['multipay'])}, paydirect={len(cookie_data['paydirect'])}"
    )


def load_site_cookies(driver, handles):
    """Load previously saved cookies into both site tabs when available."""
    if not COOKIE_STORE_PATH.exists():
        print("  No cookie file found. Proceeding without cookie restore.")
        return False

    try:
        cookie_data = json.loads(COOKIE_STORE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"✗ Failed to read cookie file: {exc}")
        return False

    loaded_counts = {"multipay": 0, "paydirect": 0}
    for site_key in ["multipay", "paydirect"]:
        if site_key not in handles:
            continue

        site_cookies = cookie_data.get(site_key, [])
        if not site_cookies:
            continue

        driver.switch_to.window(handles[site_key])
        for cookie in site_cookies:
            try:
                cookie_payload = dict(cookie)
                if "expiry" in cookie_payload and cookie_payload["expiry"] is not None:
                    cookie_payload["expiry"] = int(cookie_payload["expiry"])
                driver.add_cookie(cookie_payload)
                loaded_counts[site_key] += 1
            except Exception:
                continue

        driver.refresh()
        time.sleep(1)

    total_loaded = loaded_counts["multipay"] + loaded_counts["paydirect"]
    if total_loaded > 0:
        print(
            "✓ Cookies loaded: "
            f"multipay={loaded_counts['multipay']}, paydirect={loaded_counts['paydirect']}"
        )
        return True

    print("  Cookie file present, but no cookies could be loaded.")
    return False


def wait_for_manual_authentication(driver, handles, require_multipay=True, require_paydirect=False):
    """Pause for user to authenticate required sites and verify their readiness."""
    print("\n" + "=" * 60)
    print("MANUAL AUTHENTICATION REQUIRED")
    print("=" * 60)

    instruction_number = 1
    if require_multipay:
        print(f"{instruction_number}. Authenticate in the MultiPay Admin tab")
        instruction_number += 1
    else:
        print(f"{instruction_number}. MultiPay login is not required for selected steps")
        instruction_number += 1

    if require_paydirect:
        print(f"{instruction_number}. Authenticate in the PayDirect Admin tab")
        instruction_number += 1
    else:
        print(f"{instruction_number}. PayDirect login is not required for selected steps")
        instruction_number += 1

    print(f"{instruction_number}. Return here and press Enter to continue")
    print("=" * 60)

    if require_multipay and "multipay" in handles:
        driver.switch_to.window(handles["multipay"])
    elif require_paydirect and "paydirect" in handles:
        driver.switch_to.window(handles["paydirect"])

    if required_sites_login_ready(driver, handles, require_multipay, require_paydirect):
        print("✓ Required login(s) already active")
        return

    while True:
        if require_multipay and require_paydirect:
            prompt_input("\n▶ Press Enter after you have authenticated both websites...")
        elif require_paydirect:
            prompt_input("\n▶ Press Enter after PayDirect authentication is completed...")
        else:
            prompt_input("\n▶ Press Enter after MultiPay authentication is completed...")

        if required_sites_login_ready(driver, handles, require_multipay, require_paydirect):
            print("✓ Required login(s) confirmed")
            break

        if require_multipay and not is_multipay_login_ready(driver, handles):
            print("✗ MultiPay login not ready: Merchants tab did not open/show.")
        if require_paydirect and not is_paydirect_login_ready(driver, handles):
            print("✗ PayDirect login not ready: Profiles table did not open/show.")
        print("  Please complete the required login, then press Enter again.")


def required_sites_login_ready(driver, handles, require_multipay, require_paydirect):
    """Return whether all selected-step site logins are ready."""
    if require_multipay and not is_multipay_login_ready(driver, handles):
        return False
    if require_paydirect and not is_paydirect_login_ready(driver, handles):
        return False
    return True


def is_multipay_login_ready(driver, handles):
    """Check whether MultiPay login is complete by trying to open/show Merchants."""
    if "multipay" not in handles:
        return False

    try:
        driver.switch_to.window(handles["multipay"])
        open_multipay_merchants_page(driver)
        return True
    except Exception:
        return False


def is_paydirect_login_ready(driver, handles):
    """Check whether PayDirect login is complete by loading the profile table."""
    if "paydirect" not in handles:
        return False

    try:
        driver.switch_to.window(handles["paydirect"])
        driver.get(PAYDIRECT_URL)
        wait_for_paydirect_profiles_table(driver)
        return True
    except Exception:
        return False


def get_driver_error_context(driver):
    """Return a compact browser context string for error diagnostics."""
    try:
        current_url = driver.current_url
    except Exception:
        current_url = "(unavailable)"

    try:
        current_handle = driver.current_window_handle
    except Exception:
        current_handle = "(unavailable)"

    return f"url={current_url}, window={current_handle}"


def ensure_site_window(driver, handles, site_key, site_url, allow_reopen=True):
    """Ensure a site window exists and is focused; reopen in a new tab when possible."""
    target_handle = handles.get(site_key)

    try:
        current_handles = driver.window_handles
    except Exception as exc:
        print(f"✗ Unable to read browser windows for {site_key}: {exc}")
        return False

    if target_handle and target_handle in current_handles:
        try:
            driver.switch_to.window(target_handle)
            return True
        except Exception as exc:
            print(f"✗ Failed switching to {site_key} window: {exc}")

    print(f"⚠ {site_key} window handle is missing/closed.")
    if not allow_reopen:
        print(f"✗ Cannot continue because {site_key} window is unavailable.")
        return False

    if not current_handles:
        print("✗ All browser windows are closed. Cannot recover automatically.")
        return False

    try:
        # Anchor on an existing window, then open a fresh tab for recovery.
        driver.switch_to.window(current_handles[0])
        driver.switch_to.new_window("tab")
        driver.get(site_url)
        handles[site_key] = driver.current_window_handle
        print(f"✓ Reopened {site_key} in a new tab: {site_url}")
        return True
    except Exception as exc:
        print(f"✗ Failed to reopen {site_key} window: {exc}")
        return False


def open_fresh_site_window(driver, handles, site_key, site_url):
    """Open a fresh tab for a site and close the previous site tab when possible."""
    old_handle = handles.get(site_key)

    try:
        current_handles = driver.window_handles
    except Exception as exc:
        print(f"✗ Unable to read browser windows for fresh {site_key} open: {exc}")
        return False

    if not current_handles:
        print(f"✗ Cannot open fresh {site_key} tab because all browser windows are closed.")
        return False

    anchor_handle = next((handle for handle in current_handles if handle != old_handle), current_handles[0])

    try:
        driver.switch_to.window(anchor_handle)
        driver.switch_to.new_window("tab")
        driver.get(site_url)
        new_handle = driver.current_window_handle
        handles[site_key] = new_handle
        print(f"✓ Opened fresh {site_key} tab: {site_url}")

        if old_handle and old_handle in current_handles and old_handle != new_handle:
            try:
                driver.switch_to.window(old_handle)
                driver.close()
                print(f"✓ Closed previous {site_key} tab")
            except Exception as exc:
                print(f"  Previous {site_key} tab could not be closed: {exc}")

        driver.switch_to.window(new_handle)
        return True
    except Exception as exc:
        print(f"✗ Failed to open fresh {site_key} tab: {exc}")
        return False


def parse_site_list(site_text):
    """Parse site names separated by commas, spaces, or line breaks."""
    if not site_text or not site_text.strip():
        return []

    tokens = re.split(r"[\s,]+", site_text.strip())
    return [token for token in tokens if token]


def get_site_list(initial_value=""):
    """Return a parsed site list, prompting when the initial value is empty."""
    site_list = parse_site_list(initial_value)
    if site_list:
        return site_list
    return get_site_list_from_paragraph()


def get_site_list_from_paragraph():
    """Collect a multi-line site paragraph until two blank lines are entered."""
    print("\n" + "=" * 60)
    print("SITE LIST INPUT")
    print("=" * 60)
    print("Enter the list of Sites to be migrated")
    print("You may paste multiple lines or use commas/spaces.")
    print("Press Enter twice when done.")
    print("=" * 60)

    lines = []
    blank_line_count = 0

    while True:
        line = input()
        if not line.strip():
            if not lines:
                print("✗ At least one site name is required.")
                continue

            blank_line_count += 1
            if blank_line_count >= 2:
                site_list = parse_site_list("\n".join(lines))
                if site_list:
                    return site_list
            continue

        blank_line_count = 0
        lines.append(line)


def get_selected_steps(default_steps="12345"):
    """Prompt for steps to run and return steps in the requested order."""
    valid_steps = {"1", "2", "3", "4", "5", "6", "7", "8", "9"}
    print("\n" + "=" * 60)
    print("STEP SELECTION")
    print("=" * 60)
    print("Step 1: Import the profile in Multipay Admin")
    print("Step 2: Put the logo in Multipay Admin")
    print("Step 3: Update CSS in Paydirect Admin")
    print("Step 4: Switch On redirect flag in Paydirect Admin")
    print("Step 5: Unsupport Swipe in Paydirect Admin")
    print("Step 6: Append CSS in Paydirect Admin")
    print("Step 7: Reverse CSS change from Paydirect backup log")
    print("Step 8: Reverse Swipe checkbox from Paydirect backup log")
    print("Step 9: Uncheck redirect flag in Paydirect Admin")
    print("=" * 60)
    print("Choose which steps to run.")
    print("Default: 12345 (run all steps in this order)")
    print("Examples: 13, 53124, 789, 573124, 2")
    print("=" * 60)

    while True:
        step_input = prompt_input("▶ Enter steps to run (default 12345): ").strip()
        if not step_input:
            step_input = default_steps

        selected_steps = []
        for ch in step_input:
            if ch in valid_steps and ch not in selected_steps:
                selected_steps.append(ch)

        if selected_steps:
            print(f"✓ Steps selected: {''.join(selected_steps)}")
            return selected_steps

        print("✗ Invalid step selection. Please enter only digits 1 through 9.")


def get_followup_steps():
    """Prompt for optional follow-up steps after a workflow run."""
    value = prompt_input(
        "\n▶ Press Enter to close the browser, or enter step number(s) to run next: "
    ).strip()
    if not value:
        return []

    valid_steps = {"1", "2", "3", "4", "5", "6", "7", "8", "9"}
    selected_steps = []
    for ch in value:
        if ch in valid_steps and ch not in selected_steps:
            selected_steps.append(ch)

    if selected_steps:
        print(f"✓ Follow-up steps selected: {''.join(selected_steps)}")
        return selected_steps

    print("✗ Invalid follow-up step selection. Browser will close.")
    return []


def image_path_to_data_url(image_path):
    """Convert an image file to a data URL string."""
    image_file = Path(image_path)
    ext = image_file.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(ext, "image/png")
    encoded = base64.b64encode(image_file.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def copy_image_to_clipboard_windows(image_path):
    """Try to copy image bytes to Windows clipboard for paste workflows."""
    try:
        from PIL import Image
        import win32clipboard
        import win32con
    except Exception as exc:
        print(f"  Clipboard image copy not available in this environment: {exc}")
        return False

    try:
        with Image.open(image_path) as image_obj:
            bmp_stream = BytesIO()
            image_obj.convert("RGB").save(bmp_stream, "BMP")
            bmp_data = bmp_stream.getvalue()[14:]

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, bmp_data)
        finally:
            win32clipboard.CloseClipboard()

        print("✓ Logo image copied to clipboard")
        return True
    except Exception as exc:
        print(f"  Failed to copy image to clipboard: {exc}")
        return False


def save_site_screenshot(driver, site_name, phase):
    """Save screenshot with required naming format."""
    timestamp = datetime.now().strftime("%d%m%y-%H%M%S")
    screenshot_name = f"{timestamp}_{site_name}_{phase}.png"
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    screenshot_path = SCREENSHOTS_DIR / screenshot_name
    if driver.save_screenshot(str(screenshot_path)):
        print(f"✓ Screenshot saved: {screenshot_path}")
        update_site_status(site_name, **{"Screenshot name": screenshot_name})
        return screenshot_name
    else:
        print(f"✗ Failed to save screenshot: {screenshot_path}")
        return None


def click_visible_button_by_id(driver, button_id):
    """Click the first visible and enabled button by id."""
    buttons = driver.find_elements(By.ID, button_id)
    for button in buttons:
        if button.is_displayed() and button.is_enabled():
            driver.execute_script("arguments[0].click();", button)
            return True
    return False


def wait_for_dialog_to_close(driver, timeout=15):
    """Wait until the custom-text dialog is closed after Apply click."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "mat-dialog-container"))
        )
        print("✓ Dialog closed after Apply")
        return True
    except TimeoutException:
        print("  Dialog did not close within wait time; continuing with Save attempt")
        return False


def click_save_button_with_wait(driver, timeout=20):
    """Wait for Save to become enabled, then click it."""
    try:
        save_button = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "save"))
        )
    except TimeoutException:
        print("✗ Save button not found on page")
        return False

    try:
        WebDriverWait(driver, timeout).until(
            lambda current_driver: (
                (btn := current_driver.find_element(By.ID, "save"))
                and btn.is_displayed()
                and btn.is_enabled()
                and btn.get_attribute("disabled") is None
            )
        )
    except TimeoutException:
        disabled_attr = save_button.get_attribute("disabled")
        classes = save_button.get_attribute("class")
        print(
            "  Save button stayed disabled. "
            f"disabled={disabled_attr}, enabled={save_button.is_enabled()}, class={classes}"
        )
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", save_button)
        save_button.click()
    except Exception:
        driver.execute_script("arguments[0].click();", save_button)

    time.sleep(1)
    print("✓ Save clicked (second pass)")
    return True


def replace_logo_in_custom_text_dialog(driver, logo_data_url, clipboard_prepared):
    """Replace dialog image content with new logo, using clipboard paste when possible."""
    editor = wait_for_clickable(driver, By.CSS_SELECTOR, ".ProseMirror")
    editor.click()

    replaced = False
    if clipboard_prepared:
        try:
            editor.send_keys(Keys.CONTROL, "a")
            editor.send_keys(Keys.BACKSPACE)
            editor.send_keys(Keys.CONTROL, "v")
            time.sleep(1)
            replaced = bool(editor.find_elements(By.CSS_SELECTOR, "img"))
            if replaced:
                print("✓ Replaced logo via clipboard paste")
        except Exception as exc:
            print(f"  Clipboard paste attempt failed: {exc}")

    if not replaced:
        driver.execute_script(
            """
            const editor = document.querySelector('.ProseMirror');
            if (!editor) return false;
            editor.innerHTML = '';
            const p = document.createElement('p');
            const img = document.createElement('img');
            img.src = arguments[0];
            img.alt = 'site_logo';
            p.appendChild(img);
            editor.appendChild(p);
            editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
            editor.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
            """,
            logo_data_url,
        )
        print("✓ Replaced logo via direct editor update")


def apply_custom_text_changes(driver):
    """Click Apply first, then click Save if enabled."""
    print("▶ Clicking Apply (first pass)...")
    if click_visible_button_by_id(driver, "apply"):
        print("✓ Apply clicked (first pass)")
    else:
        print("✗ Apply button not clickable on first pass")
        return False

    wait_for_dialog_to_close(driver)
    print("▶ Clicking Save (second pass if enabled)...")
    save_clicked = click_save_button_with_wait(driver)
    if not save_clicked:
        print("  Second Save click skipped (button not enabled/visible)")
    return save_clicked


def open_hosted_payment_tab_for_site(driver, site_name):
    """Open hosted payment custom-text page for a specific site in a new tab."""
    site_url = (
        "https://app.multipayadmin.cus.prod.comm.fisfedcloud.com/"
        f"multipay-web-admin/merchants/{site_name}/custom-text/hosted-payment"
    )
    driver.switch_to.new_window("tab")
    driver.get(site_url)
    wait_for_clickable(driver, By.ID, "siteHeader", timeout=30)
    print(f"✓ Opened hosted payment page for {site_name}")


def wait_for_clickable(driver, by, value, timeout=20):
    """Wait until an element is clickable and return it."""
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))


def xpath_literal(value):
    """Return an XPath string literal for values that may contain quotes."""
    if '"' not in value:
        return f'"{value}"'
    if "'" not in value:
        return f"'{value}'"

    parts = value.split('"')
    xpath_parts = []
    for index, part in enumerate(parts):
        if part:
            xpath_parts.append(f'"{part}"')
        if index < len(parts) - 1:
            xpath_parts.append("'\"'")
    return "concat(" + ", ".join(xpath_parts) + ")"


def wait_for_paydirect_profiles_table(driver):
    """Wait until the PayDirect profile list table is available."""
    return WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "Profiles")))


def get_matching_column_index(headers, required_words):
    """Return the first header index containing all required words."""
    for index, header in enumerate(headers):
        normalized_header = re.sub(r"[^a-z0-9]+", "", header.lower())
        if all(word in normalized_header for word in required_words):
            return index
    return None


def load_paydirect_profile_cache(driver):
    """Cache PayDirect profile table values used by later site edits."""
    global PAYDIRECT_PROFILE_CACHE_LOADED

    if PAYDIRECT_PROFILE_CACHE_LOADED:
        return

    print("▶ Loading PayDirect profile table cache...")
    driver.get(PAYDIRECT_URL)
    table = wait_for_paydirect_profiles_table(driver)
    header_cells = table.find_elements(By.CSS_SELECTOR, "thead th")
    if not header_cells:
        header_cells = table.find_elements(By.XPATH, ".//tr[th][1]/th")
    headers = [cell.text.strip() for cell in header_cells]
    site_index = get_matching_column_index(headers, ["site", "name"])
    merchant_index = get_matching_column_index(headers, ["merchant", "code"])

    rows = table.find_elements(By.XPATH, ".//tr[td]")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 3:
            continue

        resolved_site_index = site_index if site_index is not None and site_index < len(cells) else 2
        resolved_merchant_index = merchant_index if merchant_index is not None and merchant_index < len(cells) else 1
        site_name = cells[resolved_site_index].text.strip()
        if not site_name:
            continue

        try:
            edit_url = get_paydirect_edit_url_from_row(row)
        except Exception:
            edit_url = ""

        PAYDIRECT_PROFILE_CACHE[site_name.strip().lower()] = {
            "site_name": site_name,
            "merchant_code": cells[resolved_merchant_index].text.strip() if resolved_merchant_index < len(cells) else "",
            "edit_url": edit_url,
        }

    PAYDIRECT_PROFILE_CACHE_LOADED = True
    print(f"✓ PayDirect profile cache loaded: {len(PAYDIRECT_PROFILE_CACHE)} row(s)")


def find_paydirect_profile_row(driver, site_name):
    """Find the PayDirect profile row whose Merchant Site Name matches site_name."""
    wait_for_paydirect_profiles_table(driver)
    site_literal = xpath_literal(site_name.strip())
    row_xpath = f"//table[@id='Profiles']//tr[td[3][normalize-space()={site_literal}]]"
    return WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, row_xpath)))


def log_paydirect_profile_row(row, site_name):
    """Log the PayDirect profile row values for auditability."""
    cells = row.find_elements(By.TAG_NAME, "td")
    row_values = [cell.text.strip() for cell in cells]
    print(f"✓ PayDirect row for {site_name}: {' | '.join(row_values)}")


def get_paydirect_edit_url_from_row(row):
    """Return the merchant edit URL from the first column link in a PayDirect row."""
    edit_link = row.find_element(By.CSS_SELECTOR, "td:first-child a[href]")
    href = edit_link.get_attribute("href")
    if not href:
        raise RuntimeError("PayDirect edit link did not contain an href.")
    return urljoin(PAYDIRECT_URL, href)


def open_paydirect_edit_page_for_site(driver, site_name):
    """Open the PayDirect edit page for one site by resolving it from the profile table."""
    load_paydirect_profile_cache(driver)
    profile = PAYDIRECT_PROFILE_CACHE.get(site_name.strip().lower())
    if profile and profile.get("edit_url"):
        edit_url = profile["edit_url"]
        update_site_status(
            site_name,
            **{
                "PD_Site_URL": edit_url,
                "Merchant Code": profile.get("merchant_code") or "NA",
            },
        )
        print(f"✓ PayDirect cached row for {site_name}: {profile.get('merchant_code') or '(no merchant code)'} | {edit_url}")
    else:
        print(f"▶ Searching PayDirect profile list for site: {site_name}")
        driver.get(PAYDIRECT_URL)
        row = find_paydirect_profile_row(driver, site_name)
        log_paydirect_profile_row(row, site_name)
        edit_url = get_paydirect_edit_url_from_row(row)
        cells = row.find_elements(By.TAG_NAME, "td")
        merchant_code = cells[1].text.strip() if len(cells) > 1 else "NA"
        update_site_status(site_name, **{"PD_Site_URL": edit_url, "Merchant Code": merchant_code})
    print(f"▶ Opening PayDirect edit page: {edit_url}")
    driver.get(edit_url)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "editForm")))
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "saveButton")))
    print(f"✓ PayDirect edit page loaded for {site_name}")


def open_paydirect_look_and_feel_tab(driver):
    """Open the Look and Feel tab on the PayDirect edit page."""
    print("▶ Opening Look and Feel tab...")
    tab_link = wait_for_clickable(driver, By.CSS_SELECTOR, "a[href='#lookandfeel']", timeout=30)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab_link)
    driver.execute_script("arguments[0].click();", tab_link)
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "SiteCss")))
    print("✓ Look and Feel tab opened")


def open_paydirect_site_settings_tab(driver):
    """Open the Site Settings tab on the PayDirect edit page."""
    print("▶ Opening Site Settings tab...")
    tab_link = wait_for_clickable(driver, By.CSS_SELECTOR, "a[href='#basics']", timeout=30)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab_link)
    driver.execute_script("arguments[0].click();", tab_link)
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "RedirectToMultipayWeb")))
    print("✓ Site Settings tab opened")


def open_paydirect_pos_tab(driver):
    """Open the POS tab on the PayDirect edit page."""
    print("▶ Opening POS tab...")
    tab_link = wait_for_clickable(driver, By.CSS_SELECTOR, "a[href='#pos']", timeout=30)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab_link)
    driver.execute_script("arguments[0].click();", tab_link)
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "IsSwipeSupported")))
    print("✓ POS tab opened")


def log_existing_paydirect_css(driver, css_field, site_name=None):
    """Append the existing PayDirect CSS textarea content before updating."""
    existing_css = css_field.get_attribute("value") or ""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    site_label = site_name or "(unknown site)"

    try:
        current_url = driver.current_url
    except Exception:
        current_url = "(unavailable)"

    backup_entry = (
        "\n"
        + "=" * 80
        + f"\nSaved at: {timestamp}\n"
        + f"Site: {site_label}\n"
        + f"URL: {current_url}\n"
        + "Existing SiteCss content:\n"
        + existing_css
        + "\n"
    )
    with CSS_BACKUP_LOG_PATH.open("a", encoding="utf-8") as backup_file:
        backup_file.write(backup_entry)

    print(f"✓ Existing PayDirect SiteCss backed up for {site_label}: {CSS_BACKUP_LOG_PATH}")
    print(f"Existing PayDirect SiteCss content for {site_label}:")
    if existing_css.strip():
        print(existing_css)
    else:
        print("(empty)")


def get_latest_paydirect_css_backup(site_name):
    """Return the most recent logged SiteCss backup for one site."""
    if not CSS_BACKUP_LOG_PATH.exists():
        raise RuntimeError(f"CSS backup log not found: {CSS_BACKUP_LOG_PATH}")

    log_text = CSS_BACKUP_LOG_PATH.read_text(encoding="utf-8")
    matching_css_values = []
    for block in log_text.split("=" * 80):
        if f"Site: {site_name}" not in block:
            continue
        marker = "Existing SiteCss content:\n"
        if marker not in block:
            continue
        matching_css_values.append(block.split(marker, 1)[1].rstrip("\n"))

    if not matching_css_values:
        raise RuntimeError(f"No CSS backup found for {site_name} in {CSS_BACKUP_LOG_PATH}")

    return matching_css_values[-1]


def restore_paydirect_css_from_backup(driver, site_name):
    """Restore SiteCss from the latest backup log entry for the site."""
    backup_css = get_latest_paydirect_css_backup(site_name)
    css_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "SiteCss")))
    driver.execute_script(
        """
        const field = arguments[0];
        field.value = arguments[1];
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        css_field,
        backup_css,
    )
    print(f"✓ PayDirect SiteCss restored from backup log for {site_name}")


def log_paydirect_swipe_status(site_name, was_checked):
    """Append the previous swipe checkbox state before Step 5 changes it."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    backup_entry = (
        "\n"
        + "=" * 80
        + f"\nSaved at: {timestamp}\n"
        + f"Site: {site_name}\n"
        + f"IsSwipeSupported: {'checked' if was_checked else 'unchecked'}\n"
    )
    with SWIPE_BACKUP_LOG_PATH.open("a", encoding="utf-8") as backup_file:
        backup_file.write(backup_entry)
    print(
        f"✓ Previous swipe support state backed up for {site_name}: "
        f"{'checked' if was_checked else 'unchecked'}"
    )


def get_paydirect_swipe_status(driver):
    """Return the current PayDirect swipe support checkbox state."""
    open_paydirect_pos_tab(driver)
    swipe_supported = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "IsSwipeSupported"))
    )
    return swipe_supported.is_selected()


def update_paydirect_swipe_status_result(site_name, initial_swipe_checked, final_swipe_checked):
    """Update final CSV swipe status from before/after checkbox state."""
    current_status = get_status_row(site_name).get("Swipe_Checkbox?")
    if initial_swipe_checked and not final_swipe_checked:
        update_site_status(site_name, **{"Swipe_Checkbox?": "Done"})
        print(f"✓ Swipe status changed to unchecked for {site_name}; status set to Done")
    elif not initial_swipe_checked and not final_swipe_checked:
        if current_status == "Done":
            print(f"✓ Swipe status already marked Done for {site_name}; keeping Done")
            return
        update_site_status(site_name, **{"Swipe_Checkbox?": "UNCH"})
        print(f"✓ Swipe was already unchecked for {site_name}; status set to UNCH")
    else:
        print(
            f"  Swipe status for {site_name}: "
            f"initial={'checked' if initial_swipe_checked else 'unchecked'}, "
            f"final={'checked' if final_swipe_checked else 'unchecked'}"
        )


def get_latest_paydirect_swipe_backup(site_name):
    """Return the most recent logged swipe checkbox state for one site."""
    if not SWIPE_BACKUP_LOG_PATH.exists():
        raise RuntimeError(f"Swipe backup log not found: {SWIPE_BACKUP_LOG_PATH}")

    log_text = SWIPE_BACKUP_LOG_PATH.read_text(encoding="utf-8")
    matching_values = []
    for block in log_text.split("=" * 80):
        if f"Site: {site_name}" not in block:
            continue
        match = re.search(r"^IsSwipeSupported:\s*(checked|unchecked)\s*$", block, flags=re.MULTILINE)
        if match:
            matching_values.append(match.group(1) == "checked")

    if not matching_values:
        raise RuntimeError(f"No swipe backup found for {site_name} in {SWIPE_BACKUP_LOG_PATH}")

    return matching_values[-1]


def set_paydirect_css_text(driver, css_text, site_name=None):
    """Replace the standard PayDirect CSS textarea value after backing it up."""
    css_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "SiteCss")))
    log_existing_paydirect_css(driver, css_field, site_name=site_name)
    driver.execute_script(
        """
        const field = arguments[0];
        field.value = arguments[1];
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        css_field,
        css_text,
    )
    print("✓ PayDirect SiteCss text updated")


def append_paydirect_css_text(driver, css_text, site_name=None):
    """Append the standard PayDirect CSS textarea value once after backing it up."""
    css_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "SiteCss")))
    log_existing_paydirect_css(driver, css_field, site_name=site_name)
    existing_css = css_field.get_attribute("value") or ""
    css_to_append = css_text.strip()

    if css_to_append in existing_css:
        print(f"✓ PayDirect SiteCss already contains standard CSS for {site_name}; append skipped")
        return False

    if existing_css.strip():
        updated_css = existing_css.rstrip() + "\n\n" + css_to_append
    else:
        updated_css = css_to_append

    driver.execute_script(
        """
        const field = arguments[0];
        field.value = arguments[1];
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        css_field,
        updated_css,
    )
    print("✓ PayDirect SiteCss text appended")
    return True


def set_empty_paydirect_url_field(driver, field_id, default_value):
    """Set a PayDirect URL input only when its current value is blank."""
    field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, field_id)))
    existing_value = (field.get_attribute("value") or "").strip()
    if existing_value:
        print(f"✓ PayDirect {field_id} already populated")
        return False

    driver.execute_script(
        """
        const field = arguments[0];
        field.value = arguments[1];
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        field,
        default_value,
    )
    print(f"✓ PayDirect {field_id} populated with default URL")
    return True


def ensure_paydirect_return_urls(driver, site_name):
    """Populate required PayDirect return/cancel URLs when blank, then save changes."""
    print(f"▶ Checking PayDirect return URLs for {site_name}...")
    changed = False
    changed |= set_empty_paydirect_url_field(driver, "ReturnUrl", PAYDIRECT_DEFAULT_RETURN_URL)
    changed |= set_empty_paydirect_url_field(driver, "CancelUrl", PAYDIRECT_DEFAULT_RETURN_URL)

    if not changed:
        print(f"✓ PayDirect return URLs already set for {site_name}")
        return True

    return click_paydirect_save_button(driver, site_name, "return/cancel URL defaults")


def set_checkbox_checked(driver, checkbox_id, checked=True):
    """Set a checkbox to the requested checked state and fire page change events."""
    checkbox = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, checkbox_id)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox)
    if checkbox.is_selected() == checked:
        print(f"✓ Checkbox already {'checked' if checked else 'unchecked'}: {checkbox_id}")
        return

    try:
        checkbox.click()
    except Exception:
        driver.execute_script("arguments[0].click();", checkbox)

    if checkbox.is_selected() != checked:
        driver.execute_script(
            """
            const checkbox = arguments[0];
            checkbox.checked = arguments[1];
            checkbox.dispatchEvent(new Event('input', { bubbles: true }));
            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            checkbox,
            checked,
        )

    if checkbox.is_selected() != checked:
        raise RuntimeError(f"Could not set checkbox {checkbox_id} to {checked}.")
    print(f"✓ Checkbox checked: {checkbox_id}")


def click_paydirect_save_button(driver, site_name, action_label):
    """Click PayDirect Save and wait for the edit form to be available again."""
    print(f"▶ Saving PayDirect {action_label} for {site_name}...")
    save_button = wait_for_clickable(driver, By.ID, "saveButton", timeout=20)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", save_button)
    try:
        save_button.click()
    except Exception:
        driver.execute_script("arguments[0].click();", save_button)

    try:
        WebDriverWait(driver, 30).until(EC.staleness_of(save_button))
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "editForm")))
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "saveButton")))
        print(f"✓ PayDirect {action_label} saved for {site_name}")
        return True
    except TimeoutException:
        print(f"✗ PayDirect save did not return to edit form for {site_name} ({action_label})")
        return False


def is_merchants_menu_visible(driver):
    """Return whether the Merchants child menu is already visible."""
    visible_merchants = driver.find_elements(By.ID, "navMultiPayWebMerchants")
    return any(item.is_displayed() for item in visible_merchants)


def open_multipay_merchants_page(driver):
    """Navigate to the MultiPay Web Merchants page."""
    print(f"▶ Opening Merchants page directly: {MULTIPAY_MERCHANTS_URL}")
    driver.get(MULTIPAY_MERCHANTS_URL)
    try:
        wait_for_clickable(driver, By.ID, "searchMerchants", timeout=20)
        print("✓ Merchants page loaded")
        return
    except TimeoutException:
        print("  Direct Merchants page load did not show search; trying menu navigation")

    print("▶ Opening MultiPay Web menu...")
    if not is_merchants_menu_visible(driver):
        multipay_web_button = wait_for_clickable(driver, By.ID, "navMultiPayWeb")
        try:
            multipay_web_button.click()
        except ElementClickInterceptedException:
            wait_for_backdrop_to_clear(driver, timeout=8)
            driver.execute_script("arguments[0].click();", multipay_web_button)
        WebDriverWait(driver, 10).until(lambda current_driver: is_merchants_menu_visible(current_driver))
    print("✓ MultiPay Web menu expanded")

    print("▶ Opening Merchants page...")
    merchants_button = wait_for_clickable(driver, By.ID, "navMultiPayWebMerchants")
    try:
        merchants_button.click()
    except ElementClickInterceptedException:
        wait_for_backdrop_to_clear(driver, timeout=8)
        driver.execute_script("arguments[0].click();", merchants_button)
    wait_for_clickable(driver, By.ID, "searchMerchants")
    print("✓ Merchants page loaded")


def open_paydirect_import_popup(driver):
    """Open the PayDirect import popup from the Merchants page."""
    wait_for_backdrop_to_clear(driver, timeout=12)
    print("▶ Opening PayDirect import popup...")
    paydirect_import_button = wait_for_clickable(driver, By.ID, "paydirect-import")

    clicked = False
    for _ in range(3):
        try:
            paydirect_import_button.click()
            clicked = True
            break
        except ElementClickInterceptedException:
            wait_for_backdrop_to_clear(driver, timeout=5)
            time.sleep(0.3)

    if not clicked:
        driver.execute_script("arguments[0].click();", paydirect_import_button)

    time.sleep(1)
    wait_for_backdrop_to_clear(driver, timeout=8)
    print("✓ PayDirect import popup opened")


def wait_for_backdrop_to_clear(driver, timeout=8):
    """Wait for blocking Angular Material backdrop overlays to disappear."""
    selectors = [
        ".cdk-overlay-backdrop.cdk-overlay-backdrop-showing",
        ".cdk-overlay-backdrop-showing",
    ]

    for selector in selectors:
        try:
            WebDriverWait(driver, timeout).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            # Continue with next selector/fallback; some pages keep non-blocking backdrops.
            continue


def get_import_popup_root(driver):
    """Return the popup container that owns the PayDirect merchant search field."""
    search_field = wait_for_clickable(driver, By.ID, "searchPayDirectMerchants")
    popup_root_xpath = "ancestor::*[@role='dialog' or contains(@class,'cdk-overlay-pane')][1]"
    try:
        return search_field.find_element(By.XPATH, popup_root_xpath)
    except NoSuchElementException:
        return driver


def get_import_overlay_pane(driver):
    """Return the specific cdk overlay pane that contains the import popup."""
    search_field = wait_for_clickable(driver, By.ID, "searchPayDirectMerchants")
    try:
        return search_field.find_element(By.XPATH, "ancestor::div[contains(@class,'cdk-overlay-pane')][1]")
    except NoSuchElementException:
        return get_import_popup_root(driver)


def get_popup_result_checkboxes(driver):
    """Return enabled result checkboxes from the import popup context."""
    popup_root = get_import_popup_root(driver)
    all_checkboxes = popup_root.find_elements(By.CSS_SELECTOR, "input.mdc-checkbox__native-control[type='checkbox']")
    if not all_checkboxes:
        # Fallback: some Angular overlays render outside the popup root.
        all_checkboxes = driver.find_elements(By.CSS_SELECTOR, "input.mdc-checkbox__native-control[type='checkbox']")
    if not all_checkboxes:
        # Last-resort fallback by type only, in case class names are changed.
        all_checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")

    popup_checkboxes = []

    for checkbox in all_checkboxes:
        try:
            if not checkbox.is_enabled():
                continue

            checkbox_id = (checkbox.get_attribute("id") or "").strip()
            if checkbox_id == "includeInactive-input":
                continue

            popup_checkboxes.append(checkbox)
        except StaleElementReferenceException:
            continue

    return popup_checkboxes


def select_all_visible_unchecked_checkboxes(driver):
    """Select all unchecked checkboxes in the import popup."""
    selected_count = 0
    checkboxes = get_popup_result_checkboxes(driver)

    for checkbox in checkboxes:
        try:
            if checkbox.is_selected():
                continue

            driver.execute_script("arguments[0].click();", checkbox)

            if not checkbox.is_selected():
                # Fallback for hidden/native controls used by Angular Material.
                driver.execute_script(
                    """
                    const cb = arguments[0];
                    cb.checked = true;
                    cb.dispatchEvent(new Event('input', { bubbles: true }));
                    cb.dispatchEvent(new Event('change', { bubbles: true }));
                    """,
                    checkbox,
                )

            if checkbox.is_selected():
                selected_count += 1
            else:
                checkbox_id = checkbox.get_attribute("id") or "(no-id)"
                print(f"  Could not select checkbox: {checkbox_id}")
        except StaleElementReferenceException:
            continue

    return selected_count


def get_checkbox_counts(driver):
    """Return checkbox counts for diagnostics: total, checked, unchecked."""
    total = 0
    checked = 0
    unchecked = 0

    for checkbox in get_popup_result_checkboxes(driver):
        try:
            total += 1
            if checkbox.is_selected():
                checked += 1
            else:
                unchecked += 1
        except StaleElementReferenceException:
            continue

    return total, checked, unchecked


def get_visible_checkbox_debug_ids(driver, max_items=20):
    """Return a short list of visible checkbox ids/names for debugging."""
    debug_values = []
    candidates = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
    for candidate in candidates:
        try:
            if not candidate.is_displayed():
                continue
            value = (candidate.get_attribute("id") or candidate.get_attribute("name") or "(no-id)").strip()
            debug_values.append(value)
            if len(debug_values) >= max_items:
                break
        except StaleElementReferenceException:
            continue
    return debug_values


def get_checkbox_debug_counts(driver):
    """Return debug counts for total/visible checkbox inputs."""
    all_candidates = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
    visible_count = 0
    for candidate in all_candidates:
        try:
            if candidate.is_displayed():
                visible_count += 1
        except StaleElementReferenceException:
            continue
    return len(all_candidates), visible_count


def click_visible_import_button(driver):
    """Click the visible Import button in the active import popup."""
    import_buttons = []
    try:
        popup_root = get_import_popup_root(driver)
        import_buttons = popup_root.find_elements(By.ID, "import")
    except Exception:
        import_buttons = []

    if not import_buttons:
        import_buttons = driver.find_elements(By.ID, "import")

    for button in import_buttons:
        if button.is_displayed() and button.is_enabled():
            driver.execute_script("arguments[0].click();", button)
            return True
    return False


def click_import_button_by_text(driver):
    """Fallback: click visible enabled Import button by label text in popup."""
    xpath = (
        "//button[normalize-space()='Import' or "
        ".//span[contains(normalize-space(), 'Import')]]"
    )
    candidates = []
    try:
        popup_root = get_import_popup_root(driver)
        candidates = popup_root.find_elements(By.XPATH, ".//button[normalize-space()='Import' or .//span[contains(normalize-space(), 'Import')]]")
    except Exception:
        candidates = []

    if not candidates:
        candidates = driver.find_elements(By.XPATH, xpath)

    for button in candidates:
        try:
            if button.is_displayed() and button.is_enabled():
                driver.execute_script("arguments[0].click();", button)
                return True
        except StaleElementReferenceException:
            continue
    return False


def is_import_popup_open(driver):
    """Return whether the PayDirect import popup is currently visible."""
    search_fields = driver.find_elements(By.ID, "searchPayDirectMerchants")
    return any(field.is_displayed() for field in search_fields)


def wait_for_import_popup_to_close(driver, timeout=6):
    """Return True when import popup closes, else False."""
    try:
        WebDriverWait(driver, timeout).until(lambda current_driver: not is_import_popup_open(current_driver))
        return True
    except TimeoutException:
        return False


def click_cancel_and_retry_import(driver):
    """Fallback: click Cancel, ensure popup is open, then retry Import click."""
    print("▶ Import fallback: clicking Cancel, then retrying Import...")

    cancel_clicked = False
    try:
        overlay_pane = get_import_overlay_pane(driver)
        overlay_id = overlay_pane.get_attribute("id") or "(no-overlay-id)"
        print(f"  Using import overlay pane: {overlay_id}")
        cancel_buttons = overlay_pane.find_elements(By.ID, "cancel")
        for button in cancel_buttons:
            if button.is_displayed() and button.is_enabled():
                driver.execute_script("arguments[0].click();", button)
                cancel_clicked = True
                break
    except Exception:
        cancel_clicked = False

    if not cancel_clicked:
        # Fallback to global lookup if popup-root lookup fails.
        cancel_clicked = click_visible_button_by_id(driver, "cancel")

    if cancel_clicked:
        print("✓ Cancel clicked")
        time.sleep(1)
        wait_for_backdrop_to_clear(driver, timeout=10)
    else:
        print("  Cancel button not found/clickable")

    if not is_import_popup_open(driver):
        print("▶ Re-opening PayDirect import popup after Cancel...")
        open_paydirect_import_popup(driver)

    time.sleep(1)
    retry_clicked = click_visible_import_button(driver)
    if retry_clicked:
        print("✓ Import button clicked on retry")
    else:
        print("✗ Import button still not clickable after Cancel retry")
    return retry_clicked


def click_text_retry_import(driver):
    """Fallback: click Import using visible text match."""
    print("▶ Import fallback: trying Import button by text...")
    text_clicked = click_import_button_by_text(driver)
    if text_clicked:
        print("✓ Import button clicked by text fallback")
    else:
        print("✗ Import button not clickable by text fallback")
    return text_clicked


def attempt_step1_import_with_fallbacks(driver):
    """Try Import click strategies and confirm success by popup closure."""
    if click_visible_import_button(driver):
        print("✓ Import button clicked")
        if wait_for_import_popup_to_close(driver):
            print("✓ Import popup closed after click")
            return True
        print("  Import popup is still open after first click")

    print("✗ Could not complete Import on first attempt")

    if click_cancel_and_retry_import(driver):
        if wait_for_import_popup_to_close(driver):
            print("✓ Import popup closed after Cancel+Retry")
            return True
        print("  Import popup is still open after Cancel+Retry")

    if click_text_retry_import(driver):
        if wait_for_import_popup_to_close(driver):
            print("✓ Import popup closed after text fallback")
            return True
        print("  Import popup is still open after text fallback")

    return False


def import_profile_in_multipay(driver, handles, site_list, is_final_batch=False):
    """Step 1: import the profile in MultiPay Admin."""
    print("\n▶ Step 1: Import profile in MultiPay Admin...")
    if not open_fresh_site_window(driver, handles, "multipay", MULTIPAY_MERCHANTS_URL):
        raise RuntimeError("A fresh MultiPay merchants tab could not be opened.")

    print(f"  Sites queued for import: {', '.join(site_list)}")
    open_multipay_merchants_page(driver)
    open_paydirect_import_popup(driver)

    print("▶ Step 1 site import loop started")
    total_selected = 0
    for index, site_name in enumerate(site_list, start=1):
        print(f"▶ Processing site {index}/{len(site_list)}: {site_name}")

        search_field = wait_for_clickable(driver, By.ID, "searchPayDirectMerchants")
        search_field.clear()
        search_field.send_keys(site_name)
        search_field.send_keys(Keys.ENTER)
        time.sleep(1)

        try:
            WebDriverWait(driver, 15).until(
                lambda current_driver: any(
                    item.is_enabled()
                    for item in current_driver.find_elements(
                        By.CSS_SELECTOR,
                        "input[type='checkbox']",
                    )
                )
            )
        except TimeoutException:
            print(f"  No visible checkboxes found for {site_name} within wait time")

        total_count, checked_count, unchecked_count = get_checkbox_counts(driver)
        print(
            f"  Checkbox summary for {site_name}: "
            f"total={total_count}, checked={checked_count}, unchecked={unchecked_count}"
        )
        if total_count == 0:
            all_count, visible_count = get_checkbox_debug_counts(driver)
            print(f"  Checkbox input debug counts: all={all_count}, visible={visible_count}")
            debug_ids = get_visible_checkbox_debug_ids(driver)
            print(f"  Visible checkbox ids for diagnostics: {debug_ids}")

        selected_for_site = select_all_visible_unchecked_checkboxes(driver)
        total_selected += selected_for_site
        update_site_status(site_name, **{"Imported count": selected_for_site})
        if selected_for_site == 0:
            record_run_issue(site_name, "Step 1", "No import checkbox selected")
        print(f"✓ Step 1 site result - {site_name}: {selected_for_site} checkbox(es) checked")

    screenshot_name = datetime.now().strftime("Step1_ImportSites_%Y%m%d_%H%M%S.png")
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    screenshot_path = SCREENSHOTS_DIR / screenshot_name
    if driver.save_screenshot(str(screenshot_path)):
        print(f"✓ Screenshot saved: {screenshot_path}")
        for site_name in site_list:
            update_site_status(site_name, **{"Screenshot name": screenshot_name})
    else:
        print("✗ Failed to save screenshot before import")

    print("▶ Waiting 1 second before clicking Import...")
    time.sleep(1)

    print("▶ Clicking Import button for Step 1...")
    import_completed = attempt_step1_import_with_fallbacks(driver)

    if not import_completed:
        for site_name in site_list:
            record_run_issue(site_name, "Step 1", "Import did not complete automatically")
        if is_final_batch:
            print("\n▶ Manual verification for Step 1 import")
            print("If import did not complete in UI, do it manually now in the same popup.")
            prompt_input("▶ Press Enter after import is completed manually...")
        else:
            print("✗ Step 1 import did not complete automatically for this batch; continuing without manual pause")
    else:
        print("✓ Step 1 import completed automatically")

    print(f"✓ Step 1 complete: processed {len(site_list)} site(s), selected {total_selected} checkbox(es)")


def upload_logo_in_multipay(driver, handles, logo_image_path=None, is_final_batch=False):
    """Step 2: upload/replace logo in MultiPay hosted payment custom text."""
    print("\n▶ Step 2: Upload logo in MultiPay Admin...")
    if not ensure_site_window(driver, handles, "multipay", MULTIPAY_URL, allow_reopen=True):
        raise RuntimeError("MultiPay window is not available and could not be recovered.")
    time.sleep(1)

    if not logo_image_path:
        logo_image_path = str(Path(__file__).with_name("LogoImage.png"))

    logo_file = Path(logo_image_path)
    if not logo_file.is_file():
        print(f"✗ Step 2 aborted. Logo image not found: {logo_file}")
        return

    clipboard_prepared = copy_image_to_clipboard_windows(str(logo_file))
    logo_data_url = image_path_to_data_url(str(logo_file))

    site_list = getattr(upload_logo_in_multipay, "site_list_context", [])
    if not site_list:
        print("✗ Step 2 aborted. No site list context available.")
        return

    if not hasattr(upload_logo_in_multipay, "close_tabs_after_site"):
        upload_logo_in_multipay.close_tabs_after_site = prompt_yes_no(
            "▶ Auto-close each Step 2 site tab after processing?",
            default=True,
        )
    close_tabs_after_site = upload_logo_in_multipay.close_tabs_after_site

    print("▶ Step 2 site loop started")
    base_window = driver.current_window_handle
    had_errors = False

    for index, site_name in enumerate(site_list, start=1):
        is_final_site = is_final_batch and index == len(site_list)
        site_tab_handle = None
        try:
            print(f"▶ Step 2 processing site {index}/{len(site_list)}: {site_name}")
            open_hosted_payment_tab_for_site(driver, site_name)
            site_tab_handle = driver.current_window_handle

            save_site_screenshot(driver, site_name, "before")

            print("▶ Opening siteHeader dialog...")
            site_header = wait_for_clickable(driver, By.ID, "siteHeader", timeout=30)
            site_header.click()
            wait_for_clickable(driver, By.CSS_SELECTOR, ".ProseMirror", timeout=30)
            print("✓ siteHeader dialog opened")

            replace_logo_in_custom_text_dialog(driver, logo_data_url, clipboard_prepared)

            save_site_screenshot(driver, site_name, "after")
            save_clicked = apply_custom_text_changes(driver)

            if save_clicked:
                update_site_status(site_name, **{"LOGO Replaced": "Yes"})
                if close_tabs_after_site:
                    driver.close()
                    driver.switch_to.window(base_window)
                    print(f"✓ Step 2 site completed and tab closed: {site_name}")
                else:
                    print(f"✓ Step 2 site completed and tab kept open: {site_name}")
                    driver.switch_to.window(base_window)
            else:
                record_run_issue(site_name, "Step 2", "Logo Save did not complete automatically")
                print(
                    "⚠ Save did not complete automatically. "
                    f"Please save manually in the open tab for {site_name}."
                )
                if is_final_site:
                    prompt_input("▶ Press Enter after manual Save is completed...")
                else:
                    print("  Continuing without manual pause; site recorded as incomplete")
                if close_tabs_after_site:
                    driver.close()
                    driver.switch_to.window(base_window)
                    print(f"✓ Step 2 incomplete tab closed: {site_name}")
                else:
                    print(f"✓ Step 2 incomplete tab left open: {site_name}")
                    driver.switch_to.window(base_window)
        except Exception as exc:
            had_errors = True
            record_run_issue(site_name, "Step 2", exc)
            print(f"✗ Step 2 site failed for {site_name}: {exc}")
            print(f"  Context: {get_driver_error_context(driver)}")
            try:
                if site_tab_handle and site_tab_handle in driver.window_handles:
                    driver.switch_to.window(site_tab_handle)
                    if close_tabs_after_site:
                        driver.close()
            except Exception:
                pass

            try:
                if base_window in driver.window_handles:
                    driver.switch_to.window(base_window)
                elif ensure_site_window(driver, handles, "multipay", MULTIPAY_URL, allow_reopen=True):
                    base_window = handles.get("multipay", base_window)
            except Exception:
                pass

            print(f"  Continuing Step 2 with next site after error on {site_name}")

    if had_errors:
        print("✗ Step 2 completed with errors. Review ERROR log lines above.")
    else:
        print("✓ Step 2 completed for all sites")


def UpdateMultipayAdmin(driver, handles, site_list, logo_image_path=None):
    """Run MultiPay Admin tasks: import profile and upload logo."""
    print("\n▶ Running UpdateMultipayAdmin()...")
    import_profile_in_multipay(driver, handles, site_list, is_final_batch=True)
    upload_logo_in_multipay(driver, handles, logo_image_path, is_final_batch=True)
    print("✓ UpdateMultipayAdmin() completed")


def process_paydirect_admin_steps(driver, handles, site_list, update_css=False, enable_redirect=False, disable_swipe=False, append_css=False, reverse_css=False, reverse_swipe=False, disable_redirect=False, is_final_batch=False):
    """Run PayDirect Admin edit-page updates for each selected site."""
    if not update_css and not enable_redirect and not disable_swipe and not append_css and not reverse_css and not reverse_swipe and not disable_redirect:
        print("  No PayDirect Admin updates requested.")
        return

    if not ensure_site_window(driver, handles, "paydirect", PAYDIRECT_URL, allow_reopen=True):
        raise RuntimeError("PayDirect window is not available and could not be recovered.")

    print("▶ PayDirect site loop started")
    had_errors = False
    for index, site_name in enumerate(site_list, start=1):
        is_final_site = is_final_batch and index == len(site_list)
        try:
            print(f"▶ PayDirect processing site {index}/{len(site_list)}: {site_name}")
            open_paydirect_edit_page_for_site(driver, site_name)
            should_check_swipe_status = update_css or enable_redirect or disable_swipe
            initial_swipe_checked = None
            if update_css or enable_redirect or disable_swipe or append_css:
                if not ensure_paydirect_return_urls(driver, site_name):
                    record_run_issue(site_name, "PayDirect URL defaults", "Return/Cancel URL Save did not complete automatically")
            if should_check_swipe_status:
                initial_swipe_checked = get_paydirect_swipe_status(driver)
                print(
                    f"✓ Initial swipe support state for {site_name}: "
                    f"{'checked' if initial_swipe_checked else 'unchecked'}"
                )

            if update_css:
                open_paydirect_look_and_feel_tab(driver)
                set_paydirect_css_text(driver, PAYDIRECT_CSS_TEXT, site_name=site_name)
                if not click_paydirect_save_button(driver, site_name, "CSS update"):
                    record_run_issue(site_name, "Step 3", "CSS Save did not complete automatically")
                    if is_final_site:
                        prompt_input("▶ Press Enter after manual CSS Save is completed...")
                    else:
                        print("✗ CSS Save did not complete automatically; continuing without manual pause")

            if append_css:
                open_paydirect_look_and_feel_tab(driver)
                css_changed = append_paydirect_css_text(driver, PAYDIRECT_CSS_TEXT, site_name=site_name)
                if not css_changed:
                    print(f"✓ PayDirect CSS append skipped for {site_name}; standard CSS already present")
                elif not click_paydirect_save_button(driver, site_name, "CSS append"):
                    record_run_issue(site_name, "Step 6", "CSS append Save did not complete automatically")
                    if is_final_site:
                        prompt_input("▶ Press Enter after manual CSS append Save is completed...")
                    else:
                        print("✗ CSS append Save did not complete automatically; continuing without manual pause")

            if reverse_css:
                open_paydirect_look_and_feel_tab(driver)
                restore_paydirect_css_from_backup(driver, site_name)
                if not click_paydirect_save_button(driver, site_name, "CSS restore"):
                    record_run_issue(site_name, "Step 7", "CSS restore Save did not complete automatically")
                    if is_final_site:
                        prompt_input("▶ Press Enter after manual CSS restore Save is completed...")
                    else:
                        print("✗ CSS restore Save did not complete automatically; continuing without manual pause")

            if disable_swipe:
                open_paydirect_pos_tab(driver)
                current_swipe_checked = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "IsSwipeSupported"))
                ).is_selected()
                log_paydirect_swipe_status(site_name, current_swipe_checked)
                print(
                    f"✓ Swipe support current state for {site_name}: "
                    f"{'checked' if current_swipe_checked else 'unchecked'}"
                )
                set_checkbox_checked(driver, "IsSwipeSupported", checked=False)
                if not click_paydirect_save_button(driver, site_name, "swipe support update"):
                    record_run_issue(site_name, "Step 5", "Swipe Save did not complete automatically")
                    if is_final_site:
                        prompt_input("▶ Press Enter after manual Swipe Save is completed...")
                    else:
                        print("✗ Swipe Save did not complete automatically; continuing without manual pause")

            if reverse_swipe:
                open_paydirect_pos_tab(driver)
                previous_swipe_state = get_latest_paydirect_swipe_backup(site_name)
                set_checkbox_checked(driver, "IsSwipeSupported", checked=previous_swipe_state)
                if not click_paydirect_save_button(driver, site_name, "swipe support restore"):
                    record_run_issue(site_name, "Step 8", "Swipe restore Save did not complete automatically")
                    if is_final_site:
                        prompt_input("▶ Press Enter after manual Swipe restore Save is completed...")
                    else:
                        print("✗ Swipe restore Save did not complete automatically; continuing without manual pause")

            if enable_redirect:
                open_paydirect_site_settings_tab(driver)
                set_checkbox_checked(driver, "RedirectToMultipayWeb", checked=True)
                if not click_paydirect_save_button(driver, site_name, "redirect flag update"):
                    record_run_issue(site_name, "Step 4", "Redirect flag Save did not complete automatically")
                    if is_final_site:
                        prompt_input("▶ Press Enter after manual redirect flag Save is completed...")
                    else:
                        print("✗ Redirect flag Save did not complete automatically; continuing without manual pause")

            if disable_redirect:
                open_paydirect_site_settings_tab(driver)
                set_checkbox_checked(driver, "RedirectToMultipayWeb", checked=False)
                if not click_paydirect_save_button(driver, site_name, "redirect flag uncheck"):
                    record_run_issue(site_name, "Step 9", "Redirect flag uncheck Save did not complete automatically")
                    if is_final_site:
                        prompt_input("▶ Press Enter after manual redirect uncheck Save is completed...")
                    else:
                        print("✗ Redirect uncheck Save did not complete automatically; continuing without manual pause")

            if should_check_swipe_status and initial_swipe_checked is not None:
                final_swipe_checked = get_paydirect_swipe_status(driver)
                update_paydirect_swipe_status_result(site_name, initial_swipe_checked, final_swipe_checked)

            print(f"✓ PayDirect site completed: {site_name}")
        except Exception as exc:
            had_errors = True
            active_steps = []
            if update_css:
                active_steps.append("Step 3")
            if enable_redirect:
                active_steps.append("Step 4")
            if disable_swipe:
                active_steps.append("Step 5")
            if append_css:
                active_steps.append("Step 6")
            if reverse_css:
                active_steps.append("Step 7")
            if reverse_swipe:
                active_steps.append("Step 8")
            if disable_redirect:
                active_steps.append("Step 9")
            record_run_issue(site_name, "+".join(active_steps) or "PayDirect", exc)
            print(f"✗ PayDirect site failed for {site_name}: {exc}")
            print(f"  Context: {get_driver_error_context(driver)}")
            if is_final_site:
                prompt_input("▶ Press Enter to continue after the final PayDirect site failure...")
            else:
                print("  Continuing with the next PayDirect site without manual pause...")

    if had_errors:
        print("✗ PayDirect Admin updates completed with errors. Review ERROR log lines above.")
    else:
        print("✓ PayDirect Admin updates completed for all sites")


def update_css_in_paydirect(driver, handles, site_list, is_final_batch=False):
    """Step 3: update CSS in PayDirect Admin."""
    print("\n▶ Step 3: Update CSS in PayDirect Admin...")
    process_paydirect_admin_steps(driver, handles, site_list, update_css=True, enable_redirect=False, is_final_batch=is_final_batch)


def enable_redirect_flag_in_paydirect(driver, handles, site_list, is_final_batch=False):
    """Step 4: switch on redirect flag in PayDirect Admin."""
    print("\n▶ Step 4: Switch on redirect flag in PayDirect Admin...")
    process_paydirect_admin_steps(driver, handles, site_list, update_css=False, enable_redirect=True, is_final_batch=is_final_batch)


def unsupport_swipe_in_paydirect(driver, handles, site_list, is_final_batch=False):
    """Step 5: uncheck swipe support in PayDirect Admin."""
    print("\n▶ Step 5: Unsupport Swipe in PayDirect Admin...")
    process_paydirect_admin_steps(driver, handles, site_list, disable_swipe=True, is_final_batch=is_final_batch)


def append_css_in_paydirect(driver, handles, site_list, is_final_batch=False):
    """Step 6: append CSS in PayDirect Admin."""
    print("\n▶ Step 6: Append CSS in PayDirect Admin...")
    process_paydirect_admin_steps(driver, handles, site_list, append_css=True, is_final_batch=is_final_batch)


def reverse_css_in_paydirect(driver, handles, site_list, is_final_batch=False):
    """Step 7: restore CSS from the PayDirect CSS backup log."""
    print("\n▶ Step 7: Reverse CSS change in PayDirect Admin...")
    process_paydirect_admin_steps(driver, handles, site_list, reverse_css=True, is_final_batch=is_final_batch)


def reverse_swipe_in_paydirect(driver, handles, site_list, is_final_batch=False):
    """Step 8: restore Swipe checkbox state from the PayDirect swipe backup log."""
    print("\n▶ Step 8: Reverse Swipe checkbox in PayDirect Admin...")
    process_paydirect_admin_steps(driver, handles, site_list, reverse_swipe=True, is_final_batch=is_final_batch)


def uncheck_redirect_flag_in_paydirect(driver, handles, site_list, is_final_batch=False):
    """Step 9: uncheck redirect flag in PayDirect Admin."""
    print("\n▶ Step 9: Uncheck redirect flag in PayDirect Admin...")
    process_paydirect_admin_steps(driver, handles, site_list, disable_redirect=True, is_final_batch=is_final_batch)


def UpdatePayDirectAdmin(driver, handles, site_list):
    """Run PayDirect Admin tasks: update CSS and enable redirect flag."""
    print("\n▶ Running UpdatePayDirectAdmin()...")
    process_paydirect_admin_steps(driver, handles, site_list, update_css=True, enable_redirect=True, disable_swipe=True)
    print("✓ UpdatePayDirectAdmin() completed")


def execute_paydirect_step_on_current_site(driver, site_name, step, is_final_site=False):
    """Run one PayDirect step on the currently loaded edit page."""
    if step == "3":
        open_paydirect_look_and_feel_tab(driver)
        set_paydirect_css_text(driver, PAYDIRECT_CSS_TEXT, site_name=site_name)
        if not click_paydirect_save_button(driver, site_name, "CSS update"):
            record_run_issue(site_name, "Step 3", "CSS Save did not complete automatically")
            if is_final_site:
                prompt_input("▶ Press Enter after manual CSS Save is completed...")
            else:
                print("✗ CSS Save did not complete automatically; continuing without manual pause")
        else:
            update_site_status(site_name, **{"CSS saved": "Yes"})
    elif step == "4":
        open_paydirect_site_settings_tab(driver)
        set_checkbox_checked(driver, "RedirectToMultipayWeb", checked=True)
        if not click_paydirect_save_button(driver, site_name, "redirect flag update"):
            record_run_issue(site_name, "Step 4", "Redirect flag Save did not complete automatically")
            if is_final_site:
                prompt_input("▶ Press Enter after manual redirect flag Save is completed...")
            else:
                print("✗ Redirect flag Save did not complete automatically; continuing without manual pause")
        else:
            update_site_status(site_name, **{"Redirect done": "Yes"})
    elif step == "5":
        open_paydirect_pos_tab(driver)
        current_swipe_checked = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "IsSwipeSupported"))
        ).is_selected()
        log_paydirect_swipe_status(site_name, current_swipe_checked)
        print(
            f"✓ Swipe support current state for {site_name}: "
            f"{'checked' if current_swipe_checked else 'unchecked'}"
        )
        set_checkbox_checked(driver, "IsSwipeSupported", checked=False)
        if not click_paydirect_save_button(driver, site_name, "swipe support update"):
            record_run_issue(site_name, "Step 5", "Swipe Save did not complete automatically")
            if is_final_site:
                prompt_input("▶ Press Enter after manual Swipe Save is completed...")
            else:
                print("✗ Swipe Save did not complete automatically; continuing without manual pause")
    elif step == "6":
        open_paydirect_look_and_feel_tab(driver)
        css_changed = append_paydirect_css_text(driver, PAYDIRECT_CSS_TEXT, site_name=site_name)
        if not css_changed:
            print(f"✓ PayDirect CSS append skipped for {site_name}; standard CSS already present")
            update_site_status(site_name, **{"CSS saved": "Yes"})
        elif not click_paydirect_save_button(driver, site_name, "CSS append"):
            record_run_issue(site_name, "Step 6", "CSS append Save did not complete automatically")
            if is_final_site:
                prompt_input("▶ Press Enter after manual CSS append Save is completed...")
            else:
                print("✗ CSS append Save did not complete automatically; continuing without manual pause")
        else:
            update_site_status(site_name, **{"CSS saved": "Yes"})
    elif step == "7":
        open_paydirect_look_and_feel_tab(driver)
        restore_paydirect_css_from_backup(driver, site_name)
        if not click_paydirect_save_button(driver, site_name, "CSS restore"):
            record_run_issue(site_name, "Step 7", "CSS restore Save did not complete automatically")
            if is_final_site:
                prompt_input("▶ Press Enter after manual CSS restore Save is completed...")
            else:
                print("✗ CSS restore Save did not complete automatically; continuing without manual pause")
        else:
            update_site_status(site_name, **{"Undo CSS": "Yes"})
    elif step == "8":
        open_paydirect_pos_tab(driver)
        previous_swipe_state = get_latest_paydirect_swipe_backup(site_name)
        set_checkbox_checked(driver, "IsSwipeSupported", checked=previous_swipe_state)
        if not click_paydirect_save_button(driver, site_name, "swipe support restore"):
            record_run_issue(site_name, "Step 8", "Swipe restore Save did not complete automatically")
            if is_final_site:
                prompt_input("▶ Press Enter after manual Swipe restore Save is completed...")
            else:
                print("✗ Swipe restore Save did not complete automatically; continuing without manual pause")
        else:
            update_site_status(site_name, **{"Undo Swipe": "Yes"})
    elif step == "9":
        open_paydirect_site_settings_tab(driver)
        set_checkbox_checked(driver, "RedirectToMultipayWeb", checked=False)
        if not click_paydirect_save_button(driver, site_name, "redirect flag uncheck"):
            record_run_issue(site_name, "Step 9", "Redirect flag uncheck Save did not complete automatically")
            if is_final_site:
                prompt_input("▶ Press Enter after manual redirect uncheck Save is completed...")
            else:
                print("✗ Redirect uncheck Save did not complete automatically; continuing without manual pause")
        else:
            update_site_status(site_name, **{"Undo Redirect": "Yes"})
    else:
        raise ValueError(f"Unknown PayDirect step: {step}")


def execute_paydirect_steps_for_sites(driver, handles, site_list, paydirect_steps, is_final_batch=False):
    """Run selected PayDirect steps with one edit-page load per site."""
    if not paydirect_steps:
        return

    if not ensure_site_window(driver, handles, "paydirect", PAYDIRECT_URL, allow_reopen=True):
        raise RuntimeError("PayDirect window is not available and could not be recovered.")

    print(f"\n▶ Running PayDirect steps in one pass per site: {''.join(paydirect_steps)}")
    had_errors = False
    for index, site_name in enumerate(site_list, start=1):
        is_final_site = is_final_batch and index == len(site_list)
        try:
            print(f"▶ PayDirect processing site {index}/{len(site_list)}: {site_name}")
            open_paydirect_edit_page_for_site(driver, site_name)
            should_check_swipe_status = any(step in {"3", "4", "5"} for step in paydirect_steps)
            initial_swipe_checked = None
            if any(step in {"3", "4", "5", "6"} for step in paydirect_steps):
                if not ensure_paydirect_return_urls(driver, site_name):
                    record_run_issue(site_name, "PayDirect URL defaults", "Return/Cancel URL Save did not complete automatically")
            if should_check_swipe_status:
                initial_swipe_checked = get_paydirect_swipe_status(driver)
                print(
                    f"✓ Initial swipe support state for {site_name}: "
                    f"{'checked' if initial_swipe_checked else 'unchecked'}"
                )
            for step in paydirect_steps:
                execute_paydirect_step_on_current_site(driver, site_name, step, is_final_site=is_final_site)
            if should_check_swipe_status and initial_swipe_checked is not None:
                final_swipe_checked = get_paydirect_swipe_status(driver)
                update_paydirect_swipe_status_result(site_name, initial_swipe_checked, final_swipe_checked)
            print(f"✓ PayDirect site completed: {site_name}")
        except Exception as exc:
            had_errors = True
            record_run_issue(site_name, "+".join(f"Step {step}" for step in paydirect_steps), exc)
            print(f"✗ PayDirect site failed for {site_name}: {exc}")
            print(f"  Context: {get_driver_error_context(driver)}")
            if is_final_site:
                prompt_input("▶ Press Enter to continue after the final PayDirect site failure...")
            else:
                print("  Continuing with the next PayDirect site without manual pause...")

    if had_errors:
        print("✗ PayDirect Admin updates completed with errors. Review ERROR log lines above.")
    else:
        print("✓ PayDirect Admin updates completed for all sites")


def execute_single_step(driver, handles, site_list, step, logo_image_path=None, is_final_batch=False):
    """Run one selected workflow step."""
    if step == "1":
        import_profile_in_multipay(driver, handles, site_list, is_final_batch=is_final_batch)
    elif step == "2":
        upload_logo_in_multipay.site_list_context = site_list
        upload_logo_in_multipay(driver, handles, logo_image_path, is_final_batch=is_final_batch)
    elif step == "3":
        update_css_in_paydirect(driver, handles, site_list, is_final_batch=is_final_batch)
    elif step == "4":
        enable_redirect_flag_in_paydirect(driver, handles, site_list, is_final_batch=is_final_batch)
    elif step == "5":
        unsupport_swipe_in_paydirect(driver, handles, site_list, is_final_batch=is_final_batch)
    elif step == "6":
        append_css_in_paydirect(driver, handles, site_list, is_final_batch=is_final_batch)
    elif step == "7":
        reverse_css_in_paydirect(driver, handles, site_list, is_final_batch=is_final_batch)
    elif step == "8":
        reverse_swipe_in_paydirect(driver, handles, site_list, is_final_batch=is_final_batch)
    elif step == "9":
        uncheck_redirect_flag_in_paydirect(driver, handles, site_list, is_final_batch=is_final_batch)
    else:
        raise ValueError(f"Unknown step: {step}")


def execute_selected_steps(driver, handles, site_list, selected_steps, logo_image_path=None, is_final_batch=False):
    """Run selected steps in the exact requested order."""
    print(f"\n▶ Executing selected steps in requested order: {''.join(selected_steps)}")
    had_step_errors = False
    paydirect_steps = {"3", "4", "5", "6", "7", "8", "9"}
    step_index = 0

    while step_index < len(selected_steps):
        step = selected_steps[step_index]
        if step in paydirect_steps:
            grouped_steps = []
            while step_index < len(selected_steps) and selected_steps[step_index] in paydirect_steps:
                grouped_steps.append(selected_steps[step_index])
                step_index += 1
            try:
                execute_paydirect_steps_for_sites(
                    driver,
                    handles,
                    site_list,
                    grouped_steps,
                    is_final_batch=is_final_batch,
                )
            except Exception as exc:
                had_step_errors = True
                for site_name in site_list:
                    record_run_issue(site_name, "+".join(f"Step {item}" for item in grouped_steps), exc)
                print(f"✗ PayDirect steps {''.join(grouped_steps)} failed: {exc}")
                print(f"  Context: {get_driver_error_context(driver)}")
                if is_final_batch:
                    prompt_input("▶ Press Enter to continue after the final batch PayDirect failure...")
                else:
                    print("  Continuing to the next selected step without manual pause...")
            continue

        try:
            execute_single_step(driver, handles, site_list, step, logo_image_path, is_final_batch=is_final_batch)
        except Exception as exc:
            had_step_errors = True
            for site_name in site_list:
                record_run_issue(site_name, f"Step {step}", exc)
            print(f"✗ Step {step} failed: {exc}")
            print(f"  Context: {get_driver_error_context(driver)}")
            if is_final_batch:
                prompt_input("▶ Press Enter to continue after the final batch step failure...")
            else:
                print("  Continuing to the next selected step without manual pause...")
        step_index += 1

    if had_step_errors:
        print("✗ Selected steps completed with errors. Review ERROR log lines above.")
    else:
        print("✓ Selected steps completed")


def get_site_batches(site_list, batch_size=BATCH_SIZE):
    """Split site names into batches for long runs."""
    if not site_list:
        return []
    return [site_list[index:index + batch_size] for index in range(0, len(site_list), batch_size)]


def execute_selected_steps_in_batches(driver, handles, site_list, selected_steps, logo_image_path=None):
    """Run selected steps across the full site list in fixed-size batches."""
    site_batches = get_site_batches(site_list)
    total_batches = len(site_batches)
    print(
        f"\n▶ Batch processing enabled: {len(site_list)} site(s), "
        f"batch size={BATCH_SIZE}, total batches={total_batches}"
    )

    for batch_index, site_batch in enumerate(site_batches, start=1):
        is_final_batch = batch_index == total_batches
        print("\n" + "=" * 60)
        print(
            f"▶ Starting batch {batch_index}/{total_batches}: "
            f"{len(site_batch)} site(s)"
        )
        print(f"  Batch sites: {get_site_preview(site_batch)}")
        print("=" * 60)
        execute_selected_steps(
            driver,
            handles,
            site_batch,
            selected_steps,
            logo_image_path,
            is_final_batch=is_final_batch,
        )
        write_status_csv(reason=f"updated after batch {batch_index}/{total_batches}")


def selected_steps_require_multipay(selected_steps):
    """Return whether the selected steps require MultiPay Admin."""
    return any(step in {"1", "2"} for step in selected_steps)


def selected_steps_require_paydirect(selected_steps):
    """Return whether the selected steps require PayDirect Admin."""
    return any(step in {"3", "4", "5", "6", "7", "8", "9"} for step in selected_steps)


def prepare_required_sites_for_steps(driver, handles, selected_steps):
    """Open and authenticate any site required by a follow-up step batch."""
    multipay_required = selected_steps_require_multipay(selected_steps)
    paydirect_required = selected_steps_require_paydirect(selected_steps)

    if multipay_required and "multipay" not in handles:
        ensure_site_window(driver, handles, "multipay", MULTIPAY_URL, allow_reopen=True)
    if paydirect_required and "paydirect" not in handles:
        ensure_site_window(driver, handles, "paydirect", PAYDIRECT_URL, allow_reopen=True)

    load_site_cookies(driver, handles)
    wait_for_manual_authentication(
        driver,
        handles,
        require_multipay=multipay_required,
        require_paydirect=paydirect_required,
    )


def save_session_context(browser_type, profile_dir):
    """Save browser context metadata for follow-up executions."""
    context = {
        "browser_type": browser_type,
        "profile_dir": profile_dir,
        "multipay_url": MULTIPAY_URL,
        "paydirect_url": PAYDIRECT_URL,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    SESSION_CONTEXT_PATH.write_text(json.dumps(context, indent=2), encoding="utf-8")
    print(f"✓ Session context saved: {SESSION_CONTEXT_PATH}")


def load_session_context():
    """Load saved browser context metadata if available."""
    if not SESSION_CONTEXT_PATH.exists():
        return None
    try:
        return json.loads(SESSION_CONTEXT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"✗ Failed to read session context file: {exc}")
        return None


def main():
    driver = None
    try:
        print("\n╔" + "=" * 58 + "╗")
        print("║" + " " * 58 + "║")
        print("║" + "  PayDirect Admin -> MultiPay Admin Automation".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("╚" + "=" * 58 + "╝")

        browser_choice = get_browser_choice()
        profile_dir = get_persistent_profile_dir(browser_choice)
        selected_steps = get_selected_steps()
        multipay_required = selected_steps_require_multipay(selected_steps)
        paydirect_required = selected_steps_require_paydirect(selected_steps)
        Site_list = ""
        site_list = get_site_list(Site_list)
        initialize_status_rows(site_list)
        write_status_csv(reason="created")
        print(f"✓ Loaded {len(site_list)} site(s): {get_site_preview(site_list)}")

        driver = initialize_driver(browser_choice, profile_dir=profile_dir)
        if not driver:
            print("✗ Failed to initialize WebDriver. Exiting...")
            return

        handles = open_required_sites(
            driver,
            open_multipay=multipay_required,
            open_paydirect=paydirect_required,
        )
        load_site_cookies(driver, handles)
        wait_for_manual_authentication(
            driver,
            handles,
            require_multipay=multipay_required,
            require_paydirect=paydirect_required,
        )
        save_site_cookies(driver, handles)
        save_session_context(browser_choice, profile_dir)

        logo_image_path = None
        if "2" in selected_steps:
            logo_image_path = str(Path(__file__).with_name("LogoImage.png"))
            print(f"✓ Step 2 will use fixed logo path: {logo_image_path}")

        while selected_steps:
            execute_selected_steps_in_batches(driver, handles, site_list, selected_steps, logo_image_path)
            selected_steps = get_followup_steps()
            if selected_steps:
                prepare_required_sites_for_steps(driver, handles, selected_steps)

        display_run_issues()
        write_status_csv(reason="finalized")
        print("\n✓ Workflow completed.")

    except Exception as exc:
        print(f"✗ Fatal error: {exc}")
        display_run_issues()
        write_status_csv(reason="updated after fatal error")
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
