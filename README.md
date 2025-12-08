# refuaAutomationCore

**Reusable Test Automation Framework for MEDITEK**

## Overview

`refuaAutomationCore` is a production-ready, open-source test automation framework built with Python and Playwright. It provides a complete foundation for building robust, scalable browser automation tests with support for:

-  Multi-environment configuration (test, preprod, production)
-  2FA authentication bypass with secure session management
-  Mobile device emulation (iOS, Android)
-  Parallel test execution with pytest-xdist
-  Allure reporting integration
-  Visual regression testing (Figma integration)
-  Automatic video and screenshot capture
-  Page Object Model (POM) pattern support

## What is This Repository?

This repository contains **only the core framework** - reusable infrastructure, configuration management, and base classes.

**Test implementation** (test cases, page objects, fixtures) is in a **separate repository**: [`refuaAutomationTests`](https://github.com/org/refuaAutomationTests)

### Key Principle

**Framework (this repo) ’ ’ ’ Test Implementation (separate repo)**

The test repository depends on this framework, not the other way around.

## Installation

### For Framework Development

Clone and install the framework for development:

```bash
git clone https://github.com/org/refuaAutomationCore.git
cd refuaAutomationCore

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -c "from refua_core.config.environment import EnvironmentManager; print(' Framework installed')"
```

### For Test Implementation

In the test repository (`refuaAutomationTests`), add to `requirements.txt`:

```
# Option 1: From PyPI (when released)
refua-automation-core>=1.0.0

# Option 2: From Git (development)
refua-automation-core @ git+https://github.com/org/refuaAutomationCore.git@main

# Option 3: Local editable install
refua-automation-core @ file://../refuaAutomationCore
```

Then install:

```bash
pip install -r requirements.txt
```

## Framework Components

### Configuration Management (`refua_core/config/`)

- **`environment.py`**: Centralized environment configuration singleton
  - Manages base URLs, API endpoints
  - Loads credentials from `.env` files
  - Environment variable: `TEST_ENV` (test, preprod, prod)

- **`session_manager.py`**: 2FA session bypass and authentication
  - Session validation and state management
  - Automatic session loading from external storage
  - Session TTL enforcement (3-day expiration)

- **`devices.json`**: Mobile device profiles
  - Pre-configured iOS and Android device emulation
  - Desktop configuration

### Core Infrastructure (`refua_core/core/`)

- **`base_test.py`**: Foundation for all test classes
  - Browser initialization and lifecycle management
  - Session validation hooks
  - Common test utilities

- **`device_manager.py`**: Mobile device emulation
  - Device profile loading and application
  - Multi-device support

- **`artifact_manager.py`**: Test artifact management
  - Video recording configuration
  - Screenshot capture
  - Conditional retention (delete on pass, keep on fail)

- **`visual_regression.py`**: Visual regression with Figma
  - Page UI comparison against design frames
  - Screenshot diff reporting

### Page Objects (`refua_core/pages/`)

- **`base_page.py`**: Base class for all page objects
  - Common navigation methods with environment awareness
  - Element interaction patterns
  - Template for inheritance

### Utilities (`scripts/`)

- **`capture_session.py`**: Manual 2FA session capture
  - Interactive browser login
  - Multi-browser support (chromium, firefox, webkit, safari)
  - Session file generation and storage

## Usage in Test Repository

See [refuaAutomationTests](https://github.com/org/refuaAutomationTests) for complete examples.

### Basic Test Example

```python
from playwright.sync_api import Page
from refua_core.pages.base_page import BasePage
from refua_core.core.base_test import BaseTest

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

class TestAuth(BaseTest):
    def test_login_success(self):
        login_page = LoginPage(self.page)
        login_page.goto("/login")
        login_page.login("user@test.com", "password")
        login_page.wait_for_url("/dashboard")
```

### Running Tests

From the test repository:

```bash
# Set environment and run tests
TEST_ENV=test pytest --alluredir=./allure-results

# Run tests on mobile device
TEST_ENV=test DEVICE=iphone pytest --alluredir=./allure-results

# Run tests in parallel
TEST_ENV=test pytest -n auto --alluredir=./allure-results

# View Allure report
allure serve ./allure-results
```

## Key Features

### Multi-Environment Support

| Environment | 2FA Bypass | Session Timeout | Use Case             |
| ----------- | ---------- | --------------- | -------------------- |
| test        | Yes        | 3 days          | Local development    |
| preprod     | Yes        | 3 days          | Integration testing  |
| prod        | Optional   | 30 minutes      | Production validation |

### 2FA Authentication Bypass

Sessions are captured once with manual 2FA completion, then reused for all tests:

```bash
# Capture session for test environment
python scripts/capture_session.py --env test --user john.doe

# Sessions stored externally in ~/.refua_sessions/
# Tests run without manual 2FA interaction
TEST_ENV=test pytest
```

### Mobile Device Testing

Built-in profiles for iOS and Android:

```bash
# Run on iPhone
TEST_ENV=test DEVICE=iphone pytest

# Run on Android
TEST_ENV=test DEVICE=android pytest

# Run on specific model
TEST_ENV=test DEVICE=iphone_14 pytest
```

### Parallel Execution

Execute tests on multiple workers simultaneously:

```bash
# Auto-detect CPU cores
TEST_ENV=test pytest -n auto

# Specific number of workers
TEST_ENV=test pytest -n 4

# With load-based distribution
TEST_ENV=test pytest -n auto --dist=loadscope
```

### Automatic Artifact Capture

Videos and screenshots captured during test execution:

```bash
# Automatic behavior:
# - Passing tests: artifacts deleted (saves storage)
# - Failed tests: artifacts retained in ./test-artifacts/
#
# Videos: test.webm
# Screenshots: captured at key test points
```

## Development

### Adding Framework Features

1. Create feature branch: `git checkout -b feature/description`
2. Implement changes in `refua_core/`
3. Update `CLAUDE.md` with documentation
4. Test changes with test repository integration
5. Submit pull request with semantic versioning comment

### Version Management

Update version in `setup.py`:

```python
setup(
    name="refua-automation-core",
    version="1.0.0",  # Update version here
    # ...
)
```

Then tag release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Publishing to PyPI

```bash
# Build distribution
python -m build

# Publish to PyPI (requires credentials)
python -m twine upload dist/*

# Or publish to internal registry
python -m twine upload -r internal dist/*
```

## Configuration

### Environment Variables

- **`TEST_ENV`** (required): Target environment - `test`, `preprod`, or `prod`
- **`SKIP_2FA`** (optional): Bypass 2FA using saved sessions - `true` or `false` (default: `true`)
- **`SESSION_DIR`** (optional): External session storage path (default: `~/.refua_sessions/`)
- **`DEVICE`** (optional): Device profile - `desktop`, `iphone`, `android`, etc. (default: `desktop`)
- **`BROWSER`** (optional): Browser engine - `chromium`, `firefox`, `webkit`, `safari` (default: `chromium`)
- **`RECORD_VIDEO`** (optional): Capture test videos - `true` or `false` (default: `true`)
- **`CAPTURE_SCREENSHOTS`** (optional): Capture test screenshots - `true` or `false` (default: `true`)

### Environment Files (Test Repository)

Create in test repository:

```bash
# .env.test
TEST_USER_EMAIL=user@test.local
TEST_USER_PASSWORD=secure_password
TEST_USER_PHONE=+1234567890

# .env.preprod
PREPROD_USER_EMAIL=user@preprod.local
PREPROD_USER_PASSWORD=secure_password

# .env.prod
PROD_USER_EMAIL=user@production.com
PROD_USER_PASSWORD=secure_password
```

**Important:** Never commit `.env` files to version control.

## Documentation

- **Framework Guide**: See `CLAUDE.md` for complete framework documentation
- **Repository Architecture**: See `REPOSITORY_SEPARATION_PLAN.md` for separation details
- **Test Implementation**: See [`refuaAutomationTests`](https://github.com/org/refuaAutomationTests) for test examples

## Project Structure

```
refuaAutomationCore/              (This repo - Framework only)
   refua_core/                   # Core framework package
      config/                   # Configuration management
         environment.py       # Environment configuration
         session_manager.py   # 2FA session management
         devices.json         # Device profiles
      core/                     # Core infrastructure
         base_test.py         # Base test class
         device_manager.py    # Device emulation
         artifact_manager.py  # Artifact management
         visual_regression.py # Visual regression testing
      pages/
          base_page.py         # Base page object class
   scripts/
      capture_session.py       # Session capture utility
   setup.py                      # Package configuration
   requirements.txt              # Framework dependencies
   CLAUDE.md                     # Framework documentation
   README.md                     # This file
   .gitignore                    # Git ignore rules
```

## Requirements

- **Python**: 3.9+
- **Playwright**: 1.40+
- **Python-dotenv**: 1.0+
- **Requests**: 2.31+
- **pytest**: 7.0+

Optional:
- **pillow**: For visual regression (Figma integration)
- **pytest-xdist**: For parallel execution
- **allure-pytest**: For test reporting

## Support

For questions about:

- **Framework development**: See `CLAUDE.md` and `REPOSITORY_SEPARATION_PLAN.md`
- **Test implementation**: See [`refuaAutomationTests`](https://github.com/org/refuaAutomationTests) repository
- **Issue reporting**: Create GitHub issue with detailed reproduction steps

## License

[Specify your license here]

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/description`)
3. Commit changes (`git commit -m "refactor: description"`)
4. Push to branch (`git push origin feature/description`)
5. Create Pull Request

Ensure all changes:

- Maintain backward compatibility (no breaking API changes without major version bump)
- Include documentation updates
- Follow existing code patterns
- Pass all framework checks

## See Also

- [`refuaAutomationTests`](https://github.com/org/refuaAutomationTests) - Test implementation repository
- `CLAUDE.md` - Complete framework documentation
- `REPOSITORY_SEPARATION_PLAN.md` - Architecture and separation strategy
