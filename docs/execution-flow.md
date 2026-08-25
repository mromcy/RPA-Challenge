# Execution flow in detail

```
bot.py
  ├── parse --driver and remove it from sys.argv
  ├── alembic upgrade head                     (only when there is a database)
  └── Execute(driver).execute()
        │
        ├── 1. BotMaestroSDK.from_sys_args()
        │      Reads the orchestrator arguments positionally.
        │      Fewer than four means local mode: task_id = None
        │
        ├── 2. AddProcessRun().execute()                      [database only]
        │      Inserts process_run with status SCHEDULED, returns run_id.
        │      With no database, run_id is 0 and a WARNING is logged
        │
        ├── 3. update_process_run_status(RUNNING)
        │
        ├── 4. read_data(logs) → FileReader(...).read_file()
        │      Reads every .xlsx in input/, oldest first,
        │      applies clean_dataframe and concatenates
        │
        ├── 5. create_items(df, run_id)                       [database only]
        │      For each row: ORMItemRun (QUEUED) + ORMItem with the form data
        │
        ├── 6. get_queued_items_by_run(run_id)                [database only]
        │      Steps 5 and 6 are the round trip through the queue. With no
        │      database, items_from_dataframe(df) builds the same objects
        │      straight from the spreadsheet and steps 5-6 do not happen
        │
        ├── 7. create_driver(...) → run_challenge(driver, logs, items, url, db)
        │      Launches the browser through the selected driver
        │      Opens the site and clicks Start
        │      For each item:
        │        ├── update_item_run_status(PROCESSING)
        │        ├── fills the seven fields, located by label
        │        ├── submits
        │        └── update_item_run_status(COMPLETED | FAILED)
        │      Reads the final success rate and stores it per item
        │      Returns that text. Deliberately **not** the counts:
        │      those are read back from the item store, which keeps
        │      being right when a failure interrupts the loop
        │
        ├── 8. driver.close() in a finally block
        │      A cleanup failure is logged as a warning, never allowed to
        │      mask the original error
        │
        ├── 9. update_process_run_status(COMPLETED)
        │
        └── 10. maestro.finish_task(SUCCESS, total, processed, failed)
                Only when a task_id is present.
                On any exception: finish_task(FAILED) + process_run(FAILED)
                with the message and the full stack trace stored in the database
```

---

---

[← Back to the README](../README.md)
