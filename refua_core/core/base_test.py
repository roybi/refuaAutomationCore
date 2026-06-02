"""
Base Test Class for Playwright-based Tests
Provides browser context, page object, and session management
Supports multiple browser engines: chromium, firefox, webkit, safari

PARAMETER HANDLING
==================
All execution parameters must be passed BEFORE pytest command:

    TEST_ENV=test BROWSER=firefox DEVICE=iphone pytest tests/ -v

Environment Parameters (passed BEFORE pytest):
- TEST_ENV (required): test, preprod, or prod
- BROWSER (optional): chromium, firefox, webkit, or safari (default: chromium)
- DEVICE (optional): desktop, iphone, android, or model name (default: desktop)
- SKIP_2FA (optional): true or false (default: true for test/preprod)
- SESSION_DIR (optional): External session storage directory
- RECORD_VIDEO (optional): true or false (default: true)
- CAPTURE_SCREENSHOTS (optional): true or false (default: true)

Pytest Options (passed AFTER pytest command):
- -v, --verbose: Verbose output
- -k PATTERN: Filter tests by pattern
- -m MARKER: Filter tests by marker
- -n auto: Run in parallel (requires pytest-xdist)
- --alluredir=PATH: Generate Allure reports
- --tb=short: Short traceback format

Example Commands:
    # Basic execution with environment variable
    TEST_ENV=test pytest tests/

    # With multiple parameters and pytest options
    TEST_ENV=test BROWSER=firefox DEVICE=iphone pytest tests/ -v -k "login" --tb=short

    # Parallel execution with Allure reporting
    TEST_ENV=test pytest -n auto --alluredir=./allure-results tests/

    # Full specification with all parameters
    TEST_ENV=test BROWSER=webkit DEVICE=iphone_14 SKIP_2FA=true \\
        RECORD_VIDEO=true CAPTURE_SCREENSHOTS=true \\
        pytest tests/ -v --alluredir=./allure-results -m smoke
"""

import logging
import os
from pathlib import Path
from typing import Optional

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from refua_core.config.environment import get_env_manager, validate_environment, EnvironmentManager

logger = logging.getLogger(__name__)


class BaseTest:
    """
    Base test class for all Playwright-based tests.

    Provides:
    - Multi-browser support (chromium, firefox, webkit, safari)
    - Browser lifecycle management (setup/teardown)
    - Session validation before tests
    - Page object management
    - Playwright context and page access
    - Environment configuration
    - Parameter handling and logging

    PARAMETER USAGE:
    ================

    Browser Selection (BROWSER environment variable):
        BROWSER=chromium (default)
        BROWSER=firefox
        BROWSER=webkit
        BROWSER=safari (macOS only)

    Device Selection (DEVICE environment variable):
        DEVICE=desktop (default)
        DEVICE=iphone
        DEVICE=iphone_14
        DEVICE=android
        DEVICE=android_pixel

    2FA Bypass (SKIP_2FA environment variable):
        SKIP_2FA=true (default for test/preprod)
        SKIP_2FA=false (forces real credentials)

    Session Management (SESSION_DIR environment variable):
        SESSION_DIR=~/.refua_sessions (default)
        SESSION_DIR=/sessions (Docker)
        SESSION_DIR=/custom/path

    Artifact Recording (RECORD_VIDEO, CAPTURE_SCREENSHOTS):
        RECORD_VIDEO=true (default)
        CAPTURE_SCREENSHOTS=true (default)

    USAGE EXAMPLES:
    ===============

    Basic test execution:
        TEST_ENV=test pytest tests/

    With specific browser:
        BROWSER=firefox TEST_ENV=test pytest tests/

    With mobile device:
        DEVICE=iphone TEST_ENV=test pytest tests/

    With pytest verbose output and filtering:
        TEST_ENV=test pytest -v -k "login" tests/

    Full parameter specification:
        TEST_ENV=test BROWSER=webkit DEVICE=iphone_14 SKIP_2FA=true \\
            pytest tests/ -v --alluredir=./allure-results

    Parallel execution:
        TEST_ENV=test pytest -n auto tests/

    All parameters together:
        TEST_ENV=test BROWSER=chrome DEVICE=iphone SKIP_2FA=true \\
            SESSION_DIR=~/.refua_sessions RECORD_VIDEO=true \\
            CAPTURE_SCREENSHOTS=true \\
            pytest -v -n auto --alluredir=./allure-results -m smoke tests/

    Test Instance Attributes:
        self.page          - Playwright page object (for interactions)
        self.context       - Playwright browser context
        self.browser       - Playwright browser instance
        self.env_mgr       - Environment manager (for base URL, credentials)
        self.browser_type  - Current browser type name (for conditionals)

    Test Methods:
        self.goto(path)                 - Navigate to path
        self.wait_for_url(path)         - Wait for URL navigation
        self.is_production()            - Check if production environment
        self.can_bypass_2fa()           - Check 2FA bypass availability
        self.get_browser_name()         - Get current browser type
        self.take_screenshot(name)      - Capture screenshot
    """

    browser: Browser
    context: BrowserContext
    page: Page
    env_mgr = None
    browser_type: str = "chromium"

    @staticmethod
    def get_browser_type() -> str:
        """Get browser type from BROWSER env var (delegates to EnvironmentManager)."""
        return EnvironmentManager.get_browser_type()

    @staticmethod
    def log_execution_parameters():
        """
        Log all test execution parameters for visibility.

        Ensures that all environment variables and configuration options
        are visible in test logs for debugging and auditing.
        """
        logger.info("=" * 80)
        logger.info("TEST EXECUTION PARAMETERS")
        logger.info("=" * 80)

        # Environment parameters
        params = {
            "TEST_ENV": os.getenv("TEST_ENV", "NOT SET"),
            "BROWSER": os.getenv("BROWSER", "chromium (default)"),
            "DEVICE": os.getenv("DEVICE", "desktop (default)"),
            "SKIP_2FA": os.getenv("SKIP_2FA", "true (default for test/preprod)"),
            "SESSION_DIR": os.getenv("SESSION_DIR", "~/.refua_sessions (default)"),
            "RECORD_VIDEO": os.getenv("RECORD_VIDEO", "true (default)"),
            "CAPTURE_SCREENSHOTS": os.getenv("CAPTURE_SCREENSHOTS", "true (default)"),
        }

        logger.info("Environment Variables:")
        for key, value in params.items():
            logger.info(f"  {key:20s} = {value}")

        logger.info("=" * 80)

    @pytest.fixture(autouse=True)
    def setup_browser(self):
        """
        Setup browser context and page before each test.
        Called automatically before each test method.
        Supports multiple browser engines.

        Steps:
        1. Validate environment variables and configuration
        2. Log all execution parameters for visibility
        3. Initialize environment manager
        4. Get browser type from BROWSER environment variable
        5. Launch browser instance
        6. Create browser context with session (if available)
        7. Create page object
        8. Yield to test execution
        9. Clean up resources after test
        """
        try:
            validate_environment()
        except Exception as e:
            pytest.fail(f"Environment validation failed: {e}")

        # Log all execution parameters at test start
        self.log_execution_parameters()

        # Initialize environment manager
        self.env_mgr = get_env_manager()

        # Get browser type from environment
        self.browser_type = self.get_browser_type()
        logger.info(f"✓ Using browser: {self.browser_type}")

        # Create playwright browser
        with sync_playwright() as p:
            # Get the appropriate browser launcher
            browser_launcher = getattr(p, self.browser_type)
            self.browser = browser_launcher.launch(headless=False)
            logger.info(f"✓ Browser launched: {self.browser_type}")

            # Create context with session state if available
            session_file = self.env_mgr.get_session_file_path()
            context_kwargs = {}

            # Log session/authentication information
            if self.env_mgr.should_bypass_2fa():
                logger.info(f"✓ 2FA bypass enabled (SKIP_2FA=true)")
                if session_file.exists():
                    context_kwargs["storage_state"] = str(session_file)
                    logger.info(f"✓ Session loaded from: {session_file}")
                else:
                    logger.warning(f"⚠ Session file not found: {session_file}")
                    logger.warning(f"  Run: python scripts/capture_session.py --env {self.env_mgr.current_env.value}")
            else:
                logger.info(f"✓ 2FA bypass disabled (SKIP_2FA=false) - using credentials from .env")

            # Log device information
            device = os.getenv("DEVICE", "desktop")
            logger.info(f"✓ Device: {device}")

            # Log recording settings
            record_video = os.getenv("RECORD_VIDEO", "true").lower() == "true"
            capture_screenshots = os.getenv("CAPTURE_SCREENSHOTS", "true").lower() == "true"
            logger.info(f"✓ Recording: video={record_video}, screenshots={capture_screenshots}")

            # Create browser context
            self.context = self.browser.new_context(**context_kwargs)
            self.page = self.context.new_page()

            logger.info(f"✓ Browser context created for {self.env_mgr.current_env.value} environment")
            logger.info("=" * 80)

            yield

            # Cleanup after test
            logger.info("Cleaning up browser resources...")
            self.page.close()
            self.context.close()
            self.browser.close()

            logger.info("✓ Browser context cleaned up")

    def goto(self, path: str, **kwargs):
        """
        Navigate to a page relative to base URL.

        Args:
            path: Relative path (e.g., '/login', '/dashboard')
            **kwargs: Additional arguments for page.goto()

        Example:
            self.goto("/login")
        """
        base_url = self.env_mgr.get_base_url()
        full_url = f"{base_url}{path}"
        logger.debug(f"Navigating to: {full_url}")
        return self.page.goto(full_url, **kwargs)

    def wait_for_url(self, path: str, timeout: int = 30000):
        """
        Wait for page to navigate to a specific URL path.

        Args:
            path: Relative path to wait for
            timeout: Maximum time to wait in milliseconds

        Example:
            self.wait_for_url("/dashboard")
        """
        base_url = self.env_mgr.get_base_url()
        full_url = f"{base_url}{path}"
        logger.debug(f"Waiting for navigation to: {full_url}")
        self.page.wait_for_url(full_url, timeout=timeout)

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.env_mgr.is_production()

    def can_bypass_2fa(self) -> bool:
        """Check if 2FA can be bypassed"""
        return self.env_mgr.should_bypass_2fa()

    def get_session_dir(self) -> Path:
        """Get external session storage directory"""
        return self.env_mgr.get_session_dir()

    def take_screenshot(self, name: str) -> str:
        """
        Take a screenshot of the current page.

        Args:
            name: Screenshot filename (without extension)

        Returns:
            Path to saved screenshot
        """
        artifacts_dir = Path("test-artifacts") / self.__class__.__name__
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = artifacts_dir / f"{name}.png"
        self.page.screenshot(path=screenshot_path)
        logger.debug(f"Screenshot saved: {screenshot_path}")
        return str(screenshot_path)

    def get_browser_name(self) -> str:
        """
        Get current browser type name.

        Returns:
            Browser type: chromium, firefox, webkit, or safari

        Example:
            if self.get_browser_name() == "firefox":
                # Firefox-specific handling
        """
        return self.browser_type
