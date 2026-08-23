"""
1 - Business flow of the RPA Challenge.
2 - Talks to the browser exclusively through the BrowserDriver contract.
3 - Imports neither Playwright nor Selenium: which library drives the screen is
    a decision for whoever assembles the driver, and this module need not know.
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

A data map, rather than seven hand-written calls: adding a field to the form
becomes one line here, with no driver touched. The labels are the ones the
challenge actually displays, and they are what the fields are located by — the
site shuffles their order on every round.
"""


class Challenge:
    """Runs the RPA Challenge flow over any BrowserDriver."""

    def __init__(self, driver: BrowserDriver, logs: Logs) -> None:
        """
        Args:
            driver: An already built BrowserDriver implementation.
            logs: Logs instance used to record the operations.
        """
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

        Args:
            item: Pydantic schema holding the current record's data, read from
                  the item table through get_queued_items_by_run.
        """
        self.logs.info(f'Filling form: {item.First_Name} {item.Last_Name}.')

        for label, attribute in FORM_FIELDS.items():
            self.driver.fill_field(label, getattr(item, attribute))

        self.driver.submit()

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
