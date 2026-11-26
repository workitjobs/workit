# Apply

Apply fills job applications in its own Chrome windows and writes the
answers with Claude. A rehearsal fills the form and stops. **A rehearsal
never submits.** Apply runs on macOS only. Before you change code here, read
`CLAUDE.md`.

## You need

- A Mac with Google Chrome in `/Applications`.
- [uv](https://docs.astral.sh/uv/) (`brew install uv`).
- A WorkIt student account, signed in from Apply (step 4). Apply's
  answers and essays go to WorkIt's Model route on `api.workitjobs.ai`
  (`ask_model: workit`, the default since 2026-11-14), which builds the
  prompts and runs the models as you. So a rehearsal needs the sign-in:
  without it, the run stops at its first written answer. To try changes to
  your own API instead, run it (`../backend/CLAUDE.md`, Commands) and set
  `APPLY_WORKIT_API=http://localhost:8000`. That API reads its model keys
  from the team's `.env` in the checkout's root (Scout's Groq and Gemini
  keys); `npm run worktree` copies it into a new worktree.
- Claude Code, logged in with your own Claude plan: `claude auth login`.
  Claude fill, Rescue and company briefs use your plan's usage, and so do
  the answers and essays if you set `ask_model: claude` in `policies.yaml`.
- Read access to the private `workitjobs/fill-engine` repo (the Fill
  engine is a git submodule). git must sign in to GitHub without a prompt:
  run `gh auth login` and then `gh auth setup-git` once.

## Set up

Run every `uv run apply` command from `apply-agent/`. In another folder,
your shell runs macOS's own `apply`, an unrelated command that prints only
`usage: apply [-a magic] ...`.

1. Clone with the submodule:

   ```sh
   git clone --recurse-submodules https://github.com/workitjobs/workit.git
   ```

   If you cloned without it, run `git submodule update --init` in the
   checkout.

2. Install Apply. The last line is only for the tests:

   ```sh
   cd workit/apply-agent
   uv sync
   uv run playwright install chromium
   ```

3. Check the setup: `uv run apply doctor`. Each line says ok, warn or fail,
   with a fix. On a new Mac, four lines fail: "WorkIt" (step 4 fixes it),
   "Applicant profile" (step 5 fixes it), "Worker profiles" (step 7 fixes
   it; after step 5 doctor lists each Worker profile, `worker-1` and on)
   and "Plain seed" (`uv run apply plain seed` fixes it: the default
   `worker_mode: protected` fills Lever, SmartRecruiters and Workable in
   plain Workers). With `worker_mode: plain` in `policies.yaml`, doctor
   checks only "Plain seed"; with `cdp`, only "Worker profiles". "Ask
   model" fails only with `ask_model: groq` or `gemini` and no key for
   them (step 8). Fix every other fail first. The warn lines are for
   optional features and optional facts (`identity.phone_type`).

4. Sign in to WorkIt. Every answer and essay goes to WorkIt's Model route
   as you, so a rehearsal needs it:

   ```sh
   uv run apply login
   ```

   Apply opens WorkIt's sign-in page in your browser. Sign in there, press
   Sign In to the App, and paste the code it shows into the terminal. The
   page shows the code only to WorkIt's admins: ask the team to add your
   email to the API's `WORKIT_ADMINS`. Without that, sign in through
   WorkIt Auto Apply's window instead, which needs no code to paste:

   ```sh
   uv run apply app
   ```

   The window also takes you through first run (Chrome, what leaves your
   Mac, Screen Recording, the seed), then runs your Auto Apply queue (W5).
   Apply keeps the login in your keychain (`apply-workit`), never in the
   repo. You sign in one time; Apply refreshes the login by itself.
   `uv run apply doctor` then says "WorkIt: logged in as" your email. If it
   says that the login expired, sign in again.

   The login also lets Apply write your applications to your Applications
   Tracker on WorkIt: a submit as Applied (with the resume sent), a
   Handoff, a missing fact or a held application as Needs you.

## First rehearsal: Test Person

5. Rehearse one Greenhouse job posting:

   ```sh
   uv run apply rehearse https://job-boards.greenhouse.io/formlabsinternships/jobs/8223362
   ```

   Your data folder (`APPLY_HOME`, default `~/.config/apply/`) is empty, so
   Apply copies the Test Person sample data (`sample/`) into it. The window
   says "Sample data". Apply fills the form as Test Person and stops. The
   result is "Filled, not sent". The first time takes about ten minutes,
   because Claude researches each company before it writes. The record (the
   answers and a screenshot) is in `~/.config/apply/rehearsals/<date>/`.
   Chrome stays open on the filled form; press Ctrl-C to stop Apply.

   Greenhouse and Lever postings work with the sample data. **Workday
   does not.** Workday refuses the sample's `example.com` email and 555 phone
   number. A Workday rehearsal also makes an employer account, and Workday
   sends mail to that address. Rehearse Workday only with your own data
   (step 6).

## Your own data

6. Replace the Test Person files in `~/.config/apply/` with your own:
   `applicant-profile.yaml` (copy `applicant-profile.template.yaml` from
   this folder and fill it in),
   `answer-bank.yaml`, `story-bank.md`, `voice.md`, your resume PDF and
   `company-briefs/`. A relative path under `files:` in the profile is read
   from the data folder. If you edit the sample profile instead, delete its
   `sample_data: true` line, or the window keeps saying "Sample data". Never
   put these files in the repo.

   To keep test data apart from real data, set `APPLY_HOME` to another
   folder. Set `APPLY_PROFILES` too, or the Chrome profiles go under
   `APPLY_HOME/profiles`.

7. Sign in to Google in Worker profile 1, by hand. Use the account you
   apply with. Quit Chrome (Cmd-Q) when you are done:

   ```sh
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --user-data-dir="$HOME/.config/apply/profiles/worker-1" \
     --use-mock-keychain --password-store=basic
   ```

   With `APPLY_HOME` or `APPLY_PROFILES` set, use the folder that `uv run
   apply doctor` prints. A run copies this profile to the other Workers.

8. Optional Keychain items. Save each one from `apply-agent/` with
   `uv run keyring set <service> <account>`, which asks for the value:
   - `apply-gmail`: a Gmail app password, so Apply can read Workday and
     Greenhouse verification codes (also the code a job site emails after
     you press Submit on a rehearsal's page: Apply types it in, and Submit
     stays yours to press)
     ([docs/accounts-setup.md](docs/accounts-setup.md)).
   - `apply-ntfy`: an ntfy topic for phone notifications
     (`./scripts/setup-wizard.sh` sets it up).
   - `apply-groq` (account `api.groq.com`) and `apply-gemini` (account
     `generativelanguage.googleapis.com`): your own Groq and Gemini API
     keys, only for `ask_model: groq` or `gemini`, which can't run a call
     whose prompt moved to WorkIt; used before the `.env`'s
     ([docs/ask-model.md](docs/ask-model.md)). Doctor's "Ask model" line
     checks them.

9. Optional: if you used a Tracker Sheet before, put its submitted applications into
   your Applications Tracker one time. Apply first lists each add and skip,
   and writes only when you type yes:

   ```sh
   uv run apply import-sheet
   ```

   Then you can delete the saved and queued applications of jobs that you
   did not apply to. Apply first lists each delete and keep, and deletes
   only when you type yes. It never deletes an application at applied or
   later. Use `--keep <link>` for a job that you still follow:

   ```sh
   uv run apply clean-tracker
   ```

10. Optional: let the WorkIt extension in your own Chrome sign you in to the
    Workday accounts that Apply made, so Chrome saves each password in its
    password manager (KAN-592). The extension must be loaded in that Chrome.

    ```sh
    uv run apply chrome-passwords
    ```

    It installs the Apply accounts host for Chrome, and lists each account
    that Keychain has (service `apply-ats`) in the Tracker. Then open the
    extension's options page and turn on Use My Apply Accounts. On a Workday
    Sign In page of such a tenant, press Sign In with Your Apply Account in
    the WorkIt panel, then Save when Chrome asks. `uv run apply doctor` then
    says "Apply accounts host: installed". Run the command again after you
    move the checkout: the host runs this checkout's Python.

Run `uv run apply doctor` again. Then rehearse a Workday posting.

## The demo

```sh
uv run apply rehearse --start-button --workers 3 <url> <url> <url>
```

Apply opens each form and plans its answers, then waits. Press Start in the
Apply window, and the Workers fill all the forms at once, each in its own
Chrome. Nothing is sent.

## Tests

CI runs ruff and only the fast test files (no browser, network or `claude`
CLI). The Filler tests need Chromium, so run the ones that your change
touches on your Mac, with `-k`: `uv run pytest tests/test_workday_filler.py
-k <name>`. Never run the full suite for a small change (over 20 minutes).

## More setup

- [docs/accounts-setup.md](docs/accounts-setup.md): Gmail, Keychain, Google
  sign-in.
- [docs/records-setup.md](docs/records-setup.md): Records repo and
  notifications.
- [docs/tracker-setup.md](docs/tracker-setup.md): Apply's Tracker (a file
  in the data folder) and what Apply writes to your Applications Tracker.
- `./scripts/setup-wizard.sh` walks through all of them.
