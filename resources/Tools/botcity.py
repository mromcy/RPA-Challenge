"""
Communication with BotCity Maestro.

Every conversation with the orchestrator goes through here: connecting, reading
the task parameters and reporting the outcome. The other modules hand over the
data and do not assemble panel messages — before this was consolidated, the
format of the failure message was written in two places, with a comment
confessing the duplication.

This module **imports neither settings nor database**, and must not: report_
failure has to work precisely when config.json is missing or the database is
down, which are two of the failures it exists to report.

The bot authenticates with the run token the runner hands it on the command
line, not with an API key kept in a file. The consequence is that no long-lived
credential sits at rest on the bot's machine. The API-key path would only make
sense for a process that **calls** the orchestrator instead of being called by
it — an internal portal that creates tasks, a network-folder watcher, a CI
pipeline — and this bot is never in that position.
"""

from collections.abc import Mapping
from typing import NamedTuple

from botcity.maestro import AutomationTaskFinishStatus, BotMaestroSDK


class Counts(NamedTuple):
    """
    The three numbers the Maestro panel shows for a run.

    They always travel together — they are exactly what finish_task receives —
    so they move as one thing instead of three loose parameters. The field
    names mirror the SDK's own: total_items, processed_items, failed_items.
    """

    total: int = 0
    processed: int = 0
    failed: int = 0


def connect() -> BotMaestroSDK:
    """
    Returns the SDK ready to use, working in both execution modes.

    `from_sys_args()` sorts both out by itself: with four or more arguments on
    the command line it reads server/task_id/token/organization **by position**
    and connects to the orchestrator; below that it returns a local instance,
    with an empty task_id, and no call to Maestro has any effect.

    Returns:
        BotMaestroSDK: Connected to the orchestrator, or in local mode.
    """
    maestro = BotMaestroSDK.from_sys_args()

    if not maestro.task_id:
        print('Running in local mode (no task_id).')

    return maestro


def get_task_parameters(maestro: BotMaestroSDK) -> Mapping[str, object]:
    """
    The parameters supplied when the task was fired from the panel.

    In local mode it returns an empty dictionary, which spares the caller from
    checking whether there is a run at all: the result always has the same type.

    Args:
        maestro: An already connected SDK.

    Returns:
        Mapping[str, object]: The task parameters, or empty in local mode.
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
    Closes a task that ran to the end, with the outcome readable in the panel.

    The status distinguishes the two possible outcomes of a complete run:
    `SUCCESS` when no item failed, `PARTIALLY_COMPLETED` when the queue
    finished but some items errored. `FAILED` is reserved for a run that did
    **not** reach the end — that is what report_failure uses.

    The distinction matters to whoever operates the bot: "it finished, but
    seven records were left behind" calls for a different action than "it never
    ran".

    The message carries the text the site itself reported and the driver used:
    it is what the operator needs to know without opening any log.

    Args:
        maestro: An already connected SDK. With no task_id, it does nothing.
        counts: Total, processed and failed.
        driver: Name of the driver that ran.
        result: The result text reported by the site.
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
    Closes the task as FAILED, with the real cause.

    Without this, a startup failure — a missing `config.json`, a database that
    is down, an invalid driver in the task parameter — kills the process before
    any `finish_task`, and the panel shows only *"An unexpected issue led to
    the task being terminated"*, which tells nobody what to do.

    The message carries the **type** of the exception along with its text:
    `FileNotFoundError` and `ValueError` send the investigation to different
    places. The full stack stays out — fifty lines in a panel help nobody — and
    is still recorded in `process_run.error_stack` and in the log file.

    Args:
        maestro: An already connected SDK. With no task_id, it does nothing.
        error: The exception that interrupted the run.
        counts: How much had been processed by the time of the failure. In a
            startup failure, zeros — nothing got to run.
        driver: The driver in use, when one had already been chosen.
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
