"""
Creates the run's initial process_run record, SCHEDULED, and returns the run_id
everything downstream is tied to.
"""

import getpass
import socket
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from resources.database import get_session
from resources.models import ORMProcessRun
from resources.Schemas.process_run import ProcessRunStatus
from resources.settings import get_settings

_TZ = ZoneInfo('America/Fortaleza')


class AddProcessRun:
    """
    Instantiated once at the start of a run. The run_id execute() returns has to
    reach every module that later updates the run's status.
    """

    def execute(self) -> int:
        """Creates the record and returns its run_id, status SCHEDULED."""
        return self.__create_process_run()

    @staticmethod
    def __create_process_run() -> int:
        """
        Inserts the record, capturing hostname and OS user automatically so the
        run is traceable with nothing to configure by hand.
        """
        settings = get_settings()

        now = datetime.now(_TZ)

        # Assignment by attribute rather than kwargs: SQLAlchemy generates
        # __init__ at runtime and no type checker sees it, so every field would
        # read as an unexpected keyword. create_items.py hits the same wall.
        process_run: Any = ORMProcessRun()
        process_run.process_name = settings.PROJECT_NAME
        process_run.resource_name = socket.gethostname()
        process_run.scheduled_by = getpass.getuser()
        process_run.area = settings.AREA
        process_run.status = ProcessRunStatus.SCHEDULED.value
        # autoload_with does not pick up PostgreSQL's DEFAULT now() on its own,
        # so the timestamps are supplied explicitly to avoid NotNullViolation
        process_run.created_at = now
        process_run.updated_at = now

        with get_session() as session:
            session.add(process_run)
            # flush sends the INSERT to the database without ending the
            # transaction, allowing the generated run_id to be read before the
            # context manager's implicit commit
            session.flush()
            run_id = process_run.run_id

        return run_id
