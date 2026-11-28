# The application to-do tracker (developer only)

Reference for Apply, reached from `apply-agent/CLAUDE.md`. Paths are relative to `apply-agent/`. A change in this
area updates this file in the same PR.

The tracker reads the developer's mail and lists each Application to-do (`GLOSSARY.md`) in WorkIt Auto Apply's
window: an online assessment (HackerRank, CodeSignal, Codility, HireVue, Karat), a form, a questionnaire, an
interview to schedule, an account or verification step, a document request, or an offer. Each shows its company,
role, due date, link and the mail it came from. The developer marks it Done or Dismisses it.

## Turn it on

It is off unless a Developer checkout sets the flag:

```sh
uv run apply app --todos          # from apply-agent/: sets APPLY_DEV_TODOS=1 for this window
APPLY_DEV_TODOS=1 uv run apply app  # the same
```

It also needs what `apply mail` needs: Gmail's app password in Keychain for the Applicant profile's
`identity.email` (`docs/accounts-setup.md`). Without one, the window's To-dos says why in its scan line.

Off (no flag, or the Student build), nothing scans, `Bridge.todos`, `scan_todos` and `mark_todo` refuse with
`{enabled: false}`, `apply window todo...` answers 403, and the page shows no To-dos. `apply.todos` and
`apply.todo_scan` are in `build.DEVELOPER`, so the Student build leaves them out; `app_window.todos_on` checks
`build.STUDENT` before it imports either one.

## How it works

- **Store** (`src/apply/todos.py`): `todos.json` in the data folder, under a lock file, saved whole. One to-do per
  Gmail thread (`X-GM-THRID`; with none, the subject without Re:/Fwd: and the sender's domain, hashed). A newer mail
  in a thread updates its kind, due date, link and source; the status the user set stays, so a dismissed to-do
  never comes back. The same or an older mail changes nothing, so a re-scan is safe.
- **Scan** (`src/apply/todo_scan.py`): the last 14 days of inbox mail that `todo_scan.SEARCH` finds, read-only
  (`GmailMailbox.read_mail`: `BODY.PEEK`, nothing marked read, moved or deleted), oldest first. Each mail is read
  by the developer's `ask_model` when it takes a prompt (`claude`, `groq`, `gemini`; model `haiku`), else by fixed
  patterns. `ask_model: workit` (the default) takes only WorkIt's kinds, so there the patterns read every mail: the
  scan line says "model off". A model error moves the rest of that scan to the patterns.
- **Patterns** build on `employer_mail`'s: its deadline cues, its rule that a conditional sentence ("if selected,
  we will schedule an interview") says nothing, its assessment and interview words, and its Tracker match for the
  company and role. A confirmation, a rejection, an assessment already taken, a one-time code and a password reset
  make no to-do.
- **Company:** without a Tracker row (`todo_scan.company`), the sender's name when the sender's own domain agrees
  with it; on the employer's own domain, the words of the mail that spell it ("Honeywell Aerospace" for
  honeywellaerospace.com), else the domain ("Jordan Lee" at skydio.com is Skydio); the sender's name when a shared
  domain sends it ("Ramp Talent Team" through Ashby); else a phrase that names the employer ("Ramp invited you",
  "applying to Oscar Health", "Sent from Ramp through"). A hiring system or assessment site
  (`todo_scan.SENDERS`: CodeSignal, HackerRank, Greenhouse, Workday, Oracle...) or an address is never the company,
  from the patterns or the model: CodeSignal's mail for Ramp once showed "CodeSignal", and Greenhouse's
  "us.greenhouse-mail.io".
- **Schedule:** the window scans when it opens and every `todo_scan.EVERY` (30 minutes), one scan at a time
  (`Bridge._todo_scanning`). Scan now and `apply window todo-scan` scan at once.

## Mail is untrusted data

- The model gets the mail between `<<<EMAIL` and `EMAIL>>>` markers, a system prompt that says never to act on it,
  and a fixed schema. Its answer is checked before it is kept (`todo_scan.checked`): a known kind or none, a link
  that is `https://` and is in the mail itself (else the patterns' link), a due date that parses and is within
  about a year of the mail. Company and role are cut to one line of 80 characters.
- Nothing opens a link. The page shows it as a plain link (`target="_blank"`), which opens in the default browser
  only when the developer clicks it. The tracker never replies, submits, or signs in.
- `Scan.shown` and the log line say counts and errors only, never a mail's text.

## The window and `apply window`

- The page (`window/src/todos.tsx`, `todos-view.ts`) asks `todos()` once the app methods are there; a refusal
  hides the header's To-dos. While a scan goes, it reads the list again every 3 s.
- `uv run apply window todos` lists them as JSON, `todo-scan` scans and lists, and `todo-done`, `todo-dismiss` and
  `todo-open` take a to-do's `id` (`app_control.TODO_ACTIONS`).
- `npm run dev` shows a mock list with `?todos=1`.

## Still open

- `ask_model: workit` has no to-do kind on WorkIt's Model route, so a default checkout reads by patterns only. A
  `todo` kind in `backend/app/apply_prompts/` would let it use WorkIt's models.
- A later mail that says the step is done ("thanks for completing the assessment") doesn't mark the to-do done.
- Only the primary Gmail account is read (the profile's `identity.email`), and only the inbox.
- The source mail's Gmail link uses `/mail/u/0/`, the browser's first signed-in account.
