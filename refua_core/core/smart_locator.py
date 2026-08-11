"""
Smart locator with multi-strategy fallback resolution.

Priority order (lower = tried first):
  TEST_ID → XPATH → ROLE → LABEL → PLACEHOLDER → ALT_TEXT → CSS → TEXT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from playwright.sync_api import Locator, Page

logger = logging.getLogger(__name__)

# Fixed resolution priority — TEST_ID first, TEXT last
_PRIORITY: dict[str, int] = {
    "test_id":     0,
    "xpath":       1,
    "role":        2,
    "label":       3,
    "placeholder": 4,
    "alt_text":    5,
    "css":         6,
    "text":        7,
}

_DEFAULT_TIMEOUT_MS = 5000


class LocatorType(str, Enum):
    """Supported locator strategies."""

    TEST_ID     = "test_id"
    XPATH       = "xpath"
    CSS         = "css"
    TEXT        = "text"
    ROLE        = "role"
    LABEL       = "label"
    PLACEHOLDER = "placeholder"
    ALT_TEXT    = "alt_text"


class LocatorResolutionError(Exception):
    """Raised when no strategy successfully locates the element."""


@dataclass
class LocatorDefinition:
    """A single locator strategy with an optional human-readable description."""

    locator_type: LocatorType
    value: str
    description: str = ""

    def __str__(self) -> str:
        suffix = f" ({self.description})" if self.description else ""
        return f"{self.locator_type.value}={self.value!r}{suffix}"


@dataclass
class SmartLocator:
    """
    Multi-strategy locator that tries each definition in priority order and
    returns the first Playwright Locator that matches ≥ 1 element on the page.

    Priority (fixed): TEST_ID → XPATH → ROLE → LABEL → PLACEHOLDER → ALT_TEXT → CSS → TEXT

    Example::

        button = SmartLocator("login-button", [
            LocatorDefinition(LocatorType.TEST_ID, "login-button"),
            LocatorDefinition(LocatorType.XPATH,   "//button[@id='login-button']"),
            LocatorDefinition(LocatorType.CSS,      "#login-button"),
        ])

        # In a page object or test:
        button.resolve(page).click()
    """

    name: str
    locators: List[LocatorDefinition] = field(default_factory=list)
    timeout: int = _DEFAULT_TIMEOUT_MS

    def resolve(self, page: Page) -> Locator:
        """Return the first Locator whose strategy finds ≥ 1 element on *page*.

        Strategies are tried in fixed priority order regardless of the order
        they were added to *locators*.

        Raises:
            LocatorResolutionError: when every strategy finds 0 elements.
        """
        sorted_defs = sorted(
            self.locators,
            key=lambda d: _PRIORITY.get(d.locator_type.value, 99),
        )

        attempts: list[str] = []
        for defn in sorted_defs:
            try:
                loc = _build_locator(page, defn)
                count = loc.count()
                if count > 0:
                    logger.debug(
                        "[SmartLocator:%s] resolved via %s (%d element(s))",
                        self.name, defn, count,
                    )
                    return loc
                attempts.append(f"  {defn} → 0 elements found")
            except Exception as exc:
                attempts.append(f"  {defn} → error: {exc}")

        raise LocatorResolutionError(
            f"SmartLocator '{self.name}': no strategy matched an element.\n"
            + "\n".join(attempts)
        )

    def __str__(self) -> str:
        strategies = ", ".join(str(d) for d in self.locators)
        return f"SmartLocator(name={self.name!r}, strategies=[{strategies}])"


# ── Internal builder ───────────────────────────────────────────────────────────

def _build_locator(page: Page, defn: LocatorDefinition) -> Locator:
    """Convert a LocatorDefinition into a Playwright Locator."""
    t, v = defn.locator_type, defn.value

    if t == LocatorType.TEST_ID:
        return page.get_by_test_id(v)

    if t == LocatorType.XPATH:
        return page.locator(f"xpath={v}")

    if t == LocatorType.CSS:
        return page.locator(v)

    if t == LocatorType.TEXT:
        return page.get_by_text(v, exact=False)

    if t == LocatorType.ROLE:
        # value format: "role" or "role:accessible-name"  e.g. "button:Login"
        parts = v.split(":", 1)
        role = parts[0]
        name = parts[1] if len(parts) > 1 else None
        return (
            page.get_by_role(role, name=name)  # type: ignore[arg-type]
            if name
            else page.get_by_role(role)  # type: ignore[arg-type]
        )

    if t == LocatorType.LABEL:
        return page.get_by_label(v)

    if t == LocatorType.PLACEHOLDER:
        return page.get_by_placeholder(v)

    if t == LocatorType.ALT_TEXT:
        return page.get_by_alt_text(v)

    raise ValueError(f"Unsupported locator type: {t!r}")
