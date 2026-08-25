"""
The two steps of a run: reading the input file, and driving the challenge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from resources.Drivers.base import BrowserDriver
from resources.Modules.challenge import Challenge
from resources.Schemas.item_run import ItemInfo, ItemRunStatus
from resources.Tools.logs import Logs
from resources.Utils.read_file import FileReader

# Types only. Importing OperationDb for real would drag in resources.models,
# which connects while being imported, and this module would then need
# PostgreSQL to be imported at all - including by the tests. The future import
# above is what lets the annotation survive without it.
if TYPE_CHECKING:
    from resources.execute import NoDatabase
    from resources.Utils.operation_db import OperationDb


def read_data(logs: Logs) -> pd.DataFrame:
    """Reads every .xlsx in the input folder into one DataFrame."""
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
    Runs the whole challenge: opens the URL, clicks Start and fills one form
    per item, moving each through QUEUED -> PROCESSING -> COMPLETED or FAILED.

    **One item failing does not interrupt the others.** The error is written to
    that item's row, counted, and the queue moves on - in a load of 5,000
    records, one bad row in the middle must not stop the following ones from
    being attempted. Only failures that make the whole run impossible surface.

    Returns the text the site reports at the end. **Not the counts**: those are
    read back from the item store, which keeps being right when a runtime
    failure interrupts the loop and an in-memory number stops being updated.

    `db` is OperationDb or NoDatabase; this function never asks which.
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
