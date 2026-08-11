"""BaseTest — lightweight base class for unit tests that do not require a browser.

Use this when your tests only need to verify:
  - URL construction / environment resolution
  - Page object attribute / method existence
  - Business logic that doesn't interact with the DOM

For tests that DO open a browser, inherit from BasePage instead:

    class TestHomePage(BasePage):          # real browser, setup_browser fixture
        def test_title(self):
            self.page.goto(...)

For pure unit / structural tests (no browser):

    class TestMainPageUnit(BaseTest):      # mock page, no browser
        def test_url_resolution(self):
            page_obj = MainPage(self.page)
            assert "test.medical.idf.il" in page_obj.items_base_url
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


class BaseTest:
    """Base class for unit tests that do not require a real browser.

    Provides ``self.page`` as a :class:`unittest.mock.MagicMock` so that
    page objects can be instantiated and their structure verified without
    launching a Playwright browser.

    Lifecycle hooks match both pytest (*setup_method* / *teardown_method*)
    and unittest-style (*setUp* / *tearDown*) so either naming convention
    works in subclasses.
    """

    page: Any = None

    # ── pytest lifecycle ──────────────────────────────────────────────────────

    def setup_method(self, method=None) -> None:
        """Called by pytest before each test method."""
        self.page = _make_mock_page()
        self.setUp()

    def teardown_method(self, method=None) -> None:
        """Called by pytest after each test method."""
        self.tearDown()

    # ── unittest-compatible hooks (call super() from subclasses) ──────────────

    def setUp(self) -> None:
        """Override in subclasses for additional per-test setup."""

    def tearDown(self) -> None:
        """Override in subclasses for additional per-test cleanup."""


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_mock_page() -> MagicMock:
    """Return a MagicMock that behaves enough like a Playwright Page.

    ``page.locator(selector)`` returns a child mock, so page object
    ``__init__`` methods that eagerly build locators won't raise.
    """
    mock_page = MagicMock(name="MockPage")

    # Each locator() call returns its own unique mock — consistent with
    # Playwright's lazy-evaluation model.
    mock_page.locator.side_effect = lambda selector, **kw: MagicMock(
        name=f"Locator({selector!r})"
    )
    mock_page.get_by_test_id.side_effect = lambda v, **kw: MagicMock(
        name=f"TestId({v!r})"
    )
    mock_page.get_by_role.side_effect = lambda r, **kw: MagicMock(
        name=f"Role({r!r})"
    )
    mock_page.get_by_text.side_effect = lambda t, **kw: MagicMock(
        name=f"Text({t!r})"
    )
    mock_page.get_by_label.side_effect = lambda l, **kw: MagicMock(
        name=f"Label({l!r})"
    )
    mock_page.get_by_alt_text.side_effect = lambda a, **kw: MagicMock(
        name=f"AltText({a!r})"
    )
    mock_page.get_by_placeholder.side_effect = lambda p, **kw: MagicMock(
        name=f"Placeholder({p!r})"
    )

    return mock_page
