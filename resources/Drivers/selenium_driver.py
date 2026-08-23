"""
BrowserDriver implementation on top of Selenium WebDriver.

All of the project's Selenium knowledge is confined here, just as the
Playwright knowledge stays in playwright_driver.py. Both use the same selectors
and the same time limit, so that the benchmark comparison measures the library
and not the quality of the code on each side.
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

    It does not inherit from BrowserDriver: conformance to the Protocol is
    structural.

    The browser only starts on the first call to open(), not in __init__, so
    that building the driver is cheap and leaves no process hanging if
    something fails before it is used.
    """

    name = 'selenium'

    def __init__(
        self,
        headless: bool = True,
        path_browser: str = '',
        path_driver: str = '',
    ):
        """
        Args:
            headless: No visible window. The default for the bot and for the
                benchmark.
            path_browser: Browser executable. Empty means letting Selenium use
                the Chrome installed on the system — see decision 10 in the
                progress notes. It is deliberately not read from the settings
                here: the caller assembling the driver decides, which keeps the
                class testable.
            path_driver: The chromedriver executable. Empty means letting
                Selenium Manager download the version matching the browser.
                Only needed on a machine with no internet access.
        """
        self._headless = headless
        self._path_browser = path_browser
        self._path_driver = path_driver
        self._browser: webdriver.Chrome | None = None

    @property
    def _active_browser(self) -> webdriver.Chrome:
        """
        The browser in use, with an explicit error if the driver was never
        opened.

        Without this, using the driver out of order would produce an
        AttributeError on None, which does not say what to do about it.
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
        Waits for a condition to hold for the selector and returns the element.

        **What this helper does, step by step:**

        1. Builds the locator in the shape Selenium expects — the tuple
           ``(By.XPATH, selector)``.
        2. Creates a ``WebDriverWait`` with the project's shared time limit.
           ``DEFAULT_TIMEOUT_MS`` is in milliseconds, because that is
           Playwright's unit; Selenium takes seconds, so the conversion happens
           here. There is a single number in the code base, and it is the one
           both drivers honour.
        3. Calls ``.until(condition(locator))``, which **repeats the DOM
           query** — by default every 0.5 s — until the condition is satisfied
           or the time runs out. Meanwhile it swallows the exceptions Selenium
           raises while the element does not exist yet, instead of letting them
           surface.
        4. Returns the WebElement, ready to receive the action.
        5. If the time runs out, it lets the ``TimeoutException`` surface, with
           a message identifying which wait failed.

        **Why it exists:** in Playwright, `locator.click()` already performs
        these checks by itself before acting. Selenium has no built-in
        equivalent, and without a helper like this one every driver method
        would repeat the same four lines. The waiting layer Playwright hands
        over ready-made is, here, code somebody has to write and maintain — and
        that is precisely one of the costs the benchmark sets out to make
        visible.

        **What it does NOT do, and the comparison has to say so:** Selenium's
        ready-made conditions cover less than Playwright's check.
        ``element_to_be_clickable`` guarantees *present*, *visible* and
        *enabled*, but it guarantees neither *stable* (element at rest, no
        animation) nor *unobstructed* (nothing on top intercepting the click).
        Reproducing those two would take custom conditions. Parity between the
        drivers is therefore approximate — and this is where it falls short.

        Args:
            condition: A condition factory from the expected_conditions module,
                for example ``EC.element_to_be_clickable``.
            selector: The element's XPath, coming from Drivers/selectors.py.

        Returns:
            WebElement: The element that satisfied the condition.

        Raises:
            TimeoutException: If the condition does not hold within the time
                limit.
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
