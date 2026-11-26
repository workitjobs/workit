# WorkIt and the Applications Tracker

Reference for Apply, reached from `apply-agent/CLAUDE.md`. Paths are relative to `apply-agent/`. A change in this area updates this file in the same PR.

## The WorkIt client and `apply login` (KAN-541)

`src/apply/workit.py` is the only module in Apply that calls WorkIt. Do not
call WorkIt from another module; add a method to `WorkIt` that uses `call`.

- `uv run apply login` signs in through the student's own browser, with no
  port (KAN-723, W5 of `../docs/desktop_application_auto_apply.md`, D12).
  Apply makes a PKCE verifier (`workit.pkce`) and opens WorkIt's
  `/app-sign-in?challenge=...` page in the default browser. The student
  signs in there as on the website (password, Google or LinkedIn) and
  presses Sign In to the App, and the page shows a one-time code, which
  they paste into the terminal. `WorkIt.trade` sends the code and the
  verifier to `POST /apply-app/session`, which answers a new Supabase
  session of Apply's own (`backend/app/services/app_sign_in.py`). A code
  works once, for 5 minutes, and only with the verifier its challenge was
  made from; a refused one is `SignInOver`. Pasting is `apply login`'s
  way, since macOS hands the page's `workit-auto-apply://` link only to
  an app bundle that claims the scheme, and the page shows the code only
  to WorkIt's admins (`WORKIT_ADMINS`; `../docs/auth.md` says why). The
  link itself, pasted in place of the code, works too. The window
  (`apply app`) needs no paste (KAN-883): before the page opens, a
  checkout's window makes and registers a small helper applet in the data
  folder (`sign_in_link.py`, `WorkIt Auto Apply Sign-In.app`) that claims
  the scheme and writes the link to `sign-in-link`, readable by this user
  alone, and the window trades it (`apply-window.md`). The built app (W8)
  claims the scheme in its own `Info.plist` and makes no helper: macOS
  hands it the link as an Apple event, which it keeps in memory
  (`sign_in_link.listen`, KAN-833). The line with the page's
  link goes straight to the terminal, past the shell's mask
  (`apply.masked` hides the challenge, a long opaque value): a developer
  whose browser doesn't open needs it, and the challenge is no secret.
  This replaced a new Chrome with a debugging port that read the
  website's cookie (KAN-541): D11 forbids the port, and Chrome refuses one
  on the student's own profile.
- The session is Apply's alone, never the website's. Apply refreshes
  the access token itself at Supabase Auth
  (`/auth/v1/token?grant_type=refresh_token`, with the public anon key) and
  keeps the new refresh token: Supabase rotates it on each use. The
  extension must not do this (its CLAUDE.md, KAN-465), but Apply's session
  is not shared with a web app. A lock file (`workit-login.lock`) stops two
  processes from using one refresh token.
- The session's refresh token is in the system's keychain (`keyring`:
  Keychain on a Mac, Credential Manager on Windows), item `apply-workit`,
  its account the Supabase URL it belongs to, so a local stack's login is
  its own. The access token lives only in memory (`workit._ACCESS`),
  shared by every client in the process, so a new process refreshes once:
  Windows keeps at most 2,560 bytes an item, less than an access token can
  be. Tests start with it empty (`conftest.py`). **A keychain that won't
  answer** (a locked one, a Deny on macOS's prompt) is `NotLoggedIn` on a
  read and `LoginExpired` on a save, never a plain `WorkItError`, and
  `logged_in()` is False: the writes and the Answer bank sync keep what
  waits on those, and drop only what WorkIt refused. Never print, log or put either in a
  Record. To log out, delete the item in Keychain Access. The file Apply
  kept before 2026-11-15 (`workit-login.json`) goes at the next save.
  Tests give `WorkIt` a keychain (`fake.keychain`, `InMemoryKeychain`).
- The API checks the bearer token (`backend/app/deps.py`, `security.py`).
  `call(method, path, body)` sends one request as the student. On a 401 it
  refreshes one time and tries again. `applicant_id()` is the student's id
  for the paths, read from `GET /auth/me` one time per client. Code outside
  `WorkIt` uses only its public methods.
- `workit.Stage` names WorkIt's application stages, and
  `workit.APPLIED_STAGES` is applied or later. Use them; do not write a
  stage name as a string in another module (`tracker.STAGES`, the import,
  the cleanup).
- Errors: `NotLoggedIn` (no file), `LoginExpired` (Supabase or WorkIt
  refused the login: run `apply login` again), `Unreachable` (no answer, or
  a 5xx).
- `apply doctor` has a "WorkIt" line. With `ask_model: workit`, the
  default, the login is needed: no login, an expired login and a company
  account each fail, since a rehearsal then stops at its first written
  answer. The fix names `apply login` and the window's sign-in (`apply
  app`), which needs no code to paste. With another `ask_model` the login
  is optional, as Gmail is, and each of those is a warn. WorkIt that
  cannot be reached is always a warn: the login is still kept. Doctor, as
  a new process, refreshes the
  access token once and saves the rotated refresh token in the keychain.
  This is the only write that doctor makes.
- Each request sends the `User-Agent` `WorkIt-Apply/1`. Cloudflare, in
  front of WorkIt's API, refuses the Python-urllib user agent (error 1010).
- A request to the live API, and the session's refresh at the live
  Supabase Auth, trust only Cloudflare's certificate authorities, never the
  computer's store (`workit.PINNED`, D28, KAN-836): a proxy the computer
  trusts can't read the session or the Fill engine's download. Supabase is
  behind Cloudflare too. Pinning the API alone left the refresh token
  readable, and with it the download. A local stack is not pinned. The set and when to change it:
  `docs/fill-engine.md`, "The connection is pinned".
- `workit.LIVE` holds the live URLs and the anon key. They are the same
  public values as `autofiller_extension/src/shared/config.js`, and
  `test_workit_login.py` checks this. For a local WorkIt stack, set
  `APPLY_WORKIT_WEB`, `APPLY_WORKIT_API`, `APPLY_WORKIT_AUTH` (the Supabase
  URL) and `APPLY_WORKIT_ANON_KEY`.

**Tests.** `tests/fake_workit.py` is a fake WorkIt: one local HTTP server
that answers as Supabase Auth and WorkIt's API, and records each request
(`fake.requests`). Use `with FakeWorkIt() as fake:` and
`WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)`, and
`workit.login(client, fake.browser)` to sign in: `fake.browser` is the
student on `/app-sign-in`, giving a code bound to the page's challenge.
`fake.session()` makes a session (`fake.lifetime` seconds),
`fake.expire()` lets the access tokens expire, `fake.revoke()` signs out
every session, and `fake.stop()` makes WorkIt unreachable. Add a WorkIt
route with `fake.route(method, path, handler)`. `test_workit_login.py` needs
no browser and is in CI.

## `apply import-sheet`: the Tracker Sheet into the Applications Tracker (KAN-545)

`src/apply/sheet_import.py`. It runs one time, after `apply login`. ADR
0007 says why the Applications Tracker is the record.

- It reads the Applications tab of the Tracker Sheet (`sheet-id`) as text.
  It does not use `SheetTracker.rows()`, because that stops on an Outcome
  that is not in `Outcome`.
- Only rows with status submitted go in. Each other row is a skip, with
  its status.
- The stage comes from Outcome: interview to interviewing, offer to offer,
  rejected to rejected. Each other Outcome, and a blank one, is applied.
  An Outcome that is not in `Outcome`, and a missing or bad Date applied,
  go in at applied (or today) and are listed under "Check these".
- The resume is the file in the Application's folder under `sent/`
  (`worker.sent_folder`) whose name matches `attach.RESUME` and not
  `attach.COVER`. The folder of the day applied comes first. With no such
  file, the application goes in with no Sent resume.
- The dry run writes nothing. It reads `GET /auth/me`, `GET
  /applicants/{id}/applications`, and `POST /jobs/listed-by-link` for each
  row. Then the student types yes (`--dry-run` only lists).
- Each add is `WorkIt.record_applied`, the same method as a submit's
  write. In this order: `POST /jobs/added-by-link` (with `"track_only":
  true`, below), then `POST
  .../sent-resumes/file` (the resume, base64 JSON), then `PUT
  .../applications/{job_id}/stage` with `applied_on`, then `POST
  /jobs/{job_id}/applied` with `sent_resume_id`. It does nothing more to
  an application that is applied or later.
- It never changes an application that is applied or later in WorkIt. The
  dry run skips it, and the write skips it again if it became applied
  after the dry run. So a second run adds nothing, and a failed run can
  run again. Two rows of one job (`job_key`: WorkIt's link rule) are one
  add.
- A refused add is listed as FAILED and the others continue. WorkIt not
  answering stops the import.

**Tests.** `tests/test_sheet_import.py` runs the command on
`tests/fixtures/tracker-sheet.csv` (the real Sheet's columns, made-up rows)
against `tests/fake_tracker.py`: an Applications Tracker held in memory on
the fake WorkIt, with WorkIt's link rule, stages and Sent resumes.

## `apply clean-tracker`: delete the jobs the student did not apply to (KAN-546)

`src/apply/tracker_cleanup.py`. Run it after `apply import-sheet`.

- It reads `GET /auth/me`, `GET /applicants/{id}/applications` and the
  Applications tab of the Tracker Sheet. With no Sheet, it uses WorkIt
  only.
- It deletes only saved and queued applications. It keeps a saved or
  queued application when:
  - the student has an application at applied or later on the same job
    (`job_key`, so also on another posting of that job);
  - the Tracker Sheet has the same job as submitted (not imported yet). The
    dry run then says to run `apply import-sheet` first;
  - Apply's own Tracker (`APPLY_HOME/tracker.json`) has the job as held,
    missing fact or handoff. Apply writes these as needs_you, but the
    write can still wait in the queue. The dry run says "Apply is waiting
    for you on it (<status>)";
  - the student gave its link or job id with `--keep`.
- It never deletes or changes an application at applied, interviewing,
  offer or rejected, or at needs_you or skipped.
- The dry run writes nothing. Then the student types yes (`--dry-run`
  only lists).
- Each delete: `DELETE /jobs/{job_id}/saved` for saved, `DELETE
  /applicants/{id}/applications/{job_id}` for queued. Both routes delete
  only at that stage, in the same SQL statement, so an application that
  became applied after the dry run stays. WorkIt then refuses (409): the
  cleanup lists it as FAILED and continues. WorkIt not answering stops it.
- After the deletes, it reads the tracker again and prints the count of
  applied applications before and after. If one is gone, it lists it and
  exits 1.

**Tests.** `tests/test_tracker_cleanup.py`, against `tests/fake_tracker.py`
(with the two delete routes), with one application at each stage.

## Apply writes to the Applications Tracker (KAN-544)

Apply's Tracker is a file in the data folder: `tracker.FileTracker`
(`tracker.json`, one JSON file, a lock file around each read and write).
`cli.live_tracker()` wraps it in `tracker.WorkItTracker`: each `add` or
`update` that gives an Application a new status in `tracker.STAGES` also
sends a `workit.Write` through a `workit.WaitingWrites`.

- submitted to `applied`, with the resume from the Application's folder
  under `sent/` (`worker.sent_resume`: the profile's resume name, else a
  PDF named resume) kept as the Sent resume. This is
  `WorkIt.record_applied`, the import's write sequence. A job that is
  applied or later on WorkIt already stays as it is ("already
  interviewing").
  handoff, missing fact and held to `needs_you` (the stage PUT; a 409
  means the job is applied already, and is not an error). Apply never
  writes `queued`: on WorkIt that is the batch apply queue, and the
  extension fills a queued application. A `queued` write still in an
  older queue file is sent as `needs_you`.
  Every other status writes nothing.
- The job comes from `POST /jobs/added-by-link`, so a later status moves
  the same row. It is the extension's Write with Claude route (KAN-515);
  Apply sends `"track_only": true` (`WorkIt.add_by_link`), so WorkIt takes
  any link (not only a form auto apply fills), tracks a closed job as it
  is, and saves a new application or keeps its stage, where Write with
  Claude moves it to needs_you. A job WorkIt does not list becomes an
  **added job** (`added_by_student`; root `GLOSSARY.md`), never a status.
  The answer is `{"job_id", "stage"}`. New added jobs count against
  WorkIt's daily cap (50): a 429 (`workit.CapReached`) keeps the Write
  with `not_before`, the response's Retry-After or else the next UTC
  midnight (WorkIt's caps count UTC days). No flush sends it before then.
- A rehearsal writes only through `submitted_to`, when Lisul presses
  Submit himself. A rehearsal that he does not submit writes nothing.
  His confirmed Submit also saves the rehearsal's Record again as
  submitted, with the confirmation page as `after-submit.png`
  (`rehearsal._keep_confirmation`). Before, the Record kept saying held
  (KLA, 2026-11-03), though the Applications Tracker had it as applied.
- No answer, or no live login: the Write waits in `workit-queue.json` (one
  per Application, the newest). `apply run` and `apply rehearse` send the
  waiting writes first; `apply doctor`'s "WorkIt writes" line lists them
  ("waits for WorkIt's daily cap of added jobs until <time>" for a capped one).
  A Write that WorkIt refuses (a 4xx) is dropped and said.
- A write that fails never stops a run: the row is in Apply's Tracker.
- Apply does not write to the Tracker Sheet. The first `live_tracker()`
  with no `tracker.json` copies the Sheet's rows and Requests in, one time
  and read only (`sheet.copy_into`), so a run does not apply again to a
  job already applied to. `python -m apply.rankings` still writes its
  ranked tabs to the Sheet when you run it by hand.
- Lisul approves a Hold with the Apply window's Approve button (`POST
  /approve`, `Tracker.approve`), not a Sheet checkbox. `SheetTracker` has
  no `approve`: Apply never writes an approval to the Sheet (ADR 0007).
- A Hold's card shows one box per essay, with the essay's text only
  (`essays.cell_texts`). The `## <question>` heading and the Plan, Checks
  and Named lines of the Essay cell (`essays.as_cell`) are not in the box,
  so Lisul cannot change them. Approve sends his texts in order
  (`essays`). The window builds the cell again from the stored headings
  and lines and his texts (`essays.with_texts`), and `Tracker.approve`
  writes it with Approve, in one write. An empty essay is refused (400)
  with a message, and the Hold still waits. The next check fills the form
  with his words (`essays.from_cell`); a Plan line never goes to the form.
  The page keeps the edit in `sessionStorage` (`apply.essays`, by
  Application ID) until he approves, so a reload does not lose it.

**Tests.** `tests/test_tracker_record.py` (in CI) runs `WaitingWrites` and
`WorkItTracker` against `tests/fake_tracker.py`. `tests/test_rehearse.py
-k "applications_tracker or sends_nothing_to_workit"` rehearses a form
in Chromium: a submit by Lisul is Applied with the Sent resume, and no
submit sends nothing. `-k saves_the_record_again` checks his submit's Record.

## The Answer bank lives on WorkIt (W11)

`src/apply/answer_bank.py`, W11 of `../../docs/desktop_application_auto_apply.md`;
why it left the data folder is `adr/0006-the-answer-bank-lives-on-workit.md`.
The bank is no file in the data folder: it is the student's on WorkIt,
which the extension fills from too, so an answer given in one fills forms
in the other. KAN-746's opt-in sync (`answer_sync.py`, `apply sync-answers`,
`workit_sync`, `workit-answers-queue.json`) went with the YAML file.

- **Read once, into memory.** `GET /applicants/{id}/answer-bank`
  (`WorkIt.answer_bank`) gives the whole bank and its version (the ETag).
  WorkIt Auto Apply reads it at startup in the background
  (`load_in_background`): the window opens at once, the Answers tab says
  why while it waits, and Start waits for it, trying again at once on a
  press (`wake`). A Developer command reads it before it starts, and stops
  with the error when WorkIt doesn't answer (`cli._answer_bank`). The
  window and every Worker of a process share the one bank.
- **Each entry is a question and an answer**, `own` for the student's (or
  a draft they reviewed) and `none` for a multi-select's "none of these".
  No options, source, company, date, use count or facts.
- **Test Person's bank** (sample data) is memory only, with no WorkIt,
  and keeps no drafts (`AnswerBank(drafts=False)`).
- **The Answers tab edits only a bank that has come from WorkIt**: before,
  an edit answers 503 with why, since the bank landing after it would drop
  it. Its labels say what the model's drafts are: "Needs review" and
  "Drafted for you", beside "Written by you", and its Reviewed takes the
  flag off.
- **Masking.** No file holds the bank's answers, so the bank gives each one
  to `masked.KNOWN` as it reads or writes it; `apply trace` reads the bank
  first, and a report's Trace takes the window's (`Known.take`).
- **Every change goes to WorkIt through one sender thread**
  (`PATCH /applicants/{id}/answer-bank`, `WorkIt.change_answer_bank`), one
  PATCH for each change, in order, so a refusal drops that change alone.
  Memory changes only from WorkIt's reply: an entry its rule keeps out
  never fills a form. A reply whose version is not the bank's own plus
  one means another writer saved meanwhile, and the bank is read again.
  - The model's drafts never wait, since the form holds its draft. Each
    names its form by `job_id` when the run's link came from the
    student's Auto Apply queue (`Posting.job_id`, from the window's
    `queue()` through `Adapters.jobs`), else by `company`. Apply no longer
    decides itself that a draft is about the company: WorkIt's rule does.
    A bare date no section places is never sent.
  - The student's own changes (the Answers tab's Save, Add, Reviewed and
    Delete, and Ask Claude's saved offer) go ahead of the drafts, take the
    place of a waiting draft to the same question, and wait up to
    `EDIT_WAIT` (10 s) for the reply. What WorkIt kept out, refused or
    didn't answer is `NotSaved`, which the tab shows with the student's
    text kept.
  - The pre-submit review's fix sends a delete of the draft it found
    wrong (`drop_draft`), never of the student's own. A draft still on
    its way goes too: one waiting is taken out, and one being sent is
    deleted once WorkIt saves it. Regenerate sends a new flagged draft
    (`redraft`) and claims no save: WorkIt's rule may keep it out.
  - Reviewed sends the answer as a pick (`choice`), so WorkIt's rule reads
    its question alone, as when the answer entered: read as text, a pick
    such as "Google" names a company the student applied to, and could
    never be reviewed.
  - A change WorkIt doesn't answer (no reply, a 5xx) is sent again after
    1, 5 and 30 seconds, then dropped; a refusal (a 4xx) is dropped at
    once. The log names the question only, masked. At quit the sender has
    5 seconds (`close`: the app's `finally`, a command's `atexit`).
- **Before each Application the bank follows WorkIt's version**
  (`AnswerBank.follow`): the run's usage reading (`GET /apply-app/usage`,
  `UsageReading.bank_version`) carries it, and when it is not memory's
  the bank is read again, so an answer saved in the extension fills the
  next Application. A Developer checkout off the Model route has no such
  reading, so the bank asks the usage route itself. A read that fails
  keeps memory, and the next Application tries again. A read older than
  memory changes nothing: answered before a save reached WorkIt but
  landing after its reply, it would undo the save. While no run goes,
  a change made elsewhere waits for the next run.
- **A Developer checkout's `answer-bank.yaml` from before** (in the
  profile's folder) goes to WorkIt once, as a command starts
  (`cli._answer_bank`, `AnswerBank.upload`): a `lisul` answer not marked
  unreviewed as the student's own and the rest flagged, in PATCHes of
  100, each through WorkIt's rule, with no word. Only what WorkIt lacks
  goes: a question it doesn't hold, or the student's own answer where it
  holds a model's draft (theirs wins, as at any save). Once the bank is
  read again, the file becomes `answer-bank.before-workit.yaml`. A failed
  upload says so in one line, keeps the file, and the next command sends
  what WorkIt still lacks. WorkIt Auto Apply never
  uploads, and shows nothing for it: no student has the file.
  `sample/answer-bank.yaml` went with it.

**WorkIt Auto Apply's profile is WorkIt's too** (W11, 2026-11-24,
`student.profile_from_workit`). The app keeps no Applicant profile file
and never copies Test Person. Each Start reads `GET /apply-app/profile`
(`WorkIt.applicant_profile`): the student's Fill engine profile and
policies, built on the server exactly as the extension builds them, so
the app fills as the extension does. The policies lie over the app's own,
and an empty one never wipes Apply's (`high_stakes_job_systems: [ashby]`
stays). "How did you hear about us?" stays Apply's, "Company careers
page": WorkIt's answer, "WorkIt", is the extension's alone (decided
2026-11-26). The Story bank, voice, Stock answers and company briefs don't
come from WorkIt yet: the app starts an empty `story-bank.md`, which
every essay reads, so a first essay never stops on a missing file. The default resume and the transcript are read then too
(`WorkIt.profile_file`) and kept in `home.HOME / "files"`, by their names
alone, for a form's upload. A Start WorkIt doesn't answer says so and
changes nothing. What the student answers in Needs you goes back
(`student.to_workit`, `PATCH /apply-app/profile`): answers by question,
and the facts the Fill engine read from them, never a file's path. A send
WorkIt doesn't answer stays in the profile and goes with the next save. A
report's log is masked with the profile read from WorkIt as it goes. A
Developer checkout keeps its profile file and Test Person. Tests:
`tests/test_profile_from_workit.py`.

**Tests.** `tests/test_answer_bank.py` (in CI) runs the bank against
`tests/fake_bank.py`, a fake of WorkIt's bank that keeps entries out,
fails, refuses or holds a reply. The backend's `backend/tests/test_answer_bank.py` runs the
routes and WorkIt's rule on Postgres.

## Already applied: no form is opened again (KAN-621)

On 2026-11-04 a rehearsal filled Astranis, which Lisul had applied to. The
Applications Tracker had it at applied. The held page had a live Submit,
and he sent it a second time.

`src/apply/already_applied.py` checks each link before any page opens
(`Adapters.applied_before`; live: `already_applied.Check`). It reads
WorkIt one time per run or rehearsal, through `WorkIt.applications`.

- A link is already applied when one of these says so:
  - WorkIt has an application at applied or later on the same job
    (`job_key`, so another Greenhouse host matches too);
  - Apply's Tracker (`tracker.json`) has a submitted row with the same
    Application ID or job;
  - a Record of the same Application has `after-submit.png`.
- A rehearsal of such a link ends as "already applied". Its terminal line
  and its tile say "Already applied on <date> (<source>)". No browser
  opens. A run makes it a Handoff and opens no form.
- `apply rehearse --force` fills it anyway. The held page keeps the submit
  guard on, under a red "You already applied on <date>, don't submit"
  note. Lisul presses Dismiss, then "Yes, I'm sure: unblock this page".
  Only then does `lift` take the guard off. The second button has no word
  that the guard blocks.
- WorkIt that cannot be read (no login, an expired login, no answer) is
  never a silent pass. The window's status line and the terminal say why
  (`already_applied.UNCHECKED`). The local checks still run.
- The check only reads WorkIt: it writes nothing there.

**Tests.** `tests/test_already_applied.py` (in CI) runs the check against
`tests/fake_tracker.py`. `tests/test_rehearse.py -k "already_applied or
could_not_run or force_rehearses"` rehearses in Chromium.

## The resume check (KAN-663)

`src/apply/resume_check.py` compares `files.resume_pdf` with policies.yaml's
`resume_source` (`repo`, `path`, `branch`, default `main`) by git blob sha.
The default is unset, and then nothing runs and doctor prints no line. A
different file stops `apply rehearse`, `apply run` and `approve-pass` at
their start, with one line that names both shas. In doctor, it is a fail. If
`gh` can't answer, it is a warning and the run goes on. The repo's sha is
kept for 10 minutes in `resume-source.json` in the data folder. A link sent
with `--into` joins a run that was checked at its start.

## The tailored resume is the Sent resume (KAN-547)

A student can tailor a resume to a job posting on WorkIt (Tailor,
`../docs/tailor_resume.md`). When the Posting has a tailored resume, Apply
gives the form that resume, and the Applications Tracker keeps that same
file as the Sent resume. Apply does not change how Tailor works.

- `tailored.resume_for` runs before each Application, in a run
  (`orchestrator._traced`) and in a rehearsal (`rehearsal._rehearse`). It
  asks `Adapters.tailored` (live: `tailored.from_workit`) for the PDF.
- `WorkIt.tailored_resume(url)` finds the job with `POST
  /jobs/listed-by-link`, the student's tailored resume for that job in `GET
  .../built-resumes` (`job_posting_id`), and renders it with `GET
  .../built-resumes/{id}/render`. It writes nothing.
- Apply writes the PDF to `APPLY_HOME/tailored/<application>/` with the
  file name of the profile's resume. The form gets it under that name, the
  Worker copies it to `sent/`, and the submit's write sends that copy
  (`worker.sent_resume`). Thus the file attached and the Sent resume are the
  same bytes.
- The Application gets a view of the profile (`tailored._WithResume`): only
  `files.resume_pdf` changes. The not-on-resume gate and the essays read the
  tailored resume too. Every write goes to the profile itself, and the
  profile file never changes.
- No WorkIt login, a job that WorkIt does not list, no tailored resume, or
  a profile with no resume: the profile's resume, as before. WorkIt down or
  a failed render: the profile's resume, and one line on stderr says so.

**Tests.** `tests/test_tailored_resume.py` (in CI) runs against
`tests/fake_tracker.py` (`FakeTracker.tailored`). `tests/test_run.py -k
tailored_resume` (the form gets the tailored file) and
`tests/test_rehearse.py -k tailored_resume` (Lisul's submit keeps it as the
Sent resume) open Chromium. The backend test
`backend/tests/test_sent_resumes.py -k tailored_resume_by_the_postings_link`
runs the same routes on Postgres.

## Send report (D26, KAN-837)

The window's support form, "Report a problem": from Settings, or from an
Application's card or row on the student page, which picks that Application. The student chooses what
it is about (`report.CATEGORIES`), writes what happened, says whether WorkIt
may email them, and, with an Application picked, whether to include its
record and log. Nothing is sent without their press. The form is W5's
(`app_window.Bridge.review_report`, then `send_report`); it calls three
functions in `apply/report.py`:

- `build(category, note, profile, row=None, include=True, contact_ok=False)`
  makes the report. With `row` and `include`, it reads the Record's own
  files from its folder (answers, essays, verification, the questions asked
  of Claude, the page's HTML and the form's screenshots) and the
  Application's Trace, masked here first (`masked.Known`, from the Applicant
  profile and the Answer bank beside it, and every email, phone and id in a
  link); a long Trace keeps its first line and its last `TRACE_MAX`
  characters. A general question (`row` None) is the student's words alone.
  `profile` is the Applicant profile's file (`home.HOME /
  "applicant-profile.yaml"`), never its folder: the mask reads a file it
  can't as no values, and a folder passed in its place sent the name in
  the log, so `build` raises ValueError when a log goes and `profile` is
  not a file.
- `parts(report)` lists what it holds, a line each with its size, for the
  form to show before Send.
- `send(report)` posts that same report through `WorkIt.send_report` to
  `POST /apply-app/reports` and answers its id.

WorkIt keeps a report until the team fixes its problem, then deletes it
(`backend/app/routers/apply_reports.py`), as `/privacy` says. A pushed
Record's link is a web page, so a Developer checkout's report holds no
files, only the Trace.

**Tests.** `tests/test_report.py` (in CI) and
`backend/tests/test_apply_reports.py`.
