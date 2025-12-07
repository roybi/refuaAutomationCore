"""
Base Test Class for Playwright-based Tests
Provides browser context, page object, and session management
Supports multiple browser engines: chromium, firefox, webkit, safari
"""

import logging
import os
from pathlib import Path
from typing import Optional

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from refua_core.config.environment import get_env_manager, validate_environment

logger = logging.getLogger(__name__)

# Supported browser types
SUPPORTED_BROWSERS = ["chromium", "firefox", "webkit", "safari"]


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

    Browser Selection:
    1. BROWSER environment variable (chromium, firefox, webkit, safari)
    2. Default: chromium

    Usage:
        # Using default chromium browser
        class TestLogin(BaseTest):
            def test_user_can_login(self):
                # self.page is available
                # self.env_mgr is available
                # Browser context is automatically managed

        # Run with different browser:
        # BROWSER=firefox TEST_ENV=test pytest
        # BROWSER=webkit TEST_ENV=test pytest
    """

    browser: Browser
    context: BrowserContext
    page: Page
    env_mgr = None
    browser_type: str = "chromium"

    @staticmethod
    def get_browser_type() -> str:
        """
        Get browser type from environment or use default.

        Priority:
        1. BROWSER environment variable
        2. Default: chromium

        Returns:
            Browser type: chromium, firefox, webkit, or safari
        """
        browser = os.getenv("BROWSER", "chromium").lower().strip()

        if browser not in SUPPORTED_BROWSERS:
            logger.warning(
                f"Unsupported browser: {browser}. "
                f"Supported: {SUPPORTED_BROWSERS}. Using chromium."
            )
            return "chromium"

        return browser

    @pytest.fixture(autouse=True)
    def setup_browser(self):
        """
        Setup browser context and page before each test.
        Called automatically before each test method.
        Supports multiple browser engines.
        """
        try:
            validate_environment()
        except Exception as e:
            pytest.fail(f"Environment validation failed: {e}")

        # Initialize environment manager
        self.env_mgr = get_env_manager()

        # Get browser type from environment
        self.browser_type = self.get_browser_type()
        logger.info(f"Using browser: {self.browser_type}")

        # Create playwright browser
        with sync_playwright() as p:
            # Get the appropriate browser launcher
            browser_launcher = getattr(p, self.browser_type)
            self.browser = browser_launcher.launch(headless=False)

            # Create context with session state if available
            session_file = self.env_mgr.get_session_file_path()
            context_kwargs = {}

            if session_file.exists() and self.env_mgr.should_bypass_2fa():
                context_kwargs["storage_state"] = str(session_file)
                logger.info(f"Loading session from: {session_file}")

            self.context = self.browser.new_context(**context_kwargs)
            self.page = self.context.new_page()

            logger.info(f"Browser context created for {self.env_mgr.current_env.value} environment")

            yield

            # Cleanup after test
            self.page.close()
            self.context.close()
            self.browser.close()

            logger.info("Browser context cleaned up")

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
