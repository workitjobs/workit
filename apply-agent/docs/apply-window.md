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
  `READY`, else the student page (`Bridge._page`, `student_page`; see
  below). A window given no `start` (a Developer checkout's) keeps the
  developer page (`page`). A new screen is a page constant here and one branch there.
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

## The student page (`window/`, KAN-867)

The page WorkIt Auto Apply's window shows (design doc, W5). It is built
for a student, not from `dashboard_page.py`.

- **One screen, one pile.** Everything that waits on the student is a
  to-do: a sign-in, a question, an emailed code, a captcha, an answer to
  check, an Essay to approve, a form to finish or to submit. The window
  shows one at a time, most blocking first, with "1 of 4" and Skip for
  now. Below it, "Still working on" lists only the jobs WorkIt is filling
  or checking, so no job shows twice. Submitted jobs are under "Applied".
- **Didn't go through (KAN-873).** A failed or skipped job (not eligible,
  closed, already applied, paused, an employer's limit) is listed with its
  reason (`reason`: `verdict()`'s label, without "Skipped:" and with no
  developer words). Try again shows only where Apply still holds the
  job's page (the tile's `again`, `askable` or `refill`): it posts
  `/fill-again` for that tile, and the job moves back to "Still working
  on" as the form fills anew. A job whose Worker moved on, one never
  opened (already applied) and one paused at the usage limit (it goes on
  by itself) have none.
- **Stop applying and Remove (KAN-874).** While a run goes (`run.mode`),
  the header has Stop applying, asked once more before it posts `/stop`.
  The run ends (`rehearse`'s stop): no job waiting starts, each held page
  is let go unsubmitted, a fill under way ends on its own (a rehearsal
  never submits) or when the run's Workers close, and #613 shows the queue
  again. Below "Still working on", each job waiting to start (`run.waiting`,
  named as the queue named it; a pasted link by its site) has Remove,
  which posts `/remove` with its link: the run drops it before its turn
  (`rehearse`'s remove), and refuses one that started already. Both routes
  take only the window's token.
- **`src/view.ts`** turns `Dashboard.state()` into that pile and that list
  (`view`), names the pile in the heading (`headline`) and says the Usage
  cap in words (`limit`). For the start screen it picks what Start runs
  (`chosen`: the ticked jobs, then a pasted link not ticked already) and
  says why there is no queue to tick (`queueNote`). A tile wins over its
  item for the same posting, but the job keeps the item's `id` and questions (what `/answer` names),
  and the tile's place on the board (what `/show/<k>` names). Its tests:
  `npm test` (Node's test runner, in CI).
- **Questions.** A question to-do asks its job's questions one at a time;
  once one is answered the next shows at once, before Apply's next state
  drops the answered one. `asking` picks each question's form from
  `choices`: up to four options as buttons, more as a list, a
  pick-all-that-apply as boxes to tick (sent joined by "; " in the form's
  order, `answerOf`, as today's window sends them), a file as a file
  picker (sent in `/answer`'s `file` field), else a box pre-filled with
  the answer Apply planned but the form refused. A question the form
  marks optional (`required` false) has Skip, which saves an empty
  answer. Keys (`shortcut`): 1 to 9 pick an option, Enter saves, S is
  Skip for now; none fires while typing in a box or with Cmd, Ctrl or
  Alt held.
- **`src/bridge.ts`** is the spec's bridge contract. `routes(token)`:
  `/state`, `/answer`, `/approve`, `/show/<k>`, `/fill-again`, `/stop` and
  `/remove` through plain `fetch` with `X-Apply-Token`, which app_window's SHIM carries to
  `Dashboard.respond`. `app`: #613's `js_api` methods, feature-detected at
  `pywebviewready`; it never settles in a window that has none. With no
  `window.APPLY_TOKEN` the page runs on `src/mock.ts`.
- **Logos (KAN-871)** come as the website finds them (`jobLogo`):
  Brandfetch's icon by `company_domain`, through `fallback/404` and
  WorkIt's public client id, then the scraper's `logo_url`, then the
  initials tile (`src/logo.ts`, `Logo` in `src/ui.tsx`). No domain is
  guessed from a name: a pasted link has none, so it shows initials. Each
  image stays hidden until it loads; one that fails moves on to the next
  source, so no broken image shows. `Bridge.queue` passes on each job's
  `logo_url` and `company_domain`, keeps them by link, and gives them to
  every board it shows (`Dashboard.logos`). The board adds them to each
  tile and item by the link the run was given (`link`, which a rehearsal
  now puts in its captions) or by `posting_url`.
- **Build:** in `window/`, `npm ci`, then `npm run build` writes one
  self-contained file into the package, `src/apply/student_page/index.html`.
  Commit it with the source change: CI's `apply-window` job rebuilds it and
  fails on any difference. Build it with WorkIt's Brandfetch client id,
  `NEXT_PUBLIC_BRANDFETCH_CLIENT_ID`, in the environment or in
  `frontend/.env.local` (CI sets it from the repo's variables); a build
  without it leaves Brandfetch out and differs from the committed file. `npm run dev` serves the page on the mock; pick
  a fixture with `?scenario=start|needs|questions|ready|quiet`
  (`questions`: one question of each kind), the day's use with
  `?usage=near|cap`, and the start screen's queue with
  `?queue=empty|unread|refused`.
- **Token:** `app_window.student_page(board)` puts SHIM and
  `<script>window.APPLY_TOKEN = "<board.token>"</script>` right after the
  page's `<meta charset="utf-8" />`, before its module script. A board
  swap (`Bridge.show_board`) reloads the page with the new board's token.
- **Look:** WorkIt's tokens from `frontend/src/app/globals.css`, under the
  same names, and Inter's Latin subset inlined.
