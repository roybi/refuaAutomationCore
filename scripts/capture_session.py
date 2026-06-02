#!/usr/bin/env python3
"""
Capture authenticated browser sessions for 2FA bypass in automated tests.

Sessions are stored in ~/.refua_sessions/ (or SESSION_DIR) with a 3-day TTL.
One file is created per environment+browser combination:
  auth_state_{env}_{browser}_latest.json

Usage:
    python scripts/capture_session.py --env test --user john.doe
    python scripts/capture_session.py --env test --user john.doe --browser firefox
    python scripts/capture_session.py --env test --user john.doe --session-dir /sessions
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

from refua_core.config.environment import (
    EnvironmentManager,
    InvalidEnvironmentError,
    EnvironmentNotSetError,
)
from refua_core.config.session_manager import SessionStateManager

logger = logging.getLogger(__name__)

SUPPORTED_BROWSERS = ["chromium", "firefox", "webkit", "safari"]


def _setup_env_manager(env: str, session_dir: str = None) -> EnvironmentManager:
    """Reset and reinitialise the EnvironmentManager singleton for the given env."""
    os.environ["TEST_ENV"] = env
    if session_dir:
        os.environ["SESSION_DIR"] = str(Path(session_dir).expanduser().resolve())
    EnvironmentManager.reset_instance()
    return EnvironmentManager()


def _browsers_to_capture(browser_arg: str) -> list[str]:
    return SUPPORTED_BROWSERS if browser_arg == "all" else [browser_arg]


def capture_session_for_browser(
    env: str,
    user: str,
    browser: str,
    device: str = "desktop",
    session_dir: str = None,
) -> str:
    """Launch an interactive browser, wait for login+2FA, then save the session.

    Returns the path to the saved session file.
    """
    env_mgr = _setup_env_manager(env, session_dir)
    base_url = env_mgr.get_base_url()
    session_dir_path = env_mgr.get_session_dir()
    session_dir_path.mkdir(parents=True, exist_ok=True)

    logger.info("Capturing %s session | env=%s device=%s", browser, env, device)
    print(f"\n{'='*70}\nBROWSER: {browser.upper()} | DEVICE: {device}")
    print("Please complete login and 2FA in the browser window.")
    print(f"{'='*70}\n")

    with sync_playwright() as p:
        browser_launcher = getattr(p, browser, None)
        if browser_launcher is None:
            raise ValueError(f"Browser '{browser}' not supported by Playwright")

        browser_instance = browser_launcher.launch(headless=False)
        context = browser_instance.new_context()
        page = context.new_page()

        try:
            page.goto(f"{base_url}/login", wait_until="networkidle")
            print(f"Login URL: {base_url}\n")

            auth_timeout_ms = 5 * 60 * 1000
            page.wait_for_url(f"{base_url.rstrip('/')}/**", timeout=auth_timeout_ms)

            if any(x in page.url.lower() for x in ("/login", "/signin")):
                raise TimeoutError("Still on login page — 2FA not completed.")

            logger.info("Authenticated | url=%s title=%s", page.url, page.title())

            session_mgr = SessionStateManager()
            if not session_mgr.is_authenticated(page):
                logger.warning("Page does not look authenticated; saving session anyway.")

            session_path = Path(
                session_mgr.save_session_state(context=context, page=page,
                                               env_type=env_mgr.current_env)
            )
            browser_path = session_path.parent / f"auth_state_{env}_{browser}_latest.json"
            session_path.rename(browser_path)

            logger.info("Session saved: %s", browser_path)
            return str(browser_path)

        finally:
            context.close()
            browser_instance.close()


def capture_sessions_for_all_browsers(
    env: str,
    user: str,
    device: str = "desktop",
    session_dir: str = None,
) -> tuple[dict, list]:
    """Capture sessions for every supported browser. Returns (results, failed_browsers)."""
    results: dict[str, str] = {}
    failed: list[str] = []

    for i, browser in enumerate(SUPPORTED_BROWSERS, 1):
        logger.info("[%d/%d] Capturing %s...", i, len(SUPPORTED_BROWSERS), browser)
        try:
            results[browser] = capture_session_for_browser(env, user, browser, device, session_dir)
        except Exception as e:
            logger.error("Failed to capture %s: %s", browser, e)
            failed.append(browser)

    return results, failed


def main():
    parser = argparse.ArgumentParser(
        description="Capture authenticated browser sessions for 2FA bypass.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--env", required=True, choices=["test", "preprod", "prod"],
                        help="Target environment")
    parser.add_argument("--user", required=True,
                        help="Username (for logging only; login is manual)")
    parser.add_argument("--browser", default="all",
                        choices=SUPPORTED_BROWSERS + ["all"],
                        help="Browser to capture (default: all)")
    parser.add_argument("--device", default="desktop",
                        choices=["desktop", "iphone", "android"],
                        help="Device profile (default: desktop)")
    parser.add_argument("--session-dir", default=None,
                        help="Session storage directory (default: ~/.refua_sessions)")

    args = parser.parse_args()

    if not args.user.strip():
        parser.error("--user cannot be empty")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    browsers = _browsers_to_capture(args.browser)
    expires_str = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M UTC")

    try:
        if len(browsers) == 1:
            session_path = capture_session_for_browser(
                args.env, args.user, browsers[0], args.device, args.session_dir
            )
            print(f"\n{'='*70}")
            print("SESSION CAPTURED")
            print(f"  File:    {session_path}")
            print(f"  Browser: {browsers[0]}")
            print(f"  Expires: {expires_str}")
            print(f"  Run:     TEST_ENV={args.env} BROWSER={browsers[0]} pytest")
            print(f"{'='*70}\n")

        else:
            results, failed = capture_sessions_for_all_browsers(
                args.env, args.user, args.device, args.session_dir
            )
            print(f"\n{'='*70}")
            print(f"SESSION CAPTURE COMPLETE | expires: {expires_str}")
            for browser, path in results.items():
                print(f"  [OK]   {browser}: {Path(path).name}")
            for browser in failed:
                print(f"  [FAIL] {browser}")
            print(f"  Run:  TEST_ENV={args.env} pytest")
            print(f"{'='*70}\n")

        sys.exit(0)

    except TimeoutError as e:
        logger.error("Timeout: %s", e)
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except (InvalidEnvironmentError, ValueError) as e:
        logger.error("%s", e)
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        print(f"\nERROR: {e}\nRun with --help for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
