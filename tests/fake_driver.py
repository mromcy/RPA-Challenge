"""
A browser stand-in for the business-flow tests.

It does not inherit from BrowserDriver and imports nothing from resources:
conformance to the Protocol is structural, and that is exactly what lets the
test live outside the production code's hierarchy.

Instead of driving a screen, it records the calls it receives — which turns
"the bot filled the seven fields with the right values" into a dictionary
assertion, with no browser, in milliseconds.
"""

DEFAULT_RESULT = 'Your success rate is 100% ( 70 out of 70 fields) in 678 milliseconds'


class FakeDriver:
    """A BrowserDriver implementation that records what it was asked to do."""

    name = 'fake'

    def __init__(self, result: str = DEFAULT_RESULT):
        """
        Args:
            result: The text read_result() will return.
        """
        self.calls: list[tuple] = []
        self.filled_fields: dict[str, str] = {}
        self._result = result

    @property
    def operations(self) -> list[str]:
        """Only the operation names, in order — for sequence assertions."""
        return [call[0] for call in self.calls]

    def open(self, url: str) -> None:
        self.calls.append(('open', url))

    def click_start(self) -> None:
        self.calls.append(('click_start',))

    def fill_field(self, label: str, value: str) -> None:
        self.calls.append(('fill_field', label, value))
        self.filled_fields[label] = value

    def submit(self) -> None:
        self.calls.append(('submit',))

    def read_result(self) -> str:
        self.calls.append(('read_result',))
        return self._result

    def close(self) -> None:
        self.calls.append(('close',))
