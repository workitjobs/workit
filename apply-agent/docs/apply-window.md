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

- A run keeps the Mac awake (KAN-885): `student.Runs.run` runs inside
  `awake.awake()`, which starts `caffeinate -dims -w <Apply's PID>` and
  stops it when the run ends. `-w` ends it with Apply too, even on a crash
  or SIGKILL. Windows and Linux do nothing yet (F4); `awake.py` is the one
  place for that OS call (`tests/test_each_os.py`).
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
- Sign-in (`SIGN_IN`, KAN-883): Sign In with WorkIt calls `Bridge.sign_in`,
  which first readies the helper that takes the page's
  `workit-auto-apply://` link (`sign_in_link.ready`, then `clear` to
  forget an old link), then opens WorkIt's page. The screen asks
  `Bridge.take_link` each second; once the helper has the link,
  `take_link` trades its code as a pasted one (`Bridge.trade`) and brings
  the window in front of the browser (`bring_forward`), signed in or
  saying why not. The built app needs no helper: it claims the link
  itself and takes it from macOS (`sign_in_link.listen`, set up in `run`
  before the window starts). Without either (off a Mac, a data folder in a
  temp folder) the code box still works. `docs/workit.md` has the PKCE flow.
- First run's steps and the app's settings (`app.json` in the data folder:
  the disclosure, the Screen Recording ask, the Worker count) are in
  `apply/first_run.py`, each check a callable that tests replace.
- A run is `student.Runs.run` in a thread of the bridge's: one at a time,
  its own `Dashboard(serve=False)` shown while it goes, the queue's again
  after. A `SetupError` (no engine, a profile in use) is its one-line
  reason (`Bridge.status`).
- Remove All My Data deletes the data folder only when `build.STUDENT`:
  in a Developer checkout it says the folder is the developer's. It
  forgets each job-site password the Tracker's Employer accounts name
  first: once the folder goes, nothing names them.
- Report a problem (Settings, and an Application's card with its id) is
  two calls: `review_report` builds the report and keeps it, the page
  shows its `parts`, and `send_report` sends that kept report, never the
  form's answers again. A changed answer hides Send Report till it is
  reviewed again. A card's `send_report` names its Application's id, and
  one whose kept report is about another (or about none, Settings') is
  refused: the window keeps one report, which another form's Review Report
  replaces. The log is masked with `app_window.PROFILE`, the
  profile's file: a folder masks nothing (`report.build` refuses it).
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
  or checking, so no job shows twice. A job WorkIt hasn't counted the
  questions of yet (Apply counts them when a fill pauses or ends) or is
  checking has a bar that moves (`bar`), never a made-up share. Each one's
  Watch shows its form as the Worker's Chrome has it now, under the row:
  Workers run headless, so this is the only place to see one being filled.
  The page asks `Bridge.frames` for a newer screen of that tile, again and
  again, while it is open.
- **The heading** (`headline`) counts the questions waiting, not the jobs
  that ask them, and with only stopped jobs left it says how many didn't go
  through. Apply's own lines (a route's refusal, an app method's error,
  `Bridge.status`) reach the page in its own words (`src/words.ts`, `said`);
  a line it doesn't know passes as it is unless it has a developer word.
- **Applied** (`appliedJobs`) is this run's submitted jobs, then what the
  student applied to on WorkIt before (`Bridge.applied`:
  `GET /applicants/{id}/applications?stage=applied`), each once by its link,
  form address, or company and role. Its button is on the start screen too.
- **Answer Bank (W11, `src/answers.tsx`, `src/bank.ts`)** is the student's
  Answer bank, with the website's design (Application Info's Answer Bank:
  `../../frontend/docs/screens.md`): a change to one goes into the other.
  It reads the Answers tab's view once (`Bridge.bank`, `GET /answers`) and
  sends each change through its routes (`Bridge.changeBank`,
  `POST /answers/bank/{save,add,review,delete}`), each of which waits for
  WorkIt's reply and answers the new view. A save WorkIt's rule keeps out
  says the rule's reason (`words.ts` keeps it, where every other "Not
  saved" line reads "Your answer wasn't saved"). Remove has Undo for the
  student's own answer only: a draft is drafted again by the next form.
  The window has no danger colour, so its error lines use the warning ink.
- **Find jobs (KAN-882, `src/find.tsx`, `src/find-view.ts`).** When the
  window has `Bridge.matches`, the start screen is Find jobs: the
  student's best matches that Auto Apply fills and that they haven't
  queued or applied to (`GET /applicants/{id}/auto-apply/matches?size=30`),
  best first, drawn as the website's Jobs page draws them: its search
  (asked half a second after the last key, and not again for the same
  words), its filter row (location, role, workplace, job type, date
  posted; Internship is picked at first), and its cards with the match
  ring and up to two highlights. `Bridge.matches` passes on only the
  Jobs page's own filters (`MATCH_FILTERS`), gives each match as the
  queue names a job with its card's facts (`MATCH_FACTS`), and keeps each
  one's logo by its link, as `Bridge.queue` does. An empty experience
  bank (the route's 404) says to add experience on WorkIt first. A card's
  click or Add to Auto Apply picks it, Add my top 5 picks the first five,
  and Start applying runs the picked links through `Bridge.start`, as
  ticked queued jobs run. The ✕ (Not interested) hides a card on this
  page only: the website's Not Interested stores nothing yet
  (`NOT_INTERESTED_LIVE` is off), so there is no route to send it to.
  Matches read for a set of filters are kept while the window is open,
  so coming back shows them at once while they are read again. "Your
  queue · paste a link" opens the queue screen, and the header's Find
  jobs comes back. A window with no `matches` keeps Add jobs and the
  queue screen.
- **Add jobs (decided, stories 33 and 41).** The header's Add jobs shows
  whenever no run is going (`addsJobs`) and is hidden during a run, because
  `Bridge.start` refuses a second run. The caught-up card has Add jobs too,
  which goes back to the queue screen (with Back to your applications).
- **The Submit card** (`checks`) lists only what Apply says it did:
  "Checked against your WorkIt profile" when `verified`, and "Resume
  attached" when a file the form was given answers its resume question
  (`files`' label).
- **The Approve card stays (decided, stories 16 and 17)** with its mock,
  though no Hold reaches a Student run yet: a rehearsal maps Held to ready.
- **Didn't go through (KAN-873).** A failed or skipped job (not eligible,
  closed, already applied, paused, an employer's limit) is listed with its
  reason (`reason`: `verdict()`'s label, without "Skipped:" and with no
  developer words). Try again shows only where Apply still holds the
  job's page (the tile's `again`, `askable` or `refill`): it posts
  `/fill-again` for that tile, and the job moves back to "Still working
  on" as the form fills anew. A job whose Worker moved on, one never
  opened (already applied) and one paused have none.
- **Today's usage (KAN-837).** On top of every page, a bar shows the
  share of today's Usage cap used ("66% used · resets at 7:00 PM"), like
  Claude's usage bar, never a token count, which means nothing to a
  student. The window reads `usage` (`GET /apply-app/usage`) each minute,
  and again each time a form leaves "Still working on", so the bar moves on
  by what that form used. A failed reading keeps the last one, and an older
  reading that arrives late never moves the bar back. The share is rounded
  down: rounded, 79,700 of 80,000 read "100% used" while forms still
  filled. From 80% the bar turns amber and says "You're
  close to today's limit."; at the cap a banner on top says when applying
  works again. A Student run waits at the cap until it resets
  (`rehearsal._after_the_limit`): its `paused_until` makes `run.paused`,
  and the banner says when it starts again. A job that reached the cap
  mid-form ends there and reads "Stopped at today's limit. Try again once
  it resets" (Try again where its page is held), from UsageLimitHit's
  "Usage limit reached" (before KAN-837, "Max usage limit hit").
- **Stop applying and Remove (KAN-874).** While a run goes (`run.mode`),
  the header has Stop applying, asked once more before it posts `/stop`.
  The run ends (`rehearse`'s stop): no job waiting starts, each held page
  is let go unsubmitted, a fill under way ends on its own (a rehearsal
  never submits) or when the run's Workers close, `on_done` still runs, and
  `app_window.Bridge` shows the queue
  again. Below "Still working on", each job waiting to start (`run.waiting`,
  named as the queue named it; a pasted link by its site) has Remove,
  which posts `/remove` with its link: the run drops it before its turn
  (`rehearse`'s remove), and refuses one that started already. Both routes
  take only the window's token.
- **`src/view.ts`** turns `Dashboard.state()` into that pile and that list
  (`view`), names the pile in the heading (`headline`), says the Usage
  cap in words (`limit`) and gives its bar's share and line (`usedShare`,
  `usageLine`). For the start screen it picks what Start runs
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
  `Dashboard.respond`. `app`: `app_window.Bridge`'s `js_api` methods (`queue`, `applied`, `matches`, `start`,
  `status`, `usage`, `settings`, `review_report`, `send_report`), feature-detected at
  `pywebviewready`; it never settles in a window that has none. With no
  `window.APPLY_TOKEN` the page runs on `src/mock.ts`.
- **Report a problem (D26)** is under each to-do card, each "Didn't go
  through" row and each Applied row whose job has an `application_id`
  (`src/report.tsx`): what it is about (`window.REPORT_CATEGORIES`, which
  `student_page` puts in from `report.CATEGORIES`), what happened, whether
  to include what was filled in and the log (ticked), and whether WorkIt
  may email the student. Review Report lists what goes; Send Report sends
  that, named by the same id. A changed answer hides Send Report, and the
  form is held still while a press is answered. A row's form opens under
  the row, so its logo and button stay where they were. The Chromium test
  (`tests/test_app_window_page.py`) drives it on the real page.
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
  `npm run build` and `npm test` are Node scripts (`window/scripts/`), so they
  run the same on Windows.
  Commit it with the source change: CI's `apply-window` job rebuilds it and
  fails on any difference. The page is built with WorkIt's public
  Brandfetch client id, `NEXT_PUBLIC_BRANDFETCH_CLIENT_ID`: from the
  environment (CI sets it from the repo's variables), else
  `frontend/.env.local` or `frontend/.env`, else the id `vite.config.ts`
  keeps as its default, so a plain `npm run build` matches the committed
  file. `npm run dev` serves the page on the mock; pick
  a fixture with `?scenario=start|needs|questions|ready|quiet|stopped`
  (`questions`: one question of each kind), the day's use with
  `?usage=near|cap`, the start screen's queue with
  `?queue=empty|unread|refused`, and Find jobs' matches with
  `?matches=empty|unread`.
- **Token:** `app_window.student_page(board)` puts SHIM and
  `<script>window.APPLY_TOKEN = "<board.token>"</script>` right after the
  page's charset meta, before its module script (`_before_scripts`, which the
  developer page's `page` uses too; with no charset meta, at the very start). A board
  swap (`Bridge.show_board`) reloads the page with the new board's token.
- **Look:** WorkIt's tokens from `frontend/src/app/globals.css`, under the
  same names (`src/theme.css`), and Inter's Latin subset inlined. The page
  follows `frontend/docs/design.md`: the type scale's `text-*` tokens, its
  radii and shadows, no hex, px or arbitrary value. Its own tokens are
  `--container-window` (its column) and `--color-updates-tint` (a logo
  tile's pink, beside the website's tints).
