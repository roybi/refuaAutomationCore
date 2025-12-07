# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**refuaAutomationCore** is a test automation framework for the MEDITEK medical system built with Python and Playwright. The architecture separates the **core framework** (reusable infrastructure and page object models) from the **test framework** (test implementation). It supports multi-environment execution (test, preprod, prod) with secure 2FA handling and Allure reporting integration.

## Project Structure

### Core Framework (`refua_core/`)

Reusable infrastructure and page object models for automation:

- **`refua_core/config/`** - Configuration and session management

  - `environment.py`: Centralized environment configuration (base URLs, API endpoints, credentials, auth settings). Uses `EnvironmentManager` singleton pattern. Loads settings from `TEST_ENV` environment variable and credentials from `.env` files per environment.
  - `session_manager.py`: Manages 2FA bypass via session JSON files in external directory. Validates session state (cookies, localStorage, metadata) before test execution and provides auth failure detection with meaningful error messages.
  - `device_config.py` or `devices.json`: Mobile device configuration (iPhone/Android profiles). Defines device viewport, user agent, and device-specific settings for Playwright emulation.

- **`refua_core/core/`** - Core testing infrastructure

  - `base_test.py`: Base test class for Playwright-based tests with session validation hooks
  - `device_manager.py`: Manages device emulation for mobile testing (iOS/Android setup)
  - `visual_regression.py`: Visual regression testing with Figma integration. Compares actual pages against Figma design frames automatically during test execution
  - `artifact_manager.py`: Manages test artifacts (videos, screenshots). Automatically captures on test execution and conditionally saves based on pass/fail status. Deletes passing test artifacts, retains failing test artifacts for debugging

- **`refua_core/pages/`** - Page Object Models (POM)
  - `mainPage.py`: Main page object for MEDITEK UI interactions
  - Additional page objects extend base POM pattern for page-specific interactions
  - All page interactions encapsulated to support maintainability and reusability
  - Responsive design support for mobile and desktop viewports

### Test Framework (`tests/`)

Test implementation using pytest with Allure reporting:

- **`tests/`** - Pytest test cases and fixtures
  - Test organization by feature/module
  - Support for markers: `@pytest.mark.smoke`, `@pytest.mark.regression`, `@pytest.mark.2fa_required`, etc.
  - Future support for Gherkin-style BDD tests via pytest plugins

### Key Design Patterns

1. **Singleton Pattern** (`EnvironmentManager`): Single environment instance across all tests
2. **Page Object Model**: UI interactions encapsulated in page classes for maintainability
3. **Session State Management**: 2FA bypass via separate session capture script with external storage, validated before each test
4. **Configuration Externalization**: Environment-specific credentials in `.env` files, session states in external JSON directory
5. **Device Emulation**: Mobile device profiles (iOS/Android) defined in separate config, selectable per test execution
6. **Visual Regression Testing**: Page objects include optional Figma design frame URLs for automatic UI comparison. Visual checks only run if `FIGMA_FRAME_URL` is set (not null), detected during test execution
7. **Artifact Management**: Automatic video and screenshot capture during test execution. On test pass: artifacts automatically deleted. On test fail: artifacts retained in timestamped directory for debugging. Works seamlessly on local machines and Docker containers

## Development Commands

### Setup and Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Running Tests

#### Basic Test Execution

```bash
# Run all tests for an environment with Allure reporting
TEST_ENV=test pytest --alluredir=./allure-results

# Run tests with verbose output and Allure report
TEST_ENV=test pytest -v --alluredir=./allure-results

# Run a specific test file
TEST_ENV=test pytest tests/test_file.py --alluredir=./allure-results

# Run a specific test function
TEST_ENV=test pytest tests/test_file.py::test_function --alluredir=./allure-results
```

#### Test Selection and Grouping

```bash
# Run tests by marker (smoke tests)
TEST_ENV=test pytest -m smoke --alluredir=./allure-results

# Run tests by marker (regression tests)
TEST_ENV=test pytest -m regression --alluredir=./allure-results

# Run tests matching a pattern
TEST_ENV=test pytest -k "login" --alluredir=./allure-results

# Run tests excluding a pattern
TEST_ENV=test pytest --ignore=tests/slow_tests/ --alluredir=./allure-results

# Run tests with multiple markers
TEST_ENV=test pytest -m "smoke and not 2fa_required" --alluredir=./allure-results
```

#### 2FA Authentication Options

```bash
# Option 1: Use saved session JSON (skip 2FA)
TEST_ENV=test SKIP_2FA=true pytest --alluredir=./allure-results

# Option 2: Use real user credentials (requires 2FA interaction)
# Credentials loaded from environment-specific .env file
TEST_ENV=test SKIP_2FA=false pytest --alluredir=./allure-results

# Option 3: Specify custom session storage path
# Sessions stored in external directory: ~/.refua_sessions/
TEST_ENV=test SESSION_DIR=~/.refua_sessions pytest --alluredir=./allure-results
```

#### Mobile Device Testing

```bash
# Run tests on iPhone device
TEST_ENV=test DEVICE=iphone pytest --alluredir=./allure-results

# Run tests on Android device
TEST_ENV=test DEVICE=android pytest --alluredir=./allure-results

# Run tests on specific device model
TEST_ENV=test DEVICE=iphone_14 pytest --alluredir=./allure-results

# Run same tests on multiple devices (sequential)
TEST_ENV=test DEVICE=iphone,android pytest --alluredir=./allure-results

# Run on desktop (default)
TEST_ENV=test DEVICE=desktop pytest --alluredir=./allure-results
```

#### Parallel Test Execution

Tests can run in parallel to reduce total execution time. Parallel execution requires `pytest-xdist`:

```

#### Multi-Browser Testing

Tests support multiple browser engines: chromium, firefox, webkit, and safari. Select browser via `BROWSER` environment variable:

```bash
# Run tests with default browser (chromium)
TEST_ENV=test pytest --alluredir=./allure-results

# Run tests with Firefox browser
BROWSER=firefox TEST_ENV=test pytest --alluredir=./allure-results

# Run tests with WebKit browser (Safari engine)
BROWSER=webkit TEST_ENV=test pytest --alluredir=./allure-results

# Run tests with Safari browser
BROWSER=safari TEST_ENV=test pytest --alluredir=./allure-results

# Run tests with multiple browsers (sequential)
BROWSER=chromium TEST_ENV=test pytest -v --alluredir=./allure-results/chromium
BROWSER=firefox TEST_ENV=test pytest -v --alluredir=./allure-results/firefox
BROWSER=webkit TEST_ENV=test pytest -v --alluredir=./allure-results/webkit

# Run with browser-specific marker
BROWSER=firefox TEST_ENV=test pytest -m "not ios_only" --alluredir=./allure-results

# Combine with other options
BROWSER=webkit TEST_ENV=test DEVICE=iphone pytest --alluredir=./allure-results
```

**Supported Browsers:**

- `chromium` - Chromium/Chrome (default)
- `firefox` - Firefox
- `webkit` - WebKit (Safari engine)
- `safari` - Safari (macOS only)

**Notes:**
- Default browser is chromium if BROWSER not specified
- Safari browser (native) only works on macOS
- WebKit is the recommended cross-platform alternative to Safari
- Browser selection works with all other test options
bash
# Run with detailed logging
TEST_ENV=test pytest --log-cli-level=DEBUG --alluredir=./allure-results

# Run tests in parallel (auto-detect CPU cores)
TEST_ENV=test pytest -n auto --alluredir=./allure-results

# Run tests with specific number of workers (4 parallel workers)
TEST_ENV=test pytest -n 4 --alluredir=./allure-results

# Run parallel tests with distribution strategy (load balancing)
TEST_ENV=test pytest -n auto --dist=loadscope --alluredir=./allure-results

# Run parallel tests on specific device with multiple workers
TEST_ENV=test DEVICE=iphone pytest -n 2 --alluredir=./allure-results

# Run tests in parallel across multiple environments (sequential environments, parallel tests)
TEST_ENV=test pytest -n auto --alluredir=./allure-results/test
TEST_ENV=preprod pytest -n auto --alluredir=./allure-results/preprod
```

**Parallel Execution Options:**

- `-n auto`: Auto-detect number of CPU cores and use that many workers
- `-n 4`: Use exactly 4 parallel workers
- `--dist=loadscope`: Distribute tests by scope (class/module) for better resource sharing
- `--dist=loadgroup`: Group tests by pytest marker (better for device testing)
- `--dist=worksteal`: Work-stealing scheduler for load balancing

#### Advanced Options

```bash
# Run with coverage report
TEST_ENV=test pytest --cov=refua_core --cov-report=html --alluredir=./allure-results

# Run in parallel with coverage
TEST_ENV=test pytest -n auto --cov=refua_core --cov-report=html --alluredir=./allure-results

# Generate and view Allure report (requires allure command line)
allure serve ./allure-results
```

### Execution Parameters

- **`TEST_ENV`** (required): Target environment

  - `test`: Test environment, supports 2FA bypass
  - `preprod`: Pre-production environment, supports 2FA bypass
  - `prod`: Production environment, requires real user auth or pre-captured session

- **`SKIP_2FA`** (optional, default: `true` for test/preprod, `false` for prod):

  - `true`: Uses saved session JSON file to bypass 2FA (no user interaction required)
  - `false`: Uses real user credentials from `.env` file (requires 2FA interaction)

- **`SESSION_DIR`** (optional): External session storage directory

  - Default: `~/.refua_sessions/`
  - Stores: `auth_state_{TEST_ENV}_{DEVICE}_{timestamp}.json`
  - Must be outside project directory for security and portability

- **`DEVICE`** (optional, default: `desktop`): Target device for testing

  - `desktop`: Standard desktop browser (1920x1080)
  - `iphone`: iPhone emulation (default: iPhone 14)
  - `iphone_12`, `iphone_13`, `iphone_14`, `iphone_15`: Specific iPhone models
  - `android`: Android emulation (default: Pixel 5)
  - `android_pixel`, `android_galaxy`: Specific Android models
  - `iphone,android`: Run tests sequentially on multiple devices
  - Device profiles loaded from `refua_core/config/devices.json`

- **`BROWSER`** (optional, default: `chromium`): Browser engine for testing

  - `chromium`: Chromium/Chrome (default)
  - `firefox`: Firefox
  - `webkit`: WebKit (Safari engine, cross-platform)
  - `safari`: Safari (macOS only)

- **`DEBUG_AUTH`** (optional): Set to `true` for detailed auth logging
- **`DEBUG_DEVICE`** (optional): Set to `true` for device emulation details

### Parallel Execution Configuration

#### pytest-xdist Setup

```bash
# Install pytest-xdist for parallel execution
pip install pytest-xdist
```

#### Pytest Configuration (`pytest.ini`)

```ini
[pytest]
# Parallel execution settings
workers = auto
dist = loadscope

# Markers for test organization
markers =
    smoke: smoke tests
    regression: regression tests
    mobile: mobile-specific tests
    ios_only: iOS-only tests
    android_only: Android-only tests
    slow: slow running tests
    2fa_required: requires 2FA authentication
    sequential: must run sequentially (cannot parallelize)

# Allure configuration
addopts = --alluredir=./allure-results
```

#### Parallel Execution Strategies

**Strategy 1: Test Class/Module Scope Distribution**

```bash
# Distributes tests by class/module scope (recommended for most cases)
TEST_ENV=test pytest -n auto --dist=loadscope --alluredir=./allure-results
```

- Each worker gets complete test classes/modules
- Better for tests with shared setup/teardown
- Minimal test isolation issues

**Strategy 2: Pytest Marker-Based Distribution**

```bash
# Groups tests by marker - useful for device-specific tests
TEST_ENV=test pytest -n auto --dist=loadgroup --alluredir=./allure-results
```

- Groups tests with same markers to same worker
- Optimal for device testing (all iPhone tests on one worker, all Android on another)
- Requires markers: `@pytest.mark.mobile`, `@pytest.mark.ios_only`, etc.

**Strategy 3: Work-Stealing Scheduler**

```bash
# Balanced work distribution - workers steal tasks when idle
TEST_ENV=test pytest -n auto --dist=worksteal --alluredir=./allure-results
```

- Best for heterogeneous test durations
- Prevents fast workers from idle time
- Slightly higher overhead

**Strategy 4: Custom Worker Count**

```bash
# Use specific number of workers (useful for resource-constrained machines)
TEST_ENV=test pytest -n 2 --alluredir=./allure-results  # 2 workers

# Use half available cores
TEST_ENV=test pytest -n $(( $(nproc) / 2 )) --alluredir=./allure-results  # Linux/Mac
```

#### Parallel Execution with Multiple Devices

```bash
# Desktop and mobile in parallel with load balancing
TEST_ENV=test pytest -n auto --dist=loadgroup \
  -m "not sequential" \
  --alluredir=./allure-results

# iOS tests in parallel
TEST_ENV=test DEVICE=iphone pytest -n 4 --alluredir=./allure-results/ios

# Android tests in parallel (separate from iOS)
TEST_ENV=test DEVICE=android pytest -n 4 --alluredir=./allure-results/android

# Desktop tests in parallel
TEST_ENV=test DEVICE=desktop pytest -n auto --alluredir=./allure-results/desktop
```

**Resource Considerations:**

- Each parallel worker launches its own browser instance
- Memory usage multiplies by number of workers
- Recommended: 1 worker per 1GB available RAM
- Monitor: `watch -n 1 'free -h'` (Linux/Mac) or Task Manager (Windows)

#### Sequential Test Execution (When Parallel Not Suitable)

```bash
# Mark tests that must run sequentially
@pytest.mark.sequential
def test_shared_state():
    """Test that modifies shared state"""
    pass

# Run with sequential tests in serial, others in parallel
TEST_ENV=test pytest -n auto -m "not sequential" --alluredir=./allure-results
```

### Environment Variables

- **`TEST_ENV`** (required): Target environment - `test`, `preprod`, or `prod`
- **`SKIP_2FA`** (optional): Override 2FA bypass behavior - `true` or `false`
- **`SESSION_DIR`** (optional): External session storage path (default: `~/.refua_sessions/`)
- **`DEVICE`** (optional): Device profile - `desktop`, `iphone`, `android`, or model name
- **`BROWSER`** (optional): Browser engine - `chromium`, `firefox`, `webkit`, or `safari` (default: `chromium`)
- **`DEBUG_AUTH`** (optional): Set to `true` for detailed auth logging
- **`DEBUG_DEVICE`** (optional): Set to `true` for device emulation logging
- **`PYTEST_XDIST_WORKER_COUNT`** (optional): Override worker count (alternative to `-n` flag)

### Authentication and Sessions

#### 2FA Session Capture Script

A separate script captures authenticated browser sessions to bypass 2FA during automated testing. Sessions are stored in an **external directory outside the project** for security and portability (~/.refua_sessions/). Supports capturing sessions for **ALL supported browsers** (chromium, firefox, webkit, safari) with separate session files per browser per environment.

**Purpose:** Capture sessions ONCE per environment/browser combination, then reuse for all tests. Eliminates need for manual 2FA interaction on every test run. Supports both single-browser and batch multi-browser capture.

**Multi-Browser Support:**

The script can capture authenticated sessions for all supported browsers:
- **Chromium**: Default, best compatibility, fastest
- **Firefox**: Alternative to Chromium, good compatibility
- **WebKit**: Safari-compatible browser engine, mobile testing
- **Safari**: macOS only, native Safari engine (requires macOS)

**Usage Examples:**

```bash
# Capture sessions for ALL supported browsers (default)
python scripts/capture_session.py --env test --user john.doe
# Creates: auth_state_test_chromium_latest.json
#          auth_state_test_firefox_latest.json
#          auth_state_test_webkit_latest.json
#          auth_state_test_safari_latest.json (macOS only)

# Capture session for specific browser only
python scripts/capture_session.py --env test --user john.doe --browser chromium
python scripts/capture_session.py --env test --user john.doe --browser firefox
python scripts/capture_session.py --env test --user john.doe --browser webkit
python scripts/capture_session.py --env test --user john.doe --browser safari

# Capture for preprod environment (all browsers)
python scripts/capture_session.py --env preprod --user john.doe

# Capture for production (if 2FA bypass enabled, all browsers)
python scripts/capture_session.py --env prod --user john.doe

# Docker volume mount support (external session storage)
SESSION_DIR=/sessions python scripts/capture_session.py --env test --user john.doe
python scripts/capture_session.py --env test --user john.doe --session-dir /sessions

# Capture for iPhone device with all browsers
python scripts/capture_session.py --env test --user john.doe --device iphone

# Capture for specific browser and device
python scripts/capture_session.py --env test --user john.doe --device iphone --browser webkit
```

**Script Flow (Multi-Browser Batch Capture):**

When running without `--browser` or with `--browser all`:

1. Validates environment (test, preprod, prod)
2. Creates/verifies session directory (respects SESSION_DIR env var)
3. **For each supported browser (chromium, firefox, webkit, safari):**
   - Launches browser with headless=false (interactive window)
   - Navigates to login page: `{base_url}/login`
   - Waits for user to complete login + 2FA manually (5-minute timeout)
   - Detects successful authentication
   - Saves session with browser-specific filename: `auth_state_{env}_{browser}_latest.json`
   - If browser fails: logs error and continues to next browser
4. **Displays summary with:**
   - Successfully captured sessions (browser and file path)
   - Failed browsers (if any) with error details
   - Session expiration date (now + 3 days)

**Session Storage:**

```
~/.refua_sessions/
├── auth_state_test_chromium_latest.json       # Test env, Chromium browser
├── auth_state_test_firefox_latest.json        # Test env, Firefox browser
├── auth_state_test_webkit_latest.json         # Test env, WebKit browser
├── auth_state_test_safari_latest.json         # Test env, Safari browser (macOS)
├── auth_state_preprod_chromium_latest.json    # Preprod env, Chromium browser
├── auth_state_preprod_firefox_latest.json     # Preprod env, Firefox browser
├── auth_state_preprod_webkit_latest.json      # Preprod env, WebKit browser
├── auth_state_preprod_safari_latest.json      # Preprod env, Safari browser (macOS)
├── auth_state_prod_chromium_latest.json       # Production env, Chromium browser
├── auth_state_prod_firefox_latest.json        # Production env, Firefox browser
├── auth_state_prod_webkit_latest.json         # Production env, WebKit browser
└── auth_state_prod_safari_latest.json         # Production env, Safari browser (macOS)
```

**Docker Volume Support:**

For Docker containers, mount external volume at `/sessions`:

```bash
# Docker run with external session storage
docker run -v ~/.refua_sessions:/sessions myimage \
  python scripts/capture_session.py --env test --user john.doe --session-dir /sessions

# Docker compose configuration
services:
  test-automation:
    volumes:
      - ./sessions:/sessions  # Mount external sessions directory
    environment:
      - SESSION_DIR=/sessions  # Tell script where to store sessions
    command: python scripts/capture_session.py --env test --user john.doe
```

**Session File Contents (Same Structure for All Browsers):**

```json
{
  "storage_state": {
    "cookies": [
      {
        "name": "session_token",
        "value": "...",
        "domain": ".meditek.local",
        "expires": 1234567890
      }
    ],
    "origins": [
      {
        "origin": "https://meditik.test.medical.idf.il",
        "localStorage": [{"name": "auth_token", "value": "..."}]
      }
    ]
  },
  "metadata": {
    "captured_at": "2025-12-07T14:30:00Z",
    "expires_at": "2025-12-10T14:30:00Z",
    "url": "https://meditik.test.medical.idf.il/home",
    "title": "MEDITEK Dashboard",
    "environment": "https://meditik.test.medical.idf.il/home"
  },
  "tokens": {
    "auth_token": "..."
  }
}
```

**Key Features:**

- **Multi-Browser Capture**: Captures sessions for all supported browsers (chromium, firefox, webkit, safari) in one run
- **Separate Session Files**: Each browser gets its own session file per environment (e.g., `auth_state_test_chromium_latest.json`)
- **Batch Capture**: Default behavior captures all browsers; continue on browser failure
- **Selective Capture**: Use `--browser` flag to capture specific browser only
- **3-Day TTL**: Sessions valid for 3 days, then must be recaptured
- **External Storage**: Sessions stored outside project for security and Docker portability
- **Automatic Loading**: Tests automatically load appropriate browser's session without user interaction
- **Environment-Specific**: Each environment (test, preprod, prod) has separate sessions per browser
- **Docker Ready**: Respects SESSION_DIR environment variable for Docker volume mounts
- **Error Recovery**: Clear error messages if session missing or expired; gracefully handles browser-specific failures

**Session Lifespan:**

- Captured: User completes login + 2FA manually per browser
- Valid: 3 days from capture time
- Expired: Must re-run capture script to refresh
- Re-captured: New session overwrites old one (same filename per browser)

#### Using Sessions in Tests

Tests automatically load the appropriate browser's captured session without requiring user interaction.

```bash
# Automated tests use captured session automatically (desktop, chromium)
TEST_ENV=test SKIP_2FA=true pytest --alluredir=./allure-results

# Run tests on Firefox browser
BROWSER=firefox TEST_ENV=test SKIP_2FA=true pytest --alluredir=./allure-results

# Run tests on WebKit browser (Safari-compatible)
BROWSER=webkit TEST_ENV=test SKIP_2FA=true pytest --alluredir=./allure-results

# Run tests on Safari browser (macOS only)
BROWSER=safari TEST_ENV=test SKIP_2FA=true pytest --alluredir=./allure-results

# Run tests on iPhone with captured session
TEST_ENV=test DEVICE=iphone SKIP_2FA=true pytest --alluredir=./allure-results

# Run tests on Android with captured session
TEST_ENV=test DEVICE=android SKIP_2FA=true pytest --alluredir=./allure-results

# Run tests on iPhone with specific browser
BROWSER=webkit TEST_ENV=test DEVICE=iphone SKIP_2FA=true pytest --alluredir=./allure-results

# Run tests in parallel with multi-browser sessions
TEST_ENV=test SKIP_2FA=true pytest -n auto --alluredir=./allure-results

# Run specific browser in parallel
BROWSER=firefox TEST_ENV=test SKIP_2FA=true pytest -n 4 --alluredir=./allure-results

# To force re-authentication (not recommended for 2FA systems):
TEST_ENV=test SKIP_2FA=false pytest --alluredir=./allure-results  # Uses credentials from .env file

# Use custom session directory (Docker volumes)
TEST_ENV=test SESSION_DIR=/sessions SKIP_2FA=true pytest --alluredir=./allure-results

# Docker with multi-browser sessions
docker run -v ~/.refua_sessions:/sessions myimage \
  bash -c "BROWSER=firefox TEST_ENV=test SESSION_DIR=/sessions SKIP_2FA=true pytest --alluredir=./allure-results"
```

**Multi-Browser Test Execution Strategy:**

```bash
# Sequential execution: test all 4 browsers one after another
for browser in chromium firefox webkit safari; do
  BROWSER=$browser TEST_ENV=test SKIP_2FA=true pytest --alluredir=./allure-results/browser_$browser
done

# Parallel execution: test different browsers with different workers
TEST_ENV=test SKIP_2FA=true pytest -n auto --alluredir=./allure-results

# Device-specific browser testing
BROWSER=webkit TEST_ENV=test DEVICE=iphone SKIP_2FA=true pytest -n auto --alluredir=./allure-results
BROWSER=chromium TEST_ENV=test DEVICE=android SKIP_2FA=true pytest -n auto --alluredir=./allure-results
```

**How Session Loading Works:**

1. Tests request browser and device combination (e.g., firefox + desktop)
2. BaseTest fixture loads session from: `~/.refua_sessions/auth_state_test_firefox_latest.json`
3. Session applied to browser context (cookies, localStorage)
4. Tests run with 2FA already bypassed (no user interaction needed)
5. Test completes with authenticated session

#### Credentials Configuration

Store credentials in environment-specific `.env` files:

```
# .env.test
TEST_USER_EMAIL=test@meditek.local
TEST_USER_PASSWORD=secure_password
TEST_USER_PHONE=+1234567890  # For 2FA if required

# .env.preprod
PREPROD_USER_EMAIL=preprod@meditek.local
PREPROD_USER_PASSWORD=secure_password

# .env.prod
PROD_USER_EMAIL=user@meditek.com
PROD_USER_PASSWORD=secure_password
```

**Security Note**: Never commit `.env` files. Use environment secrets for CI/CD.

#### Mobile Device Configuration

Device profiles are defined in `refua_core/config/devices.json`:

```json
{
  "desktop": {
    "name": "Desktop",
    "viewport": { "width": 1920, "height": 1080 },
    "deviceScaleFactor": 1,
    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "locale": "en-US",
    "timezoneId": "America/New_York",
    "isMobile": false,
    "hasTouch": false
  },
  "iphone_14": {
    "name": "iPhone 14",
    "viewport": { "width": 390, "height": 844 },
    "deviceScaleFactor": 3,
    "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
    "locale": "en-US",
    "timezoneId": "America/New_York",
    "isMobile": true,
    "hasTouch": true
  },
  "iphone": { "extends": "iphone_14" },
  "android_pixel": {
    "name": "Pixel 5",
    "viewport": { "width": 393, "height": 851 },
    "deviceScaleFactor": 2.75,
    "userAgent": "Mozilla/5.0 (Linux; Android 13)",
    "locale": "en-US",
    "timezoneId": "America/New_York",
    "isMobile": true,
    "hasTouch": true
  },
  "android": { "extends": "android_pixel" }
}
```

Device profiles can be:

- **Pre-defined**: Use built-in profiles (desktop, iphone, iphone_14, android, etc.)
- **Custom**: Add new profiles to `devices.json` with specific viewport, user agent, and capabilities
- **Environment-specific**: Different devices per environment if needed (e.g., prod uses smaller set)

**Mobile Device Best Practices:**

- Always test critical flows on both iOS and Android
- Use device markers in tests: `@pytest.mark.mobile`, `@pytest.mark.ios_only`
- Verify touch interactions work on mobile devices
- Handle device-specific notifications and permissions
- Test network conditions (throttling) separately if needed

## Important Configuration

### Environment-Specific Settings

Defined in `refua_core/config/environment.py`:

| Environment | 2FA Bypass | Auth Method                              | Session Timeout | Min Login Frequency |
| ----------- | ---------- | ---------------------------------------- | --------------- | ------------------- |
| **TEST**    | Yes        | Pre-captured session JSON                | 3 days          | Every 3 days        |
| **PREPROD** | Yes        | Pre-captured session JSON                | 3 days          | Every 3 days        |
| **PROD**    | No         | Pre-captured session or real credentials | 30 minutes      | Every 30 minutes    |

### 2FA Session Management and Validation

Session validation occurs before each test execution:

1. **Session File Format**: Contains cookies, localStorage, and metadata (JSON)
2. **Validation Checks**:
   - File exists at expected path
   - Metadata valid (not expired, created for correct environment)
   - Cookies and localStorage intact
3. **Auto-Loading**: `SessionStateManager` automatically applies valid sessions to browser context
4. **Failure Detection**: Tests detect auth failures and report with meaningful error messages:
   - "Session expired" - Capture new session with script
   - "Invalid session for environment" - Ensure correct TEST_ENV
   - "Session file not found" - Run capture script
   - "Auth credentials invalid" - Update .env file or re-capture session

### Session Validation Before Tests

Tests include a setup hook that validates session state:

```python
@pytest.fixture(autouse=True)
def validate_session_before_test(request):
    """Validate session before each test"""
    session_mgr = SessionStateManager()

    # Check if session is valid for this test
    if not session_mgr.validate_session():
        pytest.skip(f"Session invalid: {session_mgr.get_last_validation_error()}")

    yield

    # Optional: verify auth still valid after test
    if request.node.get_closest_marker("2fa_required"):
        assert session_mgr.is_authenticated(), "Lost authentication during test"
```

### Test-Level Auth Error Handling

Tests can detect auth-specific failures and report appropriately:

```python
def test_user_dashboard():
    """Example test with auth error handling"""
    try:
        page.goto("/dashboard")
        # ... test logic ...
    except AuthenticationError as e:
        pytest.fail(f"Auth failed: {e.message} - {e.recovery_suggestion}")
```

## Code Patterns

### Using EnvironmentManager

```python
from refua_core.config.environment import get_env_manager, validate_environment

# Get environment configuration
env_mgr = get_env_manager()
base_url = env_mgr.get_base_url()  # Uses current TEST_ENV
api_url = env_mgr.get_api_url()

# Check if running in production
if env_mgr.is_production():
    # Production-specific logic
    pass

# Validate setup before tests
validate_environment()  # Fails fast if misconfigured
```

### Using SessionStateManager

```python
from refua_core.config.session_manager import SessionStateManager
from refua_core.config.environment import get_env_manager
from playwright.sync_api import sync_playwright

# Initialize managers
session_mgr = SessionStateManager()
env_mgr = get_env_manager()

with sync_playwright() as p:
    browser = p.chromium.launch()

    # Get session file path (uses TEST_ENV and SESSION_FILE env vars)
    session_file = session_mgr.get_session_file_path()

    # Validate session before using it
    if session_mgr.validate_session(session_file):
        context = browser.new_context(storage_state=session_file)
        page = context.new_page()
        page.goto(env_mgr.get_base_url())

        # Apply localStorage (origin-specific, must be after goto)
        session_mgr.apply_local_storage(page)

        # Session loaded - proceed with test
    else:
        error_msg = session_mgr.get_last_validation_error()
        raise RuntimeError(f"Cannot run test - {error_msg}")
```

### Capturing New Session (Separate Script)

```python
# scripts/capture_session.py - Run manually to capture session
import argparse
import os
from pathlib import Path
from refua_core.config.environment import get_env_manager
from refua_core.config.session_manager import SessionStateManager
from refua_core.core.device_manager import DeviceManager
from playwright.sync_api import sync_playwright

def capture_session(env: str, username: str, device: str = "desktop", session_dir: str = None):
    """Capture authenticated session with 2FA on specified device"""
    env_mgr = get_env_manager(env)
    session_mgr = SessionStateManager(session_dir=session_dir)
    device_mgr = DeviceManager()

    # Get device configuration
    device_config = device_mgr.get_device_config(device)
    print(f"Capturing session for {device_config['name']} on {env} environment...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser for 2FA

        # Create context with device emulation
        context = browser.new_context(**device_config)
        page = context.new_page()

        print(f"Device: {device_config['name']}")
        print(f"Viewport: {device_config['viewport']}")
        print(f"Please login to: {env_mgr.get_base_url()}")

        # Navigate to login
        page.goto(f"{env_mgr.get_base_url()}/login")

        # Wait for user to complete login and 2FA
        print("Waiting for login completion (including 2FA)...")
        page.wait_for_url(f"{env_mgr.get_base_url()}/dashboard", timeout=300000)

        # Save session after successful login
        session_path = session_mgr.save_session_state(
            context=context,
            page=page,
            env=env,
            device=device
        )
        print(f"Session captured: {session_path}")
        print(f"Valid for 3 days from capture")

        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture authenticated session")
    parser.add_argument("--env", required=True, choices=["test", "preprod", "prod"],
                        help="Target environment")
    parser.add_argument("--user", required=True, help="Username for capture")
    parser.add_argument("--device", default="desktop",
                        help="Device profile (desktop, iphone, android, etc.)")
    parser.add_argument("--session-dir", default=None,
                        help="External session storage directory (default: ~/.refua_sessions/)")
    args = parser.parse_args()

    capture_session(args.env, args.user, args.device, args.session_dir)
```

### Page Object Model (POM) Pattern

```python
from playwright.sync_api import Page, Locator

class BasePage:
    """Base page with common methods"""
    def __init__(self, page: Page):
        self.page = page

    def goto(self, path: str):
        """Navigate to path on current environment"""
        from refua_core.config.environment import get_env_manager
        env_mgr = get_env_manager()
        self.page.goto(f"{env_mgr.get_base_url()}{path}")

    def wait_for_url(self, path: str, timeout: int = 30000):
        """Wait for URL navigation"""
        from refua_core.config.environment import get_env_manager
        env_mgr = get_env_manager()
        full_url = f"{env_mgr.get_base_url()}{path}"
        self.page.wait_for_url(full_url, timeout=timeout)

class LoginPage(BasePage):
    """Login page object"""
    def __init__(self, page: Page):
        super().__init__(page)
        self.email_input: Locator = page.locator("[data-testid='email']")
        self.password_input: Locator = page.locator("[data-testid='password']")
        self.login_button: Locator = page.locator("[data-testid='login-btn']")

    def login(self, email: str, password: str):
        """Perform login"""
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.login_button.click()

class DashboardPage(BasePage):
    """Dashboard page object"""
    def __init__(self, page: Page):
        super().__init__(page)
        self.user_menu: Locator = page.locator("[data-testid='user-menu']")
        self.logout_button: Locator = page.locator("[data-testid='logout']")

    def click_user_menu(self):
        """Click user menu"""
        self.user_menu.click()

    def logout(self):
        """Logout"""
        self.click_user_menu()
        self.logout_button.click()
```

### Using DeviceManager for Mobile Testing

```python
from refua_core.core.device_manager import DeviceManager
from playwright.sync_api import sync_playwright

device_mgr = DeviceManager()

# Get device configuration
iphone_config = device_mgr.get_device_config("iphone")
android_config = device_mgr.get_device_config("android")

# List all available devices
devices = device_mgr.list_available_devices()
print(f"Available devices: {devices}")  # ['desktop', 'iphone', 'iphone_14', 'android', ...]

with sync_playwright() as p:
    browser = p.chromium.launch()

    # Create context with iPhone emulation
    context = browser.new_context(**iphone_config)
    page = context.new_page()

    # Test on mobile viewport
    page.goto("https://app.meditek.local")
    # ... mobile-specific test logic ...

    context.close()
    browser.close()
```

### Using Page Objects in Tests

```python
import pytest
from refua_core.core.base_test import BaseTest
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage

class TestUserWorkflow(BaseTest):
    """Test user workflow using page objects"""

    def test_login_and_navigate(self):
        """Test login and dashboard navigation"""
        # Using page objects for all interactions
        login_page = LoginPage(self.page)
        login_page.goto("/login")

        dashboard_page = DashboardPage(self.page)
        login_page.login("user@test.com", "password")
        dashboard_page.wait_for_url("/dashboard")

        # Verify user menu visible
        assert dashboard_page.user_menu.is_visible()

class TestMobileWorkflow(BaseTest):
    """Test mobile-specific interactions"""

    @pytest.mark.mobile
    @pytest.mark.ios_only
    def test_mobile_navigation_menu(self):
        """Test navigation on mobile (iPhone)"""
        # Menu interactions are different on mobile
        menu_page = DashboardPage(self.page)
        menu_page.goto("/dashboard")

        # Mobile-specific interaction
        menu_page.open_mobile_menu()
        assert menu_page.mobile_menu.is_visible()

        # Verify menu items
        items = menu_page.get_menu_items()
        assert len(items) > 0

    @pytest.mark.mobile
    def test_touch_interactions(self):
        """Test touch-friendly interactions work on mobile"""
        # Ensure buttons are properly sized for touch
        login_page = LoginPage(self.page)
        login_page.goto("/login")

        # Get button size - should be at least 44x44 for touch targets
        button_box = login_page.login_button.bounding_box()
        assert button_box["width"] >= 44, "Button too small for touch"
        assert button_box["height"] >= 44, "Button too small for touch"
```

### Visual Regression Testing with Figma

Page objects can include Figma design frame URLs for automatic visual comparison during test execution. When a test navigates to a page, the actual UI is compared against the Figma design frame to detect visual regressions.

#### Page Object with Figma Frame URL

```python
from playwright.sync_api import Page, Locator

class LoginPage:
    """Login page with Figma design reference"""

    # Figma frame URL - used for visual regression testing
    # Set to None to skip visual comparison for this page
    FIGMA_FRAME_URL = "https://www.figma.com/design/PROJECT_ID/DESIGN_NAME?node-id=login-page"

    def __init__(self, page: Page):
        self.page = page
        self.email_input: Locator = page.locator("[data-testid='email']")
        self.password_input: Locator = page.locator("[data-testid='password']")
        self.login_button: Locator = page.locator("[data-testid='login-btn']")

    def login(self, email: str, password: str):
        """Perform login"""
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.login_button.click()

class DashboardPage:
    """Dashboard page without Figma comparison (set to None)"""

    # No visual comparison for this page
    FIGMA_FRAME_URL = None

    def __init__(self, page: Page):
        self.page = page
        self.user_menu: Locator = page.locator("[data-testid='user-menu']")
```

#### Visual Regression Testing in Tests

```python
import pytest
from refua_core.core.base_test import BaseTest
from refua_core.core.visual_regression import VisualRegressionManager
from tests.pages.login_page import LoginPage

class TestVisualRegression(BaseTest):
    """Test page visual appearance against Figma designs"""

    def test_login_page_visual_regression(self, visual_regression: VisualRegressionManager):
        """Test login page matches Figma design"""
        login_page = LoginPage(self.page)
        login_page.goto("/login")

        # Visual regression check - automatically compares page to Figma frame
        # Only runs if FIGMA_FRAME_URL is set
        visual_regression.compare_page(
            page=self.page,
            page_object=login_page,
            name="login_page"
        )
        # If comparison fails, test fails with detailed diff report

    def test_dashboard_visual_regression(self, visual_regression: VisualRegressionManager):
        """Test dashboard page - skips visual check (FIGMA_FRAME_URL is None)"""
        from tests.pages.dashboard_page import DashboardPage
        dashboard_page = DashboardPage(self.page)
        dashboard_page.goto("/dashboard")

        # This comparison is skipped because FIGMA_FRAME_URL is None
        visual_regression.compare_page(
            page=self.page,
            page_object=dashboard_page,
            name="dashboard_page"
        )
```

#### Auto-Comparison on Page Navigation

Tests can automatically compare pages when navigating using a fixture:

```python
import pytest
from refua_core.core.visual_regression import VisualRegressionManager

@pytest.fixture
def auto_visual_check(page, visual_regression: VisualRegressionManager):
    """Fixture that automatically checks visual regression on page navigation"""
    original_goto = page.goto

    def goto_with_check(url, **kwargs):
        result = original_goto(url, **kwargs)
        # Auto-compare page to Figma if available
        visual_regression.compare_current_page(page)
        return result

    page.goto = goto_with_check
    return visual_regression

class TestAutoVisualRegression(BaseTest):
    """Tests with automatic visual regression checking"""

    def test_login_flow_with_auto_check(self, auto_visual_check):
        """All page navigations automatically checked against Figma"""
        self.page.goto("/login")  # Automatically compared to Figma frame if URL set
        # ... fill form ...
        self.page.goto("/dashboard")  # Also automatically compared
```

#### Figma Configuration

Store Figma API credentials in environment files:

```bash
# .env.test
FIGMA_API_TOKEN=figd_xxxxxxxxxxxxxxxxxxxxx
FIGMA_PROJECT_ID=project_design_id
FIGMA_API_ENABLED=true

# .env.preprod
FIGMA_API_TOKEN=figd_xxxxxxxxxxxxxxxxxxxxx
FIGMA_PROJECT_ID=project_design_id
FIGMA_API_ENABLED=true

# .env.prod (optional - may disable for production)
FIGMA_API_ENABLED=false
```

#### VisualRegressionManager Implementation

```python
# refua_core/core/visual_regression.py
import os
import json
from pathlib import Path
from playwright.sync_api import Page
import requests

class VisualRegressionManager:
    """Manages visual regression testing with Figma integration"""

    def __init__(self):
        self.api_token = os.getenv("FIGMA_API_TOKEN")
        self.project_id = os.getenv("FIGMA_PROJECT_ID")
        self.enabled = os.getenv("FIGMA_API_ENABLED", "true").lower() == "true"
        self.results_dir = Path("./visual-regression-results")
        self.results_dir.mkdir(exist_ok=True)

    def compare_page(self, page: Page, page_object, name: str):
        """
        Compare actual page to Figma design frame

        Args:
            page: Playwright page object
            page_object: Page object with FIGMA_FRAME_URL attribute
            name: Test name for report

        Returns:
            bool: True if comparison passes, False if visual regression detected
        """
        # Skip if Figma URL not set or disabled
        if not hasattr(page_object, 'FIGMA_FRAME_URL'):
            return True

        figma_url = page_object.FIGMA_FRAME_URL
        if not figma_url or not self.enabled:
            return True

        # Capture actual page screenshot
        actual_screenshot = page.screenshot()

        # Get Figma design screenshot
        figma_screenshot = self._fetch_figma_screenshot(figma_url)

        # Compare screenshots
        diff_result = self._compare_screenshots(actual_screenshot, figma_screenshot, name)

        if not diff_result['match']:
            # Save detailed comparison report
            self._save_comparison_report(diff_result, name)
            raise AssertionError(
                f"Visual regression detected on '{name}'. "
                f"Difference: {diff_result['difference']}%. "
                f"Report: {diff_result['report_path']}"
            )

        return True

    def compare_current_page(self, page: Page):
        """Compare current page against Figma (requires FIGMA_FRAME_URL in context)"""
        # Get page object from test context if available
        pass

    def _fetch_figma_screenshot(self, figma_url: str):
        """Fetch screenshot from Figma design frame"""
        # Implementation to extract node-id from URL and fetch from Figma API
        # Returns screenshot as bytes
        pass

    def _compare_screenshots(self, actual: bytes, expected: bytes, name: str):
        """Compare actual vs expected screenshots"""
        # Use image comparison library (e.g., pixelmatch, opencv)
        # Returns dict with: match (bool), difference (%), report_path
        pass

    def _save_comparison_report(self, diff_result: dict, name: str):
        """Save visual comparison report with diffs"""
        report_file = self.results_dir / f"{name}_comparison.json"
        with open(report_file, 'w') as f:
            json.dump(diff_result, f, indent=2)
```

### Artifact Management (Videos & Screenshots)

Tests automatically capture videos and screenshots during execution. Failed test artifacts are retained for debugging, while passing test artifacts are deleted to save storage.

#### ArtifactManager Implementation

```python
# refua_core/core/artifact_manager.py
import os
import shutil
from pathlib import Path
from datetime import datetime

class ArtifactManager:
    """Manages test artifacts (videos, screenshots) with conditional retention"""

    def __init__(self):
        self.artifacts_dir = Path(os.getenv("ARTIFACTS_DIR", "./test-artifacts"))
        self.keep_on_pass = os.getenv("KEEP_ARTIFACTS_ON_PASS", "false").lower() == "true"
        self.video_enabled = os.getenv("RECORD_VIDEO", "true").lower() == "true"
        self.screenshot_enabled = os.getenv("CAPTURE_SCREENSHOTS", "true").lower() == "true"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def get_test_artifact_dir(self, test_name: str) -> Path:
        """Get artifact directory for specific test"""
        test_dir = self.artifacts_dir / test_name
        test_dir.mkdir(parents=True, exist_ok=True)
        return test_dir

    def cleanup_on_pass(self, test_name: str):
        """Delete artifacts if test passed (unless keep_on_pass enabled)"""
        if self.keep_on_pass:
            return

        test_dir = self.artifacts_dir / test_name
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"Deleted artifacts for passing test: {test_name}")

    def keep_on_fail(self, test_name: str):
        """Retain artifacts if test failed"""
        test_dir = self.artifacts_dir / test_name
        if test_dir.exists():
            # Rename with timestamp for easier identification
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            failed_dir = test_dir.parent / f"{test_dir.name}_FAILED_{timestamp}"
            test_dir.rename(failed_dir)
            print(f"Retained artifacts for failing test: {failed_dir}")

    def get_artifacts_info(self, test_name: str) -> dict:
        """Get info about test artifacts"""
        test_dir = self.artifacts_dir / test_name
        if not test_dir.exists():
            return {}

        videos = list(test_dir.glob("*.webm")) + list(test_dir.glob("*.mp4"))
        screenshots = list(test_dir.glob("*.png"))

        return {
            "test_name": test_name,
            "directory": str(test_dir),
            "video_count": len(videos),
            "screenshot_count": len(screenshots),
            "videos": [str(v) for v in videos],
            "screenshots": [str(s) for s in screenshots]
        }
```

#### Pytest Configuration for Artifacts

```ini
# pytest.ini
[pytest]
# Video recording settings
video = on_failure  # on, off, on_failure, retain-on-failure

# Screenshot capture
screenshots = only-on-failure  # none, only-on-failure, all

# Artifact directory
artifacts_dir = ./test-artifacts
```

#### Playwright Configuration with Artifact Capture

```python
# tests/conftest.py
import pytest
import os
from pathlib import Path
from refua_core.core.artifact_manager import ArtifactManager
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="function")
def browser_context(request):
    """Create browser context with video/screenshot recording"""
    artifact_mgr = ArtifactManager()
    test_name = request.node.name
    artifact_dir = artifact_mgr.get_test_artifact_dir(test_name)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Configure video recording
        context_kwargs = {}
        if artifact_mgr.video_enabled:
            context_kwargs["record_video_dir"] = str(artifact_dir)

        context = browser.new_context(**context_kwargs)

        # Add screenshot capability to page
        def take_screenshot(name: str):
            if artifact_mgr.screenshot_enabled:
                screenshot_path = artifact_dir / f"{name}.png"
                context.pages[0].screenshot(path=screenshot_path)

        yield context, artifact_mgr, test_name, take_screenshot

        # Cleanup based on test result
        if request.node.rep_call.failed:
            artifact_mgr.keep_on_fail(test_name)
        else:
            artifact_mgr.cleanup_on_pass(test_name)

        context.close()
        browser.close()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result for artifact management"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
```

#### Using Artifacts in Tests

```python
import pytest
from refua_core.core.base_test import BaseTest

class TestWithArtifacts(BaseTest):
    """Tests with automatic video/screenshot capture"""

    def test_login_flow_with_artifacts(self, browser_context):
        """Test with video and screenshot capture"""
        context, artifact_mgr, test_name, take_screenshot = browser_context

        page = context.new_page()
        page.goto("https://app.example.com/login")

        # Capture screenshot at key points
        take_screenshot("login_page_loaded")

        page.locator("[data-testid='email']").fill("user@test.com")
        page.locator("[data-testid='password']").fill("password")

        take_screenshot("login_form_filled")

        page.locator("[data-testid='login-btn']").click()
        page.wait_for_url("**/dashboard", timeout=5000)

        take_screenshot("dashboard_loaded")

        # If test passes: video + screenshots deleted
        # If test fails: video + screenshots retained in ./test-artifacts/

        page.close()
```

#### Environment Variables for Artifact Control

```bash
# .env or set as environment variables

# Enable/disable recording
RECORD_VIDEO=true              # true, false
CAPTURE_SCREENSHOTS=true       # true, false

# Artifact storage
ARTIFACTS_DIR=./test-artifacts # local path
# In Docker:
# ARTIFACTS_DIR=/artifacts   # mounted volume

# Retention policy
KEEP_ARTIFACTS_ON_PASS=false   # true to keep all, false to delete passing

# Video format and quality
VIDEO_BITRATE=1000k           # Bitrate for video compression
VIDEO_SIZE=1280x720           # Video resolution (matches viewport)
```

### Setup: Initial Session Storage Configuration

Before capturing sessions, configure external session storage:

```bash
# Create sessions directory (Linux/Mac)
mkdir -p ~/.refua_sessions

# Create sessions directory (Windows)
mkdir %USERPROFILE%\.refua_sessions
```

### Setup: Initial Session Capture (Desktop)

1. Run session capture script: `python scripts/capture_session.py --env test --user <username> --device desktop`
2. Browser opens - complete login manually (including 2FA)
3. Script captures session to `~/.refua_sessions/auth_state_test_desktop_2024-12-01_120000.json`
4. Session valid for 3 days - no further manual login required

### Setup: Mobile Session Capture (iPhone & Android)

Capture sessions for mobile devices to test on different viewports:

```bash
# Capture iPhone session
python scripts/capture_session.py --env test --user <username> --device iphone

# Capture Android session
python scripts/capture_session.py --env test --user <username> --device android

# Capture specific device model
python scripts/capture_session.py --env test --user <username> --device iphone_14
```

Sessions are stored by device:

- `~/.refua_sessions/auth_state_test_desktop_2024-12-01_120000.json`
- `~/.refua_sessions/auth_state_test_iphone_2024-12-01_121500.json`
- `~/.refua_sessions/auth_state_test_android_2024-12-01_122000.json`

### Adding a New Test

1. Create test file in `tests/test_*.py` (follows pytest naming)
2. Inherit from `BaseTest` or write as pytest function
3. Use page objects for all UI interactions
4. Mark test with appropriate markers: `@pytest.mark.smoke`, `@pytest.mark.regression`, etc.
5. Session validation happens automatically before test

```python
import pytest
from tests.pages.login_page import LoginPage

@pytest.mark.smoke
def test_user_login(browser_page):
    """Test user login flow"""
    login_page = LoginPage(browser_page)
    login_page.goto("/login")
    # ... test implementation using page objects
```

### Running Test Selections

```bash
# Run smoke tests only (desktop, serial)
TEST_ENV=test pytest -m smoke --alluredir=./allure-results

# Run smoke tests in parallel
TEST_ENV=test pytest -n auto -m smoke --alluredir=./allure-results

# Run all except slow tests
TEST_ENV=test pytest -m "not slow" --alluredir=./allure-results

# Run all except slow tests in parallel
TEST_ENV=test pytest -n auto -m "not slow" --alluredir=./allure-results

# Run tests for a specific feature
TEST_ENV=test pytest tests/features/authentication/ --alluredir=./allure-results

# Run tests for a specific feature in parallel
TEST_ENV=test pytest -n auto tests/features/authentication/ --alluredir=./allure-results
```

### Running Tests with Artifact Capture

Tests automatically capture videos and screenshots during execution:

```bash
# Run tests with automatic artifact capture
# Videos/screenshots captured, deleted on pass, retained on fail
TEST_ENV=test pytest --alluredir=./allure-results

# Run with artifact capture enabled explicitly
RECORD_VIDEO=true CAPTURE_SCREENSHOTS=true TEST_ENV=test pytest

# Run keeping all artifacts (for debugging/analysis)
KEEP_ARTIFACTS_ON_PASS=true TEST_ENV=test pytest

# Run without video recording (faster, less disk space)
RECORD_VIDEO=false TEST_ENV=test pytest

# Run without screenshot capture
CAPTURE_SCREENSHOTS=false TEST_ENV=test pytest

# Run in parallel with artifact capture
TEST_ENV=test pytest -n auto --alluredir=./allure-results

# View failed test artifacts
ls -la ./test-artifacts/
# Artifacts named: test_name_FAILED_20241201_142030/
#   ├── video.webm
#   ├── login_page_loaded.png
#   ├── login_form_filled.png
#   └── dashboard_loaded.png
```

**Artifact Storage Paths:**

Local execution:

```
./test-artifacts/
├── test_login_flow_FAILED_20241201_142030/
│   ├── video.webm                      # Full test video
│   ├── login_page_loaded.png           # Screenshot at point 1
│   ├── login_form_filled.png           # Screenshot at point 2
│   └── dashboard_loaded.png            # Screenshot at point 3
└── test_checkout_FAILED_20241201_150000/
    └── video.webm
```

Docker execution:

```
Inside container: /artifacts/
  ├── test_name_FAILED_*/
  │   ├── video.webm
  │   └── *.png

Host mounted volume: ./docker-artifacts/
  ├── test_name_FAILED_*/
  │   └── (same structure as container)
```

### Running Visual Regression Tests

Visual regression tests compare actual page UI against Figma design frames:

```bash
# Run tests with visual regression checking (requires Figma API token)
TEST_ENV=test pytest tests/test_visual_regression.py --alluredir=./allure-results

# Run visual regression tests only (exclude other tests)
TEST_ENV=test pytest -m visual_regression --alluredir=./allure-results

# Run visual regression tests on mobile device
TEST_ENV=test DEVICE=iphone pytest -m visual_regression --alluredir=./allure-results

# Run visual regression tests in parallel
TEST_ENV=test pytest -n auto -m visual_regression --alluredir=./allure-results

# Skip visual regression checks (even if FIGMA_FRAME_URL is set)
FIGMA_API_ENABLED=false TEST_ENV=test pytest --alluredir=./allure-results

# View visual regression results
open ./visual-regression-results/  # macOS
explorer .\visual-regression-results\  # Windows
```

### Running Tests on Mobile Devices

```bash
# Run all tests on iPhone (serial)
TEST_ENV=test DEVICE=iphone pytest --alluredir=./allure-results

# Run all tests on iPhone in parallel
TEST_ENV=test DEVICE=iphone pytest -n auto --alluredir=./allure-results

# Run all tests on Android (serial)
TEST_ENV=test DEVICE=android pytest --alluredir=./allure-results

# Run all tests on Android in parallel
TEST_ENV=test DEVICE=android pytest -n auto --alluredir=./allure-results

# Run only mobile-specific tests in parallel
TEST_ENV=test DEVICE=iphone pytest -n auto -m mobile --alluredir=./allure-results

# Run tests excluding mobile in parallel
TEST_ENV=test DEVICE=desktop pytest -n auto -m "not mobile" --alluredir=./allure-results

# Run smoke tests on both iPhone and Android (sequential devices, parallel tests)
TEST_ENV=test DEVICE=iphone pytest -n auto -m smoke --alluredir=./allure-results/ios
TEST_ENV=test DEVICE=android pytest -n auto -m smoke --alluredir=./allure-results/android

# Run iOS-only tests in parallel
TEST_ENV=test DEVICE=iphone pytest -n auto -m ios_only --alluredir=./allure-results

# Run Android-only tests in parallel
TEST_ENV=test DEVICE=android pytest -n auto -m android_only --alluredir=./allure-results
```

### Adding Figma Frame URLs to New Pages

When implementing a new page object, add the Figma design frame URL:

```bash
# 1. Create new page object
# tests/pages/new_feature_page.py

# 2. Copy Figma frame URL from design system
# Open Figma design → Select frame → Right-click → Copy link
# Example: https://www.figma.com/design/PROJECT_ID/MEDITEK?node-id=123:456

# 3. Add FIGMA_FRAME_URL to page object
cat > tests/pages/new_feature_page.py << 'EOF'
from playwright.sync_api import Page, Locator

class NewFeaturePage:
    """New feature page with visual regression testing"""

    # Figma design frame URL - set to None to skip visual comparison
    FIGMA_FRAME_URL = "https://www.figma.com/design/PROJECT_ID/MEDITEK?node-id=new-feature-page"

    def __init__(self, page: Page):
        self.page = page
        # ... locators ...

    def navigate(self):
        self.page.goto("/new-feature")
EOF

# 4. Create test with visual regression
cat > tests/test_new_feature_visual.py << 'EOF'
import pytest
from refua_core.core.base_test import BaseTest
from refua_core.core.visual_regression import VisualRegressionManager
from tests.pages.new_feature_page import NewFeaturePage

@pytest.mark.visual_regression
class TestNewFeatureVisual(BaseTest):
    def test_page_matches_figma_design(self, visual_regression: VisualRegressionManager):
        """Test new feature page matches Figma design"""
        page_obj = NewFeaturePage(self.page)
        page_obj.navigate()

        # Automatically skipped if FIGMA_FRAME_URL is None
        visual_regression.compare_page(
            page=self.page,
            page_object=page_obj,
            name="new_feature_page"
        )
EOF

# 5. Run visual regression test
TEST_ENV=test pytest tests/test_new_feature_visual.py -m visual_regression
```

**When to Add Figma URLs:**

- New page implementation (always)
- When page design changes in Figma
- Before merging to main branch

**When to Skip (Set to None):**

- Highly dynamic pages (dashboards with real-time data)
- Pages with user-specific content
- Pages that are tested via functional tests only

### Capturing New Session (Scheduled Refresh)

When session expires or credentials change:

```bash
# Capture new session
python scripts/capture_session.py --env test --user <username>

# Wait for user to complete login and 2FA (browser interactive)
# New session saved automatically
```

### Switching Environments

```bash
# Switch environment - all config changes automatically
TEST_ENV=preprod pytest tests/test_*.py --alluredir=./allure-results

# Session file auto-selected: auth_state_preprod_chromium_latest.json
```

### Running Tests in Parallel

Parallel execution significantly reduces test run time by running multiple tests concurrently:

```bash
# Simple parallel run - auto-detect CPU cores
TEST_ENV=test pytest -n auto --alluredir=./allure-results

# Parallel with specific number of workers (4 workers)
TEST_ENV=test pytest -n 4 --alluredir=./allure-results

# Parallel with load-scoped distribution (recommended for stability)
TEST_ENV=test pytest -n auto --dist=loadscope --alluredir=./allure-results

# Parallel with marker-based grouping (optimal for device testing)
TEST_ENV=test pytest -n auto --dist=loadgroup --alluredir=./allure-results

# Parallel execution excluding slow tests
TEST_ENV=test pytest -n auto -m "not slow" --alluredir=./allure-results

# Parallel execution of feature tests
TEST_ENV=test pytest -n auto tests/features/ --alluredir=./allure-results

# Device-specific parallel testing
TEST_ENV=test DEVICE=iphone pytest -n 4 --alluredir=./allure-results

# Multiple sequential runs with parallel tests per environment
TEST_ENV=test pytest -n auto --alluredir=./allure-results/test && \
TEST_ENV=preprod pytest -n auto --alluredir=./allure-results/preprod

# Full parallel suite: multiple devices, multiple workers
TEST_ENV=test DEVICE=desktop pytest -n auto --alluredir=./allure-results/desktop &
TEST_ENV=test DEVICE=iphone pytest -n auto --alluredir=./allure-results/ios &
TEST_ENV=test DEVICE=android pytest -n auto --alluredir=./allure-results/android &
wait
```

**Parallel Execution Benefits:**

- 4-8x faster test execution on multi-core systems
- Better resource utilization
- Faster feedback on test failures
- Significantly reduced CI/CD pipeline time

**Important Considerations for Parallel Execution:**

- Each worker uses ~100-200MB for browser instance
- Recommended: 1 worker per 1GB available RAM
- Use loadscope distribution for safer parallelization
- Mark tests that must run sequentially with `@pytest.mark.sequential`
- Ensure tests are isolated (no shared state between tests)
- Monitor system memory: `watch -n 1 'free -h'` (Linux/Mac)

### Handling Test Failures

If test fails with auth error:

```
ERROR: Session invalid: Session file expired, run: python scripts/capture_session.py --env test
```

Recovery steps:

1. Check error message for root cause
2. If session expired: Run capture script, re-run tests
3. If credentials invalid: Update .env file, capture new session
4. If environment mismatch: Verify TEST_ENV is correct

### Debugging

```bash
# Enable detailed logging
TEST_ENV=test pytest --log-cli-level=DEBUG --alluredir=./allure-results

# Check specific test with auth logging
DEBUG_AUTH=true TEST_ENV=test pytest tests/test_auth.py::test_login -v

# Run single test without session to verify POM
pytest tests/test_*.py::test_name -v  # Skips session validation
```

### Future: Gherkin BDD Tests

The framework is prepared for future Gherkin-style tests using pytest-bdd:

```gherkin
# features/authentication.feature
Feature: User Authentication
  Scenario: User can login successfully
    Given user navigates to login page
    When user enters valid credentials
    And user completes 2FA
    Then user is redirected to dashboard
```

Test implementation will use same page objects:

```python
from pytest_bdd import given, when, then
from tests.pages.login_page import LoginPage

@given("user navigates to login page")
def login_page_opened(browser_page):
    login = LoginPage(browser_page)
    login.goto("/login")
```

## Common Pitfalls

1. **Forgetting TEST_ENV**: Will raise `EnvironmentNotSetError` - always set before pytest

   ```bash
   # Wrong
   pytest tests/

   # Correct
   TEST_ENV=test pytest tests/
   ```

2. **Expired sessions**: Session expires 3 days after capture - re-run capture script

   ```bash
   # Check session file timestamp
   ls -la auth_states/auth_state_test_chromium_latest.json

   # If expired, capture new session
   python scripts/capture_session.py --env test --user <username>
   ```

3. **Session file not found**: Capture script must run before tests

   ```bash
   # First time setup
   python scripts/capture_session.py --env test --user <username>

   # Then run tests
   TEST_ENV=test pytest tests/
   ```

4. **Missing .env credentials file**: Required for SKIP_2FA=false execution

   ```
   Create: .env.test with TEST_USER_EMAIL, TEST_USER_PASSWORD
   .env files should NEVER be committed to git
   ```

5. **localStorage not applied**: Must call `apply_local_storage()` AFTER `page.goto()` - localStorage is origin-specific

   ```python
   # Wrong order
   session_mgr.apply_local_storage(page)
   page.goto(url)  # localStorage lost!

   # Correct order
   page.goto(url)
   session_mgr.apply_local_storage(page)
   ```

6. **Using wrong environment for session**: Session captured for test env won't work for preprod

   ```bash
   # Session mismatch error
   TEST_ENV=preprod pytest  # But using auth_state_test_chromium_latest.json

   # Solution: Capture session for preprod
   python scripts/capture_session.py --env preprod --user <username>
   ```

7. **Production manual auth not configured**: Prod requires either session file or real credentials

   ```bash
   # Won't work - production requires manual setup
   TEST_ENV=prod pytest tests/

   # Solution: Either
   # 1. Pre-capture session: python scripts/capture_session.py --env prod
   # 2. Or use real credentials: SKIP_2FA=false TEST_ENV=prod pytest (requires .env.prod)
   ```

8. **Test markers not configured**: Tests must have appropriate markers for selective execution

   ```python
   # Missing marker - test won't be selectable
   def test_login():
       pass

   # Better
   @pytest.mark.smoke
   @pytest.mark.authentication
   def test_login():
       pass
   ```

9. **Not using Page Objects**: Direct locator interactions reduce maintainability

   ```python
   # Anti-pattern
   page.locator("[data-testid='email']").fill("user@test.com")

   # Better - use POM
   login_page = LoginPage(page)
   login_page.login("user@test.com", "password")
   ```

10. **Allure report not installed**: Allure functionality requires pytest-allure integration

    ```bash
    pip install allure-pytest

    # Then reports generate automatically
    TEST_ENV=test pytest --alluredir=./allure-results
    allure serve ./allure-results
    ```

11. **Session directory not created**: External session storage must exist before capture

    ```bash
    # Error if directory missing
    ERROR: Session directory not found: ~/.refua_sessions/

    # Solution: Create directory
    mkdir -p ~/.refua_sessions
    python scripts/capture_session.py --env test --user <username>
    ```

12. **Device configuration file missing**: Mobile testing requires device config

    ```bash
    # Error if devices.json not found
    ERROR: Device config not found at refua_core/config/devices.json

    # Solution: Ensure devices.json exists with device profiles
    # Or use SESSION_DIR parameter with pre-configured paths
    ```

13. **Session not found for specific device**: Each device needs its own session

    ```bash
    # Running iPhone tests but no iPhone session captured
    TEST_ENV=test DEVICE=iphone pytest
    ERROR: No session found for iphone in ~/.refua_sessions/

    # Solution: Capture session for that device
    python scripts/capture_session.py --env test --user <username> --device iphone
    ```

14. **Mobile viewport not matching test expectations**: Tests must account for responsive design

    ```python
    # Wrong - assumes desktop width
    button_locator = page.locator("[data-testid='menu']").nth(0)  # Maybe hidden on mobile!

    # Better - check if visible on current viewport
    if page.viewport_size['width'] < 768:
        # Mobile viewport - use different selector
        button_locator = page.locator("[data-testid='mobile-menu']")
    else:
        button_locator = page.locator("[data-testid='menu']")
    ```

15. **Touch interactions not working**: Mobile has different interaction model

    ```python
    # May not work on mobile - uses hover
    element.hover()
    element.click()

    # Better - works on both desktop and mobile
    element.click()  # Works on touch and click
    # Use hover only if not testing on mobile
    if not is_mobile_device:
        element.hover()
    ```

16. **pytest-xdist not installed**: Parallel execution requires pytest-xdist package

    ```bash
    # Error when using -n flag
    ERROR: Unknown option: -n

    # Solution: Install pytest-xdist
    pip install pytest-xdist

    # Verify installation
    pytest --version  # Should show xdist plugin
    ```

17. **Too many parallel workers causing out of memory**: Each worker uses 100-200MB

    ```bash
    # Running on 4GB system with 8 workers = 800MB-1.6GB just for browsers
    TEST_ENV=test pytest -n 8  # May cause system to swap/crash

    # Solution: Calculate safe worker count
    # Formula: (Total RAM - 1GB for OS) / 200MB per worker
    # For 4GB: (4 - 1) / 0.2 = ~15, but be conservative
    TEST_ENV=test pytest -n 2  # Safe for 4GB system
    ```

18. **Test isolation issues in parallel execution**: Tests sharing state fail when parallelized

    ```python
    # Anti-pattern - modifies shared state
    global_state = {}

    def test_login():
        global_state['user'] = 'john'

    def test_dashboard():
        # May fail in parallel - global_state not set by previous test
        assert global_state['user'] == 'john'

    # Better - use fixtures or mark as sequential
    @pytest.mark.sequential
    def test_login():
        # Run in sequence only
        pass
    ```

19. **Parallel tests with conflicting sessions**: Multiple workers loading same session

    ```bash
    # All workers loading same session file = conflicts
    TEST_ENV=test pytest -n auto  # Each worker tries to use same session

    # Solution: Ensure session manager is thread-safe
    # Or use SESSION_DIR with per-worker sessions
    TEST_ENV=test SESSION_DIR=~/.refua_sessions pytest -n auto
    ```

20. **xdist worker reporting confuses Allure results**: Allure report parsing issues

    ```bash
    # Generate reports with proper worker handling
    TEST_ENV=test pytest -n auto --alluredir=./allure-results -v --tb=short

    # View Allure report
    allure serve ./allure-results

    # If reports seem duplicated/confused
    # Clear and regenerate:
    rm -rf ./allure-results
    TEST_ENV=test pytest -n auto --alluredir=./allure-results
    allure generate ./allure-results -o ./allure-html
    ```

21. **Figma API token not set**: Visual regression tests require Figma credentials

    ```bash
    # Error when running visual regression tests
    ERROR: FIGMA_API_TOKEN not found in environment

    # Solution: Add token to .env file
    echo "FIGMA_API_TOKEN=figd_xxxxxxxxxxxx" >> .env.test
    echo "FIGMA_PROJECT_ID=project_id" >> .env.test
    echo "FIGMA_API_ENABLED=true" >> .env.test

    # Get token from: https://www.figma.com/developers
    ```

22. **FIGMA_FRAME_URL missing in page object**: Visual regression silently skipped

    ```python
    # Wrong - no FIGMA_FRAME_URL attribute (test passes but no visual check)
    class LoginPage:
        def __init__(self, page):
            self.page = page

    # Better - explicitly set URL or None
    class LoginPage:
        FIGMA_FRAME_URL = "https://www.figma.com/design/PROJECT/DESIGN?node-id=login"
        # OR for pages without design:
        # FIGMA_FRAME_URL = None

    def __init__(self, page):
        self.page = page
    ```

23. **Visual regression test fails due to dynamic content**: Tests fail on real-time data

    ```python
    # Problem: Page has dynamic content (timestamps, user data)
    class DashboardPage:
        FIGMA_FRAME_URL = "https://figma.com/design/..."  # Has static mock data
        # But real page shows: "Updated 2 minutes ago"

    # Solution 1: Skip visual regression for dynamic pages
    class DashboardPage:
        FIGMA_FRAME_URL = None  # No visual comparison

    # Solution 2: Hide/mask dynamic content before comparison
    def test_dashboard(self, visual_regression):
        dashboard = DashboardPage(page)
        dashboard.goto("/dashboard")

        # Hide timestamps before visual comparison
        page.evaluate("document.querySelector('.timestamp').style.visibility = 'hidden'")

        visual_regression.compare_page(
            page=page,
            page_object=dashboard,
            name="dashboard_masked"
        )
    ```

24. **Visual regression not running - FIGMA_API_ENABLED=false**: Visual checks disabled globally

    ```bash
    # Check if visual regression is enabled
    echo $FIGMA_API_ENABLED  # Should be "true"

    # If disabled, enable it
    FIGMA_API_ENABLED=true TEST_ENV=test pytest -m visual_regression

    # Or set in .env file
    echo "FIGMA_API_ENABLED=true" >> .env.test
    ```

25. **Figma frame URL invalid or expired**: Visual comparison fails with API error

    ```bash
    # Error: "Invalid Figma frame URL"
    # This happens when:
    # - URL points to deleted frame
    # - Frame node-id is incorrect
    # - URL has expired sharing permissions

    # Solution: Verify and update Figma URL
    # 1. Open page in Figma
    # 2. Select correct frame
    # 3. Right-click → Copy link
    # 4. Update FIGMA_FRAME_URL in page object

    # Or temporarily disable for that page
    class ProblematicPage:
        FIGMA_FRAME_URL = None  # Fix later
    ```

26. **ARTIFACTS_DIR not accessible or missing**: Tests fail trying to save artifacts

    ```bash
    # Error: "Permission denied" or "Directory not found"

    # Local solution:
    mkdir -p ./test-artifacts
    chmod 755 ./test-artifacts
    TEST_ENV=test pytest --alluredir=./allure-results

    # Docker solution:
    # Ensure VOLUME ["/artifacts"] is in Dockerfile
    # And volume mounted in docker-compose.yml

    # Custom path solution:
    ARTIFACTS_DIR=/var/artifacts TEST_ENV=test pytest
    ```

27. **Videos consuming excessive disk space**: Recording all tests creates large files

    ```bash
    # Problem: 1 hour of testing = 500MB-1GB of videos

    # Solution 1: Only record failed tests (default)
    # Already configured - videos auto-deleted on pass

    # Solution 2: Reduce video resolution
    VIDEO_SIZE=1024x576 TEST_ENV=test pytest  # Lower res = smaller files

    # Solution 3: Disable video for fast tests
    RECORD_VIDEO=false TEST_ENV=test pytest -m "not slow"

    # Solution 4: Compress videos post-execution
    ffmpeg -i video.webm -c:v libvpx-vp9 -crf 30 video_compressed.webm
    ```

28. **Artifact timestamp format incorrect or unreadable**: Cannot identify when test failed

    ```python
    # Problem: Artifacts named without proper timestamp
    # test_login_FAILED.txt  # When did it fail?

    # Solution: Use ISO format timestamp (already implemented)
    # test_login_FAILED_20241201_142030/  # Clear: Dec 1, 14:20:30

    # If using custom artifact manager:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Good
    # NOT: datetime.now().strftime("%s")  # Unix timestamp
    ```

29. **Artifacts not retained in Docker**: Failed test evidence lost in container

    ```bash
    # Problem: Ran tests in Docker, container deleted, artifacts lost

    # Solution: Mount artifact volume BEFORE running
    docker-compose.yml:
    volumes:
      - ./docker-artifacts:/artifacts  # Must exist

    # Create directory on host first
    mkdir -p ./docker-artifacts
    docker-compose up

    # After run, artifacts available at:
    ls -la ./docker-artifacts/

    # Bad way (will lose artifacts):
    docker run --rm image_name pytest  # --rm deletes container
    # Artifacts inside container deleted!
    ```

30. **Screenshot capture too frequent causing performance issues**: Tests slow due to screenshots

    ```python
    # Problem: Taking screenshot every action = slow tests
    page.screenshot()  # For every click, fill, etc.

    # Solution: Screenshot only at key points
    def test_workflow(self):
        page.goto("/login")
        # Don't screenshot every step

        take_screenshot("page_loaded")  # Key point
        page.locator("[data-testid='email']").fill("user@test.com")
        page.locator("[data-testid='password']").fill("password")
        take_screenshot("form_filled")  # Key point
        page.click("[data-testid='login-btn']")
        # Wait for navigation
        take_screenshot("login_complete")  # Key point

    # Or disable screenshots, keep video
    CAPTURE_SCREENSHOTS=false RECORD_VIDEO=true pytest
    # Video has everything, smaller file than many screenshots
    ```

## Deployment and CI/CD

### Local Development (Current)

Tests run locally with:

- Manual session capture via script (desktop, iOS, Android)
- Local browser automation with device emulation
- Sessions stored externally in `~/.refua_sessions/`
- Allure reports generated locally
- Mobile device testing on same machine
- Automatic video and screenshot capture on test execution
- Failed test artifacts retained for debugging (videos + screenshots)
- Passing test artifacts automatically deleted to save space

**Local Setup Checklist:**

```bash
# 1. Create session directory
mkdir -p ~/.refua_sessions

# 2. Create artifact directory for videos/screenshots
mkdir -p ./test-artifacts

# 3. Capture sessions for each environment/device combo
python scripts/capture_session.py --env test --user <username> --device desktop
python scripts/capture_session.py --env test --user <username> --device iphone
python scripts/capture_session.py --env test --user <username> --device android

# 4. Run tests on all devices (parallel execution with artifact capture)
# Desktop tests in parallel
TEST_ENV=test DEVICE=desktop RECORD_VIDEO=true CAPTURE_SCREENSHOTS=true \
  pytest -n auto --alluredir=./allure-results/desktop &
# iPhone tests in parallel
TEST_ENV=test DEVICE=iphone RECORD_VIDEO=true CAPTURE_SCREENSHOTS=true \
  pytest -n auto --alluredir=./allure-results/ios &
# Android tests in parallel
TEST_ENV=test DEVICE=android RECORD_VIDEO=true CAPTURE_SCREENSHOTS=true \
  pytest -n auto --alluredir=./allure-results/android &
# Wait for all to complete
wait

# 5. View failed test artifacts (if any tests failed)
ls -la ./test-artifacts/
# Artifacts for failed tests will be in test_name_FAILED_timestamp/ directories
# Artifacts for passed tests are automatically deleted

# 6. Combine reports (optional)
# allure-results-merge ./allure-results/desktop ./allure-results/ios ./allure-results/android

# 7. View results
allure serve ./allure-results/desktop
```

**Artifact Handling:**

- Passing tests: Videos + screenshots automatically deleted (saves disk space)
- Failed tests: Artifacts retained in `./test-artifacts/test_name_FAILED_timestamp/` for debugging
- Access artifacts: Open in video player or image viewer
- Keep all artifacts: `KEEP_ARTIFACTS_ON_PASS=true TEST_ENV=test pytest`

**Parallel Execution on Local Machine:**

- Recommend 2-4 workers for desktop systems
- Each worker requires ~100-200MB for browser
- Formula: (Available RAM - 1GB) / 200MB = max workers
- Example: 8GB system = (8-1) / 0.2 = ~35 workers, but use 4-8 for stability

**Local Visual Regression Testing:**

```bash
# 1. Setup Figma credentials
echo "FIGMA_API_TOKEN=figd_xxxxx" >> .env.test
echo "FIGMA_PROJECT_ID=project_id" >> .env.test
echo "FIGMA_API_ENABLED=true" >> .env.test

# 2. Create page objects with Figma URLs (FIGMA_FRAME_URL attribute)

# 3. Create visual regression tests (@pytest.mark.visual_regression)

# 4. Run visual regression tests
TEST_ENV=test pytest -m visual_regression --alluredir=./allure-results

# 5. View results in Allure report or visual-regression-results directory
open ./visual-regression-results/
```

### Future: Docker & CI/CD Pipeline

Planned improvements:

- Tests run in Docker containers (consistent environment)
- Session capture in CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
- Sessions stored in CI/CD artifact storage or shared volume
- Automated multi-device test execution with parallel workers
- Mobile device emulation in Docker containers
- Parallel test execution (4-8 workers per job)
- Automated test scheduling and reporting
- Integration with CI/CD tools (Jenkins, etc.)

**CI/CD Session Management:**

- Sessions captured once per environment/device combination
- Stored in CI/CD artifact storage (not in git)
- Automatically refreshed when expired (3-day TTL)
- Accessible to all test jobs

**CI/CD Parallel Execution Strategy:**

- Run each device in separate CI job for scalability
- Each job uses parallel workers (-n auto or -n 4)
- Jobs run in parallel across CI infrastructure
- Combines benefits of job parallelization + test parallelization
- Final test run time = max job time (not sum of all jobs)

**CI/CD Visual Regression Testing:**

- Visual regression tests run alongside functional tests
- Figma API token stored as CI secret (not in git)
- Visual regression results uploaded as artifacts
- Failed visual comparisons block merge (like failing tests)
- Results accessible in Allure report + detailed diff reports

Docker setup (future):

```dockerfile
FROM python:3.11
RUN apt-get update && apt-get install -y \
    playwright-browser \
    chromium \
    xvfb

RUN pip install -r requirements.txt
RUN python -m playwright install

# Mount external directories
VOLUME ["/sessions"]
VOLUME ["/artifacts"]
VOLUME ["/results"]

# Environment configuration
ENV SESSION_DIR=/sessions
ENV ARTIFACTS_DIR=/artifacts
ENV RECORD_VIDEO=true
ENV CAPTURE_SCREENSHOTS=true
ENV KEEP_ARTIFACTS_ON_PASS=false

# Parallel execution optimized for Docker
CMD ["pytest", "-n", "auto", "--dist=loadscope", "--alluredir=/results"]
```

**Docker Compose for Artifact Management:**

```yaml
version: "3.8"

services:
  test-automation:
    build: .
    volumes:
      - ./sessions:/sessions # Session files
      - ./docker-artifacts:/artifacts # Test artifacts (videos, screenshots)
      - ./allure-results:/results # Test results
    environment:
      - TEST_ENV=test
      - SESSION_DIR=/sessions
      - ARTIFACTS_DIR=/artifacts
      - RECORD_VIDEO=true
      - CAPTURE_SCREENSHOTS=true
      - KEEP_ARTIFACTS_ON_PASS=false
    command: pytest -n 4 --alluredir=/results
```

**Running Tests in Docker with Artifacts:**

```bash
# Build and run tests with artifact capture
docker-compose up

# Run specific tests
docker-compose run test-automation pytest tests/test_auth.py

# View artifacts from host
ls -la ./docker-artifacts/
# Contents: same structure as local ./test-artifacts/

# Copy artifacts to host after run
docker cp container_name:/artifacts ./docker-artifacts
```

CI/CD workflow with parallel execution (future - GitHub Actions example):

```yaml
name: Test Automation

on: [push, pull_request]

jobs:
  capture-sessions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup sessions directory
        run: mkdir -p ./sessions
      - name: Capture desktop session
        run: python scripts/capture_session.py --env test --device desktop --session-dir ./sessions
      - name: Capture iPhone session
        run: python scripts/capture_session.py --env test --device iphone --session-dir ./sessions
      - name: Capture Android session
        run: python scripts/capture_session.py --env test --device android --session-dir ./sessions
      - name: Upload sessions
        uses: actions/upload-artifact@v3
        with:
          name: sessions
          path: ./sessions

  test-desktop:
    needs: capture-sessions
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Download sessions
        uses: actions/download-artifact@v3
        with:
          name: sessions
          path: ./sessions
      - name: Run tests in parallel (4 workers)
        run: |
          TEST_ENV=test DEVICE=desktop pytest -n 4 \
            --dist=loadscope \
            --alluredir=./allure-results/desktop \
            -v
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: results-desktop
          path: ./allure-results/desktop

  test-iphone:
    needs: capture-sessions
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Download sessions
        uses: actions/download-artifact@v3
        with:
          name: sessions
          path: ./sessions
      - name: Run tests in parallel (4 workers)
        run: |
          TEST_ENV=test DEVICE=iphone pytest -n 4 \
            --dist=loadscope \
            --alluredir=./allure-results/ios \
            -v
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: results-ios
          path: ./allure-results/ios

  test-android:
    needs: capture-sessions
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Download sessions
        uses: actions/download-artifact@v3
        with:
          name: sessions
          path: ./sessions
      - name: Run tests in parallel (4 workers)
        run: |
          TEST_ENV=test DEVICE=android pytest -n 4 \
            --dist=loadscope \
            --alluredir=./allure-results/android \
            -v
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: results-android
          path: ./allure-results/android

  test-visual-regression:
    needs: capture-sessions
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Download sessions
        uses: actions/download-artifact@v3
        with:
          name: sessions
          path: ./sessions
      - name: Run visual regression tests (Figma comparison)
        env:
          FIGMA_API_TOKEN: ${{ secrets.FIGMA_API_TOKEN }}
          FIGMA_PROJECT_ID: ${{ secrets.FIGMA_PROJECT_ID }}
          FIGMA_API_ENABLED: true
        run: |
          TEST_ENV=test pytest -n 4 \
            -m visual_regression \
            --dist=loadscope \
            --alluredir=./allure-results/visual \
            -v
      - name: Upload visual regression results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: results-visual
          path: ./allure-results/visual
      - name: Upload visual diff reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: visual-regression-diffs
          path: ./visual-regression-results

  report:
    needs: [test-desktop, test-iphone, test-android, test-visual-regression]
    runs-on: ubuntu-latest
    steps:
      - name: Download all results
        uses: actions/download-artifact@v3
      - name: Generate Allure report
        run: |
          allure generate results-*/ -o ./allure-report
      - name: Generate visual regression diff report (optional)
        if: always()
        run: |
          # Generate HTML report from visual-regression-results
          ls -la visual-regression-diffs/ || echo "No visual regression diffs"
      - name: Publish combined report
        uses: actions/upload-artifact@v3
        with:
          name: allure-report
          path: ./allure-report
      - name: List and upload failed test artifacts
        if: always()
        run: |
          find . -name "*_FAILED_*" -type d
      - name: Upload test artifacts (videos/screenshots from failures)
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-artifacts-failed
          path: |
            ./test-artifacts/*_FAILED_*/
          retention-days: 7
```

**CI/CD Performance:**

- Session capture: ~5 min
- Desktop tests: ~5-10 min (parallel, 4 workers)
- iPhone tests: ~5-10 min (parallel, 4 workers)
- Android tests: ~5-10 min (parallel, 4 workers)
- Visual regression tests: ~3-5 min (parallel, 4 workers)
- Report generation: ~2-3 min
- Artifact upload: ~1-2 min (only failed tests, ~10-50MB per test)
- **Total: ~15-20 min (all test jobs run in parallel)**
- Without parallel: ~90+ minutes
- **Speed improvement: 4-6x faster with parallel execution + visual regression**

**Artifact Storage in CI/CD:**

- Only failed test artifacts uploaded (auto-cleanup on pass)
- 50-100 tests passing = 0MB artifacts stored
- 5 tests failing = ~50-200MB artifacts (videos + screenshots)
- Default retention: 7 days (configurable in upload action)
- Video format: .webm (compressed, efficient)
- Screenshots: .png (lossless, ~50-200KB per screenshot)

**Figma Integration in CI/CD:**

- Figma API token stored as GitHub secret (FIGMA_API_TOKEN)
- Not exposed in logs or version control
- Used only in visual-regression job
- Results available in Allure report + visual-regression-diffs artifact

**Session Storage in CI/CD:**

```
CI/CD Artifacts/
├── sessions/
│   ├── auth_state_test_desktop_*.json
│   ├── auth_state_test_iphone_*.json
│   └── auth_state_test_android_*.json
├── results-desktop/
│   └── allure results (functional tests)
├── results-ios/
│   └── allure results (functional tests)
├── results-android/
│   └── allure results (functional tests)
├── results-visual/
│   └── allure results (visual regression tests)
├── visual-regression-diffs/
│   ├── page_name_comparison.json
│   ├── page_name_actual.png
│   ├── page_name_expected.png
│   └── page_name_diff.png
└── allure-report/
    └── combined report (all results)
```

## Implementation Roadmap

### Priority Levels & Build Order

This section outlines all components and features needed for the refuaAutomationCore framework with prioritized build order. **Build in this order** to ensure dependencies are satisfied and core functionality is available before advanced features.

---

## **PHASE 1: CRITICAL FOUNDATION (Must Build First)**

### P1.1 - EnvironmentManager Configuration

**Priority:** 🔴 CRITICAL (Build First)
**Status:** Planning
**Dependencies:** None
**Description:** Centralized environment configuration singleton

- [ ] `refua_core/config/environment.py`
  - [ ] EnvironmentManager singleton class
  - [ ] Environment variable loading (TEST_ENV)
  - [ ] Base URL management per environment (test, preprod, prod)
  - [ ] API endpoint configuration
  - [ ] Timeout settings per environment
  - [ ] `validate_environment()` function
  - [ ] `get_env_manager()` factory function
- **Estimated Effort:** 3-4 hours
- **Why First:** All other components depend on environment configuration

### P1.2 - BaseTest Class & Pytest Setup

**Priority:** 🔴 CRITICAL (Build Second)
**Status:** Planning
**Dependencies:** P1.1 (EnvironmentManager)
**Description:** Foundation for all test classes

- [ ] `refua_core/core/base_test.py`
  - [ ] BaseTest class extending pytest.TestCase
  - [ ] Browser initialization/teardown
  - [ ] Session setup hooks
  - [ ] Common fixtures and utilities
- [ ] `tests/conftest.py`
  - [ ] Pytest fixtures (page, browser, context)
  - [ ] Test hooks for setup/teardown
  - [ ] Marker registration
- [ ] `pytest.ini`
  - [ ] Pytest configuration
  - [ ] Marker definitions
  - [ ] Plugin configuration
- **Estimated Effort:** 4-5 hours
- **Why Second:** Needed before any tests can run

### P1.3 - SessionStateManager & 2FA Bypass

**Priority:** 🔴 CRITICAL (Build Third)
**Status:** Planning
**Dependencies:** P1.1 (EnvironmentManager)
**Description:** Session management and 2FA authentication bypass

- [ ] `refua_core/config/session_manager.py`
  - [ ] SessionStateManager class
  - [ ] Session file validation (cookies, localStorage)
  - [ ] `validate_session()` method
  - [ ] `apply_to_context()` method
  - [ ] `apply_local_storage()` method
  - [ ] `save_session_state()` method
  - [ ] Expiration checking (3-day TTL)
- [ ] Session capture script: `scripts/capture_session.py`
  - [ ] Manual session capture flow
  - [ ] Browser launch with headless=false
  - [ ] Wait for 2FA completion
  - [ ] Session file generation
- [ ] External session directory setup (`~/.refua_sessions/`)
  - [ ] Directory creation logic
  - [ ] Path resolution (local vs Docker)
- **Estimated Effort:** 5-6 hours
- **Why Third:** Required for all functional tests to authenticate

---

## **PHASE 2: CORE FUNCTIONALITY (Enables Basic Testing)**

### P2.1 - Page Object Model (POM) Base Classes

**Priority:** 🟠 HIGH (Build Fourth)
**Status:** Planning
**Dependencies:** P1.2 (BaseTest)
**Description:** Page object pattern foundation

- [ ] `refua_core/pages/base_page.py`
  - [ ] BasePage class
  - [ ] `goto()` method with environment awareness
  - [ ] `wait_for_url()` method
  - [ ] Common element interaction methods
- [ ] Example page objects
  - [ ] `tests/pages/login_page.py`
  - [ ] `tests/pages/dashboard_page.py`
- [ ] Page object patterns documentation
- **Estimated Effort:** 3-4 hours
- **Why Fourth:** Enables writing first meaningful tests

### P2.2 - Device Configuration & DeviceManager

**Priority:** 🟠 HIGH (Build Fifth)
**Status:** Planning
**Dependencies:** P1.1 (EnvironmentManager)
**Description:** Mobile device emulation support

- [ ] `refua_core/config/devices.json`
  - [ ] Desktop profile
  - [ ] iPhone profiles (iPhone 12-15)
  - [ ] Android profiles (Pixel 5, Galaxy S21)
  - [ ] Device specifications (viewport, UA, touch)
- [ ] `refua_core/core/device_manager.py`
  - [ ] DeviceManager class
  - [ ] `get_device_config()` method
  - [ ] `list_available_devices()` method
  - [ ] Profile inheritance/extension
- [ ] Device-aware context creation in fixtures
- **Estimated Effort:** 3-4 hours
- **Why Fifth:** Enables multi-device testing capability

### P2.3 - Artifact Manager (Videos & Screenshots)

**Priority:** 🟠 HIGH (Build Sixth)
**Status:** Planning
**Dependencies:** P1.2 (BaseTest)
**Description:** Automatic artifact capture and conditional retention

- [ ] `refua_core/core/artifact_manager.py`
  - [ ] ArtifactManager class
  - [ ] `cleanup_on_pass()` method
  - [ ] `keep_on_fail()` method
  - [ ] `get_test_artifact_dir()` method
  - [ ] Timestamp-based naming
- [ ] Browser context configuration
  - [ ] Video recording setup
  - [ ] Screenshot capture integration
  - [ ] Directory creation and management
- [ ] Pytest hooks for artifact cleanup
  - [ ] `pytest_runtest_makereport` hook
  - [ ] Test result detection
- [ ] Environment variable support
  - [ ] ARTIFACTS_DIR, RECORD_VIDEO, CAPTURE_SCREENSHOTS, KEEP_ARTIFACTS_ON_PASS
- **Estimated Effort:** 4-5 hours
- **Why Sixth:** Critical for debugging failed tests

### P2.4 - Initial Test Suite & Examples

**Priority:** 🟠 HIGH (Build Seventh)
**Status:** Planning
**Dependencies:** P2.1 (POM), P1.3 (SessionManager), P2.3 (Artifact Manager)
**Description:** First working tests to validate infrastructure

- [ ] `tests/test_auth.py`
  - [ ] Test login flow with session capture
  - [ ] Test session validation
- [ ] `tests/test_smoke.py`
  - [ ] Basic smoke tests
  - [ ] Multi-device tests
- [ ] `tests/fixtures.py`
  - [ ] Reusable fixtures
  - [ ] Helper functions
- [ ] Markers: smoke, regression, mobile
- **Estimated Effort:** 4-5 hours
- **Why Seventh:** Validates core infrastructure works end-to-end

---

## **PHASE 3: EXECUTION & REPORTING (Scale Testing)**

### P3.1 - Parallel Test Execution (pytest-xdist)

**Priority:** 🟡 MEDIUM-HIGH (Build Eighth)
**Status:** Planning
**Dependencies:** P2.4 (Initial tests)
**Description:** Parallel test execution for faster feedback

- [ ] Install and configure pytest-xdist
- [ ] `pytest.ini` updates
  - [ ] Worker configuration
  - [ ] Distribution strategy (loadscope, loadgroup)
- [ ] Test isolation verification
  - [ ] No shared state between tests
  - [ ] Session manager thread safety
- [ ] Parallel test execution documentation
  - [ ] Examples: `-n auto`, `-n 4`, `--dist=loadscope`
  - [ ] Resource recommendations
- [ ] CI environment optimization
  - [ ] Docker worker configuration
  - [ ] Resource limits
- **Estimated Effort:** 2-3 hours
- **Why Eighth:** Improves test execution speed 3-4x

### P3.2 - Allure Report Integration

**Priority:** 🟡 MEDIUM-HIGH (Build Ninth)
**Status:** Planning
**Dependencies:** P2.4 (Initial tests)
**Description:** Test reporting and result visualization

- [ ] Install pytest-allure plugin
- [ ] `pytest.ini` updates
  - [ ] Allure directory configuration
  - [ ] Report generation settings
- [ ] Test annotations for Allure
  - [ ] `@allure.feature()` decorator
  - [ ] `@allure.story()` decorator
  - [ ] `@allure.step()` for test steps
- [ ] Allure report generation and serving
  - [ ] Local report generation
  - [ ] GitHub Actions integration
- [ ] Report customization
  - [ ] Test categories
  - [ ] Custom attachments
- **Estimated Effort:** 2-3 hours
- **Why Ninth:** Enables test result analysis and trending

### P3.3 - Requirements & Dependencies Documentation

**Priority:** 🟡 MEDIUM-HIGH (Build Tenth)
**Status:** Planning
**Dependencies:** All of Phase 2
**Description:** Complete dependency and installation documentation

- [ ] `requirements.txt`
  - [ ] pytest, pytest-xdist, allure-pytest
  - [ ] playwright, pytest-allure-adaptor
  - [ ] python-dotenv, requests
  - [ ] Version specifications
- [ ] Installation guide
  - [ ] `pip install -r requirements.txt`
  - [ ] `pip install -e .` (editable install)
  - [ ] Playwright browser installation
- [ ] `.gitignore`
  - [ ] Credentials, sessions, artifacts
  - [ ] Python cache, virtualenv
- **Estimated Effort:** 1-2 hours
- **Why Tenth:** Enables reproducible environment setup

---

## **PHASE 4: ADVANCED FEATURES (Quality & Analysis)**

### P4.1 - Visual Regression Testing (Figma Integration)

**Priority:** 🟡 MEDIUM (Build Eleventh)
**Status:** Planning
**Dependencies:** P2.1 (POM), P1.1 (EnvironmentManager)
**Description:** Automatic page UI comparison against Figma designs

- [ ] `refua_core/core/visual_regression.py`
  - [ ] VisualRegressionManager class
  - [ ] `compare_page()` method
  - [ ] `compare_current_page()` method
  - [ ] `_fetch_figma_screenshot()` method
  - [ ] `_compare_screenshots()` method
  - [ ] Diff report generation
- [ ] Page object FIGMA_FRAME_URL attribute
  - [ ] Optional URL parameter per page
  - [ ] None value skips comparison
- [ ] Figma API integration
  - [ ] Token management
  - [ ] Frame extraction
  - [ ] Screenshot fetching
- [ ] Visual regression tests
  - [ ] Test examples with Figma URLs
  - [ ] Dynamic content masking
- [ ] Image comparison library
  - [ ] pixelmatch or similar
  - [ ] Diff generation
  - [ ] Threshold configuration
- [ ] Environment variables
  - [ ] FIGMA_API_TOKEN, FIGMA_PROJECT_ID
  - [ ] FIGMA_API_ENABLED
- **Estimated Effort:** 6-8 hours
- **Why Eleventh:** Nice-to-have for design validation

### P4.2 - CI/CD Pipeline (GitHub Actions)

**Priority:** 🟡 MEDIUM (Build Twelfth)
**Status:** Planning
**Dependencies:** P3.1 (Parallel), P3.2 (Allure), P4.1 (Visual Regression)
**Description:** Automated testing in CI/CD

- [ ] GitHub Actions workflow file (`.github/workflows/test.yml`)
  - [ ] Session capture job
  - [ ] Parallel test jobs (desktop, iOS, Android)
  - [ ] Visual regression job
  - [ ] Report generation job
  - [ ] Artifact upload
- [ ] Job configuration
  - [ ] Ubuntu runner selection
  - [ ] Parallel job execution
  - [ ] Dependency management
- [ ] Secrets management
  - [ ] FIGMA_API_TOKEN, etc.
- [ ] Artifact handling
  - [ ] Session storage
  - [ ] Test result uploads
  - [ ] Failed artifact retention (7 days)
- [ ] Report publishing
  - [ ] Allure report upload
  - [ ] GitHub Pages deployment (optional)
- **Estimated Effort:** 4-5 hours
- **Why Twelfth:** Enables automated test execution on push/PR

### P4.3 - Docker & Container Support

**Priority:** 🟡 MEDIUM (Build Thirteenth)
**Status:** Planning
**Dependencies:** P1.1, P2.3, P4.2
**Description:** Containerized test execution

- [ ] `Dockerfile`
  - [ ] Python 3.11 base image
  - [ ] Playwright browser installation
  - [ ] Dependency installation
  - [ ] Volume mounts (sessions, artifacts, results)
  - [ ] Environment variables
- [ ] `docker-compose.yml`
  - [ ] Service configuration
  - [ ] Volume mappings
  - [ ] Environment variable setup
  - [ ] Parallel execution configuration
- [ ] Docker documentation
  - [ ] Building images
  - [ ] Running containers
  - [ ] Volume management
  - [ ] Artifact retrieval
- [ ] CI/CD Docker integration
  - [ ] Docker build steps
  - [ ] Container execution
  - [ ] Image registry (optional)
- **Estimated Effort:** 3-4 hours
- **Why Thirteenth:** Enables consistent CI/CD environment

---

## **PHASE 5: OPTIMIZATION & FUTURE (Performance & Scalability)**

### P5.1 - Advanced Parallel Optimization

**Priority:** 🔵 LOW-MEDIUM (Build Fourteenth)
**Status:** Planning
**Dependencies:** P3.1 (Parallel)
**Description:** Optimization for large test suites

- [ ] Test distribution strategies
  - [ ] loadscope vs loadgroup analysis
  - [ ] Custom distribution plugins
- [ ] Resource optimization
  - [ ] Worker memory management
  - [ ] Browser instance pooling
  - [ ] Session reuse optimization
- [ ] Performance monitoring
  - [ ] Test execution time tracking
  - [ ] Resource usage metrics
  - [ ] Bottleneck analysis
- [ ] Scaling strategies
  - [ ] Remote worker execution
  - [ ] Cloud CI/CD integration
- **Estimated Effort:** 4-5 hours
- **Why Fourteenth:** Optional for high-volume testing

### P5.2 - Gherkin BDD Support (pytest-bdd)

**Priority:** 🔵 LOW (Build Fifteenth)
**Status:** Planning
**Dependencies:** P2.1 (POM), P2.4 (Tests)
**Description:** Behavior-Driven Development with Gherkin syntax

- [ ] Install pytest-bdd
- [ ] Feature file structure
  - [ ] `features/` directory
  - [ ] `.feature` file templates
- [ ] Step implementations
  - [ ] Given, When, Then decorators
  - [ ] Step file organization
- [ ] Example BDD tests
  - [ ] Authentication feature
  - [ ] User workflow feature
- [ ] Integration with POM
  - [ ] POM usage in step implementations
  - [ ] Shared fixtures
- [ ] Documentation
  - [ ] Gherkin syntax guide
  - [ ] Writing feature files
  - [ ] Mapping to page objects
- **Estimated Effort:** 5-6 hours
- **Why Fifteenth:** Future enhancement for non-technical stakeholders

### P5.3 - Performance & Load Testing

**Priority:** 🔵 LOW (Build Sixteenth)
**Status:** Planning
**Dependencies:** P3.1 (Parallel)
**Description:** Performance testing capabilities

- [ ] Locust or JMeter integration (optional)
- [ ] Performance test markers
- [ ] Load testing scenarios
- [ ] Performance metrics collection
- [ ] Report generation
- **Estimated Effort:** 6-8 hours
- **Why Sixteenth:** Advanced feature for specialized testing

### P5.4 - Documentation & Knowledge Base

**Priority:** 🔵 LOW (Build Seventeenth)
**Status:** Planning
**Dependencies:** All phases
**Description:** Comprehensive documentation

- [ ] API documentation
  - [ ] Class and method docs
  - [ ] Code examples
- [ ] User guides
  - [ ] Getting started
  - [ ] Common workflows
  - [ ] Troubleshooting
- [ ] Architecture documentation
  - [ ] Component diagrams
  - [ ] Data flow
  - [ ] Integration points
- [ ] Video tutorials (optional)
- [ ] FAQ and common issues
- **Estimated Effort:** 8-10 hours
- **Why Seventeenth:** Improves team adoption and knowledge sharing

---

## **Implementation Summary**

| Phase | Component             | Priority    | Effort | Dependencies     |
| ----- | --------------------- | ----------- | ------ | ---------------- |
| **1** | EnvironmentManager    | 🔴 CRITICAL | 3-4h   | None             |
| **1** | BaseTest & Pytest     | 🔴 CRITICAL | 4-5h   | P1.1             |
| **1** | SessionStateManager   | 🔴 CRITICAL | 5-6h   | P1.1             |
| **2** | Page Object Models    | 🟠 HIGH     | 3-4h   | P1.2             |
| **2** | DeviceManager         | 🟠 HIGH     | 3-4h   | P1.1             |
| **2** | Artifact Manager      | 🟠 HIGH     | 4-5h   | P1.2             |
| **2** | Initial Test Suite    | 🟠 HIGH     | 4-5h   | P2.1, P1.3, P2.3 |
| **3** | Parallel Execution    | 🟡 MED-HIGH | 2-3h   | P2.4             |
| **3** | Allure Reports        | 🟡 MED-HIGH | 2-3h   | P2.4             |
| **3** | Requirements & Docs   | 🟡 MED-HIGH | 1-2h   | Phase 2          |
| **4** | Visual Regression     | 🟡 MEDIUM   | 6-8h   | P2.1, P1.1       |
| **4** | CI/CD Pipeline        | 🟡 MEDIUM   | 4-5h   | P3.1, P3.2, P4.1 |
| **4** | Docker Support        | 🟡 MEDIUM   | 3-4h   | P1.1, P2.3, P4.2 |
| **5** | Parallel Optimization | 🔵 LOW-MED  | 4-5h   | P3.1             |
| **5** | BDD/Gherkin           | 🔵 LOW      | 5-6h   | P2.1, P2.4       |
| **5** | Performance Testing   | 🔵 LOW      | 6-8h   | P3.1             |
| **5** | Documentation         | 🔵 LOW      | 8-10h  | All phases       |

**Total Estimated Effort:** 80-110 hours

**Recommended Timeline:**

- **Week 1-2:** Phase 1 (Critical Foundation) - 12-15 hours
- **Week 2-3:** Phase 2 (Core Functionality) - 19-23 hours
- **Week 3-4:** Phase 3 (Execution & Reporting) - 7-8 hours
- **Week 4-5:** Phase 4 (Advanced Features) - 17-22 hours
- **Week 5-6+:** Phase 5 (Optimization & Future) - 25-35 hours

**Quick Start (MVP - Phase 1 + 2):** 31-38 hours (~1-1.5 weeks)
