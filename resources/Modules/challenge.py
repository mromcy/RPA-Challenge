"""
Business flow of the RPA Challenge.

Talks to the browser only through the BrowserDriver contract and imports
neither Playwright nor Selenium: which library drives the screen is decided by
whoever assembles the driver, and this module never finds out.
"""

from resources.Drivers.base import BrowserDriver
from resources.Schemas.item_run import Item
from resources.Tools.logs import Logs

FORM_FIELDS = {
    'First Name': 'First_Name',
    'Last Name': 'Last_Name',
    'Company Name': 'Company_Name',
    'Role in Company': 'Role_in_Company',
    'Address': 'Address',
    'Email': 'Email',
    'Phone Number': 'Phone_Number',
}
"""
Label shown on screen → matching attribute on Item.

A data map rather than seven hand-written calls, so adding a field is one line
and no driver changes. The labels are what the fields are located by, because
the site shuffles their order on every round.
"""


class Challenge:
    """Runs the RPA Challenge flow over any BrowserDriver."""

    def __init__(self, driver: BrowserDriver, logs: Logs) -> None:
        self.driver = driver
        self.logs = logs

    def start_challenge(self, url: str) -> None:
        """
        Navigates to the challenge URL and clicks 'Start'.

        Must be called exactly once before any form is filled.

        Args:
            url: URL of the system to reach, coming from the settings.
        """
        self.logs.info(
            f'Navigating to the RPA Challenge with the {self.driver.name} driver.'
        )
        self.driver.open(url)
        self.driver.click_start()
        self.logs.info('Challenge started successfully.')

    def fill_form(self, item: Item) -> None:
        """
        Fills every field of the form and submits it.

        **The submit is in a finally, and that is the whole point.** The site
        has ten fixed rounds and only advances on submit, so submitting only on
        success would leave a failed record sitting on its round: the next item
        fills the same form, the tenth is never submitted, and read_result waits
        out its full timeout. One bad record would cost the other nine.

        Submitting the partial form lets the round advance. The site scores
        those fields as wrong, which is true, and the final rate drops below
        100% - the honest outcome rather than a hidden one.

        The submit is itself guarded because a raise inside a finally
        **replaces** the original exception, and a dead browser is the real
        cause, not the submit that followed it.
        """
        self.logs.info(f'Filling form: {item.First_Name} {item.Last_Name}.')

        try:
            for label, attribute in FORM_FIELDS.items():
                self.driver.fill_field(label, getattr(item, attribute))
        finally:
            try:
                self.driver.submit()
            except Exception as submit_error:
                self.logs.warning(f'Failed to submit the form: {submit_error}')

    def capture_result(self) -> str:
        """
        Returns the text of the final result shown after the last submission.

        Waiting for the element is the driver's responsibility, guaranteed by
        the contract — which is why the return type is str, and no longer
        str | None as it used to be.

        Returns:
            str: The result text, e.g. 'Your success rate is 100% ...'.
        """
        result = self.driver.read_result()
        self.logs.info(result)

        return result
