"""
Building the driver from its name.

This is the only place in the project that knows both implementations at once.
The rest of the code knows only the BrowserDriver contract.
"""

from collections.abc import Mapping

from resources.Drivers.base import BrowserDriver
from resources.settings import get_settings

AVAILABLE_DRIVERS = ('playwright', 'selenium')


def driver_from_parameters(parameters: Mapping[str, object]) -> str | None:
    """
    Reads the driver from the parameters of a BotCity Maestro task.

    It allows choosing the library when firing the task from the panel, with no
    redeploy and without registering a second automation. It lives here, and
    not in execute.py, because that module cannot be imported without a
    database — the rule would be out of reach of the unit suite.

    Args:
        parameters: The run's parameter dictionary. Empty in local mode.

    Returns:
        str | None: The driver name, or None when the parameter was not
            supplied — in which case the decision falls back to Settings.DRIVER.

    Raises:
        ValueError: If the parameter carries an unknown driver. Failing here,
            at launch, is better than failing after the migrations have run and
            the run record already exists in the database.
    """
    value = parameters.get('driver')
    if not value:
        return None

    name = str(value).strip().lower()
    if name not in AVAILABLE_DRIVERS:
        raise ValueError(
            f'Task parameter "driver" has an unknown value: {value!r}. '
            f'Available: {", ".join(AVAILABLE_DRIVERS)}.'
        )

    return name


def resolve_driver(
    from_command_line: str | None,
    task_parameters: Mapping[str, object],
) -> str | None:
    """
    Decides the driver in three layers, from the most specific to the most
    general.

    1. `--driver` on the command line: whoever typed it now wanted this now.
    2. The Maestro task's `driver` parameter: a choice for *this* run, made in
       the panel, with no redeploy.
    3. `None`, letting `create_driver` fall back to `DRIVER` from config.json,
       which is the machine's default.

    Args:
        from_command_line: The value of `--driver`, if supplied.
        task_parameters: The run's parameters. Empty in local mode.

    Returns:
        str | None: The chosen driver, or None to use the machine's default.

    Raises:
        ValueError: If the task parameter carries an unknown driver.
    """
    return from_command_line or driver_from_parameters(task_parameters)


def create_driver(name: str | None = None, headless: bool = True) -> BrowserDriver:
    """
    Returns the requested driver, already configured from the settings.

    The library imports happen **inside** each branch, and not at the top of
    the module, for two reasons. First, a run should only pay the cost of
    importing the library it is going to use: `playwright.sync_api` loads 177
    modules and `selenium.webdriver` loads 23. Second, and more importantly:
    the benchmark measures startup time, and importing both on every run would
    add the same cost to both sides, hiding the real startup difference.

    That is why both import lines carry `noqa: PLC0415` — the rule is right as
    a default, and this is the exception it exists to allow.

    Args:
        name: 'playwright' or 'selenium'. Omitted, uses Settings.DRIVER.
        headless: No visible window.

    Returns:
        BrowserDriver: An implementation ready to use.

    Raises:
        ValueError: If the name matches no known driver.
    """
    settings = get_settings()
    chosen = (name or settings.DRIVER).strip().lower()

    if chosen == 'playwright':
        from resources.Drivers.playwright_driver import (  # noqa: PLC0415
            PlaywrightDriver,
        )

        return PlaywrightDriver(
            headless=headless,
            path_browser=settings.PATH_BROWSER,
        )

    if chosen == 'selenium':
        from resources.Drivers.selenium_driver import (  # noqa: PLC0415
            SeleniumDriver,
        )

        return SeleniumDriver(
            headless=headless,
            path_browser=settings.PATH_BROWSER,
            path_driver=settings.PATH_SELENIUM_DRIVER,
        )

    raise ValueError(
        f'Unknown driver: {chosen!r}. Available: {", ".join(AVAILABLE_DRIVERS)}.'
    )
