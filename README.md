# RPA Challenge — production-style bot with two browser drivers

[![CI](https://github.com/mromcy/RPA-Challenge/actions/workflows/ci.yml/badge.svg?branch=main&event=push)](https://github.com/mromcy/RPA-Challenge/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11--3.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
<!-- The badge is filtered to event=push on purpose. Unfiltered, it would show
     the last run of the whole workflow, and that includes the Monday schedule
     with the live lane against rpachallenge.com - so a badge could go red
     because someone else's site was down, which is the exact confusion this
     project separated the two lanes to avoid. -->


A Python RPA bot that solves the [RPA Challenge](https://rpachallenge.com/): it
reads records from an Excel file, tracks every item through a queue in
PostgreSQL, and fills the form in a real browser. The database is **optional** —
clone it, and it runs without one. It is built the way a
production robot is built — state machine, audit trail, encrypted credentials,
orchestrator integration — and it drives the browser through **two
interchangeable implementations, Playwright and Selenium**, so the two can be
compared on the same flow with the same code.

![The bot filling the RPA Challenge form with Selenium while the PostgreSQL queue moves from QUEUED to PROCESSING to COMPLETED](assets/demo.gif)

---

## Results at a glance

Both drivers run the *same* business code behind a `BrowserDriver` protocol,
against the same Chrome build, on the same machine. Median of 5 runs.

| | Playwright | Selenium | |
|---|---|---|---|
| End-to-end time | **4.53 s** | 8.22 s | 1.8× |
| Form filling only | **0.78 s** | 4.19 s | 5.4× |
| Explicit waits in the driver | **1** | 4 | |
| Failures in 10 end-to-end runs | **0** | **0** | |

The interesting number is the one that barely moves. Everything *except*
filling — launching the browser, navigating, reading the result — takes 3.76 s
against 3.98 s, and those two figures overlap once you look at the spread. The
gap is the form: 3.41 s of the 3.69 s total difference happens while the seven
fields are being typed. With zero failures on both sides, what separates the
drivers is speed, not reliability.

**The mechanism, and the accident that confirmed it.** Selenium's cost is HTTP
round trips to `chromedriver`: `element_to_be_clickable` is not one question but
three, at roughly 15.7 ms each, while Playwright asks the same questions inside
the browser over one persistent connection. Twenty-two days after the first
measurement the benchmark was re-run on the same machine, both libraries pinned
to the same versions. One thing had changed — Chrome 150 to 151, and the
`chromedriver` that ships with it. Playwright came back within **1.3%**;
Selenium's fill time fell **23%**. Only the driver that pays for round trips
noticed, which is what the mechanism predicted.

→ **[The full comparison](docs/playwright-vs-selenium.md)** — speed, complexity,
flakiness, the isolation experiment, limitations and how to reproduce it. Raw
output of every run is in [`benchmarks/results/`](benchmarks/results/).

---

## The challenge

The [RPA Challenge](https://rpachallenge.com/) asks a bot to:

1. Read a spreadsheet of people
2. Open the site and click **Start**
3. Fill a seven-field form for each record and submit it
4. Repeat for all records — **the fields move position on every round**
5. Read the success rate the site reports at the end

Step 4 is the trap. Any selector based on position fills the wrong box, so every
field has to be located by its visible label.

---

## Design rationale

Solving the challenge takes about forty lines of code. This repository is not
forty lines, and that is deliberate: it is built to demonstrate the patterns a
**production** RPA process needs, on a problem small enough to read in one
sitting.

**A queue with per-item state, not a loop.** Each record becomes a row that moves
`QUEUED → PROCESSING → COMPLETED | FAILED`, with timestamps and a failure reason.
Ten records do not need this. Five thousand invoices do: when the run dies at
item 3,200, someone has to answer *which ones went through, which failed, and
why* — without re-running the successful ones.

**PostgreSQL and Alembic, not a log file.** The audit trail outlives the process,
survives the machine, and can be queried by people who do not have access to the
robot. Migrations version the schema so a change is applied the same way
everywhere instead of by hand.

**Fernet-encrypted credentials.** Robots run unattended, often on shared machines
someone else administers. Database credentials in a plain config file are a
credential leak with extra steps.

**Orchestrator integration.** [BotCity Maestro](https://botcity.dev) schedules
the run, receives the outcome and item counts, and shows failures where the
operations team already looks. The bot runs identically without it.

**A driver abstraction — because there are two implementations, not because
there might be one.** The business flow talks to a `BrowserDriver` protocol and
never imports Playwright or Selenium; a test asserts that in a subprocess. That
inversion is what makes the comparison in this README possible at all, and what
lets the whole flow be tested with no browser.

None of this is accidental over-engineering. For a ten-row spreadsheet a script
would do — and the fastest way to see the difference is to compare
`resources/Modules/challenge.py`, which holds the business flow and nothing
else, against everything around it that exists to make the run **observable,
resumable and reproducible**.

---

## How it works

```
Excel (input/) → PostgreSQL queue → Browser driver → Result
      │                   │                  │              │
   read and           per-item state     fill the form   success rate
   clean rows         and audit trail    by label        stored per item
      │                    │
      │              BotCity Maestro
      │           (scheduling, monitoring,
      │              outcome reporting)
      │
      └──────────────────────────────→ (no database: the queue step is
                                         skipped and the items go straight
                                         from the spreadsheet to the driver)
```

Both middle boxes are optional and detected at startup: no BotCity, no
reporting; no PostgreSQL, no queue. The form still gets filled either way.
See [Running without a database](#running-without-a-database).

---

## Architecture

```
rpa_challenge/
├── bot.py                          # Entry point: wiring only, no logic
├── config.json                     # Local configuration (never committed)
├── config.example.json             # Template to copy
├── alembic.ini                     # Alembic configuration
├── input/                          # Input .xlsx files
├── output/                         # Output files
├── logs/  downloads/  secret/      # Created on first run
│   └── db_credentials/
│       ├── credentials.json        # Fernet-encrypted user and password
│       └── secret.key              # Fernet key
├── migrations/versions/            # Alembic migration history
├── assets/                         # The demo GIF this README opens with
├── docs/                           # The long-form analysis this README links to
├── benchmarks/
│   ├── compare_drivers.py          # The measured comparison
│   ├── mechanism_experiment.py     # Isolates *why* one driver is slower
│   ├── measure_flakiness.py        # Counts flaky runs per driver
│   └── results/                    # Raw output of the published runs
├── tests/
│   ├── conftest.py                 # Shared fixtures; isolates settings cache
│   ├── fake_driver.py              # Records calls; no browser involved
│   ├── test_challenge.py           # Business flow, incl. architecture guard
│   ├── test_execute.py             # The orchestrator, end to end, no browser
│   ├── test_no_database.py         # The run with no PostgreSQL at all
│   ├── test_execute_challenge.py   # The per-item queue loop
│   ├── test_failure_report.py      # What reaches the Maestro panel
│   ├── test_cli.py  test_cryptography.py  test_read_file.py
│   ├── test_factory.py  test_settings.py  test_environment.py
│   └── test_e2e_challenge.py       # Live site, both drivers (marker: e2e)
└── resources/
    ├── settings.py                 # Config via Pydantic + Fernet credentials
    ├── cli.py                      # Command-line parsing, kept out of bot.py
    ├── database.py                 # SQLAlchemy engine and session
    ├── models.py                   # ORM models (reflects process_run)
    ├── execute.py                  # Orchestrator, incl. BotCity integration
    ├── Drivers/
    │   ├── base.py                 # BrowserDriver protocol + shared timeout
    │   ├── selectors.py            # Selectors, shared by both drivers
    │   ├── playwright_driver.py    # Implementation 1
    │   ├── selenium_driver.py      # Implementation 2
    │   └── factory.py              # Builds the requested driver
    ├── Executors/execute_challenge.py
    ├── Modules/challenge.py        # Business flow — knows no browser library
    ├── Schemas/                    # Pydantic models + the status enums,
    │                                #   which import with no database
    ├── Tools/                      # Logging, BotCity, process_run creation
    └── Utils/                      # Excel reading, item creation, DB operations
```

---

## Requirements

- **Python** 3.11, 3.12 or 3.13 — a range with both ends measured, not assumed.
  The floor is what the dependencies declare: of the sixty installed packages,
  numpy and pandas are the strictest and both require `>=3.11`. The ceiling has a
  name: `psycopg-binary` publishes one wheel per interpreter version and the
  pinned 3.2.9 stops at cp313, so 3.14 would fall back to building from source
  and need libpq and a C compiler. CI runs both ends. Outside the range the bot
  refuses to start and says why, because `pip` would install nothing and still
  report success
- **Google Chrome** — needed by the Selenium driver; the Playwright driver ships
  its own Chromium
- **Git**
- **PostgreSQL** 13+ is optional: with one, every item is tracked through the
  queue; without one, the items are read straight from the spreadsheet. See
  [Running without a database](#running-without-a-database)
- A **BotCity Maestro** account is optional: the bot runs identically without one

---

## Installation

### 1. Clone

```bash
git clone https://github.com/mromcy/RPA-Challenge.git
cd RPA-Challenge
```

### 2. Install dependencies

Poetry *develops* this project. It is **not** required to run it.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows (PowerShell)
source .venv/bin/activate      # Linux/macOS

pip install -r requirements.txt       # to run the bot; what the BotCity runner installs
pip install -r requirements-dev.txt   # to develop; adds pytest, ruff, mypy, taskipy
```

Install one or the other, never both — the dev file already contains everything
in the other. Both are **generated** from `pyproject.toml` by `task export` and
`task export-dev`, so dependencies go there and not in the `.txt` files. Those
tasks need `poetry self add poetry-plugin-export` once; CI re-exports both and
fails the build if either drifted, which is what stops them falling behind
quietly.

### 3. Install the browser Playwright manages

```bash
playwright install chromium
```

Skip this if you only ever run `--driver selenium`, which drives the Chrome
already installed on the machine.

---

## Configuration

Copy the template and fill it in:

```bash
cp config.example.json config.json          # Windows: copy config.example.json config.json
```

`config.json` holds real credentials, is git-ignored, and must never be
committed.

| Field | Required | Description |
|---|---|---|
| `PROJECT_NAME` | yes | Process identifier in the database and in BotCity |
| `AREA` | yes | Owning area, recorded with every run |
| `PATH_URL` | yes | Target site |
| `HOST_DB_POSTGRES` | yes | PostgreSQL host |
| `PORT_DB_POSTGRES` | yes | PostgreSQL port (usually 5432) |
| `DB_NAME_POSTGRES` | yes | Database name |
| `DB_SCHEMA` | yes | Schema used by this project |
| `DRIVER` | no | `playwright` (default) or `selenium` |
| `PATH_BROWSER` | no | Browser executable, honoured by **both** drivers |
| `PATH_SELENIUM_DRIVER` | no | `chromedriver` executable, Selenium only |
| `PATH_BASE` | no | Repository root; derived automatically |
| `PATH_IN` | no | Input folder; defaults to `<repo>/input` |
| `PATH_OUT` | no | Output folder; defaults to `<repo>/output` |

There is no BotCity credential here: the bot authenticates with the run token
the orchestrator hands it on the command line, so no long-lived secret sits at
rest on the machine.

**The defaults are deliberate.** `PATH_BASE`, `PATH_IN` and `PATH_OUT` derive
from the repository root, so a fresh clone runs without configuring a single
path — they stay configurable because production folders are usually network
shares. `PATH_BROWSER` empty lets each library use the browser it manages;
filling it points **both** at one executable, which the benchmark requires and
which matches the corporate habit of pinning an approved version.
`PATH_SELENIUM_DRIVER` empty lets Selenium Manager fetch the matching
`chromedriver`, and only needs a value on a machine with no internet access.

`logs/`, `downloads/` and `secret/` are created on first use.

### Where the configuration lives, and the credentials

`config.json` is looked for beside the code, or wherever `RPA_CHALLENGE_CONFIG`
points — which is what lets an orchestrator run the bot from a temporary folder.
Database credentials are never stored in it: they live encrypted with Fernet
under `secret/`, which `.gitignore` keeps out of the repository.

→ **[The environment variable, and how to create the encrypted credentials](docs/configuration.md)**

## Database and migrations

```sql
CREATE DATABASE <database_name>;
\c <database_name>
CREATE SCHEMA IF NOT EXISTS rpa_challenge;
CREATE SCHEMA IF NOT EXISTS process_manager;
```

```bash
alembic upgrade head
```

That creates `rpa_challenge.item_run` (the queue) and `rpa_challenge.item` (form
data and result); `process_manager.process_run` is provisioned outside this
project, because it is shared with other automations.

> `bot.py` applies the migrations itself before starting, and skips them when
> there is no database — so this section is only for setting one up by hand.

### Running without a database

The whole section above is optional. `git clone`, `pip install -r
requirements.txt`, `cp config.example.json config.json`, and the bot runs — no
PostgreSQL, no `process_manager` schema, no encrypted credentials.

Copying the template unchanged is enough: the four `*_POSTGRES` keys stay
required by the settings schema and the template already fills them, so they are
validated and then simply never used. Leaving them pointing at a database that
does not exist is exactly the case this section describes.

The decision is made once, on import, and it is made by trying: the modules that
talk to the database open their connection while *being imported*, so the check
has to wrap the import rather than the call. Three failures mean the same thing
and are named explicitly — a missing `secret/` folder (what a fresh clone looks
like, since `.gitignore` keeps credentials out of the repository), a server that
does not answer, and a server that answers but was never provisioned with
`process_manager`. Anything else propagates, because a typo inside
`operation_db` reported as "no database available" would send whoever
investigates to the wrong place entirely.

| | With a database | Without one |
|---|---|---|
| Items come from | `rpa_challenge.item_run`, after being written there | the spreadsheet, directly |
| Run record | one row in `process_manager.process_run` | none |
| Per-item audit trail | timestamps, attempt count, failure reason | none |
| Survives a crash | yes — the queue holds what was done | no |
| Final counts | read back from the queue | tallied in memory |
| Form gets filled | yes | yes |

The last two rows are the point. The processing loop is the *same code* either
way — it always took the item store as a parameter, and it never asks which one
it received. What changes is what outlives the run.

**The fallback announces itself as a `WARNING`, not as an `info`.** The person
this protects is not the reviewer who cloned the repository and knows perfectly
well they have no database. It is the machine that was supposed to have one and
lost it — a rotated password, a server that did not come back after a reboot.
That run would otherwise look like a complete success while persisting nothing,
and silent degradation is worse than the failure it replaced.

---

## Input file

Drop one or more `.xlsx` files into `input/`, with exactly these columns:

| Column |
|---|
| `First Name` |
| `Last Name` |
| `Company Name` |
| `Role in Company` |
| `Address` |
| `Email` |
| `Phone Number` |

Every `.xlsx` in the folder is read and concatenated, **oldest file first** by
modification time, so a batch left over from a previous day is processed before
today's. Column names are stripped of stray whitespace, and fully empty rows and
columns are dropped.

---

## Running

```bash
python bot.py                      # uses DRIVER from config.json
python bot.py --driver selenium    # overrides it for this run
python bot.py --driver playwright
python bot.py --help
```

`--help` works on a fresh clone, before any configuration exists.

Locally, the bot detects that no orchestrator started it and prints:

```
Running in local mode (no task_id).
```

Everything else runs normally; nothing is reported to Maestro.

### Through BotCity Maestro

Register the bot in the Maestro panel, deploy it, and trigger the task. The
runner appends its own arguments to the command line, which
`BotMaestroSDK.from_sys_args()` reads **positionally**. `--driver` is parsed and
removed from `sys.argv` before the SDK sees it, so the two coexist regardless of
the order they are written in. On completion the bot reports the outcome with
total, processed and failed counts.

---

## Tests

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

The end-to-end tests reach a site nobody here controls, so they never gate a
push: red builds for reasons unrelated to the code teach a team to answer red
with "run it again" — including the day the red is real. The fast lane, `mypy`
and a check that the exported `requirements*.txt` still match `pyproject.toml`
gate every push; the live lane runs Monday mornings and on demand.

**The fast lane needs no configuration at all.** No database, no `config.json`,
no browser — a property two tests assert by checking that the settings cache was
never touched.

→ **[How the suite is built, and what its coverage number means](docs/testing.md)**
— the fake driver, the architecture guard, why there is no `--cov-fail-under`,
and what the type checker found when it was switched on.

## Execution flow

```
Excel → run record → queue → browser → result
```

Read the spreadsheet, write one row per record, process the queue one item at a
time updating its state as it goes, then close the run. Both the run record and
the queue are skipped when there is no database.

→ **[Step by step, with what each layer does](docs/execution-flow.md)** and the
**[data model](docs/data-model.md)** behind it.

## BotCity Maestro

The bot runs identically with or without the orchestrator: with fewer than four
command-line arguments the SDK returns a local instance and no call to Maestro
has any effect. Connected, it reports the outcome with total, processed and
failed counts, and distinguishes a run that finished with some items failing
from one that never finished.

→ **[Packaging, driver selection from the panel, and what gets reported](docs/botcity.md)**

## Data model

Three tables: `process_manager.process_run` (one row per execution, shared with
other automations and provisioned outside this project), `rpa_challenge.item_run`
(one row per record — this is the queue) and `rpa_challenge.item` (the form data
and the result).

→ **[Columns, status transitions and how they relate](docs/data-model.md)**

## Logs

Written to three destinations at once:

| Destination | Location | Notes |
|---|---|---|
| Console | terminal | `TIMESTAMP - LOGGER - [LEVEL] - message` |
| File | `logs/app<YYYY-MM-DD>.log` | One file per day |
| BotCity | Maestro panel → Executions | Errors reported via `maestro.error()` |

Sample output:

```
2026-05-11 10:30:00 - RPA - [INFO] - Run recorded in the database with run_id=42 (SCHEDULED)
2026-05-11 10:30:01 - RPA - [INFO] - 10 items persisted to the database (QUEUED).
2026-05-11 10:30:02 - RPA - [INFO] - 10 items loaded from the database for processing.
2026-05-11 10:30:03 - RPA - [INFO] - Navigating to the RPA Challenge with the playwright driver.
2026-05-11 10:30:15 - RPA - [INFO] - Filling form 1/10.
2026-05-11 10:31:00 - RPA - [INFO] - Run completed successfully.
```

---

## Built with

| Tool | Constraint | Role |
|---|---|---|
| [Python](https://python.org) | >=3.11,<3.14 | Language |
| [Playwright](https://playwright.dev/python/) | >=1.58 | Browser driver 1 |
| [Selenium](https://selenium.dev) | >=4.46 | Browser driver 2 |
| [SQLAlchemy](https://sqlalchemy.org) | >=2.0.51 | ORM and database access |
| [Alembic](https://alembic.sqlalchemy.org) | >=1.17 | Schema migrations |
| [psycopg](https://www.psycopg.org/) | 3.2.9 | PostgreSQL driver |
| [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | >=2.11 | Configuration loading and validation |
| [pandas](https://pandas.pydata.org) | >=3.0.1 | Excel reading and cleaning |
| [openpyxl](https://openpyxl.readthedocs.io) | >=3.1.5 | `.xlsx` support |
| [cryptography](https://cryptography.io) | >=46.0.2 | Fernet credential encryption |
| [BotCity Maestro SDK](https://botcity.dev) | >=0.9 | Orchestrator integration |
| [pytest](https://docs.pytest.org) | >=9.0 | Test runner *(dev)* |
| [Ruff](https://docs.astral.sh/ruff/) | >=0.15 | Linting and formatting *(dev)* |
| [mypy](https://mypy-lang.org) | >=2.3 | Static type checking, in CI *(dev)* |
| [Poetry](https://python-poetry.org) | — | Dependency management *(dev)* |

---

## License

[MIT](LICENSE) © Marco Romcy
