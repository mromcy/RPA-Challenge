"""
A measured comparison between the Playwright and Selenium drivers.

Run manually, outside CI and outside pytest:

    poetry run task benchmark
    poetry run python -m benchmarks.compare_drivers --repetitions 5

Method rules, all of them deliberate:

- **The same binary on both sides.** The script refuses to run without
  PATH_BROWSER filled: Playwright would drive its own Chromium and Selenium the
  system Chrome, and the measured difference would partly be browser against
  browser.
- **Warm-up discarded.** Each driver's first run pays for DNS, a cold disk
  cache and the first connection — the cost of debuting, not of running.
- **Interleaved measurements**, rather than blocks. If the network degrades
  mid-run, blocks would blame whoever ran later. Alternating spreads any
  environmental variation across both.
- **Median**, with minimum and maximum beside it. A mean lets an antivirus
  spike contaminate the result; a median does not.
- **A failure stops everything.** No run is silently repeated or replaced by
  another value — a benchmark that hides failures is advertising.
"""

from __future__ import annotations

import argparse
import ast
import io
import platform
import re
import statistics
import time
import tokenize
from datetime import date
from pathlib import Path

from resources.Drivers.playwright_driver import PlaywrightDriver
from resources.Drivers.selenium_driver import SeleniumDriver
from resources.Modules.challenge import FORM_FIELDS, Challenge
from resources.Schemas.item_run import Item
from resources.settings import get_settings
from resources.Utils.read_file import FileReader

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://rpachallenge.com/'

CONSTRUCTORS = {'playwright': PlaywrightDriver, 'selenium': SeleniumDriver}

DRIVER_FILES = {
    'playwright': ROOT / 'resources' / 'Drivers' / 'playwright_driver.py',
    'selenium': ROOT / 'resources' / 'Drivers' / 'selenium_driver.py',
}

SITE_TIME_PATTERN = re.compile(r'in (\d+) milliseconds')
SUCCESS_PATTERN = re.compile(r'(\d+)%')


class _NoLog:
    """
    A null logger.

    Challenge records one line per form; across 12 runs that would be hundreds
    of lines competing with the results table in the output.

    It plays the same role FakeDriver plays in the tests, with one difference
    the type checker charges for: `BrowserDriver` is a Protocol, and structural
    conformance is enough; `Logs` is a concrete class, and whoever receives one
    annotates the class. That is why the two calls below carry
    `type: ignore` — a recorded decision, not an oversight. Turning `Logs`
    into a Protocol would fix it properly, and that is a change to production
    annotations for the benefit of a measurement script.

    The comments say `type: ignore` rather than `pyright: ignore` because the
    checker that runs in CI is mypy, and mypy does not read pyright's form —
    the suppressions would have been silently doing nothing. Pyright honours
    `type: ignore` too, so the editor stays quiet as well.
    """

    def info(self, *_, **__) -> None: ...

    def warning(self, *_, **__) -> None: ...

    def error(self, *_, **__) -> None: ...


def browser_version(path: str) -> str:
    """
    Finds the version of the Chrome pointed at by PATH_BROWSER.

    It reads the name of the versioned sibling folder the Chrome installer
    creates (``Application/150.0.7871.187/``). It deliberately does **not** run
    ``chrome.exe --version``: on Windows that prints no version at all — it
    opens a browser window, which is an unacceptable side effect in a
    measurement script.
    """
    folder = Path(path).parent
    versions = [
        sub.name
        for sub in folder.iterdir()
        if sub.is_dir() and re.match(r'^\d+\.\d+', sub.name)
    ]

    return max(versions, default='unknown')


def load_items() -> list[Item]:
    """The records in input/, by the same path production walks."""
    data = FileReader(
        _NoLog(),  # type: ignore[arg-type]
        path_in=ROOT / 'input',
    ).read_file()

    return [
        Item(
            id=number,
            item_id=number,
            **{attribute: str(row[label]) for label, attribute in FORM_FIELDS.items()},
        )
        for number, (_, row) in enumerate(data.iterrows(), 1)
    ]


def one_run(name: str, items: list[Item], path_browser: str) -> dict[str, float]:
    """
    Runs the complete challenge once and returns the times, in seconds.

    Returns:
        dict: `total` timed by us, from zero to the result being read, and
            `fill` read from the site's own message — an independent
            measurement, immune to where we placed the stopwatch.

    Raises:
        RuntimeError: If the challenge does not close at 100%, or if the site
            does not report the time. A partial result is not a valid
            measurement.
    """
    driver = CONSTRUCTORS[name](headless=True, path_browser=path_browser)
    challenge = Challenge(
        driver,
        _NoLog(),  # type: ignore[arg-type]
    )

    try:
        start = time.perf_counter()

        challenge.start_challenge(URL)
        for item in items:
            challenge.fill_form(item)
        result = challenge.capture_result()

        total = time.perf_counter() - start
    finally:
        driver.close()

    success = SUCCESS_PATTERN.search(result)
    if not success or success.group(1) != '100':
        raise RuntimeError(f'{name}: the challenge did not close at 100% — {result!r}')

    elapsed = SITE_TIME_PATTERN.search(result)
    if not elapsed:
        raise RuntimeError(f'{name}: the site did not report the time — {result!r}')

    return {'total': total, 'fill': int(elapsed.group(1)) / 1000}


def measure_file(path: Path) -> dict[str, int]:
    """
    The size of a module in three counts.

    `stmts` are executable statements from the syntax tree and measure how much
    the program does. `effective` are physical lines without docstrings,
    comments and blank lines, and measure how much there is to read — the
    difference between the two shows up when one statement spans several lines.
    Raw `lines` are included only for transparency: they measure the author's
    documentation density, not the library's demands.
    """
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)

    ignored: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            ignored.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))

    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT and token.line.strip().startswith('#'):
            ignored.add(token.start[0])

    lines = text.splitlines()
    effective = [
        number
        for number, content in enumerate(lines, 1)
        if content.strip() and number not in ignored
    ]

    return {
        'lines': len(lines),
        'effective': len(effective),
        'stmts': sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.stmt)
            and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
        ),
        # Playwright's are counted as `.wait_for(` and not `wait_for(`: the
        # latter is a substring of Selenium's `self._wait_for(`, and the sum
        # below would count that side twice.
        'waits': text.count('.wait_for(') + text.count('self._wait_for('),
        'sleeps': text.count('time.sleep'),
    }


def _summary(values: list[float]) -> str:
    """Median with minimum and maximum in brackets, in seconds."""
    return f'**{statistics.median(values):.2f}** ({min(values):.2f}–{max(values):.2f})'


def print_results(
    measurements: dict[str, list[dict[str, float]]],
    repetitions: int,
    version: str,
) -> None:
    """Prints both tables in markdown, ready to paste into the README."""
    print('\n### Run time\n')
    print('| Driver | total (s) | fill (s) | rest (s) |')
    print('|---|---|---|---|')

    for name, runs in measurements.items():
        totals = [r['total'] for r in runs]
        fills = [r['fill'] for r in runs]
        rests = [r['total'] - r['fill'] for r in runs]
        print(f'| {name} | {_summary(totals)} | {_summary(fills)} | {_summary(rests)} |')

    print(
        '\nMedian of '
        f'{repetitions} runs, with minimum and maximum in brackets. '
        '`total` is timed here, end to end, including starting the browser. '
        '`fill` is reported by rpachallenge.com itself. `rest` is the '
        'subtraction of the two: starting the browser, clicking Start and '
        'reading the result — it is **not** only the startup, which is why it '
        'does not carry that name.'
    )

    print('\n### Code complexity\n')
    print('| Driver | statements | effective lines | explicit waits | time.sleep |')
    print('|---|---|---|---|---|')

    for name, path in DRIVER_FILES.items():
        m = measure_file(path)
        print(
            f'| {name} | {m["stmts"]} | {m["effective"]} | {m["waits"]} | {m["sleeps"]} |'
        )

    print(
        '\nOnly the driver modules are counted: `base.py` and `selectors.py` '
        'are shared and belong to neither side. `statements` ignores '
        'docstrings; `effective lines` discounts docstrings, comments and blank '
        'lines.'
    )

    print('\n### Methodology\n')
    print(f'- Machine: {platform.processor() or "unknown"}')
    print(f'- System: {platform.system()} {platform.release()}')
    print(f'- Python: {platform.python_version()}')
    print(f'- Browser: Chrome {version}, the same one for both drivers')
    print(f'- Measured runs: {repetitions} per driver, headless')
    print("- Each driver's first run discarded as warm-up")
    print('- Measurements interleaved between the drivers, not in blocks')
    print(f'- Date: {date.today().isoformat()}')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='compare_drivers',
        description='Measures Playwright against Selenium on the same flow.',
    )
    parser.add_argument(
        '--repetitions',
        type=int,
        default=5,
        help='Measured runs per driver, not counting the warm-up.',
    )
    arguments = parser.parse_args()

    path_browser = get_settings().PATH_BROWSER
    if not path_browser:
        raise SystemExit(
            'PATH_BROWSER is empty in config.json.\n'
            'The benchmark requires both drivers to drive the SAME executable: '
            'without it, Playwright would use the Chromium it manages and '
            'Selenium the system Chrome, and part of the measured difference '
            'would be browser against browser, not library against library.'
        )

    version = browser_version(path_browser)
    items = load_items()

    print(f'Browser: Chrome {version}')
    print(f'Records per run: {len(items)}')
    print('\nWarm-up (discarded)...')
    for name in CONSTRUCTORS:
        one_run(name, items, path_browser)
        print(f'  {name}: ok')

    measurements: dict[str, list[dict[str, float]]] = {name: [] for name in CONSTRUCTORS}

    print(f'\nMeasuring {arguments.repetitions} runs per driver, interleaved...')
    for round_number in range(1, arguments.repetitions + 1):
        for name in CONSTRUCTORS:
            times = one_run(name, items, path_browser)
            measurements[name].append(times)
            print(
                f'  round {round_number} · {name:<10} '
                f'total={times["total"]:6.2f}s  fill={times["fill"]:5.2f}s'
            )

    print_results(measurements, arguments.repetitions, version)


if __name__ == '__main__':
    main()
