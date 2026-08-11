# Copilot Instructions — refuaAutomationCore

## Repository purpose

This is a **framework library**, not a test repo. It is published as the `refua-automation-core` Python package and consumed by `refuaAutomationTests`. **Do not add test cases here.** All `pytest` runs happen in `refuaAutomationTests`.

---

## Setup & install commands

```bash
# Install in editable mode with dev tools (run once, or after dependency changes)
pip install -e ".[dev]"

# Install Playwright browsers
python -m playwright install

# Verify installation
python -c "from refua_core.config.environment import EnvironmentManager; print('OK')"
```

The package registers its `conftest.py` as a pytest plugin via `entry_points` in `setup.py` (`pytest11 = refua-core = refua_core.conftest`). Consumer repos get all fixtures automatically on `pip install`.

---

## Architecture

### Two-repository design

```
refuaAutomationCore   ← this repo (framework package)
refuaAutomationTests  ← separate repo (test cases, page objects)
```

During active development, install core as an editable local path in the test repo:

```
# refuaAutomationTests/requirements.txt
-e ../refuaAutomationCore
```

### Package layout

```
refua_core/
  config/
    environment.py      # EnvironmentManager singleton + app registry
    session_manager.py  # SessionStateManager — 2FA bypass via saved browser sessions
    devices.json        # Mobile device profiles (viewport, UA, touch flags)
    settting.py         # SmartLocator config dataclass (LocatorConfig / settings)
  core/
    base_page.py        # BasePage — dual-role base for page objects AND test classes
    smart_locator.py    # SmartLocator/LocatorDefinition (in progress)
  pages/
    home_Page.py        # homePage — MEDITEK login/home screen POM
    main_page.py        # MainPage — post-login dashboard POM
  conftest.py           # pytest plugin: CLI options → env vars, session-scoped fixtures
  version.py            # Single source of truth for package version
scripts/
  capture_session.py    # Interactive 2FA session capture script (run manually)
```

---

## Key conventions

### EnvironmentManager is a singleton

```python
from refua_core.config.environment import get_env_manager, EnvironmentManager

mgr = get_env_manager()           # always returns the same instance
EnvironmentManager.reset_instance()  # call in tests to reset state between test runs
```

`TEST_ENV` **must** be set before the singleton is first instantiated — it raises `EnvironmentNotSetError` otherwise. The conftest plugin validates this at collection time.

### Multi-app support via `_APP_REGISTRY`

`environment.py` contains a module-level `_APP_REGISTRY` dict with entries for `"meditek"` and `"cpr-go"`. Register new apps **before** the singleton is first used:

```python
EnvironmentManager.register_app("my-app", {
    EnvType.TEST: {"base_url": "...", "api_url": "...", "auth_config": AuthConfig(...)},
    ...
})
```

`TEST_APP` env var selects the active app (defaults to `"meditek"`).

### Session file naming convention

Session files are stored at:

```
~/.refua_sessions/auth_state_{app}_{env}_{browser}_latest.json
```

e.g. `auth_state_meditek_test_chromium_latest.json`

Override with env vars (highest priority first):

1. `{ENV}_AUTH_STATE_FILE` — exact file path
2. `{ENV}_AUTH_STATE_{BROWSER}` — browser-specific file path
3. `SESSION_DIR` env var — changes the directory only, filename is auto-constructed

`apply_local_storage()` on `SessionStateManager` **must be called after `page.goto()`** because localStorage is origin-scoped.

### BasePage dual-role pattern

`BasePage` (`refua_core/core/base_page.py`) is used two ways:

**As a page object base** — pass the Playwright `Page` object to `__init__`:

```python
class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
```

**`BasePage` must NOT be used as a test class base.** Because `BasePage` defines `__init__`, pytest refuses to collect any class that inherits it. For browser tests use the `browser_page` fixture instead:

```python
class TestHomePage:            # plain class — pytest can collect it
    def test_title(self, browser_page):
        browser_page.goto("https://...")
        home = homePage(browser_page)
        assert "כניסה" in home.get_login_title_text()
```

The `browser_page` fixture (from the `refua-core` plugin) handles the full lifecycle: launch browser → load session if 2FA-bypass is on → yield `Page` → teardown.

### Concrete page objects use `self.driver`, not `self.page`

The existing page objects (`homePage`, `MainPage`) receive the driver as a constructor argument and store it as `self.driver`. Locators are defined in `define_locators()` called from `__init__`. Follow this pattern when adding new pages:

```python
class MyPage(BasePage):
    def __init__(self, driver) -> None:
        super().__init__(driver)
        self.define_locators()

    def define_locators(self) -> None:
        self.MY_ELEMENT = self.driver.locator("#my-id")
```

### Versioning

The single source of truth is `refua_core/version.py`. Bump it there only; `setup.py` reads it at build time.

Versioning policy:
- Patch — bug fixes, internal refactors
- Minor — new features, new fixtures/config options
- Major — breaking changes (renamed class, removed method, changed fixture signature)

Release:

```bash
# Edit refua_core/version.py → __version__ = "x.y.z"
git add refua_core/version.py
git commit -m "chore: bump version to x.y.z"
git tag vx.y.z
git push origin <branch> --tags
```

---

## Environment variable reference

| Variable | Required | Default | Values |
|---|---|---|---|
| `TEST_ENV` | **Yes** | — | `test`, `preprod`, `prod` |
| `TEST_APP` | No | `meditek` | `meditek`, `cpr-go`, registered app name |
| `BROWSER` | No | `chromium` | `chromium`, `firefox`, `webkit`, `safari` |
| `DEVICE` | No | `desktop` | `desktop`, `iphone`, `android`, model name |
| `SESSION_DIR` | No | `~/.refua_sessions` | any path |
| `SKIP_2FA` | No | `true` | `true`, `false` |
| `RECORD_VIDEO` | No | `true` | `true`, `false` |
| `CAPTURE_SCREENSHOTS` | No | `true` | `true`, `false` |

CLI equivalents registered by the plugin: `--test-app`, `--test-env`, `--browser`, `--device`, `--skip-2fa`, `--session-dir`, `--record-video`, `--capture-screenshots`, `--headless`, `--slow-motion`.

---

## Session capture script

Run from this repo to capture a 2FA session interactively (required before first test run; valid 3 days):

```bash
python scripts/capture_session.py --env test --user your.name
# opens a browser window — log in manually and complete 2FA
```

Optional flags: `--browser firefox`, `--device iphone`, `--session-dir /path`.
