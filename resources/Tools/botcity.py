"""
Communication with BotCity Maestro: connecting, reading task parameters and
reporting the outcome. Panel messages are assembled only here.

This module **imports neither settings nor database**, and must not:
report_failure has to work precisely when config.json is missing or the database
is down, which are two of the failures it exists to report.

The bot authenticates with the run token the runner passes on the command line,
so no long-lived credential sits at rest on its machine. An API key would only
make sense for a process that *calls* the orchestrator instead of being called
by it, and this bot is never in that position.
"""

from collections.abc import Mapping
from typing import NamedTuple

from botcity.maestro import AutomationTaskFinishStatus, BotMaestroSDK


class Counts(NamedTuple):
    """
    The three numbers the Maestro panel shows for a run.

    They are exactly what finish_task receives, so they travel as one thing
    rather than three loose parameters, under the SDK's own field names.
    """

    total: int = 0
    processed: int = 0
    failed: int = 0


def connect() -> BotMaestroSDK:
    """
    The SDK ready to use, in either execution mode.

    from_sys_args sorts it out: four or more arguments and it reads
    server/task_id/token/organization **by position** and connects; fewer and it
    returns a local instance whose task_id is empty, where no call has effect.
    """
    maestro = BotMaestroSDK.from_sys_args()

    if not maestro.task_id:
        print('Running in local mode (no task_id).')

    return maestro


def get_task_parameters(maestro: BotMaestroSDK) -> Mapping[str, object]:
    """
    The parameters supplied when the task was fired from the panel.

    Empty in local mode rather than None, so the caller never has to ask whether
    there is a run at all.
    """
    if not maestro.task_id:
        return {}

    return maestro.get_execution().parameters


def report_completion(
    maestro: BotMaestroSDK,
    counts: Counts,
    driver: str,
    result: str,
) -> None:
    """
    Closes a task that ran to the end. Does nothing without a task_id.

    SUCCESS when no item failed, PARTIALLY_COMPLETED when the queue finished
    with some errors. FAILED is reserved for a run that never reached the end —
    that is report_failure's job. The distinction matters to whoever operates
    the bot: "it finished, but seven records were left behind" calls for a
    different action than "it never ran".
    """
    if not maestro.task_id:
        return

    had_failures = counts.failed > 0
    status = (
        AutomationTaskFinishStatus.PARTIALLY_COMPLETED
        if had_failures
        else AutomationTaskFinishStatus.SUCCESS
    )
    opening = 'Completed with failures' if had_failures else 'Completed'

    maestro.finish_task(
        task_id=str(maestro.task_id),
        status=status,
        message=(
            f'{opening} with {driver}. {result} '
            f'Processed: {counts.processed} '
            f'- Failed: {counts.failed} '
            f'- Total items: {counts.total}'
        ),
        total_items=counts.total,
        processed_items=counts.processed,
        failed_items=counts.failed,
    )


def report_failure(
    maestro: BotMaestroSDK,
    error: Exception,
    counts: Counts = Counts(),
    driver: str = '',
) -> None:
    """
    Closes the task as FAILED, with the real cause. Does nothing without a
    task_id.

    Without it a startup failure kills the process before any finish_task, and
    the panel shows only "An unexpected issue led to the task being terminated",
    which tells nobody what to do. The message carries the exception **type**
    along with its text, because FileNotFoundError and ValueError send the
    investigation to different places; the stack stays out of the panel and in
    process_run.error_stack.
    """
    if not maestro.task_id:
        return

    suffix = f' (driver: {driver})' if driver else ''

    maestro.finish_task(
        task_id=str(maestro.task_id),
        status=AutomationTaskFinishStatus.FAILED,
        message=f'{type(error).__name__}: {error}{suffix}',
        total_items=counts.total,
        processed_items=counts.processed,
        failed_items=counts.failed,
    )
