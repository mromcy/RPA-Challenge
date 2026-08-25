"""
Every database operation on process_run, item_run and item.

Each status change also fills the timestamps that go with it, so a caller never
has to remember that COMPLETED means "set ended_at and compute total_work_time".
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound

from resources.database import get_session
from resources.models import ItemRunStatus, ORMItem, ORMItemRun, ORMProcessRun
from resources.Schemas.item_run import Item, ItemInfo, ItemRun
from resources.Schemas.process_run import ProcessRun, ProcessRunStatus

# Default timezone for every timestamp recorded in the database
_TZ = ZoneInfo('America/Fortaleza')


class OperationDb:
    """
    Facade over the database. Every method is static - the class is a namespace
    with no state, and NoDatabase in execute.py stands in for it unchanged.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # process_run — insertion
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def insert_process_run(process_run: ProcessRun) -> int:
        """
        Inserts a process_run from an already-assembled schema. For the ordinary
        case prefer AddProcessRun, which fills hostname and user by itself.
        """
        orm_run: Any = ORMProcessRun()
        orm_run.process_name = process_run.process_name
        orm_run.resource_name = process_run.resource_name
        orm_run.scheduled_by = process_run.scheduled_by
        orm_run.area = process_run.area
        orm_run.status = process_run.status

        with get_session() as session:
            session.add(orm_run)
            session.flush()
            run_id = orm_run.run_id

        return run_id

    # ─────────────────────────────────────────────────────────────────────────
    # process_run — status update
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def update_process_run_status(
        run_id: int,
        status: ProcessRunStatus,
        error_message: str | None = None,
        error_stack: str | None = None,
    ) -> None:
        """
        Moves a run to a new status and fills the timestamps that go with it.

        FAILED never leaves the error fields empty: with no message or stack it
        writes placeholders, because a FAILED row that says nothing is worse
        than no row. Raises NoResultFound if the run_id does not exist.
        """
        now = datetime.now(_TZ)

        with get_session() as session:
            pr: Any = session.execute(
                select(ORMProcessRun).where(ORMProcessRun.run_id == run_id)  # type: ignore[attr-defined]
            ).scalar_one_or_none()

            if pr is None:
                raise NoResultFound(
                    f'ProcessRun with run_id={run_id} not found in the database.'
                )

            pr.status = status.value

            match status:
                case ProcessRunStatus.RUNNING:
                    # Preserves the original started_at if the process already
                    # started
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.stage_started_at = now
                    # Makes sure errors from previous runs do not linger
                    pr.error_message = None
                    pr.error_stack = None

                case ProcessRunStatus.COMPLETED:
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.ended_at = now
                    pr.total_work_time = pr.ended_at - pr.started_at.astimezone(_TZ)
                    pr.error_message = None
                    pr.error_stack = None

                case ProcessRunStatus.FAILED:
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.ended_at = now
                    pr.total_work_time = pr.ended_at - pr.started_at.astimezone(_TZ)
                    # Never leaves the error field empty, to ease diagnosis
                    pr.error_message = (
                        error_message or 'Process failed with no error message.'
                    )
                    pr.error_stack = error_stack or 'Stack trace unavailable.'

                case ProcessRunStatus.CANCELED:
                    if pr.started_at is None:
                        pr.started_at = now
                    pr.ended_at = now
                    pr.total_work_time = pr.ended_at - pr.started_at.astimezone(_TZ)

                case ProcessRunStatus.SCHEDULED:
                    pass  # Only records the new status; no timestamp changes

            session.flush()

    # ─────────────────────────────────────────────────────────────────────────
    # item_run — querying and status update
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_queued_items_by_run(run_id: int) -> list[ItemInfo]:
        """
        The run's QUEUED items, ordered by item_id, as the three-table join that
        makes a complete ItemInfo.
        """
        with get_session() as session:
            stmt = (
                select(ORMProcessRun, ORMItemRun, ORMItem)
                .join(ORMItemRun, ORMItemRun.run_id == ORMProcessRun.run_id)  # type: ignore[attr-defined]
                .join(ORMItem, ORMItem.item_id == ORMItemRun.item_id)
                .where(
                    ORMProcessRun.run_id == run_id,  # type: ignore[attr-defined]
                    ORMItemRun.status == ItemRunStatus.QUEUED.value,
                )
                .order_by(ORMItemRun.item_id)
            )
            rows = session.execute(stmt).all()
            return [
                ItemInfo(
                    process_run=ProcessRun.model_validate(pr),
                    item_run=ItemRun.model_validate(ir),
                    item=Item.model_validate(it),
                )
                for pr, ir, it in rows
            ]

    @staticmethod
    def count_completed_and_failed(run_id: int) -> tuple[int, int]:
        """
        (completed, failed) for the run, read from the queue.

        The **source of truth** for the panel: an in-memory counter stops being
        updated the moment a runtime failure interrupts the loop, and the panel
        would show zeros with dozens of items already COMPLETED in the database.
        """
        with get_session() as session:
            stmt = (
                select(ORMItemRun.status, func.count())
                .where(ORMItemRun.run_id == run_id)
                .group_by(ORMItemRun.status)
            )
            by_status = {status: amount for status, amount in session.execute(stmt)}

        return (
            by_status.get(ItemRunStatus.COMPLETED.value, 0),
            by_status.get(ItemRunStatus.FAILED.value, 0),
        )

    @staticmethod
    def update_item_run_status(
        item_id: int,
        status: ItemRunStatus,
        exception_reason: str | None = None,
    ) -> None:
        """
        Moves one item to a new status and fills the timestamps that go with it.
        Raises NoResultFound if the item_id does not exist.
        """
        now = datetime.now(_TZ)

        with get_session() as session:
            ir: Any = session.execute(
                select(ORMItemRun).where(ORMItemRun.item_id == item_id)
            ).scalar_one_or_none()

            if ir is None:
                raise NoResultFound(
                    f'ItemRun with item_id={item_id} not found in the database.'
                )

            ir.status = status.value

            match status:
                case ItemRunStatus.PROCESSING:
                    ir.started_at = now
                    ir.last_updated_at = now

                case ItemRunStatus.COMPLETED:
                    ir.completed_at = now
                    ir.last_updated_at = now
                    if ir.started_at:
                        ir.total_work_time = now - ir.started_at.astimezone(_TZ)

                case ItemRunStatus.FAILED:
                    ir.exception_at = now
                    ir.last_updated_at = now
                    ir.exception_reason = exception_reason or 'Error with no message.'
                    if ir.started_at:
                        ir.total_work_time = now - ir.started_at.astimezone(_TZ)

            session.flush()

    @staticmethod
    def update_items_result(item_ids: list[int], result: str) -> None:
        """
        Writes the challenge's closing message onto each item.

        The same text on all of them, because the site reports one score for the
        whole run rather than one per record.
        """
        with get_session() as session:
            for item_id in item_ids:
                it: Any = session.execute(
                    select(ORMItem).where(ORMItem.item_id == item_id)
                ).scalar_one_or_none()
                if it is not None:
                    it.result = result
            session.flush()
