# Getting Started

This guide walks a new team member through everything needed to run the MEDITEK test automation suite from scratch.

---

## How the two repositories fit together

```
refuaAutomationCore          ← you are here
  Published as a Python package (refua-automation-core)
  Contains: EnvironmentManager, SessionStateManager, BaseTest, BasePage,
            conftest.py plugin, capture_session.py script

refuaAutomationTests         ← separate repo, cloned alongside this one
  Contains: test cases, page objects, fixtures, pytest.ini
  Depends on: refua-automation-core (installed from git or PyPI)
```

You **never run tests from this repo**. All `pytest` commands are executed from `refuaAutomationTests`.

---

## Prerequisites

| Tool | Minimum version | How to check |
|------|-----------------|--------------|
| Python | 3.9 | `python --version` |
| Git | any | `git --version` |
| pip | 23+ | `pip --version` |

---

## Part 1 — Set up the core framework

Do this once (or when you need to modify core framework code).

```bash
# 1. Clone the core repo
git clone https://github.com/roybi/refuaAutomationCore.git
cd refuaAutomationCore

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install in editable mode (picks up your changes without reinstalling)
pip install -e ".[dev]"

# 4. Install Playwright browsers
python -m playwright install

# 5. Verify
python -c "from refua_core.config.environment import EnvironmentManager; print('Core OK')"
```

---

## Part 2 — Set up the test repository

Do this in a **separate terminal / directory** alongside the core repo.

```bash
# 1. Clone the test repo
git clone https://github.com/roybi/refuaAutomationTests.git
cd refuaAutomationTests

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install all dependencies
#    requirements.txt already lists refua-automation-core
pip install -r requirements.txt

# 4. Install Playwright browsers (if not done already)
python -m playwright install

# 5. Verify
python -c "from refua_core.config.environment import EnvironmentManager; print('OK')"
```

> **Tip — developing core and tests together:** If you are actively changing core code, install it as an editable local path instead of from git:
> ```
> # In refuaAutomationTests/requirements.txt, replace the git line with:
> -e ../refuaAutomationCore
> ```
> Then run `pip install -r requirements.txt` again. Every change you make to the core is instantly reflected in the tests.

---

## Part 3 — Create environment credential files

Tests load credentials from `.env` files in the test repo root. These files are **never committed to git**.

```
# refuaAutomationTests/.env.test
TEST_USER_EMAIL=your.name@meditek.local
TEST_USER_PASSWORD=your_password

# refuaAutomationTests/.env.preprod
PREPROD_USER_EMAIL=your.name@meditek.local
PREPROD_USER_PASSWORD=your_password
```

---

## Part 4 — Capture a 2FA session (required before first test run)

The framework bypasses 2FA by reusing a pre-captured browser session. You capture this session **once**, and it stays valid for **3 days**.

```bash
# From the refuaAutomationCore directory, with its venv active:

# Capture a session for the test environment (opens a visible browser)
python scripts/capture_session.py --env test --user your.name

# A browser window opens. Log in manually and complete 2FA.
# The script saves the session automatically — no further action needed.
```

Sessions are stored in `~/.refua_sessions/`:

```
~/.refua_sessions/
├── auth_state_test_chromium_latest.json      ← used by default
├── auth_state_test_firefox_latest.json
├── auth_state_preprod_chromium_latest.json
└── ...
```

**Capture once per environment.** Repeat when the session expires (error message will tell you).

Optional flags:
```bash
# Specific browser only
python scripts/capture_session.py --env test --user your.name --browser firefox

# Custom session directory (e.g. for Docker)
python scripts/capture_session.py --env test --user your.name --session-dir /sessions

# Mobile device session
python scripts/capture_session.py --env test --user your.name --device iphone
```

---

## Part 5 — Run tests

All commands below are run **from the `refuaAutomationTests` directory** with its venv active.

### Minimum working command

```bash
TEST_ENV=test pytest
```

### Common runs

```bash
# With Allure report output
TEST_ENV=test pytest --alluredir=./allure-results

# Verbose output
TEST_ENV=test pytest -v --alluredir=./allure-results

# Smoke tests only
TEST_ENV=test pytest -m smoke --alluredir=./allure-results

# Specific test file
TEST_ENV=test pytest tests/test_auth.py -v

# Specific test function
TEST_ENV=test pytest tests/test_auth.py::test_login -v
```

### Selecting browser

```bash
BROWSER=chromium TEST_ENV=test pytest      # default
BROWSER=firefox  TEST_ENV=test pytest
BROWSER=webkit   TEST_ENV=test pytest
```

### Selecting device

```bash
DEVICE=desktop  TEST_ENV=test pytest      # default
DEVICE=iphone   TEST_ENV=test pytest
DEVICE=android  TEST_ENV=test pytest
```

### Parallel execution

Requires `pytest-xdist` (already in requirements.txt):

```bash
# Auto-detect CPU cores
TEST_ENV=test pytest -n auto --alluredir=./allure-results

# Fixed number of workers
TEST_ENV=test pytest -n 4 --alluredir=./allure-results

# Parallel + stable distribution
TEST_ENV=test pytest -n auto --dist=loadscope --alluredir=./allure-results
```

### Headless / slow-motion (debugging)

```bash
# Run headed (see the browser)
TEST_ENV=test pytest --headless=false -v

# Slow everything down by 500ms per action
TEST_ENV=test pytest --slow-motion=500 -v
```

### View Allure report

```bash
allure serve ./allure-results
```

---

## Environment variable reference

| Variable | Required | Default | Values |
|----------|----------|---------|--------|
| `TEST_ENV` | **Yes** | — | `test`, `preprod`, `prod` |
| `BROWSER` | No | `chromium` | `chromium`, `firefox`, `webkit`, `safari` |
| `DEVICE` | No | `desktop` | `desktop`, `iphone`, `android`, model names |
| `SKIP_2FA` | No | `true` | `true`, `false` |
| `SESSION_DIR` | No | `~/.refua_sessions` | any path |
| `RECORD_VIDEO` | No | `true` | `true`, `false` |
| `CAPTURE_SCREENSHOTS` | No | `true` | `true`, `false` |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `EnvironmentNotSetError` | `TEST_ENV` not set | Add `TEST_ENV=test` before `pytest` |
| `Session file not found` | Never captured a session | Run `capture_session.py` |
| `Session expired` | Session older than 3 days | Run `capture_session.py` again |
| `Invalid session for environment` | Session captured for wrong env | Re-run capture with correct `--env` |
| `No module named refua_core` | Package not installed | Run `pip install -r requirements.txt` in the test repo |
| `playwright: command not found` | Browsers not installed | Run `python -m playwright install` |

---

## How the session file path is resolved

When tests run, `EnvironmentManager` builds the session file path in this priority order:

```
1. {ENV}_AUTH_STATE_FILE env var          ← exact file path (highest priority)
2. {ENV}_AUTH_STATE_{BROWSER} env var     ← browser-specific file path override
3. Default: ~/.refua_sessions/auth_state_{TEST_ENV}_chromium_latest.json
```

**The default always resolves to chromium**, regardless of the `BROWSER` env var.
To use a non-chromium session file, set the browser-specific override:

```bash
# Run firefox tests using a firefox session file
TEST_AUTH_STATE_FIREFOX=~/.refua_sessions/auth_state_test_firefox_latest.json \
  BROWSER=firefox TEST_ENV=test pytest

# Or point to any file explicitly
TEST_AUTH_STATE_FILE=~/.refua_sessions/auth_state_test_chromium_latest.json \
  TEST_ENV=test pytest
```

`SESSION_DIR` only changes the **directory** — the filename is still constructed automatically:

```bash
# Uses /my/sessions/auth_state_test_chromium_latest.json
SESSION_DIR=/my/sessions TEST_ENV=test pytest
```

---

## How versioning works across the two repos

### When to bump the version

| Change type | Version part | Example |
|-------------|-------------|---------|
| Bug fix, internal refactor | patch | `1.0.0` → `1.0.1` |
| New feature, new fixture, new config option | minor | `1.0.0` → `1.1.0` |
| Breaking change (renamed class, removed method) | major | `1.0.0` → `2.0.0` |

### How to release a new core version

**In `refuaAutomationCore`:**

```bash
# 1. Update the single source of truth
#    Edit refua_core/version.py:  __version__ = "1.1.0"

# 2. Commit and tag
git add refua_core/version.py
git commit -m "chore: bump version to 1.1.0"
git tag v1.1.0
git push origin roy_dev_refuaCore --tags
```

**In `refuaAutomationTests`** (update the dependency pin):

```
# requirements.txt — update the @tag at the end:
refua-automation-core @ git+https://github.com/roybi/refuaAutomationCore.git@v1.1.0

# Then reinstall:
pip install -r requirements.txt
```

If `requirements.txt` pins to `@main` (always latest), no change is needed — just `pip install -r requirements.txt` after the core is pushed.

> **Breaking changes:** If you rename a class, remove a method, or change a fixture signature, bump the major version and search the test repo for all usages before upgrading. Update call sites in the test repo before merging.

---

## Day-to-day workflow

```
1. cd refuaAutomationTests && venv\Scripts\activate   (or source venv/bin/activate)
2. Check if session is still valid (< 3 days old):
       ls -la ~/.refua_sessions/
3. If expired: cd ../refuaAutomationCore && python scripts/capture_session.py --env test --user your.name
4. Back in test repo: TEST_ENV=test pytest -m smoke -v
```
