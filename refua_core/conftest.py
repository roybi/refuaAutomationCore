"""
Pytest configuration and fixtures for refuaAutomationCore framework.

Environment Parameters:
- TEST_APP (optional): meditek, cpr-go, or any registered app (default: meditek)
- TEST_ENV (required): test, preprod, or prod
- BROWSER (optional): chromium, firefox, webkit, safari (default: chromium)
- DEVICE (optional): desktop, iphone, android, etc. (default: desktop)
- SKIP_2FA (optional): true or false
- SESSION_DIR (optional): path to session storage (default: ~/.refua_sessions)
- RECORD_VIDEO (optional): true or false (default: true)
- CAPTURE_SCREENSHOTS (optional): true or false (default: true)
"""

import logging
import os

import pytest
from playwright.sync_api import sync_playwright

from refua_core.config.environment import validate_environment, get_env_manager

logger = logging.getLogger(__name__)


def pytest_configure(config):
    """Convert pytest CLI options to env vars, then validate the environment."""
    # Only override when the option was explicitly passed — avoids clobbering
    # values the caller already exported (e.g. TEST_APP=cpr-go pytest).
    test_app = config.getoption("--test-app", default=None)
    if test_app is not None:
        os.environ["TEST_APP"] = test_app

    test_env = config.getoption("--test-env", default=None)
    if test_env is not None:
        os.environ["TEST_ENV"] = test_env

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

    try:
        validate_environment()
        _log_execution_info()
    except Exception as e:
        pytest.exit(f"Environment validation failed: {e}", returncode=1)


def _log_execution_info():
    """Log resolved env vars at session start."""
    params = {
        "TEST_APP": os.getenv("TEST_APP", "meditek"),
        "TEST_ENV": os.getenv("TEST_ENV", "NOT SET"),
        "BROWSER": os.getenv("BROWSER", "chromium"),
        "DEVICE": os.getenv("DEVICE", "desktop"),
        "SKIP_2FA": os.getenv("SKIP_2FA", "true"),
        "SESSION_DIR": os.getenv("SESSION_DIR", "~/.refua_sessions"),
        "RECORD_VIDEO": os.getenv("RECORD_VIDEO", "true"),
        "CAPTURE_SCREENSHOTS": os.getenv("CAPTURE_SCREENSHOTS", "true"),
    }
    logger.info("TEST EXECUTION PARAMETERS: %s", params)


def pytest_addoption(parser):
    """Register framework-specific CLI options."""
    parser.addoption("--test-app", default=None,
                     help="Application to test: meditek, cpr-go, or any registered app (default: meditek)")
    parser.addoption("--test-env", default=None,
                     help="Target environment: test, preprod, or prod")
    parser.addoption("--browser", default="chromium",
                     help="Browser: chromium, firefox, webkit, safari (default: chromium)")
    parser.addoption("--device", default="desktop",
                     help="Device profile: desktop, iphone, android, etc. (default: desktop)")
    parser.addoption("--skip-2fa", default=None,
                     help="Bypass 2FA: true or false")
    parser.addoption("--session-dir", default=None,
                     help="Session storage directory (default: ~/.refua_sessions)")
    parser.addoption("--record-video", default="true",
                     help="Record test videos: true or false (default: true)")
    parser.addoption("--capture-screenshots", default="true",
                     help="Capture screenshots: true or false (default: true)")
    parser.addoption("--headless", action="store_true", default=False,
                     help="Run in headless mode")
    parser.addoption("--slow-motion", default="0",
                     help="Slow down execution by N milliseconds")


@pytest.fixture(scope="session")
def headless(request) -> bool:
    return request.config.getoption("--headless")


@pytest.fixture(scope="session")
def slow_motion(request) -> int:
    return int(request.config.getoption("--slow-motion"))


@pytest.fixture(scope="function")
def env_manager():
    return get_env_manager()


@pytest.fixture(scope="function")
def playwright_instance():
    with sync_playwright() as p:
        yield p


def pytest_collection_modifyitems(config, items):
    test_env = os.getenv("TEST_ENV", "unknown")
    for item in items:
        item.add_marker(pytest.mark.env(test_env))


def pytest_runtest_logreport(report):
    if report.when == "call":
        if report.passed:
            logger.debug("PASSED: %s", report.nodeid)
        elif report.failed:
            logger.error("FAILED: %s", report.nodeid)
