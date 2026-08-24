"""
Tests for the queue processing loop (Executors/execute_challenge.py).

They run with no browser and no database: the driver is FakeDriver and the
database is a MagicMock, of which only **which calls** were made matters — that
is how the per-item state machine is verified with no PostgreSQL at all.
"""

from unittest.mock import MagicMock

from resources.Executors.execute_challenge import run_challenge
from resources.Schemas.item_run import Item, ItemInfo, ItemRun, ItemRunStatus
from resources.Schemas.process_run import ProcessRun
from tests.fake_driver import FakeDriver

URL = 'https://exemplo.invalido/'

PROCESS_RUN = ProcessRun(
    run_id=1,
    process_name='teste',
    resource_name='maquina',
    scheduled_by='marco',
    area='teste',
    status='RUNNING',
)


def _item_info(item_id: int, first_name: str) -> ItemInfo:
    return ItemInfo(
        process_run=PROCESS_RUN,
        item=Item(
            id=item_id,
            item_id=item_id,
            First_Name=first_name,
            Last_Name='Sobrenome',
            Company_Name='Empresa',
            Role_in_Company='Cargo',
            Address='Endereço',
            Email='email@exemplo.invalido',
            Phone_Number='999',
        ),
        item_run=ItemRun(
            item_id=item_id,
            run_id=1,
            process_name='teste',
            item_key=f'chave_{item_id}',
            area='teste',
            priority=0,
            status=ItemRunStatus.QUEUED.value,
            tags='',
            resource_name='maquina',
            attempt=0,
        ),
    )


class DriverThatFailsOn(FakeDriver):
    """A FakeDriver that blows up when filling the given name."""

    def __init__(self, problem_name: str):
        super().__init__()
        self._problem_name = problem_name

    def fill_field(self, label: str, value: str) -> None:
        if value == self._problem_name:
            raise RuntimeError(f'field refused: {value}')
        super().fill_field(label, value)


def _recorded_statuses(db: MagicMock, status: ItemRunStatus) -> list[int]:
    """The item_ids given that status, in the order they were written."""
    return [
        call.args[0]
        for call in db.update_item_run_status.call_args_list
        if call.args[1] == status
    ]


def test_every_item_marked_completed_when_nothing_fails():
    """
    The assertions look at the **database**, not at a returned number: that is
    where the count is read from when reporting, so that is where the test has
    to look.
    """
    db = MagicMock()
    items = [_item_info(1, 'Ana'), _item_info(2, 'Bruno')]

    result = run_challenge(FakeDriver(), MagicMock(), items, URL, db)

    assert _recorded_statuses(db, ItemRunStatus.COMPLETED) == [1, 2]
    assert _recorded_statuses(db, ItemRunStatus.FAILED) == []
    assert '100%' in result


def test_an_item_that_errors_does_not_interrupt_the_following_ones():
    """
    The behaviour that justifies keeping per-item state: in a load of 5,000
    records, one bad row in the middle must not stop the following ones from
    being attempted. Before this change the loop aborted on the first error.
    """
    db = MagicMock()
    items = [_item_info(1, 'Ana'), _item_info(2, 'Bruno'), _item_info(3, 'Carla')]

    run_challenge(DriverThatFailsOn('Bruno'), MagicMock(), items, URL, db)

    assert _recorded_statuses(db, ItemRunStatus.COMPLETED) == [1, 3]
    assert _recorded_statuses(db, ItemRunStatus.FAILED) == [2]


def test_an_item_that_errors_is_marked_failed_with_the_reason():
    db = MagicMock()
    good_item = _item_info(1, 'Ana')
    bad_item = _item_info(2, 'Bruno')

    run_challenge(DriverThatFailsOn('Bruno'), MagicMock(), [good_item, bad_item], URL, db)

    failures = [
        call
        for call in db.update_item_run_status.call_args_list
        if call.args[1] == ItemRunStatus.FAILED
    ]
    assert len(failures) == 1
    # The next assertion reads item_run.item_id, which the schema declares
    # optional. Writing the assumption down here trades an AttributeError on
    # None for a failure that says which premise of the test stopped holding.
    assert bad_item.item_run is not None
    assert failures[0].args[0] == bad_item.item_run.item_id
    assert 'field refused' in failures[0].kwargs['exception_reason']


def test_the_result_is_only_written_to_the_items_that_succeeded():
    """
    Whoever failed does not get the final success rate: the item's `result`
    field would be claiming it was processed when it was not.
    """
    db = MagicMock()
    items = [_item_info(1, 'Ana'), _item_info(2, 'Bruno'), _item_info(3, 'Carla')]

    run_challenge(DriverThatFailsOn('Bruno'), MagicMock(), items, URL, db)

    written_ids = db.update_items_result.call_args.args[0]
    assert written_ids == [1, 3]


def test_a_failed_item_still_submits_so_the_next_round_is_reached():
    """
    The challenge has ten fixed rounds and only advances on submit, so the
    invariant is one submit per item - including the ones that failed.

    Without it, a failed item leaves the page on its round, the next item fills
    that same form, and the run ends one submit short: the site never shows the
    final result and read_result waits out its timeout before taking the whole
    run down. This test states the invariant in the place where the damage would
    happen, and it fails if the submit ever goes back to being conditional on
    success.
    """
    db = MagicMock()
    items = [_item_info(1, 'Ana'), _item_info(2, 'Bruno'), _item_info(3, 'Carla')]
    driver = DriverThatFailsOn('Bruno')

    run_challenge(driver, MagicMock(), items, URL, db)

    assert driver.operations.count('submit') == len(items)
