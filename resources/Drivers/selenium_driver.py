"""
BrowserDriver implementation on top of Selenium WebDriver.

Every bit of Selenium knowledge is confined here. Both drivers share the same
selectors and the same time limit, so the benchmark measures the library rather
than the quality of the code on each side.
"""

from collections.abc import Callable
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from resources.Drivers import selectors
from resources.Drivers.base import DEFAULT_TIMEOUT_MS


class SeleniumDriver:
    """
    Drives the RPA Challenge with Selenium WebDriver.

    Conformance to BrowserDriver is structural, so there is no inheritance. The
    browser starts on the first open(), not in __init__, so building the driver
    is cheap and leaves no process hanging if something fails before it is used.
    """

    name = 'selenium'

    def __init__(
        self,
        headless: bool = True,
        path_browser: str = '',
        path_driver: str = '',
    ):
        """
        Empty paths mean defaults: the system Chrome, and the chromedriver
        Selenium Manager resolves. Neither is read from the settings here — the
        caller assembling the driver decides, which is what keeps this testable.
        """
        self._headless = headless
        self._path_browser = path_browser
        self._path_driver = path_driver
        self._browser: webdriver.Chrome | None = None

    @property
    def _active_browser(self) -> webdriver.Chrome:
        """
        The browser in use, or a readable error if open() was never called.

        Without it, using the driver out of order raises AttributeError on None.
        """
        if self._browser is None:
            raise RuntimeError('Selenium driver not started: call open(url) first.')
        return self._browser

    def _wait_for(
        self,
        condition: Callable[[tuple[str, str]], Any],
        selector: str,
    ) -> WebElement:
        """
        Waits for a condition on the selector and returns the element.

        Playwright's actions run these checks themselves; Selenium's do not, so
        without this helper every method would repeat the same four lines. That
        is one of the costs the benchmark measures. Parity is approximate:
        element_to_be_clickable covers present, visible and enabled, but not
        stable or unobstructed. DEFAULT_TIMEOUT_MS is in milliseconds because
        that is Playwright's unit; the conversion to seconds happens here.
        """
        wait = WebDriverWait(self._active_browser, DEFAULT_TIMEOUT_MS / 1000)
        return wait.until(condition((By.XPATH, selector)))

    def open(self, url: str) -> None:
        """Starts the browser on the first call and navigates to the URL."""
        if self._browser is None:
            options = Options()

            if self._headless:
                # --headless=new is Chrome's modern headless mode; the old one
                # had behaviour differences that produced CI-only failures.
                options.add_argument('--headless=new')
            else:
                # A run watched by the operator: window filling the screen.
                options.add_argument('--start-maximized')

            if self._path_browser:
                options.binary_location = self._path_browser

            # Service is omitted - not left empty - when no chromedriver is
            # pointed at: Selenium Manager then resolves the matching version.
            service = None
            if self._path_driver:
                service = Service(executable_path=self._path_driver)

            self._browser = webdriver.Chrome(options=options, service=service)
            self._browser.set_page_load_timeout(DEFAULT_TIMEOUT_MS / 1000)

        self._active_browser.get(url)

    def click_start(self) -> None:
        """Clicks 'Start'."""
        self._wait_for(EC.element_to_be_clickable, selectors.XPATH_START_BUTTON).click()

    def fill_field(self, label: str, value: str) -> None:
        """
        Fills the field whose visible label is `label`.

        The clear() before send_keys reproduces the behaviour of Playwright's
        fill(), which replaces the content instead of appending to whatever is
        already there.
        """
        selector = selectors.XPATH_FIELD_BY_LABEL.format(label=label)
        field = self._wait_for(EC.element_to_be_clickable, selector)
        field.clear()
        field.send_keys(value)

    def submit(self) -> None:
        """Clicks 'Submit'."""
        self._wait_for(EC.element_to_be_clickable, selectors.XPATH_SUBMIT_BUTTON).click()

    def read_result(self) -> str:
        """
        Waits for the closing message to become visible and returns its text.

        The wait is explicit because the contract promises `str`: reading
        before the site renders would return an empty string.
        """
        return self._wait_for(
            EC.visibility_of_element_located, selectors.XPATH_RESULT
        ).text

    def close(self) -> None:
        """
        Shuts down the browser and the chromedriver process.

        quit() takes both down; close() would only shut the window, leaving the
        driver process alive. Idempotent — calling it twice does not break.
        """
        try:
            if self._browser is not None:
                self._browser.quit()
        finally:
            self._browser = None
