"""
Tests for the BotCity Maestro communication (Tools/botcity.py).

The module imports neither settings nor database — a requirement, not a
coincidence: report_failure has to work precisely when config.json is missing
or the database is down. That is what makes these tests possible with nothing
started.
"""

from unittest.mock import MagicMock

from botcity.maestro import AutomationTaskFinishStatus

from resources.Tools.botcity import (
    Counts,
    get_task_parameters,
    report_completion,
    report_failure,
)


def test_a_local_run_reports_nothing():
    """With no task_id there is no orchestrator waiting for an answer."""
    maestro = MagicMock(task_id=None)

    report_failure(maestro, ValueError('anything at all'))

    maestro.finish_task.assert_not_called()


def test_it_reports_the_failure_with_the_exception_type_and_text():
    """
    The type goes in alongside the text because it sends the investigation to
    different places: FileNotFoundError is a deployment problem, ValueError is
    a wrong parameter on the task.
    """
    maestro = MagicMock(task_id='24475890')

    report_failure(maestro, FileNotFoundError('config.json not found'))

    maestro.finish_task.assert_called_once()
    arguments = maestro.finish_task.call_args.kwargs
    assert arguments['status'] == AutomationTaskFinishStatus.FAILED
    assert arguments['task_id'] == '24475890'
    assert arguments['message'] == ('FileNotFoundError: config.json not found')


def test_a_numeric_task_id_becomes_text():
    """The SDK expects task_id as str; the runner may hand over another type."""
    maestro = MagicMock(task_id=24475890)

    report_failure(maestro, RuntimeError('it failed'))

    assert maestro.finish_task.call_args.kwargs['task_id'] == '24475890'


def test_the_failure_carries_the_driver_when_one_had_been_chosen():
    """
    In a startup failure there is no driver yet, and the suffix does not
    appear — a blank field would be noise in a message the operator reads in a
    hurry.
    """
    maestro = MagicMock(task_id='1')

    report_failure(maestro, RuntimeError('site is down'), driver='selenium')

    message = maestro.finish_task.call_args.kwargs['message']
    assert message == 'RuntimeError: site is down (driver: selenium)'


def test_a_failure_with_no_driver_leaves_no_empty_suffix():
    maestro = MagicMock(task_id='1')

    report_failure(maestro, RuntimeError('it failed'))

    assert maestro.finish_task.call_args.kwargs['message'] == ('RuntimeError: it failed')


def test_a_startup_failure_reports_zeroed_counts():
    """Nothing got to run, and the panel needs to show that."""
    maestro = MagicMock(task_id='1')

    report_failure(maestro, ValueError('config'))

    arguments = maestro.finish_task.call_args.kwargs
    assert arguments['total_items'] == 0
    assert arguments['processed_items'] == 0
    assert arguments['failed_items'] == 0


def test_completion_with_no_failures_carries_result_driver_and_counts():
    maestro = MagicMock(task_id='42')
    counts = Counts(total=10, processed=10, failed=0)

    report_completion(
        maestro,
        counts,
        driver='selenium',
        result='Your success rate is 100% ( 70 out of 70 fields)',
    )

    arguments = maestro.finish_task.call_args.kwargs
    assert arguments['status'] == AutomationTaskFinishStatus.SUCCESS
    assert 'Completed with selenium.' in arguments['message']
    assert '100% ( 70 out of 70 fields)' in arguments['message']
    assert arguments['total_items'] == counts.total
    assert arguments['processed_items'] == counts.processed


def test_completion_with_failed_items_becomes_partially_completed():
    """
    The queue finished, but not every item passed. `FAILED` would be a lie — it
    says "it never ran" — and `SUCCESS` would hide the records left behind. To
    the operator, "finished with failures" calls for a different action from
    either.
    """
    maestro = MagicMock(task_id='42')
    counts = Counts(total=10, processed=7, failed=3)

    report_completion(maestro, counts, driver='playwright', result='70%')

    arguments = maestro.finish_task.call_args.kwargs
    assert arguments['status'] == AutomationTaskFinishStatus.PARTIALLY_COMPLETED
    assert 'Completed with failures' in arguments['message']
    assert arguments['processed_items'] == counts.processed
    assert arguments['failed_items'] == counts.failed


def test_completion_in_a_local_run_reports_nothing():
    maestro = MagicMock(task_id=None)

    report_completion(maestro, Counts(), driver='playwright', result='ok')

    maestro.finish_task.assert_not_called()


def test_parameters_in_a_local_run_are_an_empty_dictionary():
    """
    Always returning the same type spares the caller from checking whether
    there is a run at all — that `if` used to live inside Execute before this
    was consolidated.
    """
    maestro = MagicMock(task_id=None)

    assert get_task_parameters(maestro) == {}
    maestro.get_execution.assert_not_called()


def test_parameters_come_from_the_execution_when_orchestrated():
    maestro = MagicMock(task_id='42')
    maestro.get_execution.return_value = MagicMock(parameters={'driver': 'selenium'})

    assert get_task_parameters(maestro) == {'driver': 'selenium'}


def test_the_invalid_driver_message_arrives_whole():
    """
    The case that motivated all of this: before, this error died in __init__
    and the panel showed only the runner's generic message.
    """
    maestro = MagicMock(task_id='1')
    error = ValueError(
        'Task parameter "driver" has an unknown value: \'cypress\'. '
        'Available: playwright, selenium.'
    )

    report_failure(maestro, error)

    message = maestro.finish_task.call_args.kwargs['message']
    assert message.startswith('ValueError: ')
    assert 'cypress' in message
    assert 'playwright, selenium' in message
