# Desktop application for auto apply (KAN-723)

**Status (2026-11-08):** plan, not built. One decision is built: Apply's
Workers default to `worker_mode: protected`. Everything else here is a
plan. Apply's own folder is `apply-agent/`; its rules are in
`apply-agent/CLAUDE.md`, and its terms are in `apply-agent/GLOSSARY.md`.

This note records a design talk about how Apply works today and how to make
it a downloadable app. It explains the system from the ground up first,
because each part of the plan replaces or keeps one of those parts.

## 1. The decision

WorkIt will offer auto apply on two paths:

| Path | What it is | Who it is for |
|---|---|---|
| **Extension path** | The WorkIt Chrome extension (KAN-164) fills forms in the student's own Chrome. Its answers come from WorkIt or from the student's own Claude, through WorkIt's MCP server (the connector, KAN-377). | Most students. No install beyond the Chrome Web Store. It has the limits of an extension (section 4). |
| **Desktop path** | Apply as a downloadable desktop app. It runs its own Chrome Workers, fills many applications at once, and shows the Apply window. | Students who want many applications run for them, with the most control. |

On the desktop path:

- **WorkIt is the source of the student's data.** The profile, the answer
  bank, the stories, the resumes and the tracker come from the WorkIt app
  over HTTP. The answer bank's new design is owned by a teammate (section 9).
- **The desktop app only runs auto apply.** The student uses it to watch
  progress, do each captcha, check the answers and press Submit. All other
  work (the bank, the resumes, Tailor, the tracker) stays on the website.
- **Workers default to `protected` mode** (section 6).

**The rule for bot checks stays as it is:** Apply never evades bot
detection and never touches a captcha; it hands both to the student
(`apply-agent/docs/plain-workers/PROTOCOL.md`, `captcha.py`). The goal of
the desktop path is the fewest *false* blocks, the blocks that come only
from the automation channel. It is not to get past a site that decides to
block a bot. A real block goes to the student's everyday Chrome, where the
extension fills it.

## 2. How Apply works today

### 2.1 What it is

Apply is a Python package (`apply-agent/pyproject.toml`, entry point
`apply = "apply.cli:main"`). `uv sync` installs it into `apply-agent/.venv`.
Nothing is packaged for download. It runs only on macOS.

`~/Applications/Apply.app` is not a real app. Apply writes it each time it
opens its window (`dock_app.py`): an `Info.plist`, an icon and a short shell
script. The script either starts Chrome on the Apply window, or runs
`python -m apply.cli watch` from the checkout that last opened the window.
It exists only so that the Dock shows "Apply" and not a second "Google
Chrome". It holds absolute paths to one Mac's checkout, so it cannot be
shared.

### 2.2 The processes in a rehearsal

```
terminal: uv run apply rehearse <links>
 └─ Python (Apply)
     ├─ web server on 127.0.0.1   ← the Apply window (Chrome --app) calls it
     ├─ Node (Fill engine)        ← reads question sets, plans, checks
     ├─ Chrome worker-1, -2, -3   ← one process, profile and window for each Worker
     └─ claude -p (many, short)   ← text in, JSON out, then it exits
         └─ npx @playwright/mcp   ← only for Claude fill
```

Apply does not run inside Claude Code. It runs the `claude` command as
separate subprocesses, on the user's own login.

### 2.3 One Application, step by step

1. Resolve the link: the hiring system, the company, and a Greenhouse,
   Lever or Ashby form inside a careers page.
2. Check whether the student already applied. If so, stop.
3. Get a tailored resume from WorkIt, if the posting has one.
4. Read the posting's text, by API or a plain fetch, with no browser.
   Plain code checks eligibility, and checks for text aimed at AI agents.
5. Read the question set. The Fill engine reads it from the hiring
   system's API (Greenhouse, Lever, Ashby). The Workday Filler signs in and
   reads it from the page. Claude fill reads it on a site with no Filler.
6. Open the form. The submit guard goes into every page before the site's
   own code.
7. The engine's planner answers the routine questions from the profile and
   the answer bank. Missing facts go to Needs you at once.
8. Claude writes what is left (section 3).
9. Plain-code gates check each essay: caps, names, not-on-resume.
10. The engine fills the form in the page, then reads every field back. If
    the read-back is wrong, Sonnet re-plans once and the form is filled
    again.
11. Verify: plain-code checks, then a Haiku Pre-submit review.
12. A rehearsal stops on the last page and writes its Record. The page
    becomes the student's: they can answer, press Resume, or press Submit
    themselves.

### 2.4 Who reads the questions

The Fill engine reads them, not Claude. Claude gets only the questions the
planner could not answer. The one exception is Claude fill, on a site
Apply has no Filler for.

```
question set ─► engine planner ─┬─ answered from profile + answer bank
                                ├─ Missing facts ─► Needs you
                                └─ essays + one-off questions ─► Claude (text)
                                                                   │
                                     gates (plain code) ◄──────────┘
                                          │
                                          ▼
                              one plan ─► the engine fills the page
```

The engine is a JavaScript bundle (`autofiller_extension/fill-engine/dist/engine.js`),
the same build the WorkIt extension uses. Python runs it in a long-lived
Node process (`fill_engine.call_without_page`) and inside each page
(`page.evaluate`, or the worker extension's ops).

## 3. How Apply uses Claude today

Every call goes through `apply-agent/src/apply/claude_cli.py`.

**Text only (most calls, `ask`).** `claude -p` with Apply's own system
prompt, no tools, no settings, no MCP servers, a JSON schema for the
answer, and an empty working folder. `ANTHROPIC_API_KEY` is removed, so
the call uses the user's plan. The prompt holds the questions as data
(label, type, options, limits), the student's sources and the company's
material. Claude never sees the browser.

| Job | Model |
|---|---|
| Company brief, with web search (`research`) | Sonnet |
| Essay plan and essays | Opus |
| Edit and source check | Opus |
| Re-plan after a bad read-back | Sonnet |
| Pre-submit review | Haiku |
| Claude fill and Rescue (`drive`) | Haiku |

**Claude drives the browser (`drive`).** This happens only in Claude fill
and Rescue. Playwright MCP attaches to the Worker's own Chrome. Claude
reads the page's accessibility tree as text, with no images, and works
under caps on turns and tokens. Even then Claude does not write the
answers: it reads the questions, the normal planner and writer answer them,
and Claude types the planned answers in. Plain code clicks Next, types
passwords and codes, and clicks Submit only on a live run. A hook refuses
Claude's clicks on Submit.

### 3.1 Claude fill and Rescue: when the model drives the browser

These are the only two places where a model acts in the browser. Both use
Haiku through `ClaudeCLI.drive`, both run under the drive guard
(`submit_guard.DriveGuard`) and the submit-click hook (`send_click.py`),
and neither writes an answer: the answers come from the planner and the
writer first.

**Claude fill** (`claude_fill.py`, `docs/claude-fill.md`) is the Filler for
a hiring system Apply has no Filler for. `orchestrator._apply_with` picks
it when the posting's job system is not in `fillers.FILLERS` (Greenhouse,
Ashby, Lever, Workday, Rippling, Workable, Eightfold), and only after
`greenhouse.board_behind` and `embedded.form_behind` found no known form
inside the page. Oracle, iCIMS, TAL.net, SmartRecruiters and company-built
forms go here.

1. Plain code reads the posting's text off the open page, with no tokens.
2. Session 1, read: Claude reads the form and returns its questions as
   JSON. The planner and the writer answer them, as on any form.
3. Session 2, fill: Claude types the planned answers and reports what each
   field shows. On a form in steps, Claude names the step's Next and plain
   code clicks it; a new step's questions are planned like any others.
4. Plain code types passwords and emailed codes; Claude never sees them.
   Plain code checks each step before Next (`cant_be_right`).
5. Claude stops at the last step and names the button that sends. In a
   rehearsal nothing presses it. In a live run, plain code clicks it after
   the Pre-submit check, and confirms the page.
6. Caps for the whole Application: 40 turns and 400,000 tokens
   (`claude_fill.MAX_TURNS`, `MAX_TOKENS`; `policies.yaml: claude_fill`).
   A cap, a captcha or a guard block is a Handoff to the student.

**Rescue** (`rescue.py`) is for one field that a scripted Filler failed on.
Only the Fillers built per Application (Workday, Eightfold) get one.

1. The Filler fails on a field: a `FillError`, or a click that timed out
   (`WorkdayFiller._put_or_rescue`).
2. Haiku drives the same open page to put that one answer in, and reads
   the field back. It may touch no other field and no button that changes
   the step or sends.
3. Caps: 15 turns and 150,000 tokens per field, at most 6 fields per
   Application (30 turns when the field is on an earlier step of a held
   form, KAN-686).
4. The Filler reads the field back as it reads every field, so the
   Pre-submit check judges it. Each rescued field is noted for a Repair
   request, so the Filler's code gets fixed and the next form needs no
   Rescue.
5. A cap, or Claude saying it can't, gives the Filler's own error back. A
   guard block is a Handoff.

**Without a strong model**, both can be turned off. Claude fill's forms
then go to the student, in a Worker's window or in their everyday Chrome
with the extension; a field that needed a Rescue is left for the student
on the held form.

### 3.2 A generic Filler with a local model (proposed)

The aim: replace most of Claude fill and Rescue with plain code, and use a
small local model only for short, closed choices. A local model is weak at
long, open tool loops, so it never drives freely.

**A Rescue today, as an example.** Workday asks "How did you hear about
us?" with a two-level list. The planner's answer is "LinkedIn". The engine
fails ("no option LinkedIn"), and `WorkdayFiller._put_or_rescue` hands the
field to Rescue. Haiku gets `<field>`, `<answer>` and `<error>`, then works
in turns: snapshot, click the box, see the groups, click "Job Board", see
"LinkedIn", click it, close the list, read the field. It returns
`{"shown": ["LinkedIn"], "blocked": false}` in about 6 of its 15 turns. The
Filler reads the field back, the Pre-submit check judges it, and the field
is noted for a Repair request.

**Read, with no model for most fields.** Chrome's accessibility tree
already gives each control its role and its label (its accessible name).
Plain code builds the question set from it: a textbox is a text question,
a combobox or a radio group is a select with its options, a checkbox is a
yes/no. Generic code opens each custom dropdown in turn, reads its
options, and closes it. The model is asked only where the tree is unclear
(a box with no label, an "Other, please specify" box, a question split
across elements), as one short question about a few elements.

**Control, by role.** Plain code acts; the model only picks.

| Control | Plain code | The model's question, when needed |
|---|---|---|
| Textbox, textarea | Fill it with the planned answer | None |
| Native `<select>` | Pick the option; `fit.ts` maps the value to the form's wording | None |
| Checkbox, radio | Click the one whose name fits the answer | Which of these names means the answer? |
| Custom dropdown, search box | Click, type the answer to filter, read the options, match with `fit.ts` | Which of these options is the answer? |
| Two-level list | Open it and read the groups | Which group holds the answer? |
| File upload | Set the file on the file input | None |
| Next | Find it by Claude fill's `NEXT` and `BACK` patterns | Which of these buttons goes on, without sending? |

**What the model gets is not what Claude gets.** Claude gets the whole page
and the tools, and runs the loop. The local model gets one closed question
with a small part of the page, and returns one choice as JSON (Ollama and
llama.cpp can hold a model's output to a JSON schema):

```
System: Pick the option that means the answer. Reply {"choice": <number>} or {"choice": null}.
Prompt: Field: "How did you hear about us?"   Answer: "LinkedIn"
        Options: 1. Job Board   2. Social Media   3. Employee Referral   4. Career Fair
Reply:  {"choice": 1}
```

The loop belongs to plain code: act, read the tree again, check the field
by read-back, and ask the model again only for the next closed choice. The
same example runs as: code clicks the box and reads 4 groups; `fit.ts`
finds no "LinkedIn"; the model picks group 1; code clicks it and reads the
new list; `fit.ts` finds "LinkedIn"; code clicks it and reads the field
back. One model call of about a hundred tokens, against Haiku's six turns
over whole-page snapshots.

**What stays hard, and goes to the student.** A page in an unexpected
state (an error banner, a pop-up, a field that resets, a reload), a widget
missing from the tree (a canvas date picker, drag and drop), and a step
whose end is not clear. A long page is cut to the form's part before any
model sees it, because a local model's context is small and a laptop reads
long input slowly. A field the generic Filler can't place is left for the
student on the held form, as a failed Rescue is today.

**Tools for a local model: narrow, not Claude's.** A local model can call
tools (Qwen 3 and Llama 3.1 and later do; Ollama has a tools API). But
Claude's tools do not move over as they are. `drive` runs inside the
`claude` CLI, which owns the loop and attaches Playwright MCP to a CDP
endpoint. A local model has no such loop, so Apply would run the loop and
carry out each tool call itself. Give it the whole page and Claude's tools,
and it fails: snapshots are tens of thousands of tokens, a laptop reads
them slowly, and a small model repeats clicks or says "done" too early over
20 to 40 steps. So the model gets a few tools on one field's part of the
page, and plain code checks each call before it runs it:

| Tool | What plain code does |
|---|---|
| `pick_option(n)` | Clicks option n, then reads the field back |
| `click(ref)` | Clicks only an element inside the field's subtree |
| `type(ref, text)` | Types only the planned answer, never the model's own text |
| `give_up()` | Puts the field on Needs you |

The submit guard (`submit_guard.py`, `plain/guards.py`) stays under every
call, as it is under Claude's clicks today: no model can press Submit. These
tools sit on Apply's own `Filler` shape, so, unlike `drive` (CDP only), they
work on plain Workers too. The scale, most reliable first: closed questions
only (enough for most Rescues); narrow tools on one field (a widget that
takes 2 or 3 actions); full page control (not with a local model: the page
goes to the student).

**How to test it.**

1. Build the generic Filler over the accessibility tree, with the local
   model as the tie-breaker, behind the same `Filler` shape
   (`apply/fillers.py`), so it runs on CDP and plain Workers alike.
2. Run it on the engine's saved forms (`test/fixtures/`;
   `uv run apply plain fill <saved-form>` serves one on 127.0.0.1 and
   refuses every POST).
3. Rehearse the long-tail postings that Claude fill fills today.
   Rehearsals never submit.
4. Compare the share of fields filled right, and the time, with Claude
   fill on the same postings. Keep Claude fill as developer mode.

The volume comes from plain code, not from more AI: Matches cost no tokens,
the planner answers most fields, the answer bank reuses drafted answers, a
company brief is researched once per company, 3 Workers run at once, and
Apply stops starting new Applications at 85% of the 5-hour usage window or
70% of the weekly one.

## 4. Why a desktop app, and not only the website

**A web page cannot drive another site.** The same-origin policy stops a
page on `workitjobs.ai` from reading or typing into a page on
`greenhouse.io`. A page also cannot start Chrome processes or choose
profiles. So filling a job site's form needs an extension or a local
program.

| | Website + extension | Desktop app (Apply) |
|---|---|---|
| What drives the form | Chrome extension APIs | Python, through Playwright (CDP) or the worker extension |
| Where the run's state lives | An MV3 service worker, which Chrome stops when idle | A long-running Python process |
| Tabs | Background tabs in the student's own window (5 at once) | One Chrome process and window per Worker; each form is that window's active tab |
| Profiles | The student's one profile | A separate profile per Worker |
| Install | Chrome Web Store | A desktop app per OS |

The extension had these problems (`auto-apply/architecture.md` §10):
hidden tabs run slowly, the service worker stops when idle, a new window
switched the student's macOS Space, and the session expires after one
hour. Apply avoids them because:

- each form is the active tab of its own Worker's window;
- Playwright passes `--disable-background-timer-throttling`,
  `--disable-renderer-backgrounding` and
  `--disable-backgrounding-occluded-windows` by default, and plain Workers
  pass the last one;
- Python holds the run, and in plain mode the native-messaging port keeps
  the worker extension's service worker alive;
- Workers are separate Chrome processes that start in the background;
- Apply refreshes its own WorkIt session.

Two limits are the same on both paths: a minimized window stops painting,
so a Worker must never be minimized; and `apply rehearse --into` puts more
forms into one Worker, so all but one are background tabs again. The
second case is not tested on plain Workers yet, which pass only the
occluded-window flag.

Cloud browsers (Chrome on WorkIt's servers) are not a path: data-center
IPs are blocked far more often, the student's sign-ins would live on
WorkIt's servers, and the cost and the hiring-system risk are highest.

## 5. How Apply controls Chrome

**CDP Workers.** Playwright starts real Google Chrome
(`channel="chrome"`) with `launch_persistent_context` on
`profiles/worker-N`, with a normal user agent and
`--disable-blink-features=AutomationControlled`. Clicks and keys are
trusted input over CDP. The engine runs in the page through
`page.evaluate`. The tiles come from CDP screencast frames.

**Plain Workers** (`apply-agent/src/apply/plain/`, protocol in
`apply-agent/docs/plain-workers/PROTOCOL.md`):

```
Apply ── Unix socket ── host relay (Chrome starts it) ── native messaging ── worker extension
```

Apply starts a normal Chrome with no DevTools port, no `--enable-automation`
and no headless mode. A private worker extension runs each op (`tabs.goto`,
`dom click`, `fill`, `tile.start`...). `PortPage` copies the Playwright
`Page` API, so Fillers, the engine and the guards run unchanged. Claude
fill gets a tool server with the same `mcp__playwright__*` tool names.

## 6. Worker mode: `protected` is the default (built, 2026-11-06)

`apply-agent/policies.default.yaml` sets `worker_mode: protected`: plain
Workers fill the hosts that block CDP Workers (`plain_worker_hosts`: Lever,
SmartRecruiters, Workable; and each host where Apply saw a bot block,
`APPLY_HOME/plain-hosts.json`), and CDP Workers fill the rest. The team
chose this before the planned week of side-by-side runs. A student who
wants every form in a plain Worker sets `plain` in their own
`policies.yaml`.

What it means for a teammate:

- Run `uv run apply plain seed` once. `apply doctor` now shows a
  "Plain seed" line beside "Worker profiles".
- Tests do not follow the default: `apply-agent/tests/conftest.py` takes
  `worker_mode` out of the default policies, so a test that needs a plain
  Worker sets it itself.

### 6.1 The tradeoffs of plain Workers

- **Input is synthetic.** Each event has `isTrusted: false`, which a page
  can read; CDP's input is trusted. With no user activation, pop-ups are
  blocked (the extension opens the URL in a new tab), the file picker does
  not open (the extension sets files through `DataTransfer`), and focus
  events do not fire in a background window (Workday's blur, KAN-709).
  Only left clicks.
- **Page code is limited.** The extension needs "Allow User Scripts" on. A
  page whose CSP forbids `eval` refuses it, so the per-turn page functions
  are fixed extension code (`apply.plain.fixed`).
- **More setup.** Branded Chrome ignores `--load-extension`, so the worker
  extension goes into a seed profile by hand (`apply plain seed`), with
  Developer mode on.
- **Slower screens.** `captureVisibleTab` allows about 2 captures a second.
  A smooth tile needs macOS Screen Recording and a Swift helper.
- **Weaker network control.** `declarativeNetRequest` rules block requests;
  response bodies are read only for non-GET fetch and XHR calls.
- **More code to keep up.** `PortPage` copies Playwright's API by hand.
- **Chromium only, and tied to Chrome's rules.** MV3, native messaging and
  user scripts can change, and managed Chrome can block them. The native
  host is registered per OS, and the Unix socket needs a named pipe on
  Windows.

### 6.2 What plain Workers do not do

A plain Worker removes one signal: the automation channel. A site can
still see synthetic input, timing, behavior, the IP, and scores from
reCAPTCHA, hCaptcha, DataDome or Akamai (`apply-agent/docs/captchas-and-bot-blocks.md`
lists the blocks Apply met). Bot detection and AI-content checks are also
different things: an AI-content check reads the text, so the Worker kind
does not change it. Postings that ban AI answers are caught by the engine
(`posting_bans_ai`) and handed to the student.

`protected` picks the Worker kind once per host, before the form opens; a
whole form runs in one kind. Switching a Worker between plain and CDP
mid-form, to pass a check in one mode and then act in the other, is
evasion. It is out of scope, with the student in control or not: the
check judges the session that fills the form. It also cannot work as
pictured, since a Chrome gets its DevTools port only when it starts.

Within the rule, the design is: `protected` per host, hosts learned from
each block (`plain-hosts.json`), a real block sent to the student's
everyday Chrome and the extension (KAN-590), and the student's own clicks
(trusted in either Worker kind) for a field that needs them.

## 7. The desktop app: what it needs

| Part | Today | Desktop app |
|---|---|---|
| Apply's code | Python, run with `uv` | Frozen with its dependencies (PyInstaller or Briefcase), one build per OS |
| Fill engine | `engine.js` from the private submodule | `engine.js` inside the app. Decide whether a built copy of the private engine may ship in a public download |
| JS runtime | The Node inside Playwright's driver | The same, bundled |
| Browser | The user's Chrome at `/Applications/...` | Find Chrome on each OS; keep the user's installed Chrome |
| Claude | `claude -p` on the user's login | An allowed method (section 8) |
| The Apply window | A local web page on 127.0.0.1 in Chrome app mode | Keep it; it already works on any OS |
| Student data | YAML and Markdown in `~/.config/apply/` | From WorkIt over HTTP (section 9) |
| Secrets | macOS Keychain through `security` | A cross-platform store (`keyring`: Keychain, Windows Credential Manager, Secret Service) |
| Sign-ins | Chrome started by hand with flags | A first-run step that opens the Worker profile for Google sign-in |
| OS extras | Dock bundle, macOS notifications, launchd, Swift window capture | A version per OS, or left out on that OS |
| Updates | `git pull` | Code signing (Apple notarization, a Windows certificate) and an auto-updater |

**macOS-only code today** (a search of `apply-agent/src/apply/` for macOS
commands and paths; check each module before porting it): `keychain.py`, `notify.py`, `schedule.py`,
`dock_app.py`, `focus.py`, `browsers.py`, `dashboard.py`, `captcha.py`,
`doctor.py`, `accounts_tab.py`, `brief.py`, `cover_letter.py`, `cli.py`,
`workit.py`, `plain/launcher.py`, `plain/seed_setup.py`,
`plain/window_capture.py`. They use `security`, `osascript`, `launchctl`,
`open`, `pgrep`, `/Applications/...` and Swift. The core (the Worker, the
engine calls, the essays, the gates, the window's server) is ordinary
Python and Playwright.

### 7.1 The student's part

The app fills the forms. The student:

- watches each Worker's tile and the run's progress;
- answers Missing facts and does each captcha;
- checks the answers and the verification flags;
- presses Submit on each form.

`live_runs` (Apply presses Submit after every check passes) stays off in a
public build.

### 7.2 Plain Workers on every OS

Plain Workers ship on every OS, as part of the app. The CDP path already
runs anywhere Playwright runs. The plain path has these per-OS parts:

| Part | macOS today | Windows | Linux |
|---|---|---|---|
| Native-messaging host manifest | A JSON file in each Worker profile's `NativeMessagingHosts/` | A registry key under `HKCU` that names the manifest | A JSON file, as on macOS |
| The host's launcher | A shell-script wrapper | An `.exe` or `.bat` wrapper | A shell script |
| Apply ↔ host channel | A Unix socket (`workers.sock`) | A named pipe or a localhost port, with the same framing | A Unix socket |
| Starting Chrome in the background | `open -g -n -a` | `subprocess` with no focus | `subprocess` |
| Smooth tile | ScreenCaptureKit (Swift helper) | Windows Graphics Capture, or the extension's frames (about 2 fps, built) | The extension's frames |
| Seed profile | `apply plain seed` | The same steps | The same steps |

Each part is known work. The parts to test early are background-window
behaviour on Windows and Linux (`--disable-backgrounding-occluded-windows`
reads window cover differently on each OS) and the host's registration
under a school's managed Chrome.

### 7.3 Updates

- **The app** updates as a whole, in the background, with an auto-updater
  (Sparkle on macOS; Squirrel, WinSparkle or MSIX on Windows). It downloads
  a signed build, often a delta, and applies it at the next restart. The
  student never downloads the app again by hand. Python changes (how Apply
  drives Chrome, `protected` rules, the window) ship this way.
- **The Fill engine** (`engine.js`) comes from WorkIt's server, apart from
  the app, so a fill fix reaches students in minutes. Rules:
  - The file is versioned and signed; the app checks the signature and the
    sha256 before it loads it. Unsigned downloaded code would let an
    attacker run code on every student's computer.
  - Each engine names the app versions it works with; the app keeps its
    bundled engine when the new one does not fit.
  - Plain Workers already refuse an engine whose version or sha256 differs
    from Apply's, and already take a new one from a vendor set without a
    restart (`apply-agent/docs/plain-workers/PROTOCOL.md`, KAN-645). CDP
    Workers load `fill_engine.ENGINE` from disk and need the same
    download-and-check step.

### 7.4 Who can see the code

Anything that runs on the student's computer can be read in the end.
Compiling only makes it cost more. The private repo hides the source; it
does not hide what the app ships.

**Where each part of the engine runs.**

| Part | Where it runs | Can it be machine code? |
|---|---|---|
| Planner, rules (`planner.ts`, `rules.ts`), `fit.ts` | The long-lived Node process (`call_without_page`); no page needed | Yes, after a rewrite (Rust or Go, to a native binary or WebAssembly), or by moving it to the server |
| Field reading, filling, read-back | Inside the job site's page: `page.evaluate` on a CDP Worker, the worker extension's user script on a plain Worker | No. Only JavaScript can touch a page's DOM (WebAssembly needs JavaScript to reach the DOM) |

The in-page part stays JavaScript because it reads and changes the page's
DOM from inside the page. The desktop app's Python never touches the DOM:
it sends the script into the page (over CDP, or through native messaging
to the worker extension) and gets the result back.

**How a student could read it.** The engine file on disk in the app's
folder (downloaded from WorkIt or bundled); the download itself (HTTPS
stops others, not the computer's owner); DevTools on a Worker's tab, which
lists injected scripts; and the app's memory. Encrypting the file on disk
does not help: it must be plain JavaScript at the moment it enters the
page. Turning DevTools off needs a machine-wide Chrome policy, which the
student can undo.

Node packagers (Node SEA, `pkg`) put the JavaScript source in the binary,
so they hide nothing. V8 bytecode (bytenode) is harder to read but can be
decompiled. Nuitka or Cython compile Apply's Python to machine code.

**The black-box design (proposed).** Split the engine into a brain and a
thin hand:

- **The hand** (in the page, JavaScript): generic DOM steps only: list the
  controls with their roles and labels, click element n, type text into
  element n, read element n back, wait for a change. It holds no rules and
  no per-hiring-system tricks, so reading it shows little.
- **The brain** (on WorkIt's server, or compiled): the planner, the rules,
  `fit.ts`, and each hiring system's widget recipe ("Workday's two-level
  list: click the box, wait for the list, pick the group, then the
  option"), sent to the hand as a list of steps.

The server is the only real black box: the rules never leave it, and
WorkIt already holds the student's data, so no new data goes out. Costs:
one call per form for the plan (the steps can come in one reply), no
planning when WorkIt is offline, and a large refactor of the engine. The
extension, which goes through the Chrome Web Store, may be minified but
not obfuscated. The desktop app's worker extension is private and does not
go through the Store, so its hand may also be obfuscated, which only slows
a reader down.

## 8. Claude access

**Why it works today.** Apply does not run inside Claude Code. Each person
installs Claude Code, logs in with their own plan, and runs Apply on their
own computer; Apply calls the `claude` command as a subprocess. It is a
tool each developer runs for themselves, not a product WorkIt offers to
others. Having the source code is not the point; who offers the login is.

**What changes in a product.** Anthropic's Agent SDK docs say: "Unless
previously approved, Anthropic does not allow third party developers to
offer claude.ai login or rate limits for their products, including agents
built on the Claude Agent SDK. Use the API key authentication methods
described in the Quickstart instead."
(https://code.claude.com/docs/en/agent-sdk/overview, read 2026-11-06).
A WorkIt app that runs `claude -p` on a student's Pro or Max login offers
that login's rate limits in WorkIt's product. Plan on it being not allowed
without Anthropic's approval, even when the student installed Claude Code
themselves. A commercial launch also needs a read of Anthropic's terms by
someone qualified; this note only reports the docs.

**What stays allowed for a student's subscription: the connector.** The
student adds WorkIt's MCP server to their own Claude (claude.ai, Claude
Desktop or Claude Code) and starts the work there. That is the student
using Anthropic's product, which calls WorkIt's tools; WorkIt never holds
the login. It is built for the extension path (KAN-377,
`auto-apply/architecture.md` §14.6).

**The desktop app on the connector (proposed).** Apply already plans every
form before it fills (a rehearsal with `--start-button` waits, planned, for
Start). So one prompt can serve a whole batch:

1. The app reads each form's question set and runs the planner; the open
   questions (essays, one-off questions) go to WorkIt as one batch.
2. The student runs one prompt in their Claude ("Write my WorkIt
   answers"). Their Claude reads each application's questions and the
   student's material through the connector and saves the answers.
3. The app takes the saved answers, runs the gates, and fills the forms.
   The student checks, does each captcha and presses Submit.

Cost to WorkIt: none for the model. Cost to the student: one prompt per
batch, on their own plan. Limits: no Claude fill and no Rescue (they need a
model that drives the browser on the app's schedule), and no company brief
research unless the student's Claude does it in the same prompt.

**Cheaper models.** Every call goes through one adapter
(`Adapters.claude`: `ask`, `research`, `drive`), so another backend fits
behind it. `ask` needs a model that returns valid JSON reliably; essay
quality drops (`essays.py`: Opus's essays beat Sonnet's 142 to 26 in
paired judging). `research` needs Apply to fetch pages itself when the
model has no web search. `drive` needs strong tool use, so a weak model
should not drive; turn Claude fill and Rescue off (§3.1). WorkIt already
uses Groq for Scout and Gemini in production, and Scout runs on Ollama
locally; check each provider's terms for a paid product (§14.5). A local
model is free per call but slow, needs a strong laptop and writes the
weakest essays.

| Option | How | Consequence |
|---|---|---|
| A. `claude -p` on the user's login | No change | Allowed only as a developer mode, for the user's own use |
| B. The user's own API key | Replace `claude_cli.py` with the Anthropic SDK: `ask` becomes a Messages call with structured outputs, `research` uses the web search and web fetch server tools, `drive` becomes a tool loop over Playwright (or the Agent SDK with the key) | Allowed. The user pays per token, apart from any Claude plan. Opus on every form costs more, so the model mix needs a review |
| C. WorkIt pays | The app calls Claude through WorkIt's API, with WorkIt's key | Allowed. WorkIt needs billing, quotas and per-user limits (`auto-apply/architecture.md` §14.2–14.3) |
| D. The student's own Claude calls WorkIt | The connector (KAN-377): the student adds WorkIt's MCP server to their Claude, which reads the questions and saves the answers | Allowed. The student starts it from their Claude app, so the desktop app cannot call Claude on its own schedule |
| E. Sign in with ChatGPT | The student signs in with ChatGPT; the app calls OpenAI's Responses API with the student's token, on their Plus or Pro allowance | Allowed only after OpenAI approves a paid or hosted app (below). No cost to WorkIt |
| F. Chrome's built-in model | The worker extension (or the student's extension) calls Chrome's Prompt API, which runs Gemini Nano on the computer | Free and local; for closed questions (§3.2) only, not essays. Needs a strong enough computer |

**Other AI companies (read 2026-11-08; check each provider's own pages
before relying on it).**

- **OpenAI: "Sign in with ChatGPT".** OpenAI first used it in Codex CLI
  (May 2025). At DevDay (2026-09-29) it let supported third-party apps use
  a Plus or Pro subscriber's included allowance; launch partners include
  Amp, Devin and Lovable. Reports say plan usage is open to open-source
  projects, personal projects that run locally, and selected private apps;
  a paid or hosted app fills in an interest form first. The app calls the
  Responses API with the user's token; the user can cap each app weekly,
  and at the cap requests fail rather than move to other billing. This is
  the nearest thing to "use the student's own AI plan" in a product, but
  WorkIt needs OpenAI's approval, and essay quality would need a new
  comparison (Apply's prompts are tuned for Claude). Sources:
  https://www.developersdigest.tech/blog/sign-in-with-chatgpt-coding-agents-plan-usage-2026,
  https://itbrief.com.au/story/openai-launches-chatgpt-sign-in-for-16-partner-tools,
  https://techcrunch.com/2025/05/27/openai-may-soon-let-you-sign-in-with-chatgpt-for-other-apps/.
- **The connector in other chat apps.** The connector is an MCP server, so
  any chat app that takes MCP servers can call it, not only Claude
  (ChatGPT's Apps and developer-mode connectors take them). Each app has
  its own setup and review.
- **Chrome's built-in AI.** Chrome's Prompt API is stable for extensions
  (Chrome 138 and later) on Windows, macOS and Linux. Chrome downloads
  Gemini Nano the first time an extension uses it. It needs free disk
  space (Google's page has said 22 GB) and a GPU with more than 4 GB of
  memory, and the developer accepts Google's Generative AI Prohibited Uses
  Policy. It is free and needs no Ollama, but it is a small model:
  closed questions only. https://developer.chrome.com/docs/ai/prompt-api,
  https://developer.chrome.com/docs/extensions/ai/prompt-api.
- No other major company has a known program that lets a third-party app
  spend a user's chat subscription. Anthropic's rule is above.

Direction (2026-11-06): no API keys, as too costly. The open choice is
between D (the connector, above) and a cheaper or local model behind
`Adapters.claude`, or both: the connector for essays and a cheap model for
one-off answers. `claude -p` stays as developer mode. Not decided.

## 9. WorkIt as the source of the data

Apply already calls WorkIt through one client, `apply-agent/src/apply/workit.py`
(`apply-agent/docs/workit.md`): `apply login` with its own token refresh,
`GET /auth/me`, the tracker writes (applied with the sent resume,
needs_you), the tailored resume for a posting, and add-by-link. New reads go
there as methods, never in another module.

What would move from the data folder to WorkIt:

| Apply's file today | WorkIt today | Work |
|---|---|---|
| `applicant-profile.yaml` | The student's profile | Map the fields, or add an endpoint |
| `answer-bank.yaml` | Batch apply's answer bank (KAN-369) and `written_answers` | Being redesigned by a teammate |
| `story-bank.md`, `story-map.yaml` | The experience bank, by resume (`docs/bank_by_resume.md`) | Map entries to stories |
| `voice.md` | None | New |
| `company-briefs/` | None | New, or keep local |
| The resume PDF | Uploads and built resumes; sent resumes | Partly built (tailored resume) |
| `tracker.json` | The Applications Tracker | Built: Apply already writes it |

The data model is the main work, not the transport. Personal data stays
out of the repo on both sides.

## 10. Proposed build order

1. `protected` as the default. **Done.**
2. Measure one Application's model use: the tokens in about 20 rehearsal
   Records across hiring systems, by call kind. It sizes the connector
   batch and the cheaper-model options (section 8).
3. The data contract: every fact Apply reads, the module that reads it,
   and the WorkIt table or endpoint that will serve it (section 9). The
   answer bank redesign starts from it.
4. A packaging spike: freeze Apply on one Windows computer and make one
   CDP rehearsal and its window work.
5. The model backend behind `Adapters.claude` (section 8), and the
   connector batch if chosen; and the generic Filler with a local model
   (§3.2), tested on saved forms and long-tail rehearsals against Claude
   fill.
6. WorkIt client reads for the profile, answer bank and stories.
7. Replace the macOS-only modules; plain Workers on Windows and Linux
   (§7.2).
8. First-run and setup screens in the Apply window: WorkIt login, Google
   sign-in for the Worker profile, the seed, the model choice.
9. Start a run from the window (paste links, or take WorkIt's queue), not
   only from the terminal.
10. Freeze, sign and publish one build per OS, with the auto-updater and
    the engine download (§7.3).

## 11. Open questions

- The model path (section 8): the connector, a cheaper or local model, or
  both; and whether to ask Anthropic about the student's subscription.
- Whether a built copy of the private Fill engine may ship in a public
  download, and whether to move the planner to WorkIt's server (§7.4).
- Whether to apply to OpenAI for Sign in with ChatGPT plan usage (§8, E).
- The answer bank's redesign and each mapping in section 9.
- Windows and Linux plain Workers (§7.2): background-window behaviour and
  managed Chrome.
- The engine download (§7.3): who signs it, and the version rule.
- Filling in a background tab of a plain Worker (`--into`): test it before
  relying on it.
- The hiring systems' terms restrict automated applying. "The student
  presses Submit" helps; get a legal check before selling it
  (`auto-apply/architecture.md` §14.5).
