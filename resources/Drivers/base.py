"""
The contract the business flow uses to talk to the browser.

Imports neither Playwright nor Selenium, and must not: it is the only thing the
flow and both implementations can share without dragging a browser library
along, which is what lets the flow be tested with no browser at all. The
operations speak the challenge's language ("fill the field with this label"),
not the library's.
"""

from typing import Protocol

DEFAULT_TIMEOUT_MS = 30_000
"""
The time limit for every wait, in milliseconds, shared by both drivers.

Here rather than in each implementation because the comparison only holds if
both have the same patience: different numbers would make one give up first
whenever the site slowed down, and the table would read that as library merit.
"""


class BrowserDriver(Protocol):
    """
    The operations the challenge needs from a browser.

    A Protocol, not an abstract base class: conformance is structural, so no
    implementation inherits from this or imports it — including the tests'
    FakeDriver, which knows nothing about resources/. What reports a missing
    method is the type checker, and that is only worth saying because CI runs
    one: `mypy` gates every push, next to ruff.
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
        Fills the field identified by the label visible on screen. One method
        for all of them, so the interface does not grow with the form.
        """
        ...

    def submit(self) -> None:
        """Clicks 'Submit', sending the current form."""
        ...

    def read_result(self) -> str:
        """
        Waits for the final result to appear and returns its text. `str`, not
        `str | None`: waiting is the implementation's job, not the caller's luck.
        """
        ...

    def close(self) -> None:
        """Shuts the browser down and releases its resources."""
        ...
