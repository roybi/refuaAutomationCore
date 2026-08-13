#!/usr/bin/env python3
"""
Capture authenticated browser sessions for reuse in automated tests.

The user enters their username manually in the browser; the script waits for
the Microsoft 2FA number-matching page to appear, displays the number, and
polls until the user approves it in the Authenticator app. Once past login,
the session state (cookies/tokens) is saved to disk so test runs don't need
to repeat the interactive login + 2FA flow every time.

Sessions are stored in ~/.refua_sessions/ (or SESSION_DIR) with a 3-day TTL.
One file is created per app+environment+browser combination:
  auth_state_{app}_{env}_{browser}_latest.json

Every browser context is launched in private/incognito mode, and defaults to
emulating an iPhone 14 Pro Max unless a different --device is specified.

Usage:
    python scripts/capture_session.py --env test
    python scripts/capture_session.py --env test --app cpr-go
    python scripts/capture_session.py --env test --browser firefox
    python scripts/capture_session.py --env test --device desktop
    python scripts/capture_session.py --env test --session-dir /sessions
"""

import argparse
import logging
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Force UTF-8 output on Windows — must happen before any print() or logging
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from colorama import Fore, init
from playwright.sync_api import sync_playwright

from refua_core.config.environment import (
    _APP_REGISTRY,
    EnvironmentManager,
    InvalidEnvironmentError,
    UnknownAppError,
)
from refua_core.config.session_manager import SessionStateManager

init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("auth_capture.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

SUPPORTED_BROWSERS = ["chromium", "firefox"]

DEFAULT_DEVICE = "iphone_14_pro_max"

# Maps CLI device names to Playwright built-in descriptor names.
# Playwright's p.devices[name] provides viewport, UA, scale factor, isMobile, hasTouch.
_DEVICE_MAP = {
    "desktop": None,
    "iphone_14_pro_max": "iPhone 14 Pro Max",
    "iphone": "iPhone 14 Pro",
    "iphone_14_pro": "iPhone 14 Pro",
    "iphone_14": "iPhone 14",
    "iphone_13": "iPhone 13",
    "iphone_12": "iPhone 12",
    "android": "Pixel 7",
    "android_pixel": "Pixel 7",
    "android_galaxy": "Galaxy S9+",
}


def _setup_env_manager(
    env: str, app: str = "meditek", session_dir: str = None
) -> EnvironmentManager:
    os.environ["TEST_ENV"] = env
    os.environ["TEST_APP"] = app
    if session_dir:
        os.environ["SESSION_DIR"] = str(Path(session_dir).expanduser().resolve())
    EnvironmentManager.reset_instance()
    return EnvironmentManager()


def _browsers_to_capture(browser_arg: str) -> list[str]:
    return SUPPORTED_BROWSERS if browser_arg == "all" else [browser_arg]


def _log_auth_request(request):
    if any(
        p in request.url.lower()
        for p in ["login", "auth", "token", "microsoft", "oauth", "msal"]
    ):
        logger.debug("→ Auth Request: %s %s", request.method, request.url)


def _log_auth_response(response):
    if any(
        p in response.url.lower()
        for p in ["login", "auth", "token", "microsoft", "oauth", "msal"]
    ):
        logger.debug("← Auth Response: %s %s", response.status, response.url)
        if response.status >= 400:
            logger.warning("Auth Error: %s at %s", response.status, response.url)


# ── 2FA detection / waiting helpers ──────────────────────────────────────────


def _extract_2fa_number(page) -> str | None:
    """Try to read the number shown on the Microsoft 2FA number-matching page.

    Returns the number string if found, or None if the page layout is unexpected.
    """
    for sel in [
        "#idRichContext_DisplaySign",
        '[data-bind*="displaySign"]',
        ".displaySign",
        "#displaySign",
        '[aria-label*="number"]',
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                text = el.text_content(timeout=2000).strip()
                if text:
                    return text
        except Exception:
            continue
    return None


def _handle_stay_signed_in(page, timeout: int = 20000) -> bool:
    """Auto-click 'No' on Microsoft 'Stay signed in?' (KMSI) page.

    Returns True if the page was found and dismissed, False if it never appeared.
    """
    try:
        no_btn = page.locator("#idBtn_Back").first
        no_btn.wait_for(state="visible", timeout=timeout)
        logger.info("'Stay signed in?' page detected — clicking No")
        no_btn.click(timeout=5000)
        print(f"{Fore.GREEN}✅  'Stay signed in?' — clicked No automatically\n")
        return True
    except Exception:
        logger.debug("'Stay signed in?' page not detected")
        return False


def _wait_for_2fa_page(page, base_url: str, timeout_seconds: int = 300) -> bool:
    """Poll until the Microsoft 2FA number-matching element appears.

    Returns True if the 2FA page was detected, False if login completed
    without a 2FA prompt (browser already back in the app, or on the
    'Stay signed in?' page).
    Raises TimeoutError if neither happens within timeout_seconds.
    """
    import time
    from urllib.parse import urlparse

    app_host = urlparse(base_url).netloc

    _2fa_selectors = [
        "#idRichContext_DisplaySign",
        '[data-bind*="displaySign"]',
        ".displaySign",
        "#displaySign",
        '[aria-label*="number"]',
        # Fallback: any input[name="otc"] (OTP code entry box) means we're past the 2FA prompt
        'input[name="otc"]',
    ]
    deadline = time.monotonic() + timeout_seconds
    dots = 0
    while time.monotonic() < deadline:
        for sel in _2fa_selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=1000):
                    print(f"\n{Fore.GREEN}✅  2FA page detected\n")
                    return True
            except Exception:
                pass

        # Microsoft may skip the 2FA prompt entirely (cached device trust,
        # conditional access, ...). If the browser is already back in the app
        # past the login page, treat login as complete.
        parsed = urlparse(page.url)
        if parsed.netloc == app_host and parsed.path not in ("", "/", "/home"):
            print(
                f"\n{Fore.GREEN}✅  Logged in without a 2FA prompt — browser is back in the app\n"
            )
            logger.info("Login completed without 2FA prompt: %s", page.url)
            return False
        try:
            # KMSI 'No' button — only present on the 'Stay signed in?' page
            if page.locator("#idBtn_Back").first.is_visible(timeout=500):
                print(
                    f"\n{Fore.GREEN}✅  Logged in without a 2FA prompt — 'Stay signed in?' page shown\n"
                )
                logger.info("Login completed without 2FA prompt (KMSI page)")
                return False
        except Exception:
            pass

        dots = (dots + 1) % 4
        print(
            f"\r{Fore.CYAN}  Waiting for 2FA page{'.' * dots + ' ' * (3 - dots)}",
            end="",
            flush=True,
        )
        time.sleep(1)
    print()
    raise TimeoutError(
        f"2FA page not detected within {timeout_seconds}s — "
        "check the browser window and ensure credentials were entered correctly."
    )


def _wait_for_post_2fa(page, base_url: str, timeout_seconds: int = 180) -> None:
    """Poll until the browser leaves the Microsoft login domain (2FA approved).

    Checks for the KMSI page, app URL, or any non-Microsoft URL.
    """
    import time

    # Selectors / URL patterns that indicate 2FA is done
    _post_2fa_selectors = [
        "#idBtn_Back",  # 'Stay signed in?' No button (KMSI page)
        "#idSIButton9",  # 'Stay signed in?' Yes button
    ]
    deadline = time.monotonic() + timeout_seconds
    dots = 0
    while time.monotonic() < deadline:
        current_url = page.url
        # Redirected back to the app or KMSI interstitial
        if (
            "microsoftonline.com" not in current_url
            and "login.microsoft" not in current_url
        ):
            print(f"\n{Fore.GREEN}✅  2FA approved — browser left Microsoft login\n")
            return
        for sel in _post_2fa_selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=1000):
                    print(f"\n{Fore.GREEN}✅  2FA approved — KMSI page detected\n")
                    return
            except Exception:
                pass
        dots = (dots + 1) % 4
        print(
            f"\r{Fore.CYAN}  Waiting for 2FA approval{'.' * dots + ' ' * (3 - dots)}",
            end="",
            flush=True,
        )
        time.sleep(1)
    print()
    raise TimeoutError(
        f"2FA approval not detected within {timeout_seconds}s — "
        "did you approve in the Authenticator app?"
    )


def _wait_for_app_redirect(page, base_url: str, timeout_seconds: int = 30) -> None:
    """Wait until the page URL is on the app domain (not Microsoft login)."""
    import time
    from urllib.parse import urlparse

    app_host = urlparse(base_url).netloc
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass
        current_host = urlparse(page.url).netloc
        if app_host and app_host in current_host:
            logger.info("App URL reached: %s", page.url)
            print(f"{Fore.GREEN}✅  Redirected back to app ({current_host})\n")
            return
        if "microsoftonline.com" not in page.url and "login.microsoft" not in page.url:
            logger.info("Left Microsoft domain — URL: %s", page.url)
            print(f"{Fore.GREEN}✅  Left Microsoft login domain\n")
            return
        time.sleep(1)
    # Timeout: log warning and continue — better to capture whatever state we have
    logger.warning(
        "App redirect not confirmed within %ds (still at %s) — capturing anyway",
        timeout_seconds,
        page.url,
    )


# ── Main capture ─────────────────────────────────────────────────────────────


def capture_session_for_browser(
    env: str,
    browser: str,
    app: str = "meditek",
    device: str = DEFAULT_DEVICE,
    session_dir: str = None,
) -> str:
    """Launch an interactive browser, guide through login + 2FA, then save session.

    Returns the path to the saved session file.
    """
    os.environ["BROWSER"] = browser
    env_mgr = _setup_env_manager(env, app, session_dir)
    base_url = env_mgr.get_base_url()
    env_mgr.get_session_dir().mkdir(parents=True, exist_ok=True)

    display_device = _DEVICE_MAP.get(device.lower(), device) or "Desktop"
    print(f"\n{Fore.CYAN}{'=' * 70}")
    print(
        f"{Fore.CYAN}BROWSER: {browser.upper()} | APP: {app} | ENV: {env.upper()} | DEVICE: {display_device}"
    )
    print(f"{Fore.CYAN}{'=' * 70}\n")

    with sync_playwright() as p:
        browser_launcher = getattr(p, browser, None)
        if browser_launcher is None:
            raise ValueError(f"Browser '{browser}' not supported by Playwright")

        # Every context below is a fresh, non-persistent Playwright context,
        # which is isolated by default. These launch args are an extra,
        # explicit guarantee of private/incognito mode.
        _incognito_args = {
            "chromium": ["--no-sandbox", "--disable-dev-shm-usage", "--incognito"],
            "firefox": ["-private"],
        }
        browser_instance = browser_launcher.launch(
            headless=False,
            args=_incognito_args.get(browser, []),
        )

        playwright_device_name = _DEVICE_MAP.get(
            device.lower() if device else DEFAULT_DEVICE
        )
        device_kwargs = (
            dict(p.devices[playwright_device_name]) if playwright_device_name else {}
        )
        if playwright_device_name:
            logger.info("Device emulation: %s", playwright_device_name)

        context = browser_instance.new_context(
            **device_kwargs,
            locale="he-IL",
            timezone_id="Asia/Jerusalem",
        )
        context.on("request", _log_auth_request)
        context.on("response", _log_auth_response)
        page = context.new_page()

        try:
            # ── 1. Load app ───────────────────────────────────────────────────
            print(
                f"{Fore.YELLOW}⏳  Opening {base_url} — may take a moment on slow network..."
            )
            logger.info("Navigating to %s", base_url)
            page.goto(base_url, wait_until="domcontentloaded", timeout=240000)

            # 50% zoom for better visibility on high-resolution screens
            page.evaluate("document.body.style.zoom = '0.5'")

            # ── 2. Connection page (optional interstitial) ─────────────────────
            try:
                page.wait_for_selector("#connection-page-title", timeout=10000)
                logger.info("Connection page detected — clicking login")
                print(f"{Fore.GREEN}✅  Connection page loaded\n")
                page.locator("#login-button").click(timeout=10000)
            except Exception:
                logger.info("No connection page — proceeding directly to login")

            # ── 3. Wait for app login page ────────────────────────────────────
            try:
                page.wait_for_selector("#login-page-title", timeout=60000)
                print(f"{Fore.GREEN}✅  Login page is ready\n")
                logger.info("Login page confirmed (#login-page-title)")
            except Exception:
                print(
                    f"{Fore.YELLOW}⚠   Could not confirm login page — check the browser\n"
                )
                logger.warning("Could not find #login-page-title — proceeding anyway")

            # ── 4. Credentials — entered manually by the user ────────────────
            print(f"{Fore.YELLOW}{'=' * 70}")
            print(f"{Fore.YELLOW}STEP 1 of 2 — Log in with your credentials")
            print(f"{Fore.YELLOW}{'=' * 70}")
            print(f"{Fore.WHITE}In the browser, do all of these:")
            print(f"{Fore.GREEN}  1.  Click the login button")
            print(f"{Fore.GREEN}  2.  Enter your username  →  click Next")
            print(f"{Fore.GREEN}  3.  Enter your password  →  click Sign in")
            print(
                f"{Fore.GREEN}  4.  Wait until a large number appears on screen (2FA step)"
            )
            print(
                f"\n{Fore.CYAN}  ⏳  Waiting automatically for the 2FA number to appear..."
            )
            two_fa_shown = _wait_for_2fa_page(page, base_url, timeout_seconds=300)

            # ── 5. 2FA — display number and wait for approval ─────────────────
            if two_fa_shown:
                two_fa_number = _extract_2fa_number(page)

                print(f"\n{Fore.YELLOW}{'=' * 70}")
                print(
                    f"{Fore.YELLOW}STEP 2 of 2 — Approve Microsoft 2FA in Authenticator"
                )
                print(f"{Fore.YELLOW}{'=' * 70}")

                if two_fa_number:
                    print(
                        f"\n{Fore.WHITE}Number shown on screen (enter this in Authenticator):"
                    )
                    print(f"\n        {Fore.GREEN}{two_fa_number}        \n")
                else:
                    print(
                        f"\n{Fore.WHITE}A number is shown in the browser — enter it in Authenticator.\n"
                    )

                print(f"{Fore.GREEN}  → Open Microsoft Authenticator on your phone")
                print(f"{Fore.GREEN}  → Enter / tap the number when prompted")
                print(f"{Fore.GREEN}  → Confirm / Approve")
                print(
                    f"\n{Fore.YELLOW}⚠   Do NOT close the browser — the script handles everything after this"
                )
                print(f"\n{Fore.CYAN}  ⏳  Waiting automatically for 2FA approval...")
            else:
                print(
                    f"{Fore.CYAN}  2FA prompt was skipped by Microsoft — continuing to save the session\n"
                )
            _wait_for_post_2fa(page, base_url, timeout_seconds=180)

            # ── 6. Auto-handle 'Stay signed in?' ──────────────────────────────
            print(f"\n{Fore.YELLOW}⏳  Handling post-login pages...")
            _handle_stay_signed_in(page, timeout=20000)

            # Wait for full navigation back to the app (leave Microsoft domain).
            # The sso_reload redirect on this environment can be slow.
            _wait_for_app_redirect(page, base_url, timeout_seconds=240)

            # Reaching the app's domain still leaves the SPA on
            # /login#code=... until it finishes loading its (slow, no-store)
            # JS bundle and processes the MSAL redirect into localStorage.
            # Wait for the URL to actually leave /login before capturing,
            # otherwise storage_state() misses the MSAL tokens entirely.
            import time as _time

            print(f"{Fore.YELLOW}⏳  Waiting for SPA to finish processing MSAL redirect...")
            _deadline = _time.monotonic() + 180
            while _time.monotonic() < _deadline:
                if "/login" not in page.url.lower():
                    print(f"{Fore.GREEN}✅  Left /login — SPA finished processing redirect\n")
                    break
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=3000)
                except Exception:
                    pass
                _time.sleep(1)
            else:
                logger.warning(
                    "Still on /login after 180s (still at %s) — capturing anyway",
                    page.url,
                )

            # ── 7. Dismiss PWA install prompt ──────────────────────────────────
            try:
                page.wait_for_selector(
                    '//*[@id="download-pwa"]/div[3]/div', timeout=8000
                )
                logger.info("PWA install prompt detected — dismissing")
                page.locator('[data-testid="CloseIcon"]').click(timeout=5000)
                logger.info("PWA prompt dismissed")
                print(f"{Fore.GREEN}✅  PWA popup dismissed\n")
            except Exception:
                pass  # No popup, that's fine

            # ── 8. Capture session ─────────────────────────────────────────────
            print(f"\n{Fore.YELLOW}📸 Capturing authentication state...")

            session_mgr = SessionStateManager()
            auth_ok = session_mgr.is_authenticated(page)
            if not auth_ok:
                logger.warning(
                    "Auth check uncertain — saving session anyway (login was just completed)."
                )

            session_path = Path(
                session_mgr.save_session_state(
                    context=context,
                    page=page,
                    env_type=env_mgr.current_env,
                )
            )

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ts_path = session_path.parent / session_path.name.replace(
                "_latest.json", f"_{ts}.json"
            )
            shutil.copy2(session_path, ts_path)
            logger.info("Timestamped backup: %s", ts_path)

            _print_success(session_path, app, env, browser)
            return str(session_path)

        finally:
            context.close()
            browser_instance.close()


def _print_success(session_path: Path, app: str, env: str, browser: str):
    expires_str = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
    print(f"\n{Fore.GREEN}{'=' * 70}")
    print(f"{Fore.GREEN}✅ SUCCESS! Authentication State Captured")
    print(f"{Fore.GREEN}{'=' * 70}\n")
    print(f"{Fore.WHITE}📁 File:    {Fore.CYAN}{session_path}")
    print(f"{Fore.WHITE}🔑 App:     {Fore.CYAN}{app}")
    print(f"{Fore.WHITE}🌍 Env:     {Fore.CYAN}{env}")
    print(f"{Fore.WHITE}🌐 Browser: {Fore.CYAN}{browser}")
    print(f"{Fore.WHITE}⏰ Expires: {Fore.CYAN}{expires_str}")
    print(f"\n{Fore.YELLOW}Run tests with:")
    print(f"{Fore.CYAN}  TEST_APP={app} TEST_ENV={env} BROWSER={browser} pytest")
    print(f"{Fore.GREEN}{'=' * 70}\n")


def capture_sessions_for_all_browsers(
    env: str,
    app: str = "meditek",
    device: str = DEFAULT_DEVICE,
    session_dir: str = None,
) -> tuple[dict, list]:
    """Capture sessions for every supported browser. Returns (results, failed_browsers)."""
    results: dict[str, str] = {}
    failed: list[str] = []

    for i, browser in enumerate(SUPPORTED_BROWSERS, 1):
        logger.info("[%d/%d] Capturing %s...", i, len(SUPPORTED_BROWSERS), browser)
        try:
            results[browser] = capture_session_for_browser(
                env, browser, app, device, session_dir
            )
        except Exception as e:
            logger.error("Failed to capture %s: %s", browser, e)
            failed.append(browser)

    return results, failed


def main():
    known_apps = list(_APP_REGISTRY.keys())

    parser = argparse.ArgumentParser(
        description="Capture authenticated browser sessions for reuse in test runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--app",
        default="meditek",
        choices=known_apps,
        help=f"Application to capture session for (default: meditek). Known: {known_apps}",
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["test", "preprod", "prod"],
        help="Target environment",
    )
    parser.add_argument(
        "--browser",
        default="all",
        choices=SUPPORTED_BROWSERS + ["all"],
        help="Browser to capture (default: all)",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        choices=list(_DEVICE_MAP.keys()),
        help=f"Device profile (default: {DEFAULT_DEVICE})",
    )
    parser.add_argument(
        "--session-dir",
        default=None,
        help="Session storage directory (default: ~/.refua_sessions)",
    )

    args = parser.parse_args()

    browsers = _browsers_to_capture(args.browser)
    expires_str = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")

    try:
        if len(browsers) == 1:
            session_path = capture_session_for_browser(
                args.env,
                browsers[0],
                args.app,
                args.device,
                args.session_dir,
            )
            print(f"\n{'=' * 70}")
            print("SESSION CAPTURED")
            print(f"  File:    {session_path}")
            print(f"  App:     {args.app}")
            print(f"  Browser: {browsers[0]}")
            print(f"  Expires: {expires_str}")
            print(
                f"  Run:     TEST_APP={args.app} TEST_ENV={args.env} BROWSER={browsers[0]} pytest"
            )
            print(f"{'=' * 70}\n")

        else:
            results, failed = capture_sessions_for_all_browsers(
                args.env, args.app, args.device, args.session_dir
            )
            print(f"\n{'=' * 70}")
            print(
                f"SESSION CAPTURE COMPLETE | app: {args.app} | expires: {expires_str}"
            )
            for browser, path in results.items():
                print(f"  [OK]   {browser}: {Path(path).name}")
            for browser in failed:
                print(f"  [FAIL] {browser}")
            print(f"  Run:  TEST_APP={args.app} TEST_ENV={args.env} pytest")
            print(f"{'=' * 70}\n")

        sys.exit(0)

    except TimeoutError as e:
        logger.error("Timeout: %s", e)
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except (InvalidEnvironmentError, UnknownAppError, ValueError) as e:
        logger.error("%s", e)
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        print(f"\nERROR: {e}\nRun with --help for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
