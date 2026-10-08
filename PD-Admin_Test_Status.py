import base64
import builtins
import csv
from datetime import datetime
import html
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

SCRIPT_NAME = "PD-Admin_Test_Status"
BASE_DIR = Path(__file__).resolve().parent
PAYDIRECT_URL = "http://p5zlgintc01:16020/PayDirect/"
MULTIPAY_WEB_URL = "https://app.multipayweb.cus.prod.comm.fisfedcloud.com/"
MULTIPAY_FORM_TIMEOUT_MS = 20_000
PAYDIRECT_STYLE_URLS = [
    "http://p5zlgintc01:16020/PayDirect/Content/jquery-ui/jquery-ui.min.css",
    "http://p5zlgintc01:16020/PayDirect/Content/jquery-ui/smoothness/jquery.ui.theme.css",
    "http://p5zlgintc01:16020/PayDirect/Content/style.1.1.css",
]
RUN_STAMP = datetime.now().strftime("%d%m%Y_%H%M%S")
LOG_FILE_PATH = BASE_DIR / f"{SCRIPT_NAME}.log"
STORAGE_STATE_PATH = BASE_DIR / f"{SCRIPT_NAME}.storage.json"
HTML_REPORT_PATH = BASE_DIR / f"{SCRIPT_NAME}.HTML"
CSV_PATH = BASE_DIR / f"{SCRIPT_NAME}_{RUN_STAMP}.csv"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
VIDEOS_DIR = BASE_DIR / "videos" / SCRIPT_NAME

CACHE_MIN_SITES = 30
SAVE_EVERY_SITES = 10
TARGET_ENVIRONMENT = "PROD"
NAV_TIMEOUT_MS = 60_000
REDIRECT_TIMEOUT_S = 60
SETTLE_STABLE_S = 3
VIDEO_SIZE = (1280, 720)
VIDEO_FPS = 25
BROWSER_PROFILE_ROOT = BASE_DIR / ".pdadmin_browser_profile"
BROWSER_EXECUTABLES = {
    "chrome": [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ],
    "edge": [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    ],
}
# PayDirect uses Windows (NTLM/Negotiate) auth; allow the current Windows identity for this host.
BROWSER_ARGS = [
    "--auth-server-allowlist=p5zlgintc01,*.p5zlgintc01",
    "--auth-negotiate-delegate-allowlist=p5zlgintc01,*.p5zlgintc01",
]

CSV_COLUMNS = [
    "Name",
    "Merchant Code",
    "Merchant Site Name",
    "Type",
    "Status",
    "Test URL",
    "PROD URL",
    "Result",
    "Screenshot",
    "Multipay?",
    "Multipay URL",
    "MP Screenshot",
    "Tested At",
]

HTML_DATA_RE = re.compile(
    r'<script type="application/json" id="pd-test-data">(.*?)</script>', re.S
)

# Reads every row of the Profiles table in one round-trip; optional term filters by exact match.
PROFILE_ROWS_JS = """
(term) => {
    const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
    const wanted = term ? norm(term) : null;
    const rows = [];
    document.querySelectorAll('#Profiles tr').forEach((tr) => {
        const cells = tr.querySelectorAll('td');
        if (cells.length < 5) return;
        const text = (i) => (cells[i] ? cells[i].innerText : '').replace(/\\s+/g, ' ').trim();
        const editLink = cells[0].querySelector('a[href]');
        const testLink = tr.querySelector('a[id^="lnkTestMerchant"]')
            || (cells[5] ? cells[5].querySelector('a[href]') : null);
        const row = {
            name: text(0),
            merchant_code: text(1),
            site_name: text(2),
            type: text(3),
            status: text(4),
            edit_url: editLink ? editLink.href : '',
            test_url: testLink ? testLink.href : '',
        };
        if (wanted !== null
            && norm(row.name) !== wanted
            && norm(row.merchant_code) !== wanted
            && norm(row.site_name) !== wanted) {
            return;
        }
        rows.push(row);
    });
    return rows;
}
"""

LOG_BUFFER = []
PROFILE_CACHE = []
RESULTS = []


# ---------------------------------------------------------------------------
# Logging (same format as PayDirAdminMig2Mulpay.py, newest entries on top)
# ---------------------------------------------------------------------------
def get_log_status(message):
    """Infer a log status from the console message prefix/content."""
    stripped_message = message.strip()
    if not stripped_message:
        return None
    if stripped_message.startswith("✗") or "fatal error" in stripped_message.lower():
        return "ERROR"
    if stripped_message.startswith("⚠"):
        return "WARN"
    if stripped_message.startswith("▶"):
        return "STARTED"
    if stripped_message.startswith("✓"):
        return "DONE"
    return "INFO"


def print(*args, sep=" ", end="\n", file=None, flush=False):
    """Mirror console output to the log buffer using the requested format."""
    message = sep.join(str(arg) for arg in args)
    timestamp = datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
    for line in message.splitlines():
        line = line.strip()
        status = get_log_status(line)
        if status:
            LOG_BUFFER.append(f"{timestamp} - {status} - {line}")
    builtins.print(*args, sep=sep, end=end, file=file, flush=flush)


def flush_log():
    """Prepend buffered log entries (newest first) to the log file."""
    if not LOG_BUFFER:
        return
    existing_content = ""
    if LOG_FILE_PATH.exists():
        existing_content = LOG_FILE_PATH.read_text(encoding="utf-8")
    new_content = "\n".join(reversed(LOG_BUFFER))
    if existing_content:
        new_content = new_content + "\n" + existing_content
    LOG_FILE_PATH.write_text(new_content, encoding="utf-8")
    LOG_BUFFER.clear()


def prompt_input(prompt):
    """Display and log an input prompt before reading user input."""
    print(prompt, end="")
    flush_log()
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


# ---------------------------------------------------------------------------
# User input
# ---------------------------------------------------------------------------
def get_browser_choice():
    """Ask user which browser to use and return the selected browser type."""
    print("\n" + "=" * 60)
    print("Select browser:")
    print("=" * 60)
    print("1. Chrome (default)")
    print("2. Microsoft Edge")
    print("=" * 60)
    choice = prompt_input("▶ Enter choice (1 or 2, default is 1): ").strip()
    return "edge" if choice == "2" else "chrome"


def get_site_entries():
    """Collect site entries (one per line). Returns None when ALL sites are requested."""
    print("\n" + "=" * 60)
    print("SITE LIST INPUT")
    print("=" * 60)
    print("Enter one site per line using any of:")
    print("  - Full Name          e.g. 35EDM Hopatcong Borough Various Animal")
    print("  - Merchant Code      e.g. 35EDM-HOPAU-VARAN-W")
    print("  - Merchant Site Name e.g. PPNJ1912 (may match several rows)")
    print("Enter * or ALL to test every site listed in PayDirect Admin.")
    print("Press Enter twice when done.")
    print("=" * 60)

    lines = []
    blank_line_count = 0
    while True:
        line = input().strip()
        if not line:
            if not lines:
                print("✗ At least one site entry is required.")
                continue
            blank_line_count += 1
            if blank_line_count >= 2:
                break
            continue

        blank_line_count = 0
        if line == "*" or line.upper() == "ALL":
            print("✓ ALL sites requested")
            return None
        lines.append(line)

    print(f"✓ {len(lines)} site entr{'y' if len(lines) == 1 else 'ies'} received:")
    for line in lines:
        print(f"  - {line}")
    return lines


# ---------------------------------------------------------------------------
# Browser / session
# ---------------------------------------------------------------------------
def find_browser_executable(browser_choice):
    for candidate in BROWSER_EXECUTABLES[browser_choice]:
        path = Path(os.path.expandvars(candidate))
        if path.is_file():
            return path
    raise RuntimeError(f"{browser_choice} executable not found in the standard install locations")


def get_free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def launch_browser(playwright, browser_choice):
    """Start a normal Chrome/Edge window (native login prompts work) and attach Playwright to it."""
    executable = find_browser_executable(browser_choice)
    profile_dir = BROWSER_PROFILE_ROOT / browser_choice
    profile_dir.mkdir(parents=True, exist_ok=True)
    port = get_free_port()
    print(f"\n▶ Launching {executable.name} with dedicated profile: {profile_dir}")
    process = subprocess.Popen(
        [
            str(executable),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
            *BROWSER_ARGS,
            PAYDIRECT_URL,
        ]
    )

    endpoint = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 30
    while True:
        try:
            browser = playwright.chromium.connect_over_cdp(endpoint)
            break
        except PlaywrightError:
            if time.monotonic() > deadline:
                process.terminate()
                raise RuntimeError(
                    f"Could not attach to {executable.name}. Close any browser window already using {profile_dir} and retry."
                )
            time.sleep(0.5)
    print(f"✓ Browser launched and attached ({endpoint})")
    return browser, process


def get_session(browser):
    """Return the browser's default context and its PayDirect tab, restoring saved cookies."""
    context = browser.contexts[0]
    context.set_default_timeout(NAV_TIMEOUT_MS)
    if STORAGE_STATE_PATH.exists():
        try:
            cookies = json.loads(STORAGE_STATE_PATH.read_text(encoding="utf-8")).get("cookies", [])
            if cookies:
                context.add_cookies(cookies)
                print(f"✓ Session cookies loaded from {STORAGE_STATE_PATH.name}: {len(cookies)}")
        except Exception as exc:
            print(f"⚠ Saved cookies could not be loaded ({exc})")
    else:
        print("  No saved cookie file found.")

    page = context.pages[0] if context.pages else context.new_page()
    for extra_page in context.pages[1:]:
        extra_page.close()
    page.bring_to_front()
    return context, page


def close_browser(browser, process):
    """Close the launched browser cleanly so the profile is flushed to disk."""
    try:
        browser.new_browser_cdp_session().send("Browser.close")
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.terminate()


def find_ffmpeg():
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    matches = sorted(root.glob("ffmpeg-*/ffmpeg-win64.exe"))
    return matches[-1] if matches else None


class ScreencastRecorder:
    """Records one page to WebM by piping CDP screencast JPEG frames into Playwright's ffmpeg."""

    def __init__(self, page, output_path, ffmpeg_path):
        self.page = page
        self.output_path = output_path
        self.ffmpeg_path = ffmpeg_path
        self.session = None
        self.process = None
        self.last_frame = None
        self.last_time = None

    def start(self):
        width, height = VIDEO_SIZE
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen(
            [
                str(self.ffmpeg_path), "-loglevel", "error",
                "-f", "image2pipe", "-avioflags", "direct", "-fpsprobesize", "0",
                "-probesize", "32", "-analyzeduration", "0", "-c:v", "mjpeg", "-i", "pipe:0",
                "-y", "-an", "-r", str(VIDEO_FPS), "-c:v", "vp8", "-qmin", "0", "-qmax", "50",
                "-crf", "8", "-deadline", "realtime", "-speed", "8", "-b:v", "1M", "-threads", "1",
                "-vf", f"pad={width}:{height}:0:0:gray,crop={width}:{height}:0:0",
                str(self.output_path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.session = self.page.context.new_cdp_session(self.page)
        self.session.on("Page.screencastFrame", self._on_frame)
        self.session.send(
            "Page.startScreencast",
            {"format": "jpeg", "quality": 80, "maxWidth": width, "maxHeight": height, "everyNthFrame": 1},
        )
        print(f"✓ Video recording started: {self.output_path}")

    def _write_previous_frame(self, now):
        # Screencast only emits on change, so hold the previous frame for the elapsed time.
        if self.last_frame is None:
            return
        repeats = max(1, round((now - self.last_time) * VIDEO_FPS))
        for _ in range(repeats):
            self.process.stdin.write(self.last_frame)

    def _on_frame(self, params):
        try:
            self.session.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            now = time.monotonic()
            self._write_previous_frame(now)
            self.last_frame = base64.b64decode(params["data"])
            self.last_time = now
        except Exception:
            pass

    def stop(self):
        try:
            self.session.send("Page.stopScreencast")
        except Exception:
            pass
        try:
            self._write_previous_frame(time.monotonic())
            self.process.stdin.close()
            self.process.wait(timeout=60)
            print(f"✓ Video saved: {self.output_path}")
        except Exception as exc:
            print(f"⚠ Could not finalize video: {exc}")


def start_video_recording(page):
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("⚠ Video recording unavailable (run: python -m playwright install ffmpeg); continuing without video")
        return None
    recorder = ScreencastRecorder(page, VIDEOS_DIR / f"{SCRIPT_NAME}_{RUN_STAMP}.webm", ffmpeg_path)
    try:
        recorder.start()
        return recorder
    except Exception as exc:
        print(f"⚠ Could not start video recording: {exc}")
        return None


def save_storage_state(context):
    """Persist cookies and local storage to JSON for the next execution."""
    try:
        context.storage_state(path=str(STORAGE_STATE_PATH))
        print(f"✓ Session cookies/storage saved: {STORAGE_STATE_PATH}")
    except Exception as exc:
        print(f"✗ Failed to save session cookies/storage: {exc}")


def is_profiles_visible(page, timeout_ms=20_000):
    try:
        page.wait_for_selector("#Profiles", state="visible", timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


def open_profiles_page(page):
    """Navigate to PayDirect Admin and report whether the Profiles table is visible."""
    try:
        page.goto(PAYDIRECT_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    except PlaywrightError as exc:
        print(f"⚠ PayDirect navigation issue: {exc}".splitlines()[0])
    return is_profiles_visible(page)


def wait_for_login(page, context):
    """Wait for the user to log in manually until the Profiles table shows."""
    print(f"\n▶ Checking PayDirect Admin login: {PAYDIRECT_URL}")
    # Chrome was opened on PayDirect already; don't navigate away from a pending login prompt.
    if not page.url.lower().startswith(PAYDIRECT_URL.lower()):
        open_profiles_page(page)
    if is_profiles_visible(page):
        print("✓ PayDirect profile list visible (login already active)")
    else:
        print("\n" + "=" * 60)
        print("MANUAL AUTHENTICATION REQUIRED")
        print("=" * 60)
        print("1. Log in to PayDirect Admin in the opened browser window")
        print("2. Return here and press Enter to continue")
        print("=" * 60)
        while True:
            prompt_input("\n▶ Press Enter after PayDirect authentication is completed...")
            if is_profiles_visible(page, timeout_ms=3_000) or open_profiles_page(page):
                print("✓ PayDirect login confirmed")
                break
            print("✗ PayDirect login not ready: Profiles table did not open/show.")
            print("  Please complete the login, then press Enter again.")
    save_storage_state(context)


# ---------------------------------------------------------------------------
# Profile lookup
# ---------------------------------------------------------------------------
def get_row_key(row):
    """Return a stable unique key for a profile row (PayDirect merchant id)."""
    match = re.search(r"/(?:Edit|Test)/(\d+)", row.get("edit_url") or row.get("test_url") or "")
    if match:
        return match.group(1)
    return f"{row.get('merchant_code', '')}|{row.get('site_name', '')}|{row.get('name', '')}"


def normalize(value):
    return re.sub(r"\s+", " ", value or "").strip().lower()


def load_profile_cache(page):
    """Read the full Profiles table into memory."""
    print("▶ Loading PayDirect profile table into cache...")
    if not page.locator("#Profiles").is_visible():
        open_profiles_page(page)
    PROFILE_CACHE.clear()
    PROFILE_CACHE.extend(page.evaluate(PROFILE_ROWS_JS, None))
    print(f"✓ PayDirect profile cache loaded: {len(PROFILE_CACHE)} row(s)")


def find_profile_rows(page, term, use_cache):
    """Return rows whose Name, Merchant Code or Merchant Site Name exactly matches term."""
    if use_cache:
        wanted = normalize(term)
        return [
            row for row in PROFILE_CACHE
            if wanted in (normalize(row["name"]), normalize(row["merchant_code"]), normalize(row["site_name"]))
        ]
    if not page.locator("#Profiles").is_visible():
        open_profiles_page(page)
    return page.evaluate(PROFILE_ROWS_JS, term)


def resolve_rows_to_test(page, entries):
    """Resolve user entries (or ALL) to a de-duplicated list of profile rows."""
    if entries is None:
        load_profile_cache(page)
        print(f"✓ ALL mode: {len(PROFILE_CACHE)} site(s) will be tested")
        return list(PROFILE_CACHE)

    use_cache = len(entries) > CACHE_MIN_SITES
    if use_cache:
        load_profile_cache(page)
    else:
        print(f"  {len(entries)} entr(ies) <= {CACHE_MIN_SITES}; searching the live table per entry")

    selected = {}
    unmatched = []
    for entry in entries:
        print(f"▶ Searching PayDirect profile list for: {entry}")
        matches = find_profile_rows(page, entry, use_cache)
        if not matches and re.search(r"[\s,]", entry):
            # Line may hold several codes/site names separated by spaces or commas.
            for token in [t for t in re.split(r"[\s,]+", entry) if t]:
                token_matches = find_profile_rows(page, token, use_cache)
                if token_matches:
                    matches.extend(token_matches)
                else:
                    unmatched.append(token)
        elif not matches:
            unmatched.append(entry)

        print(f"  {len(matches)} match(es) for: {entry}")
        for row in matches:
            print(f"  ✓ {row['name']} | {row['merchant_code']} | {row['site_name']} | {row['type']} | {row['status']}")
            selected.setdefault(get_row_key(row), row)

    for entry in unmatched:
        print(f"✗ No PayDirect profile found for: {entry}")
        RESULTS.append(build_result(
            {"name": entry, "merchant_code": "", "site_name": "", "type": "", "status": "", "test_url": ""},
            result="Not found in PayDirect profile list",
        ))

    print(f"✓ {len(selected)} unique site(s) resolved for testing")
    return list(selected.values())


# ---------------------------------------------------------------------------
# Test execution
# ---------------------------------------------------------------------------
def build_result(row, prod_url="", result="", screenshot=""):
    return {
        "key": get_row_key(row),
        "Name": row.get("name", ""),
        "Merchant Code": row.get("merchant_code", ""),
        "Merchant Site Name": row.get("site_name", ""),
        "Type": row.get("type", ""),
        "Status": row.get("status", ""),
        "Edit URL": row.get("edit_url", ""),
        "Test URL": row.get("test_url", ""),
        "PROD URL": prod_url,
        "Result": result,
        "Screenshot": screenshot,
        "Multipay?": "",
        "Multipay URL": "",
        "MP Screenshot": "",
        "Tested At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def safe_file_part(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("_")[:60] or "site"


def take_screenshot(target_page, row, phase):
    """Save a full-page screenshot and return its file name."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
    file_name = (
        f"{safe_file_part(row.get('site_name'))}_"
        f"{safe_file_part(row.get('merchant_code'))}_{timestamp}"
        f"{'' if phase == TARGET_ENVIRONMENT else '_' + phase}.png"
    )
    path = SCREENSHOTS_DIR / file_name
    target_page.screenshot(path=str(path), full_page=True)
    print(f"✓ Screenshot saved: {path}")
    return file_name


def wait_for_redirect(context, page, pages_before, url_before, navigations):
    """Wait for the submit to navigate the page or open a new tab; return the target page."""
    deadline = time.monotonic() + REDIRECT_TIMEOUT_S
    while time.monotonic() < deadline:
        new_pages = [p for p in context.pages if p not in pages_before]
        if new_pages:
            return new_pages[-1], True
        if navigations or page.url != url_before:
            return page, True
        page.wait_for_timeout(250)
    return page, False


def wait_for_page_settle(target_page):
    """Wait until the page is loaded and its URL stops changing (handles redirect chains)."""
    deadline = time.monotonic() + REDIRECT_TIMEOUT_S
    last_url = target_page.url
    stable_since = time.monotonic()
    while time.monotonic() < deadline:
        try:
            target_page.wait_for_load_state("load", timeout=5_000)
        except PlaywrightTimeoutError:
            pass
        target_page.wait_for_timeout(500)
        if target_page.url != last_url:
            print(f"  Redirected to: {target_page.url}")
            last_url = target_page.url
            stable_since = time.monotonic()
        elif time.monotonic() - stable_since >= SETTLE_STABLE_S:
            break
    try:
        target_page.wait_for_load_state("networkidle", timeout=10_000)
    except PlaywrightTimeoutError:
        print("  Network did not go idle within 10s; continuing")


def test_site(context, page, row):
    """Open the site's Test page, post to PROD and capture the resulting page."""
    test_url = row.get("test_url")
    if not test_url:
        raise RuntimeError("Test link not found in the PayDirect row")

    print(f"▶ Opening Test page: {test_url}")
    page.goto(test_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)

    env_select = page.locator("#SelectedPostEnvironment")
    env_select.wait_for(state="visible", timeout=30_000)
    env_select.select_option(label=TARGET_ENVIRONMENT)
    print(f"✓ SelectedPostEnvironment set to {env_select.input_value()}")

    # The page holds a hidden Submit (other POST type) before the visible one.
    submit_button = page.locator("input.testPageButton[type='submit']:visible").first
    submit_button.wait_for(state="visible", timeout=30_000)

    pages_before = list(context.pages)
    url_before = page.url
    navigations = []

    def on_frame_navigated(frame):
        if frame == page.main_frame:
            navigations.append(frame.url)

    page.on("framenavigated", on_frame_navigated)
    try:
        print("▶ Clicking first 'Submit Form' button...")
        submit_button.click(no_wait_after=True)
        target_page, redirected = wait_for_redirect(context, page, pages_before, url_before, navigations)
    finally:
        page.remove_listener("framenavigated", on_frame_navigated)

    if target_page is not page:
        print("  Submit opened a new tab; following it")
    wait_for_page_settle(target_page)

    prod_url = target_page.url
    screenshot = take_screenshot(target_page, row, TARGET_ENVIRONMENT)
    if target_page is not page:
        target_page.close()

    if redirected:
        print(f"✓ PROD page reached: {prod_url}")
        return build_result(row, prod_url=prod_url, result="Success", screenshot=screenshot)

    print(f"✗ No redirect detected within {REDIRECT_TIMEOUT_S}s; current URL: {prod_url}")
    return build_result(row, prod_url=prod_url, result="No redirect detected", screenshot=screenshot)


def check_multipay_web(page, row):
    """Open the MultiPay Web page for the site; OK when the checkout form renders."""
    site_name = (row.get("site_name") or "").strip()
    if not site_name:
        return "NO", "", ""
    url = MULTIPAY_WEB_URL + site_name
    print(f"▶ Checking MultiPay Web page: {url}")
    status = "NO"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        page.locator("form #checkoutContainer").first.wait_for(state="visible", timeout=MULTIPAY_FORM_TIMEOUT_MS)
        status = "OK"
    except PlaywrightError as exc:
        print(f"  MultiPay checkout form not found: {exc}".splitlines()[0])
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except PlaywrightTimeoutError:
        pass

    screenshot = ""
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        screenshot = f"MP_{safe_file_part(site_name)}_{datetime.now().strftime('%d%m%Y %H%M%S')}.png"
        page.screenshot(path=str(SCREENSHOTS_DIR / screenshot), full_page=True)
        print(f"✓ Screenshot saved: {SCREENSHOTS_DIR / screenshot}")
    except Exception as exc:
        print(f"⚠ MultiPay screenshot failed: {exc}")
        screenshot = ""

    if status == "OK":
        print(f"✓ MultiPay Web OK for {site_name}")
    else:
        print(f"✗ MultiPay Web NO for {site_name}")
    return status, url, screenshot


def test_sites(context, page, rows):
    """Test every resolved row, saving reports periodically."""
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        print("\n" + "-" * 60)
        print(f"▶ Testing site {index}/{total}: {row['name']} | {row['merchant_code']} | {row['site_name']}")
        try:
            result = test_site(context, page, row)
        except Exception as exc:
            print(f"✗ Test failed for {row['name']}: {exc}")
            screenshot = ""
            try:
                screenshot = take_screenshot(page, row, "ERROR")
            except Exception:
                pass
            current_url = ""
            try:
                current_url = page.url
            except Exception:
                pass
            result = build_result(row, prod_url=current_url, result=f"Error: {exc}".splitlines()[0], screenshot=screenshot)

        try:
            mp_status, mp_url, mp_screenshot = check_multipay_web(page, row)
        except Exception as exc:
            print(f"✗ MultiPay Web check failed for {row['name']}: {exc}")
            mp_status, mp_url, mp_screenshot = "NO", "", ""
        result.update({"Multipay?": mp_status, "Multipay URL": mp_url, "MP Screenshot": mp_screenshot})
        RESULTS.append(result)

        if index % SAVE_EVERY_SITES == 0:
            write_reports(reason=f"updated after {index}/{total} site(s)")
        flush_log()


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def write_status_csv():
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(RESULTS)
    return CSV_PATH


def load_html_records():
    """Load previously reported rows from the data block embedded in the HTML report."""
    if not HTML_REPORT_PATH.exists():
        return {}
    match = HTML_DATA_RE.search(HTML_REPORT_PATH.read_text(encoding="utf-8"))
    if not match:
        print(f"⚠ Existing {HTML_REPORT_PATH.name} has no data block; it will be recreated")
        return {}
    try:
        return {record["key"]: record for record in json.loads(match.group(1))}
    except (ValueError, KeyError, TypeError) as exc:
        print(f"⚠ Could not read existing HTML data ({exc}); it will be recreated")
        return {}


def render_url_cell(url, error_text=""):
    if error_text and not url:
        return f'<td class="error">{html.escape(error_text)}</td>'
    if not url:
        return "<td></td>"
    display = re.sub(r"^https?://", "", url)
    css_class = "url error" if error_text else "url"
    title = f"{url}\n{error_text}" if error_text else url
    return (
        f'<td class="{css_class}"><a href="{html.escape(url)}" target="_blank" '
        f'title="{html.escape(title)}">{html.escape(display)}</a></td>'
    )


def render_multipay_cell(status, url):
    if not status:
        return "<td></td>"
    css_class = "mp-ok" if status == "OK" else "mp-no"
    label = html.escape(status)
    if url:
        label = f'<a href="{html.escape(url)}" target="_blank" title="{html.escape(url)}">{label}</a>'
    return f'<td class="{css_class}">{label}</td>'


def sort_key(record):
    return (
        (record.get("PROD URL") or "").lower(),
        (record.get("Merchant Site Name") or "").lower(),
        record.get("key", ""),
    )


def write_html_report(records):
    rows_html = []
    for index, record in enumerate(sorted(records.values(), key=sort_key)):
        row_class = ' class="oddRow"' if index % 2 == 0 else ""
        result = record.get("Result", "")
        error_text = "" if result == "Success" else result
        name_html = html.escape(record.get("Name", ""))
        name_title = name_html
        if record.get("Edit URL"):
            name_html = f'<a href="{html.escape(record["Edit URL"])}" target="_blank">{name_html}</a>'
        rows_html.append(
            f"        <tr{row_class}>\n"
            f'            <td class="name" title="{name_title}">{name_html}</td>\n'
            f'            <td class="nowrap">{html.escape(record.get("Merchant Code", ""))}</td>\n'
            f'            <td>{html.escape(record.get("Merchant Site Name", ""))}</td>\n'
            f'            <td>{html.escape(record.get("Type", ""))}</td>\n'
            f'            <td>{html.escape(record.get("Status", ""))}</td>\n'
            f"            {render_url_cell(record.get('Test URL', ''))}\n"
            f"            {render_url_cell(record.get('PROD URL', ''), error_text)}\n"
            f"            {render_multipay_cell(record.get('Multipay?', ''), record.get('Multipay URL', ''))}\n"
            f'            <td class="nowrap">{html.escape(record.get("Last Updated", ""))}</td>\n'
            f"        </tr>"
        )

    total = len(records)
    success = sum(1 for record in records.values() if record.get("Result") == "Success")
    style_links = "\n".join(
        f'    <link rel="stylesheet" href="{url}" type="text/css">' for url in PAYDIRECT_STYLE_URLS
    )
    data_json = json.dumps(sorted(records.values(), key=sort_key), indent=0).replace("</", "<\\/")

    content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"><head>
    <meta charset="utf-8">
    <title>PayDirect Admin - Test Status</title>
{style_links}
    <style>
        body {{ font-family: Arial, Helvetica, sans-serif; font-size: 12px; margin: 0; }}
        .header {{ background: #2a62b1; color: #fff; padding: 8px 0; }}
        .header h1, .header h1 a {{ color: #fff; margin: 0; text-decoration: none; }}
        .header h2 {{ color: #dfe8f5; font-size: 12px; margin: 2px 0 0; }}
        .container {{ padding: 0 16px; }}
        .navbar {{ display: inline-block; margin-top: 6px; }}
        table.edit_table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
        table.edit_table th {{ background: #e6e6e6; text-align: left; padding: 4px 6px; border: 1px solid #ccc; }}
        table.edit_table td {{ padding: 3px 6px; border: 1px solid #e0e0e0; vertical-align: top; }}
        tr.oddRow {{ background: #f2f6fb; }}
        td.nowrap {{ white-space: nowrap; }}
        td.url {{ max-width: 15ch; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        td.name {{ max-width: 30ch; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        td.error, td.error a {{ color: #c00; }}
        td.mp-ok, td.mp-ok a {{ color: #1a7f37; font-weight: bold; }}
        td.mp-no, td.mp-no a {{ color: #c00; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <div class="title"><h1>PayDirect Admin</h1></div>
            <div class="navbar">
                <div class="menuOption">
                    <h1><a href="{PAYDIRECT_URL}" target="_blank">All Merchants</a></h1>
                    <h2>Test Status - POST to {TARGET_ENVIRONMENT}</h2>
                </div>
            </div>
        </div>
    </div>
    <div class="container">
<table id="Profiles" class="edit_table">
    <tbody><tr>
        <th>Name</th>
        <th>Merchant Code</th>
        <th>Merchant Site Name</th>
        <th>Type</th>
        <th>Status</th>
        <th>Test URL</th>
        <th>PROD URL</th>
        <th>Multipay?</th>
        <th>Last Updated</th>
    </tr>
{chr(10).join(rows_html)}
</tbody></table>
<p>{total} profiles tested ({success} reached {TARGET_ENVIRONMENT})</p>
<p>Report updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
<script type="application/json" id="pd-test-data">{data_json}</script>
</body></html>
"""
    HTML_REPORT_PATH.write_text(content, encoding="utf-8")
    return HTML_REPORT_PATH


def write_reports(reason="update"):
    """Write the per-run CSV and merge this run's results into the persistent HTML report."""
    if not RESULTS:
        print("  No results to write yet.")
        return
    try:
        csv_path = write_status_csv()
        print(f"✓ Status CSV {reason}: {csv_path}")
    except Exception as exc:
        print(f"✗ Failed to write status CSV: {exc}")

    try:
        records = load_html_records()
        for result in RESULTS:
            if not result["Test URL"] and not result["Merchant Code"]:
                continue
            record = {key: value for key, value in result.items() if key not in {"Screenshot", "MP Screenshot", "Tested At"}}
            record["Last Updated"] = result["Tested At"]
            records[result["key"]] = record
        html_path = write_html_report(records)
        print(f"✓ HTML report {reason}: {html_path}")
    except Exception as exc:
        print(f"✗ Failed to write HTML report: {exc}")


def display_summary():
    failures = [result for result in RESULTS if result["Result"] != "Success"]
    print("\n" + "=" * 60)
    print(f"RUN SUMMARY: {len(RESULTS) - len(failures)} success, {len(failures)} incomplete/error")
    print("=" * 60)
    for index, result in enumerate(failures, start=1):
        print(f"{index}. ✗ {result['Name']} | {result['Merchant Code']} | {result['Result']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + "  PayDirect Admin -> Test Page PROD Submit Status".center(58) + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        browser_choice = get_browser_choice()
        record_video = prompt_yes_no("▶ Record a video of this run?", default=True)
        entries = get_site_entries()
    except (KeyboardInterrupt, EOFError):
        print("✗ Input cancelled. Exiting.")
        flush_log()
        return

    with sync_playwright() as playwright:
        try:
            browser, browser_process = launch_browser(playwright, browser_choice)
        except Exception as exc:
            print(f"✗ Fatal error: {exc}")
            flush_log()
            return
        context, page = get_session(browser)
        recorder = start_video_recording(page) if record_video else None

        try:
            wait_for_login(page, context)
            rows = resolve_rows_to_test(page, entries)
            flush_log()
            if rows:
                test_sites(context, page, rows)
            else:
                print("✗ No sites resolved for testing.")
            display_summary()
            print("\n✓ Workflow completed.")
        except KeyboardInterrupt:
            print("✗ Run interrupted by user.")
        except Exception as exc:
            print(f"✗ Fatal error: {exc}")
        finally:
            write_reports(reason="finalized")
            save_storage_state(context)
            if recorder:
                recorder.stop()
            close_browser(browser, browser_process)
            flush_log()


if __name__ == "__main__":
    main()
