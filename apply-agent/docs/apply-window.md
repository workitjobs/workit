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
- Links sent in (`uv run apply app <link>...`): an agent or a script hands
  the window links with no port and no clicks. `send_links` writes them as
  one file in `APPLY_HOME/app-inbox/`; the window takes them every 2 s
  (`Bridge._take_inbox`) once signed in and set up. With no run going they
  start one, as Start does; during a run each joins it (`Dashboard.into`),
  else it waits for the next run. Each posting is taken once
  (`workit.job_key`): a Greenhouse board's link and its embed's link with
  the same token are one job, both in one take and against the links
  already waiting or in the run (`rehearse`'s `into` answers with the
  tile that has it). With no window open, the command opens
  one, which starts them. `APPLY_HOME/app.pid` names the running window.
  Its stdout and stderr are line-buffered (`line_by_line`), so a log
  written under nohup can be followed live.
- The window from a terminal (`uv run apply window ...`,
  `src/apply/app_control.py`): an agent reads and drives the window as
  JSON, with no screen automation. Use it before any screenshot or
  accessibility tool. It works in a Developer checkout's window only
  (`build.DEVELOPER`), and a window opened before the command existed
  never answers: quit it and open it again.
  - `state` prints what the window shows, sorted as the student page sorts
    it: `needs_you`, `working`, `applied`, `stopped` and `waiting` (queued
    links), plus `window` (sign-in, first run or the page), `summary` and
    `run`. Each job has its `tile` and `id`, company, title, URL, `status`,
    `stage` and `doing`. A held form also has every answer and its
    `source`, its Pre-submit `flags` (dismissed ones left out),
    `legal_holds`, `missing` (each question, whether it is required, its
    choices and the planned answer), `essays`, `why_not` (Auto-submit's
    reason) and the path of its Record's `screenshot`. `applied` lists
    what WorkIt's Tracker says was applied to.
  - `submit <tile> --yes`, `cancel <tile>`, `skip <tile> --yes`,
    `fill-again <tile>`, `answer <id> "<question>" "<answer>"` (or
    `--file <path>`), `remove <link>` and `stop --yes` (or `--new-only`)
    are the page's buttons. Each posts to the route its button posts to,
    through `Bridge.request` with the board's token, so it has the same
    checks and refusals. `submit` is Approve and submit: POST /submit, and
    the run presses the form's Submit (`send_button.press`), reads the
    confirmation and makes a Handoff without one. `--yes` stands in for
    the window's second question. `add <link>...` sends links through
    `app-inbox`, as `apply app <link>` does: the window takes them once
    signed in and set up.
  - The channel is a folder, `APPLY_HOME/app-control/`. The command writes
    one `.request` file (written whole, then renamed). The window looks
    every 0.25 s, renames it `.taken`, answers in a thread of its own and
    writes a `.reply` the same way. A request carries when it expires, so
    a submit the window hadn't taken when the command gave up (after 30 s)
    is never pressed later. One it took but answered late may still go
    through: the command says so, and `state` shows whether it did.
    The folder takes action names, never routes: `/start`, Settings and
    the developer routes can't be reached through it.
  - Output goes through the masked printer, like every command: a value
    from the profile prints as its key, never the value. The exit code is
    1 when the window refused or isn't open.
- `Dashboard(serve=False)` binds nothing. The window loads the Apply
  window's page as a string, with `app_window.SHIM` right after its first
  `<meta charset="utf-8">`, before the page's scripts.
- The shim sends every `fetch` of a path through pywebview's bridge to
  `Bridge.request`, which runs the server's own handler in this process
  (`Dashboard.respond`, `dashboard._InProcess`): the same routes, the
  same token and Origin checks. A new route needs nothing more. The
  frame streams (`/frames`, `/stream/k`) never go through it, since their
  answer never ends: the shim makes `/frames` from `Bridge.frames`.
- A `js_api` method's return that comes back after its page was
  replaced (`load_html`: Go on, Back, the board), such as a `matches`
  wait of up to 90 seconds, finds no callback on the new page.
  `late_replies` drops it, so pywebview's reply thread logs no
  JavascriptException; any other script's error still raises.
- Closing the window or quitting the app closes every form held for the
  student, so it asks first only while one is (`guard_close`): pywebview's
  `confirm_close`, with its question naming how many (`close_words`:
  "Quit WorkIt Auto Apply? Your 3 filled forms waiting for you will
  close."). The `closing` event sets `confirm_close` just before pywebview
  reads it; on a Mac the question's words are read before that event, so a
  thread sets them again each `CLOSE_GUARD_EVERY`. The count is
  `Dashboard.held`: each tile whose page is held (`again`), not submitted.
- `kill <pid>`, Ctrl-C in its terminal and a closed terminal (`QUITS`)
  close the window as its own close does (`closing`), so each `finally`
  stops the run's Workers' Chromes. Without it, Ctrl-C aborted the app
  inside Cocoa and SIGHUP ended it at once, and their Chromes stayed open
  (`docs/plain-workers/guide.md`, "Any exit"). A second one while it
  closes ends the app at once, after the atexit sweep stops the Chromes.
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
  `apply/first_run.py`, each check a callable that tests replace. The seed
  step (Set Up the Worker Extension) comes only when the Workers run on
  Google Chrome (`plain_chrome: chrome`, the default). With
  `plain_chrome: testing` or `APPLY_PLAIN_CHROME=testing`, Workers load the
  worker extension with `--load-extension`, so first run skips the step.
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
  now. The card comes first, right under the headline, so the one thing
  to do is the first thing seen. Under it, when there is more than one,
  "Needs you" lists every to-do in one row each, forms ready to submit first, with what it asks and how long it has waited
  ("Ready to submit · 12 min", from the tile's `since` or the item's `at`);
  a row jumps to its card. Below it, "Still working on" lists only the jobs WorkIt is filling
  or checking, so no job shows twice. A job WorkIt hasn't counted the
  questions of yet (Apply counts them when a fill pauses or ends) or is
  checking has a bar that moves (`bar`), never a made-up share. Each one's
  Watch shows its form as the Worker's Chrome has it now, under the row:
  Workers run headless, so this is the only place to see one being filled.
  The page asks `Bridge.frames` for a newer screen of that tile, again and
  again, while it is open.
- **The run's count** (`runLine`) sits under the heading while a run goes:
  "3 of 10 done · 2 need you · 4 filling · 1 waiting". It counts this run's
  jobs only. Each "Still working on" row says "Filling · 6 min" (from the
  tile's `since`) and, when Apply's `doing` line is one `words.step` knows,
  its step: "Writing answers".
- **Notifications and the Dock badge.** While the window is behind, a
  macOS notification titled "WorkIt Auto Apply" names each form newly
  waiting and what it asks ("Amazon: sign in needed", "Stripe: ready to
  submit"), at most one a minute (`Dashboard._tell`). The Dock icon's badge
  (`app_window.badge`, through pyobjc on a Mac) is the number of to-dos
  (`dashboard.todo_count`), and clears when the run ends.
- **The heading** (`headline`) counts the questions waiting, not the jobs
  that ask them, and with only stopped jobs left it says how many didn't go
  through. Apply's own lines (a route's refusal, an app method's error,
  `Bridge.status`) reach the page in its own words (`src/words.ts`, `said`);
  a line it doesn't know passes as it is unless it has a developer word.
- **Applied** (`appliedJobs`) is this run's submitted jobs, then what the
  student applied to on WorkIt before (`Bridge.applied`:
  `GET /applicants/{id}/applications?stage=applied`), each once by its link,
  form address, or company and role. Its button is on the start screen too.
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
- **What we filled** (the Submit and Check cards, `filledIn`): every
  answer the form was filled with, from the tile's `answers`
  (`worker._Planned.listed`), each with where it came from (Your
  profile, Your saved answer, Written by WorkIt). The ones worth a
  glance come first and are marked, in this order: what WorkIt wrote,
  work authorization and sponsorship, demographics, school and
  graduation, pay, the files attached (`worker.topic`); the rest are
  behind "Show the other N answers". An answer longer than 220
  characters is cut at a word with Show more (`clip`). `listed` never
  holds a secret (`records.SECRET`: a job-site password Apply made) or
  a file's path, only its name, and it reaches the page only through
  `/state`. When the Pre-submit review changed answers after checking
  (the tile's `fixed`, from `_Planned.fix`), the card says "We changed
  N answers after checking" with each "question: old → new"
  (`changes`).
- **The Check card** (`toCheck`) lists every flag verifying says needs
  the student, each with its question, in WorkIt's words (`flagged`).
  With no flags it lists each part of the form's reason in the same
  words, never "Something went wrong" for a reason that names the
  Pre-submit review; with no part left, "One answer doesn't match your
  WorkIt profile." Then "Fix it in the form, then press Submit there." Like every card, it has no
  Submit of its own: Apply never submits.
- **Handing back.** Each to-do card says how the student hands the form
  back (`HANDOFF` in `view.ts`): sign in yourself in the window that
  opens; check your email for the code and type it (Apply reads no email);
  finish the captcha check (Apply never solves one); fix a flagged answer
  and press Submit there. A handoff whose reason names the fields a
  Workday step won't leave (`wantedFields`, from its "Error-<field> The
  field ..." lines) lists them and says to press Next there. Once the
  student presses Open on a card, it says "Waiting for you in Chrome…":
  Apply tells the page nothing of Chrome's focus, so this is only what the
  page itself knows.
- **Empty and waiting states.** Start shows a one-time, dismissible "How
  it works" strip (remembered in the page's local storage only). When
  nothing is left to do, the home page says how many applications this
  run submitted (`submittedLine`, not the student's earlier ones from
  WorkIt) with a link to Applied. Watch's blank screen says "It can take a
  minute the first time."
- **The Approve card stays (decided, stories 16 and 17)** with its mock,
  though no Hold reaches a Student run yet: a rehearsal maps Held to ready.
- **Didn't go through (KAN-873).** A failed or skipped job (not eligible,
  closed, already applied, paused, an employer's limit) is listed with its
  reason (`reason`: `verdict()`'s label, without "Skipped:" and with no
  developer words). Try again shows only where Apply still holds the
  job's page (the tile's `again`, `askable` or `refill`): it posts
  `/fill-again` for that tile, and the job moves back to "Still working
  on" as the form fills anew. A job whose Worker moved on, one never
  opened (already applied) and one paused have none. Every row says what
  to do (`stopOf`, `stopActions`): a closed posting ("This job was taken
  down. Nothing to do.") and an already applied one ("You already
  applied. Nothing to do.") offer nothing; any other failure reads "We
  couldn't finish filling this one." and never shows the raw error (a
  timeout, `PortTimeoutError: ...`), with Try again, "Open the form and
  finish it yourself" while its page is held, and "Apply on the company's
  site", which calls `Bridge.open_posting` (opens only a posting this run
  lists, in the student's own browser).
- **Today's usage (KAN-837).** At the foot of every page, a bar shows the
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
  The question names the filled forms a full Stop closes (`stopWords`,
  from each tile whose page is held, `again`): "Stop? 3 filled forms
  waiting for you will close." While jobs wait to start, Stop new ones
  only comes first and posts `/stop` with `{"new_only": true}`: no job
  waiting starts, the run takes no new link (`into`), a fill under way ends
  held as any does, and every held page stays open until the student closes
  it or presses Stop again. A full Stop ends the run (`rehearse`'s stop): no
  job waiting starts, each held page
  is let go unsubmitted, a fill under way ends on its own (a rehearsal
  never submits) or when the run's Workers close, `on_done` still runs, and
  `app_window.Bridge` shows the queue
  again. Below "Still working on", each job waiting to start (`run.waiting`,
  named as the queue named it; a link sent in or pasted as
  `apply.queued_names` names it, else by its site) has Remove,
  which posts `/remove` with its link: the run drops it before its turn
  (`rehearse`'s remove), and refuses one that started already. Both routes
  take only the window's token.
- **At most five forms open.** Each open form is a browser window, so a
  rehearsal opens at most `rehearsal.OPEN_FORMS` (5) at once: a job takes
  a slot before its form opens and gives it back when its page closes
  (sent, let go, or its window closed). A form gives it back at once,
  with its tab still open, when it is sent, when the student presses Not
  applying to this one, and when Apply pressed its Submit but the job
  site never confirmed it (that Handoff waits on no Worker). The run says the cap
  (`run.open_forms`); while nothing fills, jobs wait and the to-dos fill
  every slot, "Still working on" says the next starts when the student
  submits, lets go of, or closes one (`view`'s `full`). Start together is
  not capped.
- **Auto-submit** (ADR 0006, `apply.auto_submit`). With `auto_submit: true`
  in a Developer checkout's policies.yaml (off by default; the Student build
  reads no policies.yaml), a held form that needs nobody counts down ten
  minutes and then is pressed as Approve and submit presses it. Its Review
  card shows "We'll submit this in 9:42 unless you cancel." with Cancel
  (`POST /auto-cancel`) and Submit now, and a notification says it is
  coming ("Open Auto Apply to cancel": macOS notifications from osascript
  carry no buttons, so Cancel lives in the window). A form needs nobody
  when it passed the Pre-submit check with no flags, no Missing fact, no
  legal hold and no reason to hold it (so never in the Calibration run);
  has no Essay, in a text box or as a file; never paused (a sign-in,
  captcha or code); names its company, and it isn't a Target company; is
  on a job system that emails no code after Submit (Greenhouse does); had
  no Employer account made for it today; and is on a job system Apply has
  submitted to before ("other", any careers site Apply doesn't know, never
  counts). Any other form's card says why it waits ("Waiting for you: it
  has an Essay."). Any answer Apply changes on the page during the wait
  (from the window, Ask Claude or a regenerate) ends the countdown, and a
  Cancel that lands as the wait runs out either stops the press or is
  refused, never both (`Dashboard.auto_go`).
- **Review card, Approve and submit** (ADR 0006). A form ready to submit
  is a Review card: what was checked, what the Pre-submit review changed,
  the answers worth a look (Essays, work authorization, demographics,
  school, pay, files), and every other answer folded under What we
  filled. The decision (Approve and submit, Fix in the form) sticks to
  the window's foot while the answers scroll by, so it never sits below
  the fold. Approve and submit (`POST /submit`) has the run press the held
  form's own Submit (`apply.send_button`): only the one visible Submit or
  Send button, in the page or a frame, and with none or several it
  presses nothing and the card says why. It refuses while an answer is
  still needed, while Submit is held on the page (a red note, an earlier
  application), and after any Submit. A click that never answers, as a
  Submit that sends the whole page away can end it (`send_button.Unsure`),
  counts as pressed. The job system's confirmation is
  read as for the student's own press; with none within two minutes
  (`rehearsal.CONFIRM_S`), and no captcha or refusal to explain it, the
  form becomes a Handoff that says it may have gone in, and Apply never
  presses its Submit again. A card with flags leads with Fix in the form
  and offers Submit as it is. Opening the form and pressing Submit by
  hand still works.
- **Not applying to this one.** A to-do card whose form is held (its
  tile's `again`) has Not applying to this one, asked once more before it
  posts `/let-go` with the tile (`Dashboard.let_go`). The tile gets
  `let_go`, so `view` drops its card at once, and the run lets that one
  page go unsubmitted, as if its window closed (`hold`'s `let_go`, through
  `Board.let_go_asked`); the other forms stay held. The route takes only
  the window's token, and refuses a tile with no held form or one
  submitted.
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
  `/state`, `/answer`, `/approve`, `/show/<k>`, `/fill-again`, `/let-go`,
  `/stop` and `/remove` through plain `fetch` with `X-Apply-Token`, which app_window's SHIM carries to
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
  guessed from a name. A link sent in or pasted is named in the
  background as it waits (`Dashboard.names_by`, `apply.queued_names`), with
  plain reads and no browser: WorkIt's job when WorkIt lists the link (its
  logo sources too), else its job system's names (`request.resolve`), and a
  careers page's Greenhouse job (`greenhouse.board_behind`) with the page's
  own registered domain as `company_domain`. One nothing names shows its
  host and initials. Each
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
