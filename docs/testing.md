# Tests

Two lanes, separated by a pytest marker.

```bash
pytest -m "not e2e"     # fast lane: no database, no browser, no config.json
pytest -m e2e           # live lane: real browser against rpachallenge.com
```

With Poetry, `task test` runs the fast lane with coverage and `task e2e` runs
the live one.

| Lane | Tests | Needs | Time |
|---|---|---|---|
| unit | 95 | nothing | ~2 s |
| e2e | 2 | network + browser | ~20 s |

**Why they are separated.** The end-to-end tests depend on a system nobody here
controls: the site can go down, change its DOM, or simply be slow. Running them
on every push produces red builds for reasons unrelated to the code, and a team
that sees red often enough learns to answer it with "run it again" — including
the day the red is real. The live lane belongs on a schedule and on demand, not
on every commit.

**That separation is what `.github/workflows/ci.yml` implements.** The fast lane,
`mypy`, and a check that the exported `requirements*.txt` still match
`pyproject.toml` gate every push and pull request. The fast lane runs on 3.11 and 3.13, the ends
of the supported range, because compatibility breaks at the edges. The live lane runs Monday mornings and from
the Actions tab, never on a push, as two jobs — one per driver — so a failure
names the driver that broke without anyone opening a log.

**The type checker is what makes the `BrowserDriver` Protocol a contract.**
Structural conformance is checked statically or not at all, so `mypy` runs in CI
next to ruff. Turning it on paid for itself immediately. The project carried 20
suppression comments, and `warn_unused_ignores` proved that **11 of them
suppressed nothing**: they had been written for the editor's checker, which
ignores the error code in the brackets, so those codes had never been read by
anything. Two more were `# pyright: ignore`, which mypy does not read at all, and
were converted rather than deleted. In the other direction, the checker's first
run found two spots that genuinely needed suppressing and had none — SQLAlchemy
generates the mapped classes' `__init__` at runtime, and no checker sees it.

That is 20 − 11 + 2, which is where the eleven that remain come from. Each of
them now suppresses an error some tool actually reports.

**The fast lane needs no configuration at all.** No database, no `config.json`,
no browser. That is a property held on purpose, and two tests assert it by
checking that the settings cache was never touched. A `conftest.py` fixture
clears that cache around every test, so results never depend on execution order.

## What the coverage number means

The fast lane reports about **63%** of `resources`, and that figure is still
dominated by code it cannot reach by design. Of the 315 uncovered statements,
**218 sit in five modules that need a live PostgreSQL just to be imported** —
`operation_db`, `models`, `add_process_run`, `create_items` and `database`.
Another 66 are in the two browser drivers, which the live lane covers instead.
That leaves **31** statements genuinely uncovered and reachable. The code that
needs neither a database nor a browser sits at roughly **94%**.

> Every number here is measured the way CI runs the suite: **no `config.json`,
> no `secret/`, no database**. The condition matters — on a clone that does have
> a `config.json`, one more statement in `settings.py` gets covered and the
> totals read 314 and 30 instead. To reproduce exactly what this paragraph
> claims, run it somewhere none of those three exist, and with the
> `RPA_CHALLENGE_CONFIG` environment variable unset.

`execute.py` used to be the sixth name on that list, and the orchestrator having
no unit tests used to be recorded here as a known cost. It left the list when
the database became optional: the imports that open a connection now sit inside
a `try`, so the module loads on a machine with neither configuration nor
PostgreSQL. `tests/test_execute.py` then drove the whole `Execute` class from
the top — a spreadsheet on disk, a fake browser, no network — and took it from
0% to **96%**, the remainder being the import lines that can only run where a
database exists.

**Watch the two figures move in opposite directions on the way there.** Making
the database optional pushed the overall number **up** (48% → 53%) while pushing
"the code that needs neither a database nor a browser" **down** (~85% → ~78%):
ninety-two statements left the bucket that was excused from measurement and
entered the one that is measured, arriving untested. Writing the tests then
moved both up together (53% → 63%, ~78% → ~94%). One metric, two directions,
from a change that only ever improved the codebase — which is the whole argument
of the next paragraph.

The tests earned something the percentage does not show, too. Four behaviours in
`execute.py` existed only as prose: that the browser is closed even when the
challenge blows up, that a failure *while closing* must not replace the real
error, that a failure *while counting* must not mask the exception being
reported, and that the numbers sent to the orchestrator come from the item store
rather than from a counter in memory. Each was verified by breaking it on
purpose and confirming exactly one test objected.

The reason the remaining five need a database at import time is a deliberate
trade.
`models.py` **reflects** `process_manager.process_run` from the database instead
of declaring it here, because that table is shared with other automations and
provisioned outside this project — keeping a local copy of a shared schema's
definition is how drift between systems begins. The price is that the reflection
runs on import, and pulls a connection with it. Reversing the trade means
building the engine lazily and deferring the reflection, which changes how every
database session in the project is obtained: worth doing deliberately, not
casually. The optional-database fallback does not reverse it — it routes around
it, which is why those five modules are still unreachable here while the
orchestrator that used to import them is now covered like any other module.

There is deliberately **no `--cov-fail-under`**. A global percentage here moves
mostly when database-bound code is added or removed, not when tests are — adding
a correct new repository module would *lower* it and break the build. And it is
too coarse to catch what it would exist to catch: business logic added to
`challenge.py` without a test is four or five statements against a denominator of
850, half a percentage point that no sane threshold would trip on. Coverage is
read here as a report, not enforced as a gate.

**The end-to-end test is one test, parametrised over both drivers.** Same
assertions, two browser backends — which is what cross-browser testing is. It
builds the drivers directly rather than through the factory: going through the
factory would apply the configured `PATH_BROWSER`, and once that is set both
cases would collapse onto the same browser and the cross-browser coverage would
vanish with every test still green.

**One test guards the architecture.** It runs a subprocess that imports the
business flow and asserts that no browser module was loaded — the property that
makes the driver abstraction real rather than decorative. Adding
`from playwright.sync_api import Page` to `challenge.py` turns that test, and
only that test, red.

**A fake driver replaces the browser.** `tests/fake_driver.py` records the calls
it receives, which turns *"the bot filled all seven fields with the right
values"* into a dictionary assertion that runs in milliseconds. It neither
inherits from nor imports the protocol — structural conformance is what makes
that possible.

Every test here was validated by breaking the code it covers on purpose and
confirming it turns red. A test that cannot fail proves nothing — and a suite
that has never been seen failing is an assumption, not evidence.

---

---

[← Back to the README](../README.md)
