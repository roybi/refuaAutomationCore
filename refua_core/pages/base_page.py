"""Base page object for inheritance by test page objects."""

from playwright.sync_api import Page
from refua_core.config.environment import get_env_manager


class BasePage:
    """Base page object for Page Object Model (POM) pattern.

    Provides common methods for all page objects:
    - Navigation with environment awareness
    - URL waiting
    - Common locator patterns

    Usage in test repository (refuaAutomationTests):
        from refua_core.pages.base_page import BasePage

        class LoginPage(BasePage):
            def __init__(self, page: Page):
                super().__init__(page)
                self.email_input = page.locator("[data-testid='email']")
                self.password_input = page.locator("[data-testid='password']")

            def login(self, email: str, password: str):
                self.email_input.fill(email)
                self.password_input.fill(password)
                self.login_button.click()
    """

    def __init__(self, page: Page):
        """Initialize page object with Playwright page instance.

        Args:
            page: Playwright Page object from browser context
        """
        self.page = page

    def goto(self, path: str, **kwargs):
        """Navigate to path on current environment.

        Automatically prepends the base URL for the current TEST_ENV.

        Args:
            path: Path relative to base URL (e.g., "/login", "/dashboard")
            **kwargs: Additional arguments passed to page.goto()

        Example:
            page.goto("/login")  # Navigates to https://app.test.env/login
        """
        env_mgr = get_env_manager()
        full_url = f"{env_mgr.get_base_url()}{path}"
        self.page.goto(full_url, **kwargs)

    def wait_for_url(self, path: str, timeout: int = 30000):
        """Wait for URL navigation to complete.

        Args:
            path: Expected path relative to base URL
            timeout: Maximum time to wait in milliseconds (default: 30000)

        Example:
            page.wait_for_url("/dashboard")  # Waits for dashboard URL
        """
        env_mgr = get_env_manager()
        full_url = f"{env_mgr.get_base_url()}{path}"
        self.page.wait_for_url(full_url, timeout=timeout)

    def is_visible(self, selector: str) -> bool:
        """Check if element is visible on page.

        Args:
            selector: CSS selector for the element

        Returns:
            True if element is visible, False otherwise
        """
        return self.page.locator(selector).is_visible()

    def get_text(self, selector: str) -> str:
        """Get text content of element.

        Args:
            selector: CSS selector for the element

        Returns:
            Text content of the element
        """
        return self.page.locator(selector).text_content()

    def screenshot(self, name: str = "page") -> bytes:
        """Capture screenshot of current page.

        Args:
            name: Name for screenshot (used by artifact manager)

        Returns:
            Screenshot as bytes
        """
        return self.page.screenshot()
