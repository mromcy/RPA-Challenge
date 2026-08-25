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
    Reads the driver from a Maestro task's parameters, or None if absent.

    It lets the panel choose the library for one run, with no redeploy and no
    second automation registered. An unknown value raises here, at launch,
    rather than after the migrations have run and the run record already exists.
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
    Decides the driver in three layers, most specific first.

    1. `--driver` on the command line: whoever typed it wanted this, now.
    2. The Maestro task parameter: a choice for *this* run, from the panel.
    3. None, which lets create_driver fall back to the machine's DRIVER.
    """
    return from_command_line or driver_from_parameters(task_parameters)


def create_driver(name: str | None = None, headless: bool = True) -> BrowserDriver:
    """
    Returns the named driver, configured from the settings. Omitted, uses
    Settings.DRIVER.

    The library imports sit **inside** each branch on purpose: a run should only
    pay for the library it uses (playwright.sync_api loads 177 modules,
    selenium.webdriver 23), and the benchmark measures startup — importing both
    every time would add the same cost to both sides and hide the difference it
    exists to show. Hence the `noqa: PLC0415` on both lines.
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
