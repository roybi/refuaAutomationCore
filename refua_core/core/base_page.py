"""Base page object for the Page Object Model pattern."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import (Browser, BrowserContext, Locator, Page,
                                 sync_playwright)

from refua_core.config.environment import (EnvironmentManager, get_env_manager,
                                           validate_environment)

if TYPE_CHECKING:
    from refua_core.core.smart_locator import SmartLocator

logger = logging.getLogger(__name__)


class BasePage:
    """Base class for all page objects and test classes.

    As a page object base (POM):
        class LoginPage(BasePage):
            def __init__(self, page: Page):
                super().__init__(page)

    As a test base:
        class TestLogin(BasePage):
            def test_something(self):
                self.goto("/login")
    """

    browser: Browser
    context: BrowserContext
    page: Page
    env_mgr = None
    browser_type: str = "chromium"

    def __init__(self, page: Page = None):
        self.page = page
        self.env_mgr = get_env_manager()

    @staticmethod
    def get_browser_type() -> str:
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
        """Navigate to path on the current environment's base URL."""
        return self.page.goto(f"{self.env_mgr.get_base_url()}{path}", **kwargs)

    def wait_for_url(self, path: str, timeout: int = 30000):
        """Wait for navigation to a path relative to the base URL."""
        self.page.wait_for_url(f"{self.env_mgr.get_base_url()}{path}", timeout=timeout)

    def is_visible(self, selector: str) -> bool:
        return self.page.locator(selector).is_visible()

    def get_text(self, selector: str) -> str :
        return self.page.locator(selector).text_content()

    def take_screenshot(self, name: str) -> str:
        """Save a screenshot and return its file path."""
        artifacts_dir = Path("test-artifacts") / self.__class__.__name__
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = artifacts_dir / f"{name}.png"
        self.page.screenshot(path=path)
        return str(path)

    def is_production(self) -> bool:
        return self.env_mgr.is_production()

    def can_bypass_2fa(self) -> bool:
        return self.env_mgr.should_bypass_2fa()

    def get_session_dir(self) -> Path:
        return self.env_mgr.get_session_dir()

    def get_browser_name(self) -> str:
        return self.browser_type

    def locate(self, smart_locator: SmartLocator) -> Locator:
        """Resolve a SmartLocator against the current page.

        Tries each strategy in priority order (TEST_ID → XPATH → … → TEXT)
        and returns the first Playwright Locator that matches ≥ 1 element.

        Example::

            el = self.locate(self.LOGIN_BUTTON)
            el.click()
        """
        return smart_locator.resolve(self.page)
