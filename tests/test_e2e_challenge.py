"""
End-to-end tests against the live rpachallenge.com.

One suite, two browser backends, the same assertion — literally what
cross-browser testing is.

They stay out of the fast lane through the `e2e` marker, because they depend on
an external system: the site can go down, change its DOM or suffer network
jitter. A failure here does not always mean a defect in the code, and a CI that
goes red for someone else's reason teaches a team to ignore red.

The drivers are built **directly**, not through the factory: the factory would
apply PATH_BROWSER from config.json, and with it filled both drivers would end
up using the same browser — exactly the cross-browser coverage these tests
exist to give (decision 12 in the progress notes). As a useful side effect, the
suite runs with no config.json at all.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from resources.Drivers.playwright_driver import PlaywrightDriver
from resources.Drivers.selenium_driver import SeleniumDriver
from resources.Modules.challenge import FORM_FIELDS, Challenge
from resources.Schemas.item_run import Item
from resources.Utils.read_file import FileReader

URL = 'https://rpachallenge.com/'
INPUT_FOLDER = Path(__file__).resolve().parents[1] / 'Entrada'

CONSTRUCTORS = {
    'playwright': PlaywrightDriver,
    'selenium': SeleniumDriver,
}


@pytest.fixture
def driver(request):
    """
    Instantiates the requested driver headless and guarantees close() on
    teardown.

    What comes after the yield runs even when the test fails, which stops a
    browser being left hanging in memory when the site changes or goes down.
    """
    instance = CONSTRUCTORS[request.param](headless=True)

    yield instance

    instance.close()


@pytest.fixture(scope='module')
def items() -> list[Item]:
    """
    The ten records of Entrada/challenge.xlsx, in the shape the flow consumes.

    It reuses FileReader and clean_dataframe instead of reimplementing the
    reading: it is the same path production walks, so a break there shows up
    here too. Module scope because the file does not change between tests.
    """
    data = FileReader(MagicMock(), path_in=INPUT_FOLDER).read_file()

    return [
        Item(
            id=number,
            item_id=number,
            **{attribute: str(row[label]) for label, attribute in FORM_FIELDS.items()},
        )
        for number, (_, row) in enumerate(data.iterrows(), 1)
    ]


@pytest.mark.e2e
@pytest.mark.parametrize('driver', CONSTRUCTORS, indirect=True)
def test_full_challenge_with_a_perfect_score(driver, items):
    """
    The whole flow, from zero to result, in a real browser.

    `indirect=True` makes the parametrize value reach the `driver` fixture
    rather than the test: each name becomes a different instance, and the body
    of the test does not know which library is on the other side — which is the
    proof that the abstraction works.
    """
    challenge = Challenge(driver, MagicMock())

    challenge.start_challenge(URL)
    for item in items:
        challenge.fill_form(item)

    result = challenge.capture_result()

    assert '100%' in result, f'Driver {driver.name} did not ace the challenge: {result}'
    assert '70 out of 70' in result
