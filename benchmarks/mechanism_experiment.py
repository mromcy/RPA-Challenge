"""
Experiment: where does the time difference between Playwright and Selenium come
from?

The benchmark shows Playwright ~6.7× faster in the filling phase. This script
exists to answer **why**, separating two explanations the number alone does not
tell apart:

1. **The cost of waiting** — every Selenium interaction goes through a
   WebDriverWait, which polls the DOM at intervals until the condition holds.
2. **The cost per command** — Selenium talks to the browser over HTTP with
   chromedriver, one request and one response per command, while Playwright
   keeps a persistent WebSocket. And Selenium spends three commands per field
   (locate, clear, send_keys) against Playwright's one.

The method is to isolate one variable at a time, inheriting from the production
driver and overriding the minimum:

- `SeleniumWithoutWaiting` swaps WebDriverWait for a direct find_element. If the
  time does not change, waiting is **not** the bottleneck.
- `SeleniumWithoutWaitingOrClear` also removes clear(), dropping from three
  commands per field to two. If the time falls to roughly a third, the cost is
  per command.

**These variants are not production code.** With no explicit wait, the driver
becomes susceptible to races again — which is exactly the robustness the real
driver buys with those extra statements.

    poetry run python -m benchmarks.mechanism_experiment --repetitions 3
"""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Callable
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from benchmarks import compare_drivers
from benchmarks.compare_drivers import browser_version, load_items, one_run
from resources.Drivers import selectors
from resources.Drivers.playwright_driver import PlaywrightDriver
from resources.Drivers.selenium_driver import SeleniumDriver
from resources.Modules.challenge import FORM_FIELDS
from resources.settings import get_settings


class SeleniumWithoutWaiting(SeleniumDriver):
    """Selenium with a direct find_element, no WebDriverWait. Isolates waiting."""

    name = 'selenium-no-wait'

    def _wait_for(
        self,
        # `| None` widens the parameter compared with the production driver,
        # and it is honest: this variant ignores the condition, so the caller
        # has nothing to pass. Widening a parameter in an override is legal and
        # does not force the real driver to accept None.
        condition: Callable[[tuple[str, str]], Any] | None,  # noqa: ARG002
        selector: str,
    ) -> WebElement:
        return self._active_browser.find_element(By.XPATH, selector)


class SeleniumWithoutWaitingOrClear(SeleniumWithoutWaiting):
    """Also without clear(): two commands per field instead of three."""

    name = 'selenium-no-wait-no-clear'

    def fill_field(self, label: str, value: str) -> None:
        selector = selectors.XPATH_FIELD_BY_LABEL.format(label=label)
        self._wait_for(None, selector).send_keys(value)


VARIANTS = {
    'playwright': PlaywrightDriver,
    'selenium': SeleniumDriver,
    'selenium-no-wait': SeleniumWithoutWaiting,
    'selenium-no-wait-no-clear': SeleniumWithoutWaitingOrClear,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='mechanism_experiment',
        description='Separates the cost of waiting from the cost per command '
        'in Selenium.',
    )
    parser.add_argument('--repetitions', type=int, default=3)
    arguments = parser.parse_args()

    path_browser = get_settings().PATH_BROWSER
    if not path_browser:
        raise SystemExit('PATH_BROWSER is empty: the variants need the same Chrome.')

    items = load_items()

    # 7 fields per item, plus one submission per item, plus the initial Start
    # click.
    interactions = len(items) * len(FORM_FIELDS) + len(items) + 1

    print(f'Browser: Chrome {browser_version(path_browser)}')
    print(f'Page interactions per run: {interactions}')

    # The benchmark's one_run() looks CONSTRUCTORS up by name; here the
    # variants are different ones, so the map is replaced in memory.
    compare_drivers.CONSTRUCTORS = VARIANTS

    measurements: dict[str, list[float]] = {name: [] for name in VARIANTS}

    print('\nWarm-up (discarded)...')
    for name in VARIANTS:
        one_run(name, items, path_browser)
        print(f'  {name}: ok')

    print(f'\nMeasuring {arguments.repetitions} runs per variant, interleaved...')
    for round_number in range(1, arguments.repetitions + 1):
        for name in VARIANTS:
            times = one_run(name, items, path_browser)
            measurements[name].append(times['fill'])
            print(f'  round {round_number} · {name:<32} fill={times["fill"]:5.2f}s')

    print('\n### Fill time per variant\n')
    print('| Variant | median fill (s) | vs. Selenium |')
    print('|---|---|---|')

    baseline = statistics.median(measurements['selenium'])
    for name, values in measurements.items():
        median = statistics.median(values)
        print(f'| {name} | {median:.2f} | {median / baseline:.2f}× |')


if __name__ == '__main__':
    main()
