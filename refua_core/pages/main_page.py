from refua_core.core.base_page import BasePage
from playwright.sync_api import Page


class MainPage(BasePage):
    """Page object for the Main Dashboard (post-login). URL stays /home after auth."""
    PAGE_URL = "https://meditik.test.medical.idf.il/home"
    PAGE_NAME = "MainPage"

    def __init__(self, driver) -> None:
        super().__init__(driver)
        self.define_locators()

    def define_locators(self) -> None:
        # ── Header / Toolbar ─────────────────────────────────────────────────
        self.TOOLBAR = self.driver.locator("#main-toolbar")
        self.MENU_BUTTON = self.driver.locator("#menu-button")           # hamburger → opens side drawer
        self.NAVBAR_TABS_PORTAL = self.driver.locator("#navbar-tabs-portal")

        # ── Greeting (DYNAMIC – changes with time-of-day and logged-in user) ─
        # e.g. "ערב טוב רועי" / "בוקר טוב רועי" — no static ID on element
        self.GREETING_TEXT = self.driver.locator("p > p").first

        # ── Speed Dial – Quick-Actions FAB ────────────────────────────────────
        self.SPEED_DIAL = self.driver.locator("#speed-dial")
        self.SPEED_DIAL_BUTTON = self.driver.locator("button[aria-label='SpeedDial']")
        self.SPEED_DIAL_ACTIONS = self.driver.locator("#SpeedDial-actions")
        # Items are only visible/interactable after opening the SpeedDial (DYNAMIC)
        self.SPEED_DIAL_ACTION_PRESCRIPTION = self.driver.locator("[role='menuitem']:has-text('בקשה למרשם')")
        self.SPEED_DIAL_ACTION_REFERRAL_ANSWER = self.driver.locator("[role='menuitem']:has-text('החזרת תשובה להפניה')")
        self.SPEED_DIAL_ACTION_MEDICAL_CORPS = self.driver.locator("[role='menuitem']:has-text('פניה לברה')")
        self.SPEED_DIAL_ACTION_HEART_VOICE = self.driver.locator("[role='menuitem']:has-text('פנייה למוקד מקול הלב')")

        # ── My Requests Widget ────────────────────────────────────────────────
        self.REQUESTS_WIDGET_HEADER = self.driver.locator("#user-requests-widget-hp-header")
        self.REQUESTS_WIDGET_NAV_BTN = self.driver.locator("#user-requests-widget-hp-header button")
        # Empty-state (DYNAMIC – visible only when user has no requests)
        self.REQUESTS_EMPTY_STATE_TEXT = self.driver.locator("#user-requests-widget-empty-state-extra-info")
        self.REQUESTS_EMPTY_STATE_LINK = self.driver.locator("#emptyState-link-link")   # "שליחת בקשה לרופא"

        # ── Appointments Widget ───────────────────────────────────────────────
        self.APPOINTMENTS_WIDGET_HEADER = self.driver.locator("#future-appointments-widget-hp-header")
        self.APPOINTMENTS_WIDGET_NAV_BTN = self.driver.locator("#future-appointments-widget-hp-header button")
        # Empty-state (DYNAMIC)
        self.APPOINTMENTS_EMPTY_STATE_TEXT = self.driver.locator("#future-appointments-widget-empty-state-extra-info")
        self.APPOINTMENTS_EMPTY_STATE_LINK = self.driver.locator("text=לזימון תורים")   # "לזימון תורים"

        # ── Referrals Widget ──────────────────────────────────────────────────
        self.REFERRALS_WIDGET_HEADER = self.driver.locator("#referrals-widget-hp-header")
        self.REFERRALS_WIDGET_NAV_BTN = self.driver.locator("#referrals-widget-hp-header button")
        # Empty-state (DYNAMIC)
        self.REFERRALS_EMPTY_STATE_TEXT = self.driver.locator("#referrals-widget-empty-state-extra-info")
        self.REFERRALS_EMPTY_STATE_LINK = self.driver.locator("text=לבקשת הפניה")      # "לבקשת הפניה"

        # ── Medicines & Prescriptions Widget ──────────────────────────────────
        self.MEDICINES_WIDGET_HEADER = self.driver.locator("#medicines-widget-hp-header")
        self.MEDICINES_WIDGET_NAV_BTN = self.driver.locator("#medicines-widget-hp-header button")
        # Empty-state (DYNAMIC)
        self.MEDICINES_EMPTY_STATE_TEXT = self.driver.locator("#medicines-widget-empty-state-extra-info")
        self.MEDICINES_EMPTY_STATE_LINK = self.driver.locator("text=לבקשת מרשם")       # "לבקשת מרשם"

        # ── Exemptions Widget ─────────────────────────────────────────────────
        self.EXEMPTIONS_WIDGET_HEADER = self.driver.locator("#exemptions-home-page-hp-header")
        self.EXEMPTIONS_WIDGET_NAV_BTN = self.driver.locator("#exemptions-home-page-hp-header button")
        # Empty-state (DYNAMIC)
        self.EXEMPTIONS_EMPTY_STATE_TEXT = self.driver.locator("#exemptions-home-page-empty-state-extra-info")

        # ── Support Footer ────────────────────────────────────────────────────
        self.SUPPORT_PHONE_LINK = self.driver.locator("a[href^='tel:']")   # "*6690"

        # ── Side Drawer Menu (visible after clicking MENU_BUTTON) ─────────────
        self.SIDE_DRAWER = self.driver.locator("#main-side-drawer")
        self.DRAWER_CLOSE_BTN = self.driver.locator("#close-menu-button")
        self.DRAWER_HOME_BTN = self.driver.locator("#home-menu-button")
        # Quick-action shortcuts at top of drawer
        self.DRAWER_BOOKING_BTN = self.driver.locator("#main-side-drawer #common-action-15")    # זימון תור
        self.DRAWER_REQUEST_BTN = self.driver.locator("#main-side-drawer #common-action-29")    # בקשה
        self.DRAWER_EMERGENCY_BTN = self.driver.locator("#main-side-drawer #common-action-23")  # ברה"ן / חירום
        # Navigation menu items
        self.DRAWER_MY_QUEUES_BTN = self.driver.locator("#menu-item-1")         # התורים שלי
        self.DRAWER_REQUESTS_BTN = self.driver.locator("#menu-item-14")         # בקשות
        self.DRAWER_TEST_RESULTS_BTN = self.driver.locator("#menu-item-2")      # תוצאות בדיקות
        self.DRAWER_PRESCRIPTIONS_BTN = self.driver.locator("#menu-item-3")     # מרשמים
        self.DRAWER_SUMMARY_BTN = self.driver.locator("#menu-item-8")           # סיכום
        self.DRAWER_DISCHARGE_BTN = self.driver.locator("#menu-item-5")         # שחרור
        self.DRAWER_SICK_DAYS_BTN = self.driver.locator("#menu-item-6")         # ימי מחלה
        self.DRAWER_REFERENCES_BTN = self.driver.locator("#menu-item-4")        # הפניות
        self.DRAWER_VACCINE_BTN = self.driver.locator("#menu-item-7")           # חיסונים
        self.DRAWER_MEDICAL_PROFILE_BTN = self.driver.locator("#menu-item-12")  # פרופיל רפואי
        # Drawer utility buttons
        self.DRAWER_FEEDBACK_BTN = self.driver.locator("#feedback-button")
        self.DRAWER_INSTALL_BTN = self.driver.locator("#install-button")        # PWA install
        self.DRAWER_SHARE_BTN = self.driver.locator("#share-button")
        self.DRAWER_LOGOUT_BTN = self.driver.locator("#logout-button")
