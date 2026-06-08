#!/usr/bin/env python3
"""
Capture authenticated browser sessions for 2FA bypass in automated tests.

Sessions are stored in ~/.refua_sessions/ (or SESSION_DIR) with a 3-day TTL.
One file is created per app+environment+browser combination:
  auth_state_{app}_{env}_{browser}_latest.json

Usage:
    python scripts/capture_session.py --env test
    python scripts/capture_session.py --env test --app cpr-go
    python scripts/capture_session.py --env test --browser firefox
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

SUPPORTED_BROWSERS = ["chromium", "firefox", "safari"]

# Maps CLI device names to Playwright built-in descriptor names.
# Playwright's p.devices[name] provides viewport, UA, scale factor, isMobile, hasTouch.
_DEVICE_MAP = {
    "desktop": None,
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


# ── Microsoft login helpers ──────────────────────────────────────────────────


def _click_submit(page, timeout: int = 10000) -> bool:
    """Click the Next / Submit / Sign-in button on Microsoft login pages.

    Tries multiple selectors so it works regardless of which step we're on.
    """
    for sel in [
        "#idSIButton9",
        'input[type="submit"]',
        'button[type="submit"]',
        'button:has-text("Next")',
        'button:has-text("Sign in")',
    ]:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click(timeout=timeout)
                return True
        except Exception:
            continue
    return False


def _auto_microsoft_login(page, username: str, password: str) -> bool:
    """Auto-fill Microsoft AAD login: username → Next, password → Sign in.

    Uses element-based waits only — not networkidle — so it works on
    both fast and slow networks. Returns True when credentials are submitted.
    The caller must still handle the 2FA step.
    """
    try:
        # ── Username ──────────────────────────────────────────────────────────
        user_input = page.locator('input[name="loginfmt"], input[type="email"]').first
        user_input.wait_for(state="visible", timeout=30000)
        user_input.fill(username)
        logger.info("Filled username")
        _click_submit(page)
        logger.info("Clicked Next after username")

        # ── Password ──────────────────────────────────────────────────────────
        pass_input = page.locator('input[name="passwd"], input[type="password"]').first
        pass_input.wait_for(state="visible", timeout=30000)
        pass_input.fill(password)
        logger.info("Filled password")
        _click_submit(page)
        logger.info("Password submitted — 2FA page should appear")

        return True

    except Exception as e:
        logger.error("Auto-login failed: %s", e)
        return False


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


# ── Main capture ─────────────────────────────────────────────────────────────


def capture_session_for_browser(
    env: str,
    browser: str,
    app: str = "meditek",
    device: str = "desktop",
    session_dir: str = None,
    username: str = None,
    password: str = None,
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

        _incognito_args = {
            "chromium": ["--no-sandbox", "--disable-dev-shm-usage", "--incognito"],
            "firefox": ["-private"],
            # "webkit": [],
            "safari": [],
        }
        browser_instance = browser_launcher.launch(
            headless=False,
            args=_incognito_args.get(browser, []),
        )

        playwright_device_name = _DEVICE_MAP.get(
            device.lower() if device else "desktop"
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
            page.goto(base_url, wait_until="domcontentloaded", timeout=120000)

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

            # ── 4. Credentials ────────────────────────────────────────────────
            if username and password:
                # AUTO mode: script fills username + password
                print(f"{Fore.YELLOW}⏳  Clicking login button...")
                try:
                    page.locator("#login-button").click(timeout=10000)
                    logger.info("Clicked #login-button")
                except Exception as e:
                    logger.warning("Could not click #login-button: %s", e)

                print(f"{Fore.YELLOW}⏳  Filling credentials automatically...")
                ok = _auto_microsoft_login(page, username, password)
                if ok:
                    print(
                        f"{Fore.GREEN}✅  Credentials submitted — waiting for 2FA...\n"
                    )
                else:
                    print(
                        f"{Fore.YELLOW}⚠   Auto-login had issues — "
                        f"complete the credentials manually in the browser\n"
                    )

            else:
                # MANUAL mode: user fills credentials
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
                    f"\n{Fore.CYAN}  When you see the number on screen, press ENTER here ↵"
                )
                input()

            # ── 5. 2FA — display number and wait for approval ─────────────────
            two_fa_number = _extract_2fa_number(page)

            print(f"\n{Fore.YELLOW}{'=' * 70}")
            print(f"{Fore.YELLOW}STEP 2 of 2 — Approve Microsoft 2FA in Authenticator")
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
            print(
                f"\n{Fore.CYAN}  Press ENTER here after you have approved in the app ↵"
            )
            input()

            # ── 6. Auto-handle 'Stay signed in?' ──────────────────────────────
            print(f"\n{Fore.YELLOW}⏳  Handling post-login pages...")
            _handle_stay_signed_in(page, timeout=20000)

            # Wait for the app to finish redirecting after KMSI
            try:
                page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass  # Page may already be loaded

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
            if not session_mgr.is_authenticated(page):
                logger.warning(
                    "Page does not look authenticated; saving session anyway."
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
    device: str = "desktop",
    session_dir: str = None,
    username: str = None,
    password: str = None,
) -> tuple[dict, list]:
    """Capture sessions for every supported browser. Returns (results, failed_browsers)."""
    results: dict[str, str] = {}
    failed: list[str] = []

    for i, browser in enumerate(SUPPORTED_BROWSERS, 1):
        logger.info("[%d/%d] Capturing %s...", i, len(SUPPORTED_BROWSERS), browser)
        try:
            results[browser] = capture_session_for_browser(
                env, browser, app, device, session_dir, username, password
            )
        except Exception as e:
            logger.error("Failed to capture %s: %s", browser, e)
            failed.append(browser)

    return results, failed


def main():
    known_apps = list(_APP_REGISTRY.keys())

    parser = argparse.ArgumentParser(
        description="Capture authenticated browser sessions for 2FA bypass.",
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
        "--username",
        default=os.getenv("CAPTURE_USERNAME"),
        help="Username for auto-login (or set CAPTURE_USERNAME env var). "
        "If omitted, login is done manually in the browser.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("CAPTURE_PASSWORD"),
        help="Password for auto-login (or set CAPTURE_PASSWORD env var). "
        "Prefer env var over CLI arg to keep password out of shell history.",
    )
    parser.add_argument(
        "--browser",
        default="all",
        choices=SUPPORTED_BROWSERS + ["all"],
        help="Browser to capture (default: all)",
    )
    parser.add_argument(
        "--device",
        default="desktop",
        choices=list(_DEVICE_MAP.keys()),
        help="Device profile (default: desktop)",
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
        if args.username and args.password:
            print(f"{Fore.CYAN}Auto-login enabled for: {args.username}\n")

        if len(browsers) == 1:
            session_path = capture_session_for_browser(
                args.env,
                browsers[0],
                args.app,
                args.device,
                args.session_dir,
                args.username,
                args.password,
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
