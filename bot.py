"""
The bot's entry point.

    poetry run python bot.py
    poetry run python bot.py --driver selenium
    poetry run python bot.py --help

Only reading the command line and talking to the orchestrator go at the top —
neither of them needs any configuration. Alembic and Execute are imported
inside the execution block, and that is not a matter of style: importing
`resources.execute` opens the chain that reads config.json and builds the
database engine. In there, that failure happens **inside the try** and reaches
the Maestro panel with its real cause; at the top of the file it would take the
process down before anyone existed to report it — and would make `--help`
require a finished configuration.
"""

from resources.environment import require_supported_python

# Before the imports below: on the wrong version nothing was installed, and the
# Maestro SDK would blow up first, silencing the message that says what to do.
require_supported_python()

from resources.cli import driver_from_argv  # noqa: E402
from resources.Tools.botcity import connect, report_failure  # noqa: E402

if __name__ == '__main__':
    driver = driver_from_argv()
    maestro = connect()

    # Only the startup goes inside the try. execute() stays out because it
    # already reports its own outcome: wrapping it here would make the same
    # failure be reported twice, and the second call could blow up, masking the
    # original error.
    try:
        from alembic import command
        from alembic.config import Config

        from resources.execute import Execute

        command.upgrade(Config('alembic.ini'), 'head')
        executor = Execute(maestro, driver)
    except Exception as error:
        report_failure(maestro, error)
        raise

    executor.execute()
