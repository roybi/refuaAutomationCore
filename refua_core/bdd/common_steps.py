"""
Generic BDD step definitions — app-agnostic, reusable across any test suite
that depends on refua_core.

These steps cover:
  - Environment / browser setup verification
  - Type and structural assertions on page object attributes
  - String value shape assertions (prefix, suffix)

All steps use @allure.step so they appear in the Allure report trace.
"""

import allure
import pytest
from pytest_bdd import given, parsers, then


@given("the test environment is configured")
@allure.step("Given the test environment is configured")
def test_environment_configured():
    """Verify the test environment is configured (resolved by conftest before session)."""
    pass


@given("the browser is launched")
@allure.step("Given the browser is launched")
def browser_launched(setup_browser):
    """Verify the browser was launched by the session fixture."""
    assert setup_browser is not None, "Browser fixture returned None — check conftest setup"


@then(parsers.parse('the "{attribute}" should be a string'))
def attribute_should_be_string(context, attribute):
    with allure.step(f'Then the "{attribute}" should be a string'):
        value = context.get(attribute)
        assert isinstance(value, str), \
            f"{attribute} should be str, got {type(value).__name__}"


@then(parsers.parse('it should return a string'))
def should_return_string(context):
    with allure.step("Then it should return a string"):
        value = context.get("result")
        assert isinstance(value, str), \
            f"Result should be str, got {type(value).__name__}"


@then(parsers.parse('it should start with "{prefix}"'))
def should_start_with(context, prefix):
    with allure.step(f'Then it should start with "{prefix}"'):
        value = context.get("result")
        assert value.startswith(prefix), \
            f"Expected value to start with '{prefix}', got '{value}'"


@then(parsers.parse('it should end with "{suffix}"'))
def should_end_with(context, suffix):
    with allure.step(f'Then it should end with "{suffix}"'):
        value = context.get("result")
        assert value.endswith(suffix), \
            f"Expected value to end with '{suffix}', got '{value}'"


@then(parsers.parse('the "{property}" property should not be None'))
def property_should_not_be_none(main_page, property):
    with allure.step(f'Then the "{property}" property should not be None'):
        value = getattr(main_page, property, None)
        assert value is not None, f"{property} should not be None"


@then(parsers.parse('the "{method}" method should be callable'))
def method_should_be_callable(main_page, method):
    with allure.step(f'Then the "{method}" method should be callable'):
        method_obj = getattr(main_page, method, None)
        assert callable(method_obj), f"{method} should be callable"


@then(parsers.parse('the "{attribute}" should be initialized'))
def attribute_should_be_initialized(main_page, attribute):
    with allure.step(f'Then the "{attribute}" should be initialized'):
        value = getattr(main_page, attribute, None)
        assert value is not None, f"{attribute} should be initialized"
