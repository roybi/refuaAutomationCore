#!/usr/bin/env python3
"""
Session Capture Script for refuaAutomationCore

Captures authenticated browser sessions to bypass 2FA in tests.
Sessions are saved with 3-day TTL in external directory: ~/.refua_sessions/

This script is run ONCE per environment/user before automated tests execute.
The captured session is then automatically loaded by tests to skip 2FA.

Usage Examples:
    # Capture session for test environment
    python scripts/capture_session.py --env test --user john.doe

    # Capture session for iPhone device
    python scripts/capture_session.py --env test --user john.doe --device iphone

    # Use custom session directory
    python scripts/capture_session.py --env test --user john.doe --session-dir /custom/path

    # Capture for preprod environment
    python scripts/capture_session.py --env preprod --user john.doe

Session Details:
    - Sessions are stored in: ~/.refua_sessions/
    - Session file: auth_state_{env}_{browser}_latest.json
    - Valid for: 3 days from capture time
    - Re-run this script to refresh expired sessions
    - Sessions contain: cookies, localStorage, auth tokens
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
        ValueError: If username not provided
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

    logger.info(f"Arguments validated: env={args.env}, user={args.user}")


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


def capture_session(
    env: str,
    user: str,
    device: str = "desktop",
    session_dir: str = None
):
    """
    Main session capture function

    Launches browser, waits for user to complete login + 2FA,
    then saves the authenticated session.

    Args:
        env: Environment (test, preprod, prod)
        user: Username for logging/reference
        device: Device profile (desktop, iphone, android) - defaults to desktop
        session_dir: Optional custom session directory

    Raises:
        EnvironmentNotSetError: If environment configuration invalid
        TimeoutError: If user doesn't complete login within timeout
        Exception: If session save fails

    Flow:
        1. Setup environment configuration
        2. Get base URLs from EnvironmentManager
        3. Create/verify session directory
        4. Launch browser with headless=false (interactive)
        5. Navigate to login page
        6. Wait for user to complete login and 2FA
        7. Detect authenticated page
        8. Save session with metadata
        9. Display success message
    """
    logger.info(f"Starting session capture: env={env}, user={user}, device={device}")

    # Step 1: Setup environment manager
    try:
        env_mgr = setup_environment_manager(env, session_dir)
        logger.info(f"Environment configured: {env_mgr.current_env.value}")
    except (EnvironmentNotSetError, InvalidEnvironmentError) as e:
        logger.error(f"Environment setup failed: {e}")
        raise

    # Step 2: Get configuration
    base_url = env_mgr.get_base_url()
    api_url = env_mgr.get_api_url()
    session_timeout = env_mgr.get_session_timeout()
    bypass_2fa = env_mgr.should_bypass_2fa()

    logger.info(f"Base URL: {base_url}")
    logger.info(f"2FA Bypass: {'Enabled' if bypass_2fa else 'Disabled'}")
    logger.info(f"Session Timeout: {session_timeout}s")

    # Step 3: Get session directory
    session_dir_path = env_mgr.get_session_dir()
    logger.info(f"Session directory: {session_dir_path}")

    # Create session directory if needed
    session_dir_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Session directory ready: {session_dir_path}")

    # Step 4: Launch browser
    logger.info(f"Launching {device} browser (headless=false for interactive login)...")
    print("\n" + "=" * 70)
    print("BROWSER WINDOW OPENING - Please complete login and 2FA")
    print("=" * 70)

    try:
        with sync_playwright() as p:
            # Launch chromium (other browsers supported in future)
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            try:
                # Step 5: Navigate to login page
                login_url = f"{base_url}/login"
                logger.info(f"Navigating to login page: {login_url}")
                page.goto(login_url, wait_until='networkidle')

                # Step 6: Wait for user to complete login
                print("\n" + "-" * 70)
                print(f"Please login to: {base_url}")
                print(f"Complete the login form and 2FA if required")
                print("-" * 70 + "\n")

                # Wait for successful authentication (user navigates away from login page)
                # Timeout: 5 minutes for user interaction
                auth_timeout_ms = 5 * 60 * 1000  # 5 minutes
                dashboard_url_pattern = f"{base_url.rstrip('/')}/dashboard"

                logger.info(f"Waiting for authentication... (timeout: 5 minutes)")
                logger.debug(f"Will detect navigation away from login page")

                try:
                    # Wait for navigation to any authenticated page
                    # This handles various redirect patterns (dashboard, home, etc.)
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

                    logger.info(f"Authentication detected!")
                    logger.info(f"Current URL: {current_url}")
                    logger.info(f"Page title: {current_title}")

                except TimeoutError:
                    raise TimeoutError(
                        "Login timeout after 5 minutes. "
                        "Please check if login/2FA was completed successfully."
                    )

                # Step 7: Verify authenticated state
                session_mgr = SessionStateManager()
                is_auth = session_mgr.is_authenticated(page)
                logger.info(f"Is authenticated: {is_auth}")

                if not is_auth:
                    logger.warning(
                        "Page doesn't appear authenticated. "
                        "Attempting to save session anyway."
                    )

                # Step 8: Save session
                logger.info("Saving authenticated session...")
                try:
                    session_path = session_mgr.save_session_state(
                        context=context,
                        page=page,
                        env_type=env_mgr.current_env
                    )
                    logger.info(f"Session saved successfully: {session_path}")
                except Exception as e:
                    logger.error(f"Failed to save session: {e}")
                    raise

            finally:
                # Cleanup
                context.close()
                browser.close()
                logger.debug("Browser closed")

    except Exception as e:
        logger.error(f"Session capture failed: {e}")
        raise

    # Step 9: Display success message
    expiration_time = datetime.now() + timedelta(days=3)
    expiration_str = expiration_time.strftime('%Y-%m-%d %H:%M:%S UTC')

    print("\n" + "=" * 70)
    print("SESSION CAPTURED SUCCESSFULLY!")
    print("=" * 70)
    print(f"Session file: {session_path}")
    print(f"Environment: {env}")
    print(f"User: {user}")
    print(f"Device: {device}")
    print(f"Valid until: {expiration_str}")
    print("=" * 70)
    print("\nNext Steps:")
    print(f"  1. Run tests: TEST_ENV={env} pytest --alluredir=./allure-results")
    print(f"  2. Tests will automatically load this session")
    print(f"  3. Session valid for 3 days")
    print(f"  4. To refresh: re-run this script")
    print("\n")

    logger.info("Session capture complete")
    return session_path


def main():
    """Entry point for session capture script"""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Capture authenticated browser session for test automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Capture for test environment:
    python scripts/capture_session.py --env test --user john.doe

  Capture for iPhone device:
    python scripts/capture_session.py --env test --user john.doe --device iphone

  Use custom session directory:
    python scripts/capture_session.py --env test --user john.doe --session-dir /custom/path

Session Details:
  - Sessions stored in: ~/.refua_sessions/
  - Session file: auth_state_{env}_{browser}_latest.json
  - Valid for: 3 days from capture
  - Can be refreshed by re-running this script
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
        '--device',
        default='desktop',
        choices=['desktop', 'iphone', 'android'],
        help='Device profile (default: desktop)'
    )

    parser.add_argument(
        '--session-dir',
        default=None,
        help='Custom session directory (default: ~/.refua_sessions/)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger.info(f"refuaAutomationCore Session Capture Script")
    logger.info(f"Python version: {sys.version}")

    try:
        # Validate arguments
        validate_arguments(args)

        # Capture session
        session_path = capture_session(
            env=args.env,
            user=args.user,
            device=args.device,
            session_dir=args.session_dir
        )

        # Success
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
        print("  4. Browser can launch (Chromium installed)")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
