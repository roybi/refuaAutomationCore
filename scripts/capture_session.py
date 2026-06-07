#!/usr/bin/env python3
"""
Capture authenticated browser sessions for 2FA bypass in automated tests.

Sessions are stored in ~/.refua_sessions/ (or SESSION_DIR) with a 3-day TTL.
One file is created per app+environment+browser combination:
  auth_state_{app}_{env}_{browser}_latest.json

Usage:
    python scripts/capture_session.py --env test --user john.doe
    python scripts/capture_session.py --env test --user john.doe --app cpr-go
    python scripts/capture_session.py --env test --user john.doe --browser firefox
    python scripts/capture_session.py --env test --user john.doe --session-dir /sessions
"""

import argparse
import logging
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from colorama import Fore, init
from playwright.sync_api import sync_playwright

from refua_core.config.environment import (
    EnvironmentManager,
    InvalidEnvironmentError,
    UnknownAppError,
    _APP_REGISTRY,
)
from refua_core.config.session_manager import SessionStateManager

init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("auth_capture.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

SUPPORTED_BROWSERS = ["chromium", "firefox", "webkit", "safari"]


def _setup_env_manager(env: str, app: str = "meditek", session_dir: str = None) -> EnvironmentManager:
    """Reset and reinitialise the EnvironmentManager singleton for the given app+env."""
    os.environ["TEST_ENV"] = env
    os.environ["TEST_APP"] = app
    if session_dir:
        os.environ["SESSION_DIR"] = str(Path(session_dir).expanduser().resolve())
    EnvironmentManager.reset_instance()
    return EnvironmentManager()


def _browsers_to_capture(browser_arg: str) -> list[str]:
    return SUPPORTED_BROWSERS if browser_arg == "all" else [browser_arg]


def _log_auth_request(request):
    if any(p in request.url.lower() for p in ["login", "auth", "token", "microsoft", "oauth", "msal"]):
        logger.debug("→ Auth Request: %s %s", request.method, request.url)


def _log_auth_response(response):
    if any(p in response.url.lower() for p in ["login", "auth", "token", "microsoft", "oauth", "msal"]):
        logger.debug("← Auth Response: %s %s", response.status, response.url)
        if response.status >= 400:
            logger.warning("Auth Error: %s at %s", response.status, response.url)


def capture_session_for_browser(
    env: str,
    user: str,
    browser: str,
    app: str = "meditek",
    device: str = "desktop",
    session_dir: str = None,
) -> str:
    """Launch an interactive browser, wait for ENTER after login+2FA, then save session.

    Returns the path to the saved session file.
    """
    os.environ["BROWSER"] = browser  # ensures get_session_file_path uses the right browser name
    env_mgr = _setup_env_manager(env, app, session_dir)
    base_url = env_mgr.get_base_url()
    env_mgr.get_session_dir().mkdir(parents=True, exist_ok=True)

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}BROWSER: {browser.upper()} | APP: {app} | ENV: {env.upper()} | DEVICE: {device}")
    print(f"{Fore.CYAN}{'='*70}")
    print(f"\n{Fore.YELLOW}{'='*70}")
    print(f"{Fore.YELLOW}MANUAL AUTHENTICATION REQUIRED — {env.upper()} Environment")
    print(f"{Fore.YELLOW}{'='*70}")
    print(f"\n{Fore.WHITE}Follow these steps:")
    print(f"{Fore.GREEN}1. ✓  Browser will open at: {Fore.CYAN}{base_url}")
    print(f"{Fore.GREEN}2. →  Enter your username and password")
    print(f"{Fore.GREEN}3. →  Complete Microsoft 2FA verification")
    print(f"{Fore.GREEN}4. →  Wait for the main application page to load")
    print(f"{Fore.GREEN}5. →  Return here and press ENTER")
    print(f"\n{Fore.YELLOW}⚠   DO NOT close the browser — the script will close it automatically.")
    print(f"{Fore.YELLOW}{'='*70}\n")

    with sync_playwright() as p:
        browser_launcher = getattr(p, browser, None)
        if browser_launcher is None:
            raise ValueError(f"Browser '{browser}' not supported by Playwright")

        launch_kwargs = {"headless": False}
        if browser == "chromium":
            launch_kwargs["args"] = ["--no-sandbox", "--disable-dev-shm-usage"]

        browser_instance = browser_launcher.launch(**launch_kwargs)
        context = browser_instance.new_context(
            locale="he-IL",
            timezone_id="Asia/Jerusalem",
        )

        context.on("request", _log_auth_request)
        context.on("response", _log_auth_response)

        page = context.new_page()

        try:
            login_url = base_url.rstrip("/") + "/login"
            logger.info("Navigating to %s", login_url)
            page.goto(login_url, wait_until="networkidle", timeout=60000)

            # 50% zoom for better visibility on high-resolution screens
            page.evaluate("document.body.style.zoom = '0.5'")

            print(f"{Fore.GREEN}➜   Press ENTER after completing login and 2FA...")
            input()

            print(f"\n{Fore.YELLOW}📸 Capturing authentication state...")

            session_mgr = SessionStateManager()
            if not session_mgr.is_authenticated(page):
                logger.warning("Page does not look authenticated; saving session anyway.")

            session_path = Path(
                session_mgr.save_session_state(
                    context=context,
                    page=page,
                    env_type=env_mgr.current_env,
                )
            )

            # Save a timestamped backup alongside the _latest file
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ts_path = session_path.parent / session_path.name.replace("_latest.json", f"_{ts}.json")
            shutil.copy2(session_path, ts_path)
            logger.info("Timestamped backup: %s", ts_path)

            _print_success(session_path, app, env, browser)
            return str(session_path)

        finally:
            context.close()
            browser_instance.close()


def _print_success(session_path: Path, app: str, env: str, browser: str):
    expires_str = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"{Fore.GREEN}✅ SUCCESS! Authentication State Captured")
    print(f"{Fore.GREEN}{'='*70}\n")
    print(f"{Fore.WHITE}📁 File:    {Fore.CYAN}{session_path}")
    print(f"{Fore.WHITE}🔑 App:     {Fore.CYAN}{app}")
    print(f"{Fore.WHITE}🌍 Env:     {Fore.CYAN}{env}")
    print(f"{Fore.WHITE}🌐 Browser: {Fore.CYAN}{browser}")
    print(f"{Fore.WHITE}⏰ Expires: {Fore.CYAN}{expires_str}")
    print(f"\n{Fore.YELLOW}Run tests with:")
    print(f"{Fore.CYAN}  TEST_APP={app} TEST_ENV={env} BROWSER={browser} pytest")
    print(f"{Fore.GREEN}{'='*70}\n")


def capture_sessions_for_all_browsers(
    env: str,
    user: str,
    app: str = "meditek",
    device: str = "desktop",
    session_dir: str = None,
) -> tuple[dict, list]:
    """Capture sessions for every supported browser. Returns (results, failed_browsers)."""
    results: dict[str, str] = {}
    failed: list[str] = []

    for i, browser in enumerate(SUPPORTED_BROWSERS, 1):
        logger.info("[%d/%d] Capturing %s...", i, len(SUPPORTED_BROWSERS), browser)
        try:
            results[browser] = capture_session_for_browser(env, user, browser, app, device, session_dir)
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
    parser.add_argument("--app", default="meditek", choices=known_apps,
                        help=f"Application to capture session for (default: meditek). Known: {known_apps}")
    parser.add_argument("--env", required=True, choices=["test", "preprod", "prod"],
                        help="Target environment")
    parser.add_argument("--user", default=None,
                        help="Username (optional, for log output only; login is done manually in the browser)")
    parser.add_argument("--browser", default="all",
                        choices=SUPPORTED_BROWSERS + ["all"],
                        help="Browser to capture (default: all)")
    parser.add_argument("--device", default="desktop",
                        choices=["desktop", "iphone", "android"],
                        help="Device profile (default: desktop)")
    parser.add_argument("--session-dir", default=None,
                        help="Session storage directory (default: ~/.refua_sessions)")

    args = parser.parse_args()

    browsers = _browsers_to_capture(args.browser)
    expires_str = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")

    try:
        if len(browsers) == 1:
            session_path = capture_session_for_browser(
                args.env, args.user, browsers[0], args.app, args.device, args.session_dir
            )
            print(f"\n{'='*70}")
            print("SESSION CAPTURED")
            print(f"  File:    {session_path}")
            print(f"  App:     {args.app}")
            print(f"  Browser: {browsers[0]}")
            print(f"  Expires: {expires_str}")
            print(f"  Run:     TEST_APP={args.app} TEST_ENV={args.env} BROWSER={browsers[0]} pytest")
            print(f"{'='*70}\n")

        else:
            results, failed = capture_sessions_for_all_browsers(
                args.env, args.user, args.app, args.device, args.session_dir
            )
            print(f"\n{'='*70}")
            print(f"SESSION CAPTURE COMPLETE | app: {args.app} | expires: {expires_str}")
            for browser, path in results.items():
                print(f"  [OK]   {browser}: {Path(path).name}")
            for browser in failed:
                print(f"  [FAIL] {browser}")
            print(f"  Run:  TEST_APP={args.app} TEST_ENV={args.env} pytest")
            print(f"{'='*70}\n")

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
