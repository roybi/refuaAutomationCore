"""Base test class for Playwright-based tests."""

import logging
import os
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from refua_core.config.environment import get_env_manager, validate_environment, EnvironmentManager

logger = logging.getLogger(__name__)


class BaseTest:
    """Base class for all Playwright tests.

    Provides browser lifecycle, session loading, and common navigation helpers.

    Instance attributes (available inside tests):
        self.page          - Playwright Page
        self.context       - Playwright BrowserContext
        self.browser       - Playwright Browser
        self.env_mgr       - EnvironmentManager
        self.browser_type  - current browser name
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

    @pytest.fixture(autouse=True)
    def setup_browser(self):
        """Set up browser, context, and page before each test; tear down after."""
        try:
            validate_environment()
        except Exception as e:
            pytest.fail(f"Environment validation failed: {e}")

        self.env_mgr = get_env_manager()
        self.browser_type = self.get_browser_type()
        logger.info("Browser: %s | Env: %s", self.browser_type, self.env_mgr.current_env.value)

        with sync_playwright() as p:
            browser_launcher = getattr(p, self.browser_type)
            self.browser = browser_launcher.launch(headless=False)

            context_kwargs = {}
            session_file = self.env_mgr.get_session_file_path()
            if self.env_mgr.should_bypass_2fa():
                if session_file.exists():
                    context_kwargs["storage_state"] = str(session_file)
                    logger.info("Session loaded: %s", session_file)
                else:
                    logger.warning("Session file not found: %s", session_file)

            self.context = self.browser.new_context(**context_kwargs)
            self.page = self.context.new_page()

            yield

            self.page.close()
            self.context.close()
            self.browser.close()

    def goto(self, path: str, **kwargs):
        """Navigate to a path relative to the current environment's base URL."""
        return self.page.goto(f"{self.env_mgr.get_base_url()}{path}", **kwargs)

    def wait_for_url(self, path: str, timeout: int = 30000):
        """Wait for navigation to a path relative to the base URL."""
        self.page.wait_for_url(f"{self.env_mgr.get_base_url()}{path}", timeout=timeout)

    def is_production(self) -> bool:
        return self.env_mgr.is_production()

    def can_bypass_2fa(self) -> bool:
        return self.env_mgr.should_bypass_2fa()

    def get_session_dir(self) -> Path:
        return self.env_mgr.get_session_dir()

    def take_screenshot(self, name: str) -> str:
        """Save a screenshot and return its path."""
        artifacts_dir = Path("test-artifacts") / self.__class__.__name__
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = artifacts_dir / f"{name}.png"
        self.page.screenshot(path=path)
        return str(path)

    def get_browser_name(self) -> str:
        return self.browser_type
