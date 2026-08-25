"""
Checking the environment before the bot starts.

Only the standard library goes in here, and that is a requirement rather than a
matter of style: this module has to be importable on exactly the machine where
nothing else is installed.
"""

import sys

MINIMUM_VERSION = (3, 11)
"""
The lowest accepted Python, inclusive.

Not a matter of taste: it is the floor the dependencies declare. Of the 60
installed packages, numpy and pandas are the strictest, and both ask for
`>=3.11`.
"""

FIRST_UNSUPPORTED_VERSION = (3, 14)
"""
The first version **not** accepted, exclusive.

The ceiling has an owner: `psycopg-binary` publishes one wheel per interpreter
version, and 3.2.9 — pinned with `==` in pyproject.toml — stops at cp313. On
3.14 pip finds no binary, tries to build from source and needs libpq and a C
compiler, which an ordinary Windows workstation does not have. When psycopg is
bumped to a version with a cp314 wheel, this ceiling can rise with it.
"""

RUNNING_VERSION = (sys.version_info.major, sys.version_info.minor)
"""
The version of the running interpreter, as a pair of integers.

Extracted field by field, rather than taken from `sys.version_info` whole,
because that object has five positions and the fourth is text (`'final'`,
`'beta'`) — it is not a tuple of integers, however much the first two positions
may look like one.
"""


def require_supported_python(version: tuple[int, ...] = RUNNING_VERSION) -> None:
    """
    Stops the process with a readable message on an unsupported interpreter.

    It runs before the other imports because on the wrong version nothing was
    installed, and the first third-party import would blow up first, hiding the
    message that says what to do.
    """
    if MINIMUM_VERSION <= version[:2] < FIRST_UNSUPPORTED_VERSION:
        return

    def format_version(parts: tuple[int, ...]) -> str:
        return '.'.join(str(part) for part in parts)

    raise SystemExit(
        f'This bot requires Python >= {format_version(MINIMUM_VERSION)} and '
        f'< {format_version(FIRST_UNSUPPORTED_VERSION)}; found '
        f'{format_version(version[:2])}.\n'
        'The requirements are exported with markers for that range, so outside '
        'it pip installs no dependency at all and still reports success.'
    )
