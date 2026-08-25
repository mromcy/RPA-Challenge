"""
Reading the bot's command-line arguments.

Outside bot.py so the entry point stays one, and so this is testable on its own.
extract_driver holds the rule and is pure; driver_from_argv is the thin shell
that rewrites global state.
"""

import argparse
import sys

from resources.Drivers.factory import AVAILABLE_DRIVERS


def extract_driver(argv: list[str]) -> tuple[str | None, list[str]]:
    """
    Extracts --driver, and returns it with the command line that was left.

    parse_known_args, not parse_args, because Maestro appends arguments of its
    own: parse_args exits on the first unknown one, so the bot would die at the
    gate every time the orchestrator called it.
    """
    parser = argparse.ArgumentParser(
        prog='bot.py',
        description='Runs the RPA Challenge.',
    )
    parser.add_argument(
        '--driver',
        choices=AVAILABLE_DRIVERS,
        help='Library that drives the browser. Default: DRIVER from config.json.',
    )

    arguments, remaining = parser.parse_known_args(argv[1:])

    return arguments.driver, [argv[0], *remaining]


def driver_from_argv() -> str | None:
    """
    Reads --driver from sys.argv and removes it from there.

    The removal is not cosmetic: BotMaestroSDK.from_sys_args reads the command
    line **by position** as (server, task_id, token, organization), so one extra
    argument ahead of them makes the bot connect to a server called '--driver'.
    """
    driver, remaining = extract_driver(sys.argv)
    sys.argv = remaining

    return driver
