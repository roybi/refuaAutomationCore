#!/usr/bin/env python3
"""
Session Capture Script for refuaAutomationCore

Captures authenticated browser sessions to bypass 2FA in tests.
Sessions are saved with 3-day TTL in external directory: ~/.refua_sessions/

MULTI-BROWSER SUPPORT:
  - Captures sessions for ALL supported browsers (chromium, firefox, webkit, safari)
  - Creates separate session file for each browser per environment
  - Each file: auth_state_{env}_{browser}_latest.json
  - All files stored in same external directory for easy management

DOCKER SUPPORT:
  - External path configurable via SESSION_DIR environment variable
  - Default: ~/.refua_sessions/ (mounted volume in Docker)
  - Custom: SESSION_DIR=/path/to/sessions python scripts/capture_session.py ...
  - Respects Docker volume mounts for persistence

This script is run ONCE per environment/user/browser before automated tests execute.
The captured sessions are then automatically loaded by tests to skip 2FA.

Usage Examples:
    # Capture session for test environment (all browsers)
    python scripts/capture_session.py --env test --user john.doe

    # Capture session for specific browser only
    python scripts/capture_session.py --env test --user john.doe --browser chromium
    python scripts/capture_session.py --env test --user john.doe --browser firefox
    python scripts/capture_session.py --env test --user john.doe --browser webkit

    # Capture for all browsers (chromium, firefox, webkit, safari)
    python scripts/capture_session.py --env test --user john.doe --browser all

    # Capture session for iPhone device with specific browser
    python scripts/capture_session.py --env test --user john.doe --device iphone --browser webkit

    # Use custom session directory (Docker volumes)
    python scripts/capture_session.py --env test --user john.doe --session-dir /sessions
    SESSION_DIR=/shared/sessions python scripts/capture_session.py --env test --user john.doe

    # Capture for preprod environment
    python scripts/capture_session.py --env preprod --user john.doe

Session Details:
    - Sessions stored in external directory (default: ~/.refua_sessions/)
    - Session files: auth_state_{env}_{browser}_latest.json
      Examples:
        - auth_state_test_chromium_latest.json
        - auth_state_test_firefox_latest.json
        - auth_state_test_webkit_latest.json
        - auth_state_test_safari_latest.json
    - Valid for: 3 days from capture time
    - Re-run this script to refresh expired sessions
    - Sessions contain: cookies, localStorage, auth tokens
    - Ready for Docker volume mounts
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

from refua_core.config.environment import (
    EnvironmentManager,
    EnvType,
    InvalidEnvironmentError,
    EnvironmentNotSetError,
)
from refua_core.config.session_manager import SessionStateManager

# Setup logging
logger = logging.getLogger(__name__)

# Supported browsers for session capture
SUPPORTED_BROWSERS = ['chromium', 'firefox', 'webkit', 'safari']


def setup_logging():
    """Configure logging for capture script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - SESSION_CAPTURE - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_arguments(args):
    """
    Validate command-line arguments

    Args:
        args: Parsed command-line arguments

    Raises:
        InvalidEnvironmentError: If environment invalid
        ValueError: If username or browser not provided
    """
    # Validate environment
    valid_envs = ['test', 'preprod', 'prod']
    if args.env not in valid_envs:
        raise InvalidEnvironmentError(
            f"Invalid environment: '{args.env}'\n"
            f"Valid values: {', '.join(valid_envs)}"
        )

    # Validate username provided
    if not args.user or args.user.strip() == '':
        raise ValueError("Username is required (--user <username>)")

    # Validate browser provided
    valid_browsers = SUPPORTED_BROWSERS + ['all']
    if args.browser not in valid_browsers:
        raise ValueError(
            f"Invalid browser: '{args.browser}'\n"
            f"Valid values: {', '.join(valid_browsers)}"
        )

    logger.info(f"Arguments validated: env={args.env}, user={args.user}, browser={args.browser}")


def setup_environment_manager(env: str, session_dir: str = None):
    """
    Setup EnvironmentManager for specified environment

    Args:
        env: Environment (test, preprod, prod)
        session_dir: Optional custom session directory

    Returns:
        EnvironmentManager instance configured for environment

    Note:
        This temporarily overrides TEST_ENV to the specified environment.
        The SESSION_DIR override is set if custom path provided.
    """
    # Temporarily set TEST_ENV to the specified environment
    import os
    os.environ['TEST_ENV'] = env

    # If custom session dir provided, set SESSION_DIR
    if session_dir:
        session_path = Path(session_dir).expanduser().resolve()
        os.environ['SESSION_DIR'] = str(session_path)
        logger.debug(f"Using custom session directory: {session_path}")
    else:
        logger.debug(f"Using default session directory: ~/.refua_sessions/")

    # Create EnvironmentManager - will use TEST_ENV
    return EnvironmentManager()


def get_browsers_to_capture(browser_arg: str) -> list:
    """
    Get list of browsers to capture based on argument

    Args:
        browser_arg: Browser argument (specific browser or 'all')

    Returns:
        List of browsers to capture
    """
    if browser_arg.lower() == 'all':
        return SUPPORTED_BROWSERS
    else:
        return [browser_arg.lower()]


def capture_session_for_browser(
    env: str,
    user: str,
    browser: str,
    device: str = "desktop",
    session_dir: str = None
) -> str:
    """
    Capture authenticated session for a specific browser

    Args:
        env: Environment (test, preprod, prod)
        user: Username for logging/reference
        browser: Browser type (chromium, firefox, webkit, safari)
        device: Device profile (desktop, iphone, android)
        session_dir: Optional custom session directory

    Returns:
        Path to saved session file

    Raises:
        EnvironmentNotSetError: If environment configuration invalid
        TimeoutError: If user doesn't complete login within timeout
        Exception: If session save fails
    """
    logger.info(f"Capturing session for {browser} browser on {device}")

    # Setup environment manager
    try:
        env_mgr = setup_environment_manager(env, session_dir)
        logger.info(f"Environment configured: {env_mgr.current_env.value}")
    except (EnvironmentNotSetError, InvalidEnvironmentError) as e:
        logger.error(f"Environment setup failed: {e}")
        raise

    # Get configuration
    base_url = env_mgr.get_base_url()
    session_dir_path = env_mgr.get_session_dir()
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Browser: {browser}")
    logger.info(f"Session directory: {session_dir_path}")

    # Create session directory if needed
    session_dir_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Session directory ready: {session_dir_path}")

    # Launch browser
    logger.info(f"Launching {browser} browser (headless=false for interactive login)...")
    print(f"\n{'='*70}")
    print(f"BROWSER: {browser.upper()}")
    print(f"DEVICE: {device}")
    print(f"Please complete login and 2FA")
    print(f"{'='*70}\n")

    try:
        with sync_playwright() as p:
            # Get browser launcher dynamically
            try:
                browser_launcher = getattr(p, browser)
            except AttributeError:
                raise ValueError(f"Browser '{browser}' not supported by Playwright")

            # Launch browser
            browser_instance = browser_launcher.launch(headless=False)
            context = browser_instance.new_context()
            page = context.new_page()

            try:
                # Navigate to login page
                login_url = f"{base_url}/login"
                logger.info(f"Navigating to login page: {login_url}")
                page.goto(login_url, wait_until='networkidle')

                # Wait for user to complete login
                print("-" * 70)
                print(f"Please login to: {base_url}")
                print(f"Complete the login form and 2FA if required")
                print("-" * 70 + "\n")

                # Wait for successful authentication
                auth_timeout_ms = 5 * 60 * 1000  # 5 minutes

                logger.info(f"Waiting for authentication... (timeout: 5 minutes)")

                try:
                    # Wait for navigation to any authenticated page
                    page.wait_for_url(
                        f"{base_url.rstrip('/')}/**",
                        timeout=auth_timeout_ms
                    )

                    # Verify we're not on login page anymore
                    current_url = page.url
                    current_title = page.title()

                    if 'login' in current_url.lower() or 'signin' in current_url.lower():
                        raise TimeoutError(
                            "Still on login page - authentication incomplete. "
                            "Please ensure 2FA is completed."
                        )

                    logger.info(f"Authentication detected for {browser}!")
                    logger.info(f"Current URL: {current_url}")
                    logger.info(f"Page title: {current_title}")

                except TimeoutError:
                    raise TimeoutError(
                        f"Login timeout after 5 minutes on {browser} browser. "
                        "Please check if login/2FA was completed successfully."
                    )

                # Verify authenticated state
                session_mgr = SessionStateManager()
                is_auth = session_mgr.is_authenticated(page)
                logger.info(f"Is authenticated on {browser}: {is_auth}")

                if not is_auth:
                    logger.warning(
                        f"Page on {browser} doesn't appear authenticated. "
                        "Attempting to save session anyway."
                    )

                # Save session
                logger.info(f"Saving authenticated session for {browser}...")
                try:
                    session_path = session_mgr.save_session_state(
                        context=context,
                        page=page,
                        env_type=env_mgr.current_env
                    )

                    # Update session file name to include browser
                    original_path = Path(session_path)
                    browser_session_path = original_path.parent / f"auth_state_{env}_{browser}_latest.json"
                    original_path.rename(browser_session_path)

                    logger.info(f"Session saved for {browser}: {browser_session_path}")
                    return str(browser_session_path)

                except Exception as e:
                    logger.error(f"Failed to save session for {browser}: {e}")
                    raise

            finally:
                # Cleanup
                context.close()
                browser_instance.close()
                logger.debug(f"{browser} browser closed")

    except Exception as e:
        logger.error(f"Session capture failed for {browser}: {e}")
        raise


def capture_sessions_for_all_browsers(
    env: str,
    user: str,
    device: str = "desktop",
    session_dir: str = None
) -> dict:
    """
    Capture sessions for all supported browsers

    Args:
        env: Environment (test, preprod, prod)
        user: Username for logging/reference
        device: Device profile (desktop, iphone, android)
        session_dir: Optional custom session directory

    Returns:
        Dictionary mapping browser names to session file paths
    """
    logger.info(f"Capturing sessions for ALL browsers: {', '.join(SUPPORTED_BROWSERS)}")

    results = {}
    failed_browsers = []

    for browser in SUPPORTED_BROWSERS:
        try:
            logger.info(f"\n[{SUPPORTED_BROWSERS.index(browser) + 1}/{len(SUPPORTED_BROWSERS)}] Capturing {browser}...")
            session_path = capture_session_for_browser(env, user, browser, device, session_dir)
            results[browser] = session_path
            logger.info(f"Successfully captured {browser} session")

        except Exception as e:
            logger.error(f"Failed to capture {browser} session: {e}")
            failed_browsers.append(browser)
            # Continue with next browser instead of failing
            input(f"\nPress Enter to continue with next browser (or Ctrl+C to exit)...")

    return results, failed_browsers


def main():
    """Entry point for session capture script"""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Capture authenticated browser sessions for test automation (multi-browser support)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Capture all browsers for test environment:
    python scripts/capture_session.py --env test --user john.doe

  Capture specific browser:
    python scripts/capture_session.py --env test --user john.doe --browser chromium
    python scripts/capture_session.py --env test --user john.doe --browser firefox

  Capture for all browsers explicitly:
    python scripts/capture_session.py --env test --user john.doe --browser all

  Use custom session directory (Docker):
    SESSION_DIR=/sessions python scripts/capture_session.py --env test --user john.doe
    python scripts/capture_session.py --env test --user john.doe --session-dir /mnt/sessions

Session Files Created:
  - auth_state_test_chromium_latest.json
  - auth_state_test_firefox_latest.json
  - auth_state_test_webkit_latest.json
  - auth_state_test_safari_latest.json

Each file is reusable for 3 days from capture time.
        """
    )

    parser.add_argument(
        '--env',
        required=True,
        choices=['test', 'preprod', 'prod'],
        help='Target environment for session capture'
    )

    parser.add_argument(
        '--user',
        required=True,
        help='Username for authentication (required for 2FA)'
    )

    parser.add_argument(
        '--browser',
        default='all',
        choices=SUPPORTED_BROWSERS + ['all'],
        help='Browser to capture (default: all - captures all supported browsers)'
    )

    parser.add_argument(
        '--device',
        default='desktop',
        choices=['desktop', 'iphone', 'android'],
        help='Device profile (default: desktop)'
    )

    parser.add_argument(
        '--session-dir',
        default=None,
        help='Custom session directory (default: ~/.refua_sessions/). Respects Docker volume mounts.'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger.info(f"refuaAutomationCore Multi-Browser Session Capture Script")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Supported browsers: {', '.join(SUPPORTED_BROWSERS)}")

    try:
        # Validate arguments
        validate_arguments(args)

        # Determine which browsers to capture
        browsers_to_capture = get_browsers_to_capture(args.browser)
        logger.info(f"Will capture for browser(s): {', '.join(browsers_to_capture)}")

        # Capture sessions
        if len(browsers_to_capture) == 1:
            # Single browser capture
            session_path = capture_session_for_browser(
                env=args.env,
                user=args.user,
                browser=browsers_to_capture[0],
                device=args.device,
                session_dir=args.session_dir
            )

            # Display success
            expiration_time = datetime.now() + timedelta(days=3)
            expiration_str = expiration_time.strftime('%Y-%m-%d %H:%M:%S UTC')

            print("\n" + "=" * 70)
            print("SESSION CAPTURED SUCCESSFULLY!")
            print("=" * 70)
            print(f"Session file: {session_path}")
            print(f"Environment: {args.env}")
            print(f"User: {args.user}")
            print(f"Browser: {browsers_to_capture[0]}")
            print(f"Device: {args.device}")
            print(f"Valid until: {expiration_str}")
            print("=" * 70)
            print("\nNext Steps:")
            print(f"  1. Run tests: TEST_ENV={args.env} BROWSER={browsers_to_capture[0]} pytest")
            print(f"  2. Tests will automatically load this session")
            print(f"  3. Session valid for 3 days")
            print(f"  4. To refresh: re-run this script\n")

        else:
            # Multiple browsers capture
            results, failed = capture_sessions_for_all_browsers(
                env=args.env,
                user=args.user,
                device=args.device,
                session_dir=args.session_dir
            )

            # Display results
            expiration_time = datetime.now() + timedelta(days=3)
            expiration_str = expiration_time.strftime('%Y-%m-%d %H:%M:%S UTC')

            print("\n" + "=" * 70)
            print("SESSION CAPTURE COMPLETE!")
            print("=" * 70)
            print(f"Environment: {args.env}")
            print(f"User: {args.user}")
            print(f"Device: {args.device}")
            print(f"Valid until: {expiration_str}")
            print("\nCaptured Browsers:")
            for browser, path in results.items():
                print(f"  [OK] {browser}: {Path(path).name}")

            if failed:
                print("\nFailed Browsers:")
                for browser in failed:
                    print(f"  [FAIL] {browser}")

            print("\n" + "=" * 70)
            print("Next Steps:")
            print(f"  1. Run tests with any browser:")
            print(f"     TEST_ENV={args.env} pytest")
            print(f"  2. Or run with specific browser:")
            print(f"     BROWSER=firefox TEST_ENV={args.env} pytest")
            print(f"  3. All captured sessions valid for 3 days")
            print(f"  4. To refresh: re-run this script\n")

        logger.info("Session capture complete")
        sys.exit(0)

    except InvalidEnvironmentError as e:
        logger.error(f"Invalid environment: {e}")
        print(f"\nERROR: {e}\n", file=sys.stderr)
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Invalid argument: {e}")
        print(f"\nERROR: {e}\n", file=sys.stderr)
        sys.exit(1)

    except TimeoutError as e:
        logger.error(f"Timeout: {e}")
        print(f"\nERROR: {e}\n", file=sys.stderr)
        print("\nTroubleshooting:")
        print("  1. Check if browser window opened")
        print("  2. Complete login and 2FA in the browser")
        print("  3. Wait for dashboard/home page to load")
        print("  4. Re-run this script if needed")
        print()
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nERROR: Failed to capture session: {e}\n", file=sys.stderr)
        print("\nPlease check the logs above for details.")
        print("If the issue persists, verify:")
        print("  1. Environment is valid (test, preprod, prod)")
        print("  2. Username is correct")
        print("  3. Network connectivity to base URL")
        print("  4. Playwright browsers are installed")
        print("     (Run: python -m playwright install)")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
