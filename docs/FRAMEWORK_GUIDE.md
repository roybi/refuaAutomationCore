# מדריך Framework — refuaAutomationCore

## 📌 מה זה הפרויקט הזה?

**refuaAutomationCore** הוא ספריית תשתית (Framework) לאוטומציה של בדיקות עבור מערכת **MEDITEK** — מערכת רפואית צבאית.

הספרייה בנויה ב-**Python** עם **Playwright** (כלי אוטומציה לדפדפנים) ומספקת את כל התשתית הנדרשת כדי לכתוב, להריץ ולנהל בדיקות אוטומטיות על אפליקציות וב.

> **נקודה חשובה:** ה-Repository הזה מכיל **רק את התשתית** — לא את הבדיקות עצמן.
> הבדיקות נמצאות ב-Repository נפרד בשם **`refuaAutomationTests`** שמתקין את הספרייה הזו כתלות (dependency).

---

## 🏗️ ארכיטקטורה — שני Repositories

הפרויקט מחולק לשני חלקים בכוונה, כדי לאפשר הפרדת אחריות ושימוש חוזר:

```
┌─────────────────────────────────┐      ┌──────────────────────────────────┐
│  refuaAutomationCore            │      │  refuaAutomationTests            │
│  (הריפו הזה)                    │      │  (ריפו נפרד)                     │
│                                 │      │                                  │
│  ✔ EnvironmentManager           │◄─────│  ✔ קבצי בדיקות (test_*.py)       │
│  ✔ SessionStateManager          │ pip  │  ✔ Page Objects לאפליקציה         │
│  ✔ BasePage                     │      │  ✔ Fixtures                      │
│  ✔ conftest.py plugin           │      │  ✔ pytest.ini                    │
│  ✔ capture_session.py           │      │  ✔ .env קבצי credentials         │
│  ✔ devices.json                 │      │                                  │
└─────────────────────────────────┘      └──────────────────────────────────┘
```

**למה ההפרדה?**

- ✅ הספרייה יכולה לקבל גרסאות ולהתפתח בנפרד
- ✅ מספר פרויקטי בדיקות יכולים להשתמש באותה תשתית (למשל: MEDITEK + CPR-GO)
- ✅ הפרדת אחריות ברורה — מי שמפתח תשתית לא מערבב עם מי שכותב בדיקות
- ✅ ניהול תלויות (dependencies) פשוט יותר

---

## 📁 מבנה הקבצים

```
refuaAutomationCore/
│
├── refua_core/                        ← הפקג'ג הראשי שמותקן דרך pip
│   ├── __init__.py
│   ├── version.py                     ← גרסת הספרייה (1.0.0)
│   ├── conftest.py                    ← Pytest plugin — CLI options + validation
│   │
│   ├── config/                        ← קונפיגורציה וניהול סביבות
│   │   ├── environment.py             ← EnvironmentManager (Singleton)
│   │   ├── session_manager.py         ← SessionStateManager (ניהול 2FA)
│   │   └── devices.json               ← פרופילי מכשירים (iPhone, Android, Desktop)
│   │
│   ├── pages/                         ← Page Object Model
│   │   └── base_page.py               ← BasePage — מחלקת בסיס לכל הדפים ולטסטים
│   │
│   └── core/                          ← תשתית נוספת (בפיתוח)
│       └── __init__.py
│
├── scripts/
│   └── capture_session.py             ← סקריפט לכידת Session (עוקף 2FA)
│
├── setup.py                           ← הגדרות חבילה (pip install)
├── requirements.txt                   ← תלויות הספרייה
├── README.md                          ← תיעוד מהיר
├── GETTING_STARTED.md                 ← מדריך התחלה מהירה
└── CLAUDE.md                          ← תיעוד מלא לפיתוח עם AI
```

---

## 🧩 הרכיבים העיקריים — מה כל אחד עושה?

### 1. EnvironmentManager — ניהול סביבות (`config/environment.py`)

זהו הלב של הקונפיגורציה. מחלקת **Singleton** שמנהלת את כל ההגדרות לפי סביבה.

**מה הוא עושה:**

- טוען את סביבת הריצה מהמשתנה `TEST_ENV` (חובה: `test`, `preprod`, `prod`)
- מספק כתובות URL לכל סביבה (base URL, API URL)
- מנהל הגדרות אימות (2FA bypass, session timeout)
- תומך במספר אפליקציות (`TEST_APP`): כברירת מחדל MEDITEK, אבל גם CPR-GO
- מזהה אוטומטית סביבת CI/CD (GitHub Actions, Jenkins) לנתיבי session

**דוגמת שימוש:**

```python
from refua_core.config.environment import get_env_manager

env = get_env_manager()

# קבלת URL של הסביבה
base_url = env.get_base_url()        # "https://meditik.test.medical.idf.il/home"
api_url  = env.get_api_url()         # "https://meditik.test.medical.idf.il/api"

# בדיקת סביבה
env.is_production()                   # False (בסביבת test)
env.should_bypass_2fa()               # True (בסביבת test)

# מידע מלא
print(env.get_env_summary())
```

**הסביבות הנתמכות:**

| סביבה | 2FA Bypass | Session Timeout | שימוש |
|--------|------------|-----------------|-------|
| `test` | ✅ כן | 3 ימים | פיתוח ובדיקות יומיומיות |
| `preprod` | ✅ כן | 3 ימים | בדיקות לפני Production |
| `prod` | ❌ לא | 30 דקות | בדיקות על סביבה חיה |

**האפליקציות הרשומות:**

| אפליקציה | משתנה סביבה | כתובת Test |
|-----------|------------|------------|
| `meditek` (ברירת מחדל) | `TEST_APP=meditek` | `meditik.test.medical.idf.il` |
| `cpr-go` | `TEST_APP=cpr-go` | `cpr-go.test.medical.idf.il` |

> ניתן לרשום אפליקציות נוספות דרך `EnvironmentManager.register_app()`.

---

### 2. SessionStateManager — ניהול Sessions ועקיפת 2FA (`config/session_manager.py`)

מערכת MEDITEK משתמשת באימות דו-שלבי (2FA). כדי למנוע צורך באימות ידני בכל הרצת בדיקה, הרכיב הזה מנהל Sessions שמורים.

**איך זה עובד:**

```
┌──────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ 1. כידה ידנית    │────►│ 2. קובץ Session    │────►│ 3. הרצת בדיקות   │
│                  │     │    שמור בדיסק      │     │    אוטומטית      │
│ המשתמש מתחבר     │     │                   │     │                  │
│ פעם אחת ידנית   │     │ cookies +          │     │ Session נטען     │
│ ומשלים 2FA      │     │ localStorage +     │     │ אוטומטית לדפדפן  │
│                  │     │ metadata           │     │ → ללא 2FA!       │
│ תוקף: 3 ימים    │     │                   │     │                  │
└──────────────────┘     └───────────────────┘     └──────────────────┘
```

**תכונות עיקריות:**

- **טעינה ואימות:** טוען קובץ session, מוודא שלא פג תוקף (TTL של 3 ימים)
- **הזרקת Cookies:** מזריק cookies שמורים ל-Browser Context של Playwright
- **הזרקת localStorage:** מחיל localStorage אחרי ניווט לדף (חייב להיות אחרי `goto`)
- **שמירת Session חדש:** שומר את המצב הנוכחי של הדפדפן לקובץ JSON
- **בדיקת אימות:** בודק אם הדף נראה כמחובר (מחפש אלמנטי UI של משתמש מחובר)

**קבצי Session נשמרים מחוץ לפרויקט:**

```
~/.refua_sessions/
├── auth_state_meditek_test_chromium_latest.json
├── auth_state_meditek_test_firefox_latest.json
├── auth_state_meditek_preprod_chromium_latest.json
├── auth_state_cpr-go_test_chromium_latest.json
└── ...
```

**מבנה קובץ Session:**

```json
{
  "storage_state": {
    "cookies": [ { "name": "session_token", "value": "...", "domain": "..." } ],
    "origins": [ { "origin": "https://...", "localStorage": [...] } ]
  },
  "metadata": {
    "captured_at": "2026-07-21T10:00:00+00:00",
    "expires_at":  "2026-07-24T10:00:00+00:00",
    "url": "https://meditik.test.medical.idf.il/home",
    "environment": "https://meditik.test.medical.idf.il/home"
  },
  "tokens": {
    "auth_token": "..."
  }
}
```

---

### 3. BasePage — מחלקת בסיס (`pages/base_page.py`)

מחלקה בעלת **תפקיד כפול** — משמשת גם כבסיס ל-Page Objects וגם כבסיס למחלקות בדיקה.

**כ-Page Object (דפוס POM):**

```python
from refua_core.pages.base_page import BasePage
from playwright.sync_api import Page

class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.email_input = page.locator("[data-testid='email']")
        self.password_input = page.locator("[data-testid='password']")
        self.login_button = page.locator("[data-testid='login-btn']")

    def login(self, email: str, password: str):
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.login_button.click()
```

**כמחלקת בדיקה:**

```python
from refua_core.pages.base_page import BasePage

class TestLogin(BasePage):
    def test_successful_login(self):
        # self.page מוגדר אוטומטית דרך fixture
        login_page = LoginPage(self.page)
        login_page.goto("/login")
        login_page.login("user@test.com", "password")
        self.wait_for_url("/dashboard")
```

**מה BasePage מספקת:**

| מתודה | תיאור |
|-------|--------|
| `goto(path)` | ניווט לנתיב יחסי ל-base URL |
| `wait_for_url(path)` | המתנה לניווט |
| `is_visible(selector)` | בדיקה אם אלמנט גלוי |
| `get_text(selector)` | קבלת טקסט של אלמנט |
| `take_screenshot(name)` | צילום מסך ושמירה לקובץ |
| `is_production()` | האם סביבת Production? |
| `can_bypass_2fa()` | האם ניתן לעקוף 2FA? |
| `get_session_dir()` | נתיב תיקיית Sessions |
| `setup_browser` (fixture) | הקמה אוטומטית של דפדפן עבור כל טסט |

---

### 4. Pytest Plugin — conftest.py (`refua_core/conftest.py`)

פלאגין של Pytest שנרשם אוטומטית כשמתקינים את הספרייה. הוא מוסיף:

**אפשרויות CLI:**

```bash
pytest --test-env test              # סביבה (חלופה ל-TEST_ENV)
pytest --test-app cpr-go            # אפליקציה (חלופה ל-TEST_APP)
pytest --browser firefox            # דפדפן
pytest --device iphone              # מכשיר
pytest --skip-2fa true              # דילוג על 2FA
pytest --session-dir /path          # נתיב Sessions
pytest --headless                   # הרצה ללא חלון דפדפן
pytest --slow-motion 500            # האטת פעולות (מילישניות)
pytest --record-video true          # הקלטת וידאו
pytest --capture-screenshots true   # צילומי מסך
```

**מה קורה בזמן טעינה:**

1. ממיר CLI options למשתני סביבה (אם הועברו)
2. מוודא שהסביבה מוגדרת נכון (`validate_environment`)
3. מדפיס לוג עם כל הפרמטרים של ההרצה
4. מוסיף marker של סביבה לכל טסט

**Fixtures זמינים:**

| Fixture | Scope | תיאור |
|---------|-------|--------|
| `env_manager` | function | מופע של EnvironmentManager |
| `playwright_instance` | function | מופע Playwright פעיל |
| `headless` | session | האם להריץ headless |
| `slow_motion` | session | האטת פעולות |

---

### 5. סקריפט לכידת Session (`scripts/capture_session.py`)

סקריפט אינטראקטיבי שפותח דפדפן, מאפשר למשתמש להתחבר ידנית (כולל 2FA), ושומר את ה-Session.

**שימוש בסיסי:**

```bash
# לכידת session לסביבת test (כל הדפדפנים)
python scripts/capture_session.py --env test --user john.doe

# לכידה לדפדפן ספציפי
python scripts/capture_session.py --env test --user john.doe --browser firefox

# לכידה לאפליקציה אחרת
python scripts/capture_session.py --env test --user john.doe --app cpr-go

# עם נתיב session מותאם (Docker)
python scripts/capture_session.py --env test --user john.doe --session-dir /sessions
```

**תהליך הלכידה:**

1. הסקריפט פותח דפדפן גלוי (headless=false)
2. מנווט לדף ההתחברות של הסביבה
3. המשתמש מתחבר ידנית ומשלים 2FA
4. הסקריפט מזהה שההתחברות הצליחה
5. שומר את כל ה-cookies, localStorage ו-metadata לקובץ JSON
6. הקובץ תקף ל-3 ימים

---

### 6. פרופילי מכשירים (`config/devices.json`)

קובץ JSON עם הגדרות מכשירים לאמולציה — מאפשר להריץ בדיקות בתצוגת מובייל:

| מכשיר | viewport | mobile | touch |
|--------|----------|--------|-------|
| `desktop` | 1920×1080 | ❌ | ❌ |
| `iphone` / `iphone_14_pro` | 393×852 | ✅ | ✅ |
| `iphone_14` | 390×844 | ✅ | ✅ |
| `iphone_13` | 390×844 | ✅ | ✅ |
| `android` / `android_pixel` | 412×915 | ✅ | ✅ |
| `android_galaxy` | 320×658 | ✅ | ✅ |

---

## 🚀 איך מתחילים — Quick Start

### שלב 1: התקנת הסביבה

```bash
# שכפול הריפו
git clone https://github.com/roybi/refuaAutomationCore.git
cd refuaAutomationCore

# יצירת סביבה וירטואלית
python -m venv venv

# הפעלת הסביבה (Windows)
venv\Scripts\activate

# התקנת הספרייה במצב פיתוח
pip install -e ".[dev]"

# התקנת דפדפני Playwright
python -m playwright install

# אימות
python -c "from refua_core.config.environment import EnvironmentManager; print('✔ הכל עובד!')"
```

### שלב 2: יצירת תיקיית Sessions

```bash
# Windows
mkdir %USERPROFILE%\.refua_sessions

# Linux/Mac
mkdir -p ~/.refua_sessions
```

### שלב 3: לכידת Session

```bash
python scripts/capture_session.py --env test --user YOUR_NAME
# ← דפדפן ייפתח. התחברו ידנית והשלימו 2FA.
```

### שלב 4: הרצת בדיקות (מ-refuaAutomationTests)

```bash
cd ../refuaAutomationTests
pip install -r requirements.txt
TEST_ENV=test pytest -v
```

---

## 🔧 משתני סביבה — Reference

### חובה

| משתנה | ערכים | תיאור |
|-------|-------|--------|
| `TEST_ENV` | `test`, `preprod`, `prod` | סביבת הריצה |

### אופציונליים

| משתנה | ברירת מחדל | ערכים | תיאור |
|-------|------------|-------|--------|
| `TEST_APP` | `meditek` | `meditek`, `cpr-go` | אפליקציה לבדיקה |
| `BROWSER` | `chromium` | `chromium`, `firefox`, `webkit`, `safari` | דפדפן |
| `DEVICE` | `desktop` | `desktop`, `iphone`, `android`, ושמות ספציפיים | מכשיר |
| `SKIP_2FA` | `true` | `true`, `false` | עקיפת 2FA |
| `SESSION_DIR` | `~/.refua_sessions` | נתיב כלשהו | תיקיית Sessions |
| `RECORD_VIDEO` | `true` | `true`, `false` | הקלטת וידאו |
| `CAPTURE_SCREENSHOTS` | `true` | `true`, `false` | צילומי מסך |
| `DEBUG_AUTH` | — | `true` | לוגים מפורטים לאימות |

---

## 📐 Design Patterns — דפוסי עיצוב בשימוש

### 1. Singleton (EnvironmentManager)

מופע יחיד לכל הריצה — כל הטסטים חולקים את אותה קונפיגורציה:

```python
env1 = get_env_manager()
env2 = get_env_manager()
assert env1 is env2  # True — אותו מופע בדיוק
```

### 2. Page Object Model (POM)

כל דף באפליקציה מיוצג במחלקה נפרדת. מפריד בין "מה הדף מכיל" ל"מה הבדיקה עושה":

```python
# Page Object — מגדיר את הדף
class DashboardPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.user_menu = page.locator("[data-testid='user-menu']")

    def open_user_menu(self):
        self.user_menu.click()

# בדיקה — משתמשת ב-Page Object
class TestDashboard(BasePage):
    def test_user_menu_visible(self):
        dashboard = DashboardPage(self.page)
        dashboard.goto("/dashboard")
        assert dashboard.user_menu.is_visible()
```

**למה זה חשוב?** אם UI משתנה, מתקנים רק את ה-Page Object — לא את כל הבדיקות.

### 3. Session State Management

הפרדה בין לכידת Session ידנית (פעם ב-3 ימים) לשימוש אוטומטי בו בכל הרצת בדיקה.

### 4. Configuration Externalization

הפרדה של credentials ל-`.env` קבצים, sessions לתיקייה חיצונית, והגדרות סביבה למשתנים — שום דבר סודי לא נכנס ל-Git.

### 5. Pytest Plugin Architecture

הספרייה נרשמת כפלאגין של Pytest דרך `entry_points` ב-`setup.py`, כך שרק `pip install` מספיק כדי שכל ה-fixtures וה-CLI options יהיו זמינים.

---

## 🔄 תהליך עבודה יומיומי

```
                    ┌─────────────────────────┐
                    │  בדיקת תוקף Session     │
                    │  (< 3 ימים?)            │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │ אם פג → capture_session │
                    │ אם תקף → המשך          │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │ cd refuaAutomationTests  │
                    │ TEST_ENV=test pytest -v  │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ✅ עבר         ❌ נכשל       ⚠️ שגיאת Session
              │              │              │
         סיים            תקן           הרץ capture
                        והרץ שוב       מחדש
```

---

## ⚠️ טעויות נפוצות ופתרונות

### 1. `EnvironmentNotSetError`

```
❌ TEST_ENV environment variable is required.
```

**פתרון:** הוסיפו `TEST_ENV=test` לפני פקודת pytest.

### 2. `Session file not found`

```
❌ Session file not found: ~/.refua_sessions/auth_state_meditek_test_chromium_latest.json
```

**פתרון:** הריצו `python scripts/capture_session.py --env test --user YOUR_NAME`

### 3. `Session expired`

```
❌ Session expired at: 2026-07-18T10:00:00+00:00
```

**פתרון:** הריצו שוב את סקריפט הלכידה — ה-Session תקף רק 3 ימים.

### 4. `No module named refua_core`

**פתרון:** וודאו שהתקנתם את הספרייה:

```bash
pip install -e ".[dev]"               # בריפו של Core
pip install -r requirements.txt       # בריפו של Tests
```

### 5. localStorage לא נטען

**פתרון:** `apply_local_storage()` חייב להיקרא **אחרי** `page.goto()` — כי localStorage הוא per-origin:

```python
# ❌ שגוי
session_mgr.apply_local_storage(page)
page.goto(url)   # localStorage אבד!

# ✅ נכון
page.goto(url)
session_mgr.apply_local_storage(page)
```

### 6. Session לא מתאים לסביבה

```
❌ Invalid session for environment
```

**פתרון:** וודאו שה-`TEST_ENV` תואם לסביבה שבה נלכד ה-Session.

---

## 📦 ניהול גרסאות

הגרסה מוגדרת במקום אחד: `refua_core/version.py`

```python
__version__ = "1.0.0"
```

### מתי מעלים גרסה?

| סוג שינוי | חלק בגרסה | דוגמה |
|-----------|-----------|--------|
| תיקון באג, refactor פנימי | **patch** | `1.0.0` → `1.0.1` |
| פיצ'ר חדש, fixture חדש | **minor** | `1.0.0` → `1.1.0` |
| שינוי שובר (שינוי שם מחלקה, מחיקת מתודה) | **major** | `1.0.0` → `2.0.0` |

### תהליך שחרור גרסה

```bash
# 1. עדכון version.py
# 2. Commit ו-Tag
git add refua_core/version.py
git commit -m "chore: bump version to 1.1.0"
git tag v1.1.0
git push origin main --tags
```

---

## 🧪 הרצת בדיקות — פקודות שימושיות

כל הפקודות הבאות מורצות **מתוך refuaAutomationTests**:

```bash
# הרצה בסיסית
TEST_ENV=test pytest

# עם Allure report
TEST_ENV=test pytest --alluredir=./allure-results

# רק smoke tests
TEST_ENV=test pytest -m smoke

# בדיקות ספציפיות
TEST_ENV=test pytest tests/test_auth.py -v
TEST_ENV=test pytest tests/test_auth.py::test_login -v

# בדפדפן אחר
BROWSER=firefox TEST_ENV=test pytest

# במכשיר מובייל
DEVICE=iphone TEST_ENV=test pytest

# הרצה מקבילית (מהירה יותר ×3-4)
TEST_ENV=test pytest -n auto --dist=loadscope

# צפייה ב-Allure report
allure serve ./allure-results
```

---

## 🔌 רישום אפליקציה חדשה

אם רוצים לבדוק אפליקציה נוספת (מעבר ל-MEDITEK ו-CPR-GO):

```python
# ב-conftest.py של פרויקט הבדיקות
from refua_core.config.environment import EnvironmentManager, EnvType, AuthConfig

EnvironmentManager.register_app("my-new-app", {
    EnvType.TEST: {
        "base_url": "https://my-app.test.example.com",
        "api_url": "https://my-app.test.example.com/api",
        "auth_config": AuthConfig(
            use_2fa=True,
            bypass_2fa=True,
            session_timeout=3600,
            auth_method="session_state",
        ),
    },
    # ... PREPROD, PROD ...
})
```

ואז הריצו עם:

```bash
TEST_APP=my-new-app TEST_ENV=test pytest
```

---

## 💡 טיפים למפתח חדש

### 1. התחילו מ-GETTING_STARTED.md

קובץ `GETTING_STARTED.md` בשורש הריפו מכיל מדריך צעד-אחר-צעד.

### 2. אל תריצו בדיקות מתוך הריפו הזה

הריפו הזה הוא **רק תשתית**. הבדיקות עצמן נמצאות ב-`refuaAutomationTests`.

### 3. פיתוח מקביל של Core + Tests

אם אתם משנים את התשתית ורוצים לראות את ההשפעה על הבדיקות מיד:

```bash
# ב-refuaAutomationTests/requirements.txt:
-e ../refuaAutomationCore
```

כך כל שינוי ב-Core משתקף מיד בבדיקות, ללא צורך ב-reinstall.

### 4. ה-Session חייב להיות תקף לפני ריצה

אם מקבלים שגיאת session — הריצו `capture_session.py`. זה לוקח דקה.

### 5. השתמשו ב-Page Objects

אל תכתבו `page.locator(...)` ישירות בבדיקות. צרו Page Object — זה חוסך זמן כשה-UI משתנה.

### 6. סמנו בדיקות עם markers

```python
@pytest.mark.smoke           # בדיקות עשן
@pytest.mark.regression      # בדיקות רגרסיה
@pytest.mark.mobile          # בדיקות מובייל
@pytest.mark.sequential      # חייב לרוץ סדרתי (לא מקבילי)
```

### 7. קבצי `.env` לעולם לא נכנסים ל-Git

קבצי credentials (`.env.test`, `.env.preprod`) חייבים להישאר מחוץ ל-version control.

### 8. בדקו את `env_summary` לפני debugging

```python
env = get_env_manager()
print(env.get_env_summary())
```

מדפיס מידע מלא: סביבה, URL, session file, וכו'.

---

## 📊 Roadmap — מה עוד מתוכנן

| רכיב | סטטוס | תיאור |
|-------|--------|--------|
| EnvironmentManager | ✅ מוכן | ניהול סביבות ואפליקציות |
| SessionStateManager | ✅ מוכן | ניהול Sessions ו-2FA |
| BasePage | ✅ מוכן | מחלקת בסיס POM + Tests |
| conftest.py Plugin | ✅ מוכן | CLI options + validation |
| capture_session.py | ✅ מוכן | לכידת Session |
| DeviceManager | 📋 מתוכנן | ניהול פרופילי מכשירים |
| ArtifactManager | 📋 מתוכנן | ניהול וידאו/צילומי מסך |
| VisualRegression | 📋 מתוכנן | השוואה מול Figma |
| CI/CD Pipeline | 📋 מתוכנן | GitHub Actions |
| Docker Support | 📋 מתוכנן | הרצה בקונטיינר |
| BDD/Gherkin | 📋 עתידי | בדיקות בסגנון Gherkin |

---

## 📞 לסיכום

**refuaAutomationCore** מספק את כל מה שצריך כדי לכתוב בדיקות אוטומטיות למערכת MEDITEK:

- ✅ ניהול סביבות (test/preprod/prod) עם תמיכה במספר אפליקציות
- ✅ עקיפת 2FA אוטומטית דרך Sessions שמורים
- ✅ Page Object Model מובנה
- ✅ תמיכה בריבוי דפדפנים ומכשירים
- ✅ Pytest Plugin עם CLI options נוחים
- ✅ סקריפט לכידת Session אינטראקטיבי

**שאלות? בעיות?** פתחו Issue ב-GitHub Repository.
