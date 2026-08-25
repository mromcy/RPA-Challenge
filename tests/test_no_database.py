"""
Tests for the run that has no database (resources/execute.py).

The point of these tests is not that the two new pieces work in isolation — it
is that they **feed the real loop**. So they build the items with
items_from_dataframe, hand them to the same run_challenge the production path
uses, and read the numbers back out of NoDatabase. If the shape ever stops
matching what get_queued_items_by_run returns, the loop breaks here.

Importing resources.execute on a machine with no configuration and no
PostgreSQL is itself part of what is under test: the try/except around the
database imports is the whole mechanism, and CI is a machine with neither.
"""

import json
from unittest.mock import MagicMock

import pandas as pd
import pytest

from resources import settings as settings_module
from resources.execute import NoDatabase, items_from_dataframe
from resources.Executors.execute_challenge import run_challenge
from resources.Schemas.item_run import ItemRunStatus
from resources.settings import CONFIG_ENV_VAR
from tests.fake_driver import FakeDriver

URL = 'https://exemplo.invalido/'

MINIMAL_CONFIG = {
    'PROJECT_NAME': 'projeto_de_teste',
    'AREA': 'area_de_teste',
    'PATH_URL': URL,
    'HOST_DB_POSTGRES': 'localhost',
    'PORT_DB_POSTGRES': 5432,
    'DB_NAME_POSTGRES': 'banco_de_teste',
    'DB_SCHEMA': 'schema_de_teste',
}

ROWS = [
    {
        'First Name': 'Ana',
        'Last Name': 'Sobrenome',
        'Company Name': 'Empresa',
        'Role in Company': 'Cargo',
        'Address': 'Endereço',
        'Email': 'ana@exemplo.invalido',
        'Phone Number': '111',
    },
    {
        'First Name': 'Bruno',
        'Last Name': 'Sobrenome',
        'Company Name': 'Empresa',
        'Role in Company': 'Cargo',
        'Address': 'Endereço',
        'Email': 'bruno@exemplo.invalido',
        'Phone Number': '222',
    },
    {
        'First Name': 'Carla',
        'Last Name': 'Sobrenome',
        'Company Name': 'Empresa',
        'Role in Company': 'Cargo',
        'Address': 'Endereço',
        'Email': 'carla@exemplo.invalido',
        'Phone Number': '333',
    },
]


class DriverThatFailsOn(FakeDriver):
    """A FakeDriver that blows up when filling the given name."""

    def __init__(self, problem_name: str):
        super().__init__()
        self._problem_name = problem_name

    def fill_field(self, label: str, value: str) -> None:
        if value == self._problem_name:
            raise RuntimeError(f'field refused: {value}')
        super().fill_field(label, value)


@pytest.fixture(autouse=True)
def config(tmp_path, monkeypatch):
    """
    Gives items_from_dataframe a configuration to read PROJECT_NAME and AREA
    from, without touching the machine's own.

    Deleting the environment variable is the other half of the job: config_path
    consults RPA_CHALLENGE_CONFIG **before** falling back to _REPO_ROOT, so
    swapping only the root would leave the winning half alive on Marco's
    machine, where the BotCity runner sets it.
    """
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    monkeypatch.setattr(settings_module, '_REPO_ROOT', tmp_path)
    (tmp_path / 'config.json').write_text(json.dumps(MINIMAL_CONFIG), encoding='utf-8')
    return tmp_path


def test_the_items_built_from_the_spreadsheet_run_the_whole_challenge():
    """
    The end the fallback exists for: a spreadsheet in, every form filled, with
    no database anywhere in the path.
    """
    driver = FakeDriver()
    db = NoDatabase()

    items = items_from_dataframe(pd.DataFrame(ROWS))
    result = run_challenge(driver, MagicMock(), items, URL, db)

    assert driver.operations.count('submit') == len(ROWS)
    assert driver.filled_fields['First Name'] == 'Carla'
    assert '100%' in result
    assert db.count_completed_and_failed(0) == (3, 0)


def test_the_items_carry_the_positions_the_loop_needs():
    """
    run_challenge reads item_run.item_id to say which item it is working on.
    Without an identifier per item the loop cannot report anything, and the
    numbering has to start where a database's would.
    """
    items = items_from_dataframe(pd.DataFrame(ROWS))

    assert [item.item_run.item_id for item in items] == [1, 2, 3]
    assert [item.item.First_Name for item in items] == ['Ana', 'Bruno', 'Carla']
    assert all(item.item_run.status == ItemRunStatus.QUEUED.value for item in items)


def test_a_failing_item_is_counted_without_stopping_the_others():
    """
    The same guarantee the database path gives, which is what makes the counts
    reported at the end of the run mean the same thing in both modes.
    """
    db = NoDatabase()

    items = items_from_dataframe(pd.DataFrame(ROWS))
    run_challenge(DriverThatFailsOn('Bruno'), MagicMock(), items, URL, db)

    assert db.count_completed_and_failed(0) == (2, 1)
