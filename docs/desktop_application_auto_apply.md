# WorkIt Auto Apply: the desktop app (KAN-723)

**Status (2026-11-13):** designed, not built. A design review on
2026-11-13 settled every decision in section 2. Built so far: Workers
default to `worker_mode: protected` (2026-11-06), and `ask` runs on Groq
with Gemini as backup (`ask_model: [groq, gemini]`, 2026-11-10,
`apply-agent/docs/ask-model.md`).

**How to use this doc.** Read sections 1 to 3 first. Then take one
workstream from section 6: each one says what it changes, which files it
touches, what it waits for and when it is done, so one session can work
on it without the others. Section 4 explains Apply as it is today, as
background. Apply's terms are in `apply-agent/GLOSSARY.md`. The main
decision is ADR 0005 (`apply-agent/docs/adr/0005-student-build-calls-models-only-through-workit.md`).

**Where this doc lives.** Apply's code moves to the private repo
`workitjobs/apply-agent` (workstream W0), and this doc and the ADR move
with it. The WorkIt repo then keeps the server side: the API routes and
the website pages this design adds.

## 1. What the app is

### 1.1 Two paths to auto apply

| Path | What it is | Who it is for |
|---|---|---|
| **The extension** | The WorkIt Chrome extension (KAN-164) fills forms in the student's own Chrome. The student opens each form and goes over it. Open answers come from WorkIt, or from the student's own Claude through WorkIt's MCP server (the connector, KAN-377). | Most students. Install from the Chrome Web Store. Reliable, but the student works one form at a time. |
| **WorkIt Auto Apply** | Apply as a desktop app. It runs its own Chrome Workers in the background and fills several applications at once. One window shows every Worker. | Students who want applications filled for them: they check, change and approve in one window, and press Submit. |

**The connector belongs to the extension path only.** It needs the
student to start each piece of work from their own Claude, so it can't
serve a run in the background. The desktop app calls its models by
itself, through WorkIt (ADR 0005).

### 1.2 What the student does

The app fills the forms. The student:

- signs in to WorkIt once;
- adds jobs to the Auto Apply queue on the website, or pastes a posting's
  link into the app, and presses Start;
- watches each Worker's tile;
- answers Needs-you items, types emailed codes and does each captcha;
- checks the answers and the verification flags;
- presses Submit on each form, in that Worker's Chrome window.

**Apply never presses Submit in WorkIt Auto Apply.** `live_runs` is fixed
off in the Student build, and nothing in it can turn it on. W12 removes
`live_runs` and Rehearsals from Apply altogether.

**The app is simple.** One sign-in (the student's WorkIt account), no API
keys, no settings files, no terminal. First run needs only Google Chrome
and one click to add the Worker extension (section 3.1). All other work
stays on the website: the profile, the answer bank, the resumes, Tailor
and the Tracker.

### 1.3 The bot rule

Apply never evades bot detection and never touches a captcha; it hands
both to the student (`apply-agent/docs/captchas-and-bot-blocks.md`). The
goal is the fewest *false* blocks: blocks that come only from the
automation channel. Choosing the channel with the fewest false blocks is
within the rule; getting past a site that decided to block is not. A real
block goes to the student's everyday Chrome, where the extension fills
it.

### 1.4 Names

| Name | What it is |
|---|---|
| **WorkIt Auto Apply** | The released desktop app: the **Student build** of Apply. Bundle id `ai.workitjobs.autoapply` |
| **Developer checkout** | Apply run from a clone of `workitjobs/apply-agent`. It keeps every developer part, Claude included |
| **WorkIt Auto Apply Worker** | The **Worker extension** as it is listed on the Chrome Web Store (unlisted) |
| **Seed** | The Worker profile that gets the Worker extension once; each plain Worker's profile starts as a copy of it |
| **Model route** | WorkIt's API routes that make each model call for a Student build and count it |
| **Usage cap** | The model use one student may spend in one month, shown in the app |

"Apply" stays the code's and the glossary's name for the agent itself.

## 2. Decisions

All dated 2026-11-13 unless noted. Each row names the workstream that
builds it.

| # | Decision | Why | Builds it |
|---|---|---|---|
| D1 | **Every model call goes through WorkIt's Model route.** No `claude -p`, no local model and no student key in the app (2026-11-10; ADR 0005) | A product may not offer a student's Claude login; a local model is too weak and too heavy for a laptop; a key in the app is a key for everyone | W1 |
| D2 | **The app does no research.** It reads each company's brief from WorkIt | Research is the most expensive call, and a brief holds no student data, so WorkIt can make one per company for every student | W9, F2 |
| D3 | **The Fill engine is downloaded only, never shipped in the app.** Signed, encrypted, unlocked by a per-launch key, kept only in memory | A copy in the download is a copy for everyone; the app needs WorkIt to run anyway | W7 |
| D4 | **The Worker extension goes on the Chrome Web Store, unlisted, from WorkIt's existing developer account.** Apply's page code and the Fill engine reach pages through the Debugger API, not `userScripts`; the guards and the fixed page functions are packaged in it, since only a content script reaches a pop-up (measured); it holds no engine. A spike decides it (KAN-839, started); if it fails, v1 keeps the extension off the store | One click for the student; the store allows outside code only through the Debugger or User Scripts API, and User Scripts is only for the user's own code; the existing account costs no new fee and has a trust history | W6 |
| D5 | **The Model route is a thin proxy for v1.** The app sends the call; WorkIt adds the key, runs the provider chain and counts tokens. The prompts stay in the app | Fastest path; writing on WorkIt's server can come later (F6) | W1 |
| D6 | **A free beta with a Usage cap of 3,000,000 tokens per student per calendar month**, reset on the 1st (UTC), always shown in the app. WorkIt can change it without an app update | High enough for testing; the number is checked after W13 measures one Application | W1 |
| D7 | **The beta uses the providers' free tiers.** Paid tiers come later (F3) | No paid keys for now | W1, F3 |
| D8 | **Personal data is replaced before a prompt leaves the computer**, and put back on the computer. Self-ID answers are never sent. The app shows a short disclosure | Prompts go to WorkIt and to Groq and Google, and Google's free tier may use prompts to improve its products | W1, W5 |
| D9 | **No Gmail.** A job site's emailed code becomes a Needs-you item that the student types | Reading Gmail needs an app password (a hard setup) or Google's paid security review | W3 |
| D10 | **macOS-only code is removed or replaced.** Scheduled runs, phone push and the Dock bundle are dropped; Keychain becomes `keyring`; Chrome is found per OS | A simple app, and a later Windows port that is not a rewrite | W4 |
| D11 | **The window is native (pywebview) and opens no port.** Its page talks to Python through pywebview's bridge, not through a server on `127.0.0.1` | It works like any other app; no local server that other programs can call | W5 |
| D12 | **The only sign-in is WorkIt**, in the student's default browser, back to the app through `workit-auto-apply://` with PKCE. The session lives in `keyring` | No new account and no port; the student signs in where they already do | W5, W1 |
| D13 | **In v1 no model drives the browser.** Job systems with no Filler get the generic Filler; what it can't fill is a Handoff, and a field a Filler fails on is a Needs-you item. **A hosted `drive` loop is the next work after v1** (F1) | `drive` needs a strong model, large calls and an adversarial guard review; the generic Filler needs only short closed choices | W2, F1 |
| D14 | **One codebase, two builds.** The Student build is compiled without the developer parts. There is no setting, switch or key that turns them on | Developer features can't be turned on by accident when their code isn't in the app | W3 |
| D15 | **Company briefs belong to WorkIt** and may become proprietary. One brief format, a company registry and a pipeline that keeps briefs are designed but not built for v1 | Shared briefs cost per company, not per application | W9, F2 |
| D16 | **Legal uses free templates and tools now.** No review of the hiring systems' terms for now | No budget; the student presses Submit | W10 |
| D17 | **Distribution: a notarized DMG on workitjobs.ai, with Sparkle updates** from Cloudflare R2. Not the Mac App Store | The App Store's sandbox blocks control of Chrome | W8 |
| D18 | **Apple Silicon only, macOS 13 and later.** Intel Macs are future work (F8) | One build; macOS 26 is the last version for Intel Macs | W8 |
| D19 | **Names:** "WorkIt Auto Apply", `ai.workitjobs.autoapply`, and "WorkIt Auto Apply Worker" for the extension | | W5, W6, W8 |
| D20 | **Apple enrollment: an individual now**, an organization later (F7) | An organization needs a registered company and a D-U-N-S number; Apple says the Team ID stays on conversion | W8 |
| D21 | **Google Chrome is required.** First run checks for it and links to its download | Chrome for Testing can't turn on Allow User Scripts, and other browsers are untested | W5 |
| D22 | **CDP Workers keep their debugging port on `127.0.0.1` in v1.** One Worker kind with no port is future work (F5) | Pipe mode adds automation switches; the bridge may later carry CDP Workers too | F5 |
| D23 | **Jobs come from the student's Auto Apply queue on WorkIt**, plus a box to paste one posting's link | The queue is already on the website | W5 |
| D24 | **Two Workers by default, one to three.** Each is a full Chrome, about 0.5 to 1 GB of memory | Student laptops | W5 |
| D25 | **"Remove all my data"** in settings deletes the Worker profiles, the seed, Records, Traces and the app's `keyring` items. The data folder is in each OS's standard place | Mac apps have no uninstaller | W5 |
| D26 | **"Send report"** sends one Application's Record and a masked Trace to WorkIt only when the student presses it. No automatic telemetry | Testers need a way to report; privacy first | W5, W1 |
| D27 | **Engine signing:** the Fill engine's CI signs each build with an Ed25519 key; WorkIt serves the newest build that fits the app's version; the app holds only the public key | An unsigned download would let an attacker run code on every student's computer | W7 |
| D28 | **Certificate pinning** to the certificate authorities Cloudflare uses for `api.workitjobs.ai`, with backups. Sparkle's feed is on another host without pinning, so an update can fix the set | A proxy on the student's computer can't read the engine download | W7 |
| D29 | **Apply moves to the private repo `workitjobs/apply-agent`**, with its history | The WorkIt repo is public; compiling protects nothing while the source is public | W0 |
| D30 | **The Developer checkout uses the local API** (`ask_model: workit` against localhost by default after W0). `claude` stays a developer choice. There is no staging server | Simple; keys stay only in WorkIt's `backend/.env` | W0, W1 |
| D31 | **Developer setup is `git clone --recurse-submodules`, `uv sync`, `uv run apply app`.** The window's first run does the rest, as for a student | One path for everyone | W5, W0 |
| D32 | **CI is small:** GitHub-hosted Linux runners, on PRs only, ruff and a short list of fast tests. No builds and no tags in CI | GitHub Actions minutes are limited | W0 |
| D33 | **One mode:** Apply fills each form and stops on its last page; a person always presses Submit. Rehearsals and `live_runs` go. Not a v1 blocker | Simpler and safer: Apply never sends an application | W12 |
| D34 | **The student's data comes through the Fill engine's code as it does now.** Its redesign is a teammate's work | Out of this design's scope | W11 |

## 3. The v1 app, end to end

### 3.1 First run

1. **Download.** The student downloads `WorkIt Auto Apply.dmg` from
   workitjobs.ai and drags the app to Applications. The app is signed and
   notarized, so macOS opens it with only its standard "downloaded from
   the internet" question.
2. **Sign in.** The window shows "Sign in with WorkIt". The app opens
   WorkIt's sign-in page in the default browser (password, Google or
   LinkedIn, as on the website). After sign-in, the website opens
   `workit-auto-apply://signed-in?code=…`; macOS hands it to the app,
   which trades the one-time code for a session (PKCE, W5). The session
   goes into `keyring`.
3. **Chrome.** If Google Chrome is missing, the app says "WorkIt Auto
   Apply needs Google Chrome" with a Download button (google.com/chrome
   in the default browser), and goes on when Chrome appears.
4. **Disclosure.** One screen says what leaves the computer (section 3.4)
   and that Google's free tier may use prompts to improve its products.
   The student presses OK.
5. **The seed.** The app makes a Chrome profile folder in its data folder
   and opens Chrome on it at the store listing of WorkIt Auto Apply
   Worker. The student clicks "Add to Chrome" and confirms Chrome's
   dialog ("Access the page debugger backend", "Communicate with
   cooperating native applications"). The app sees the extension in the
   profile's files, closes that Chrome, starts one test Worker from a copy
   and waits for its hello. It takes about a minute. The student types
   nothing. (If the W6 spike fails, this step is the three-click guide
   that `apply plain seed` is today.)
6. **Ready.** The window shows the student's Auto Apply queue, the paste
   box, Start, and the Usage cap ("Model use this month: 0 of 3,000,000
   tokens").

The seed is made once. Each Worker's profile is copied from it the first
time that Worker is needed, then kept: it holds its own sign-ins between
Applications and runs. Every Worker profile is its own Chrome user data
folder (`--user-data-dir`): none of it shows in the student's own Chrome
profiles, and nothing of theirs changes.

### 3.2 A run

1. The student presses Start. The app downloads the Fill engine for its
   version (W7), unless it already holds this launch's copy in memory.
2. The Orchestrator gives one Application to each Worker (two by
   default). Each Application goes as in section 4.3, with these v1
   changes:
   - Model calls go to the Model route (W1), with personal data replaced.
   - The company brief comes from WorkIt (W9). No research.
   - A job system with no Filler gets the generic Filler (W2); what it
     can't fill is a Handoff. A field a Filler fails on is a Needs-you
     item; there is no Rescue.
   - An emailed code is a Needs-you item; Apply reads no mail.
3. The window shows each Worker's tile. When the student must act (a
   captcha, a sign-in, a Needs-you item, Submit), the app brings that
   Worker's Chrome window to the front.
4. Each form stops on its last page. The student checks it and presses
   Submit in the Worker's window. Apply writes the Tracker on WorkIt.
5. At the Usage cap, the run pauses with "Monthly model use reached;
   resets on <date>". The window always shows the use so far.

### 3.3 The processes

```
WorkIt Auto Apply (one compiled app)
 ├─ window: pywebview (WKWebView), no port ◄── bridge ──► Python core
 ├─ Node: the Fill engine, from memory (stdin), never from a file
 ├─ Chrome Worker 1 (CDP)    ◄── Playwright, debugging port on 127.0.0.1 (D22)
 ├─ Chrome Worker 2 (plain)  ◄── socket file ── host relay ── native messaging ── Worker extension ── debugger
 └─ HTTPS to api.workitjobs.ai (pinned): sign-in, Model route, usage, engine, briefs, queue, Tracker
```

`worker_mode: protected` stays: plain Workers fill the hosts that block
CDP Workers (Lever, SmartRecruiters, Workable and each host where Apply
saw a block), and CDP Workers fill the rest (section 4.7).

### 3.4 What leaves the computer

| To | What | When |
|---|---|---|
| WorkIt | Each model call's prompt with personal data replaced; tokens used | Each call |
| Groq, Google (Gemini) | The same prompt, sent by WorkIt with WorkIt's key | Each call |
| WorkIt | Tracker writes, answers the student approves, the queue | As today (`apply-agent/docs/workit.md`) |
| WorkIt | One Application's Record and masked Trace | Only when the student presses "Send report" |
| Job sites | The form's answers, in the Worker's Chrome | As a person filling the form |

**Replaced before a prompt leaves** (D8): the name, email, phone, street
address and ZIP code, birth date, links to personal profiles (LinkedIn,
GitHub, portfolio) and student ID, each with a placeholder such as
`@NAME@` (essays already use it). The app puts the real values back into
the answer. **Never sent:** self-ID answers (gender, race, disability,
veteran status). **Kept, because essays need them:** school, major,
graduation date, city and state, employers and the text of the student's
stories. **Not caught:** other people's names inside a story.

### 3.5 What stays on the computer

| What | Where |
|---|---|
| The data folder: Records, Traces, the Worker profiles, the seed, the local copy of the student's data | `~/Library/Application Support/WorkIt Auto Apply` (`%APPDATA%` on Windows) |
| The WorkIt session; Employer account passwords (passwords Apply makes for job-site accounts) | `keyring`: macOS Keychain, Windows Credential Manager. The student can see and change them in Keychain Access |
| The Fill engine | Memory only, for one launch |

WorkIt never holds a student's job-site passwords: a breach would expose
every student's accounts. A new computer starts with no saved job-site
accounts.

### 3.6 What v1 does not do

- No model drives the browser: no Claude fill, no Rescue, no Ask Claude
  (F1).
- No company research; no brief where WorkIt has none (F2).
- No Gmail: emailed codes and links are the student's.
- No scheduled runs, no phone push, no Daily sweep.
- No Intel Macs, no Windows (F8, F4).
- No paid model tiers (F3).

## 4. How Apply works today

Background for every workstream. Apply is the Python package in
`apply-agent/` (`pyproject.toml`, entry point `apply = "apply.cli:main"`),
installed with `uv sync`, macOS only, nothing packaged.

### 4.1 The processes in a rehearsal

```
terminal: uv run apply rehearse <links>
 └─ Python (Apply)
     ├─ web server on 127.0.0.1   ← the Apply window (Chrome --app) calls it (dashboard.py)
     ├─ Node (Fill engine)        ← reads question sets, plans, checks
     ├─ Chrome worker-1, -2, -3   ← one process, profile and window for each Worker
     └─ claude -p (many, short)   ← only with ask_model: claude, and for drive and research
```

`~/Applications/Apply.app` is not a real app: `dock_app.py` writes an
`Info.plist`, an icon and a shell script so the Dock shows "Apply" and
not a second "Google Chrome". D10 drops it.

### 4.2 Who reads the questions

The Fill engine reads them, not a model. A model gets only the questions
the planner could not answer.

```
question set ─► engine planner ─┬─ answered from profile + answer bank
                                ├─ Missing facts ─► Needs you
                                └─ essays + one-off questions ─► ask (text)
                                                                   │
                                     gates (plain code) ◄──────────┘
                                          │
                                          ▼
                              one plan ─► the engine fills the page
```

The engine is a JavaScript bundle (`autofiller_extension/fill-engine/dist/engine.js`,
about 590 KB), the same build the WorkIt extension loads. Python runs it
in a long-lived Node process (`fill_engine.call_without_page`) and inside
each page.

### 4.3 One Application, step by step

1. Resolve the link: the hiring system, the company, and a Greenhouse,
   Lever or Ashby form inside a careers page.
2. Check whether the student already applied. If so, stop.
3. Get a tailored resume from WorkIt, if the posting has one.
4. Read the posting's text, by API or a plain fetch. Plain code checks
   eligibility and text aimed at AI agents.
5. Read the question set: from the hiring system's API (Greenhouse,
   Lever, Ashby), from the page (Workday), or by Claude fill on a site
   with no Filler.
6. Open the form. The submit guard goes into every page before the
   site's own code.
7. The planner answers the routine questions from the profile and the
   answer bank. Missing facts go to Needs you.
8. `ask` writes what is left: essays, one-off answers.
9. Plain-code gates check each essay: caps, names, not-on-resume.
10. The engine fills the form, then reads every field back; a wrong
    read-back is re-planned once.
11. Verify: plain-code checks, then a Pre-submit review.
12. Stop on the last page and write the Record. The page is the
    student's.

### 4.4 Model calls today

Every call goes through one adapter (`Adapters.claude`) with three kinds
of call:

| Kind | Jobs | Goes to today |
|---|---|---|
| `ask`: text in, JSON out | Essay plans and essays, edits and checks, one-off answers, re-plans, the Pre-submit review, the team's name, the story map | `ask_model`: Groq, then Gemini, by default; `claude -p` for a developer who sets `claude` (`apply-agent/docs/ask-model.md`) |
| `research`: web search over many turns | Company briefs (`brief.py`) | `claude -p`, Sonnet |
| `drive`: the model controls the page | Claude fill (`claude_fill.py`), Rescue (`rescue.py`), Ask Claude | `claude -p`, Haiku, through Playwright MCP |

`ask_model.HostedAsk` takes over only `ask`; the other kinds go to
`claude -p` unchanged. In the Student build, `ask` goes to the Model
route (W1), `research` is gone (D2) and `drive` is gone (D13).

**Claude fill** is the Filler for a hiring system Apply has no Filler for
(Oracle, iCIMS, TAL.net, company-built forms). Claude reads the form,
the planner and the writer answer it, and Claude types the planned
answers in. Caps: 40 turns and 400,000 tokens per Application. **Rescue**
fills one field a scripted Filler failed on (Workday, Eightfold): up to
15 turns and 150,000 tokens per field. Both run under the drive guard and
the submit-click hook, and neither writes an answer itself
(`apply-agent/docs/claude-fill.md`).

### 4.5 How Apply controls Chrome

| Worker | Path from Python to the page |
|---|---|
| CDP | Python → Playwright → Playwright's Node driver → CDP over a debugging port on `127.0.0.1` → the page |
| Plain | Python → socket file → host relay (Chrome starts it) → native messaging → Worker extension → the page |

**CDP Workers.** Apply starts real Google Chrome on `profiles/worker-N`
with `--remote-debugging-port=0` (`browsers.py`) and connects Playwright.
Input is trusted. The engine runs through `page.evaluate`; tiles come
from CDP screencast frames.

**Plain Workers** (`apply-agent/src/apply/plain/`, protocol in
`apply-agent/docs/plain-workers/PROTOCOL.md`). Chrome starts with no
debugging port, no `--enable-automation` and no headless mode.
`PortPage` copies Playwright's `Page` API, so Fillers, the engine and the
guards run unchanged. Today the Worker extension (about 3,000 lines in
`apply-agent/worker-extension/`) runs code in pages three ways:

- its own packaged ops (`ops/*.js`, `page/*.js`): tabs, clicks, tiles,
  typing;
- files that `apply plain prepare` writes into the extension's `vendor/`
  folder before each launch: the Fill engine (`vendor/engine.js`,
  injected as a file, `ops/engine.js`), the guard scripts (registered as
  content scripts in every frame at `document_start`, `ops/guard.js`),
  `fixed.js` (the page functions a held page runs on each turn) and
  `injected.js` (Playwright's injected script);
- Apply's other page code (each `page.evaluate` with no fixed copy)
  through `userScripts.execute` (`ops/core.js`), or through `eval` where
  user scripts are off and the page's CSP allows it.

It types through its own `chrome.debugger`, attached only while text goes
in (`ops/typing.js`); Workers start with `--silent-debugger-extension-api`,
so Chrome shows no debugging bar. The extension is loaded unpacked into
the seed by the student's own clicks (`apply plain seed`: Developer mode,
Load unpacked, Allow User Scripts), and each Worker profile copies the
seed. W6 changes the last two ways (section 6, W6).

A model never touches Chrome directly. It names an action, and Apply's
code carries it out on whichever path the Worker has
(`apply/plain/tools.py`, `apply/plain/mcp_tools.json`).

### 4.6 Why a desktop app, and not only the website

A web page can't drive another site (the same-origin policy), start
Chrome or pick profiles. The extension path fills in the student's own
Chrome, in background tabs, with an MV3 service worker that Chrome
stops when idle (`auto-apply/architecture.md` §10). Apply avoids those
limits: each form is the active tab of its own Worker's window, Workers
pass the anti-throttling switches, Python holds the run, and the native
messaging port keeps the Worker extension's service worker alive. A
Worker must never be minimized: a minimized window stops painting.

Cloud browsers (Chrome on WorkIt's servers) are not a path: data-center
IPs are blocked far more often, the student's sign-ins would live on
WorkIt's servers, and the cost is highest.

### 4.7 Worker mode and the plain Workers' tradeoffs

`worker_mode: protected` (the default since 2026-11-06): plain Workers
fill the hosts that block CDP Workers (`plain_worker_hosts`: Lever,
SmartRecruiters, Workable, and each host in `APPLY_HOME/plain-hosts.json`
where Apply saw a block); CDP Workers fill the rest. `protected` picks
the kind once per host, before the form opens. Switching kinds in the
middle of a form to pass a check is evasion and out of scope.

Plain Workers' tradeoffs: most input is synthetic (`isTrusted: false`)
except the debugger's typing and choice clicks; pop-ups and file pickers
need workarounds; `captureVisibleTab` allows about two captures a second
(the smooth tile needs macOS Screen Recording and a Swift helper today);
request control is weaker; `PortPage` copies Playwright by hand; and
Chrome's MV3 rules can change. A plain Worker removes one signal, the
automation channel. A site can still read synthetic input, timing, the IP
and captcha scores.

## 5. The Developer checkout, the repo, testing and CI

### 5.1 The repo (D29)

`workitjobs/apply-agent` is private (created 2026-11-13, one README
commit). W0 moves `apply-agent/` there with its history. The Fill engine
becomes its submodule at `fill-engine/`. The WorkIt repo keeps the API
routes, the website pages and a pointer. The old commits stay readable in
the WorkIt repo's public history: the move protects only what comes after
it.

### 5.2 Setup (D31)

```
git clone --recurse-submodules git@github.com:workitjobs/apply-agent.git
cd apply-agent && uv sync
uv run apply app
```

The window's first run does the rest, as for a student (section 3.1):
sign-in against the local API, the Chrome check and the seed. Doctor's
checks become first-run checks. Claude Code is needed only for
`ask_model: claude`. A developer loads the Worker extension unpacked
from the checkout, so it can change without a store release; its ID is
pinned by the manifest's `key`, and the native host accepts both that ID
and the store's.

### 5.3 Which model a Developer checkout uses (D30)

| `ask_model` | Calls go to | Keys |
|---|---|---|
| `workit` (the default after W0) | The Model route of the WorkIt API the checkout points at: `http://localhost:8000` unless set | Only in WorkIt's `backend/.env` |
| `[groq, gemini]` | Groq and Gemini directly (`ask_model.py`) | The new repo's own `.env`, or `GROQ_API_KEY` and `GEMINI_API_KEY` |
| `claude` | `claude -p` on the developer's own login, full prompts; `drive` and `research` too | The developer's Claude Code login |

The Student build has none of these choices: it always uses `workit`
against `https://api.workitjobs.ai`.

### 5.4 Testing while the app is built

1. **From source, every day.** `uv run apply app` runs the real window
   and first run with no compile step. It points at the local API (`npm
   run dev` in the WorkIt repo, or Superset's Run button). Sign in with
   the shared test account (`frontend/CLAUDE.md`, "Auth and the API").
2. **On real forms.** Start a posting from the window or the paste box.
   The form stops on its last page; never press Submit on a real posting
   in a test.
3. **As a real app.** A developer runs the build script on a Mac (W8)
   and installs the result, or sends it to testers through Sparkle's beta
   channel. Testers outside the team need the Apple enrollment first,
   because macOS blocks an app signed by no one.

There is no staging server. Tests that reach production use the shared
test account.

### 5.5 CI (D32)

GitHub-hosted Linux runners, on PRs only: `uv run ruff check .` and a
short list of fast tests (no browser, no network, no `claude`), a few
minutes in all. No macOS runners, no builds, no version tags. Builds run
by hand (W8).

## 6. Workstreams

| # | Workstream | Waits for | v1 |
|---|---|---|---|
| W0 | Move Apply to `workitjobs/apply-agent` | KAN-723 merged into WorkIt's `main` | Yes, first |
| W1 | Model route and Usage cap | None | Yes |
| W2 | Filling with no model in the browser | None | Yes |
| W3 | What the Student build leaves out | None | Yes |
| W4 | Remove macOS-only code | None | Yes |
| W5 | The app shell | W3, W4 (and W1 for sign-in and usage) | Yes |
| W6 | The Worker extension on the store (spike first) | None | Yes |
| W7 | The engine download and its protection | W1 (sign-in) | Yes |
| W8 | Compile, sign, notarize, update, publish | W3, W4, W5 | Yes |
| W9 | Company briefs in v1 | None | Yes |
| W10 | Legal | None | Yes |
| W11 | The student's data | A teammate | Yes (not ours) |
| W12 | One mode: remove Rehearsals and `live_runs` | W0 | No |
| W13 | Measure quality and model use | W1 | Yes, for the cap |

Every workstream that adds or changes a click path, or touches
`submit_guard.py`, `plain/guards.py`, `send_click.py` or a guard flag,
gets the adversarial review (root `CLAUDE.md`, KAN-666) and new cases in
`tests/test_submit_guard_hostile.py`. Claude never runs `alembic
upgrade`: a workstream that adds a table writes the migration and asks
the user to apply it (root `CLAUDE.md`).

### W0. Move Apply to `workitjobs/apply-agent`

**Goal.** Apply's code in a private repo, with its history, before any
code that must stay secret lands.

**Steps.**

1. Merge KAN-723 into WorkIt's `main`. Ask teammates to merge or hold
   their open `apply-agent/` PRs for one day.
2. On a fresh clone: `git filter-repo --subdirectory-filter apply-agent`.
   Apply's files and history are then at the root.
3. Add the Fill engine as a submodule at `fill-engine/`, and fix every
   path that points outside Apply:
   - `fill_engine.py` (`parents[3] / "autofiller_extension" / "fill-engine"`);
   - `ask_model.DOTENV` (WorkIt's root `.env`);
   - `repairer.py` (`ENGINE`, `FROM_APP`, the prompt's paths) and Repairs'
     merge target;
   - `native_host.py`'s note on the WorkIt extension's ID;
   - links into WorkIt's `docs/` from Apply's docs and code comments.
4. Push to the new repo's `main` once, with force, to replace the
   README-only commit. The user says yes to the force push at that time.
5. Add the new repo's CI (D32) and `ask_model: workit` as the Developer
   checkout's default (D30), once W1's route exists.
6. In WorkIt: delete `apply-agent/`, remove the `apply` job from
   `.github/workflows/ci.yml` (and `apply-nightly.yml`), and replace the
   root `CLAUDE.md`'s Apply section with a pointer. Move this doc and
   ADR 0005 to the new repo; keep a short server-side note in WorkIt's
   `docs/`.

**Done when.** The new repo's CI passes, a Developer checkout runs a form
to its last page, and WorkIt's CI passes without `apply-agent/`.

### W1. Model route and Usage cap

**Goal.** Every model call of a Student build goes through WorkIt, is
counted, stops at the cap, and carries no personal data.

**The server (WorkIt repo, `backend/`).**

- **Routes** (names to settle in the PR), each signed in as the student:
  - `POST /apply-app/model`: body `{kind, model, system, prompt, schema}`.
    `model` is Apply's tier (`haiku`, `sonnet`, `opus`); WorkIt maps it
    to a provider's model. The server runs the provider chain that
    `apply-agent/src/apply/ask_model.py` runs today (Groq, then Gemini;
    strict schemas; moving on at 413, 429 and 5xx; `_misfit` checks), with
    the keys from the API's secrets (`CF_API_SECRETS_JSON`). It answers
    `{answer, tokens}`.
  - `GET /apply-app/usage`: `{used, cap, resets_at}`.
  - At the cap, `POST /apply-app/model` answers 429 with `resets_at`.
- **Table** `model_usage`: one row per student per month (`applicant_id`,
  `month`, `input_tokens`, `output_tokens`, `calls`). A new Alembic
  migration that enables RLS with no policies (root `CLAUDE.md`).
- **The cap** (3,000,000 tokens) is a server setting, so it changes with
  no app update. A short per-student rate limit (requests a minute)
  protects the free tiers, which every student shares.
- **Logs** keep no prompt text: only the student, the kind, the model and
  the tokens.

**The app (Apply).**

- `ask_model: workit`: a provider in `ask_model.py` whose endpoint is
  the Model route and whose key is the student's WorkIt session. The
  lean prompts stay (`adapters.lean`).
- **Personal data out, back in** (D8, section 3.4): one module replaces
  each personal value with its placeholder before `ask` sends, and puts
  the values back into the answer. Self-ID answers are never in a
  prompt. Tests check that no profile value of the listed kinds reaches
  the request.
- **The Orchestrator's limit.** Today it pauses on Claude Code's 5-hour
  and weekly windows (`orchestrator._resume_at`, `adapters.usage`). The
  Student build reads `GET /apply-app/usage` instead and pauses at the
  cap with its reset date.
- **Send report** (D26) uploads one Record and masked Trace through a
  WorkIt route; the server keeps it for the team.

**Waits for.** Nothing. Sign-in (W5) supplies the session in the app; a
developer can test with an existing WorkIt token.

**Done when.** A Developer checkout with `ask_model: workit` against the
local API writes a form's essays, the usage row grows, a cap set low
pauses the run with its date, and a request captured in a test holds no
personal value.

**Open.** The route's exact names; whether the server keeps the
`[groq, gemini]` chain or adds Cloudflare AI Gateway in front of it for
logs.

### W2. Filling with no model in the browser

**Goal.** v1 fills without `drive` (D13).

**Design.**

1. **Handoffs first** (needed in every case): in the Student build, a job
   system with no Filler and no generic fill is a Handoff to the student
   in that Worker's window; a field a Filler fails on (today a Rescue)
   is a Needs-you item on the held form, with the planned answer shown.
2. **The generic Filler**, behind the same `Filler` shape
   (`apply/fillers.py`), on CDP and plain Workers alike:
   - **Read with no model.** Chrome's accessibility tree gives each
     control its role and label. A textbox is a text question, a combobox
     or radio group a select with its options, a checkbox a yes/no.
     Generic code opens each custom dropdown, reads its options and
     closes it.
   - **Act with plain code; the model only picks.**

     | Control | Plain code | The model's question, when needed |
     |---|---|---|
     | Textbox, textarea | Fill the planned answer | None |
     | Native `<select>` | Pick the option; `fit.ts` maps the value | None |
     | Checkbox, radio | Click the one whose name fits | Which of these names means the answer? |
     | Custom dropdown, search box | Click, type to filter, read, match with `fit.ts` | Which of these options is the answer? |
     | Two-level list | Open it, read the groups | Which group holds the answer? |
     | File upload | Set the file | None |
     | Next | Claude fill's `NEXT` and `BACK` patterns | Which of these buttons goes on, without sending? |

   - **The model's question is a small `ask`** through the Model route:
     `{"choice": <number> | null}` for one field's few options, about a
     hundred tokens. Example: Workday's "How did you hear about us?" with
     groups Job Board, Social Media, Employee Referral, Career Fair, and
     the answer "LinkedIn": `fit.ts` finds no "LinkedIn", the model picks
     group 1, code opens it, `fit.ts` finds "LinkedIn", code clicks it
     and reads the field back.
   - **What goes to the student:** a page in an unexpected state (an
     error banner, a pop-up, a reset field), a widget missing from the
     tree (a canvas date picker, drag and drop), and a step whose end is
     not clear.

**Touches.** `claude_fill.py`, `rescue.py` (their Student-build paths),
`fillers.py`, `orchestrator._apply_with`, a new generic Filler module,
`apply/plain/tools.py` for its narrow tools.

**Done when.** On the engine's saved forms (`uv run apply plain fill
<saved-form>` serves one on 127.0.0.1 and refuses every POST) and on
long-tail postings that Claude fill fills today, the generic Filler's
share of fields filled right is measured against Claude fill's, and
every field it can't place is a clear Needs-you item or Handoff. The
generic Filler's clicks pass the adversarial review.

### W3. What the Student build leaves out

**Goal.** The Student build holds no developer part, and nothing in it
can turn one on (D14).

**Left out** (kept in the Developer checkout):

- `claude_cli.py` and every `claude -p` path: `ask_model: claude`,
  `research` (`brief.research`), `drive` (Claude fill, Rescue, Ask
  Claude), Repairs (`repair.py`, `repairer.py`, `work`), Claude Code's
  usage reading;
- mail: `gmail.py`, `email_code.py`'s Gmail lookups, Employer mail, `apply
  mail` (D9: the code is a Needs-you item);
- `schedule.py`, `notify.py` (ntfy), `dock_app.py` (D10);
- `sheet_import.py`, `clean-tracker`, `apply ask` and every command that
  only runs from a terminal; `doctor.py`'s developer checks;
- `live_runs` and its paths (fixed off; W12 removes them everywhere).

**Design.** One build constant (for example `apply.build.STUDENT`) that
the build script sets. Developer modules are not imported on the Student
path, and Nuitka leaves them out of the compile (W8). The Student build
reads no developer keys from `policies.yaml`: its few settings (the
Worker count) live in the window.

**Done when.** A Student build's file list holds none of the modules
above, and a test proves that setting `ask_model: claude` or `live_runs:
true` in its data folder changes nothing.

### W4. Remove macOS-only code

**Goal.** No macOS command or path in the code the Student build runs,
so the Windows port (F4) is a port, not a rewrite.

| Module | macOS part today | Change |
|---|---|---|
| `keychain.py`, `brief.py`, `gmail.py` | `security` | `keyring` (Keychain on Mac, Credential Manager on Windows). Items left: Employer account passwords (`apply-ats`) and the WorkIt session |
| `workit.py` | Session in `workit-login.json`; sign-in through Chrome's debugging port | Session in `keyring`; sign-in through the browser and `workit-auto-apply://` (W5) |
| `notify.py` | `osascript` notifications, ntfy | Dropped: the window shows notices |
| `schedule.py`, `cli.py` | `launchctl`, `~/Library/LaunchAgents` | Dropped |
| `dock_app.py` | The Dock bundle | Dropped: the app is its own bundle |
| `dashboard.py` | `open`, `osascript`, `pgrep`, Chrome `--app` | Replaced by the pywebview window (W5) |
| `focus.py`, `captcha.py` | `osascript`, `open` | Bring the Worker's window forward through Chrome (`Page.bringToFront`, or `chrome.windows.update` through the Worker extension) |
| `accounts_tab.py` | `osascript` clipboard (`MacClipboard`) | A cross-platform clipboard |
| `browsers.py`, `plain/launcher.py`, `cover_letter.py`, `workit.py` | `/Applications/Google Chrome.app` | One Chrome finder per OS. Windows: `C:\Program Files\Google\Chrome\Application\chrome.exe`, then the per-user folder |
| `plain/launcher.py` | `open -g -n -a` | Start Chrome as a background process per OS |
| `plain/window_capture.*` | Swift and ScreenCaptureKit | Dropped: tiles come from the debugger's screencast (W6) or the extension's frames |
| `plain/seed_setup.py` | `open -R`, `pbcopy`, `ps` | The store install needs none of them (W6); the fallback guide uses cross-platform calls |
| `native_host.py`, `plain/launcher.py` | `~/Library/...` paths | Per-OS paths; the data folder through the standard per-OS place (D25) |

**Done when.** A search of the Student build's modules for `osascript`,
`security`, `launchctl`, `open`, `pgrep`, `pbcopy`, `/Applications/` and
`~/Library/` finds nothing, and the moved features work on the Mac.

### W5. The app shell

**Goal.** One native window that does everything a student needs
(sections 3.1 and 3.2).

**Design.**

- **pywebview, no port** (D11). The window's page is today's Apply
  window (Start, Needs you, Answers, Accounts) without the Developer-only
  parts. Its 28 routes in `dashboard.py` (`/state`, `/start`, `/answer`,
  `/answers`, `/approve`, `/resume`, `/fill-again`, `/regenerate`,
  `/accounts`, `/frames`, `/stream/`, `/input/`, ...) become methods on
  pywebview's JavaScript bridge (`js_api`). Tiles' frames are pushed into
  the page through the bridge. The window shows in the Dock while open,
  as every Mac app does.
- **Sign-in** (D12):
  1. The app makes a PKCE verifier and challenge and opens
     `https://workitjobs.ai/app-sign-in?challenge=…&state=…` in the default
     browser (a new website page).
  2. The page signs the student in as the website does, then asks the
     API for a one-time code bound to the challenge, and opens
     `workit-auto-apply://signed-in?code=…&state=…`.
  3. The app (registered for the scheme in its `Info.plist`) sends the
     code and the verifier to the API and gets the session. The session
     goes into `keyring`; the app refreshes it as `workit.py` does today.
- **First run:** the Chrome check (D21), the disclosure (D8), the seed
  (W6), then Ready.
- **A run:** the Auto Apply queue from WorkIt (the batch routes in
  `backend/app/routers/auto_apply.py`), the paste box, Start, tiles,
  Needs you, the Usage cap line (W1).
- **Settings:** the Worker count (one to three, default two), "Remove all
  my data" (D25), "Send report" (D26), the disclosure, sign out.
- **Notices** replace phone push: the window and macOS's own notification
  for "needs you".

**Touches.** `dashboard.py`, `accounts_tab.py`, `workit.py`, a new app
entry point (`uv run apply app`), new website page and API routes in the
WorkIt repo.

**Done when.** From a Developer checkout, `uv run apply app` takes a new
user from sign-in to a filled form held on its last page, with no
terminal step and no open port.

### W6. The Worker extension on the store

**Goal.** One click to add the Worker extension, from the Chrome Web
Store, under the store's rules (D4).

**Why the change.** The store allows code from outside the extension's
package only through the Debugger API or the User Scripts API, each for
its stated purpose; the User Scripts API is for code the user writes.
Today the extension runs Apply's page code (the `eval` op) through
`userScripts.execute`, and loads files that `apply plain prepare` writes
into its `vendor/` folder: the engine, the guard scripts, `fixed.js` (the
fixed page functions) and `injected.js` (Playwright's injected script). A
store extension's folder belongs to Chrome, so Apply can't write there.
The store also forbids obfuscated code, including code the extension
runs; minified code is allowed.

**The change: the debugger carries what changes; the rest is packaged.**

| Today | In the store copy |
|---|---|
| `vendor/engine.js` written into the extension's folder, injected as a file | Apply sends the engine's text over native messaging once per connection (`cdp.keep`, checked by its sha256; Apply splits any message over 512 KiB); the extension holds it in memory and runs it through the debugger (`cdp.load`). No engine file on disk |
| `userScripts.execute` for Apply's page code that has no fixed copy (`ops/core.js`) | `cdp.eval` through the debugger, with `Runtime` never turned on |
| The guard scripts, `fixed.js`, `injected.js` and `page/relay.js` as `vendor/` files Apply writes, registered as content scripts | The same files packaged in the extension at its build, each checked against Apply's sha256. Chrome puts a registered content script in every tab and frame itself, pop-ups included; the debugger can't (measured) |
| Tiles through `captureVisibleTab`, about 2 a second; Swift for smooth tiles | `Page.startScreencast` (not built yet) |
| Packaged ops (tabs, clicks, typing) | Unchanged |

A guard change then needs a store release before the app that expects
it: Apply already refuses a guard file whose sha256 isn't its own.

The `userScripts` permission goes, so the student never turns on Allow
User Scripts and needs no Developer mode. The extension keeps
`nativeMessaging` and `debugger` (and host access, if attaching needs
it). Chrome's install dialog then says "Access the page debugger
backend" and "Communicate with cooperating native applications". Students
with Enhanced Safe Browsing on may also see "Proceed with caution" for a
developer without a trust history. Workers start with
`--silent-debugger-extension-api`, so no debugging bar shows.

**The spike (KAN-839, started 2026-11-13).** Built behind
`APPLY_PLAIN_EXEC=debugger`, off by default: `ops/cdp.js` and
`ops/debug.js` in the extension, `apply.plain.script` in Apply, and
`tests/test_plain_debugger.py` (`apply-agent/docs/plain-workers/guide.md`,
"Page code through the debugger"). Measured on Chrome for Testing 158 with
user scripts off:

1. **Frames from other sites: passed.** Page code and the engine reach the
   MAIN world of the top frame, a same-site frame and a frame from another
   site (its own process), on a page whose CSP forbids eval, where today's
   `eval` op fails. `Runtime` is never turned on: a page that watches for
   it sees nothing.
2. **Early scripts: passed for the tab, failed for pop-ups.** With
   `Page.enable`, an early script runs before the page's code in every
   frame of the tab, but never in a pop-up the page opens, a new tab
   outside the tab's debugger session. So the guards stay registered
   content scripts, packaged (the table above); no guard code moved.
3. **Bot signals: no change on three live postings.** The debugger stays
   attached for the whole form, not only while typing. One Lever, one
   Workable and one SmartRecruiters posting, rehearsed as Test Person in
   Chrome for Testing on both paths, ended the same way each (Lever held
   and verified; Workable failed on its Filler's Apply button; SmartRecruiters
   handed off when the guard refused a page worker), and no Trace held a
   captcha or a block. KAN-839 fixed both: Workable's form is then held on
   its last page, and Claude fill goes on past the page's refused worker. Still to check: branded Chrome on a real seed, and
   more postings.
4. **A whole form: passed on one saved form.** `lever-immuta` through
   `apply plain fill` gives the same read-back on both paths (13 of 13
   answers shown). Next and file upload on a multi-step form are still to
   test.

Left after the spike: item 3 in branded Chrome; the packaged files and a store build of the
extension; turning the switch on by default and removing the
`userScripts` path; the tile's screencast.

**If the spike passes:** list "WorkIt Auto Apply Worker", unlisted, from
WorkIt's existing developer account: a privacy policy link, one stated
purpose ("lets WorkIt Auto Apply control its own Chrome windows"), a
reason for each permission, and a license header in each file (W10).
The native host's manifest names the store's extension ID beside the
Developer checkout's unpacked one. The extension updates from the store
on Chrome's schedule, so the app and the extension check one protocol
version on hello (`PROTOCOL.md` already has a feature number) and the app
says "Updating the Worker extension" while they differ.

**If the spike fails:** v1 keeps today's extension off the store. First
run guides the student through Developer mode, Load unpacked and Allow
User Scripts (`plain/seed_setup.py` does this today), and the engine
still reaches the Worker in memory, not in a file.

**Touches.** `apply-agent/worker-extension/` (`ops/cdp.js`, `ops/debug.js`,
`ops/core.js`, `ops/guard.js`, `ops/engine.js`, `ops/tile.js`,
`background.js`, `manifest.json`), `apply/plain/` (`script`, `page`,
`bridge`, `extension`, `launcher`, `seed_setup`, `tile`),
`docs/plain-workers/PROTOCOL.md` and `guide.md`.

### W7. The engine download and its protection

**Goal.** The Fill engine never sits on the student's disk in plain text
and comes only from WorkIt (D3, D27, D28).

**Design.**

1. **Build and sign.** The Fill engine's CI builds `dist/engine.js` and
   signs it with an Ed25519 key kept in its GitHub secrets, then uploads
   the build and its signature to WorkIt (R2 or the API's storage) with
   the app versions it fits. This step is in the engine's repo, so its
   owners make it.
2. **Serve.** `GET /apply-app/engine?app_version=…` (signed in) answers
   the newest build that fits, encrypted with AES-GCM under a key made
   for this launch; `POST /apply-app/engine-key` gives that key to this
   session only, for a short time.
3. **Load.** The app checks the signature with the public key compiled
   into it, decrypts in memory, and never writes the plain text:
   - the Node process gets the engine on stdin (today
     `fill_engine.call_without_page` loads a file path);
   - CDP Workers get it as text through `page.evaluate` and
     `add_init_script` (today `fill_engine.ENGINE` is a file);
   - plain Workers get it over native messaging (W6).
4. **Pinning.** The app's HTTPS client trusts only the certificate
   authorities that Cloudflare uses for `api.workitjobs.ai`, with backups.
   Sparkle's feed is on another host without pinning.
5. **No source maps** ship; they stay on WorkIt.

**A dependency outside this design.** The WorkIt extension ships the
minified engine in its public store package today, so anyone can read
it. The download above protects one copy while another is public. A
teammate's work on the engine's exposure through the extension must
close that gap, or most of W7's value is lost.

**Done when.** A Developer checkout runs a form with the engine from
the route, the data folder and the Worker extension's folder hold no
engine file, and a wrong signature stops the run with a clear message.

### W8. Compile, sign, notarize, update, publish

**Goal.** A signed, notarized `WorkIt Auto Apply.dmg` that updates
itself (D17, D18, D20).

**Design.**

- **Compile:** Nuitka, standalone, as a macOS app bundle, on Apple
  Silicon with macOS 13 as the minimum (`MACOSX_DEPLOYMENT_TARGET`). It
  holds Playwright's Node driver (`site-packages/playwright/driver/`) as
  data, pywebview, and none of W3's modules. Nuitka is AGPLv3 with an
  exception: the compiled app is not bound by the AGPL.
- **Sign:** Developer ID, with the hardened runtime and without
  `get-task-allow`, so other programs can't read the app's memory. Every
  Mach-O file inside is signed, the Node binary included, with the
  entitlements Node needs (JIT) and no more.
- **Notarize** with `notarytool`, then staple.
- **Update:** Sparkle with its own EdDSA key; the feed and builds on
  Cloudflare R2; a beta channel for testers. The app checks at launch and
  installs at the next restart.
- **Publish:** a download page on workitjobs.ai (WorkIt repo, `frontend/`)
  that says "Apple Silicon Macs (M1 and later), macOS 13 or later".
- **Build by hand:** one script (for example `scripts/build_app.py`) that
  compiles, signs, notarizes, makes the DMG and uploads it. No builds in
  CI (D32).

**Done when.** A clean Apple Silicon Mac on macOS 13 opens the
downloaded app with no warning beyond macOS's "downloaded from the
internet", runs a form to its last page, and takes a newer build through
Sparkle.

**Cost.** Section 9.

### W9. Company briefs in v1

**Goal.** Essays name real company facts with no research in the app
(D2).

**Design.** The app reads WorkIt's shared brief (`company_briefs`,
KAN-382; `backend/app/auto_apply/briefs.py`): one per company and one per
team a posting names, built today by extension students' Claude through
the connector and checked in code (each quote found on its page). WorkIt
already serves its facts (`brief_for`; `GET /jobs/{job_id}/company` for
the job page's Company tab); the app reads them through `apply/workit.py`
and turns them into the lines `essays.py` reads. Where WorkIt has no
brief, essays use the posting and the Company material only, and a "why
us" essay names no brief fact. The shared brief has no problem tags yet,
so the plan picks its fact without the tag match.

**Done when.** An essay for a company with a shared brief names one of
its facts, and one for a company with none still passes the gates.

### W10. Legal

**Goal.** The app and the Worker extension go out with free, adequate
terms (D16).

- **App license (EULA):** adapt Basecamp's open-source policies (CC BY
  4.0, archived; attribution required). Forbid copying, reverse
  engineering and use of the app or its output to train AI models.
- **WorkIt's `/terms`:** add a section for the desktop app.
- **WorkIt's `/privacy`:** name each outside service (Groq, Google's
  Gemini, Cloudflare, Supabase; Tavily when F2 is built) and section
  3.4's flows, including that Google's free tier may use prompts.
- **Third-party notices:** generated with `pip-licenses` (free) for the
  Python packages, plus Playwright's driver, pywebview, Sparkle (MIT) and
  Nuitka's runtime exception.
- **Chrome Web Store:** a privacy policy link and its user-data rules for
  the Worker extension; a license header in each of its files.
- **Not now:** a review of the hiring systems' terms on automated
  applying.

### W11. The student's data

A teammate owns it. Until their design lands, the app reads the student's
data as the Fill engine's code and `apply/workit.py` do now, and keeps
its local copy in the data folder. The answer bank's redesign, the data
contract (each fact Apply reads and the WorkIt table that serves it) and
the sync are theirs.

### W12. One mode: remove Rehearsals and `live_runs`

**Goal.** Apply never presses Submit, in any build (D33). Not a v1
blocker: the Student build already fixes `live_runs` off.

**Design.** Remove `live_runs`, the run versus Rehearsal split, the
guard's lift for Apply's own Submit click, the Daily sweep and the
Calibration and Backlog runs. `apply rehearse <link>` becomes the
window's paste box, or a short command in the Developer checkout. Update
the glossary (Rehearsal, Calibration run, Backlog run, Daily sweep) and
`apply-agent/CLAUDE.md`'s testing rules. The guard change gets the
adversarial review.

### W13. Measure quality and model use

**Goal.** Numbers for the cap and for quality.

1. Fill the same postings with `ask_model: claude` and `workit`, and
   compare answers and essays (a comparison outside a rehearsal on
   2026-11-10 found Groq's plainer but correct, `apply-agent/docs/ask-model.md`).
2. Count calls and tokens by call kind on about 20 forms across hiring
   systems: the tokens of one Application, which sets the app's "about N
   Applications left".
3. With W2: the generic Filler's share of fields filled right, against
   Claude fill.

## 7. Future work

Designed or noted, not scheduled. F1 is the next work after v1.

### F1. A hosted `drive` loop (next after v1)

Apply runs the loop itself and sends each tool call to Playwright (CDP)
or `apply/plain/tools.py` (plain), with `apply/plain/mcp_tools.json` as
the tool definitions. What Groq's gpt-oss models need
(https://console.groq.com/docs/tool-use, read 2026-11-10):

- Structured output and tools do not mix on Groq, so the loop ends with
  a `finish` tool whose parameters are the answer's schema, checked by
  Apply.
- No parallel tool calls on gpt-oss: one action per turn, which suits
  the guards.
- A Claude fill may use up to 400,000 tokens on one form, so each turn
  sends a trimmed snapshot of the form's part of the page, not the whole
  page. It needs a paid tier (F3).
- The caps on turns and tokens, the send-click hook, the drive guard and
  the captcha refusal stay. It is a new click path: adversarial review.
- Measure it against Claude fill on the same postings before it ships.

### F2. The company brief pipeline

**One brief format** (D15). Apply's own brief (`brief.py`) has, on each
fact, a type and problem tags; plus the mission, the values, the problems
the company states and its teams. WorkIt's shared brief has four
categories (products, launches, engineering, team) and none of the rest.
The shared format takes Apply's fields; WorkIt's categories map onto
them; the connector's save takes the same format. Briefs belong to
WorkIt, and the student no longer edits them.

**A company registry.** WorkIt has no table of companies: a brief is
keyed by the folded name (`briefs.company_key`), and each posting has a
`company_name` and often a `company_domain` (the website its job board
names, read by the scraper's `logos.py`, never guessed). The pipeline
needs to know which company to research: a `companies` table with the
key, the name, other names, website domains and job boards, filled from
the postings. A person reviews each merge of two names and each new
domain, as the scraper's Wikidata domain proposals are reviewed now. It
must handle one company under two names, two companies with nearly the
same name, and postings on a staffing agency's board.

**The pipeline.** A scheduled job fills the briefs no student has
researched and refreshes the stale and weak ones:

1. **Pick** the companies of open postings and students' queues whose
   brief is missing, older than `FRESH_DAYS` or under `STRONG` (the rules
   `research_task` uses).
2. **Gather in code, free sources first:** the posting's own text; the
   company's intro on its Greenhouse job board
   (`boards-api.greenhouse.io/v1/boards/{token}`); its own about, values,
   careers and team pages; its blog or newsroom feed (RSS or Atom); its
   GitHub organization; press news from GDELT's DOC 2.0 API (free, no
   key, about the last 3 months).
3. **Search with Tavily** for what those miss
   (https://docs.tavily.com/documentation/api-credits, read 2026-11-13):
   a basic search is 1 credit and an advanced one 2, up to 20 results;
   extracting page text is 1 credit per 5 pages. The free plan has 1,000
   credits a month, then $0.008 a credit. A brief needs about 3 to 6
   basic searches (an estimate): 125 to 250 briefs a month free. A credit
   is one search, not an answer. Our own search would need a web index;
   pages at known addresses need none, so step 2 stays ours.
4. **Read.** One `ask` call turns the text into facts, each with a quote
   copied from its page, its link and month, a type and tags, plus the
   mission and values word for word. It runs once per company, so it can
   use a bigger model on WorkIt's key.
5. **Check and save** with `briefs.py` as it is: each quote found on its
   page, the page on the company's own site or a news site, every number
   in its quote, and the brief kept only when it scores higher.

| Step | Runs | Model |
|---|---|---|
| Gather and search | Once per company | None |
| Read the pages into facts | Once per company | Bigger; the check catches a made-up fact |
| Plan: the fact that fits the student's story and the role | Once per essay | Bigger |
| Write the essay from the plan's slots | Once per essay | Smaller; test it first |

**Work it needs:** a save with no student (`save_brief` refuses a company
the student doesn't apply to, `NotApplying`), the one format, the
registry, and a place to run. **Open:** where it runs (GitHub Actions on
GitHub's runners, or the team computer after the scrape, KAN-726), which
model reads, how often it refreshes, and Tavily's terms for a paid
product. A Tavily query holds no student data.

### F3. Paid model tiers

Groq's Developer plan (pay per token; gpt-oss-120b $0.15 in and $0.60 out
per million tokens, read 2026-11-10) and Gemini's paid tier, before the
beta grows past invited testers. Paid terms don't use prompts for
training, and `drive` (F1) needs the larger limits.

### F4. Windows

| Part | macOS | Windows |
|---|---|---|
| Native host manifest | A JSON file in each Worker profile's `NativeMessagingHosts/` | A registry key under `HKCU` that names the manifest |
| The host's launcher | A shell-script wrapper | An `.exe` or `.bat` wrapper |
| Apply ↔ host channel | A socket file | A named pipe (no port) |
| Starting Chrome in the background | A background process | A process with no focus |
| Window | pywebview on WKWebView | pywebview on WebView2 |
| Secrets | `keyring` on Keychain | `keyring` on Credential Manager |
| Signing | Developer ID and notarization | A code-signing certificate, so SmartScreen doesn't warn |
| Updates | Sparkle | WinSparkle or similar |

Test early: background-window behaviour (`--disable-backgrounding-occluded-windows`
reads window cover differently per OS) and the native host under a
school's managed Chrome.

### F5. One Worker kind with no port

If W6's debugger path fills every host as well as CDP Workers do, CDP
Workers move onto it too: one Worker kind, no debugging port, the same on
every OS.

### F6. The brain and the hand, and writing on WorkIt

The strongest protection keeps the valuable code on WorkIt's server.

- **The hand** (in the page, JavaScript): generic DOM steps only (list
  the controls with roles and labels, click element n, type into element
  n, read it back, wait for a change). No rules, no per-system tricks.
  It is also the way to a fully static store extension.
- **The brain** (on WorkIt's server): the planner, the rules, `fit.ts`
  and each hiring system's widget recipe, sent to the hand as data ("click
  the box, wait for the list, pick the group").
- **The label cache:** the app keeps the server's results for each
  label (its meaning and its fit to an option list), never the rules. Key:
  the label in a standard form, the control type, the option list and the
  engine version. The value always comes from the student's current
  data; a new engine version clears the cache.
- **Writing on WorkIt:** the app sends the questions and the data, and
  WorkIt builds the prompts, so the prompts and answering guides leave
  the app (D5's later step).

Costs: one call per form for the plan, no planning while WorkIt is
offline, and a large refactor of the engine.

### F7. An Apple organization enrollment

Register a company (an LLC: a state filing fee of tens to hundreds of
dollars, some states yearly; an EIN from the IRS, free), get a D-U-N-S
number (free, days to weeks), then ask Apple to convert the individual
membership. Apple's support says the Team ID stays; get it in writing
first, because `keyring` items are tied to the app's signature.

### F8. Intel Macs

One more build: an Intel Python and every library for Intel (Rosetta can
run them on an Apple Silicon Mac until Apple limits Rosetta after macOS
27), then either a universal app (each compiled file merged with
`lipo`; about twice the size) or a second download. It needs a test on a
real Intel Mac.

### F9. Emailed codes from Gmail

Gmail through OAuth needs Google's paid security review, the reason
WorkIt's Inbox is archived (`docs/email_tracker.md`). Until then the
student types each code.

## 8. Who can see the code

Anything that runs on the student's computer can be read in the end;
each step only raises the cost.

| Part | Where it is | Protection |
|---|---|---|
| Apply's Python | The private repo; machine code in the app | Nuitka. Strings (prompts) still show to a tool that reads the binary; F6 moves the prompts to WorkIt |
| Answering guides and prompts | Data inside the app | Compiled in; F6 moves them |
| The Fill engine | WorkIt; the app's memory; each page while it fills | Signed, encrypted download, per-launch key, pinning, no file on disk (W7). In the page it is plain JavaScript that DevTools can show. The WorkIt extension's public copy is a teammate's work |
| The Worker extension | The Chrome Web Store, readable by anyone | Little of value in it (generic browser steps and the submit guard); the license (W10). The store forbids obfuscation |
| Model keys | WorkIt's API secrets only | Never in the app (D1) |
| Job-site passwords, the WorkIt session | `keyring` on the student's computer | The OS's safe store |
| The app's memory | The running app | The hardened runtime without `get-task-allow` blocks other programs, but not a root user or one who turns off System Integrity Protection |

**Minify and obfuscate are different.** Minifying (a teammate's work for
the engine) removes spaces and comments and shortens names; DevTools'
pretty-print restores the layout, and every string and regex stays
readable. Obfuscating encodes strings and scrambles control flow, slows
the code, and is forbidden for code that passes through a store
extension. Heavy packers and anti-debug code also make antivirus and
notarization flag the app. Neither stops a reader with time; F6 does.

**Other desktop apps ship readable code too** (checked 2026-11-09).
Electron apps ship their JavaScript in an `app.asar` archive (a file
list and the files' bytes, not encrypted); on one team Mac, Slack's held
954 files, 518 of them minified but readable JavaScript. Electron's docs
say it hides code "from cursory inspection" only. Those companies keep
their value on their servers; WorkIt Auto Apply does the same.

## 9. Costs

| Item | Cost |
|---|---|
| Apple Developer Program (Developer ID, notarization included) | $99 a year (the fee waiver is for nonprofits, accredited schools and governments, never individuals) |
| Chrome Web Store | $0: WorkIt's existing developer account already paid the $5 fee |
| Sparkle | Free (MIT) |
| Cloudflare R2 for builds and the update feed | Free tier: 10 GB stored, no fee for downloads |
| Nuitka | Free (AGPLv3 with a runtime exception); Nuitka Commercial, for extra protection, about €400 |
| Model calls in the beta | Free tiers (D7); paid tiers later (F3), cost per Application from W13 |
| Tavily (F2, not v1) | 1,000 free credits a month, then $0.008 a credit |
| GitHub Actions | Small Linux jobs on PRs only (D32) |
| **Fixed total for v1** | **About $99 a year** |

## 10. Open questions

- The W6 spike's result: the store with the debugger, or the
  three-click fallback.
- The Usage cap's number after W13, and when to move to paid tiers (F3).
- Where the brief pipeline runs, and when it is built (F2).
- The teammate's work on the engine's exposure through the WorkIt
  extension (W7's dependency).
- When to enroll with Apple, and when to convert to an organization (F7).

## 11. History

- **2026-11-06:** `worker_mode: protected` became the default.
- **2026-11-09:** the connector was rejected for the desktop path: it needs
  the student to start each piece of work from their own Claude.
- **2026-11-10:** the launched app became API-only (ADR 0005). A local
  model in the app was dropped. `ask` moved to Groq with Gemini as
  backup, on lean prompts that fit Groq's free tier.
- **2026-11-13:** a design review settled sections 2 to 7: no research in
  the app, the Model route and Usage cap, the engine download, the Worker
  extension on the store through the Debugger API, the private repo, and
  the v1 scope.
