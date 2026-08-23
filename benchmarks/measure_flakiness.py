"""
Measures the flakiness of the E2E suite on each driver.

A flaky test passes and fails **without the code changing**: the result stops
being a function of the code and starts depending on response time, rendering
and machine load. It is the worst class of defect because it does not reproduce
under investigation — and because the team learns to answer red with "run it
again", until the day the red is real.

In RPA the same cause produces an intermittent bot in production. A slow bot is
an annoyance you solve by scheduling it earlier; an intermittent bot consumes
one investigation a week and erodes the trust of everyone who depends on it.

The method is to run the **real E2E test**, one process per run, and count
non-zero exits. Reimplementing the flow here would measure something else.

**What this number does NOT prove**, and the report repeats it in the output:

1. Zero failures is not zero flakiness. By the rule of three, no occurrence in
   N attempts gives an upper bound of ~3/N with 95% confidence — with 10 runs,
   that is 30%. To claim "under 1%" would take ~300 runs.
2. This measures **the implementations**, not the libraries. A Selenium driver
   with time.sleep and absolute XPath would be scandalously flaky; ours has a
   WebDriverWait on every interaction on purpose. Zero on both sides is the
   **desired** result: it confirms the robustness is comparable and that the
   difference measured by the benchmark is one of speed, not of reliability.

    poetry run python -m benchmarks.measure_flakiness --repetitions 10
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DRIVERS = ('playwright', 'selenium')
TEST_NODE = (
    'tests/test_e2e_challenge.py::test_full_challenge_with_a_perfect_score[{driver}]'
)


def one_round(driver: str) -> tuple[bool, str]:
    """
    Runs that driver's E2E test in a clean process.

    Returns:
        tuple[bool, str]: Whether it passed, and pytest's output for diagnosis.
    """
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            TEST_NODE.format(driver=driver),
            '-q',
            '--no-header',
            '-p',
            'no:cacheprovider',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0, result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='measure_flakiness',
        description='Counts E2E suite failures across repeated runs.',
    )
    parser.add_argument('--repetitions', type=int, default=10)
    arguments = parser.parse_args()

    failures: dict[str, list[str]] = {driver: [] for driver in DRIVERS}

    print(f'Running the E2E suite {arguments.repetitions}× per driver.\n')

    for round_number in range(1, arguments.repetitions + 1):
        for driver in DRIVERS:
            passed, output = one_round(driver)
            if not passed:
                failures[driver].append(output)
            print(
                f'  round {round_number:>2} · {driver:<10} {"ok" if passed else "FAILED"}'
            )

    print('\n### Flakiness\n')
    print('| Driver | runs | failures | observed rate |')
    print('|---|---|---|---|')

    for driver in DRIVERS:
        amount = len(failures[driver])
        rate = amount / arguments.repetitions
        print(f'| {driver} | {arguments.repetitions} | {amount} | {rate:.0%} |')

    # The rule of three is an approximation; below ~3 runs it would return a
    # bound greater than 100%, which means nothing.
    bound = min(3 / arguments.repetitions, 1.0)
    print(
        f'\nZero failures in {arguments.repetitions} runs does **not** mean zero '
        f'flakiness: by the rule of three, the upper bound with 95% confidence is '
        f'roughly {bound:.0%}. This measurement detects gross problems; it does not '
        "certify reliability. It also measures this repository's implementations, "
        'not the libraries in general.'
    )

    for driver, outputs in failures.items():
        for number, output in enumerate(outputs, 1):
            print(f'\n--- failure {number} on {driver} ---')
            print(output.strip()[-1500:])


if __name__ == '__main__':
    main()
