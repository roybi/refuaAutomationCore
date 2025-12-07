"""
Pytest Configuration and Fixtures
Provides fixtures for browser, page, and session management
Supports multiple browser engines: chromium, firefox, webkit, safari
"""

import logging
import os
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright
from refua_core.config.environment import get_env_manager, validate_environment

logger = logging.getLogger(__name__)

# Supported browser types
SUPPORTED_BROWSERS = ["chromium", "firefox", "webkit", "safari"]


def get_browser_type() -> str:
    """
    Get browser type from environment or use default.

    Priority:
    1. BROWSER environment variable
    2. Default: chromium

    Returns:
        Browser type: chromium, firefox, webkit, or safari
    """
    browser = os.getenv("BROWSER", "chromium").lower().strip()

    if browser not in SUPPORTED_BROWSERS:
        logger.warning(
            f"Unsupported browser: {browser}. "
            f"Supported: {SUPPORTED_BROWSERS}. Using chromium."
        )
        return "chromium"

    return browser


@pytest.fixture(scope="session", autouse=True)
def validate_env_session():
    """
    Validate environment setup once per test session.
    Fails fast if environment is misconfigured.
    """
    try:
        validate_environment()
        logger.info("Environment validation passed")
        logger.info(f"Browser type: {get_browser_type()}")
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        raise


@pytest.fixture(scope="function")
def env_manager():
    """
    Provide environment manager to tests.
    
    Usage:
        def test_something(env_manager):
            base_url = env_manager.get_base_url()
    """
    return get_env_manager()


@pytest.fixture(scope="function")
def browser():
    """
    Provide Playwright browser instance to tests.
    Supports multiple browsers via BROWSER environment variable.
    
    Usage:
        def test_something(browser):
            context = browser.new_context()
            page = context.new_page()
    
    Browser Selection:
        BROWSER=chromium pytest  (default)
        BROWSER=firefox pytest
        BROWSER=webkit pytest
        BROWSER=safari pytest
    """
    browser_type = get_browser_type()
    logger.info(f"Launching {browser_type} browser")
    
    with sync_playwright() as p:
        # Get the appropriate browser launcher
        browser_launcher = getattr(p, browser_type)
        browser_instance = browser_launcher.launch(headless=False)
        
        yield browser_instance
        browser_instance.close()
        logger.debug(f"{browser_type} browser closed")


@pytest.fixture(scope="function")
def context(browser, env_manager):
    """
    Provide Playwright browser context with session loading.
    
    Usage:
        def test_something(context):
            page = context.new_page()
    """
    context_kwargs = {}
    
    # Load session if available and 2FA bypass enabled
    session_file = env_manager.get_session_file_path()
    if session_file.exists() and env_manager.should_bypass_2fa():
        context_kwargs["storage_state"] = str(session_file)
        logger.debug(f"Loading session from: {session_file}")
    
    browser_context = browser.new_context(**context_kwargs)
    
    logger.debug(f"Browser context created for {env_manager.current_env.value} environment")
    
    yield browser_context
    
    browser_context.close()
    logger.debug("Browser context closed")


@pytest.fixture(scope="function")
def page(context):
    """
    Provide Playwright page instance to tests.
    
    Usage:
        def test_something(page):
            page.goto("https://example.com")
            assert page.title()
    """
    page_instance = context.new_page()
    yield page_instance
    page_instance.close()


@pytest.fixture(scope="function")
def artifacts_dir(request):
    """
    Provide artifacts directory for test.
    
    Usage:
        def test_something(artifacts_dir):
            screenshot_path = artifacts_dir / "screenshot.png"
    """
    test_name = request.node.name
    test_class = request.cls.__name__ if request.cls else "test"
    artifacts_base = Path("test-artifacts")
    artifacts_base.mkdir(parents=True, exist_ok=True)
    
    test_artifacts = artifacts_base / test_class / test_name
    test_artifacts.mkdir(parents=True, exist_ok=True)
    
    return test_artifacts


def pytest_configure(config):
    """
    Configure pytest with custom markers.
    Called at the beginning of test run.
    """
    config.addinivalue_line(
        "markers", "smoke: smoke tests - critical path tests"
    )
    config.addinivalue_line(
        "markers", "regression: regression tests - broader test coverage"
    )
    config.addinivalue_line(
        "markers", "mobile: mobile-specific tests"
    )
    config.addinivalue_line(
        "markers", "ios_only: iOS-only tests"
    )
    config.addinivalue_line(
        "markers", "android_only: Android-only tests"
    )
    config.addinivalue_line(
        "markers", "slow: slow running tests"
    )
    config.addinivalue_line(
        "markers", "2fa_required: requires 2FA authentication"
    )
    config.addinivalue_line(
        "markers", "sequential: must run sequentially (cannot parallelize)"
    )
    config.addinivalue_line(
        "markers", "visual_regression: visual regression tests"
    )
    config.addinivalue_line(
        "markers", "browser_specific: browser-specific tests"
    )
    
    logger.info("Pytest markers configured")


def pytest_collection_modifyitems(config, items):
    """
    Modify test items during collection.
    Can add markers or skip tests based on conditions.
    """
    env_mgr = get_env_manager()
    browser_type = get_browser_type()
    
    for item in items:
        # Add environment marker to all tests
        item.add_marker(pytest.mark.env(env_mgr.current_env.value))
        # Add browser marker to all tests
        item.add_marker(pytest.mark.browser(browser_type))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Capture test result for report generation.
    Allows tests to check if they passed/failed after execution.
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
