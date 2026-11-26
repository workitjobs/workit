# CLAUDE.md — Apply

Loaded on top of the root `../CLAUDE.md` when you work in `apply-agent/`.

## What Apply is

Apply is a command-line agent that applies to job postings for one person.
It reads a job posting, fills the application form in Chrome through the
Fill engine, writes the answers and essays with hosted models (Groq, with
Gemini as backup; `claude -p` for a developer who sets `ask_model: claude`),
and shows the Apply
window (Start, Needs you, Answers, Accounts). A rehearsal fills the form and never
submits. It runs on the person's own Mac, with their own Chrome and their
own Claude Code login. Today it is a developer and power-user tool, not a student
feature: students apply through the extension and the connector (KAN-369).
KAN-723 designs WorkIt Auto Apply, the Student build of Apply: a desktop
app for students, beside the extension (decided 2026-11-13, being built;
the design doc's section 6 says where each workstream stands). It
makes every model call through WorkIt's Model route and does no research
(ADR 0005), downloads the Fill engine encrypted, puts the Worker extension
on the Chrome Web Store through the Debugger API, and is compiled without
the developer parts. Apply's code moves to the private repo
`workitjobs/apply-agent` first (workstream W0). Read
`../docs/desktop_application_auto_apply.md` before a change toward that:
it splits the work into workstreams a session can take one at a time.
`ask_model: workit` is the default (2026-11-14, KAN-723 D5): each text
call goes to WorkIt's Model route as a kind and its data, and WorkIt builds
the prompt (`../backend/app/apply_prompts/`) and runs the models; Apply
builds no `ask` prompt of its own. Before that,
`ask_model: [groq, gemini]` (2026-11-10) sent them to Groq, with Gemini as its backup, on shorter (lean) essay
prompts, with keys from the checkout's `.env` (`docs/ask-model.md`).

Workers default to `worker_mode: protected` (2026-11-06, KAN-723): plain
Workers fill the hosts that block CDP Workers, and CDP Workers fill the rest
(`docs/plain-workers/guide.md`).

Apply has its own domain language. Read `GLOSSARY.md` and `docs/adr/` here,
not the root ones, for its terms (root `GLOSSARY-MAP.md`). Write each
glossary entry in ASD-STE100 wording: sentences of 25 words or fewer.

## How it differs from `auto-apply/` and the extension

- `auto-apply/` is the design document for WorkIt's auto apply (KAN-223)
  and its rehearsal records. It holds no runnable code.
- `autofiller_extension/` is the Chrome extension that students install. It
  fills forms in the student's own Chrome; Scout and the connector write its
  answers, and the WorkIt backend keeps its state.
- `apply-agent/` is a Python program (uv, Playwright) that runs its own
  Chrome workers. Hosted models (or Claude) write its answers. Its state is files in the data
  folder, not the WorkIt database. It calls the WorkIt API only through
  the WorkIt client (`docs/workit.md`), as the signed-in student.

Both Apply and the extension fill forms with the same Fill engine
(`docs/fill-engine.md`). A fix to how a field is read, planned from the profile, filled
or read back goes into the engine, not into Apply. Apply's own plan rules
are Apply-side checks, not fill fixes: they decide what
Claude may draft and what Apply's own read-back accepts, and the extension
has neither.

## Rules for every run

- **A change to what the Worker extension's store package holds needs a store
  release** (KAN-839). Students run the copy the Chrome Web Store publishes,
  never a checkout's, so a change reaches them only in a new store version.
  - **These change it:** the extension's own code (`worker-extension/`:
    `manifest.json`, `background.js`, `ops/`, `page/`); the guard scripts
    (anything that changes `plain/guards.FILES`: `submit_guard.py`'s scripts and
    the constants they take in); the fixed page functions (`plain/fixed.py` and
    every string it lists); and Playwright's version (`vendor/injected.js`).
  - **These don't:** the Fill engine (Apply hands it over at run time), the rest
    of Apply's Python, prompts, and page code that runs through `eval`.
  - `tests/test_worker_extension_store.py` (in CI) fails on such a change and
    says what to do: bump `worker-extension/store.json`'s `version`, set its
    `code` and `files`, then build and upload the package after merge, and
    release an app that needs it only once the store publishes it
    (`docs/plain-workers/worker-extension-todo.md`, Releases).
- **Code that differs by OS** (W4 of `../docs/desktop_application_auto_apply.md`,
  KAN-850): Apply runs on the Mac today, and WorkIt Auto Apply ports to Windows
  and Linux later (F4). A general library comes first: Python's standard
  library, `psutil` (a process's arguments), `platformdirs` (each OS's data and
  cache folders), `pyperclip` (the seed guide's clipboard), the window's own
  `navigator.clipboard`, or Chrome itself (`/json/activate`, the worker
  extension's `windows.focus`). Per-OS code lives in one place for each job,
  with an entry for macOS, Windows and Linux picked by a `system` argument
  (`sys.platform`): Chrome's places and version (`chrome_finder.py`, the one
  Chrome finder), the native host's folder (`native_host.chrome_hosts`), a
  Chrome's start (`plain/launcher.start_in_background`: a Worker's in the
  background, the seed's in front; on the Mac through `open`, never as
  Apply's child, or macOS blames the built app for what Chrome's updater
  does: "prevented from modifying apps"), a link in
  the student's everyday Chrome (`captcha.to_everyday_chrome`: `open -a` on the
  Mac, so Chrome never runs as Apply's child), showing a folder
  (`plain/seed_setup.Desk.reveal`), and keeping the computer awake during a run
  (`awake.command`: `caffeinate` on the Mac). FocusKeeper (`focus.py`) is the
  Mac's only: elsewhere `focus.KEEPER` is a `NoKeeper`. A new Chrome path or OS
  call goes into one of these places, with a case for each OS in
  `tests/test_each_os.py` (in CI); never a `/Applications/` path, `open`,
  `osascript` or `ps` anywhere else. What W4 left for F4 is in its "Found on
  the way" list.
- **In the Student build no model drives the browser** (D13, KAN-861, W2
  step 2, `docs/generic-filler.md`). A job system with no Filler gets the
  generic Filler: code reads the form from the accessibility tree and does
  every click, and a model only picks an option or a Next by its number
  (`generic_fill.pick`, `generic_fill.next`). Its clicks are click paths:
  a change to them gets the adversarial review and joins
  `tests/test_submit_guard_hostile.py` (KAN-666).
- **The Student build leaves the developer parts out** (KAN-723, W3,
  `src/apply/build.py`). WorkIt Auto Apply is compiled from `apply.student`
  without the modules in `build.DEVELOPER` (`claude -p`, Claude fill, Rescue,
  Ask Claude, Repairs, Gmail, notifications, the Dock keeper, the Sheet,
  `cli.py`). So a module on the Student path never imports one of them at its
  top: import it inside the function that uses it, behind `if build.STUDENT`
  or in a path the Student build never runs (a Developer checkout's command).
  A function the Student build does run counts too: `plain/fixed.functions()`
  imported Ask Claude and the emailed code for their page strings, which loaded
  Gmail and Claude fill at every plain Worker's first page call. A string or
  class the Student path needs moves out of the developer module
  (`page_functions.py`, `one_page.py`, `code_box.py`, `adapters.ClaudeError`,
  `workit.job_key`), and its callers import it from there.
  `tests/test_student_build.py` (in CI) fails when the Student path loads one,
  as it imports, builds `student.adapters()` or makes that first page call.
  Read `build.STUDENT` when the code runs, never into a constant at import. The one
  exception is `home.HOME`, which every data path is made from at import: the build
  script writes STUDENT before it compiles (`tests/test_student_build.py` checks it in a
  new process).
  The Student build reads no `policies.yaml`: `build.STUDENT_POLICIES` go over
  the defaults. A new developer part joins `DEVELOPER`, and the Student
  build's stand-in for it joins `apply.student.adapters()`.
- **In the Student build, what Apply can't do is the student's, in the Apply
  window** (KAN-855, W2 step 1, `docs/held-forms.md`). A field the form
  didn't take, a page the generic Filler can't go on from, and an emailed
  code are each held for the student, who does it through Fix here; an
  answer they type in the window goes in by the Fill engine, never a model.
  Every message says "press Fix here" (`generic_fill.FIX_HERE`), never "your
  own Chrome". Only a captcha
  takes the Worker's own window (Open in Chrome): the tile's clicks are
  synthetic, and Apply never makes one look like a person's.
- **Lisul reports a problem with an open application in a Claude Code chat:**
  send it to the form with `uv run apply ask "<company, role or application
  ID>" "<his words>"` (from `apply-agent/`). Do not open or drive the form
  yourself. `uv run apply ask --list` lists every open form. Print the reply
  to him. Never press the offer's Save for him: only his click in the window
  saves to his sources.
- **After a restart of the Mac:** run `uv run apply reopen` (`docs/restart-recovery.md`). It never
  types into a sign-in: Lisul signs in on each "needs sign-in" tile.
- **A next posting on a job site a running Worker is signed in to:** send it
  into that Worker with `uv run apply rehearse --into`, never into a new
  rehearsal (`docs/plain-workers/guide.md`).
- **Bot detection and captchas:** Apply never evades bot detection and never
  touches a captcha. It hands them to the user.
- **The Fill engine:** run `git submodule update --init` once per checkout.
  Without it, Apply cannot fill a form, and `uv run apply doctor` says so.
  **Read the engine only through `fill_engine.source()`**, never
  `fill_engine.ENGINE` (KAN-836, W7): with `fill_engine: workit`, and always
  in the Student build, the engine is WorkIt's signed download, kept only in
  memory, and no engine file may be written (`docs/fill-engine.md`, "Where
  the bundle comes from").
- **`README.md`** is a teammate's setup path, from a clone to a rehearsal. Its
  steps and doctor's fix lines say the same thing. When you change one,
  change the other.

## Reference by area

Read the file that matches your change. Update it in the same PR: it counts as
this folder's `CLAUDE.md` for its area.

- `docs/fill-engine.md`: Apply's plan rules, `fill_engine.py`, `APPLY_FILL_ENGINE`, or what the plan answers from the Tracker, the Answer bank or a bare date.
- `docs/workit.md`: a WorkIt call, `apply login`, `import-sheet`, `clean-tracker`, `sync-answers` (the Answer bank sync), a Tracker write, the already-applied check, the resume check, or the tailored resume.
- `docs/held-forms.md`: verifying, a flag, Resume, Regenerate, Ask Claude, Fill again (`apply fill-again`), page gates, a held form's job-site session (`keepalive.py`), or how a question reaches Needs you.
- `docs/ask-model.md`: `ask_model`, `ask_model.py` (Groq, Gemini), the lean essay prompts, or another model behind `ask` (`Adapters.claude`).
- `docs/prompts-and-gates.md`: a prompt, a length, cap or names gate, or the catch-all box rule.
- `docs/claude-fill.md`: Claude fill, its Next and profile clicks, its dropdowns, or a Filler's `form_url`.
- `docs/generic-filler.md`: the generic Filler (`generic_fill.py`) and its reader (`form_tree.py`), the Student
  build's Filler for a job system with no Filler of its own.
- `docs/captchas-and-bot-blocks.md`: a captcha wait, a block's handoff, or `captcha.py`.
- `docs/sign-in.md`: a sign-in page, an Employer account or its password (the one Lisul chooses, its rule, Show password), where secrets live (`keychain.py`, `keyring`), the Accounts tab, or `apply preflight`.
- `docs/app-build.md`: building WorkIt Auto Apply (`scripts/build_app.py`), changing what goes into the app, or launching and testing the built app.
- `docs/apply-window.md`: the window's lifetime, its Dock keeper, WorkIt Auto Apply's window with no port (`apply app`, `app_window.py`), or what a Record keeps.
- `docs/restart-recovery.md`: what survives a restart of the Mac: Workers' sign-ins across a quit, the open-forms list (`batch.py`), `apply reopen`, and `apply preflight --open`.
- `docs/plain-workers/guide.md`: `apply/plain/`, `worker_mode`, `--into`, or the worker extension; `docs/plain-workers/worker-extension-todo.md` for its store package and what is left.
- `docs/plain-workers/PROTOCOL.md`: a message between Apply and the worker extension.
- `docs/research/`: the research behind plain Workers, Employer account sign-in, the held form's session keep-alive (`session-timeouts.md`), keeping Workers out of the student's view (`workers-out-of-view.md`: hidden Workers, a virtual screen, F10), held forms in tabs of a CDP Worker (`held-forms-in-tabs.md`, KAN-865 and KAN-876, with `tools/held_forms_tabs.py`: a form behind fills as one in front while Playwright drives it, on every saved form that fills; a window, not a tab, since a Playwright click in a tab behind waits about 2 s; a cap of 4 held forms per Worker on 8 GB), and what a Worker's Chrome crash costs held forms (`held-forms-after-a-crash.md`, KAN-866, with `tools/held_forms_crash.py`: no tab comes back; on Linux a plain Worker with `--no-startup-window` quits at once). Each note's Status line says what was built.

## The data folder (`APPLY_HOME`)

**Personal data is never in the repo.** WorkIt is a public repo. All of a
person's data is in one folder, `APPLY_HOME` (default `~/.config/apply/`):

- the applicant profile, answer bank, story bank, voice and story map;
- the company briefs and stock answers;
- a `policies.yaml` that overrides `policies.default.yaml` key by key.
- the WorkIt login's lock (`workit-login.lock`); the login itself is in
  the system's keychain (`apply-workit`, `docs/workit.md`).
- Apply's Tracker (`tracker.json`) and the writes that wait for WorkIt
  (`workit-queue.json`, and the Answer bank's changes in
  `workit-answers-queue.json`, KAN-746).
- the tailored resumes that Apply gave to forms (`tailored/`, KAN-547).

Apply also writes its output there: rehearsal records, Repairs, Traces and
the Chrome worker profiles (`APPLY_PROFILES`, under `APPLY_HOME` by
default). `src/apply/home.py` derives every data path from `APPLY_HOME`.
WorkIt Auto Apply's own data folder is `home.APP_FOLDER`, each OS's
standard place from `platformdirs` (D25); W5 makes it the Student build's
`APPLY_HOME`.

The repo holds only generic inputs: `policies.default.yaml` (with
`live_runs` off) and the profile template. The Question types come from
WorkIt (`GET /apply-app/types`, `apply.answering`) into the data folder's
`question-types.json` when a run starts; the answering guides live only on
the server (`../backend/app/apply_prompts/answering/`).
When `APPLY_HOME` has no profile, Apply copies the Test Person sample data
into it and the window shows "Sample data".

- Never commit a data file. `.gitignore` here lists each data file name.
- **Agents: never read this folder raw.** Run `uv run apply data keys [FILE]`
  and `uv run apply data show-key KEY [--file FILE]`. They list the keys and
  the shape of each value (`<email>`, `<text, 12 chars>`), never a value. A URL
  keeps only its scheme and the end of its host.
- Apply's own stdout and stderr go through `apply.masked` (KAN-664): the
  profile's and Answer bank's values, addresses, phone numbers, and the ids
  and tokens in a URL are masked. A print that carries a typed answer or a
  message gives only its size (`masked.sized`). Add new prints the same way.
  The one line that skips the mask is `apply login`'s link to WorkIt's
  sign-in page: its challenge is no secret, and the mask hid it.
  Traces and Records are files on this Mac and keep the real values; `apply
  trace` prints through the same mask, which can't catch a value that no data
  file holds.
- To stop raw reads in Claude Code, install
  `tools/block-apply-home-reads.sh` as a PreToolUse hook. Nothing installs it
  for you. In `~/.claude/settings.json`, with the path to your checkout:

  ```json
  {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
    "command": "/path/to/apply-agent/tools/block-apply-home-reads.sh"}]}]}}
  ```

  It refuses `cat`, `grep`, `sed`, Python and other readers on
  `~/.config/apply` or `$APPLY_HOME`. It can't see a path that is built at run
  time.
- For a test run, set `APPLY_HOME` and `APPLY_PROFILES` to a scratch folder,
  so the run does not write into your real data folder.
- `apply rehearse`, `apply run` and `approve-pass` refuse an `APPLY_HOME` or
  profiles folder under a temp path (`/tmp`, `/private/tmp`, `/var/folders`,
  KAN-665), since a reboot wipes held forms and sign-ins there. Test Person
  (`sample_data: true`) and tests (`APPLY_TEST_TEMP_OK`, set in `conftest.py`)
  go on. Use a scratch folder under your home folder for a rehearsal.

## Testing

- **Never run the full test suite (`uv run pytest` over all of `tests/`)
  for a small change.** It takes more than 20 minutes. Run it only for a
  major change that touches many modules, and say why.
- Run only the tests that the change touches, with `-k`. For example,
  `tests/test_workday_filler.py` alone takes about 5 minutes; do not run
  the whole file again after each small fix.
- Run `uv run ruff check .` here before you commit. It uses the backend's
  ruff config. `pyproject.toml` lists the findings that Apply keeps on
  purpose, each with its reason.
- CI (the `apply-fast` job in `../.github/workflows/ci.yml`, on Ubuntu)
  runs ruff and only a fixed list of fast test files: the files that need
  no browser, no network and no `claude` CLI. When you add a test file that
  needs none of them, add it to that list. Only the browser tests run on
  macOS (`apply`, `apply-hostile`), since the organization has few macOS
  runners (`../.github/CLAUDE.md`), and a change to only the student page
  or the docs starts neither. Its test steps run in parallel
  (`pytest -n auto`), so a new test there can't share a fixed port or
  path with another. A test of `rehearse` with `keep_open` picks out the
  lines it checks, and never counts all it printed: when a form's thread
  is still running as the first line prints, the run also says "Apply
  submitted nothing", and a test that unpacked every line failed 5 runs
  in 400 on a busy machine (2026-11-14). CI also installs Chrome for Testing and runs
  `test_plain_guards.py` and `test_plain_routing.py` on a real plain Worker.
  The hostile pages run in a job of their own beside it, `apply-hostile`.
  CI never runs the Filler tests (`test_*_filler.py`, `test_claude_fill.py`
  and the other files that open Chromium). Run the ones that your change
  touches on your Mac, with `-k`.
- **Every test earns its place: one scenario, and a fault it alone turns
  red** (KAN-780: the hostile pages' 495 PR cases became 220 and still
  catch every fault they caught). A fault is a guard check switched off, a
  path's branch broken, a page's trick no other test holds. Before you add a
  test, a hostile page, a path or a timed copy:
  1. Name its fault in its comment.
  2. Find the tests that already go red on that fault: put the fault in
     (switch the check off, break the branch) and run the PR cases of the
     files it touches. When one goes red, extend that test, or add nothing.
  3. Give it the place its kind has. A page of a known kind joins its set
     (`APPLIES`, `OWN`) and runs once on PRs, on its own path; its other
     pairs go nightly by themselves. One delay per scenario: a hold that
     lasts past T stops every page that sends later than T, so a copy at
     another delay is the same test, slower.
  4. Wait on the event: a request, a selector, a flag the page sets
     (`window.saving === 0`). A hostile page's late send waits `wait_ms` on
     its clock (`LATEST` for a timer with no number). A fixed time is for a
     scenario that is itself timed (a hold, a tile's retries), and says so.
  5. Run it where its kind runs: no browser in the fast list (port 0, its
     own `tmp_path`); CDP in a parallel step; a plain Worker in the
     one-process step, or `xdist_group("plain-worker")` in a parallel file,
     since plain Workers side by side miss their timing.
  6. Keep it on PRs. A test runs only nightly when a fault run shows a PR
     test goes red on every fault it does, or when it reads only files a CI
     filter watches and the filter runs it on their change (the hostile
     controls, `CONTROLS_ON_PRS`).

  Done when its comment names the fault, the test goes red with that fault
  in, and the file's no-browser self-checks pass.
- **The submit guard's hostile pages** (`tests/test_submit_guard_hostile.py`,
  KAN-666) run every click path that presses through the guards (plain
  code's Next, the profile click, the account click, Ask Claude's press,
  the keep-alive's stay-signed-in press, Fill again) against pages built to
  trick them. Every pair must send no
  application request. A new click path joins `PATHS`, and a new trick joins
  `PAGES`, in the same PR. A pair runs only where its path looks for
  something the page holds (`APPLIES`): the four paths that press a form's
  own button take every page, the profile click only the profile pop-ups,
  Ask's press of a listed step only pages with a step list, and the
  keep-alive's presses only the session dialogs. Anywhere else the path finds
  nothing, and the pair is the guarded page sitting still: 312 of the 728
  pairs were, and 12 pages' only PR pair was one (KAN-780, 2026-11-14, found
  by recording what each pair's path pressed). A new page of one of those
  kinds joins its set; a new path that looks for its own kind of element
  gets a set. CI runs its no-browser cases, each page once on CDP on its
  own path (`PATH_FOR`, else its kind's in `OWN`, else Ask Claude's press,
  which pressed on all 91 pages), and on a plain Worker the first page, each
  path once and each `PLAIN_HOLES` page; the other pairs are marked
  `nightly` and run in `apply-nightly.yml` (KAN-780). Guard holes once ran
  on every path on PRs: a mutation study (2026-11-14: 24 faults, each one
  guard check switched off with the network rule off) found that on 54 of
  the 56 hole pages one path caught every fault the page's other paths
  caught, and the one-per-page set still catches every fault any case did.
  A page whose hole only some paths reach goes in `PATH_FOR`. A no-browser
  test fails on a pair whose path doesn't apply and on a page or path with
  no PR case.
  A case waits for the page's own late send as long as its latest timer
  and a second more, 1.5 s for a page with none (`wait_ms`; `LATEST` for a
  timer whose delay is no number), where every case once waited 3 s:
  unguarded, 78 of the 91 pages sent within 0.5 s. **On CDP the page keeps
  that time on Playwright's clock** (`cdp(clock=True)`, `_run_out`; KAN-780):
  time flows as unfaked while the path presses, then the clock moves through
  the wait in 250 ms steps, each with 50 ms of real time for the requests a
  timer made, and 0.5 s more at the end. A 1.5 s wait takes 0.8 s and an
  11.5 s one 2.8 s, and a busy runner can't push a timed send past its wait.
  Unguarded, each of the 87
  pages sent on it as on real time, or more (timers that never ran on real
  time, since the page had left, now run before it leaves). A mutation run
  (2026-11-15: the 25 guard faults on the 81 CDP PR cases, on each clock)
  found each fault caught by the same cases on both clocks, but two that timed
  out on a click on real time and failed on the sent application on the
  clock. Playwright's clock replaces
  `performance`, and the guard's `now()` throws on it, so a CDP guard reads
  no clock: `test_a_cdp_guard_reads_no_clock_a_page_can_fake` fails once it
  does. A plain Worker has no such clock and waits in real time, as do the
  held-page tests, whose hold is Python's, and **a page whose send waits on
  what the clock never moves** (a worker's timers, the scheduler's delay, an
  animation, a refresh, a socket: `REAL_TIME`, found by its words, today the
  6 worker pages): on the clock a worker's 4 s timer got 1.6 s of real time
  and its post never came (the adversarial review of #583). A wait whose
  clock fails to move in any step gets the whole wait in real time, so a page
  can't skip its own timers by breaking the clock. A page's control waits on the same
  clock as its cases, so a page that sends later than its wait fails its
  control, never passes unseen. The control runs no Apply code: PRs run three
  (`CONTROLS_ON_PRS`, a check that the runner leaves the real time the wait
  needs), every control when the PR changes what the control reads (`ci.yml`'s
  `hostile_pages` filter: this file, the fake site, `uv.lock`, the setup), and
  the nightly workflow the rest. A new page whose send needs more real time
  than these joins `CONTROLS_ON_PRS`. The session pages that send after 3 s
  (`HELD_ONLY`) are in no matrix: there the guard is on throughout, so they
  were the plain dialog's pair again; their scenario is the held-page
  tests'. One timed copy per dialog kind, at 10 s: a hold that ended after
  T seconds lets through any page that sends later than T, so the 3.5 s and
  60 s copies added nothing but a minute each. Which test runs only nightly:
  "Every test earns its place", above. A guard PR gets an adversarial review first (root `CLAUDE.md`).
  A page loads with no guard and is then guarded and reloaded, unless it
  sends by itself from the moment it loads (a timer, before any press):
  such a page joins `SENDS_AS_IT_LOADS` and is guarded before its first
  load, as a rehearsal opens every page. Loaded first, its timer posted
  before the guard was on on CI's slow runner, and its post moved the
  page during the guard's reload (`net::ERR_ABORTED`, 2026-11-14).
- **The guards read the page only through built-ins taken before any page
  code** (KAN-710, KAN-783): the guard script's own (`fn`, `get`, `test`,
  `up`, `formOf`, ...), and `apply.natives` for the reads that also run on
  their own (`PROFILE_DIALOG`, `send_click.ELEMENT`; the drive guard takes
  the natives for Ask's read as it starts). A page's getter that throws or
  lies, a Proxy prototype, or a replaced built-in sent an application when
  a guard read `el.innerText` directly. A new read uses one of these, never
  a property of the page's object, and a new listener that judges a press
  goes through `judged` (a throw blocks). A request's URL, method and body
  are read once, and what was judged is what is sent: an XHR keeps what its
  `open()` took, and one opened by no `open()` of the guard's is not sent.
- **A GET form's submit reaches none of the page's handlers while a guard
  is on** (KAN-868). A form with no method whose own submit handler posts
  the application (a React form's onSubmit, by fetch to any URL) sent it past
  both guards when a press of anything else of the form's submitted it: a
  Next, a dropdown made of a submit button, one the page turned into a submit
  button as it was pressed (the adversarial review of KAN-861). A test of the
  form's buttons was got round each way the review of KAN-868 tried: a
  Submit the press renamed, blanked or took away, one renamed on pointerdown,
  one outside the form with no `form=`, a `<div>` of no role, words only in
  CSS. So every submit of a form that doesn't POST is stopped: a GET form's,
  and a dialog's, whose submit runs the page's handlers all the same. Only a
  sign-in step goes on, and only under plain code's own sign-in press
  (`apply.account_pages`, `let_account_click(sign_in=True)`, never a Next's
  account click): its only boxes are an email or user name and passwords
  (iCIMS's email step), and the page shows no other answer box anywhere, an
  editable box, a radio, a tick or one in an open shadow root too (rounds 2
  and 3 of the review put the answers outside the form). The residual: an
  app whose answers a script holds, behind one email box, looks like a
  sign-in step under that press. A wizard whose Next submits a GET form is a
  step no code or model presses: a Handoff, the student's on the held page,
  whose own press goes through as before. A form in a shadow root the page
  wrote is heard as a script submits it, clicks in it or dispatches an event
  in its root, and a closed one as its element's internals hand it over
  (`hearRootOf`), as one a press passes through always was; an open one as
  a script first reaches it (`shadowRoot`, `getRootNode()`, an event's
  `composedPath()`), so the guard's listener there is the first. That
  order can still be beaten from inside a root (a custom element in it
  that listens on its root as it connects: round 4 of the review), so the
  press itself is stopped too: a click on a submit button of a form that
  doesn't POST is cancelled at the window, before any of the page's
  listeners, and a script's `requestSubmit()` of one is refused. The sign-in
  step's page check also reads same-origin frames and every root the guard
  has heard, closed ones too. Whenever page code adds a `submit` listener,
  the guard first hears that node's root (the `addEventListener` wrapper),
  so code inside a root that walks up to it can't get there first, and an
  Enter that submits with no click is stopped there (round 5). Plain
  code's sign-in with a password goes on for a form that doesn't POST only
  under Apply's own sign-in press and as a sign-in step: an application
  that makes an account as it applies is a GET form with a password box. The guard
  scripts are one function each, built from shared parts: a name two parts
  declare stops the whole script with no error Apply sees, and every page
  is unguarded. That happened twice while KAN-868 was built;
  `tests/test_guard_scripts_compile.py` (CI) compiles each script.
- **A request body is read as its server reads it, never by a regex on
  its text** (KAN-791). One regex on Ashby's `operationName` let through
  escaped JSON, a submit named only in `query`, a batch, and form or
  multipart bodies. The guard parses each body to Ashby (JSON with no
  duplicate key, form fields, multipart `operations`), parses each
  query as GraphQL, and blocks a mutation whose root field names a
  submit. A body to Ashby's GraphQL that it can't read is blocked: when
  the guard can't tell, it fails closed.
- **A guarded page makes no worker** (KAN-791). A worker runs none of
  the guard script, so a Web Worker, a shared or service worker, or a
  blob: or data: worker script posted the application past both guards.
  While a guard is on, the script refuses `Worker`, `SharedWorker`, a
  service worker's `register` and a worklet's `addModule`, and ends a
  dedicated worker made while the page was lifted when the guard comes
  back on. On a CDP Worker, `_end_workers` closes the shared workers and
  unregisters the service workers as the guard goes on (Playwright
  routes no shared worker's request). On a plain Worker, the rules on
  -1 block the final URLs and Ashby's GraphQL from them. A new way to
  run code outside the page's realm needs the same three layers.
  **A refused worker the page made is no Handoff** (KAN-839,
  `submit_guard.drive_blocks`): the page's code made it, not a model's
  click, and the refusal sent nothing, so Claude fill, Rescue and Ask
  Claude go on past it while the worker stays refused. As a Handoff it
  stopped every SmartRecruiters form, whose page makes one as it opens.
  Every other block while a model drives is still a Handoff.
- **A captcha's frame is known by its host, or by its path only on
  reCAPTCHA's own host** (`captcha.PATH_HOSTS`, KAN-791). The guard
  leaves a captcha's frame alone, and it took any frame at `/recaptcha/`
  for one. A page served that path from its own site or another one, and
  the frame posted the application, or the page did through its `fetch`
  and `Worker`.
- **A file goes only to the form's own site** (KAN-795, `apply.upload_origin`,
  `docs/claude-fill.md`): the top frame, a frame of its origin, or a job
  system's embedded form, with every frame between it and the top of the
  top's own origin. A hostile page's frame from another site could take the
  resume when nothing checked where a file went, and PR 556's review found
  five more ways past the first fix (a form inside another site's frame, a
  dispatched click, a closed shadow root, a scriptless frame, a pop-up), and
  its re-review four more. So while a guard is on, a frame that may not take a
  file is closed to every press, Claude's too: a narrower block was got round
  each time. Every new way to set a
  file goes through `upload_origin.give` (CDP) or the worker extension's
  checked sets (plain), and each new trick joins `tests/test_upload_origin.py`
  on CDP and on a plain Worker. The rule's JS copies (page/dom.js,
  ops/tile.js) stay word for word the same as `RULE_JS`; a test checks that.
  The guard's picker block is guard code: its PR gets an adversarial review.
  The rule covers an answer's text too where Apply fills one field in a held
  page's frames (`rehearsal._engine_fill`, `regenerate.done`): only a frame
  that `upload_origin.frame_may_upload` allows. Another site's frame with its
  own `FillEngine` took a resume's bytes (KAN-855's review). The top frame
  passes the rule whatever site it is on, so those fills also check that the
  tab is still on the form's own origin, as Apply handed it over.
- **No test reaches past loopback** (`tests/network_block.py`, KAN-662). A
  socket or name lookup to another host raises `NetworkBlocked`, Chrome
  started by a test resolves other hosts to nothing, and Playwright's own
  requests are refused. The test then fails, even if it swallowed the error.
  A test that goes live on purpose names its hosts:
  `@pytest.mark.live_network("example.com")`. A program that a test starts
  other than Chrome (`curl`, `gh`) is not covered, so fake those.
- **No test reaches the system's keychain** (KAN-838). `conftest.py` puts
  keyring's null backend in place, so a `SystemKeychain` that a test gave
  no backend reads nothing, and its save fails. Pass `InMemoryKeychain` or
  a fake backend. Only `test_keychain_contract.py` with
  `APPLY_TEST_KEYCHAIN=1` touches the real one (`docs/sign-in.md`).
- **No test reads a real model key.** A test that builds the hosted models
  (`ask_model.live_claude`) gives them stand-in keys in their environment
  variables (`GROQ_API_KEY`, `GEMINI_API_KEY`), which come before the
  Keychain and the checkout's `.env`. The `.env` holds the team's real key,
  so `test_student_build.py` passed on a Mac and failed on CI, which has no
  key (2026-11-15).
- **Every Chrome a test starts closes when its test process ends, finished
  or killed** (`tests/chrome_reaper.py`, wired in `conftest.py`). A plain
  Worker's Chrome runs on its own (`launcher.start_in_background`), and pytest
  runs that a timeout, a stopped task or a second Ctrl-C ended left their Chrome
  for Testing windows open: five of them (2026-11-15). conftest lists each
  Chrome's profile before it starts: every `start_in_background`, and every
  Chrome command started through `subprocess` with a `--user-data-dir`. A
  reaper outside the test process's tree (a stopped task kills the whole tree)
  hears that process end through a pipe, however it ends, and stops each
  listed browser still running, a fixture's leftover too. A new way a test
  starts a browser outside those two calls `chrome_reaper.watch` itself. Test
  runs leave their `/tmp/apw-*` folders, finished or not; the reaper stops
  processes only.
- **Prove a fix on the real form.** Rehearse the job posting that showed the
  bug (`uv run apply rehearse <url>`) and read its record. A rehearsal never
  submits. A unit test that passes is not the check that matters; the live
  form is.
- **Never press Submit** on a form, and never turn on `live_runs` for a
  test. A rehearsal leaves the browser open on the last page; leave it
  there.
- **Never press a button after an Emailed code.** On a page held for Lisul,
  `email_code.py` types the code that a job system emails after his own
  Submit, and nothing more (`test_email_code.py` checks that it has no click
  or key press). Test it on the fakes only: never press Submit on a real
  posting to make a code come. Two held pages whose lookups overlap on the
  same senders type neither code (`_join`, `CROSSED`): Greenhouse mails
  every company's code from one sender, and the newest mail after each press
  could be the other page's.
- Kill only the processes you started, by PID. Other people's rehearsals
  can run on the same Mac.

## Repairs

A Repair is Claude's fix to Apply's own code for a fill bug (`GLOSSARY.md`,
`docs/adr/0002`). Repairs are off: `policies.default.yaml` sets
`repair.max_per_day: 0`. When you turn them on in your data folder, a Repair
merges into the branch Apply runs from (or `repair.branch`) and pushes to
this checkout's `origin`, the WorkIt repo. It also moves the engine pointer
`autofiller_extension/fill-engine` on that branch, which is the extension's
pointer too. A Repair never runs on `main` (`repair_waiting` refuses it):
its pushes would move fill-engine's `main` and WorkIt's `main` to code
Claude wrote, and only WorkIt's `main` is protected.

## The app's license and notices

WorkIt Auto Apply ships with two legal files (W10 of
`../docs/desktop_application_auto_apply.md`, KAN-848). Both stay in this
folder, so they move with Apply to `workitjobs/apply-agent` (W0) and the
app's build (W8) finds them.

- **`legal/EULA.txt`** is the app's license. It is adapted from
  Basecamp's open-source policies under CC BY 4.0: keep its Credits
  section, which is the attribution that license needs. WorkIt's
  `/terms` sums it up (`../frontend/src/app/(landing)/terms/page.tsx`):
  change the two together, and only with the team's yes.
- **`THIRD-PARTY-NOTICES.txt` is made, never kept**: `uv run python
  scripts/third_party_notices.py` writes it to `dist/` from `uv.lock`.
  Never add a Python package to it by hand: a dependency in
  `pyproject.toml` joins it on the next run, and a dev dependency never
  does. Code that ships without a Python package (a macOS framework, a
  font, Nuitka's runtime) joins `BY_HAND` in the script, with its license
  text in `legal/licenses/`. The build runs the script with `--strict`
  (`build_app.py --release`), which fails while a text is missing. The
  build runs it on its own Python with `UV_PYTHON` set to it, so the
  notices name the Python the app ships: on uv's first-found 3.12 they
  named Anaconda's 3.12.2 for an app that ships 3.12.14 (2026-11-24).
- **A text in `legal/licenses/` is the shipped version's own, unchanged**
  but for LF line endings (KAN-833, 2026-11-21): the student page's
  packages at `window/package-lock.json`'s versions (each package checked
  against its `integrity`), Nuitka's from the wheel the `build` group
  pins, the GUST Font License from the URL `src/apply/fonts/README.md`
  names, and Sparkle's from release 2.10.1. A version change copies the
  text again in the same PR; Sparkle's when W8 step 3 bundles a release
  other than 2.10.1.
- **A change to what the app sends off the Mac** (a model call's data, a
  new WorkIt route, a new outside service) updates the WorkIt Auto Apply
  section of `/privacy` in the same PR (`../frontend/CLAUDE.md`, the legal
  pages).

## Building the app

`python3 scripts/build_app.py`, on an Apple Silicon Mac, builds WorkIt Auto
Apply into `build/out/WorkIt Auto Apply.app` (KAN-833, W8 of
`../docs/desktop_application_auto_apply.md`). Its docstring lists the steps.
Any teammate's Mac builds the same app: it needs only Xcode's Command Line
Tools, uv and the network, and any `python3` runs the script, macOS's own
3.9 too (standard library only; checked 2026-11-21 in an empty environment
with only the system folders and uv on the `PATH`).
The app has only the compiler's ad-hoc signature, so it opens on the Mac
that built it and nowhere else until step 2 (Developer ID and
notarizing). Sparkle (step 3) is in every build. A release is built,
signed and published only by `../.github/workflows/publish-app.yml` on a
GitHub Mac (step 4, D32), never on a person's computer. `--release` makes
the notices strict (above).

- **What ships is decided in three places only**: `INPUTS` and `LEAVE_OUT`
  in `scripts/build_app.py`, and `build.DEVELOPER`; beyond those, the
  modules the Student path imports and every non-Python file in
  `src/apply`. Remove a file from `INPUTS` only after the code stops
  reading it, then launch the built app: the build doesn't check what the
  code reads, and a missing input crashes the app when it runs. How to
  change each list and how to test the built app: `docs/app-build.md`.
- **A release builds from the commit, never the working tree** (KAN-833,
  2026-11-21). `--release` exports the current commit's files of this
  folder with `git archive` into `build/source` and builds from there, so
  an untracked or uncommitted file can't get in, and says when the working
  tree has changes it leaves out. Only the inputs come from the commit: the
  build script itself runs from the working tree, so a release refuses to
  start while `scripts/build_app.py` has uncommitted changes, which would
  decide what the app holds while `WorkItCommit` names another commit. Before, Apply installed from its folder
  with every untracked file in it (hatchling takes any file git doesn't
  ignore), Nuitka shipped every data file of the package, and the inputs
  were copied as whole folders: a test file in `src/apply` went into the
  wheel. Every build writes its commit into `Info.plist` (`WorkItCommit`,
  with `+changes` on a test build of a changed working tree), so a report
  names the code it came from. `git archive` runs from the repo's top
  folder: run in a subfolder, it keeps only paths under that folder,
  inside the exported subtree too, and exported nothing.

- **The build has its own venv, `build/venv`**, from `uv.lock` with uv's
  own Python 3.12 and the `build` group (Nuitka), never the checkout's
  `.venv`: its Python can be Anaconda's or Homebrew's, which differ per
  Mac. It installs Apply as a copy and sets `STUDENT = True` there, so the
  checkout's `build.py` stays False. uv puts that Python in
  `/Users/Shared/workit-auto-apply-build/python` (`PYTHON_HOME`), never in
  its default `~/.local/share/uv`: the app carries the Python's install
  path (its `sysconfig` settings and `libpython`'s own name), and from the
  default place every copy held the builder's user name (2026-11-21). The
  build refuses an app whose own files (the program, `libpython`, the
  capture helper) hold the builder's home folder path. Only those: third-party
  files carry their own builders' paths (`/Users/admin` in Node,
  `/Users/runner` in cffi), and a check of every file refused a teammate
  whose home folder matched one.
- **It compiles with Apple's tools and nothing from the shell** (found
  2026-11-21). Homebrew's LLVM exports `CPPFLAGS` and `LDFLAGS`, and Nuitka
  passed them on: the first build linked Homebrew's `libunwind`, which a
  student's Mac lacks. With Anaconda first on the `PATH`, Nuitka ran
  Anaconda's `install_name_tool`, which failed. So the script drops every
  compiler variable (`COMPILER_ENV`), runs Nuitka on `/usr/bin` only, and
  sets `SDKROOT`: the clang `xcrun` names finds no `stdlib.h` without it.
  It drops every `PYTHON*` variable too: `PYTHONPATH` comes before the
  venv, so a teammate's could make Nuitka compile the checkout's Apply or
  another copy of a library. `--release` also compiles with no ccache
  (`--disable-cache=ccache`): on a Mac with Rosetta, Nuitka downloads it
  from nuitka.net with no hash check and runs it on every C file.
- **No docstrings in the app.** Each one is a plain sentence about how Apply
  works, and Nuitka keeps it as text in the program. The build passes
  `no_docstrings` and checks that a known docstring is gone, so code on the
  Student path must work with `__doc__` as None. Asserts stay: `launcher.py`'s
  `NEVER` check is one.
- **No JavaScript comments in the app's page code, and all of them in the
  checkout.** Comments in Python vanish when it compiles, but JavaScript in
  a Python string kept them (the tiles window's page code, for one), so the
  build strips its own copy (`scripts/strip_js_comments.py`). It changes a
  piece only when Node parses it the same way before and after, keeps a
  comment that names a license, and never touches `STORE_CODE`, the modules
  whose page code goes into the Worker extension's store copy: the
  extension checks those files by sha256, and the guards are public there.
  The build then checks that the store copy's files are the same, and fails
  if not: `upload_origin` was missing from `STORE_CODE` and failed it
  (`RULE_JS` goes into the guards). A module that a new fixed function or
  guard takes code from joins `STORE_CODE`.
- **The app has no checkout and no Python.** `home.CODE` is the program's
  own folder when the module is compiled (`__compiled__`), and the build
  puts the inputs the Student path reads there (`INPUTS`: the EULA, the
  default policies, the Worker extension; and the notices). A new file the
  Student path reads beside the code joins `INPUTS`. The Worker extension's
  folder, which the seed setup copies for Load unpacked, is there only for
  now: it shrinks to what the store copy needs once W6 ships it. The Test
  Person sample (`sample/`) is not in the app (2026-11-24): a student's app
  has no Test Person, and its data comes from WorkIt (W11). Until W11 stops
  `student.app` from copying it (`home.fill_from_sample`), a built app whose
  data folder has no Applicant profile stops at launch, since the sample it
  copies isn't there. A plain
  Worker's wrapper starts the app's own program as the relay
  (`launcher.host_command`, `scripts/app_entry.py`), never `python3 -I
  host.py`. It names that program with `psutil.Process().exe()`, never
  `sys.executable`: in a Nuitka program, `sys.executable` is a `python`
  beside the program that doesn't exist, and the first wrapper named it
  (found in review, 2026-11-21). A new place that starts the app's own
  program needs the same.
- **The build refuses an app** that compiled a module in `build.DEVELOPER`,
  holds a `.py` or `.pyc` file, or still holds docstrings or page code
  comments. The checks look for text read from the build's copy before the
  compile (`PROBES`), never text typed into the script, which a reworded
  docstring would turn into a check that always passes. Nuitka's report
  (`build/out/report.xml`) lists every module it compiled and why.
- **The build ends with the DMG**, `build/out/WorkIt Auto Apply.dmg`: the
  app (copied with `ditto`, which keeps its signatures), a link to
  Applications, and `License.txt` and `Third-Party Notices.txt` beside them
  (W10). The build mounts it read-only and refuses one whose app fails
  `codesign --verify` or has no Applications link. A failed or refused build
  leaves no DMG: the build deletes the last one when it starts.
- **The app's icon is `assets/app-icon.png`**: WorkIt's logo at 1024 px on
  Apple's macOS icon grid, an 824 px shape with a transparent margin, so it
  shows at the size of other apps' icons (the logo filled the whole canvas
  and stood about a quarter bigger). The build makes the `.icns` from it
  with `sips` and `iconutil` (`make_icon`). `src/apply/Apply.icns` is the
  developer's Dock icon (`dock_app`) and stays out of the app (`LEAVE_OUT`).
- **Updates are Sparkle 2.10.1** (W8 step 3, KAN-941). The build
  downloads the pinned release once into `build/sparkle-2.10.1/`, checked
  against `SPARKLE_SHA256` (its `bin/` holds `generate_keys` and
  `sign_update`), and puts `Sparkle.framework` in `Contents/Frameworks`
  without the XPC services (for sandboxed apps only), headers and module
  maps. It writes the settings: `SUFeedURL` (`FEED`,
  `https://downloads.workitjobs.ai/appcast.xml`), `SUPublicEDKey`
  (`SPARKLE_PUBLIC_KEY`, made on 2026-11-26), checks and installs with no
  question asked, and the EdDSA check before unpacking. **Never change
  `FEED` or `SPARKLE_PUBLIC_KEY`:** every app keeps both for good, so after
  a change no installed app updates again. `apply.updates` starts Sparkle's
  updater once the run loop runs; an app built before the key (2026-11-26)
  has no framework, and it starts nothing. A new Sparkle
  version changes `SPARKLE_SHA256` and `legal/licenses/Sparkle-LICENSE.txt`
  in the same PR. Tested on 2026-11-24 (`docs/app-build.md`, "Test an
  update"): with ad-hoc signatures, an older build found, downloaded and,
  on quit, installed a newer one; one signed with another key was
  downloaded and refused.
- **Only a release is published, and only from a GitHub Mac** (W8 step 4,
  KAN-941, D32). `../.github/workflows/publish-app.yml`, run by hand from
  `main`, builds with `--release`, then `scripts/publish_app.py` signs the
  DMG with the update key, which it gets from the environment and gives
  `sign_update` on stdin, and writes the feed (one item, the newest
  build); the workflow uploads both to R2 (`../.github/CLAUDE.md`). The
  script refuses a test build (`WorkItRelease` false in `Info.plist`),
  which can hold untracked files and incomplete notices, and a key whose
  signature the app's `SUPublicEDKey` rejects (checked with
  `cryptography`, as an app checks it), which every app would download and
  refuse. It reads the feed back with ElementTree and refuses one Sparkle
  couldn't read or that offers another file. **It never prints
  `sign_update`'s output on a failure:** its error repeats the key it was
  given. No developer holds the key: a test build signs nothing. How to
  publish: `docs/app-build.md`.
- **`CFBundleVersion` is the build's UTC time** (`YYYYMMDDHHMM`), so it only
  grows: Sparkle offers an update only when the feed's number is higher
  than the app's, and `pyproject.toml`'s version, the one the student sees
  (`CFBundleShortVersionString`), stays the same over many builds. Not a
  commit count: that drops when W0 moves Apply to its own repo, and it
  differs between branches.
- **Nuitka puts the data files in `Contents/MacOS`**, beside the program, and
  names the bundle after the entry file; the script renames it, adds
  `LSMinimumSystemVersion`, `CFBundleURLTypes` (the app claims
  `workit-auto-apply://`, WorkIt's sign-in link, `sign_in_link.SCHEME`) and
  `NSAppleEventsUsageDescription` (FocusKeeper's `osascript` sends System
  Events an Apple event as the app, and with no reason macOS refuses it
  and never asks), and
  signs it ad hoc again, since the edit breaks Nuitka's signature. The app is about 227 MB, Playwright's driver 128 MB of
  it.
- **The app ships the window capture helper**, `window-capture` beside the
  program (`window_capture.BUNDLED`), which the build compiles with `swiftc`
  for macOS 13 and checks with `--check`. A Developer checkout builds it on
  first use, but a student's Mac has no `swiftc`: without the shipped one,
  every live tile took the slow captureVisibleTab path. The `.swift`
  source stays out of the app, as do `plain/mcp_tools.json`, the tools
  Claude drives a page with, and Playwright's web UIs (`lib/vite`: its
  trace viewer, HTML report, recorder and dashboard, which Apply never
  opens; its driver starts Chrome without them). They are `LEAVE_OUT`,
  and the build refuses an app that holds any of them. The helper is the app's child process, so
  it has the app's own Screen Recording permission. macOS keys that
  permission to the app's signature: with the ad-hoc signature, each new
  build asks again; a Developer ID signature (step 2) keeps it across
  updates.

## The privacy gate

`scripts/privacy_gate.py` scans the files for personal data (phone numbers,
email addresses, street addresses, student IDs, links to private repos) and
for secrets (API keys, GitHub and Slack tokens, private keys, cookies).
The identifiers it looks for come from a local file outside the repo
(`private-identifiers.txt`), never from the repo.

Run it before you push any file that you copied from a personal checkout.
If it finds something, remove it; do not push and fix later. A pushed file
stays in the public history.
