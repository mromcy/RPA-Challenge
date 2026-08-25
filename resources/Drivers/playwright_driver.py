"""
BrowserDriver implementation on top of Playwright.

All of the project's Playwright knowledge is confined here: outside this file
nobody imports `playwright`, and that is why the business flow can be tested
with no browser.
"""

from typing import Any

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from resources.Drivers import selectors
from resources.Drivers.base import DEFAULT_TIMEOUT_MS


class PlaywrightDriver:
    """
    Drives the RPA Challenge with Playwright.

    Conformance to BrowserDriver is structural, so there is no inheritance. The
    browser starts on the first open(), not in __init__, so building the driver
    is cheap and leaves no process hanging if something fails before it is used.
    """

    name = 'playwright'

    def __init__(self, headless: bool = True, path_browser: str = ''):
        """
        An empty path_browser lets Playwright drive the Chromium it manages.
        It is not read from the settings here - the caller assembling the driver
        decides, which is what keeps this testable.
        """
        self._headless = headless
        self._path_browser = path_browser
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    @property
    def _active_page(self) -> Page:
        """
        The page in use, or a readable error if open() was never called.
        """
        if self._page is None:
            raise RuntimeError('Playwright driver not started: call open(url) first.')
        return self._page

    def open(self, url: str) -> None:
        """Starts the browser on the first call and navigates to the URL."""
        if self._page is None:
            self._playwright = sync_playwright().start()

            # The argument is omitted - not left empty - when no executable is
            # pointed at: an empty string would make Playwright try to run it.
            extras: dict[str, Any] = {}
            if self._path_browser:
                extras['executable_path'] = self._path_browser

            if not self._headless:
                # A run watched by the operator: window filling the screen,
                # as it behaved before the driver existed.
                extras['args'] = ['--start-maximized']

            self._browser = self._playwright.chromium.launch(
                headless=self._headless, **extras
            )
            self._page = self._browser.new_page(no_viewport=not self._headless)

        self._active_page.goto(url, timeout=DEFAULT_TIMEOUT_MS)

    def click_start(self) -> None:
        """Clicks 'Start'."""
        self._active_page.locator(selectors.XPATH_START_BUTTON).click(
            timeout=DEFAULT_TIMEOUT_MS
        )

    def fill_field(self, label: str, value: str) -> None:
        """Fills the field whose visible label is `label`."""
        selector = selectors.XPATH_FIELD_BY_LABEL.format(label=label)
        self._active_page.locator(selector).fill(value, timeout=DEFAULT_TIMEOUT_MS)

    def submit(self) -> None:
        """Clicks 'Submit'."""
        self._active_page.locator(selectors.XPATH_SUBMIT_BUTTON).click(
            timeout=DEFAULT_TIMEOUT_MS
        )

    def read_result(self) -> str:
        """
        Waits for the closing message to become visible and returns its text.

        The wait is explicit because the contract promises `str`: reading
        before the site renders would return an empty string, which was the
        source of instability in the earlier capture_result.
        """
        locator = self._active_page.locator(selectors.XPATH_RESULT).first
        locator.wait_for(state='visible', timeout=DEFAULT_TIMEOUT_MS)
        return locator.inner_text()

    def close(self) -> None:
        """
        Shuts down browser and Playwright, in any state.

        Each step is independent: a failure closing the browser must not
        prevent stopping Playwright, which is what keeps the driver process
        alive. Idempotent — calling it twice does not break.
        """
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            self._browser = None
            self._page = None

            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None
