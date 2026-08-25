"""
The contract the business flow uses to talk to the browser.

This module imports neither Playwright nor Selenium, and must not. It is the
only point that both the flow (Modules/challenge.py) and the implementations
(Drivers/playwright_driver.py, Drivers/selenium_driver.py) can know about
without dragging a browser library along — which is what makes it possible to
test the flow with no browser at all.

The operations speak the language of the challenge ("fill the field with this
label"), not that of the library ("page.locator(...).fill(...)").
"""

from typing import Protocol

DEFAULT_TIMEOUT_MS = 30_000
"""
The time limit for every wait, in milliseconds, shared by both drivers.

It lives here, rather than inside each implementation, because the benchmark
comparison only holds if both have the same patience. Different numbers would
make one give up before the other whenever the site slowed down, and the
difference would show up in the table as if it were the library's merit.
"""


class BrowserDriver(Protocol):
    """
    The operations the challenge needs from a browser.

    A Protocol rather than an abstract base class: conformance is structural,
    meaning it is enough for the class to have the methods with the right
    signatures. No implementation has to inherit from this contract or import
    it — including the FakeDriver used by the tests, which lives in tests/ and
    knows nothing about resources/.

    Verification is static: what reports a missing method is the type checker,
    not the interpreter. That is only worth writing down because CI runs one -
    `mypy` gates every push, next to ruff. Before it did, this paragraph
    described a check nobody performed, and the Protocol was documentation
    wearing the costume of a contract.
    """

    name: str
    """Identifies the driver in the logs and in the benchmark table."""

    def open(self, url: str) -> None:
        """Starts the browser, if not up yet, and navigates to the URL."""
        ...

    def click_start(self) -> None:
        """Clicks the 'Start' button. The boundary between launch and filling."""
        ...

    def fill_field(self, label: str, value: str) -> None:
        """
        Fills the field identified by the label visible on screen.

        One method for every field, addressed by label, so that the interface
        does not grow with each new field added to the form.
        """
        ...

    def submit(self) -> None:
        """Clicks 'Submit', sending the current form."""
        ...

    def read_result(self) -> str:
        """
        Waits for the final result to appear and returns its text.

        The return type is str and not str | None on purpose: waiting is the
        implementation's obligation, not the caller's luck.
        """
        ...

    def close(self) -> None:
        """Shuts the browser down and releases its resources."""
        ...
