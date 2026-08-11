from playwright.sync_api import Page

from refua_core.core.base_page import BasePage
from refua_core.core.smart_locator import LocatorDefinition, LocatorType, SmartLocator


class homePage(BasePage):
    """Page object for the MEDITEK Home / Login screen.

    URL: https://meditik.test.medical.idf.il/home

    Locator resolution priority per element (handled by SmartLocator):
      1. TEST_ID  — ``data-testid`` attribute  (preferred; add to DOM as devs instrument the app)
      2. XPATH    — id / structural path        (current primary for un-instrumented elements)
      3. CSS / TEXT / ROLE                      (last resort)

    Usage::

        page_obj = homePage(page)

        # Resolve a SmartLocator to a Playwright Locator and act on it:
        page_obj.locate(page_obj.LOGIN_BUTTON).click()

        # Or use the convenience action methods:
        page_obj.click_login()
    """

    PAGE_URL = "https://meditik.test.medical.idf.il/home"
    PAGE_NAME = "HomePage"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._define_locators()

    # ── Locator definitions ───────────────────────────────────────────────────

    def _define_locators(self) -> None:
        """Initialise SmartLocator instances for every element on this page.

        Real DOM (captured 2026-06-30):
          - No data-testid attributes on this page yet (except CloseIcon inside PWA dialog)
          - Stable IDs: login-page-title, login-page-subtitle, login-button, link-to-myidf
          - Images: no id/testid — identified via src / alt attributes
          - All buttons are MUI: type="button", identifiable by role+text as last resort
        """

        # ── Branding / background images ──────────────────────────────────────
        # No id or testid; src is the most reliable selector.
        self.MAIN_LOGO = SmartLocator("main-logo", [
            LocatorDefinition(LocatorType.TEST_ID, "login-page-logo",
                              "aspirational — add data-testid when app is instrumented"),
            LocatorDefinition(LocatorType.XPATH,
                              "//img[@src='icons/login-page-logo.svg']"),
            LocatorDefinition(LocatorType.CSS,
                              "img[src='icons/login-page-logo.svg']"),
        ])

        self.TOP_LEFT_DECORATION = SmartLocator("top-left-decoration", [
            LocatorDefinition(LocatorType.TEST_ID, "top-left-decoration"),
            LocatorDefinition(LocatorType.XPATH,
                              "//img[@src='icons/top-left.svg']"),
            LocatorDefinition(LocatorType.CSS,
                              "img[src='icons/top-left.svg']"),
        ])

        # ── Login card ────────────────────────────────────────────────────────
        # img has alt="icon"; src contains "login-icon"
        self.LOGIN_CARD_ICON = SmartLocator("login-card-icon", [
            LocatorDefinition(LocatorType.TEST_ID, "login-icon"),
            LocatorDefinition(LocatorType.XPATH,
                              "//img[@alt='icon' and contains(@src,'login-icon')]"),
            LocatorDefinition(LocatorType.ALT_TEXT, "icon"),
        ])

        # h4#login-page-title  — text: "כניסה למערכת"
        self.LOGIN_TITLE = SmartLocator("login-title", [
            LocatorDefinition(LocatorType.TEST_ID, "login-page-title"),
            LocatorDefinition(LocatorType.XPATH,
                              "//h4[@id='login-page-title']"),
            LocatorDefinition(LocatorType.TEXT, "כניסה למערכת"),
        ])

        # p#login-page-subtitle — text: "לפני שממשיכים..."
        self.LOGIN_SUBTITLE = SmartLocator("login-subtitle", [
            LocatorDefinition(LocatorType.TEST_ID, "login-page-subtitle"),
            LocatorDefinition(LocatorType.XPATH,
                              "//p[@id='login-page-subtitle']"),
            LocatorDefinition(LocatorType.CSS, "#login-page-subtitle"),
        ])

        # button#login-button — text: "התחברות"
        self.LOGIN_BUTTON = SmartLocator("login-button", [
            LocatorDefinition(LocatorType.TEST_ID, "login-button",
                              "aspirational — add data-testid when app is instrumented"),
            LocatorDefinition(LocatorType.XPATH,
                              "//button[@id='login-button']",
                              "id attribute via xpath"),
            LocatorDefinition(LocatorType.ROLE, "button:התחברות",
                              "role + accessible name fallback"),
        ])

        # button#link-to-myidf — text: "הרשמה כאן!"
        self.REGISTER_MYIDF_BUTTON = SmartLocator("register-myidf-button", [
            LocatorDefinition(LocatorType.TEST_ID, "link-to-myidf"),
            LocatorDefinition(LocatorType.XPATH,
                              "//button[@id='link-to-myidf']"),
            LocatorDefinition(LocatorType.ROLE, "button:הרשמה כאן!"),
        ])

        # ── PWA install dialog (shown conditionally on first visit) ───────────
        # div#download-pwa
        self.PWA_DIALOG = SmartLocator("pwa-dialog", [
            LocatorDefinition(LocatorType.TEST_ID, "download-pwa"),
            LocatorDefinition(LocatorType.XPATH,
                              "//div[@id='download-pwa']"),
            LocatorDefinition(LocatorType.CSS, "div#download-pwa"),
        ])

        # Close button — MUI CloseIcon has data-testid="CloseIcon" (confirmed in DOM)
        self.PWA_DIALOG_CLOSE_BUTTON = SmartLocator("pwa-dialog-close", [
            LocatorDefinition(LocatorType.TEST_ID, "CloseIcon",
                              "confirmed in DOM — MUI SvgIcon has data-testid"),
            LocatorDefinition(LocatorType.XPATH,
                              "//button[.//*[@data-testid='CloseIcon']]",
                              "button ancestor of the CloseIcon"),
            LocatorDefinition(LocatorType.CSS,
                              "button:has([data-testid='CloseIcon'])"),
        ])

        # img[src*='download.png'] — no id/testid
        self.PWA_DIALOG_ICON = SmartLocator("pwa-dialog-icon", [
            LocatorDefinition(LocatorType.TEST_ID, "pwa-download-icon"),
            LocatorDefinition(LocatorType.XPATH,
                              "//img[contains(@src,'download.png')]"),
            LocatorDefinition(LocatorType.CSS,
                              "img[src*='download.png']"),
        ])

        # h4 with text "כל המידע הרפואי" — no id
        self.PWA_DIALOG_TITLE = SmartLocator("pwa-dialog-title", [
            LocatorDefinition(LocatorType.TEST_ID, "pwa-dialog-title"),
            LocatorDefinition(LocatorType.XPATH,
                              "//h4[contains(.,'כל המידע הרפואי')]"),
            LocatorDefinition(LocatorType.TEXT, "כל המידע הרפואי"),
        ])

        # button#download-pwa — text: "הוספה למסך הבית"
        self.PWA_ADD_TO_HOME_BUTTON = SmartLocator("pwa-add-to-home", [
            LocatorDefinition(LocatorType.TEST_ID, "pwa-add-to-home-button"),
            LocatorDefinition(LocatorType.XPATH,
                              "//button[@id='download-pwa']"),
            LocatorDefinition(LocatorType.ROLE, "button:הוספה למסך הבית"),
        ])

        # input[type='checkbox'] — "אל תציג לי הודעה זו שוב"
        self.PWA_DONT_SHOW_CHECKBOX = SmartLocator("pwa-dont-show-checkbox", [
            LocatorDefinition(LocatorType.TEST_ID, "pwa-dont-show-checkbox"),
            LocatorDefinition(LocatorType.XPATH,
                              "//div[@id='download-pwa']//input[@type='checkbox']",
                              "scoped to the PWA dialog to avoid ambiguity"),
            LocatorDefinition(LocatorType.CSS,
                              "div#download-pwa input[type='checkbox']"),
        ])

    # ── Convenience action methods ────────────────────────────────────────────

    def click_login(self) -> None:
        """Click the main login / SSO button (התחברות)."""
        self.locate(self.LOGIN_BUTTON).click()

    def click_register_myidf(self) -> None:
        """Click the MyIDF registration link (הרשמה כאן!)."""
        self.locate(self.REGISTER_MYIDF_BUTTON).click()

    def get_login_title_text(self) -> str:
        """Return the text content of the login card title."""
        return self.locate(self.LOGIN_TITLE).text_content() or ""

    def is_pwa_dialog_visible(self) -> bool:
        """Return True if the PWA install dialog is currently shown."""
        try:
            return self.locate(self.PWA_DIALOG).is_visible()
        except Exception:
            return False

    def close_pwa_dialog(self) -> None:
        """Close the PWA install dialog if it is visible."""
        if self.is_pwa_dialog_visible():
            self.locate(self.PWA_DIALOG_CLOSE_BUTTON).click()

    def dismiss_pwa_and_dont_show_again(self) -> None:
        """Tick 'do not show again' and close the PWA dialog."""
        if self.is_pwa_dialog_visible():
            self.locate(self.PWA_DONT_SHOW_CHECKBOX).check()
            self.locate(self.PWA_DIALOG_CLOSE_BUTTON).click()

