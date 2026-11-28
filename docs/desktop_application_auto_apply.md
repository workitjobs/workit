# WorkIt Auto Apply: the desktop app (KAN-723)

**Status (2026-11-15):** being built, one workstream at a time. A design
review on 2026-11-13 settled every decision in section 2. Section 6's
table says where each workstream stands. Merged so far: Workers default
to `worker_mode: protected` (2026-11-06); W1, the Model route, the Usage
cap and the prompts on WorkIt's server, so each call sends a kind and its
data, with `ask_model: workit` the default and the student's private
values masked (#577, #587), and Send report (#614); W3's Student path with no developer part
(#581); W2's step 1, what Apply can't fill handed to the student in the
window (#590); W4, no macOS-only code in the Student path (#576, #585); W6's
store-ready Worker extension (#570, #578), which no app can use yet;
W10's legal text (#579, #582); W5, the app's window with no port:
sign-in (#609), first run, a run, and Report a problem in Settings and
on each Application's card (KAN-858); W2's step 2, the generic Filler (KAN-861); W7, the engine
download (KAN-836); and W8's build, signing, notarizing, updates and publishing (KAN-833, KAN-941,
KAN-950), which have published nothing yet.

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
| **Usage cap** | The model use one student may spend in one day (UTC), shown in the app |

"Apply" stays the code's and the glossary's name for the agent itself.

## 2. Decisions

All dated 2026-11-13 unless noted. Each row names the workstream that
builds it.

| # | Decision | Why | Builds it |
|---|---|---|---|
| D1 | **Every model call goes through WorkIt's Model route.** No `claude -p`, no local model and no student key in the app (2026-11-10; ADR 0005) | A product may not offer a student's Claude login; a local model is too weak and too heavy for a laptop; a key in the app is a key for everyone | W1 |
| D2 | **The app does no research.** It reads each company's brief from WorkIt | Research is the most expensive call, and a brief holds no student data, so WorkIt can make one per company for every student | W9, F2 |
| D3 | **The Fill engine is downloaded only, never shipped in the app.** Signed, encrypted, unlocked by a per-launch key, kept only in memory | A copy in the download is a copy for everyone; the app needs WorkIt to run anyway | W7 |
| D4 | **The Worker extension goes on the Chrome Web Store, unlisted, from WorkIt's existing developer account.** Apply's page code and the Fill engine reach pages through the Debugger API, not `userScripts`; the guards and the fixed page functions are packaged in it, since only a content script reaches a pop-up (measured); it holds no engine. The spike passed and the store package is built (KAN-839, 2026-11-14); no copy goes up until the guards learn their per-run tokens another way (W6) | One click for the student; the store allows outside code only through the Debugger or User Scripts API, and User Scripts is only for the user's own code; the existing account costs no new fee and has a trust history | W6 |
| D5 | **WorkIt builds the prompts** (2026-11-14; a thin proxy was decided 2026-11-13). The app sends each call's kind and its data; WorkIt builds the system prompt, the prompt and the schema (`backend/app/apply_prompts/`), runs the provider chain and counts tokens. The prompts and answering guides leave the app | A call that carried its own prompt and schema let anyone with an account use WorkIt as a free general model and send schemas that attack the server (W1). A prompt change ships with the merge that deploys the API | W1 |
| D6 | **A free beta with a Usage cap of 80,000 tokens per student per day**, reset at midnight UTC, always shown in the app. WorkIt can change it without an app update (2026-11-14; it was 3,000,000 a month) | The free tiers limit WorkIt's one key a day, shared by every student and feature: Groq allows 200,000 tokens a day for each model, about 400,000 for our two, so about five students at full use fill it. A monthly cap let one student spend a whole day's share. 80,000 is about thirteen 6,000-token calls, about three forms with essays; on Groq's paid tier it costs under 2 cents a student a day. W13 checks the number | W1 |
| D7 | **The beta uses the providers' free tiers.** Paid tiers come later (F3). One account per provider, owned by the team Gmail with developers as members, as Cloudflare's is; the team does not pool developers' free keys | No paid keys for now. Groq's AI policy forbids use "beyond published parameters, rate limits, or use limitations, including by registering multiple accounts" (checked 2026-11-14); members share their organization's limits | W1, F3 |
| D8 | **Private details are replaced before a prompt leaves the computer, and put back on the computer**: the exact values the student gave, theirs and their references' (2026-11-15). **Self-ID answers stay out where Apply can tell, by exact value**: the profile's self-ID section is never sent, and a form answer that is exactly one of the student's self-ID answers is left out of every call. One the Fill engine types in the form's own words ("I am not a protected veteran") still goes, until the engine reports which answers it took from a self-ID fact. An essay that states something private is flagged for the student. The app shows a short disclosure (section 3.4) | Prompts go to WorkIt and to Groq and Google, and Google's free tier may use prompts to improve its products | W1, W5 |
| D9 | **No Gmail.** A job site's emailed code becomes a Needs-you item that the student types | Reading Gmail needs an app password (a hard setup) or Google's paid security review | W3 |
| D10 | **macOS-only code is removed or replaced with code for macOS, Windows and Linux** (Linux added 2026-11-14). A general cross-platform library comes first; per-OS code stays only where no library does the job (W4's rules). Scheduled runs, phone push and the Dock bundle are dropped; Keychain becomes `keyring`; Chrome is found per OS | A simple app, and a later Windows and Linux port (F4) that is not a rewrite | W4 |
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
| D24 | **One to four Workers, by default from the computer's memory:** one under 8 GB, two from 8 to 16 GB, three over 16 GB (two when the memory can't be read). Settings' Automatic shows the count; a count the student picks wins, and only a picked count is four (2026-11-26). Each Worker is a full Chrome, about 0.5 to 1 GB of memory | Student laptops | W5 |
| D25 | **"Remove all my data"** in settings deletes the Worker profiles, the seed, Records, Traces and the app's `keyring` items. The data folder is in each OS's standard place | Mac apps have no uninstaller | W5 |
| D26 | **"Send report"** sends one Application's Record and a masked Trace to WorkIt only when the student presses it. No automatic telemetry. As built (KAN-837): a support form ("Report a problem", from Settings or an Application's tile): a category, the student's words, whether WorkIt may email them, and, if they include one, an Application's Record and masked Trace | Testers need a way to report; privacy first | W5, W1 |
| D27 | **Engine signing:** each build is signed with WorkIt's Ed25519 engine key by WorkIt's own CI on each merge that moves the engine pointer (`.github/workflows/publish-engine.yml` runs `backend/app/scripts/publish_engine.py`, with the key a secret of an environment that takes `main` only; 2026-11-15, it was the Fill engine's CI, then a person's hand run); WorkIt serves the build made for the nearest app version at or below the app's; the app holds only the public key | An unsigned download would let an attacker run code on every student's computer. A step in the engine's CI would need write access to WorkIt's Storage from another repo. WorkIt's CI signs only the engine a merged pointer names, which its PR's checks built, and no person's computer holds the key after setup | W7 |
| D28 | **Certificate pinning** to the certificate authorities Cloudflare uses for `api.workitjobs.ai` and for the live Supabase Auth, which refreshes the session (2026-11-15: pinning the API alone left the refresh token readable, and with it the download), with backups. Sparkle's feed is on another host without pinning, so an update can fix the set | A proxy on the student's computer can't read the engine download | W7 |
| D29 | **Apply moves to the private repo `workitjobs/apply-agent`**, with its history | The WorkIt repo is public; compiling protects nothing while the source is public | W0 |
| D30 | **The Developer checkout uses the local API** (`ask_model: workit` against localhost by default after W0). `claude` stays a developer choice. There is no staging server | Simple; keys stay only in WorkIt's `backend/.env` | W0, W1 |
| D31 | **Developer setup is `git clone --recurse-submodules`, `uv sync`, `uv run apply app`.** The window's first run does the rest, as for a student | One path for everyone | W5, W0 |
| D32 | **CI is small:** GitHub-hosted Linux runners, on PRs only, ruff and a short list of fast tests; no builds and no tags on PRs. **A release is the one build in CI** (revised 2026-11-26, KAN-941): `publish-app.yml` builds, signs and publishes it on a GitHub-hosted Mac, by hand from `main` | GitHub Actions minutes are limited. A release built on a person's Mac needs the signing keys on that Mac, and holds whatever that checkout holds | W0, W8 |
| D33 | **One mode:** Apply fills each form and stops on its last page; a person always presses Submit. Rehearsals and `live_runs` go. Not a v1 blocker | Simpler and safer: Apply never sends an application | W12 |
| D34 | **The student's data comes through the Fill engine's code as it does now.** Its redesign is a teammate's work | Out of this design's scope | W11 |
| D35 | **Keeping a job-site password from the student is not a requirement** (2026-11-14). The passwords Apply makes are the student's. Copy password writes through the window's own clipboard function, as the window's other copy buttons do, with no secret marks and no clear after a minute | It works on every OS with no clipboard code in Apply; the student can already see each password with Show password | W4 |

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
   nothing. (Until a store copy can be used (W6), this step is the guide
   that `apply plain seed` is today: Developer mode and Load unpacked.)
6. **Ready.** The window shows the student's Auto Apply queue, the paste
   box, Start, and the Usage cap ("Model use today: 0 of 80,000
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
5. At the Usage cap, the run pauses with "Today's model use is reached;
   it resets at midnight UTC". The window always shows the use so far.
   A Student run, a rehearsal, waits before its next form until the cap
   resets (`rehearsal._after_the_limit`, KAN-837), and the window shows
   the pause and when it goes on (`paused_until`).

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
| WorkIt | What each model call needs, without private details; tokens used | Each call |
| Groq, Google (Gemini) | The same prompt, sent by WorkIt with WorkIt's key | Each call |
| WorkIt | Tracker writes, answers the student approves, the queue | As today (`apply-agent/docs/workit.md`) |
| WorkIt | Each link the student sends in or pastes, to find WorkIt's job and name it while it waits | When it waits to start (`apply.queued_names`) |
| WorkIt | A support report: the student's words and, if they include one, an Application's Record and masked Trace | Only when the student sends the "Report a problem" form |
| Job sites | The form's answers, in the Worker's Chrome | As a person filling the form |
| Brandfetch | Each company's website (its domain, from the WorkIt job posting or a careers page's own host), for its logo, with WorkIt's public client id | Each logo the window draws, straight from the window, as the website does (KAN-871) |
| Job boards, Google (favicons) | The logo URL the scraper found, where Brandfetch has none | The same, as the website does |

**Replaced before a prompt leaves** (D8, as built in PR #587, 2026-11-15,
W1): the exact private values the student gave, by field, never a value
guessed from a question or a text: their names (legal, preferred, in
their own script), email, phone, street address, ZIP code, birth date and
profile links, and each reference's name, email and phone
(`experience_facts.professional_references`). Each becomes its
placeholder (`@FIRST_NAME@`, `@EMAIL@`, `@ZIP@`, `@REFERENCE1_NAME@`)
wherever it is in what a call sends, as a whole word, and comes back into
the answer on the computer (`apply/private.py`). A name matches in its
own case only, so a student named Will never masks "will". A value that
says there is none ("N/A", "None") is no private value and is never
masked: a native-script name of "N/A" once turned every N/A in the
Pre-submit review into that name's placeholder. No answer
needs these values, since the Fill engine types them from the profile;
a draft or an essay that needs one (a reference's details, the ZIP code
an essay box asks for, live at Applied Materials) writes the placeholder,
and the student's value comes back. The server also hides any email or
phone it finds and the student's own links (`Masked`), and puts them
back.

**Self-ID answers, as built** (PR #587, 2026-11-15): the profile's own
self-ID section is never sent as profile facts, and a form answer that is
exactly one of the student's self-ID answers is left out of the
Pre-submit review's rows and the essays' form answers
(`private.self_id`). Left out, not masked: the review sees each
question's options, and a placeholder beside the others would name the
one it hides. An answer that says nothing on its own (a decline, a yes or
no) is not matched, so a "No" to sponsorship is still reviewed. **The
gap:** the Fill engine types many self-ID answers in the form's own words
("I don't wish to answer" for `decline`, "I am not a protected veteran"
for `false`), so the student's value is not in the text, and those still
reach the model. **The full fix, by source:** the Fill engine's plan says
which answers it took from a `voluntary_self_id` fact (its rules already
name the fact, such as `voluntary_self_id.veteran`; the plan reports
only a coarse `sources` today), and Apply leaves those out instead. No
question's wording is matched either way, so neither the age question
nor Rippling's school question can be dropped, which the label pattern
did. The read-back check, which is code, still checks every self-ID field
the engine typed.

**Sent, because the answers need them:** the posting, the form's
questions and its other answers, school, major, graduation date, city and
state, employers and the student's stories. **Flagged, not blocked:** an
essay that states a private fact, a self-ID answer or a trait ("as a
first-generation student") is held for the student to read
(`private.sensitive`). **Not caught:** other people's names inside a
story. The privacy page says this in general terms (KAN-848).

### 3.5 What stays on the computer

| What | Where |
|---|---|
| The data folder: Records, Traces, the Worker profiles, the seed, the local copy of the student's data | `~/Library/Application Support/WorkIt Auto Apply` (`%LOCALAPPDATA%` on Windows, not the roaming `%APPDATA%`: a Worker profile is a Chrome profile, which Chrome keeps there too; `~/.local/share` on Linux), from `platformdirs` (`home.APP_FOLDER`) |
| The WorkIt session; Employer account passwords (passwords Apply makes for job-site accounts) | `keyring`: macOS Keychain, Windows Credential Manager, the Secret Service on Linux. The student chooses the job-site password in the Accounts tab (KAN-838), sees each account's with Show password, copies it with Copy password (D35), and can see and change them in Keychain Access |
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
- No Intel Macs, no Windows, no Linux (F8, F4).
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
   and installs the result; testers will get releases through Sparkle's
   beta channel (not built). Testers outside the team need the Apple enrollment first,
   because macOS blocks an app signed by no one.

There is no staging server. Tests that reach production use the shared
test account.

### 5.5 CI (D32)

GitHub-hosted Linux runners, on PRs only: `uv run ruff check .` and a
short list of fast tests (no browser, no network, no `claude`), a few
minutes in all. No macOS runners, builds or version tags on PRs. The one
build in CI is a release, on a GitHub-hosted Mac (D32, W8); test builds run
on a developer's Mac.

## 6. Workstreams

| # | Workstream | Waits for | v1 | Where it stands (2026-11-14) |
|---|---|---|---|---|
| W0 | Move Apply to `workitjobs/apply-agent` | KAN-723 merged into WorkIt's `main` | Yes, first | Not started. KAN-723's first parts are merged (#569, #577, #581); the open `apply-agent/` PRs (#554, #557, #403) merge or hold first |
| W1 | Model route and Usage cap | None | Yes | Built (#577, #587, KAN-837): the Model route, the Usage cap, the 11 kinds (13 with W2's two picks) and the Question types on the server, the student's private values masked in every call, Send report's route (D26), and the run's pause at the Usage cap (`GET /apply-app/usage`). Left: reworded self-ID answers, which wait on the Fill engine saying which answers came from a self-ID fact (D8, section 3.4) |
| W2 | Filling with no model in the browser | None | Yes | Step 1 built (#590): what Apply can't fill is the student's, in the window's Fix here; a failed field is a Needs-you item with its planned answer; the emailed code's box. Step 2 built (KAN-861): the generic Filler, code only but for two small picks; on the six saved Lever forms it fills 114 of 126 (90%, code only) of the engine's planned answers right, Claude fill 122 (97%), in 5 to 10 times the time. Left: frames other than the top one, and live long-tail postings ("Done when"); any further work stays with the teammate, beside the Fillers they write for each job system |
| W3 | What the Student build leaves out | None | Yes | Step 1 built (#581); `ask_model` fixed to `workit` (#590). Left: W8's compile flags |
| W4 | Remove macOS-only code | None | Yes | Built (#576, #585). Left to others: `dashboard.py` (W5) and `window_capture` (W6); what stops Apply on Windows is F4's |
| W5 | The app shell | W3, W4 (and W1 for sign-in and usage) | Yes | Built: sign-in (#609); the window with no port, first run, a run, Report a problem in Settings and on each Application's card, and the Student build's Tracker in the data folder (KAN-858), and a Student run's pause at the Usage cap (KAN-837), and the built app's sign-in link (KAN-833) |
| W6 | The Worker extension on the store (spike first) | None | Yes | The spike passed; the store package is built (#570, #578). Blocked: the guards' per-run tokens (`worker-extension-todo.md`, item 0), then the first upload |
| W7 | The engine download and its protection | W1 (sign-in) | Yes | Built (KAN-836): the two routes, the publish script, the app's download, decryption and signature check in memory, no engine file anywhere, and the pin. Each merge that moves the engine pointer publishes it (`publish-engine.yml`); the first publish passed on 2026-11-17. Open: the WorkIt extension's public copy of the engine |
| W8 | Compile, sign, notarize, update, publish | W3, W4, W5 | Yes | Step 1 built (KAN-833): `scripts/build_app.py` compiles an app that opens on the Mac that built it, and its DMG. Sparkle and publishing are built (KAN-941, steps 3 and 4), and so are signing and notarizing (KAN-950, step 2), which wait on the Apple enrollment and its keys. Left: those keys, the first publish, a beta channel. The download page is built (KAN-835): `/auto-apply/desktop`, Auto Apply's Desktop App tab (a rail row at `/auto-apply-desktop` until 2026-11-23), with Download for Mac off until `DOWNLOAD_URL` names the DMG |
| W9 | Company briefs in v1 | None | Yes | Not started. The Student build already does no research (#581) |
| W10 | Legal | None | Yes | Text merged (#579; the WorkIt extension's license, #582). The license and complete notices are in W8's app and its DMG: every hand entry's text is in `legal/licenses/` (KAN-833), so `build_app.py --release` passes. Left: a `/privacy` that is true of the app |
| W11 | The student's data | A teammate | Yes (not ours) | A teammate's |
| W12 | One mode: remove Rehearsals and `live_runs` | W0 | No | Not started |
| W13 | Measure quality and model use | W1 | Yes, for the cap | Not started. Step 2's token count is parked, not merged, on branch `KAN-837-tokens-by-kind` (section W13) |

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

**The server (WorkIt repo, `backend/`). Built 2026-11-13.** The route's
docstring (`backend/app/routers/apply_app.py`) is the reference for its
shapes and status codes.

- **Routes**, each signed in as a student (a company account gets 403):
  - `POST /apply-app/ask`: body `{kind, version, data}` (below, "Prompts
    on the server"). Each kind runs on the size of the API's model chain
    it names: Apply's Haiku calls on the small one, its Sonnet and Opus
    calls on the large one (`app/services/models.py`). So the models and
    their keys are the `SCOUT_ENDPOINTS*` settings already in the API's
    production secrets (Infisical's `workit-prod/api`, `secrets.md`), and a
    model change is an env change. It answers
    `{answer, tokens, usage}`, with `usage` as below, so the window's cap
    line updates with each call. The free-form `POST /apply-app/model`,
    which took the app's own prompt and schema, went once every kind was
    built on the server (2026-11-14).
  - `GET /apply-app/usage`: `{used, cap, resets_at}`.
  - `GET /apply-app/types`: each Question type's front matter and the order
    Apply tries them in, never a guide's body (2026-11-15).
  - **429 with `Retry-After`** at the cap (it runs to midnight, UTC) and
    past the per-minute limit (to the next minute). Nothing goes to a
    model. `ask_model.py` already reads a `Retry-After` over 60 seconds as
    a limit hit and pauses the run until then.
  - 413 when every model finds the request too large, 502 when no model's
    answer fits the schema or every model refused the request (asking
    again the same way won't help), 503 with `Retry-After: 60` when every
    model is busy or down. A failed call's tokens still count.
- **The call** is `workit_scout.llm.LLM.complete_schema`, the API's one
  model seam, with the schema as JSON data. It tries the chain in order
  and moves on at a 429, a 5xx, a request too large, a 400 or 422 (the
  provider refused this request: Groq's `json_validate_failed`, or a
  schema it does not take) or an answer outside the schema (checked with
  `jsonschema`). It sends the schema as given:
  no strict mode and no plain-JSON retry, unlike `ask_model.py`'s three
  modes. W13 shows whether Apply's schemas need them.
- **Contact details are masked on the server too, and come back**: the
  seam replaces the student's email, phone and links from their WorkIt
  profile, and any email, phone or link found by pattern, with
  placeholders (`[email]`, `[email2]` for a second address, `[phone]`,
  `[link]`) whatever the app replaced first, and puts each value back
  into the answer (`workit_scout.identity.Masked`). The map lives in
  memory for the one call, never stored or logged; a placeholder already
  in the prompt (the app's own) is never used. The answer is checked
  against the schema with the values back in. **The name is the app's to
  replace (D8), not the server's** (2026-11-13): the server's name
  removal takes each part of the name as a word in any case, so for a
  student named Will Mark, "You will write" reached the model as "You
  [name] write", and the prompt broke. The cost: a name the app misses
  reaches Groq or Google. **The app replaces it** (PR #587): each name
  field's exact value, in its own case and as a whole word, so "will"
  stays (section 3.4).
- **No request carries a schema** (2026-11-14): the server builds each
  kind's. The free-form route's checks went with it. Its lesson stays for
  any route that takes a schema from outside: refuse a `$ref` (or its
  dynamic forms), since `jsonschema` fetches a remote URL by default;
  refuse `pattern` and `patternProperties`, since the answer's check runs
  them with Python's backtracking `re` in the API's event loop, and one
  call with `^(a+)+$` could stop the API for every user; and refuse more
  than 32 levels, where `jsonschema`'s own check runs out of stack.
- **Table** `model_usage` (migration `3132c5026bf6`, RLS on, no
  policies): one row per student per day (UTC), with
  `input_tokens`, `output_tokens`, `calls`, and the current minute's
  calls for the limit (`app/queries/model_usage.py`). A call takes its
  place in the minute before it goes, and adds its tokens after, with no
  database connection held while the model writes. Two calls at once
  just under the cap both go: the cap can be passed by one call per
  Worker. Kept 90 days (`services/retention.py`).
- **Settings**: `APPLY_APP_DAILY_TOKENS` (80,000) and
  `APPLY_APP_CALLS_PER_MINUTE` (20), so both change with no app update.
- **Logs** keep no prompt text: only the student, the kind, the model and
  the tokens. A provider's error is logged by its status and code only,
  since its body can hold the model's output.
- **Send report** (D26, KAN-837) is a support form, "Report a problem",
  from Settings or an Application's tile, which picks that Application:
  a category (`report.CATEGORIES`), the student's own words, whether
  WorkIt may email them, and, with an Application picked, whether to
  include its Record (its answers, essays, verification, the questions
  asked of Claude, the page's HTML and the form's screenshots) and its
  Trace, masked in the app. A general question names no Application.
  `POST /apply-app/reports` keeps it in `apply_reports` (RLS on, no
  policies; migration `36d339a2d6b4`). Admins list and read reports with
  the student's email (`/admin/apply-reports`) and `DELETE` one once its
  problem is fixed, so a report has no retention period, as `/privacy`
  says. Up to 24 MB, 10 a day per student. The window (W5's) calls
  `report.build` with the form's answers, shows `report.parts`, and on
  Send calls `report.send` with that same report.

**Prompts on the server (decided 2026-11-14, being built).** D5 changed:
the app no longer sends a prompt and a schema, so a request can't carry
its own instructions or a hostile schema.

- **The cut.** Each of Apply's `ask` calls splits in three. The app
  collects the data (the form's questions, the drafts, the student's
  sources). WorkIt builds the system prompt, the prompt and the schema,
  and calls the model. The app uses the answer (gates, read-back, the
  Answer bank). Today one Apply function often does all three: it reads
  a file from the data folder, builds the text and parses the answer.
- **The route:** `POST /apply-app/ask {kind, version, data}` answers
  `{answer, tokens, usage}`, with the Model route's limits, cap and
  status codes. Each kind's `data` is a Pydantic model, checked before
  anything counts. The prompt builders and the answering guides live in
  `backend/app/apply_prompts/`, not a package: the WorkIt repo goes
  private (2026-11-14).
- **A kind's data fields never change in place.** A student's app can
  be an older copy, so a change to the fields is a new `version`, and
  the server keeps the old one while app copies still send it. The
  prompt text changes with any merge to `main`.
- **`drafts` come from the app**: they belong to one form. **`sources`
  is one text field the app builds for now** (Story bank, Stock
  answers, profile facts, links, town, Company material, and the style
  card for `writing.edit`).
- **Sources move to the server** (noted 2026-11-14, part of W11's
  answer bank redesign). Sources belong to the student, not to one form,
  so WorkIt builds and stores them, and the app pulls a copy and caches
  it, as it will for the redesigned answer bank; the student edits them
  through WorkIt's routes. Each call then sends only the form's own data
  (drafts, questions, the posting), and a new version of each kind reads
  the sources on the server. That keeps each call small and lets the
  server send a kind only the sources it needs.
- **The student sees and edits the Story bank in the app** (decided
  2026-11-14). WorkIt holds the one true copy; the app keeps a cached
  copy, so the window shows it at once and Apply's own checks read it on
  the Mac (the plan's quotes, the truth check, the copy check). An edit in
  the app goes to WorkIt first and then updates the cache; the app pulls
  a fresh copy before each run, so an edit on the website is never lost.
  Part of W11's redesign, with the answer bank.
- **Order every prompt for the providers' prompt cache** (decided
  2026-11-14). A provider keeps the start of recent prompts: a call whose
  prompt starts with exactly the same text pays half for that part on
  Groq ($0.075 for each million tokens, not $0.15), and Groq does not
  count cached tokens against its rate limits, so on the free tier it
  also stretches the daily 400,000. The match is exact from the first
  character, needs 128 to 1,024 tokens by model, and lasts about 2 hours
  without use (https://console.groq.com/docs/prompt-caching, read
  2026-11-14). So each builder puts what is the same for many calls
  first: the kind's own instructions (the same for every student), then
  the student's sources (the same for their calls that day), then the
  form's data. Not done yet: the essay kinds' system prompts add each
  question type's guide, so their shared start ends early; moving those
  guides after the fixed part is next, checked by W13 since the order can
  change an answer.
- **The free-form `POST /apply-app/model` went** (2026-11-14), with its
  schema guards, once every call sent a kind.
- **Urgent, for developers:** `ask_model: claude` can't run a ported
  kind once Apply's calls send kinds, since the prompts are no longer in
  the app. It needs the developer prompt route
  (`docs/developer_apply_agent_testing_framework.md`, not built). Until
  then a developer runs a ported kind through WorkIt (the local API,
  D30).
- **The kinds**, one for each `ask` call that writes or judges. All 11
  are built on the server (2026-11-14). Each was checked to build the
  same system prompt, prompt, schema and model size as Apply for the same
  inputs, by running Apply's own call with a fake model. Only the calls
  Apply says as the applicant (essays.py's and the Pre-submit review) get
  the pronouns note. Where Apply reads a page (`own_application`, Claude
  fill's sent check), the app sends the page's text and links, not the
  page. The answering guides live once, in
  `backend/app/apply_prompts/answering/`: Apply fetches their front matter
  (which type a question is, its slots, its default length) from
  `GET /apply-app/types` when a run starts and keeps the last copy in its
  data folder (`apply.answering`, 2026-11-15), since it is the same for
  every student and no input of theirs. A change reaches every app with
  the API's deploy.
  Every one of Apply's calls sends its kind (`ask_model: workit`, the
  default since 2026-11-14), and Apply builds no prompt of its own.
- **Next, not in this PR: the checks move to the server too, and fewer
  round trips** (noted 2026-11-14). Today the app runs every check on an
  answer (the plan's quotes, the gates, the claim check loop, the truth
  check, sameness) and calls the next kind itself. With the sources on the
  server (W11), WorkIt can run them, and these optimizations open up:
  - one call per form for its essays: the server runs plan, write,
    claim check and edit in a row and answers once, so four round trips
    become one and the app holds no essay logic;
  - only the sources each step needs (the plan's picked episodes for the
    write, check and edit steps), so fewer tokens;
  - a shared prompt start for each student's calls (instructions, then
    their sources), so more cached tokens, which Groq bills at half and
    leaves out of its rate limits;
  - the default probe's cache on the server, shared by every student
    who applies to the same company and question, not one per Mac;
  - the essay kinds' per-type guides after the fixed part of the system
    prompt, so the cached start runs longer (W13 checks the answers).

  It waits on: W11's data on the server (the plan check, the truth check
  and the copy check read the Story bank, Stock answers, profile facts
  and the Answer bank); WorkIt tables for the sameness ledger (each
  student's past answers by company, a file on the Mac today) and the
  default probe's cache; and a route that runs the loop and can stop for
  the student (an essay whose plan needs a fact waits in Needs you, then
  goes on). Checks that read the live page (the read-back, the replan's
  "does the page show it") stay in the app. It does not wait on W0 or W6.

  | Kind | Apply today | What the app sends |
  |---|---|---|
  | `essays.plan` | `essays._ask_plan` | the questions with their matched types, the posting, sources, form answers, typical answers, redo context |
  | `essays.write` | `essays.answer` | the questions, the plans, short questions, the posting, sources, form answers, redraft and redo context |
  | `writing.check` | `writing._check` | drafts, sources |
  | `writing.edit` | `writing._pass` | drafts, sources, flagged problems, the questions, their lengths |
  | `probe.typical` | `probe.typical` | the questions, the posting and its text, Company material |
  | `recording.brief` | `recording.brief` | a video link question, the prompts its posting lists, sources, the posting |
  | `presubmit.review` | `presubmit` | the filled form's answers read back, sources, the posting |
  | `presubmit.fix` | `presubmit` | the review's problems, the answers it read, sources, the posting |
  | `presubmit.replan` | `presubmit` | the flagged fields, the posting |
  | `story_map.tag` | `story_map` | the Story bank (the server knows the Question types) |
  | `brief.team` | `brief.name_team` | the posting's title and text |
  | `own_application.find` | `own_application` | the page's text and address |
  | `claude_fill.sent` | `claude_fill` | the page's text after a send |

  `applicant.as_applicant` (the name and the pronouns note on every
  call) becomes a `pronouns` field the server reads. The prompts say
  `@NAME@` where the name goes, and the app puts the first name into the
  answer (D8); the name in a call's data goes as a placeholder too
  (section 3.4). The `claude_cli` probe ("Reply with
  ok") is not a kind: `GET /apply-app/usage` checks the session.

**The app (Apply).**

- `ask_model: workit`: a provider in `ask_model.py` whose endpoint is
  the Model route (`/apply-app/ask`) and whose key is the student's
  WorkIt session. It sends a kind and its data, never a prompt.
- **Personal data out, back in** (D8, section 3.4): one module replaces
  each personal value with its placeholder before `ask` sends, and puts
  the values back into the answer. Self-ID answers are never in a
  prompt. Tests check that no profile value of the listed kinds reaches
  the request.
  **Built in PR #587** (2026-11-15, section 3.4): `apply/private.py`
  replaces the exact private values the student gave, theirs and their
  references', in every kind's data, and `applicant.as_applicant`, which
  wraps every adapter where a run, the window or a command builds it,
  puts them back. An essay that states something private is flagged at
  the Hold (`private.sensitive`), never cut or written again. A form
  answer that is exactly one of the student's self-ID answers is left out
  of every call (`private.self_id`); one the Fill engine rewords still
  goes until the engine reports which answers it took from a self-ID fact
  (section 3.4, next). The label pattern that dropped self-ID answers went
  in that PR, with the answers it dropped by mistake (a diversity essay,
  Rippling's school question).
- **The Orchestrator's limit.** **Built** (KAN-837): with `ask_model:
  workit` the run's usage (`adapters.usage`) is `WorkItAsk.reading`, which
  reads `GET /apply-app/usage`. Once `used` reaches `cap`, no form opens
  until `resets_at`: a rehearsal, the Student build's run, waits before
  each link (`rehearsal._after_the_limit`), `apply run` waits before each
  Application (`orchestrator._resume_at`), and the window shows the pause
  with its time. A Developer checkout keeps Claude Code's 5-hour and
  weekly windows beside it. Before this, the Student build never paused:
  at the cap each link left opened its form, was refused at its first
  ask and ended paused, and nothing started it again.
- **Send report** (D26) uploads one Record and masked Trace through a
  WorkIt route; the server keeps it for the team. **Built** (KAN-837)
  as the support form above: `report.build` reads the Record's files from
  its folder and the Application's Trace, masks the Trace with
  `masked.Known` (the profile's and Answer bank's own values, and every
  email, phone and id in a link) and keeps its start and its last 4 MB.

**Waits for.** Nothing. Sign-in (W5) supplies the session in the app; a
developer can test with an existing WorkIt token.

**Done when.** A Developer checkout with `ask_model: workit` against the
local API writes a form's essays, the usage row grows, a cap set low
pauses the run with its date, and a request captured in a test holds no
personal value.

**Open.** Whether to add Cloudflare AI Gateway in front of the chain for
logs. Whether Apply's schemas need Groq's strict mode on the server (W13).

### W2. Filling with no model in the browser

**Goal.** v1 fills without `drive` (D13).

**Who builds it.** Both steps are built (below): step 1 in KAN-855,
step 2 in KAN-861. The generic Filler stays with this workstream, not
with the teammate who writes a Filler for each job system (2026-11-16,
reversing #617's hand-over). A Filler of a job system's own still comes
first: `by_filler` uses the generic Filler only where `FILLERS` has none,
so the two never meet in `fillers.py`. What a Filler can't place goes to
step 1's paths: a Needs-you item with its planned answer, or a Handoff
of the held form. Each new click path needs the adversarial review
(KAN-666) and its cases in `tests/test_submit_guard_hostile.py`.

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

**Built (2026-11-15, step 1, KAN-855: Handoffs first).** In the Student
build, what Apply can't fill is the student's, and they do it in the
Apply window, never in the Worker's own Chrome window. Fix here gives
them the form's live view, which takes their clicks, keys, picks, files
and the form's own Submit. Only a captcha takes the Worker's window:
the tile's clicks are synthetic, so a captcha item's first button is
Open in Chrome, and once Apply sees it done the app comes back to the
front 2 seconds later, if that window is still in front. With no Screen Recording permission the view is about
two frames a second, so W5's first run asks for the permission.

| Case | Student build now |
|---|---|
| A job system with no Filler | The form opens and is held, nothing filled (`orchestrator.ForTheStudent`); the student fills and sends it through Fix here |
| A field a Filler fails on | A Needs-you item whose box starts with the planned answer; the held page tries it once more by the Fill engine |
| An answer typed in the window | The Fill engine puts it in its field (`rehearsal._engine_fill`), no model; else "press Fix here and type it on the form in this window" |
| An emailed code after Submit | No mail read: once the code field comes, Needs you says to type the code (`code_box.TypeTheCode`) |

`docs/held-forms.md` has the rules; `tests/test_student_build.py` (CI)
and `tests/test_student_handoffs.py` (Chromium) test them. Step 2, below, fills a form with no Filler of its own.

**Built (2026-11-15, step 2, KAN-861: the generic Filler).** In the Student build a job system with no Filler gets
the generic Filler (`apply-agent/src/apply/generic_fill.py`, `apply-agent/docs/generic-filler.md`), in place of
step 1's hold of the whole form. As designed above, with these choices made on the way:

- **The tree is Playwright's ARIA snapshot**, not CDP's `Accessibility.getFullAXTree`: the same call runs on a plain
  Worker, which has no op for Chrome's raw tree. Each control's element gives what the tree leaves out (a required
  mark, a text area, a select's placeholder, a file input). Only the top frame is read.
- **fit.ts is reached through the planner.** The engine exports no `fit`, so an option read before planning is
  fitted by the planner as for any Filler; an option seen only as the fill opens or types is matched by its words,
  then by the engine's `shows`, then by the model.
- **Two kinds, not one:** `generic_fill.pick` (`{"choice": <number> | null}` for one field's options, the number
  bounded by the list) and `generic_fill.next` (which of two or more Nexts goes on without sending). Both run on the
  small chain and send no pronouns or school.
- **A posting page with no field** opens its form by its one Apply link (followed with no click) or Apply button
  outside any form (BambooHR's "Apply for This Job").
- **Every field is read back as it is filled.** A wrong or empty one is a `FillError` naming it, so step 1's path
  makes it a Needs-you item with the planned answer.

**Measured** (`apply-agent/scripts/generic_fill_measure.py`): the Fill engine's six saved Lever forms, served on
127.0.0.1 and refusing every POST, filled in a plain Worker as Test Person by each Filler in turn; then the engine
reads each page back and counts how many of its own planned answers it shows. The generic Filler ran code only (a
Developer checkout has no Model route), so every field it couldn't match counted as wrong.

| Form | Planned answers | Lever's own Filler (engine) | Generic Filler, code only | Claude fill |
|---|---|---|---|---|
| lever-belvedere | 26 | 26 | 24 | 26 |
| lever-hermeus | 23 | 23 | 20 | 21 (stopped at its cap) |
| lever-immuta | 15 | 15 | 14 | 15 |
| lever-rhombus | 17 | 17 | 15 | 17 |
| lever-shieldai | 28 | 28 | 26 | 26 (stopped at its cap) |
| lever-xcimer | 17 | 17 | 15 | 17 |
| **All six** | **126** | **126 (100%)** | **114 (90%)** | **122 (97%)** |

Time per form: the generic Filler 3 to 13 s, Claude fill 28 to 63 s and about 40 Haiku turns, the engine under 1 s.
The generic Filler's 12 misses are each a field it left for the student, never a wrong answer typed: Lever's
location search on all six forms (its choices come from Lever's live API, which the saved form's server doesn't
answer, so no model could pick one either), Lever's school list on three, and a self-ID survey the page keeps
collapsed on two. Each is a Needs-you item with its planned answer in a run. The model's picks would add to the
generic Filler's count only where code finds options but no match; on these forms it found none such.

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

**Built (2026-11-14, step 1).** `apply/build.py` holds `STUDENT` (False
in a checkout; the build script writes True), `DEVELOPER` (the modules
left out) and `STUDENT_POLICIES`. `apply/student.py` is the Student
path's root: W5's window starts there, and its `adapters()` replace each
developer part with one that does nothing (`NoClaude`, `NoMailbox`,
`Silent`, `NoRepairs`). `tests/test_student_build.py` (CI) imports the
Student path in a new process, builds its adapters and makes a plain
Worker's first page call, and fails if any module in `DEVELOPER` loads.
It also proves that a `policies.yaml` changes nothing. A developer
module is now imported only inside the function that uses it, in a
branch the Student build never reaches. What the Student path needs from
one moved out of it: Ask Claude's and the emailed code's page strings
(`page_functions.py`), `OnePage`, `ClaudeError` and `job_key`. What each
part does in the Student build:

| Part | Developer checkout | Student build (until the workstream named) |
|---|---|---|
| A job system with no Filler | Claude fill | Held for the student to fill through Fix here (W2 step 1); the generic Filler is W2 step 2 |
| A field a Filler fails on | Rescue | A Needs-you item with its planned answer (W2 step 1) |
| An answer typed in the window | Rescue fills it in place | The Fill engine fills it in place (W2 step 1) |
| Ask Claude on a held form | On | The tile takes no message |
| An emailed code after Submit | Gmail, typed by script | A Needs-you item: the student types it through Fix here (W2 step 1) |
| The company brief | Researched with `claude -p` | A kept brief only, never researched (W9) |
| Repair requests, notifications, phone push | Kept, shown, pushed | None |
| `ask_model` | `policies.yaml` | Fixed `workit`, WorkIt's Model route (W1) |

Left: W8 passes `--nofollow-import-to` for each module in `DEVELOPER`
and compiles from `apply.student`, and the build's smoke test fills one
form. Code a Student build never runs but still holds stays until its
workstream: the research prompts in `brief.py` (W9), the window's
`open_window` (W5).

### W4. Remove macOS-only code

**Goal.** No macOS command or path in the code the Student build runs,
outside the few places that only the Mac needs, so the Windows and Linux
port (F4) is a port, not a rewrite (D10). The rest of W4 is KAN-850,
built 2026-11-14 except where a row below says what waits.

**Rules (decided 2026-11-14).**

- **A general library first.** Where a cross-platform library, Python's
  standard library or Chrome itself does the job, Apply uses it and holds
  no per-OS code: the window's clipboard function for Copy password
  (D35), `psutil` for a process's command line, and a library for each
  OS's standard data folder (D25).
- **Per-OS code only where nothing general does the job,** in one place
  for each job, with an entry for macOS, Windows and Linux: Chrome's
  install paths, the native host's place, Playwright's browsers folder,
  and how Chrome starts in the background.
- **FocusKeeper stays Mac-only.** On the Mac, Chrome makes itself the
  front app as it starts and at each new tab or pop-up, and macOS lets
  it. FocusKeeper (`focus.py`) gives the front back to the student's app
  when the student did not choose that Chrome. Windows and Linux desktops
  stop a background program from taking the front (Windows flashes its
  taskbar button instead), so there FocusKeeper does nothing. F4 checks
  this on each OS.

| Module | macOS part today | Change |
|---|---|---|
| `keychain.py` | `security` | Built (KAN-838): `keyring` (Keychain on Mac, Credential Manager on Windows, the Secret Service on Linux) for every caller, `gmail.py` too; `brief.py` never called `security`. Items left in the Student build: Employer account passwords (`apply-ats`) and the WorkIt session (W5). One developer-only `security dump-keychain` stays in `cli._mac_keychain_sites`, the backfill of accounts made before KAN-592 |
| `workit.py` | Session in `workit-login.json`; sign-in through Chrome's debugging port | Built (W5's sign-in, 2026-11-15): the refresh token in `keyring` (`apply-workit`), the access token in memory; sign-in in the default browser with a one-time code, pasted or through `workit-auto-apply://`: a checkout's window takes the link through a helper applet (`sign_in_link.py`, KAN-883), and the built app will claim it once W8 builds the bundle |
| `notify.py` | `osascript` notifications, ntfy | Dropped: the window shows notices |
| `schedule.py`, `cli.py` | `launchctl`, `~/Library/LaunchAgents` | Dropped |
| `dock_app.py` | The Dock bundle | Dropped: the app is its own bundle |
| `dashboard.py` | `open`, `osascript`, `pgrep`, Chrome `--app` | Replaced by the pywebview window (W5) |
| `focus.py` | `lsappinfo`, CoreGraphics, `osascript` | Built (KAN-850). Stays, Mac only (the rules above): `focus.KEEPER` is a FocusKeeper on the Mac and a `NoKeeper`, which does nothing, on Windows and Linux. Show (the window's Open in Chrome) brings a Worker forward through Chrome when there is no FocusKeeper, or when FocusKeeper can't: a CDP Worker whose Chrome the profile's lock names as running, through `browsers.activate` (`/json/activate`, the DevTools HTTP form of `Page.bringToFront`, on the page `/json/list` names as used last), a plain Worker through the Worker extension's new `windows.focus` op (`chrome.windows.update`; features 6, store version 0.4.0) |
| `captcha.py` | `open -a "Google Chrome"`: a bot-blocked posting, or the Accounts tab's Open sign-in page, opens in the student's everyday Chrome | Built (KAN-850): `to_everyday_chrome` gives the finder's Chrome the link with no profile flag. The Mac's entry stays `open -a`, with the found app: started from its binary, a Chrome that wasn't running would be the app's child process, with the app's privacy permissions (camera, microphone) and environment (review, 2026-11-15). Windows and Linux start the binary |
| `accounts_tab.py` | `MacClipboard`: `osascript` writes the clipboard with Concealed and Transient marks and clears it after a minute | Built (KAN-850): Copy password gets the password as Show password does and writes it through the window's clipboard function (`navigator.clipboard`), as the window's other copy buttons do, with the write started inside the click (a `ClipboardItem` that waits for the reply), which WebKit's window needs; `MacClipboard`, its route and the clear are gone (D35). W5 checks that pywebview's window allows it on each OS |
| `browsers.py`, `plain/launcher.py`, `cover_letter.py`, `workit.py` | `/Applications/Google Chrome.app` | Built (KAN-850): one Chrome finder, `chrome_finder.py`, with each OS's places. macOS: `/Applications/Google Chrome.app`, then `~/Applications`. Windows: `%PROGRAMFILES%\Google\Chrome\Application\chrome.exe`, the 32-bit Program Files, then the per-user `%LOCALAPPDATA%`. Linux: `google-chrome` or `google-chrome-stable` on the `PATH`. It also reads Chrome's version on each OS and gives a Worker's user agent its OS's platform. `browsers.py`, `plain/launcher.py`, `plain/seed_setup.py`, `captcha.py`, `cover_letter.py` (after PR #577, W1) and `doctor.py` use it. `cover_letter.py`'s date has no `%-d` either, which Windows lacks. `workit.py` starts no Chrome any more: W5's sign-in uses the default browser |
| `plain/launcher.py` | `open -g -n -a` | Built (KAN-850): stays on the Mac: `-g` keeps a new Chrome from taking the front as it starts, and starting the binary itself brings it forward. On Windows and Linux, `start_in_background` starts the binary as a plain background process, in a session (a process group on Windows) of its own, and its Popen is the Worker's process |
| `plain/window_capture.*` | Swift and ScreenCaptureKit | Dropped: tiles come from the debugger's screencast (W6) or the extension's frames |
| `plain/seed_setup.py` | `open -R`, `pbcopy`, `ps` | Built (KAN-850): the store install needs none of them (W6); the fallback guide uses `pyperclip` for `pbcopy` and `psutil` for `ps`. Showing a folder has no library, so `Desk.reveal` has an entry per OS: `open -R`, `explorer /select,"<path>"` as one string (a path with a space stays whole), `xdg-open` on its parent. Its words (Finder, Cmd+Shift+G) are still the Mac's (F4) |
| `plain/extension.py` | `ps -axo` (found 2026-11-14) | Built (KAN-850): `psutil` reads each process's arguments as a list, so a path with spaces stays whole |
| `native_host.py`, `plain/launcher.py`, `doctor.py` | `~/Library/...` paths | Built (KAN-850): each OS's places. The everyday Chrome's native host folder: `native_host.chrome_hosts` (`~/.config/google-chrome/NativeMessagingHosts`, or under `$XDG_CONFIG_HOME`, on Linux; none on Windows, where Chrome reads a registry key under `HKCU`: F4 writes it). Playwright's browsers folder: `chrome_finder.playwright_browsers`, the OS's cache folder from `platformdirs`, as Playwright picks it, with Chrome for Testing's layout for each OS. The data folder: `home.APP_FOLDER` from `platformdirs` (D25); W5 makes it the Student build's data folder |

**Done when.** A search of the Student build's modules for `osascript`,
`security`, `launchctl`, `open`, `pgrep`, `pbcopy`, `ps`, `/Applications/`
and `~/Library/` finds them only where the rules allow: FocusKeeper, the
Mac's background start of Chrome, and the Mac entries of the per-OS
places. The moved features work on the Mac, and tests give the Windows
and Linux entries their own paths. Running on Windows and Linux is F4's.

**Where it stands (2026-11-14, KAN-850).** The search finds the rules'
places, and the modules that other workstreams replace: `dashboard.py`
(W5) and `plain/window_capture.*` (W6); `workit.py`'s Chrome went with W5's sign-in (2026-11-15). `tests/test_each_os.py` (in CI) runs each OS's entry on
the Mac with paths of its own. The plain and CDP Worker tests and the
Accounts tab's browser test pass on the Mac.

Found on the way, left for F4, since each needs Windows to build and test.
The first three work on macOS and Linux (they are Unix's, not only the
Mac's), so W4's search for macOS-only calls did not find them (2026-11-15);
on Windows each one stops Apply:

- **File locks.** `tracker.py`, `records.py`, `answer_bank.py`,
  `answer_sync.py`, `batch.py`, `verify.py` and `workit.py` import `fcntl`
  at their top, which Windows lacks, so Apply can't even start there. Built
  (KAN-929): every lock goes through `apply.locks`, on `portalocker`
  (`windows_desktop.md`, P1).
- **The channel between Apply and the plain Workers.** `plain/bridge.py`,
  `plain/host.py`, `plain/mcp.py` and `plain/tools.py` use a Unix socket
  (`AF_UNIX`, which Python lacks on Windows) in a folder named with
  `os.getuid()`, which Windows lacks too. Windows needs a named pipe (F4's
  table). Built (KAN-929): `plain/channel.py`, a named pipe on Windows,
  checked in both directions (`windows_desktop.md`, P4).
- **"Is it still running?"** `into.py` checks a window's process with
  `os.kill(pid, 0)`. On Windows that call ends the process: it would close
  the Worker's Chrome. Built (KAN-929): every such check is
  `psutil.pid_exists` (`windows_desktop.md`, P2).
- Chrome's profile lock. `browsers.chrome_pid` reads the profile's
  `SingletonLock`, a link that Chrome makes on macOS and Linux only; on
  Windows a profile has a `lockfile`, so a Worker's "in use" check and its
  PID read find nothing there, and Show brings no CDP Worker forward: it
  brings one only when the lock names a running Chrome, since Chrome
  leaves its `DevToolsActivePort` file behind when it quits. Built
  (KAN-929): on Windows `chrome_pid` finds the Chrome by its arguments
  (`windows_desktop.md`, P3).
- Signals. `launcher.Chrome` (the Mac's) and the seed guide's quit use
  SIGTERM and `os.kill(pid, 0)`. On Windows, `os.kill` ends a process at
  once, with no clean exit, so the seed's preferences would not be saved.
  A Worker started off the Mac is a Popen, which stops it on each OS.
- The hosts' wrappers are shell scripts (`native_host.install`,
  `PlainWorkers.install_host`), and Chrome on Windows reads a Worker
  profile's host from the registry, not from its `NativeMessagingHosts`
  folder (F4's table).
- The seed guide's words name Finder and the Mac's keys.

### W5. The app shell

**Goal.** One native window that does everything a student needs
(sections 3.1 and 3.2).

**Design.**

- **pywebview, no port** (D11). The window's page is the student page
  (KAN-867: one to-do at a time, what WorkIt is still working on, Applied,
  the queue and Start), in place of today's Apply window, which a
  Developer checkout's window keeps. Its 28 routes in `dashboard.py` (`/state`, `/start`, `/answer`,
  `/answers`, `/approve`, `/resume`, `/fill-again`, `/regenerate`,
  `/accounts`, `/frames`, `/stream/`, `/input/`, ...) become methods on
  pywebview's JavaScript bridge (`js_api`). Tiles' frames are pushed into
  the page through the bridge. The window shows in the Dock while open,
  as every Mac app does.
- **Sign-in** (D12):
  1. The app makes a PKCE verifier and challenge and opens
     `https://workitjobs.ai/app-sign-in?challenge=…` in the default
     browser (a new website page).
  2. The page signs the student in as the website does, then asks the
     API for a one-time code bound to the challenge, and opens
     `workit-auto-apply://signed-in?code=…`. It shows no code to copy.
  3. The app (registered for the scheme in its `Info.plist`) sends the
     code and the verifier to the API and gets the session. The session
     goes into `keyring`; the app refreshes it as `workit.py` does today.

  **The API makes the app a new Supabase session** (decided 2026-11-15),
  never the website's: Supabase rotates a refresh token at each use, so
  two holders of one session sign each other out. **A Developer checkout
  pastes the code** (decided 2026-11-15): it is no app bundle, so macOS
  can't hand it the link. PKCE makes a pasted or caught code useless
  without the app's verifier, so no `state` goes with it. **Only an
  admin's page shows the code** (found in review, 2026-11-15): a phisher
  who starts a sign-in with their own challenge could talk a student into
  sending a code they can see. The flow and its
  cases are in `docs/auth.md`, "WorkIt Auto Apply's sign-in".
- **First run:** the Chrome check (D21), the disclosure (D8), the seed
  (W6), then Ready.
- **A run:** the Auto Apply queue from WorkIt (the batch routes in
  `backend/app/routers/auto_apply.py`), the paste box, Start, tiles,
  Needs you, the Usage cap line (W1).
- **Settings:** the Worker count (one to four, default Automatic: from the memory, D24), "Remove all
  my data" (D25), "Send report" (D26), the disclosure, sign out.
- **Notices** replace phone push: the window and macOS's own notification
  for "needs you".

**Touches.** `dashboard.py`, `accounts_tab.py`, `workit.py`, a new app
entry point (`uv run apply app`), new website page and API routes in the
WorkIt repo.

**Done when.** From a Developer checkout, `uv run apply app` takes a new
user from sign-in to a filled form held on its last page, with no
terminal step and no open port.

**Steps**, each one PR:

1. Sign-in (D12). **Built (2026-11-15).**
2. The window on pywebview, no port, and `uv run apply app`, with the
   sign-in screen. **Built (KAN-858).**
3. First run. **Built (KAN-858).**
4. A run. **Built (KAN-858).**
5. Settings and notices, with Report a problem. **Built (KAN-858).**

**Built (2026-11-15, step 1): sign-in.**

- WorkIt: `POST /apply-app/sign-in` gives the website's `/app-sign-in`
  page a one-time code for the app's challenge (5 minutes, 10 sign-ins an
  hour), and `POST /apply-app/session` trades it once, with the verifier,
  for a new Supabase session (`backend/app/services/app_sign_in.py`, table
  `app_sign_ins`, migration `696b3a46ca95`). The page shows the account
  and opens the app's link (`frontend/src/app/app-sign-in/`); only for
  WorkIt's admins it shows the code with Copy Code. `/login?next=` comes
  back to it.
- Apply: `uv run apply login` is the Developer checkout's sign-in. It
  opens the page in the default browser and asks for the code in the
  terminal (`workit.login`, `workit.pkce`, `WorkIt.trade`). The Chrome
  with a debugging port that read the website's cookie is gone, and with
  it `workit.py`'s Chrome path (W4's row).
- The session is in `keyring` (item `apply-workit`): only its refresh
  token, since Windows keeps at most 2,560 bytes an item, and the access
  token in memory. The old `workit-login.json` goes at the next save.
- A Google or LinkedIn sign-in started on `/login` comes back to the page
  (and to the connector's), through `frontend/src/lib/sign-in-next.ts`.
- What ends the app's session, read in Supabase's source: its sign-out, a
  sign-out everywhere, deleting the account, and a password change. An
  app sign-in cancels a password-reset link asked for just before
  (`docs/auth.md`).

**Built (KAN-858, step 2): the window, with no port.** `uv run apply app`
runs `apply.student.app`, the Student build's entry point.

- **The routes stay; the port goes.** `Dashboard(serve=False)` listens
  on nothing. `apply/app_window.py` loads the Apply window's own page as
  a string (pywebview opens no server for that) with `SHIM` before its
  scripts. The shim sends each `fetch` of a path to `Bridge.request`,
  pywebview's `js_api`, which answers it in this process through the same
  handler, checks and token as the server (`Dashboard.respond`). The
  tiles' `/frames` stream comes from `Bridge.frames`, and a link to a file
  a tile lists opens in the system's own app (`Bridge.open`, only what
  `Dashboard.listed` allows). So the 28 routes did not become 28 bridge
  methods, and the Developer checkout's Chrome window keeps the server.
- **Signed out, the window shows the sign-in screen:** Sign In with
  WorkIt opens `/app-sign-in` with a new PKCE challenge, and the box
  takes the code (an admin's page shows it); then the window shows the
  Apply window with the student's answers.
- **Checked on this Mac in WKWebView:** the page's requests and a tile's
  frames came through the bridge, and the process listened on no port.
  `tests/test_app_window.py` (CI) and `tests/test_app_window_page.py`
  (Chromium) test it.

- **The app's page loads no web font** (`app_window.FONTS`): Google
  Fonts would be a request the privacy page doesn't name. The system's
  fonts stand in.

**Built (KAN-858, step 3): first run** (`apply/first_run.py`, `FIRST_RUN`
in `app_window.py`). After sign-in, one step at a time, before the Apply
window:

1. Google Chrome (D21): the Chrome finder's; missing, Download Google
   Chrome, and the window goes on by itself once it is installed.
2. What leaves the Mac (D8, section 3.4) and the license (W10): OK once
   for each `first_run.DISCLOSURE`; Read the License opens `EULA.txt`.
3. Screen Recording, on a Mac only: asked once (`Quartz`'s
   `CGRequestScreenCaptureAccess`, which pywebview's pyobjc brings), or
   Not Now. Without it, Fix here's view is about two frames a second (W2).
4. The seed: `apply plain seed`'s wizard in its own thread, its lines in
   the window and its "press Return" as Try Again, till a real Worker says
   hello. The way in until a store copy can be used (W6). Skipped when
   the Workers run on Chrome for Testing (`plain_chrome: testing`), which
   loads the worker extension itself.

Chrome and the seed are looked at again at each launch; the disclosure,
the Screen Recording ask and the Worker count are kept in the data
folder's `app.json`. **The Student build's data folder is
`home.APP_FOLDER`** (D25): `home.HOME` reads `build.STUDENT` once, at
import, which the build script writes before it compiles.

**Built (KAN-858, step 4): a run.** With no run going, the window shows
the queue: the student's queued, open jobs on WorkIt (`Bridge.queue`),
oldest first, a job board's posting by its employer's form; a box for one
pasted link; Start (`Bridge.start`). Start runs the ticked links
in `student.Runs`: `student.adapters()`, the Worker count from Settings,
and the run's own Apply window, its tiles, till every form it held is
closed; then the queue again. One run at a time. The window comes back to
the front after a captcha (Dashboard's `back`, `app_window.bring_forward`,
a Mac only). A run that can't start (a refused engine, W7's
`EngineRefused`; a Worker profile in use) says why in one line. The frame
source and closing the plain Workers moved from `cli.py` to
`worker_tiles.py`, so the Student path has them; quitting the app stops the
plain Workers' Chromes, which outlive it.

**Built (KAN-882): Find jobs.** With no run going, the window first
shows Find jobs: the student's best Auto Apply matches they haven't queued
or applied to (`Bridge.matches`, the `auto-apply/matches` route), with the
website's Jobs page search, filters and cards. The student picks jobs and
presses Start applying, which runs them as ticked queued jobs run; the
queue and a pasted link are one click away
(`apply-agent/docs/apply-window.md`).

**Built (KAN-858, step 5): Settings and notices** (`SETTINGS`): the Worker
count (one to four, D24), What Leaves Your Mac, the license and the
third-party notices, Sign Out (`WorkIt.sign_out` ends this session at
Supabase and forgets it), and Remove All My Data (D25): the login and the
whole data folder, then the app closes, in the Student build only, since a
Developer checkout's data folder is the developer's own. A second press
removes. Notices of what newly waits on the student (Dashboard's
`notify`) are macOS's own, which only an app bundle may post (W8).

Checked on this Mac in WKWebView: first run's disclosure, the queue with
its usage line, and Settings. `tests/test_first_run.py` and
`tests/test_app_window.py` (CI) and `tests/test_app_window_page.py`
(Chromium: every page of the app runs with no script error) test them.

**The Student build's window shows the student page** (KAN-867,
KAN-869), in place of the developer Apply window: one to-do card at a
time, "Still working on", Applied (this run's, then those on WorkIt from
before), the queue and Start when no run goes (Add jobs brings it back
whenever no run is going; a run refuses a second), today's usage as a bar
(the share of the Usage cap used, never a token count, read again as each
form is filled; KAN-837) with words from 80%, and Settings. Its source is
`apply-agent/window/` (React, Tailwind, the website's tokens and Inter),
built by Vite into one self-contained file committed in the package
(`apply/student_page/index.html`), so the app ships it with no Node; CI
checks the file matches its source. `app_window.student_page` puts SHIM
and the window's token (`window.APPLY_TOKEN`) before its scripts. The page
reads `/state` and sends `/answer`, `/approve`, `/show/<k>`,
`/fill-again`, `/stop` (Stop applying) and `/remove` (one job not started
yet) with plain `fetch` and the token, which SHIM carries to the
same handler and checks, with no port; it uses the bridge's app methods
(queue, applied, start, status, usage, settings) only when the window has them. A
Developer checkout's window, which runs nothing, keeps the developer page.
A run's board takes the student's answers (`answers_tab.saving_answers`).

**Built (KAN-858): Report a problem** (D26, W1's #614), in Settings: what
it is about (`report.CATEGORIES`), what happened, "WorkIt may email me
about this". Review Report makes the report (`Bridge.review_report`, which
calls `report.build`) and lists what goes (`report.parts`); Send Report
sends that same report (`Bridge.send_report`), and a changed answer hides
Send Report till it is reviewed again. After it, the form says WorkIt
deletes the report once its problem is fixed. With an Application's id,
the report is about that Application, with its record and log unless the
student unticks them: its Tracker row, or, for a form this run held (a
rehearsal keeps no Tracker row for one), its tile with its newest Record
under `student.RECORDS`. `build`'s `profile` is the Applicant profile's
file (`app_window.PROFILE`), never its folder: the log's mask reads a path
it can't open as no values, so a folder sent the student's name and street
in the log. No words, `build`'s ValueError, and each of the send's errors
(the daily cap's too) are each a one-line message.

The student page has the same form on each Application's to-do card,
its "Didn't go through" row and its Applied row (`window/src/report.tsx`),
under "Report a problem". It calls `review_report` with the Application's
id, and `send_report` with that id too, which refuses a report another
form reviewed since: the window keeps one report, so without the id a
second form's Review Report changed what the first one's Send Report sent.
It shows only for a job with an `application_id`, in the app's window; its
categories come in the page (`window.REPORT_CATEGORIES`, from
`report.CATEGORIES`, put in by `student_page`).

**Built (KAN-858): the Student build's Tracker is in the data folder**
(`student.adapters`): `WorkItTracker(FileTracker(), WaitingWrites(), ...)`,
as a Developer checkout's, in place of a Tracker in memory. So the
Employer accounts outlive a launch (the Accounts tab shows them), a
submitted job is found as already applied, and the student's own Submit
from a held form is written to their Applications Tracker on WorkIt with
the resume the form was given (KAN-544). Remove All My Data (`first_run.remove_all_data`) forgets each
Employer account's keychain item (`apply-ats`, one per site) before the
folder goes, and names any the keychain kept.

Left from W5:
- A tile added during a run (`--into`) reloads the page with
  `location.reload()`, which a page loaded as a string can't do. The app
  never sends a link into a run, so only the Developer checkout's window
  does.

**The built app's link: built (KAN-833, 2026-11-21).** The build adds
`workit-auto-apply://` to the bundle's `Info.plist` (`CFBundleURLTypes`),
so macOS opens the app for the page's link and hands it the link as an
Apple event; the app's handler (`sign_in_link.listen`, set up once the
run loop runs) keeps it in memory for the window's sign-in poll, and no
file holds it. A checkout's window still has a helper applet claim the
scheme for it (`apply-agent/src/apply/sign_in_link.py`, KAN-883); the
built app makes no helper.

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

**Built after the spike (KAN-839, 2026-11-14):**

- No user scripts: the manifest asks for none, `eval` runs through the
  debugger on every page, a code-only init script is refused, and the
  seed's setup is Developer mode and Load unpacked only.
- No engine file: Apply hands the engine to the extension's memory once
  per connection (`cdp.keep`), and `vendor/` holds no `engine.js`.
- The store package: `uv run apply plain package` builds the zip
  (`apply-agent/dist/`) with the guard scripts, `fixed.js` and
  `injected.js` built in, `LICENSE`, `NOTICE` and Playwright's
  Apache-2.0 license, `store.json`'s name and version, and no manifest
  `key`. The hello names the package's built-in files and its install
  type; the bridge welcomes a package to its own files when they are
  Apply's, and refuses a store copy whose files aren't. A test loads the
  package in Chrome for Testing, guards a page from its files and loads
  the engine.
- Both extension IDs may connect (`extension.STORE_ID`, empty until the
  store gives one).

**The adversarial review (2026-11-14) found a blocker:** the guard scripts
carry each Apply process's own random tokens (KAN-710), so a package built
once never matches a student's app and the bridge refuses every store copy.
It fails closed, but no store copy can be used until the guards learn their
tokens another way (the to-do list's item 0, for the guards' owners). It
also fixed two smaller issues: `refresh` and a store copy, and the `gesture`
flag. A change to what the package holds now fails CI until `store.json`
records a new version (`apply-agent/CLAUDE.md`).

Left: `apply-agent/docs/plain-workers/worker-extension-todo.md` lists it,
item by item: the first store upload and its ID, the seed from the store,
releases and updates, item 3 in branded Chrome, a multi-step form on a
plain Worker, and the tile's screencast.

**If the spike passes:** list "WorkIt Auto Apply Worker", unlisted, from
WorkIt's existing developer account: a privacy policy link, one stated
purpose ("lets WorkIt Auto Apply control its own Chrome windows"), a
reason for each permission, and a license header in each file (W10).
The native host's manifest names the store's extension ID beside the
Developer checkout's unpacked one. The extension updates from the store
on Chrome's schedule, so the app and the extension check one protocol
version on hello (`PROTOCOL.md` already has a feature number) and the app
says "Updating the Worker extension" while they differ.

**If the spike fails:** v1 keeps the extension off the store. First run
guides the student through Developer mode and Load unpacked
(`plain/seed_setup.py` does this today), and the engine still reaches the
Worker in memory, not in a file.

**Touches.** `apply-agent/worker-extension/` (`ops/cdp.js`, `ops/debug.js`,
`ops/core.js`, `ops/guard.js`, `ops/engine.js`, `ops/tile.js`,
`background.js`, `manifest.json`), `apply/plain/` (`script`, `page`,
`bridge`, `extension`, `launcher`, `seed_setup`, `tile`),
`docs/plain-workers/PROTOCOL.md` and `guide.md`.

### W7. The engine download and its protection

**Goal.** The Fill engine never sits on the student's disk in plain text
and comes only from WorkIt (D3, D27, D28).

**Built (KAN-836, 2026-11-15).**

1. **Sign and publish, on each merge.** `.github/workflows/publish-engine.yml`
   runs `uv run python -m app.scripts.publish_engine publish --key <file>`
   when a merge to `main` moves the engine pointer or
   `backend/app/scripts/engine_min_app.txt` (the oldest app the engine
   fits). It signs the submodule's `dist/engine.js` with WorkIt's
   Ed25519 engine key and puts it in the private Supabase Storage bucket
   `ApplyEngine` (chosen over Cloudflare R2 on 2026-11-15: no new account
   or cost): `<sha256>.js`, and a line in `builds.json` (`sha256`,
   `signature`, `min_app`, `published_at`). It refuses a bundle that names a
   source map, so no source map ships, and a key whose public half Apply
   doesn't hold. A run with nothing new uploads nothing, and a pointer
   moved back serves the older build again, unless the bad build had a
   higher min app (`autofiller_extension/CLAUDE.md`, "Move the engine
   pointer"). `make-key <file>` makes the key
   once; its private half is a secret of the `auto-apply-desktop` environment,
   which takes jobs from `main` only, since whoever holds it can make every
   app run their code (`.github/CLAUDE.md`, "Publish the Fill engine").
2. **Serve.** `GET /apply-app/engine?app_version=` (signed in) answers the
   build made for the nearest app version at or below the app's (the
   highest `min_app` that fits, then the last published), so a fix
   published later for older apps never reaches a newer app. It is
   encrypted with AES-GCM under a key for this account, this Supabase
   session and this download. `POST /apply-app/engine-key` makes that key
   again for two minutes, for the same account and session only. The key
   is an HMAC under a key derived from the API's service key: nothing is
   stored, and every API instance makes the same key
   (`backend/app/services/engine_builds.py`). The server never checks a
   signature; the app does.
3. **Load.** `apply.engine_download` asks for both, decrypts in memory and
   checks the signature with `PUBLIC_KEY`, compiled into the app. Every
   reader takes the text from `fill_engine.source()`: Node on its stdin,
   CDP Workers through `page.evaluate`, plain Workers over native
   messaging. It runs once per process, and `rehearsal.rehearse` checks it
   before any Worker opens, so a wrong signature, a changed download, no
   sign-in or no build for this version stops the run with one sentence.
   The Student build always uses it; a Developer checkout uses it with
   `fill_engine: workit` in `policies.yaml` (`apply-agent/docs/fill-engine.md`).
4. **Pinning.** `apply.workit` trusts only Cloudflare's CAs for
   `api.workitjobs.ai` and for the live Supabase Auth, which is behind
   Cloudflare too (Let's Encrypt, Google Trust Services, SSL.com, and
   Sectigo, which Cloudflare uses for backup certificates), 13 roots from
   certifi's copy of Mozilla's list (`apply-agent/scripts/workit_roots.py`;
   `--check` connects to both with them). The session's hourly refresh goes
   to Supabase, so pinning the API alone let a proxy read the refresh token
   and then download the engine itself. A local stack is not pinned. Sparkle's feed is on another host without pinning, so an update
   can change the set. Cloudflare's own documentation advises against
   pinning to its CAs, since it may change them: the set must ship before
   it does.

**The steps by hand are done** (`.github/CLAUDE.md`, "Publish the Fill
engine"): the key (`make-key`), with its public half in
`engine_download.PUBLIC_KEY`, the private `ApplyEngine` bucket, the
environment with its branch rule and secret (`auto-apply-desktop` since
KAN-941), and the first publish, which passed on 2026-11-17. With no build
published, the API answers 503 and the app says that WorkIt did not send
the Fill engine.

**A dependency outside this design.** The WorkIt extension ships the
minified engine in its public store package today, so anyone can read
it. The download above protects one copy while another is public. A
teammate's work on the engine's exposure through the extension must
close that gap, or most of W7's value is lost. KAN-849 (#582,
2026-11-14) put the WorkIt extension under its own license: it forbids
copying, but the code stays readable.

**Done when.** A Developer checkout runs a form with the engine from
the route, the data folder and the Worker extension's folder hold no
engine file, and a wrong signature stops the run with a clear message.
Checked on 2026-11-15 against the API on the same computer, with a
stand-in bucket and sign-in (the route itself is not deployed until the
merge).

### W8. Compile, sign, notarize, update, publish

**Goal.** A signed, notarized `WorkIt Auto Apply.dmg` that updates
itself (D17, D18, D20).

**Design.**

- **Compile:** Nuitka, standalone, as a macOS app bundle, on Apple
  Silicon with macOS 13 as the minimum (`MACOSX_DEPLOYMENT_TARGET`). It
  holds Playwright's Node driver (`site-packages/playwright/driver/`) as
  data, pywebview, and none of W3's modules. It also keeps Apply's own
  package metadata (`--include-distribution-metadata=apply`): the engine
  download names the app's version from it (`engine_download.app_version`,
  W7), and without it no build fits. `cryptography`'s compiled module
  (`_rust.abi3.so`) is a Mach-O file to sign like the others. Nuitka is AGPLv3 with an
  exception: the compiled app is not bound by the AGPL.
- **The native host is the app's own program** (found 2026-11-14, built
  2026-11-21). Chrome starts the plain Workers' relay
  (`apply/plain/host.py`) through a wrapper that runs it with `python3
  -I`. A compiled app has no Python, so the wrapper starts the app's own
  program with `--worker-host` first, and the program then runs only the
  relay (`scripts/app_entry.py`). One program, not two: a second would
  carry a second copy of Python's runtime.
- **Sign:** Developer ID, with the hardened runtime and without
  `get-task-allow`, so other programs can't read the app's memory. Every
  Mach-O file inside is signed, the Node binary included, with the
  entitlements Node needs (JIT) and the app's Apple events
  (`com.apple.security.automation.apple-events`: FocusKeeper's `osascript`
  to System Events), and no more.
- **Notarize** with `notarytool`, then staple.
- **Update:** Sparkle with its own EdDSA key; the feed and builds on
  Cloudflare R2; a beta channel for testers. The app checks at launch and
  installs at the next restart.
- **Publish:** a download page on workitjobs.ai (WorkIt repo, `frontend/`)
  that says "Apple Silicon Macs (M1 and later), macOS 13 or later". Built
  (KAN-835): `/auto-apply/desktop`, Auto Apply's Desktop App tab
  (`frontend/docs/screens.md`). Publishing the DMG sets `DOWNLOAD_URL` in its `page.tsx`.
- **Build a release in one workflow** (D32):
  `.github/workflows/publish-app.yml`, by hand from `main`, on a
  GitHub-hosted Apple Silicon Mac: `scripts/build_app.py --release`, from
  step 2 the Developer ID signature and notarizing, Sparkle's signature
  (`scripts/publish_app.py`), the upload. Its keys are secrets of the
  `auto-apply-desktop` environment only (`.github/CLAUDE.md`, Publish
  WorkIt Auto Apply). A release builds from the commit's own files (`git
  archive`), never the working tree, and writes the commit into
  `Info.plist` (`WorkItCommit`).

**Steps.**

1. **Compile only. Built (KAN-833, 2026-11-21).** `python3
   scripts/build_app.py` makes `build/out/WorkIt Auto Apply.app`, about
   227 MB, with the compiler's ad-hoc signature, so it opens only on the
   Mac that built it. It compiles in a venv of its own with uv's Python
   3.12, with Apple's tools only, with no docstrings, and refuses an app
   that holds a developer module, Python source or a docstring
   (`apply-agent/CLAUDE.md`, "Building the app"). The built app opened its
   window and ran the relay. On 2026-11-21 it passed the sign-in round trip
   in the browser and the Worker setup, which ends on a real plain Worker's
   hello through the app's own relay. It claims `workit-auto-apply://` and takes
   the sign-in link itself (W5's last step), and ships the plain
   Workers' window capture helper, built by `swiftc` in the build, since a
   student's Mac has no `swiftc`. Step 1 is done.
2. Sign with Developer ID and notarize. Built (KAN-950, 2026-11-27), never
   run: every build signs each program with the hardened runtime and
   only its own entitlements (Node's JIT, the app's Apple events), a test
   build ad hoc; `publish-app.yml` signs with the Developer ID from a
   keychain it makes, `scripts/notarize_app.py` notarizes the DMG and
   staples its ticket, and a publish refuses a DMG with none
   (`apply-agent/CLAUDE.md`, "Building the app"). An ad-hoc build under
   the hardened runtime ran its window, Sparkle, the relay and Node.
   Left: the Apple enrollment, its five keys in Infisical, and the first
   notarized build opened on a Mac that never built the app.
3. Sparkle: the framework in the bundle, the key, the feed on R2. Sparkle
   is in the build (KAN-941, 2026-11-24): the pinned 2.10.1, the feed at
   `https://downloads.workitjobs.ai/appcast.xml`, checks and installs with
   no question, and `apply.updates` to start it; tested end to end on one
   Mac with a throwaway key and a local feed (`apply-agent/docs/app-build.md`).
   The key is made and its public half is in every build (2026-11-26).
   Left: a beta channel.
4. The DMG, its upload, and `DOWNLOAD_URL`, after W0, W6 and W7. The DMG
   is built (KAN-833, 2026-11-24): `build/out/WorkIt Auto Apply.dmg`, with the
   app, a link to Applications, and the license and notices beside them.
   Publishing is built (KAN-941, 2026-11-26): the workflow above, into
   the R2 bucket `auto-apply-desktop` behind `downloads.workitjobs.ai`.
   A publish refuses a DMG Apple hasn't notarized (step 2). Left: the
   first publish, once step 2's keys are in, and `DOWNLOAD_URL`.

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

**Built (KAN-848, #579, merged 2026-11-14 with the team's yes).** Legal
text merges only once the team approves it.

- **App license (EULA):** `apply-agent/legal/EULA.txt`, adapted from
  Basecamp's open-source policies (CC BY 4.0; the repo was archived on
  2026-10-06). Its Credits section is the attribution that CC BY needs:
  the source, the license's link and what WorkIt changed. It forbids
  copying, reverse engineering, using the app or its output to train AI
  models, and giving the app to an AI tool to learn how it works, as the
  Worker extension's `LICENSE` does. It also limits the app's AI, and the
  WorkIt routes the app calls, to filling and checking the student's own
  applications in the app: no other program, no prompts of the student's
  own (decided 2026-11-14; the license's side of D5's reason, beside the
  server's kinds and schema checks). The answers the app writes for a
  student stay the student's to keep and send (decided 2026-11-14). **Why in
  `apply-agent/legal/`:** the file ships with the app, which W8 builds
  from Apply's folder, and W0's `git filter-repo --subdirectory-filter
  apply-agent` takes only what is under `apply-agent/` to
  `workitjobs/apply-agent`; a file at WorkIt's root would stay behind.
  It covers the app as WorkIt distributes it and says nothing about the
  MIT code: that code leaves public view (the MIT bullet below). The
  five copyright holders approved licensing the compiled app under it
  (2026-11-14).
- **WorkIt's `/terms`:** a section "WorkIt Auto Apply for Mac" that sums
  up the EULA (each line points to the EULA's rule), and the page's first
  line names the app.
- **WorkIt's `/privacy`:** a section "WorkIt Auto Apply for Mac": what
  stays on the Mac; what goes to WorkIt (the AI calls' data, the Tracker,
  the queue, Send report only on a click, no analytics); what the AI calls
  send, after section 3.4 and W1's server (WorkIt builds each prompt and
  sends it to Groq or Google with its own key, masks email, phone and
  links a second time, and logs no prompt or answer); that Google's free
  tier uses prompts to improve its products and lets people read them,
  and that Groq can log them for 30 days; job sites; the Worker extension
  (it sends only to the app, under the store's User Data Policy and its
  Limited Use rules); Chrome; updates from Cloudflare; "Remove all my
  data"; and the daily use counts, kept 90 days. The page already named
  Supabase and Cloudflare. The website's AI section now says that only
  the website and the extension keep form answers from the models.
  Tavily joins the page with F2.
- **Third-party notices:** `uv run python scripts/third_party_notices.py`
  (in `apply-agent/`) writes `dist/THIRD-PARTY-NOTICES.txt`. It runs
  `pip-licenses` on a new environment built from `uv.lock` without the
  dev group, so a new dependency joins it with no edit, and adds
  Playwright's driver (Node.js's license, playwright-core's and the
  license files beside its bundles), Python's own license (Nuitka
  compiles the runtime in), and a hand list, `BY_HAND`: pywebview
  (BSD-3-Clause; left out since KAN-858 added the package, which
  pip-licenses lists with the pyobjc packages and bottle it brings),
  Sparkle (MIT, with the notices for the code it includes), Nuitka's
  runtime exception (AGPLv3; the compiled app is not bound by the AGPL)
  and the cover letters' Latin Modern font (GUST Font License). A hand
  entry's full text goes in `apply-agent/legal/licenses/`, copied from
  the release that W5 or W8 uses; `--strict` fails until each is there.
  On 2026-11-14 it listed 27 packages, each with its license text, in
  about 400 KB.

**Before the app ships, `/privacy` must be true of it (found
2026-11-14).** The page describes the app as section 3.4 designs it, and
the app does not do all of it yet:

- **W1's app side (D8) is built but for reworded self-ID answers** (PR
  #587, 2026-11-15): the app replaces the exact private values the
  student gave (names, email, phone, street, ZIP code, birth date, links,
  references) with placeholders in every call and puts them back, the
  server masks contact details again, and a form answer that is exactly
  one of the student's self-ID answers is left out. A self-ID answer the
  Fill engine typed in the form's own words still goes (section 3.4), and
  the page says self-ID answers are included; once the engine reports
  its sources and Apply leaves those out, the page changes with it. Not
  done: a student ID has no placeholder, since the profile keeps none.
- **Send report is built** (W1's #614, and its form in W5's Settings):
  **WorkIt keeps a report until the problem it shows is fixed, then
  deletes it** (decided 2026-11-14), and `/privacy` says so. The team's
  `DELETE /admin/apply-reports/{id}` marks it fixed and deletes it; there
  is no period in `backend/app/services/retention.py`. A report whose
  problem is never fixed stays until the team deletes it.
- **The page merged before W1's PR (#577)**, whose route it describes.
  Both are on `main` now.

**Left.**

- W5 shows the EULA at first run and in Settings, with the notices
  (KAN-858). W8: put `EULA.txt` and `THIRD-PARTY-NOTICES.txt`
  (made with `--strict`) in the app bundle and the DMG, and link both
  from the download page.
- W3: when the Student build leaves out a developer part, move the
  packages only that part needs (`gspread` and `google-auth` for the
  Google Sheet) to a dependency group, so the notices leave them out.
- Groq: the team may turn off Groq's 30-day logging (Zero Data
  Retention, in its Data Controls) for WorkIt's organization; then
  `/privacy` changes.
- A new provider in production's model chain (Cloudflare Workers AI is
  in the spec, `scout/CLAUDE.md`) joins `/privacy` before it gets an app's
  prompt.

**Done before.**

- **Chrome Web Store:** a privacy policy link and its user-data rules for
  the Worker extension. Done (KAN-839, approved by the team 2026-11-14):
  its `LICENSE` (proprietary: no copying, reverse engineering or AI
  training), `NOTICE` (Playwright's Apache-2.0 script) and a header line
  in each file. `/privacy`'s Worker extension item (KAN-848) is the
  policy that the store listing links to.
- **The repo's MIT license (found 2026-11-14).** The WorkIt repo's root
  `LICENSE` is MIT, held by five team members, and covers everything in
  it, Apply and the Worker extension too. Every version already pushed
  stays MIT: anyone may copy it, and a new license can't take that back.
  The five holders agreed (2026-11-14) to license the Worker extension's
  new versions under its own proprietary `LICENSE`, and the root
  `README.md` says so until Apply moves to its private repo (W0). **The
  team decided (2026-11-14) to make the WorkIt repo private and remove
  the open MIT code from public view.** That stops new copies. It does
  not take MIT back from a copy someone already has, so the EULA names
  no MIT code at all. **Not done yet:** on 2026-11-14 `workitjobs/workit`
  was still public, and with it the prompts in
  `backend/app/apply_prompts/` (D5).

**Not now:** a review of the hiring systems' terms on automated
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
   Applications left". **Parked (KAN-837, 2026-11-17)** on branch
   `KAN-837-tokens-by-kind`, not merged; W13 starts again from it:
   - Each WorkIt call's Trace event gets the `tokens` WorkIt counted
     against the cap, or the status it `failed` with
     (`WorkItAsk._post`). Each fill already ends with a `result` event.
   - `uv run apply tokens [--since YYYY-MM-DD] [--cap N]` adds them up
     over the Traces: by call kind, by job system, and a fill's tokens
     divided into the cap. Each `start` in a Trace is one fill, so a Fill
     again counts on its own.
   - **Fix before it merges:** it divides by every fill, so a fill that
     stopped early (a sign-in, a closed posting, a failure) counts as a
     whole form, and "about N" comes out too high (15 forms of 8,000
     tokens and 5 stops of 300 gave 13; the right answer is 9). Divide
     all tokens by the fills whose `result` reached the form's end (held
     or submitted). Name job systems with `preflight.job_system`:
     `Posting.job_system` puts Jobvite, SmartRecruiters, iCIMS, BambooHR
     and Paylocity under "other".
   - It can't see what a failed call spent (WorkIt counts it; its answer
     doesn't say), or calls outside a fill (`apply story-map`, a held
     page's Regenerate or Ask Claude).
   - The measurement: rehearse about 20 postings across hiring systems
     with `ask_model: workit`, against a local API with a higher
     `APPLY_APP_DAILY_TOKENS` (on the real server they count against the
     developer's own cap), then run `apply tokens --since` that day.
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

### F4. Windows and Linux

Linux joined the port on 2026-11-14 (D10). W4 writes each per-OS entry
for all three systems; F4 builds, packages and tests the app on Windows
and Linux. W4's "Found on the way" list names what W4 left for it (file
locks, the plain Workers' channel, the process check, Chrome's profile
lock, signals, the hosts' wrappers, the seed guide's words), and
`windows_desktop.md` (KAN-929) takes them one at a time.

| Part | macOS | Windows | Linux |
|---|---|---|---|
| Native host manifest | A JSON file in each Worker profile's `NativeMessagingHosts/` | A registry key under `HKCU` that names the manifest | A JSON file, as on macOS |
| The host's launcher | A shell-script wrapper | An `.exe` or `.bat` wrapper | A shell-script wrapper |
| Apply ↔ host channel | A socket file | A named pipe (no port; `windows_desktop.md`, P4) | A socket file |
| Starting Chrome in the background | `open -g` | A process with no focus | A background process |
| Keeping Workers behind | FocusKeeper | The OS (a flashing taskbar button) | The desktop's focus-stealing prevention |
| Window | pywebview on WKWebView | pywebview on WebView2 | pywebview on GTK or Qt |
| Secrets | `keyring` on Keychain | `keyring` on Credential Manager | `keyring` on the Secret Service (GNOME Keyring, KWallet) |
| Signing | Developer ID and notarization | A code-signing certificate, so SmartScreen doesn't warn | To decide with the package |
| Updates | Sparkle | WinSparkle or similar | To decide with the package (an AppImage, a `.deb`, or both) |

Test early: background-window behaviour (`--disable-backgrounding-occluded-windows`
reads window cover differently per OS), the native host under a school's
managed Chrome, and on Linux, focus on more than one desktop (GNOME, KDE),
since each has its own focus-stealing rules.

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
- **Writing on WorkIt:** moved into v1 (2026-11-14, D5 and W1's
  "Prompts on the server").

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

### F10. Workers out of the student's view

Each Worker is its own Chrome process, with its own profile. On the Mac,
five Workers are five Chrome icons in the Dock, five apps in Cmd-Tab and
five windows in Mission Control (two plain Workers made two Dock apps,
2026-11-15). macOS gives each running copy of an app its own Dock icon,
and it cannot group separate processes. W5's window shows every Worker as
a tile, so the student needs none of these windows. The tests and the
helper to repeat them are in `apply-agent/docs/research/workers-out-of-view.md`.

Not a path (tested or checked 2026-11-15):

- **Hiding or minimizing a Worker.** Hidden as Cmd-H hides it, its windows
  leave Mission Control, but a hidden page draws nothing: in 3 s a plain
  Worker drew 0 frames (180 when shown), and its screenshots failed. The
  tiles would freeze, and job sites would see a hidden page. Chrome's
  `--disable-renderer-backgrounding` and
  `--disable-background-timer-throttling` keep its scripts running, but it
  still draws nothing.
- **Hiding Chrome's Dock icon.** Chrome has no switch for it, and editing
  its app breaks Apple's signature.
- **Another macOS desktop (Space).** No supported way lets an app move a
  window there.
- **Headless Workers.** Plain Workers can't be (§4.7); CDP Workers have had
  windows since 2026-10-17, for the bot checks.
- **Chrome on WorkIt's servers, streamed to a web page.** Out for §4.6's
  reasons (reconsidered 2026-11-15): data-center IPs are blocked far more
  often, WorkIt would hold every student's job-site sign-ins and
  passwords, and the cost is highest. The latency (about 0.1 to 0.3 s a
  round trip) was not the problem.

Two parts that can still be built, each alone or both. Together, the
student sees one Chrome in the Dock and no Worker in Mission Control.

1. **One Chrome process for every Worker.** Each Worker becomes a profile
   (`--profile-directory`) in one Chrome user data folder, so the Dock and
   Cmd-Tab show one Chrome. Mission Control still shows each Worker's
   window, under that Chrome. It is a large change:
   - Playwright opens one persistent profile per Chrome, so CDP Workers
     need another way to reach their profile's pages.
   - The native host's manifest is one per user data folder, so each
     plain Worker's extension must say which Worker it is (today the
     wrapper in its own profile says so).
   - Apply stops a Worker by its Chrome's PID; with one process it closes
     the profile's windows instead, and one crash or quit ends every
     Worker. The in-use check (`SingletonLock`, one per folder), restart
     recovery and the seed copy change with it.
   - On Windows, Chrome may still give each profile its own taskbar
     button (not checked, F4).
2. **Workers on a virtual screen** (tested on macOS 26.0.1). macOS's
   private `CGVirtualDisplay` classes make a screen that no one sees, and
   the Workers' windows go there. A 40-line helper made a 1920 × 1080
   screen. Chrome for Testing on it drew 181 frames in 3 s, its page was
   visible, and screenshots and the screencast worked: the tiles keep
   working. Mission Control on the main screen did not show its window
   (checked by hand, 2026-11-15): macOS shows each screen's own windows
   there.
   - macOS treats it as a real screen. System Settings lists it, and it
     sat beside the main screen, so the pointer can move onto it and seem
     to vanish.
   - It lives only while the process that made it runs, as a monitor
     lives only while it is plugged in. Tested: when that process died
     with no clean exit, the screen went away at once, Chrome kept running
     and drawing, and in under 3 s macOS moved its window onto the
     student's screen (from x 2022 on the 1920 × 1080 screen to x 306 on
     the 1512 × 982 one). Workers outlive Apply on purpose (restart
     recovery), so a crash shows every Worker's window to the student.
   - It is a private Apple API. Apple documents none of it, ships it in no
     developer kit and promises nothing: the helper finds the classes by
     name as it runs. Any macOS update can rename, change or remove them,
     or allow them only to apps Apple approves. Other Mac apps
     (BetterDisplay, DeskPad) use them today. The app ships outside the
     Mac App Store (D17), which would refuse it.
   - The Dock and Cmd-Tab still show each Chrome, unless part 1 is built
     too. It is Mac only: Windows and Linux need their own way (F4).

   Before it ships to Mac users, build:
   - **A holder that outlives Apply.** A small helper, apart from Apply,
     holds the screen while any Worker runs. When the helper itself dies,
     Apply makes the screen again and moves the Workers back.
   - **A fallback.** When the API is missing or refused, Workers open on
     the student's screen, as today.
   - **Window placement.** The Worker extension opens a plain Worker's
     window on the primary screen (`onScreen` in `ops/core.js`), so it
     must aim at the virtual screen: a store release. CDP Workers take a
     start position. Pop-ups, such as a sign-in window, must open there
     too.
   - **Show and handoffs.** For a captcha or a sign-in, Show moves the
     window onto the student's screen and back after; or the student works
     in the tile, which already sends clicks and keys to the Worker.
   - **The pointer.** The app places the screen where the pointer rarely
     goes (`CGConfigureDisplayOrigin`, a public API), and again when the
     student plugs in or removes a monitor.
   - **Packaging.** The helper is Objective-C: it is signed and notarized
     inside the app (W8), and must work under the hardened runtime.
   - **Words for the student.** System Settings, Displays lists a screen
     named "WorkIt Auto Apply"; the app says what it is.

   And test:
   - the Mac asleep, its lid closed and its screen locked: does the
     screen still draw?
   - a monitor plugged in or removed while Workers run;
   - the oldest macOS the app supports, and each new macOS, betas too;
   - the memory and graphics cost of a 1920 × 1080 screen;
   - the bot checks: pages see this screen. HiDPI off gave a pixel ratio
     of 1, where a MacBook's own screen gives 2, so the screen's settings
     must look like a common Mac setup;
   - FocusKeeper: Chrome can probably still take the keyboard focus when
     a pop-up opens on a screen no one sees, so it likely stays.

## 8. Who can see the code

Anything that runs on the student's computer can be read in the end;
each step only raises the cost.

| Part | Where it is | Protection |
|---|---|---|
| Apply's Python | The private repo; machine code in the app | Nuitka. No prompts in it once W1's "Prompts on the server" is done |
| Answering guides and prompts | WorkIt's server (`backend/app/apply_prompts/`, D5) | Never in the app; a request carries data only |
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
| GitHub Actions | Small Linux jobs on PRs, and a Mac runner for each release (D32). Free while the repo is public; after W0's private repo, a Mac minute counts as about 10 free minutes (check GitHub's prices then) |
| **Fixed total for v1** | **About $99 a year** |

## 10. Open questions

- How the guards learn their per-run tokens, so that a store copy can
  be used (W6; `worker-extension-todo.md`, item 0). The spike chose the
  store with the debugger (KAN-839).
- The Usage cap's number after W13, and when to move to paid tiers (F3).
- Where the brief pipeline runs, and when it is built (F2).
- The teammate's work on the engine's exposure through the WorkIt
  extension (W7's dependency).
- When to enroll with Apple, and when to convert to an organization (F7).
- **When the Fill engine reports which answers it took from a self-ID
  fact** (its own repo, then a pin move), so that Apply leaves out the
  self-ID answers it rewords too (D8, section 3.4).
- **Whether Gemini's free tier stays in the Model route's chain** while
  reworded self-ID answers reach it: the team allowed it on 2026-10-14
  only because identity data is removed on every call (`scout/CLAUDE.md`).
- Whether to keep Workers out of the student's view (F10): one Chrome
  process, a virtual screen, or both.

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
- **2026-11-14:** W4's rules: Linux joins Windows as a later port (F4); a
  general library comes before per-OS code; FocusKeeper and `open -g` stay
  Mac-only; and keeping a job-site password from the student is not a
  requirement, so Copy password uses the window's clipboard (D35).
- **2026-11-15:** five Workers are five Chrome apps on the Mac. Hiding a
  Worker stops its drawing, and a virtual screen keeps it drawing and out
  of Mission Control. One Chrome process for every Worker and a virtual
  screen stay future work (F10). Chrome on WorkIt's servers stays out (§4.6).
