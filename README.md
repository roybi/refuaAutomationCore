# refuaAutomationCore

Reusable test automation framework for the MEDITEK medical system, built with Python and Playwright.

## What's in this repository

This repository contains **only the core framework** — reusable infrastructure, configuration, and base classes. Test cases, page objects, and fixtures live in the separate **`refuaAutomationTests`** repository that depends on this package.

## Components

### `refua_core/config/`

| File | Purpose |
|------|---------|
| `environment.py` | `EnvironmentManager` singleton — base URLs, API endpoints, credential loading per environment |
| `session_manager.py` | 2FA bypass — session file validation, cookie/localStorage injection, 3-day TTL |

### `refua_core/pages/`

| File | Purpose |
|------|---------|
| `base_page.py` | `BasePage` — single base for both page objects and test classes; includes browser lifecycle fixture, environment-aware `goto()` / `wait_for_url()`, element helpers, and screenshot capture |

### `refua_core/core/`

Supporting infrastructure (no test base class — that lives in `pages/base_page.py`):

### `refua_core/conftest.py`

Pytest plugin that registers `--test-env`, `--browser`, `--device`, `--skip-2fa`, `--session-dir` CLI options and validates the environment before tests start.

### `scripts/capture_session.py`

Interactive session capture — launches a browser, waits for manual login + 2FA, then saves the authenticated state to `~/.refua_sessions/`. Run once per environment, reuse for all tests.

```
~/.refua_sessions/
├── auth_state_test_chromium_latest.json
├── auth_state_test_firefox_latest.json
├── auth_state_preprod_chromium_latest.json
└── ...
```

## Installation

### Framework development

```bash
git clone https://github.com/roybi/refuaAutomationCore.git
cd refuaAutomationCore

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -e ".[dev]"

# Verify
python -c "from refua_core.config.environment import EnvironmentManager; print('OK')"
```

### As a dependency (in `refuaAutomationTests`)

```
# requirements.txt

# From Git (recommended during development)
refua-automation-core @ git+https://github.com/roybi/refuaAutomationCore.git@main

# From PyPI (when released)
refua-automation-core>=1.0.0
```

## Usage

### 1. Capture a session (once per environment)

```bash
# All browsers
python scripts/capture_session.py --env test --user john.doe

# Specific browser
python scripts/capture_session.py --env test --user john.doe --browser firefox

# Custom session directory (Docker)
python scripts/capture_session.py --env test --user john.doe --session-dir /sessions
```

### 2. Run tests (from `refuaAutomationTests`)

```bash
# Basic run
TEST_ENV=test pytest --alluredir=./allure-results

# Specific browser
BROWSER=firefox TEST_ENV=test pytest

# Parallel execution
TEST_ENV=test pytest -n auto --dist=loadscope

# View Allure report
allure serve ./allure-results
```

### Page Object Model example

```python
from playwright.sync_api import Page
from refua_core.pages.base_page import BasePage

class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.locator("[data-testid='email']")
        self.password = page.locator("[data-testid='password']")
        self.submit = page.locator("[data-testid='login-btn']")

    def login(self, email: str, password: str):
        self.email.fill(email)
        self.password.fill(password)
        self.submit.click()

class TestAuth(BasePage):
    def test_login(self):
        login = LoginPage(self.page)
        login.goto("/login")
        login.login("user@test.com", "password")
        self.wait_for_url("/dashboard")
```

## Environment variables

| Variable | Required | Default | Values |
|----------|----------|---------|--------|
| `TEST_ENV` | Yes | — | `test`, `preprod`, `prod` |
| `BROWSER` | No | `chromium` | `chromium`, `firefox`, `webkit`, `safari` |
| `DEVICE` | No | `desktop` | `desktop`, `iphone`, `android` |
| `SKIP_2FA` | No | `true` | `true`, `false` |
| `SESSION_DIR` | No | `~/.refua_sessions` | any path |
| `RECORD_VIDEO` | No | `true` | `true`, `false` |
| `CAPTURE_SCREENSHOTS` | No | `true` | `true`, `false` |

## Environment configuration

| Environment | 2FA bypass | Session timeout |
|-------------|------------|-----------------|
| `test` | Yes | 3 days |
| `preprod` | Yes | 3 days |
| `prod` | No | 30 minutes |

## Project structure

```
refuaAutomationCore/
├── refua_core/
│   ├── config/
│   │   ├── environment.py       # EnvironmentManager singleton
│   │   └── session_manager.py   # SessionStateManager (2FA bypass)
│   ├── pages/
│   │   └── base_page.py         # BasePage — base for page objects and test classes
│   ├── core/
│   ├── conftest.py              # Pytest plugin (CLI options + env validation)
│   └── version.py
├── scripts/
│   └── capture_session.py       # Interactive session capture
├── setup.py
├── requirements.txt
├── CLAUDE.md                    # Full framework documentation
└── README.md
```

## Dependencies

**Core** (installed automatically):
- `playwright >= 1.40`
- `python-dotenv >= 1.0`
- `requests >= 2.31`
- `packaging >= 21.0`

**Dev extras** (`pip install -e ".[dev]"`):
- `pytest`, `pytest-xdist`, `black`, `flake8`, `mypy`, `isort`

**Test-runner extras** (install in `refuaAutomationTests`):
- `allure-pytest` — Allure report generation
- `pytest-xdist` — parallel execution

## Releasing a new version

1. Update `__version__` in `refua_core/version.py`
2. Commit and tag: `git tag v1.x.x && git push origin v1.x.x`
3. Build and publish: `python -m build && python -m twine upload dist/*`
