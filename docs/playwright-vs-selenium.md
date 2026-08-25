# Playwright vs Selenium

Both drivers implement the same `BrowserDriver` protocol and are called by the
same business code. They share the selector strings, the timeout constant and,
for these measurements, the same Chrome binary. What differs between the two
columns below is the library, and — as far as this setup can isolate it —
nothing else.

Each driver is written in **its own documented style**: `WebDriverWait` with
`expected_conditions` on one side, auto-waiting locators on the other. Neither
is hand-tuned beyond what its documentation teaches, because the question worth
answering is not which library can be fastest in expert hands, but what a
competent developer following normal usage actually gets.

## Speed

Median of 5 runs, min–max in parentheses, warm-up discarded.

| Driver | total (s) | fill (s) | rest (s) |
|---|---|---|---|
| **Playwright** | **4.53** (4.47–4.88) | **0.78** (0.76–0.79) | **3.76** (3.67–4.11) |
| **Selenium** | 8.22 (8.03–8.71) | 4.19 (4.18–4.24) | 3.98 (3.85–4.52) |

`total` is measured here, end to end, and includes launching the browser.
`fill` is reported by rpachallenge.com itself — an independent measurement,
immune to where our stopwatch sits. `rest` is the subtraction, and it is
deliberately **not** called *startup*: it also contains the Start click and the
final read.

> Subtracting the two medians gives 4.03 s for Selenium, where the table shows
> 3.98 s. That is not an error: `rest` is subtracted **per run** and the median
> taken of those five differences, and the median of differences is not the
> difference of medians. Each column is the median of what it measures.
>
> The raw output of the run these medians come from — every individual round,
> the machine, the Chrome build — is committed at
> [`benchmarks/results/2026-08-25.md`](../benchmarks/results/2026-08-25.md).

**The interesting number is `rest`, and it is interesting for not saying
much.** The medians are 3.76 s and 3.98 s, but the ranges behind them are
3.67–4.11 and 3.85–4.52: a quarter of a second of shared ground, which is more
than the 0.22 s that separates the medians. Five runs cannot tell these two
apart outside the form, and reporting the ordering as a result would be reading
a coin toss.

What the run does settle is where the difference lives. Of the 3.69 s total gap,
**3.41 s happens during the fill phase** — 92% of it, while the seven fields are
being typed. The common assumption that Playwright wins by starting the browser
faster does not hold here: whatever it wins, it wins at the keyboard.

## Complexity

Only the driver modules count: `base.py` and `selectors.py` are shared and
belong to neither side.

| Driver | statements | effective lines | explicit waits | `time.sleep` |
|---|---|---|---|---|
| **Playwright** | **47** | **55** | **1** | 0 |
| **Selenium** | 55 | 69 | 4 | 0 |

`statements` counts executable statements from the syntax tree and ignores
docstrings — it measures how much the program *does*. `effective lines` drops
docstrings, comments and blank lines — it measures how much you *read*. The two
differ because a single Selenium call spans more physical lines.

The waits column tells the story better than either size metric. Playwright
needs one explicit wait in the whole driver, because its actions already wait;
Selenium has to declare a wait at every interaction, and each of those is a
place where forgetting produces a flaky test.

## Reliability

The full end-to-end suite, run ten times per driver, one process each:

| Driver | runs | failures |
|---|---|---|
| Playwright | 10 | **0** |
| Selenium | 10 | **0** |

This is the result the comparison needs. It turns *"both drivers are equally
robust"* from an assertion into a measurement, which is what allows the timing
difference to be attributed to speed rather than reliability. It was measured on
the same machine, on the same day as the timings, and the raw output is in
[`benchmarks/results/2026-08-25.md`](../benchmarks/results/2026-08-25.md).

## Where the difference comes from

A number without a mechanism is a blog post. `benchmarks/mechanism_experiment.py`
isolates one variable at a time by subclassing the production driver. The table
below is from the 3 August run, on Chrome 150 — read the ratios, not the
absolute seconds, and see the note underneath it for why:

| Variant | fill (s) | vs. Selenium |
|---|---|---|
| Playwright | 0.82 | 0.15× |
| Selenium | 5.53 | 1.00× |
| Selenium without any explicit wait | 4.66 | 0.84× |
| …and without the `clear()` before `send_keys` | 3.56 | 0.64× |

Removing **every** explicit wait recovers only 16%. Removing a single command
per field — the `clear()`, 70 calls per run — recovers another 20%, which puts
the cost at roughly **15.7 ms per command exchanged with the browser**.

Reading the Selenium source explains the rest: `element_to_be_clickable` is not
one question but three. It locates the element, asks whether it is displayed,
then asks whether it is enabled — each an HTTP round trip to `chromedriver`.
WebDriverWait is not slow because it waits; it is slow because it asks three
times.

Playwright runs the same checks, and more, **inside the browser**, and sends one
command over a persistent connection. It is not that one waits smarter — one
asks where the DOM is.

Note that even the stripped Selenium variant, which is *not* safe for production
because it reintroduces races, is still 4.3× slower than Playwright. That
residue is the protocol.

**Three weeks later the mechanism made a prediction, and kept it.** The timings
above were re-measured on 25 August, twenty-two days after the first run, on the
same machine and the same operating system, with `selenium` still at 4.46.0 and
`playwright` still at 1.59.0. One thing had changed: Chrome had gone from 150 to
151, taking the matching `chromedriver` with it. Playwright came back within
1.3% of its old numbers. Selenium's fill time fell **23%**. A new `chromedriver`
made the round trips cheaper, and only the driver that pays for round trips
noticed — which is what this section claims the difference is made of.

That is also why the isolation table above has not been re-run: its absolute
seconds belong to Chrome 150, and the ratios between its variants are what the
argument rests on. Re-measuring it would move all four rows together and change
nothing about which variable costs what.

## Methodology

- Machine: AMD64, Windows 11, Python 3.13.5
- Browser: Chrome 151.0.7922.174 for the timings and the flakiness runs;
  Chrome 150.0.7871.187 for the isolation table, which was measured earlier and
  is deliberately not re-run — see above
- 5 measured runs per driver, headless, first run of each discarded as warm-up
- Runs interleaved between drivers, not executed in blocks, so that any drift in
  network or machine load is spread across both
- Median reported, never the mean: one antivirus spike ruins a mean
- A failed run aborts the benchmark instead of being silently retried
- Flakiness measured separately: 10 runs of the real end-to-end suite per driver
- Date: 2026-08-25 for the timings and flakiness; 2026-08-03 for the isolation table

## Limitations

Stated plainly, because the number is only worth what its limits are:

- **This is not a general benchmark of the two libraries.** It measures one flow,
  on one site, on one machine, on a home network. A different page — heavier
  DOM, more navigation, fewer form fields — would shift the balance.
- **The gap scales with the number of interactions, not with time.** This flow
  performs 81 interactions per run. A flow dominated by page loads rather than
  field entry would show a much smaller difference.
- **Wait parity is approximate.** Selenium's `element_to_be_clickable` covers
  *present*, *visible* and *enabled*, but not *stable* (not animating) and not
  *unobstructed* (nothing intercepting the click) — two checks Playwright makes
  before every action. Reproducing them would require custom conditions. See the
  `_wait_for` docstring in `selenium_driver.py`.
- **Zero failures out of ten is not zero flakiness.** By the rule of three, no
  occurrences in N trials bounds the rate at roughly 3/N with 95% confidence —
  with ten runs, that is 30%. Claiming under 1% would take some three hundred
  runs.
- **Reliability here measures these implementations, not the libraries.** A
  Selenium driver written with `time.sleep` and absolute XPath would fail
  repeatedly. What separates them is the usage.

## What this means in practice

For this kind of flow — many small interactions with form fields — the cost that
matters is per-command round-trip, and it compounds with every field. A bot
filling seventy fields pays it seventy times. If you are choosing a library for
interaction-heavy automation, that is the number to look at, and it favours
Playwright by a wide margin.

The corollary matters just as much: if your automation is dominated by page
loads, downloads or waiting on a backend, most of this difference disappears,
because browser startup and navigation cost roughly the same on both. Choosing
on "Playwright is faster" without knowing which half of your runtime dominates
is choosing on a slogan.

And speed is not the only axis. Selenium's ecosystem, Grid support and the sheer
volume of existing code are real arguments that this benchmark does not measure.

## Reproducing it

```bash
poetry run task benchmark                              # timing, N=5
poetry run python -m benchmarks.mechanism_experiment  # where the time goes
poetry run python -m benchmarks.measure_flakiness     # reliability
```

The benchmark refuses to run unless `PATH_BROWSER` is set, because otherwise
Playwright would drive its own Chromium and Selenium the system Chrome, and part
of any measured difference would be browser against browser.

The numbers published above are not asked to be taken on trust:
[`benchmarks/results/`](../benchmarks/results/) holds the raw output of the run
they came from, with every individual round, the machine, the operating system,
the Python version and the Chrome build. Re-running on different hardware will
give different numbers — that is the point of writing down which hardware.

---

---

[← Back to the README](../README.md)
