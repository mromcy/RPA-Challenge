"""
Main orchestrator of the RPA Challenge run.

Responsibilities:
- Record the start and the end of the run in the process_run table.
- Load the input data (XLSX).
- Start the browser and run the form filling.
- Make sure the status in the database reflects what actually happened, either
  COMPLETED on success or FAILED with the error details.

**The database is optional**, the same way BotCity Maestro already is. With one
reachable, the run is recorded and every item passes through the queue. Without
one, the items are built straight from the spreadsheet and the challenge is
filled all the same — which is what lets somebody clone the repository and run
it without provisioning PostgreSQL first.
"""

import getpass
import socket
import traceback
from collections import Counter

import pandas as pd
from botcity.maestro import BotMaestroSDK
from sqlalchemy.exc import OperationalError

from resources.Drivers.factory import create_driver, resolve_driver
from resources.Executors.execute_challenge import read_data, run_challenge
from resources.Schemas.item_run import Item, ItemInfo, ItemRun, ItemRunStatus
from resources.Schemas.process_run import ProcessRun, ProcessRunStatus
from resources.settings import get_settings
from resources.Tools.botcity import (
    Counts,
    get_task_parameters,
    report_completion,
    report_failure,
)
from resources.Tools.logs import Logs

# The check has to wrap the *import*, not the calls: resources.models connects
# while it is being imported - it reflects process_manager.process_run with
# autoload_with=engine - so by the time a method could be called, the failure
# has already happened.
#
# The three exceptions are the three ways of not having a database, and naming
# them is the point: a bare `except Exception` would swallow a typo inside
# operation_db and report it as "no database available", sending whoever
# investigates to the wrong place.
try:
    from resources.Tools.add_process_run import AddProcessRun
    from resources.Utils.create_items import create_items
    from resources.Utils.operation_db import OperationDb

    DATABASE = True
except (FileNotFoundError, OperationalError, RuntimeError):
    # FileNotFoundError: the secret/ folder is missing, which is what a fresh
    #   clone looks like - .gitignore keeps the credentials out of the repo.
    # OperationalError: credentials exist, the server does not answer.
    # RuntimeError: the server answers, but process_manager was never
    #   provisioned - raised by models._ensure_process_run_exists.
    DATABASE = False


def items_from_dataframe(data: pd.DataFrame) -> list[ItemInfo]:
    """
    Builds the items straight from the spreadsheet, with no database in between.

    It produces exactly what get_queued_items_by_run returns, so run_challenge
    cannot tell the two apart — that is the whole reason the fallback costs so
    little: the processing loop already took the items as a parameter and was
    already being exercised without a database by the tests.

    run_id and item_id are positional rather than generated. Zero is a truthful
    value here: no database handed out an identifier, and anybody reading a log
    line that says run_id=0 knows immediately which mode produced it.

    Args:
        data: The cleaned DataFrame, exactly as read_data returns it.

    Returns:
        list[ItemInfo]: One item per row, in the spreadsheet's own order.
    """
    settings = get_settings()
    resource_name = socket.gethostname()

    # The run really is happening, on this machine, started by this user. The
    # only invented field is run_id - so the object is built once, outside the
    # loop, and shared by every item.
    process_run = ProcessRun(
        run_id=0,
        process_name=settings.PROJECT_NAME,
        resource_name=resource_name,
        scheduled_by=getpass.getuser(),
        area=settings.AREA,
        status=ProcessRunStatus.RUNNING.value,
    )

    return [
        ItemInfo(
            process_run=process_run,
            item=Item(
                id=position,
                item_id=position,
                First_Name=str(row['First Name']),
                Last_Name=str(row['Last Name']),
                Company_Name=str(row['Company Name']),
                Role_in_Company=str(row['Role in Company']),
                Address=str(row['Address']),
                Email=str(row['Email']),
                Phone_Number=str(row['Phone Number']),
            ),
            item_run=ItemRun(
                item_id=position,
                run_id=0,
                process_name=settings.PROJECT_NAME,
                item_key=f'{row["First Name"]}_{row["Phone Number"]}',
                area=settings.AREA,
                priority=0,
                status=ItemRunStatus.QUEUED.value,
                tags='',
                resource_name=resource_name,
                attempt=0,
            ),
        )
        for position, (_, row) in enumerate(data.iterrows(), 1)
    ]


class NoDatabase:
    """
    Stands in for OperationDb when there is no database to write to.

    It accepts the same calls and drops most of them. The one thing it does
    keep is the tally of item transitions, because count_completed_and_failed
    feeds the numbers the operator reads at the end of the run — losing the
    database should cost the history, not the report.

    Counting here is safe in a way it would not be inside run_challenge: the
    counter is written at the same moment the real one would write to
    item_run, so a failure that interrupts the loop leaves this object holding
    exactly what had happened up to that point.
    """

    def __init__(self):
        self._counts: Counter[str] = Counter()

    def update_process_run_status(
        self,
        run_id: int,
        status: ProcessRunStatus,
        error_message: str | None = None,
        error_stack: str | None = None,
    ) -> None:
        """No run record exists to update; the log already carries the status."""

    def update_item_run_status(
        self,
        item_id: int,
        status: ItemRunStatus,
        exception_reason: str | None = None,
    ) -> None:
        """Records the transition, which is all the final report needs."""
        self._counts[status] += 1

    def update_items_result(self, item_ids: list[int], result: str) -> None:
        """The result reaches the operator through run_challenge's return."""

    def count_completed_and_failed(self, run_id: int) -> tuple[int, int]:
        """Same contract as OperationDb's: (completed, failed)."""
        return (
            self._counts[ItemRunStatus.COMPLETED],
            self._counts[ItemRunStatus.FAILED],
        )


class Execute:
    """
    Class responsible for orchestrating the entire bot run.

    The constructor already creates the run record in the database with status
    SCHEDULED, giving traceability from the instant the process starts.

    Attributes:
        maestro: BotCity SDK for integration with the automation server.
        logs: Combined logger (console, file and database).
        settings: Settings loaded from config.json.
        db: Facade for the database operations on process_run and item_run.
        run_id: Unique identifier of this run, generated by the database at
            startup.
    """

    def __init__(self, maestro: BotMaestroSDK, driver: str | None = None):
        """
        Args:
            maestro: SDK already initialised by the entry point. It arrives
                ready-made rather than being created here, so as not to open a
                second connection to the orchestrator — bot.py needs the SDK
                before this class exists, in order to report startup failures.
            driver: 'playwright' or 'selenium', coming from the command line.
                Omitted, the driver is decided in three layers — see
                Drivers.factory.resolve_driver.
        """
        self.maestro = maestro
        task_parameters = get_task_parameters(maestro)

        self.logs = Logs(self.maestro)
        self.settings = get_settings()
        self.chosen_driver = resolve_driver(driver, task_parameters)

        # With no command-line argument, a chosen driver can only have come
        # from the task parameter - and recording where it came from spares
        # whoever investigates from checking three places to learn why that
        # driver ran.
        if self.chosen_driver and not driver:
            self.logs.info(f'Driver set by the task parameter: {self.chosen_driver}.')

        if DATABASE:
            self.db = OperationDb()

            # Creates the initial record in the database; from here on, run_id
            # identifies this run across every related table
            self.run_id = AddProcessRun().execute()
            self.logs.info(
                f'Run recorded in the database with run_id={self.run_id} (SCHEDULED)'
            )
        else:
            self.db = NoDatabase()
            self.run_id = 0

            # A warning, not an info: the dangerous case is not the reviewer who
            # cloned the repository and knows they have no database - it is the
            # machine that was meant to have one and lost it, whose run would
            # otherwise look perfectly successful while persisting nothing.
            self.logs.warning(
                'No database available: the items will be read straight from '
                'the input file and nothing will be persisted - no run record, '
                'no queue, no item history. If this machine was supposed to '
                'have one, check config.json, the secret/ folder and whether '
                'PostgreSQL is up.'
            )

    def execute(self) -> None:
        """
        Runs the complete RPA Challenge flow.

        Flow:
            1. Update process_run to RUNNING.
            2. Read the data from the input XLSX file.
            3. Persist the data into the item_run and item tables (QUEUED).
            4. Read from the database the items ready for processing.
            5. Open the browser and run the form filling, updating each item's
               status in the database.
            6. Update process_run to COMPLETED on success.
            7. On any exception, update it to FAILED with message and stack
               trace, and re-raise the error.
        """
        self.db.update_process_run_status(self.run_id, ProcessRunStatus.RUNNING)
        self.logs.info(f'run_id={self.run_id} → RUNNING')

        total = 0
        result = ''
        driver_name = self.chosen_driver or self.settings.DRIVER

        try:
            data = read_data(self.logs)

            if DATABASE:
                # The items go through the queue: persisted as QUEUED, then read
                # back. The round trip is not ceremony - it is what makes the
                # state survive a crash, and what a second worker would read
                # from.
                item_ids = create_items(data, self.run_id)
                self.logs.info(
                    f'{len(item_ids)} items persisted to the database (QUEUED).'
                )
                # DATABASE being True is what guarantees self.db is an
                # OperationDb, and a module-level flag is not something the type
                # checker can narrow an attribute from.
                items = self.db.get_queued_items_by_run(  # type: ignore[union-attr]
                    self.run_id
                )
                self.logs.info(
                    f'{len(items)} items loaded from the database for processing.'
                )
            else:
                items = items_from_dataframe(data)
                self.logs.info(
                    f'{len(items)} items built from the input file for processing.'
                )

            total = len(items)

            # Visible window: the operator watches the bot filling the form.
            driver = create_driver(self.chosen_driver, headless=False)
            driver_name = driver.name
            self.logs.info(f'Driver selected: {driver.name}.')
            try:
                result = run_challenge(
                    driver, self.logs, items, self.settings.PATH_URL, self.db
                )
            finally:
                # A failure to close becomes a warning: masking the original
                # error with a cleanup problem would send the diagnosis to the
                # wrong place.
                try:
                    driver.close()
                except Exception as cleanup_error:
                    self.logs.warning(f'Failed to close the browser: {cleanup_error}')

            self.db.update_process_run_status(self.run_id, ProcessRunStatus.COMPLETED)
            self.logs.info(f'run_id={self.run_id} → COMPLETED')

            processed, failed = self.db.count_completed_and_failed(self.run_id)
            report_completion(
                self.maestro,
                Counts(total, processed, failed),
                driver_name,
                result,
            )

        except Exception as e:
            # Captures the full stack trace for diagnosis in the database
            stack = traceback.format_exc()
            self.db.update_process_run_status(
                self.run_id,
                ProcessRunStatus.FAILED,
                error_message=str(e),
                error_stack=stack,
            )
            self.logs.error(e)
            self.logs.info(f'run_id={self.run_id} → FAILED')

            # This query runs while we are already trying to report another
            # exception: letting it surface would mask the original problem,
            # which is the one that matters.
            try:
                processed, failed = self.db.count_completed_and_failed(self.run_id)
            except Exception as query_error:
                self.logs.warning(f'Could not count the items: {query_error}')
                processed = failed = 0

            report_failure(
                self.maestro,
                e,
                Counts(total, processed, failed),
                driver_name,
            )
            raise
