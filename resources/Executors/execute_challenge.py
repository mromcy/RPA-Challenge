"""
1 - Step functions for running the RPA Challenge.
2 - Responsible for reading the data and automating the form.
3 - Takes (driver, logs) as parameters, following the project's pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from resources.Drivers.base import BrowserDriver
from resources.Modules.challenge import Challenge
from resources.Schemas.item_run import ItemInfo, ItemRunStatus
from resources.Tools.logs import Logs
from resources.Utils.read_file import FileReader

# OperationDb appears only in the signature of run_challenge; at runtime what
# arrives here is the finished object, coming from execute.py. Importing it for
# real would drag in resources.models, which connects to the database during the
# import - and this module would then require PostgreSQL to be imported at all,
# including by the tests, which pass a stand-in instead. The
# from __future__ import annotations above is what lets the annotation survive
# without the import: it is not evaluated at runtime.
#
# NoDatabase is the stand-in used when there is no database to talk to. It
# appears here only so the annotation states the truth - both are accepted, and
# this module never asks which one it got.
if TYPE_CHECKING:
    from resources.execute import NoDatabase
    from resources.Utils.operation_db import OperationDb


def read_data(logs: Logs) -> pd.DataFrame:
    """
    Reads the .xlsx files from the input folder and returns one merged
    DataFrame.

    Args:
        logs: Logs instance used to record the operations.

    Returns:
        DataFrame with the cleaned data, ready to use.
    """
    logs.info('Reading input file.')
    data = FileReader(logs).read_file()
    logs.info(f'{len(data)} records loaded successfully.')
    return data


def run_challenge(
    driver: BrowserDriver,
    logs: Logs,
    items: list[ItemInfo],
    url: str,
    db: OperationDb | NoDatabase,
) -> str:
    """
    Runs the complete RPA Challenge flow: navigates to the URL, starts the
    challenge and fills the form for every item read from the database.

    For each item, it updates the status in the database:
    QUEUED → PROCESSING → COMPLETED (or FAILED on error).

    **One item failing does not interrupt the others.** The error is written to
    that item's `item_run`, counted, and the queue moves on. This is the
    behaviour that justifies keeping per-item state: in a load of 5,000
    records, one bad row in the middle must not stop the following ones from
    being attempted. Only failures that make the whole run impossible — a
    browser that will not start, a site that is down — surface and stop
    everything.

    Args:
        driver: A BrowserDriver implementation (Playwright, Selenium, ...).
        logs: Logs instance used to record the operations.
        items: List of ItemInfo read from the database with status QUEUED.
        url: The RPA Challenge URL.
        db: Used to update the status of each item. OperationDb writes them to
            PostgreSQL; NoDatabase only tallies them. This function does not
            care which one it received.

    Returns:
        str: The text the site itself reports at the end. It travels up to the
            orchestrator so the operator can see the outcome without opening
            the log.

            **How many items succeeded is deliberately not returned here.**
            Every transition is written to `item_run` the moment it happens,
            and that is where the count is read from — a number held in memory
            stops being updated if a runtime failure interrupts the loop, and
            the panel would then show zeros with dozens of items already
            completed in the database.
    """
    total = len(items)
    logs.info('Starting challenge.')
    challenge = Challenge(driver, logs)
    challenge.start_challenge(url)

    item_ids: list[int] = []

    for i, item_info in enumerate(items, 1):
        item_id = item_info.item_run.item_id  # type: ignore[union-attr]
        logs.info(f'Filling form {i}/{total}.')

        db.update_item_run_status(item_id, ItemRunStatus.PROCESSING)
        try:
            challenge.fill_form(item_info.item)  # type: ignore[arg-type]
            db.update_item_run_status(item_id, ItemRunStatus.COMPLETED)
            item_ids.append(item_id)

        except Exception as e:
            # The queue carries on: one bad record does not take the others
            # down. This is the reason per-item state exists - without it, item
            # 3,200 of 5,000 would stop the following 1,800 from even being
            # attempted.
            db.update_item_run_status(
                item_id,
                ItemRunStatus.FAILED,
                exception_reason=str(e),
            )
            logs.error(e)

    logs.info('Waiting for the final result.')
    result = challenge.capture_result()
    if result:
        db.update_items_result(item_ids, result)
    logs.info('Run completed successfully.')

    return result
