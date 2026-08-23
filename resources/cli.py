"""
Reading the bot's command-line arguments.

It lives outside bot.py so that the entry point stays nothing but an entry
point, and so that this logic is testable: importing bot.py drags in the
orchestrator and, with it, the database connection.

The split follows the pattern used everywhere else in the project —
extract_driver is a pure function and holds the rule; driver_from_argv is the
thin shell that reads and rewrites global state.
"""

import argparse
import sys

from resources.Drivers.factory import AVAILABLE_DRIVERS


def extract_driver(argv: list[str]) -> tuple[str | None, list[str]]:
    """
    Extracts --driver from the command line and returns what was left.

    It uses parse_known_args() rather than parse_args() because the bot is also
    fired by BotCity Maestro, which appends arguments of its own. parse_args
    would end the program on seeing the first unknown argument — that is, the
    bot would die at the gate every time the orchestrator called it.

    Args:
        argv: The full command line, including the script name at position 0.

    Returns:
        tuple[str | None, list[str]]: The requested driver (None if absent) and
            the command line without the consumed arguments, with the script
            name preserved at position 0.

    Raises:
        SystemExit: If --driver is given a value outside AVAILABLE_DRIVERS, or
            if --help is requested. Standard argparse behaviour.
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

    The removal is not cosmetic. BotMaestroSDK.from_sys_args() reads the
    command line **by position**, unpacking sys.argv[1:] as
    (server, task_id, token, organization). One extra argument before them
    shifts everything: the bot would try to connect to a server called
    '--driver'. Taking out what has already been consumed hands the SDK exactly
    the line it expects, no matter where --driver was typed.

    Returns:
        str | None: The driver name, or None if it was not supplied.
    """
    driver, remaining = extract_driver(sys.argv)
    sys.argv = remaining

    return driver
