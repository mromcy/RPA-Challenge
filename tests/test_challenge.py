"""
Tests for the business flow (resources/Modules/challenge.py).

They run with no browser: Challenge talks to a BrowserDriver, and in the tests
that driver is FakeDriver, which only records what it was asked to do. This is
the gain that justifies P2's dependency inversion — before this block,
challenge.py had 0% coverage because there was no way to exercise it without
starting a browser.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from resources.Modules.challenge import FORM_FIELDS, Challenge
from resources.Schemas.item_run import Item
from tests.fake_driver import DEFAULT_RESULT, FakeDriver

URL = 'https://rpachallenge.com/'


def _item(**overrides) -> Item:
    """An Item with all seven fields filled, overridable by name."""
    values = {
        'id': 1,
        'item_id': 1,
        'First_Name': 'Marco',
        'Last_Name': 'Romcy',
        'Company_Name': 'Empresa Ficticia',
        'Role_in_Company': 'RPA Developer',
        'Address': 'Rua de Teste, 123',
        'Email': 'teste@exemplo.invalido',
        'Phone_Number': '5511999999999',
    }
    return Item(**{**values, **overrides})


@pytest.fixture
def driver():
    return FakeDriver()


@pytest.fixture
def challenge(driver):
    return Challenge(driver, MagicMock())


def test_start_challenge_navigates_and_then_clicks_start(challenge, driver):
    challenge.start_challenge(URL)

    assert driver.calls == [('open', URL), ('click_start',)]


def test_fill_form_fills_the_seven_fields(challenge, driver):
    challenge.fill_form(_item())

    assert driver.filled_fields == {
        'First Name': 'Marco',
        'Last Name': 'Romcy',
        'Company Name': 'Empresa Ficticia',
        'Role in Company': 'RPA Developer',
        'Address': 'Rua de Teste, 123',
        'Email': 'teste@exemplo.invalido',
        'Phone Number': '5511999999999',
    }


def test_fill_form_submits_after_filling_everything(challenge, driver):
    """Submitting must be the last operation: submitting mid-way loses fields."""
    challenge.fill_form(_item())

    fills = ['fill_field'] * len(FORM_FIELDS)
    assert driver.operations == [*fills, 'submit']


def test_fill_form_submits_once_per_item(challenge, driver):
    items = [_item(First_Name='Ana'), _item(First_Name='Bruno')]

    for item in items:
        challenge.fill_form(item)

    assert driver.operations.count('submit') == len(items)


def test_fill_form_uses_the_values_of_the_item_it_received(challenge, driver):
    challenge.fill_form(_item(First_Name='Ana', Email='ana@exemplo.invalido'))

    assert driver.filled_fields['First Name'] == 'Ana'
    assert driver.filled_fields['Email'] == 'ana@exemplo.invalido'


def test_capture_result_returns_the_text_read_by_the_driver(challenge):
    assert challenge.capture_result() == DEFAULT_RESULT


def test_capture_result_does_not_return_none():
    """
    The contract promises str. The earlier capture_result returned str | None
    because it read without waiting — this guard stops None from coming back.
    """
    challenge = Challenge(FakeDriver(result=''), MagicMock())

    assert isinstance(challenge.capture_result(), str)


def test_field_map_covers_every_form_field_of_item():
    """
    Synchronisation guard: if somebody adds a form field to Item and forgets
    the map, the bot would start submitting an incomplete form with no error at
    all — the site would simply score lower.
    """
    not_form_fields = {'id', 'item_id', 'result'}
    item_fields = set(Item.model_fields) - not_form_fields

    assert set(FORM_FIELDS.values()) == item_fields


def test_business_flow_does_not_depend_on_a_browser_library():
    """
    P2's architecture guard: importing the flow must load neither Playwright
    nor Selenium. It runs in a subprocess because, inside the pytest process,
    another test may already have imported the library by another route.
    """
    code = (
        'import sys; import resources.Modules.challenge; '
        "print([m for m in sys.modules if 'playwright' in m or 'selenium' in m])"
    )
    result = subprocess.run(
        [sys.executable, '-c', code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == '[]'
