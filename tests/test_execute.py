"""
Tests for the run orchestrator (resources/execute.py).

This file could not exist until the database became optional: importing
`resources.execute` used to open a PostgreSQL connection, so the whole `Execute`
class sat outside the unit suite's reach and its behaviour was described only in
comments.

Four of the behaviours asserted here were exactly that — prose with nothing
holding it in place. That the browser is closed even when the challenge blows
up; that a failure *while closing* must not replace the real error; that a
failure *while counting* during error reporting must not mask the exception
being reported; and that the numbers sent to the orchestrator come from the item
store rather than from a counter kept in memory. A comment claiming a behaviour
with no test behind it is the cheapest kind of future regression: somebody
tidies the `finally` away and nothing objects.

Everything runs with no browser, no database and no network: `create_driver` is
swapped for a FakeDriver and the input spreadsheet is written into a temporary
folder.
"""

import json
import logging
from unittest.mock import MagicMock

import pandas as pd
import pytest
from botcity.maestro import BotMaestroSDK

from resources import execute as execute_module
from resources import settings as settings_module
from resources.execute import Execute, items_from_dataframe
from resources.Schemas.process_run import ProcessRunStatus
from resources.settings import CONFIG_ENV_VAR
from resources.Tools.botcity import Counts
from tests.fake_driver import FakeDriver

NAMES = ('Ana', 'Bruno', 'Carla')
"""The spreadsheet the fixture writes. Assertions count against it, never
against a literal, so changing the fixture cannot leave a stale number behind."""

QUEUE_NAMES = ('Ana', 'Bruno')
"""What the fake database hands back in the queue test."""

RUN_ID = 42
"""The run_id the fake AddProcessRun returns, tracked through the whole run."""

CONFIG = {
    'PROJECT_NAME': 'projeto_de_teste',
    'AREA': 'area_de_teste',
    'PATH_URL': 'https://exemplo.invalido/',
    'DRIVER': 'playwright',
    'HOST_DB_POSTGRES': 'localhost',
    'PORT_DB_POSTGRES': 5432,
    'DB_NAME_POSTGRES': 'banco_de_teste',
    'DB_SCHEMA': 'schema_de_teste',
}


def _rows(*first_names: str) -> list[dict]:
    """One well-formed spreadsheet row per name, with the seven form columns."""
    return [
        {
            'First Name': name,
            'Last Name': 'Sobrenome',
            'Company Name': 'Empresa',
            'Role in Company': 'Cargo',
            'Address': 'Endereço',
            'Email': f'{name.lower()}@exemplo.invalido',
            'Phone Number': '999',
        }
        for name in first_names
    ]


class DriverThatCannotStart(FakeDriver):
    """
    Fails where run_challenge does *not* catch it.

    The per-item loop swallows its own errors on purpose, so a failure inside
    fill_field would never reach execute(). Blowing up on click_start is what
    exercises the orchestrator's error path.
    """

    def click_start(self) -> None:
        # Records the attempt before failing: the operator's log should show
        # that the bot got as far as trying.
        super().click_start()
        raise RuntimeError('the site never loaded')


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
def project(tmp_path, monkeypatch):
    """
    A complete project on disk: configuration, input folder and spreadsheet.

    Pinning DATABASE to False is not decoration. Without it these tests would
    take the real branch on a machine that has PostgreSQL — Marco's — and every
    suite run would leave an orphan SCHEDULED row in his process_run table. With
    it, the test behaves the same here and on CI.
    """
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    monkeypatch.setattr(settings_module, '_REPO_ROOT', tmp_path)
    (tmp_path / 'config.json').write_text(json.dumps(CONFIG), encoding='utf-8')

    entrada = tmp_path / 'Entrada'
    entrada.mkdir()
    pd.DataFrame(_rows(*NAMES)).to_excel(entrada / 'challenge.xlsx', index=False)

    monkeypatch.setattr(execute_module, 'DATABASE', False)
    return tmp_path


@pytest.fixture(autouse=True)
def _clean_handlers():
    """
    Empties the 'RPA' logger around every test.

    Logs() adds a console and a file handler to a logger it fetches **by name**,
    which is process-wide state. Each Execute built here would stack another
    pair onto the same logger, and by the last test one log line would be
    printed seven times.
    """
    logging.getLogger('RPA').handlers.clear()
    yield
    logging.getLogger('RPA').handlers.clear()


@pytest.fixture
def driver(monkeypatch):
    """Hands execute() a FakeDriver instead of opening a browser."""

    def _install(fake: FakeDriver) -> FakeDriver:
        monkeypatch.setattr(execute_module, 'create_driver', lambda *_, **__: fake)
        return fake

    return _install


class Reported:
    """Whatever execute() handed to the orchestrator, captured."""

    def __init__(self):
        self.completion: tuple | None = None
        self.failure: tuple | None = None


@pytest.fixture
def reported(monkeypatch):
    """
    Intercepts the two report functions.

    They are read through the module's own namespace, which is what makes them
    swappable: execute.py imported them by name, so replacing the attribute here
    replaces what execute() calls.
    """
    recorder = Reported()

    monkeypatch.setattr(
        execute_module,
        'report_completion',
        lambda maestro, counts, driver, result: setattr(
            recorder, 'completion', (counts, driver, result)
        ),
    )
    monkeypatch.setattr(
        execute_module,
        'report_failure',
        lambda maestro, error, counts, driver: setattr(
            recorder, 'failure', (error, counts, driver)
        ),
    )
    return recorder


def test_a_run_with_no_database_fills_every_form_and_reports_completion(driver, reported):
    """
    The end the fallback exists for, asserted from the top: a spreadsheet on
    disk, three forms filled in a browser, and a completed run reported — with
    no PostgreSQL anywhere in the path.
    """
    fake = driver(FakeDriver())

    Execute(BotMaestroSDK()).execute()

    assert fake.operations.count('submit') == len(NAMES)
    assert fake.filled_fields['First Name'] == NAMES[-1]

    counts, driver_name, result = reported.completion
    assert counts == Counts(total=len(NAMES), processed=len(NAMES), failed=0)
    assert driver_name == 'fake'
    assert '100%' in result


def test_the_counts_reported_come_from_the_store_not_from_a_memory_counter(
    driver, reported
):
    """
    run_challenge deliberately does not return how many items succeeded, and
    execute() deliberately asks the store instead. This is that contract: one
    item fails, and the panel is told 3 total, 2 processed, 1 failed.
    """
    driver(DriverThatFailsOn(NAMES[1]))

    Execute(BotMaestroSDK()).execute()

    counts, _, _ = reported.completion
    assert counts == Counts(total=len(NAMES), processed=len(NAMES) - 1, failed=1)


def test_the_browser_is_closed_even_when_the_challenge_blows_up(driver, reported):
    """
    The `finally` around run_challenge. Without it a failed run leaks a browser
    process on the machine, and the next run competes with it for the port.
    """
    fake = driver(DriverThatCannotStart())

    with pytest.raises(RuntimeError, match='the site never loaded'):
        Execute(BotMaestroSDK()).execute()

    assert 'close' in fake.operations


def test_a_failure_while_closing_does_not_replace_the_real_error(driver, reported):
    """
    Both things go wrong at once: the site never loaded *and* the browser
    refuses to close. The one that surfaces has to be the first, because it is
    the one that explains the run.
    """

    class DriverThatAlsoFailsToClose(DriverThatCannotStart):
        def close(self) -> None:
            super().close()
            raise RuntimeError('the browser was already gone')

    driver(DriverThatAlsoFailsToClose())

    with pytest.raises(RuntimeError, match='the site never loaded'):
        Execute(BotMaestroSDK()).execute()


def test_the_failure_path_records_the_message_and_the_stack_and_reraises(
    driver, reported
):
    """
    What the run leaves behind when it dies: FAILED, the message, and the full
    traceback — the stack being the half that makes the record worth reading.
    """
    driver(DriverThatCannotStart())

    executor = Execute(BotMaestroSDK())
    executor.db = MagicMock()
    executor.db.count_completed_and_failed.return_value = (0, 0)

    with pytest.raises(RuntimeError, match='the site never loaded'):
        executor.execute()

    last = executor.db.update_process_run_status.call_args_list[-1]
    assert last.args[1] == ProcessRunStatus.FAILED
    assert 'the site never loaded' in last.kwargs['error_message']
    assert 'Traceback' in last.kwargs['error_stack']


def test_a_failure_while_counting_does_not_mask_the_error_being_reported(
    driver, reported
):
    """
    The nested try in the error path. Counting the items runs while an exception
    is already being reported — and a database that has just gone down is
    exactly when that count fails too. Letting it surface would replace the
    diagnosis with a symptom of the same outage.
    """
    driver(DriverThatCannotStart())

    executor = Execute(BotMaestroSDK())
    executor.db = MagicMock()
    executor.db.count_completed_and_failed.side_effect = RuntimeError('connection lost')

    with pytest.raises(RuntimeError, match='the site never loaded'):
        executor.execute()

    _, counts, _ = reported.failure
    assert counts == Counts(total=len(NAMES), processed=0, failed=0)


def test_with_a_database_the_items_go_through_the_queue(monkeypatch, driver, reported):
    """
    The production path, which had no test either. The items are persisted and
    then **read back** before processing, and the run_id used throughout is the
    one the database handed out.

    raising=False on the three replacements is what lets this test run on a
    machine with no database, where those names were never bound: the try around
    the imports failed, so there is no attribute to overwrite.
    """
    db = MagicMock()
    db.get_queued_items_by_run.return_value = items_from_dataframe(
        pd.DataFrame(_rows(*QUEUE_NAMES))
    )
    db.count_completed_and_failed.return_value = (len(QUEUE_NAMES), 0)
    persisted: list[int] = []

    monkeypatch.setattr(execute_module, 'DATABASE', True)
    monkeypatch.setattr(execute_module, 'OperationDb', lambda: db, raising=False)
    monkeypatch.setattr(
        execute_module,
        'AddProcessRun',
        lambda: MagicMock(execute=lambda: RUN_ID),
        raising=False,
    )
    monkeypatch.setattr(
        execute_module,
        'create_items',
        lambda data, run_id: persisted.append(run_id) or [1, 2],
        raising=False,
    )

    fake = driver(FakeDriver())
    executor = Execute(BotMaestroSDK())
    executor.execute()

    assert executor.run_id == RUN_ID
    assert persisted == [RUN_ID]
    db.get_queued_items_by_run.assert_called_once_with(RUN_ID)
    assert fake.operations.count('submit') == len(QUEUE_NAMES)

    counts, _, _ = reported.completion
    assert counts == Counts(total=len(QUEUE_NAMES), processed=len(QUEUE_NAMES), failed=0)
