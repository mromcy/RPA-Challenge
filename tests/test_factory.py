"""
Tests for resources/Drivers/factory.py.

Reading the task parameter lives in the factory, and not in execute.py, because
that module opens a database connection at import time — the rule would be out
of reach of the unit suite.
"""

import pytest

from resources.Drivers.factory import (
    AVAILABLE_DRIVERS,
    driver_from_parameters,
    resolve_driver,
)


def test_no_parameters_returns_none():
    """Local mode: BotExecution arrives with empty parameters."""
    assert driver_from_parameters({}) is None


def test_missing_parameter_returns_none():
    assert driver_from_parameters({'something_else': 'value'}) is None


def test_empty_parameter_returns_none():
    """A field left blank in the panel must not override the default."""
    assert driver_from_parameters({'driver': ''}) is None


@pytest.mark.parametrize('name', AVAILABLE_DRIVERS)
def test_returns_each_available_driver(name):
    assert driver_from_parameters({'driver': name}) == name


def test_normalises_spaces_and_capitals():
    """A value typed by hand in the Maestro panel usually arrives dirty."""
    assert driver_from_parameters({'driver': '  SELENIUM '}) == 'selenium'


def test_command_line_beats_the_task_parameter():
    """
    The more specific layer wins: whoever typed the flag now wanted that now,
    even if the task was created asking for something else.
    """
    assert resolve_driver('playwright', {'driver': 'selenium'}) == 'playwright'


def test_without_command_line_the_task_parameter_holds():
    assert resolve_driver(None, {'driver': 'selenium'}) == 'selenium'


def test_with_neither_of_them_returns_none():
    """None means "decide from config.json" — the most general layer."""
    assert resolve_driver(None, {}) is None


def test_resolution_rejects_an_invalid_task_parameter():
    with pytest.raises(ValueError, match='playwright, selenium'):
        resolve_driver(None, {'driver': 'cypress'})


def test_unknown_driver_raises_an_error_naming_the_valid_ones():
    """
    It fails at launch, before the migrations run and before the run is
    recorded in the database — a typo in the panel should leave no trace of a
    failed run behind.
    """
    with pytest.raises(ValueError, match='playwright, selenium'):
        driver_from_parameters({'driver': 'cypress'})
