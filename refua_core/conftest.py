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

    # Only override env vars when the option was explicitly supplied by the user.
    # Checking against None (not the option default) avoids clobbering values the
    # caller already exported (e.g. BROWSER=firefox pytest).
    test_env = config.getoption("--test-env", default=None)
    if test_env is not None:
        os.environ["TEST_ENV"] = test_env

    # --browser default is "chromium"; only override when value differs from default,
    # which signals the user explicitly passed it.
    browser = config.getoption("--browser", default=None)
    if browser is not None and browser != "chromium":
        os.environ["BROWSER"] = browser

    device = config.getoption("--device", default=None)
    if device is not None and device != "desktop":
        os.environ["DEVICE"] = device

    skip_2fa = config.getoption("--skip-2fa", default=None)
    if skip_2fa is not None:
        os.environ["SKIP_2FA"] = skip_2fa

    session_dir = config.getoption("--session-dir", default=None)
    if session_dir is not None:
        os.environ["SESSION_DIR"] = session_dir

    record_video = config.getoption("--record-video", default=None)
    if record_video is not None and record_video != "true":
        os.environ["RECORD_VIDEO"] = record_video

    capture_screenshots = config.getoption("--capture-screenshots", default=None)
    if capture_screenshots is not None and capture_screenshots != "true":
        os.environ["CAPTURE_SCREENSHOTS"] = capture_screenshots

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
