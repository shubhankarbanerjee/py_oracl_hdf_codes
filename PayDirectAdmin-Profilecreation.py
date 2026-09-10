import json
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


CREATE_MERCHANT_URL = "http://p5zlgintc01:16020/PayDirect/Merchant/Create"
TEMPLATE_DIRECTORY = Path(r"C:\Users\SBanerjee\Downloads\PD Templates")
PARKS_AND_RECREATION_TEMPLATE = TEMPLATE_DIRECTORY / "EDM_ParksNRec_Templ.xml"
STANDARD_TEMPLATE = TEMPLATE_DIRECTORY / "EdmondsPDATermplate020823.xml"
UPLOAD_INPUT_ID = "uploadedImportFile"
UPLOAD_BUTTON_ID = "importFileUploadButton"


def prompt_yes_no(prompt, default=False):
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = input(prompt + suffix).strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer y or n.")


def collect_profile_input():
    print("\nPaste the profile details below.")
    print("Press Enter on two consecutive blank lines when finished.\n")

    lines = []
    blank_line_count = 0
    while True:
        line = input()
        if not line.strip():
            if not lines:
                print("At least one input line is required.")
                continue
            blank_line_count += 1
            if blank_line_count == 2:
                return lines
            continue

        blank_line_count = 0
        lines.append(line)


def parse_profile_lines(lines):
    fields = {}
    other_lines = []

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
        if "=" not in stripped_line:
            other_lines.append(stripped_line)
            continue

        key, value = stripped_line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid input line with no field name: {line!r}")
        if key in fields:
            raise ValueError(f"Duplicate field in input: {key}")
        fields[key] = value.strip()

    if not fields:
        raise ValueError("No key=value fields were found in the input.")
    return fields, other_lines


def resolve_open_items(fields):
    resolved_fields = dict(fields)
    for key in list(resolved_fields):
        while not resolved_fields[key].strip():
            print(f"\nOpen item found: {key}=")
            value = input(f"Enter a value for {key}, or press Enter to remove it: ").strip()
            if value:
                resolved_fields[key] = value
                break
            if prompt_yes_no(f"Remove {key} from this profile?"):
                del resolved_fields[key]
                break
            print(f"{key} still needs a value.")
    return resolved_fields


def validate_profile_fields(fields):
    unique_site_name = fields.get("UniqueSiteName", "").strip()
    if not unique_site_name:
        raise ValueError("UniqueSiteName is required to select an XML template.")

    payment_method = fields.get("PaymentMethod")
    if payment_method:
        try:
            parsed_payment_method = json.loads(payment_method)
        except json.JSONDecodeError as exc:
            raise ValueError(f"PaymentMethod is not valid JSON: {exc}") from exc
        if not isinstance(parsed_payment_method, dict):
            raise ValueError("PaymentMethod must be a JSON object.")


def select_template(unique_site_name):
    normalized_name = unique_site_name.strip().casefold()
    if normalized_name.endswith("parknrec web"):
        return PARKS_AND_RECREATION_TEMPLATE
    if normalized_name.endswith(("web", "vt")):
        return STANDARD_TEMPLATE
    raise ValueError(
        "UniqueSiteName must end with 'ParkNRec Web', 'Web', or 'VT' "
        f"to select an XML template. Received: {unique_site_name!r}"
    )


def get_browser_choice():
    print("\nSelect browser:")
    print("1. Chrome (default)")
    print("2. Microsoft Edge")
    return "edge" if input("Choice [1]: ").strip() == "2" else "chrome"


def get_persistent_profile_dir(browser_type):
    profile_dir = Path(__file__).with_name(".paydir_browser_profile") / browser_type
    profile_dir.mkdir(parents=True, exist_ok=True)
    return str(profile_dir.resolve())


def initialize_driver(browser_type):
    profile_dir = get_persistent_profile_dir(browser_type)
    if browser_type == "edge":
        options = webdriver.EdgeOptions()
        options.add_argument(f"--user-data-dir={profile_dir}")
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    else:
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile_dir}")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

    driver.maximize_window()
    return driver


def wait_for_create_form_after_login(driver):
    driver.get(CREATE_MERCHANT_URL)
    while True:
        try:
            return WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, UPLOAD_INPUT_ID))
            )
        except TimeoutException:
            input(
                "Complete the PayDirect login in the browser, then press Enter "
                "to check for the Create Merchant form..."
            )
            driver.get(CREATE_MERCHANT_URL)


def upload_template(driver, template_path):
    if not template_path.is_file():
        raise FileNotFoundError(f"XML template was not found: {template_path}")

    file_input = wait_for_create_form_after_login(driver)
    file_input.send_keys(str(template_path.resolve()))

    upload_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, UPLOAD_BUTTON_ID))
    )
    upload_button.click()
    WebDriverWait(driver, 30).until(
        lambda current_driver: current_driver.execute_script("return document.readyState")
        == "complete"
    )


def display_input_summary(fields, other_lines, template_path):
    print("\nValidated profile input:")
    for key, value in fields.items():
        print(f"  {key}={value}")
    for line in other_lines:
        print(f"  {line}")
    print(f"\nSelected XML template: {template_path}")


def main():
    driver = None
    try:
        lines = collect_profile_input()
        fields, other_lines = parse_profile_lines(lines)
        fields = resolve_open_items(fields)
        validate_profile_fields(fields)

        template_path = select_template(fields["UniqueSiteName"])
        if not template_path.is_file():
            raise FileNotFoundError(f"XML template was not found: {template_path}")
        display_input_summary(fields, other_lines, template_path)

        browser_type = get_browser_choice()
        print(f"\nOpening PayDirect Create Merchant page in {browser_type.title()}...")
        driver = initialize_driver(browser_type)
        upload_template(driver, template_path)
        print("\nXML uploaded. The imported merchant settings should now be populated.")
        input("Review the form in the browser, then press Enter to close it...")
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"\nError: {exc}")
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()