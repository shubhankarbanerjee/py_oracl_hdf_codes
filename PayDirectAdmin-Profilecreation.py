import json
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


CREATE_MERCHANT_URL = "http://p5zlgintc01:16020/PayDirect/Merchant/Create"
TEMPLATE_DIRECTORY = Path(r"C:\Users\SBanerjee\Downloads\PD Templates")
PARKS_AND_RECREATION_TEMPLATE = TEMPLATE_DIRECTORY / "EDM_ParksNRec_Templ.xml"
STANDARD_TEMPLATE = TEMPLATE_DIRECTORY / "EdmondsPDATermplate020823.xml"
UPLOAD_INPUT_ID = "uploadedImportFile"
UPLOAD_BUTTON_ID = "importFileUploadButton"
TRUSTED_DOMAINS = "wipp.edmundsassoc.com\nwipp.edmundsgovtech.cloud"
MERCHANT_CODE_PASSWORD = "3dMunD5"
REQUIRED_PROFILE_FIELDS = (
    "UniqueSiteName",
    "SiteNameGiven",
    "State",
    "L2GMerchantCode",
    "UniqueID",
)
VALID_STATE_CODES = {
    "AL", "AK", "AS", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "GU", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "PR", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VI", "VA", "WA", "WV", "WI", "WY",
}


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


def collect_profile_input(allow_blank_exit=False):
    print("\nPaste the profile details below.")
    print("Press Enter on two consecutive blank lines when finished.\n")
    if allow_blank_exit:
        print("Press Enter on the first line to finish and close the browser.\n")

    lines = []
    blank_line_count = 0
    while True:
        line = input()
        if not line.strip():
            if not lines:
                if allow_blank_exit:
                    return None
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
    missing_fields = [
        field_name
        for field_name in REQUIRED_PROFILE_FIELDS
        if not fields.get(field_name, "").strip()
    ]
    if missing_fields:
        raise ValueError(
            "Required input value(s) missing: " + ", ".join(missing_fields)
        )

    state_code = fields["State"].strip().upper()
    if state_code not in VALID_STATE_CODES:
        raise ValueError(
            f"State must be a valid two-letter code. Received: {fields['State']!r}"
        )
    fields["State"] = state_code

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


def open_create_page(driver):
    try:
        driver.get(CREATE_MERCHANT_URL)
    except TimeoutException:
        print("Create Merchant page load timed out; checking whether the form is usable...")


def get_browser_context(driver):
    try:
        current_url = driver.current_url
    except Exception:
        current_url = "(unavailable)"
    try:
        page_title = driver.title
    except Exception:
        page_title = "(unavailable)"
    return f"URL={current_url}, title={page_title!r}"


def activate_profile_tab(driver, tab_id, visible_element_id):
    wait = WebDriverWait(driver, 15)
    tab_link = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f"#tabs > ul a[href='#{tab_id}']")
        )
    )
    driver.execute_script("arguments[0].click();", tab_link)
    return wait.until(
        EC.visibility_of_element_located((By.ID, visible_element_id))
    )


def wait_for_create_form_after_login(driver):
    open_create_page(driver)
    while True:
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, UPLOAD_INPUT_ID))
            )
            return activate_profile_tab(driver, "advanced", UPLOAD_INPUT_ID)
        except TimeoutException:
            print(
                "Create Merchant import form is not ready. "
                + get_browser_context(driver)
            )
            input(
                "Complete the PayDirect login in the browser, then press Enter "
                "to check for the Create Merchant form..."
            )
            open_create_page(driver)


def upload_template(driver, template_path):
    if not template_path.is_file():
        raise FileNotFoundError(f"XML template was not found: {template_path}")

    file_input = wait_for_create_form_after_login(driver)
    file_input.send_keys(str(template_path.resolve()))

    upload_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, UPLOAD_BUTTON_ID))
    )
    upload_button.click()
    WebDriverWait(driver, 30).until(EC.staleness_of(file_input))
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "MerchantName"))
    )


def replace_element_value(element, value):
    element.clear()
    element.send_keys(value)


def set_checkbox_state(driver, checkbox, checked):
    if checkbox.is_selected() != checked:
        driver.execute_script("arguments[0].click();", checkbox)


def populate_imported_profile(driver, fields):
    wait = WebDriverWait(driver, 30)
    merchant_name = activate_profile_tab(driver, "basics", "MerchantName")
    merchant_site_name = wait.until(
        EC.visibility_of_element_located((By.ID, "MerchantSiteName"))
    )
    trusted_domains = wait.until(
        EC.visibility_of_element_located((By.ID, "TrustedDomains"))
    )
    default_state = wait.until(
        EC.presence_of_element_located((By.ID, "DefaultState"))
    )

    replace_element_value(merchant_name, fields["UniqueSiteName"])
    replace_element_value(merchant_site_name, fields["SiteNameGiven"])
    replace_element_value(trusted_domains, TRUSTED_DOMAINS)
    Select(default_state).select_by_value(fields["State"])

    merchant_code = activate_profile_tab(driver, "transaction", "MerchantCode")
    merchant_code_password = wait.until(
        EC.visibility_of_element_located((By.ID, "MerchantCodePassword"))
    )
    settle_code = wait.until(
        EC.visibility_of_element_located((By.ID, "SettleCode"))
    )
    replace_element_value(merchant_code, fields["L2GMerchantCode"])
    replace_element_value(merchant_code_password, MERCHANT_CODE_PASSWORD)
    replace_element_value(settle_code, fields["UniqueID"])

    swipe_supported = activate_profile_tab(driver, "pos", "IsSwipeSupported")
    should_support_swipe = fields["UniqueSiteName"].strip().casefold().endswith(" vt")
    set_checkbox_state(driver, swipe_supported, should_support_swipe)

    populated_values = {
        "MerchantName": merchant_name.get_attribute("value"),
        "MerchantSiteName": merchant_site_name.get_attribute("value"),
        "TrustedDomains": trusted_domains.get_attribute("value"),
        "DefaultState": Select(default_state).first_selected_option.get_attribute("value"),
        "MerchantCode": merchant_code.get_attribute("value"),
        "MerchantCodePassword": merchant_code_password.get_attribute("value"),
        "SettleCode": settle_code.get_attribute("value"),
        "IsSwipeSupported": swipe_supported.is_selected(),
    }
    expected_values = {
        "MerchantName": fields["UniqueSiteName"],
        "MerchantSiteName": fields["SiteNameGiven"],
        "TrustedDomains": TRUSTED_DOMAINS,
        "DefaultState": fields["State"],
        "MerchantCode": fields["L2GMerchantCode"],
        "MerchantCodePassword": MERCHANT_CODE_PASSWORD,
        "SettleCode": fields["UniqueID"],
        "IsSwipeSupported": should_support_swipe,
    }
    incorrect_fields = [
        field_name
        for field_name, expected_value in expected_values.items()
        if populated_values[field_name] != expected_value
    ]
    if incorrect_fields:
        raise RuntimeError(
            "Imported form value verification failed for: "
            + ", ".join(incorrect_fields)
        )
    activate_profile_tab(driver, "basics", "MerchantName")


def display_input_summary(fields, other_lines, template_path):
    print("\nValidated profile input:")
    for key, value in fields.items():
        print(f"  {key}={value}")
    for line in other_lines:
        print(f"  {line}")
    print(f"\nSelected XML template: {template_path}")


def prepare_profile_input(lines):
    fields, other_lines = parse_profile_lines(lines)
    fields = resolve_open_items(fields)
    validate_profile_fields(fields)

    template_path = select_template(fields["UniqueSiteName"])
    if not template_path.is_file():
        raise FileNotFoundError(f"XML template was not found: {template_path}")
    display_input_summary(fields, other_lines, template_path)
    return fields, template_path


def collect_prepared_profile(allow_blank_exit=False):
    while True:
        lines = collect_profile_input(allow_blank_exit=allow_blank_exit)
        if lines is None:
            return None
        try:
            return prepare_profile_input(lines)
        except (FileNotFoundError, ValueError) as exc:
            print(f"\nError: {exc}")
            print("Please enter the profile again.")


def process_profile(driver, fields, template_path):
    upload_template(driver, template_path)
    populate_imported_profile(driver, fields)
    print("\nXML uploaded and required merchant fields populated successfully.")
    input(
        "Save and test the site in the browser. "
        "Press Enter here only after both are complete..."
    )


def main():
    driver = None
    try:
        fields, template_path = collect_prepared_profile()

        browser_type = get_browser_choice()
        print(f"\nOpening PayDirect Create Merchant page in {browser_type.title()}...")
        driver = initialize_driver(browser_type)
        while True:
            process_profile(driver, fields, template_path)

            next_profile = collect_prepared_profile(allow_blank_exit=True)
            if next_profile is None:
                print("\nNo additional profile entered. Closing the browser.")
                break
            fields, template_path = next_profile
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"\nError: {exc}")
    except Exception as exc:
        print(f"\nUnexpected error ({type(exc).__name__}): {exc!r}")
        if driver:
            print("Browser context: " + get_browser_context(driver))
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()