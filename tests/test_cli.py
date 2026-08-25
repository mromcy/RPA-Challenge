"""
Tests for the command-line argument reading (resources/cli.py).

What these tests protect: BotMaestroSDK.from_sys_args() reads the command line
**by position**, unpacking sys.argv[1:] as
(server, task_id, token, organization). Any argument of ours left in there
shifts the positions and makes the bot connect to the wrong place.
"""

import sys

import pytest

from resources.cli import driver_from_argv, extract_driver

MAESTRO = ['https://server.botcity', '12345', 'secret-token', 'my-org']


def test_no_driver_returns_none_and_leaves_the_command_line_alone():
    argv = ['bot.py', *MAESTRO]

    driver, remaining = extract_driver(argv)

    assert driver is None
    assert remaining == argv


def test_driver_after_the_maestro_arguments():
    argv = ['bot.py', *MAESTRO, '--driver', 'selenium']

    driver, remaining = extract_driver(argv)

    assert driver == 'selenium'
    assert remaining == ['bot.py', *MAESTRO]


def test_driver_before_the_maestro_arguments_preserves_the_order():
    """
    The case that justifies the cleanup: without removing --driver, the SDK
    would read server='--driver' and task_id='selenium'.
    """
    argv = ['bot.py', '--driver', 'selenium', *MAESTRO]

    driver, remaining = extract_driver(argv)

    assert driver == 'selenium'
    assert remaining == ['bot.py', *MAESTRO]


def test_local_run_with_the_driver_alone():
    driver, remaining = extract_driver(['bot.py', '--driver', 'playwright'])

    assert driver == 'playwright'
    assert remaining == ['bot.py']


def test_an_unknown_driver_exits_with_an_error():
    with pytest.raises(SystemExit):
        extract_driver(['bot.py', '--driver', 'cypress'])


def test_help_exits_without_running_anything():
    """
    With add_help turned off, --help would become an unknown argument and the
    bot would run — opening a browser for someone who only wanted to read the
    help.
    """
    with pytest.raises(SystemExit):
        extract_driver(['bot.py', '--help'])


def test_driver_from_argv_rewrites_sys_argv(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['bot.py', '--driver', 'selenium', *MAESTRO])

    driver = driver_from_argv()

    assert driver == 'selenium'
    assert sys.argv == ['bot.py', *MAESTRO]
