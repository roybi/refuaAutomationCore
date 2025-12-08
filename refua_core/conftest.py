"""
Pytest configuration and fixtures for refuaAutomationCore framework.

This file should be imported or extended by test repositories to ensure
proper environment parameter handling and test execution configuration.

Environment Parameters (must be set before running tests):
- TEST_ENV (required): test, preprod, or prod
- BROWSER (optional): chromium, firefox, webkit, or safari (default: chromium)
- DEVICE (optional): desktop, iphone, android, or specific model (default: desktop)
- SKIP_2FA (optional): true or false (default: true for test/preprod)
- SESSION_DIR (optional): External session storage path
- RECORD_VIDEO (optional): true or false (default: true)
- CAPTURE_SCREENSHOTS (optional): true or false (default: true)

Example test execution with all parameters:
    TEST_ENV=test BROWSER=firefox DEVICE=iphone SKIP_2FA=true pytest \\
        --alluredir=./allure-results -v --tb=short

All parameters should be passed BEFORE pytest and its options at the END.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import sync_playwright

from refua_core.config.environment import validate_environment, get_env_manager

logger = logging.getLogger(__name__)


def pytest_configure(config):
    """
    Pytest hook: Configure pytest and validate test environment.

    This hook runs before tests execute. It:
    1. Converts pytest options to environment variables (if provided)
    2. Validates that all required environment parameters are set
    3. Logs the configuration for visibility

    Allows parameters to be passed at END of pytest command:
        pytest tests/ --test-env=test --browser=firefox --device=iphone
    """
    # Convert pytest options to environment variables
    # This allows parameters to be passed at the END of the pytest command

    if config.getoption("--test-env"):
        os.environ["TEST_ENV"] = config.getoption("--test-env")

    if config.getoption("--browser"):
        os.environ["BROWSER"] = config.getoption("--browser")

    if config.getoption("--device"):
        os.environ["DEVICE"] = config.getoption("--device")

    if config.getoption("--skip-2fa"):
        os.environ["SKIP_2FA"] = config.getoption("--skip-2fa")

    if config.getoption("--session-dir"):
        os.environ["SESSION_DIR"] = config.getoption("--session-dir")

    if config.getoption("--record-video"):
        os.environ["RECORD_VIDEO"] = config.getoption("--record-video")

    if config.getoption("--capture-screenshots"):
        os.environ["CAPTURE_SCREENSHOTS"] = config.getoption("--capture-screenshots")

    # Validate environment before tests start
    try:
        validate_environment()
        log_test_execution_info()
    except Exception as e:
        pytest.exit(f"❌ Environment validation failed: {e}", returncode=1)


def log_test_execution_info():
    """Log all test execution parameters for visibility."""
    logger.info("=" * 80)
    logger.info("TEST EXECUTION PARAMETERS")
    logger.info("=" * 80)

    # Environment variables
    env_vars = {
        "TEST_ENV": os.getenv("TEST_ENV", "NOT SET"),
        "BROWSER": os.getenv("BROWSER", "chromium (default)"),
        "DEVICE": os.getenv("DEVICE", "desktop (default)"),
        "SKIP_2FA": os.getenv("SKIP_2FA", "true (default for test/preprod)"),
        "SESSION_DIR": os.getenv("SESSION_DIR", "~/.refua_sessions (default)"),
        "RECORD_VIDEO": os.getenv("RECORD_VIDEO", "true (default)"),
        "CAPTURE_SCREENSHOTS": os.getenv("CAPTURE_SCREENSHOTS", "true (default)"),
    }

    logger.info("Environment Variables:")
    for key, value in env_vars.items():
        logger.info(f"  {key}: {value}")

    logger.info("=" * 80)


def pytest_addoption(parser):
    """
    Add custom pytest command-line options.

    These options can be passed at the END of the pytest command AFTER all test paths:
        pytest tests/ --test-env=test --browser=firefox --device=iphone

    This allows environment variables to be passed as pytest arguments:
        pytest tests/ --test-env=test --browser=firefox --device=iphone \\
                      --skip-2fa=true --session-dir=~/.refua_sessions
    """
    # Environment parameter options
    parser.addoption(
        "--test-env",
        action="store",
        default=None,
        help="Target environment: test, preprod, or prod (REQUIRED)",
    )
    parser.addoption(
        "--browser",
        action="store",
        default="chromium",
        help="Browser engine: chromium, firefox, webkit, or safari (default: chromium)",
    )
    parser.addoption(
        "--device",
        action="store",
        default="desktop",
        help="Device profile: desktop, iphone, android, etc. (default: desktop)",
    )
    parser.addoption(
        "--skip-2fa",
        action="store",
        default=None,
        help="Bypass 2FA: true or false (default: true for test/preprod)",
    )
    parser.addoption(
        "--session-dir",
        action="store",
        default=None,
        help="External session storage directory (default: ~/.refua_sessions)",
    )
    parser.addoption(
        "--record-video",
        action="store",
        default="true",
        help="Record test videos: true or false (default: true)",
    )
    parser.addoption(
        "--capture-screenshots",
        action="store",
        default="true",
        help="Capture screenshots: true or false (default: true)",
    )

    # Additional execution options
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run browsers in headless mode (default: interactive)",
    )
    parser.addoption(
        "--slow-motion",
        action="store",
        default="0",
        help="Slow down test execution by specified milliseconds",
    )
    parser.addoption(
        "--browsers",
        action="store",
        default="chromium",
        help="Comma-separated list of browsers to test with",
    )
    parser.addoption(
        "--devices",
        action="store",
        default="desktop",
        help="Comma-separated list of devices to test on",
    )


@pytest.fixture(scope="session")
def headless(request) -> bool:
    """Get headless mode setting from command line."""
    return request.config.getoption("--headless")


@pytest.fixture(scope="session")
def slow_motion(request) -> int:
    """Get slow motion value from command line."""
    return int(request.config.getoption("--slow-motion"))


@pytest.fixture(scope="session")
def browser_list(request) -> list:
    """Get list of browsers to test from command line."""
    browsers_str = request.config.getoption("--browsers")
    return [b.strip() for b in browsers_str.split(",")]


@pytest.fixture(scope="session")
def device_list(request) -> list:
    """Get list of devices to test from command line."""
    devices_str = request.config.getoption("--devices")
    return [d.strip() for d in devices_str.split(",")]


@pytest.fixture(scope="function")
def env_manager():
    """Provide environment manager instance to tests."""
    return get_env_manager()


@pytest.fixture(scope="function")
def playwright_instance():
    """Provide Playwright sync instance to tests."""
    with sync_playwright() as p:
        yield p


def pytest_collection_modifyitems(config, items):
    """
    Pytest hook: Modify test items after collection.

    Automatically adds markers and parameters based on environment variables.
    Ensures tests are marked appropriately for filtering.
    """
    # Log test collection info
    logger.info(f"Collected {len(items)} tests")

    # Add environment marker to all tests
    test_env = os.getenv("TEST_ENV", "unknown")
    for item in items:
        item.add_marker(pytest.mark.env(test_env))


def pytest_runtest_logreport(report):
    """
    Pytest hook: Log test execution details.

    Provides visibility into each test's execution status and parameters.
    """
    if report.when == "setup":
        logger.debug(f"Setting up: {report.nodeid}")
    elif report.when == "call":
        if report.passed:
            logger.debug(f"✓ PASSED: {report.nodeid}")
        elif report.failed:
            logger.error(f"✗ FAILED: {report.nodeid}")
    elif report.when == "teardown":
        logger.debug(f"Cleaning up: {report.nodeid}")


# ============================================================================
# COMMAND-LINE USAGE EXAMPLES
# ============================================================================
"""
The pytest command must have:
1. Environment variables FIRST
2. pytest and its options LAST

✅ CORRECT USAGE:
    TEST_ENV=test BROWSER=chromium DEVICE=desktop pytest tests/ -v --tb=short

    TEST_ENV=test \\
    BROWSER=firefox \\
    DEVICE=iphone \\
    SKIP_2FA=true \\
    RECORD_VIDEO=true \\
    pytest tests/test_auth.py -v --alluredir=./allure-results

✅ WITH PYTEST OPTIONS AT END:
    TEST_ENV=test pytest tests/ -v -k "login" --tb=short
    TEST_ENV=test pytest -n auto tests/ --dist=loadscope
    TEST_ENV=test pytest tests/ --alluredir=./allure-results

✅ WITH CUSTOM PYTEST OPTIONS:
    TEST_ENV=test pytest tests/ --headless --slow-motion=100
    TEST_ENV=test pytest tests/ --browsers=firefox,webkit --devices=iphone,android

❌ INCORRECT USAGE (environment variables after pytest):
    pytest tests/ TEST_ENV=test BROWSER=chromium  # WRONG!
    pytest TEST_ENV=test tests/  # WRONG!

================================================================
ENVIRONMENT VARIABLE DESCRIPTION
================================================================

TEST_ENV (REQUIRED)
    Purpose: Specify target environment
    Values: test, preprod, prod
    Default: None (must be set)
    Example: TEST_ENV=test

BROWSER (OPTIONAL)
    Purpose: Select browser engine
    Values: chromium, firefox, webkit, safari
    Default: chromium
    Example: BROWSER=firefox TEST_ENV=test pytest

DEVICE (OPTIONAL)
    Purpose: Select device profile for emulation
    Values: desktop, iphone, iphone_14, android, android_pixel, etc.
    Default: desktop
    Example: DEVICE=iphone TEST_ENV=test pytest

SKIP_2FA (OPTIONAL)
    Purpose: Bypass 2FA using saved session
    Values: true, false
    Default: true for test/preprod, false for prod
    Example: SKIP_2FA=true TEST_ENV=test pytest

SESSION_DIR (OPTIONAL)
    Purpose: External session storage directory
    Values: File path (absolute or ~)
    Default: ~/.refua_sessions/
    Example: SESSION_DIR=/sessions TEST_ENV=test pytest

RECORD_VIDEO (OPTIONAL)
    Purpose: Enable/disable test video recording
    Values: true, false
    Default: true
    Example: RECORD_VIDEO=true TEST_ENV=test pytest

CAPTURE_SCREENSHOTS (OPTIONAL)
    Purpose: Enable/disable test screenshot capture
    Values: true, false
    Default: true
    Example: CAPTURE_SCREENSHOTS=true TEST_ENV=test pytest

================================================================
PYTEST OPTIONS (AT END OF COMMAND)
================================================================

-v, --verbose
    Verbose output
    Example: TEST_ENV=test pytest -v

-q, --quiet
    Quiet output
    Example: TEST_ENV=test pytest -q

-s
    Don't capture output (show print statements)
    Example: TEST_ENV=test pytest -s

-k EXPRESSION
    Run tests matching expression
    Example: TEST_ENV=test pytest -k "login"

-m MARKER
    Run tests with specific marker
    Example: TEST_ENV=test pytest -m smoke

--tb=short
    Short traceback format
    Example: TEST_ENV=test pytest --tb=short

-x
    Stop on first failure
    Example: TEST_ENV=test pytest -x

-n auto
    Run tests in parallel (requires pytest-xdist)
    Example: TEST_ENV=test pytest -n auto

--dist=loadscope
    Parallel distribution strategy
    Example: TEST_ENV=test pytest -n auto --dist=loadscope

--alluredir=PATH
    Generate Allure results directory
    Example: TEST_ENV=test pytest --alluredir=./allure-results

--headless
    Run in headless mode (custom option)
    Example: TEST_ENV=test pytest --headless

================================================================
COMMON TEST EXECUTION PATTERNS
================================================================

1. BASIC TEST RUN (Single environment, single browser):
    TEST_ENV=test pytest tests/

2. WITH VERBOSE OUTPUT:
    TEST_ENV=test pytest -v tests/

3. WITH SPECIFIC TEST FILE:
    TEST_ENV=test pytest tests/test_auth.py

4. WITH SPECIFIC TEST FUNCTION:
    TEST_ENV=test pytest tests/test_auth.py::test_login_success

5. WITH TEST MARKERS:
    TEST_ENV=test pytest -m smoke tests/

6. WITH TEST NAME FILTER:
    TEST_ENV=test pytest -k "login" tests/

7. MOBILE DEVICE TESTING:
    TEST_ENV=test DEVICE=iphone pytest tests/
    TEST_ENV=test DEVICE=android pytest tests/

8. BROWSER-SPECIFIC TESTING:
    BROWSER=firefox TEST_ENV=test pytest tests/
    BROWSER=webkit TEST_ENV=test pytest tests/

9. PARALLEL EXECUTION:
    TEST_ENV=test pytest -n auto tests/
    TEST_ENV=test pytest -n 4 --dist=loadscope tests/

10. WITH ALLURE REPORTING:
    TEST_ENV=test pytest --alluredir=./allure-results tests/
    allure serve ./allure-results

11. FULL MULTI-ENVIRONMENT EXECUTION:
    TEST_ENV=test BROWSER=chromium DEVICE=desktop \\
        RECORD_VIDEO=true CAPTURE_SCREENSHOTS=true \\
        pytest -n auto --alluredir=./allure-results -v

12. PRODUCTION ENVIRONMENT (No 2FA bypass):
    TEST_ENV=prod SKIP_2FA=false pytest tests/

13. PREPROD ENVIRONMENT (2FA bypass enabled):
    TEST_ENV=preprod SKIP_2FA=true pytest tests/

14. CUSTOM SESSION DIRECTORY (Docker):
    TEST_ENV=test SESSION_DIR=/sessions pytest tests/

15. HEADLESS MODE (Custom option):
    TEST_ENV=test pytest --headless tests/

================================================================
DEBUGGING TEST EXECUTION
================================================================

Enable debug logging to see all parameter handling:
    TEST_ENV=test pytest tests/ -v -s --log-cli-level=DEBUG

Check session file validation:
    TEST_ENV=test pytest tests/test_auth.py -v -s --tb=short

View all executed commands:
    TEST_ENV=test pytest tests/ -v --capture=no

================================================================
"""
