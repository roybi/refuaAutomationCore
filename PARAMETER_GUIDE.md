# Test Execution Parameter Guide

## Overview

When running tests with the refuaAutomationCore framework, **all environment parameters must be passed BEFORE the `pytest` command**. Pytest options are passed AFTER the command.

## ✅ CORRECT FORMAT

```bash
ENV_VAR1=value1 ENV_VAR2=value2 pytest [OPTIONS] [TEST_PATH]
```

### Example:
```bash
TEST_ENV=test BROWSER=firefox DEVICE=iphone pytest tests/ -v --alluredir=./allure-results
```

## ❌ INCORRECT FORMAT

```bash
# WRONG - environment variables after pytest
pytest tests/ TEST_ENV=test BROWSER=firefox

# WRONG - pytest options mixed with environment variables
TEST_ENV=test pytest -v DEVICE=iphone tests/

# WRONG - environment variables at the end
pytest tests/ -v TEST_ENV=test
```

## Environment Variables (BEFORE pytest)

All environment variables must be set before the `pytest` command. They control test execution behavior.

### Required Parameters

#### TEST_ENV (REQUIRED)
Specifies the target environment for testing.

**Values:** `test`, `preprod`, `prod`

**Default:** None (must be explicitly set)

**Purpose:**
- Determines base URL and API endpoints
- Controls 2FA bypass availability (enabled for test/preprod, optional for prod)
- Selects appropriate credentials from `.env.*` files
- Configures session validation behavior

**Examples:**
```bash
TEST_ENV=test pytest tests/
TEST_ENV=preprod pytest tests/
TEST_ENV=prod pytest tests/
```

**Behavior by Environment:**
- **test**: 2FA bypass enabled, uses saved sessions, relaxed timeouts
- **preprod**: 2FA bypass enabled, uses saved sessions, standard timeouts
- **prod**: 2FA bypass optional, may require real credentials, strict timeouts

### Optional Parameters

#### BROWSER (Optional)
Specifies the browser engine to use for testing.

**Values:** `chromium`, `firefox`, `webkit`, `safari`

**Default:** `chromium`

**Purpose:**
- Selects Playwright browser engine
- Tests cross-browser compatibility
- Session files are separate per browser

**Examples:**
```bash
BROWSER=chromium TEST_ENV=test pytest tests/
BROWSER=firefox TEST_ENV=test pytest tests/
BROWSER=webkit TEST_ENV=test pytest tests/
BROWSER=safari TEST_ENV=test pytest tests/  # macOS only
```

**Note:** Safari browser only works on macOS. Use `webkit` for cross-platform Safari engine.

#### DEVICE (Optional)
Specifies the device profile for emulation.

**Values:**
- `desktop` (default)
- `iphone`, `iphone_12`, `iphone_13`, `iphone_14`, `iphone_15`
- `android`, `android_pixel`, `android_galaxy`

**Default:** `desktop`

**Purpose:**
- Emulates mobile device viewports, user agent, touch capabilities
- Tests responsive design and mobile interactions
- Different device profiles loaded from `refua_core/config/devices.json`

**Examples:**
```bash
DEVICE=desktop TEST_ENV=test pytest tests/
DEVICE=iphone TEST_ENV=test pytest tests/
DEVICE=iphone_14 TEST_ENV=test pytest tests/
DEVICE=android TEST_ENV=test pytest tests/
```

**Note:** Each device has its own session file: `auth_state_test_iphone_latest.json`, etc.

#### SKIP_2FA (Optional)
Controls whether to bypass 2FA using saved session files.

**Values:** `true`, `false`

**Default:**
- `true` for test/preprod (uses saved sessions)
- `false` for prod (requires real credentials)

**Purpose:**
- `true`: Uses pre-captured session JSON file (no manual 2FA needed)
- `false`: Uses real credentials from `.env` file (requires 2FA interaction or automated handling)

**Examples:**
```bash
# Use saved session (no 2FA prompt)
SKIP_2FA=true TEST_ENV=test pytest tests/

# Use real credentials (may require 2FA)
SKIP_2FA=false TEST_ENV=test pytest tests/

# Override production default (use session instead of real auth)
SKIP_2FA=true TEST_ENV=prod pytest tests/
```

**How Sessions Work:**
1. Capture: `python scripts/capture_session.py --env test --user john.doe`
2. Stored: `~/.refua_sessions/auth_state_test_chromium_latest.json`
3. Load: Automatically used when `SKIP_2FA=true` (default)
4. Expire: Valid for 3 days, then must recapture

#### SESSION_DIR (Optional)
Specifies where session files are stored.

**Values:** File path (absolute or `~` for home)

**Default:** `~/.refua_sessions/`

**Purpose:**
- Allows custom session storage location
- Essential for Docker/container execution (external volume mount)
- Supports different session directories for different test environments

**Examples:**
```bash
# Use default location
TEST_ENV=test pytest tests/

# Use custom directory
SESSION_DIR=/custom/sessions TEST_ENV=test pytest tests/

# Docker with volume mount
SESSION_DIR=/sessions TEST_ENV=test pytest tests/

# Network path (if supported)
SESSION_DIR=/mnt/shared/sessions TEST_ENV=test pytest tests/
```

**File Structure:**
```
~/.refua_sessions/
├── auth_state_test_chromium_latest.json
├── auth_state_test_firefox_latest.json
├── auth_state_test_webkit_latest.json
├── auth_state_preprod_chromium_latest.json
└── auth_state_prod_chromium_latest.json
```

#### RECORD_VIDEO (Optional)
Enables/disables test video recording.

**Values:** `true`, `false`

**Default:** `true`

**Purpose:**
- `true`: Records test execution as video (useful for debugging failures)
- `false`: Skips video recording (faster execution, less disk usage)

**Examples:**
```bash
# Record all tests
RECORD_VIDEO=true TEST_ENV=test pytest tests/

# Disable recording
RECORD_VIDEO=false TEST_ENV=test pytest tests/

# Disable recording for faster execution
RECORD_VIDEO=false CAPTURE_SCREENSHOTS=false TEST_ENV=test pytest tests/ -n auto
```

**Behavior:**
- Passing tests: Videos automatically deleted (saves storage)
- Failed tests: Videos retained in `./test-artifacts/`

#### CAPTURE_SCREENSHOTS (Optional)
Enables/disables test screenshot capture.

**Values:** `true`, `false`

**Default:** `true`

**Purpose:**
- `true`: Captures screenshots at test key points
- `false`: Skips screenshot capture (faster execution)

**Examples:**
```bash
# Capture screenshots
CAPTURE_SCREENSHOTS=true TEST_ENV=test pytest tests/

# Disable screenshots
CAPTURE_SCREENSHOTS=false TEST_ENV=test pytest tests/
```

## Pytest Options (AFTER pytest)

These are standard pytest options passed AFTER the `pytest` command. They control test selection and output, not test behavior.

### Common Options

#### -v, --verbose
Verbose output showing each test

```bash
TEST_ENV=test pytest -v tests/
```

#### -q, --quiet
Minimal output

```bash
TEST_ENV=test pytest -q tests/
```

#### -s
Don't capture stdout (show print statements)

```bash
TEST_ENV=test pytest -s tests/
```

#### -k PATTERN
Run tests matching pattern

```bash
TEST_ENV=test pytest -k "login" tests/
TEST_ENV=test pytest -k "test_auth and not slow" tests/
```

#### -m MARKER
Run tests with specific marker

```bash
TEST_ENV=test pytest -m smoke tests/
TEST_ENV=test pytest -m "regression and not slow" tests/
```

#### -x
Stop on first failure

```bash
TEST_ENV=test pytest -x tests/
```

#### --tb=FORMAT
Set traceback format (short, long, line, native)

```bash
TEST_ENV=test pytest --tb=short tests/
```

#### -n WORKERS
Run tests in parallel (requires pytest-xdist)

```bash
TEST_ENV=test pytest -n auto tests/
TEST_ENV=test pytest -n 4 tests/
```

#### --dist=STRATEGY
Distribution strategy for parallel execution (loadscope, loadgroup, worksteal)

```bash
TEST_ENV=test pytest -n auto --dist=loadscope tests/
```

#### --alluredir=PATH
Generate Allure test reports

```bash
TEST_ENV=test pytest --alluredir=./allure-results tests/
```

#### --log-cli-level=LEVEL
Set logging level for console output (DEBUG, INFO, WARNING, ERROR)

```bash
TEST_ENV=test pytest --log-cli-level=DEBUG tests/
```

## Command Examples

### 1. Basic Execution
```bash
TEST_ENV=test pytest tests/
```
- Environment: test
- Browser: chromium (default)
- Device: desktop (default)
- 2FA: bypass enabled (default)

### 2. Specific Browser
```bash
BROWSER=firefox TEST_ENV=test pytest tests/
```
- Browser: Firefox
- Other parameters: defaults

### 3. Mobile Device
```bash
DEVICE=iphone TEST_ENV=test pytest tests/
```
- Device: iPhone (iphone_14 model)
- Other parameters: defaults

### 4. Specific Browser + Device
```bash
BROWSER=webkit DEVICE=iphone_14 TEST_ENV=test pytest tests/
```
- Browser: WebKit (Safari engine)
- Device: iPhone 14
- 2FA: bypass enabled

### 5. With Verbose Output
```bash
TEST_ENV=test pytest -v tests/
```
- Adds pytest verbose output
- Shows each test as it runs

### 6. With Test Filtering
```bash
TEST_ENV=test pytest -k "login" tests/
TEST_ENV=test pytest -m smoke tests/
```
- Runs only matching tests
- `-k` for test name pattern
- `-m` for marker

### 7. Parallel Execution
```bash
TEST_ENV=test pytest -n auto tests/
TEST_ENV=test pytest -n 4 --dist=loadscope tests/
```
- `-n auto`: Use all CPU cores
- `-n 4`: Use 4 workers
- `--dist=loadscope`: Better for multi-device testing

### 8. With Allure Reporting
```bash
TEST_ENV=test pytest --alluredir=./allure-results tests/
allure serve ./allure-results
```
- Generates Allure report
- Serves report in browser

### 9. Custom Session Directory (Docker)
```bash
SESSION_DIR=/sessions TEST_ENV=test pytest tests/
```
- Uses mounted volume for sessions
- Essential for Docker containers

### 10. Full Example (All Parameters)
```bash
TEST_ENV=test \
BROWSER=webkit \
DEVICE=iphone_14 \
SKIP_2FA=true \
SESSION_DIR=~/.refua_sessions \
RECORD_VIDEO=true \
CAPTURE_SCREENSHOTS=true \
pytest tests/ -v -n auto --alluredir=./allure-results -m smoke
```

### 11. Production Environment
```bash
TEST_ENV=prod SKIP_2FA=false pytest tests/
```
- Requires real credentials from `.env.prod`
- Uses credentials instead of saved session

### 12. Multi-Environment Sequential Execution
```bash
TEST_ENV=test pytest tests/
TEST_ENV=preprod pytest tests/
TEST_ENV=prod pytest tests/
```
- Tests each environment sequentially

### 13. Multi-Device Parallel Execution
```bash
TEST_ENV=test DEVICE=desktop pytest -n 4 --alluredir=./allure-results/desktop &
TEST_ENV=test DEVICE=iphone pytest -n 4 --alluredir=./allure-results/ios &
TEST_ENV=test DEVICE=android pytest -n 4 --alluredir=./allure-results/android &
wait
```
- Runs tests on different devices in parallel
- Each device gets 4 parallel workers
- Results separated by device

### 14. Performance/Debug Mode
```bash
TEST_ENV=test pytest --log-cli-level=DEBUG tests/
TEST_ENV=test pytest -s tests/  # Don't capture output
```
- Enables detailed logging
- Shows print statements

### 15. CI/CD Pipeline
```bash
set -e  # Exit on first error

# Capture sessions for all browsers
python scripts/capture_session.py --env test --user ci_user --browser chromium
python scripts/capture_session.py --env test --user ci_user --browser firefox

# Run tests in parallel with reporting
TEST_ENV=test \
  RECORD_VIDEO=true \
  CAPTURE_SCREENSHOTS=true \
  pytest -n auto \
  --alluredir=./allure-results \
  --tb=short \
  -v \
  tests/

# Generate and publish report
allure generate ./allure-results -o ./allure-html
```

## Environment Variables in .env Files

These are different from execution parameters - they're credentials stored in test repository:

```bash
# .env.test
TEST_USER_EMAIL=user@test.local
TEST_USER_PASSWORD=password123
TEST_USER_PHONE=+1234567890

# .env.preprod
PREPROD_USER_EMAIL=user@preprod.local
PREPROD_USER_PASSWORD=password456

# .env.prod
PROD_USER_EMAIL=user@production.com
PROD_USER_PASSWORD=production_password
```

**Note:** Never commit `.env` files to version control.

## Troubleshooting

### "TEST_ENV not set"
```bash
# Wrong
pytest tests/

# Correct
TEST_ENV=test pytest tests/
```

### Session file not found
```bash
# Capture session first
python scripts/capture_session.py --env test --user john.doe

# Then run tests
TEST_ENV=test pytest tests/
```

### Browser not launching
```bash
# Ensure browser is supported
BROWSER=chrome TEST_ENV=test pytest tests/  # WRONG - chrome not supported

# Use supported browser
BROWSER=chromium TEST_ENV=test pytest tests/  # Correct
```

### Parameters not being applied
```bash
# Check order - environment variables MUST come first
TEST_ENV=test BROWSER=firefox pytest tests/  # Correct
pytest -v TEST_ENV=test BROWSER=firefox tests/  # Wrong
```

## Reference

### Parameter Order in Command
```
[ENV_VARS] pytest [PYTEST_OPTIONS] [TEST_PATH]

Example:
TEST_ENV=test BROWSER=firefox DEVICE=iphone pytest -v -n 4 tests/
└─────────────┬──────────────────────────────────┘  └────────────┘  └────┘
         Env Vars                              Pytest Options      Test Path
```

### All Environment Variables
| Variable | Values | Default | Purpose |
|----------|--------|---------|---------|
| TEST_ENV | test, preprod, prod | None (required) | Target environment |
| BROWSER | chromium, firefox, webkit, safari | chromium | Browser engine |
| DEVICE | desktop, iphone*, android* | desktop | Device emulation |
| SKIP_2FA | true, false | true (test/preprod) | 2FA bypass |
| SESSION_DIR | file path | ~/.refua_sessions | Session storage |
| RECORD_VIDEO | true, false | true | Video recording |
| CAPTURE_SCREENSHOTS | true, false | true | Screenshot capture |

### Common Pytest Options
| Option | Purpose |
|--------|---------|
| -v, --verbose | Verbose output |
| -q, --quiet | Minimal output |
| -s | Show print statements |
| -k PATTERN | Filter by pattern |
| -m MARKER | Filter by marker |
| -x | Stop on first failure |
| --tb=FORMAT | Traceback format |
| -n WORKERS | Parallel workers |
| --alluredir=PATH | Allure report path |
| --log-cli-level=LEVEL | Logging level |
