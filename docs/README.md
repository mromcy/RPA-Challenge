# Documentation assets

## `demo.gif` — pending recording

The README embeds `docs/demo.gif` at the top. Until it exists, the image simply
does not render; nothing else breaks.

**What it must show** — two things, not one:

1. The browser filling the form on rpachallenge.com.
2. The database rows moving from `QUEUED` to `PROCESSING` to `COMPLETED`.

The second half is the point. Plenty of repositories show a form being filled;
showing the queue and the state machine is what makes the architecture visible
instead of merely claimed.

**Constraints**

- Under ~5 MB. The file enters git history permanently and everyone who clones
  downloads it. GIF compresses poorly, so an unedited recording easily exceeds
  20 MB.
- 10–15 seconds is enough.

**Suggested setup**

Run `python bot.py` with the browser window visible — `execute.py` already runs
non-headless — and a database client beside it querying `rpa_challenge.item_run`.

**Tooling**

ScreenToGif records straight to GIF and lets you drop idle frames and lower the
frame rate before exporting, which is how you land under the size limit. Tools
that record to MP4 work too, but add a conversion step where the final size is
only discovered at the end.
