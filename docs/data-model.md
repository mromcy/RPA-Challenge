# Data model

## `process_run` (schema `process_manager`)

One row per execution of the bot.

| Column | Type | Description |
|---|---|---|
| `run_id` | INT (PK) | Execution identifier |
| `process_name` | VARCHAR | Process name |
| `resource_name` | VARCHAR | Hostname of the machine that ran it |
| `scheduled_by` | VARCHAR | OS user that started it |
| `area` | VARCHAR | Owning area |
| `status` | ENUM | `SCHEDULED → RUNNING → COMPLETED / FAILED / CANCELED` |
| `started_at` / `ended_at` | TIMESTAMP | Start and end |
| `total_work_time` | INTERVAL | Duration |
| `error_message` | TEXT | Error message, when it failed |
| `error_stack` | TEXT | Full stack trace, when it failed |

## `item_run` (schema `rpa_challenge`)

One row per record, tracked individually — this is the queue.

| Column | Type | Description |
|---|---|---|
| `item_id` | INT (PK) | Item identifier |
| `run_id` | INT (FK) | Parent execution |
| `item_key` | VARCHAR | Business key for the item |
| `status` | ENUM | `QUEUED → PROCESSING → COMPLETED / FAILED` |
| `attempt` | INT | Attempt count |
| `created_at` / `started_at` / `completed_at` | TIMESTAMP | Lifecycle timestamps |
| `total_work_time` | INTERVAL | Processing time |
| `exception_reason` | VARCHAR | Why it failed |

## `item` (schema `rpa_challenge`)

The form data and the outcome.

| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Row identifier |
| `item_id` | INT (FK) | Reference to `item_run` |
| `First_Name` … `Phone_Number` | VARCHAR | The seven form fields |
| `result` | VARCHAR | Success rate reported by the site |

## Status transitions

```
process_run:  SCHEDULED → RUNNING → COMPLETED
                                  ↘ FAILED
                                  ↘ CANCELED

item_run:     QUEUED → PROCESSING → COMPLETED
                                  ↘ FAILED
```

---

---

[← Back to the README](../README.md)
