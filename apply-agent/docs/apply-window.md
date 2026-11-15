# The Apply window and rehearsal records

Reference for Apply, reached from `apply-agent/CLAUDE.md`. Paths are relative to `apply-agent/`. A change in this area updates this file in the same PR.

## The Apply window

- The status line counts a link as "queued" only until a Worker starts it.
  A rehearsal sends `board.run(queued=...)` each time a link starts.
- When a run or rehearsal ends, its window closes (`Dashboard.__exit__`).
  A window with no server shows a run that is gone.
- A click on Apply in the Dock goes to the window's Chrome, which counts no
  app window as a browser window and opens a New Tab window, every click.
  The window's keeper (`dock_app.keep`) closes it at once and brings the
  window forward. The bundle's launcher starts the keeper beside the
  window's Chrome, so it lives as long as that Chrome. Never move it back
  into the process that opens the window: `apply watch` exits right after.
- `kill <pid>` (SIGTERM) stops Apply as Ctrl-C does: the Worker browsers
  and the window close. Ctrl-C does not reach Apply when it runs in the
  background, so use SIGTERM there.

## WorkIt Auto Apply's window (`uv run apply app`, KAN-858)

`src/apply/app_window.py`, started by `apply.student.app`: a native window
(pywebview, WKWebView on a Mac) with no port (D11). Read the module's
docstring first.

- `Dashboard(serve=False)` binds nothing. The window loads the Apply
  window's page as a string, with `app_window.SHIM` right after its first
  `<meta charset="utf-8">`, before the page's scripts.
- The shim sends every `fetch` of a path through pywebview's bridge to
  `Bridge.request`, which runs the server's own handler in this process
  (`Dashboard.respond`, `dashboard._InProcess`): the same routes, the
  same token and Origin checks. A new route needs nothing more. The
  frame streams (`/frames`, `/stream/k`) never go through it, since their
  answer never ends: the shim makes `/frames` from `Bridge.frames`.
- A link to `/...` opens through `Bridge.open`, which opens only a file
  a tile or History lists (`Dashboard.listed`). `sendBeacon('/closed')`
  does nothing: the window's own close ends the app.
- pywebview gives the page every public method and attribute of
  `Bridge`, nested ones too, and nothing whose name starts with `_`. Keep
  every reference the page must not call behind an underscore.
- What the window shows comes from one place, `Bridge._html`: `SIGN_IN`
  signed out, `FIRST_RUN` while `first_run.FirstRun.step()` isn't
  `READY`, else the Apply window (`Bridge._page`), with the queue on top
  (`PANEL`) when no run goes, and `USAGE` (model use, Settings) on every
  page. A new screen is a page constant here and one branch there.
- First run's steps and the app's settings (`app.json` in the data folder:
  the disclosure, the Screen Recording ask, the Worker count) are in
  `apply/first_run.py`, each check a callable that tests replace.
- A run is `student.Runs.run` in a thread of the bridge's: one at a time,
  its own `Dashboard(serve=False)` shown while it goes, the queue's again
  after. A `SetupError` (no engine, a profile in use) is its one-line
  reason (`Bridge.status`).
- Remove All My Data deletes the data folder only when `build.STUDENT`:
  in a Developer checkout it says the folder is the developer's.
- A link to a new window (`target="_blank"`: a posting, History's
  Applications Tracker on WorkIt) opens in the default browser: pywebview
  does that itself. The app's windows pass `tracker_url` (`student.tracker_url`).
- `pywebview` is imported only in `app_window.run`, so the bridge and its
  tests need no window. `tests/test_app_window.py` (no browser, CI) and
  `tests/test_app_window_page.py` (the shim in Chromium, with Playwright
  in pywebview's place: it puts `window.pywebview` in after the page
  loads, as pywebview does, since `set_content` runs no init script).

## Rehearsal records

A Workday link is named from the Feed; one the Feed lacks is named by
Workday's job API, its legal entity trimmed to the company
(`workday.company_of`: "ASML US, LP. (US30)" is ASML). Unnamed, ASML's
Record was headed "# : " in a folder named `company-...`.

Every rehearsal outcome writes its Record (`rehearsals/<date>/`), a Handoff or
a failure too, not only a filled form. A step Workday won't leave keeps what
was planned and what each field showed up to there
(`WorkdayFiller.shown_so_far`); an outcome before any form opened keeps a
screenshot of the page it stopped on.
