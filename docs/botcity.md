# BotCity Maestro integration

The bot runs identically with or without the orchestrator.

`BotMaestroSDK.from_sys_args()` inspects the command line: when the runner
started the process it finds the server, task id, token and organization there
and connects; otherwise it falls back to a local instance with `task_id = None`,
and every Maestro call is skipped.

Because those arguments are read **by position**, `--driver` is parsed and
removed from `sys.argv` before the SDK sees it — otherwise a flag written before
them would shift every position and the bot would try to reach a server named
`--driver`.

## Packaging for the runner

The runner extracts the package into a directory of its own — on Windows,
something like `…\BotCity\run\temp\` — so the package needs the code and
nothing else:

```
resources/  migrations/  bot.py  alembic.ini  requirements.txt
```

Configuration, credentials and input folders stay on the machine and are found
through `RPA_CHALLENGE_CONFIG`, which keeps secrets out of the distributed
artifact entirely. Set the variable once on the machine that hosts the runner
and every deployment after that carries only code.

## Choosing the driver from the panel

The driver is resolved in three layers, most specific first:

| Source | When it wins |
|---|---|
| `--driver` on the command line | Always, when present |
| `driver` task parameter in Maestro | When the task supplies one |
| `DRIVER` in `config.json` | Default for the machine |

So an operator can trigger the same registered automation with
`driver = selenium` as a task parameter and get the Selenium run — no redeploy,
no second automation, no editing a file on the robot. An unknown value fails
immediately, before the migrations run and before the execution is recorded, so
a typo in the panel leaves no half-finished run behind.

## What is reported

| Event | SDK call | When |
|---|---|---|
| Successful completion | `finish_task(SUCCESS)` | Run finished, no item failed |
| Completed with failures | `finish_task(PARTIALLY_COMPLETED)` | Queue finished, some items errored |
| Failed run | `finish_task(FAILED)` | The run did not reach the end |
| Error detail | `maestro.error()` | `logs.error()` called with an exception |

`finish_task` carries `total_items`, `processed_items` and `failed_items`, which
show up in the Maestro panel.

## No credentials to store

The bot authenticates with the execution token the runner hands it on the
command line, so **there is no BotCity API key anywhere in the configuration**
and nothing to rotate on the robot machine. A stored API key would only be
needed by a process that *calls* the orchestrator instead of being called by it
— an internal portal that creates tasks, a folder watcher, a CI pipeline — and
this bot is never in that position.

---

---

[← Back to the README](../README.md)
