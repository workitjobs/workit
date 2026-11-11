# CLAUDE.md — GitHub Actions

Loaded on top of the root `../CLAUDE.md` when working in `.github/`. The jobs
themselves are in `workflows/*.yml`; this file holds why they are shaped that
way and what bites.

## CI (`workflows/ci.yml`)

`scout/` has no job of its own: the backend installs it, so the backend job
lints and tests it too. The `api-worker` job type-checks the API's Cloudflare
Worker (`backend/cloudflare/`, `npm run check`), which nothing else builds
before the deploy on `main`.

The backend job runs `pgvector/pgvector:pg15` as a service on port 54330,
the same image and port as the local test container, and sets
`TEST_DATABASE_URL` to it. The tests migrate their own database to head on it
(`backend/CLAUDE.md`, "Tests against real Postgres"). Because `CI` is set
there, a test database that cannot be reached fails the job instead of
skipping the tests.

**The backend job runs only on a PR that touches `backend/`, `scout/`,
`scraper/`, the fill-engine submodule's pin or `ci.yml`** (the `changes` job's `backend` filter). The API
installs both packages (`workit-scout` and `workit-scraper`, path
dependencies in `backend/pyproject.toml`), and its tests read no other
folder: the root `.env` is absent in CI, and the Fill engine test skips
without the submodule. A new path dependency joins the filter too.
**The backend job checks out the fill-engine submodule when
`FILL_ENGINE_TOKEN` is set** (KAN-756), pinned as the other engine jobs
pin it, and sets up Node 22: the Rules table's tests read the engine's
`dist/rules-table.json` and run its round trip on the built engine
(`backend/tests/test_rules_watermark.py`). Without the token those tests
skip and the rest of the job runs. Only 3 of the 40 PRs merged before
2026-11-04 touched either folder; the rest waited about 7 minutes for a
job their change could not fail. A skipped job passes a required check. A
new backend test that reads a file outside those folders adds that folder
to the filter, or a PR that changes the file merges untested.

The backend job runs pytest with one worker per core (`-n auto`,
pytest-xdist). One at a time, its 2,368 tests took 6.5 of the job's 7.3
minutes (2026-11-04): about 40% resume tests that each compile a real PDF
(about 1 s), the rest database tests that each empty every table after
them. Each worker imports `tests/conftest.py` on its own, so each makes and
migrates its own randomly named database and the workers share no table.

The backend job installs real Tectonic with `backend/scripts/fetch_tectonic.py`
(kept in the Actions cache) before pytest. Because `CI` is set, the resume
template text test fails, never skips, when Tectonic is missing
(`backend/app/services/resume_render/CLAUDE.md`).

The `extension-store-build` job (KAN-463) builds the Chrome Web Store package
(`autofiller_extension/store/build.mjs`), which fails if a packaged file names
localhost, vercel.app or "Prototype", and runs `store-build.spec.ts` and
`extension-id.spec.ts`. The package needs the private fill-engine submodule,
which the default token can't read, so the build steps run only once a
`FILL_ENGINE_TOKEN` secret (read access to workitjobs/fill-engine) is set;
without it they show as skipped and the job checks the extension ID only.
The build first runs `npm ci` in `store/` for esbuild, which minifies every
packaged script (KAN-744).

**Without `FILL_ENGINE_TOKEN`, the engine's tests are skipped, never green.**
`ci.yml`, `extension-nightly.yml`, `apply-nightly.yml` and `live-canary.yml` each first call
`workflows/engine-token.yml` (a reusable workflow, job `engine`), which
answers whether the secret is set and, when it isn't, writes "SKIPPED: ..."
to its job summary and a warning. A job that needs the engine depends on it
(`needs.engine.outputs.set == 'true'`), so it shows as skipped instead of a
run of tests that did nothing. Those jobs share their setup after the
checkout (Node, `autofiller_extension/test`'s `npm ci`, Playwright's
Chromium) in the composite action `actions/extension-setup`; the checkout
stays in each job, since a local action can't check out its own repo.

The `extension` job (KAN-464) runs the smoke specs listed in
`autofiller_extension/test/ci-smoke.txt` headless (both projects) on the
engine the submodule pins, and first fails if that engine commit's committed `dist/` differs from
what its `src/` builds. It runs only on a PR touching `autofiller_extension/`
(the engine pointer included) or `ci.yml`: the `changes` job
(`dorny/paths-filter`) decides, and a skipped job counts as passed. The whole
suite is about 40 minutes on the runner's one worker, so PRs get the smoke
set (an 8-minute limit, KAN-736) and `workflows/extension-nightly.yml` runs
every spec, the `speed.extension.spec.ts` timing harness too, every night at
07:41 UTC (and by hand: `gh workflow run extension-nightly.yml`). Both need
`FILL_ENGINE_TOKEN`, as `extension-store-build` does, and are skipped
without it. Both run on `macos-latest` (free on a public repo): on Linux, Chromium
asks `accounts.google.com` on its own (which `practice.extension.spec.ts`'s
request list catches) and a field a panel row scrolls to doesn't come into
view (`panel-reopen`, `workday-show`), found in the Playwright image
2026-10-31. On CI each spec gets two retries; a broken one fails all three.

**`timeout-minutes` on this job was never validated against a real run
until 2026-11-03** (KAN-447): every PR before that one shows the job as
skipped (no `FILL_ENGINE_TOKEN` yet), so the original 30-minute figure
was a guess, never measured. The first real run reached 329 of 388 tests
at the 30-minute mark and was cancelled; raised to 45, which is what
showed the full suite needs about 40 minutes on one worker — the measurement
KAN-736 then acted on by moving PRs to the smoke set above, at an 8-minute
limit. Raise that 8 if the smoke set itself ever gets close, rather than
guessing a second time.

**`actions/checkout@v4`'s own submodule handling can silently land `fill-engine`
on the wrong commit, and `fetch-depth: 0` alone does not fix it** (found
2026-11-08, revised 2026-11-09): without `fetch-depth: 0`, the submodule
fetch is shallow too, and when the pinned commit isn't on the default
branch's shallow history (true as soon as `main` moves past it, which it
usually has) it silently checks out the submodule's current branch tip
instead — no error, no warning. A run pinning `fill-engine@0.3.26` built
and tested `0.3.30` instead. Adding `fetch-depth: 0` to the checkout
**did not stop this from recurring** on a later run, for a reason not yet
root-caused (a plain local `git clone` + `git submodule update --init`
reaches the pinned commit fine, so it isn't simply "the commit is
unreachable" — something in `actions/checkout`'s own submodule step
behaves differently). Rather than keep chasing that action's internals,
every job now forces it explicitly right after the checkout: read the
gitlink `git ls-tree HEAD` actually records, then `git -C
autofiller_extension/fill-engine fetch --depth 1 origin <that SHA> &&
checkout --detach <that SHA>`. This is the "Pin fill-engine to the commit
this branch actually records" step in `ci.yml` (`extension-store-build`,
`extension`, `apply`), `extension-nightly.yml`, `apply-nightly.yml`,
`live-canary.yml` and `publish-extension.yml` — seven places, one pattern. If `actions/checkout`
ever fixes this upstream, these steps are redundant but harmless; don't
remove them without confirming a real run's build log prints the version
`git ls-tree HEAD` actually names, not just that the step exists.
A plain local `git submodule update --init` was never affected (no
`--depth` flag, so it always resolves the real pinned commit) — this was
CI-only, and the most serious place it bit was `publish-extension.yml`,
which could have shipped students an unreviewed engine build with no
record of having done so.

**The pin step's paths are repo-root-relative; a job's `defaults.run.working-directory`
breaks it silently** (found 2026-11-09, fixed 2026-11-10): `extension-store-build`,
`extension` (both files) and `apply` each set a job-wide working directory
(`autofiller_extension`, `autofiller_extension/test`, `apply-agent`), and the
pin step's `git ls-tree HEAD autofiller_extension/fill-engine` and `git -C
autofiller_extension/fill-engine ...` resolve those paths against *that*
directory, not the repo root — so in `autofiller_extension/test` it looked
for `autofiller_extension/test/autofiller_extension/fill-engine`, found
nothing, and failed every run with "fatal: cannot change to
'autofiller_extension/fill-engine': No such file or directory" right after a
successful submodule checkout. Fixed by adding `working-directory: .` on the
pin step itself in every job that sets a non-root default (five of the six:
all but `publish-extension.yml`, which sets no job-wide default and was
never affected). A step's own `working-directory:` is always resolved from
`$GITHUB_WORKSPACE`, never nested inside the job's default, so this is safe
to copy into a sixth place if one is ever added.

The fill-engine repo has its own CI (its `.github/workflows/ci.yml`):
typecheck, the same stale-`dist/` check, and its tests, on every PR.

The `apply` job (KAN-535) lints and tests Apply (`apply-agent/`) on
macOS: `uv sync --locked`, `uv run ruff check .` and a fixed list of test
files. The list holds only the 44 files that need no browser, no network
and no `claude` CLI: about 770 tests (28 skipped), 10 s of pytest and 14 s
with `uv sync --locked` and ruff, timed in a Linux container
(`ghcr.io/astral-sh/uv:python3.12-bookworm`) on 2026-11-02. The tests read
the engine's saved forms, so the job needs the fill-engine submodule: it
needs `FILL_ENGINE_TOKEN` and is skipped without it. It runs only on a PR
that touches `apply-agent/`, the engine pointer, `ci.yml` or
`engine-token.yml` (the `changes` job). It then installs Chrome for Testing
(cached by `uv.lock`) and runs `test_submit_guard_hostile.py`,
`test_plain_focus.py`, `test_plain_guards.py` and
`test_plain_routing.py`, the last two on a real plain Worker (KAN-667). macOS, because a
plain Worker starts through `open` and the browser's `.app`; a step fails the
job if the browser is missing, since these tests skip without it.
**Its limit is 20 minutes** (KAN-780, 2026-11-10; raised from 15 on
2026-11-11): the job took 16 to 20 minutes once the hostile pages'
plain-Worker cases ran there (it was raised to 35 for that), about 6 after
KAN-780 (below), and about 13 once the guard holes' pages ran on every CDP
path (KAN-710, KAN-783). Each step has its own
limit too, so a hang fails in that step.
**CI does not run the other 28 test files**, which hold the Filler tests
(`test_*_filler.py`, `test_claude_fill.py`, `test_run.py`,
`test_rehearse.py` and more). Most of them need Chromium or the macOS
`security` tool. The full suite takes more than 20
minutes. Run the files that a change touches on a Mac, with `-k`
(`apply-agent/CLAUDE.md`, Testing).

Each test step has its own `timeout-minutes` and skips tests marked
`nightly` (KAN-780). The fast tests and the hostile pages run in parallel
(`pytest -n auto`, pytest-xdist), but plain-Worker cases always run one at
a time in one process (the hostile pages' `xdist_group`, `--dist
loadgroup`, and the plain-Worker step without `-n`): in parallel, plain
Workers' trusted typing missed its field. The tile's tests, which time
frames in real seconds, have their own one-process step too. Before KAN-780 the job took 16 to 20 minutes,
10 to 15 of them in the hostile pages' matrix. PRs now run every hostile
page and every path at least once; `workflows/apply-nightly.yml` (07:53
UTC, or `gh workflow run apply-nightly.yml`) runs every `nightly` test.
The pages of PR 477's guard holes (KAN-710: `GUARD_HOLES` in
`test_submit_guard_hostile.py`, among them a page that sets the guards' old
`window.__apply*` flags itself) are never only nightly: PRs run each one on
every CDP path. The holes that hang on how a plain Worker carries the guards'
state, touches, controls and network rules (`PLAIN_HOLES`) also run on one
plain-Worker path; the rest of their plain-Worker pairs run nightly, since the
guard script is the same on both kinds of Worker. A page added for a new
guard hole joins `GUARD_HOLES`, and `PLAIN_HOLES` too when it is about a plain
Worker. With all 38 on a plain Worker the hostile step took 551 s on CI
(2026-11-11) and hit its 9-minute limit, so only `PLAIN_HOLES` run there on
PRs. Even then the step took 505 s for 350 cases, and 547 s for 398 once
KAN-783's eight pages joined (about five times its time on a 14-core Mac),
so its limit is 12 minutes. A
test safe only on its own (a fixed port or path) can't join a parallel step.

The frontend job runs `format:check`, so an unformatted file fails the PR.
Run `npm run format` before pushing. Markdown docs are in
`frontend/.prettierignore`, so Prettier never rewrites prose.

## Deploy to Cloudflare (`workflows/deploy.yml`, KAN-169)

Every push to `main` deploys both halves to Cloudflare Workers Paid
(`../docs/adr/0004-host-on-cloudflare.md`): the API job builds
`backend/Dockerfile` into a Container behind the Worker in
`backend/cloudflare/` (`api.workitjobs.ai`), and the web job builds the app
with OpenNext and deploys it (`workitjobs.ai`). A branch never deploys on
push, because each deploy overwrites production. To try one before merge, run
it by hand: `gh workflow run deploy.yml --ref <branch>`. Every run shares one
concurrency group (`deploy-cloudflare`), whatever its ref: a group per ref let
a branch run and a push to `main` deploy at once, so the app could end up on
one's code and the API on the other's.

- **The API job checks out the fill-engine submodule** with
  `FILL_ENGINE_TOKEN`, pinned to the commit `main` records, because the image
  copies the engine's Rules table from it (`backend/Dockerfile`, KAN-756). A
  missing table fails the image build, never a deploy without it.
- **Secrets:** `CLOUDFLARE_API_TOKEN` (account token from the "Edit Cloudflare
  Workers" template, scoped to the WorkIt account and the `workitjobs.ai`
  zone) and `CLOUDFLARE_ACCOUNT_ID`, which wrangler reads from the env.
- **The API's runtime values are one secret, `CF_API_SECRETS_JSON`**: a JSON
  object of every variable the API reads in production (first copied from
  Vercel's production env, before Vercel was retired). The job pipes it to
  `wrangler secret bulk` **before** the deploy: the image rollout restarts the containers with the secrets of that
  moment, and a secrets-only version restarts none, so set after, the new
  values reach no container until each sleeps (found 2026-10-21). `secret
  bulk` never deletes a secret, so a key dropped from the JSON keeps its old
  value. **Build it from the root `.env`, never `vercel env pull`**: Vercel
  returns every sensitive variable as the text `[SENSITIVE]`, which once
  shipped as the database URL and keys. To change one value, rewrite the whole JSON
  (`gh secret set CF_API_SECRETS_JSON < file.json`); never put a value in the
  workflow. `DIRECT_URL` never goes in it: migrations stay a local step.
- **`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
  `NEXT_PUBLIC_BRANDFETCH_CLIENT_ID` (KAN-442) and
  `NEXT_PUBLIC_TURNSTILE_SITE_KEY` are repo variables, not secrets**: Next
  inlines them at build time and all are public by design. Setting them as
  Worker secrets would do nothing. Without the Brandfetch one, every company
  logo falls back to what the scraper found. The Turnstile site key and the
  API's `TURNSTILE_SECRET_KEY` go in together: the secret alone makes every
  signup answer 400, since the form then sends no token.
- **A new Worker's first deploy needs `scripts/ensure-worker.sh`.** For a
  Worker that does not exist yet, Cloudflare answers wrangler's secrets lookup
  with "No access to the specified resource" rather than "not found" when the
  token is an account token, and the deploy fails. The script uploads a
  one-line placeholder first, only when the Worker is missing from the
  account's script list. A failed lookup is never read as "missing": it
  stops the deploy, because the placeholder answers 503, and put over the
  live Worker it would take the site down until the real deploy lands.
- **The token's account permissions must be scoped to the account**, not to
  the `workitjobs.ai` zone. Scoped to the zone, Workers Scripts Write grants
  nothing and every call answers "No access" (found 2026-10-21). Zone scope is
  right only for Workers Routes Write.
- **The health check** polls `https://api.workitjobs.ai/health/db` for five
  minutes, the database route because `/health` answers 200 with every
  secret wrong (it did, with `[SENSITIVE]` placeholders). Five minutes,
  because a fresh Container takes a while to start and a rollout replaces
  instances in steps; a red API job with a green deploy step usually means
  the rollout is not finished.

## Scheduled scrape and import (KAN-160)

`workflows/scrape.yml` runs the scraper and then
`app.scripts.import_jobs` into Supabase **every three hours at :17 UTC** (off the
hour: GitHub delays, and under load drops, runs scheduled on it). Daily is what
the big internship lists do and hourly the most any aggregator does; every few
hours gets a new posting onto the site the same day for a ~15 minute run that
only writes the rows that changed. Twelve of those minutes are Workday's (KAN-134):
its boards are read for a fixed share of each run and take about four runs to go
round, page reads stop 20 minutes in (`PAGES_UNTIL_S`), no lane starts a board
after 30 (`BOARDS_UNTIL_S`) and no board's read goes past 40 (`READS_UNTIL_S`),
which keeps the job inside its 90-minute timeout
(`scraper/CLAUDE.md`, "Page reads have a deadline too"): a run cut off by the
timeout saves no store, so the next one repeats it. The scraper runs with `-u`, so
a slow run's log shows where it is.
**A change to the cron changes `RUN_EVERY` in `scraper/workit_scraper/store.py`
too**: quiet boards take turns by that slot. Each run keeps `feed.json`,
`closings.json` (why each stored job is not in the feed, which the import
reads beside `feed.json`), `internships.html` and `metrics.json` (each
provider's share of the run) as an artifact for a week.

It was every six hours until KAN-166. GitHub started those runs up to five hours
late and skipped some outright (2026-10-08 to 10-09), so a posting could wait
twelve hours. Three hours halves the average wait (about 1.5 hours) and the gap a
skipped run leaves, at no cost on a public repo, for twice the requests to the
boards; the scraper's robots.txt and per-site pacing still govern each run, and
the concurrency group queues a late run rather than overlapping it. Going below
an hour buys minutes, multiplies that traffic and raises the odds of a board
rate-limiting the shared GitHub runners, which would stall every job on it.

**Still open: GitHub runs about half of the schedule.** Between 2026-10-16 and
10-27 it started 50 of the 94 runs due at :17 (53%), a median 102 minutes late,
so the real gap between runs was a median 5.5 hours, at most 8.7. The fix being
weighed is a Cloudflare Cron Trigger that starts this workflow through GitHub's
API at exact times (`scraper/docs/coverage.md`, "Later").

**Scheduled and manual runs go to a self-hosted runner** (KAN-726) on a
team computer with Ollama, picked by its `workit-scraper` label; PR runs
stay on `ubuntu-latest`, since the repo is public and a PR run executes the
PR's code. With no such runner online, a scheduled run waits in the queue
and none runs. The job runs bash on both (a Windows runner needs Git for
Windows' bash on its PATH) and calls `python`, not `python3`, which Windows
lacks. A Windows runner also needs the machine's PowerShell policy at
`RemoteSigned`: Windows' default blocks `setup-python`'s installer script,
which failed the first dry run there (2026-11-08). It also needs Python
3.12 put in its tool cache once by an admin, because the installer cannot
install as Network Service; a change to `python-version` in `scrape.yml`
needs that step again (the plan, step 5). And Git's `bin` folder must be
first in the `PATH=` line of the runner's own `C:\actions-runner\.env`
(a `.path` file did nothing for the service): the machine PATH holds
only `Git\cmd`, and the scrape step failed with "bash: command not found".
The job sets `PYTHONUTF8=1`: Windows' default output encoding (cp1252)
failed the import's report on a place name, after the import had worked.
The setup (the runner
and the bank job), why every import embedded 0
before, and a shorter PR run not yet taken up are in
`../docs/scraper_gh_action/plan.md`.

- **Secret:** `DATABASE_URL` (the API's pooler URL, from the root `.env`), in the
  repo's Actions secrets. Without it the run fails at the import step and says so.
- **The keyword pass's model** (`backend/CLAUDE.md`, The feed import):
  `SCOUT_ENDPOINTS_SMALL` is a plain value in the workflow, the computer's
  own Ollama (`qwen3.5:9b` at `localhost:11434`), since it holds no key; the
  `SCOUT_ENDPOINTS` secret, the hosted default chain copied from the root
  `.env` as one JSON line, is its fallback. The four single `SCOUT_*`
  variables are not passed. These are the import's own: the deployed API
  reads its chains from `CF_API_SECRETS_JSON`. The step unsets an empty
  one, because GitHub passes a missing secret as `""`, which Scout's
  settings refuse as a list. The `SCOUT_ENDPOINTS_SMALL` and
  `GEMINI_API_KEY` secrets are no longer read here; `GEMINI_API_KEY` stays
  for the job alerts.
- **`EMBEDDING_PROVIDER: ollama`**: the import embeds jobs on the
  computer's Ollama with the code's default model, `qwen3-embedding:4b`, the
  one model every vector comes from (the computer's bank job embeds the
  banks). Every other workflow leaves the default, `none`.
- **The company list** (`scraper/boards.csv`) is grown by `build_boards.py`
  before every scrape, from the curated GitHub lists, so a company they name
  today is read on the next run without a commit. It only ever adds; the rules
  are in `scraper/CLAUDE.md`.
- **The import retries its own transaction when the connection drops**
  (`import_jobs.IMPORT_ATTEMPTS`, three tries 10 seconds apart), so a
  `DATABASE_URL` pooler disconnect doesn't fail a good scrape. Nothing else is
  retried: an `ImportRefused` or a bad row fails the same way again, and the
  keyword pass after the commit makes paid Scout calls, so the workflow step
  itself runs the import once.
- **The scraper's memory** (`scraper/jobs.json`) lives in the Actions cache,
  restored from the newest entry and saved only after a scrape that finished. A
  missed cache is safe, just slow: that run re-reads every Greenhouse page and
  counts nothing as new.
- **Manual run:** Actions → Scrape jobs → Run workflow, or
  `gh workflow run scrape.yml` (inputs `full` and `dry_run`). A PR that touches the
  scraper, the import or this workflow runs it too, with the import always
  `--dry-run`.
- **It stops silently after 60 days without a commit** to `main` (GitHub pauses
  idle schedules). Re-enable with `gh workflow enable scrape.yml`.
- **When it fails, GitHub emails whoever last edited the cron line.** The import
  refuses to close more than half the jobs at once, so a broken scrape fails the
  run instead of emptying the site; nothing is written either way.

## Job alerts (KAN-298)

`workflows/job-alerts.yml` **no longer carries the real daily schedule.**
The digest (every opted-in applicant's best new matches, scored by the
same `fetch_recommended` + `pick_batch` auto apply's own batch uses,
`auto-apply/architecture.md`'s "Match (built)"/"The batch";
`backend/app/services/job_alerts.py`) now sends through AWS SES
(`backend/app/services/email.py`), authenticated by the sending EC2
instance's IAM role — a role's credentials never leave that instance, so
GitHub's runners structurally cannot send the real mail anymore. The live
run is a crontab entry on that instance, daily at 13:13 UTC (off the
hour, same reasoning as the scrape's own cron), running the same
`app.scripts.send_job_alerts` this workflow calls.
The same instance runs `app.scripts.send_fill_report_alerts` hourly
(KAN-478; e.g. `17 * * * *`), which emails the admins new fix report
groups through the same SES sender and role.

This workflow still exists for two things, both free of real AWS access:
a PR that touches the digest, the script, `email.py` or this workflow
runs it once, always `--dry-run` (never calls `send_email` at all); and
`workflow_dispatch` (Actions → Job alerts → Run workflow, or
`gh workflow run job-alerts.yml`, input `dry_run`) is still there for a
manual non-dry run, but with no IAM role attached it can only prove the
bell-notification path — `send_email` catches the missing-credentials
error, logs it, and returns `False`, the same best-effort outcome as a
bounced send.

- **Secret:** `DATABASE_URL` only. **It makes no embeddings** (KAN-726):
  the default provider `none` reads the bank vectors the team computer
  stores. It set `EMBEDDING_PROVIDER=gemini` until then, which wrote
  Gemini bank vectors beside the others; **the EC2 crontab's environment
  must drop it too**, since that crontab lives outside this repo.
- **One run at a time**, same reasoning as the scrape's concurrency group:
  two overlapping runs would double-send the same applicant. This guards
  against two *workflow* runs overlapping; it says nothing about the EC2
  crontab, which is the user's own to keep from overlapping a workflow run.
- **It stops silently after 60 days without a commit** to `main`, same as
  the scrape. Re-enable with `gh workflow enable job-alerts.yml`.
- **No retry and no queue.** One applicant's failure (an empty bank, a
  bounced email) is caught, counted in the run's report, and logged; it
  never stops the rest of the run, and nobody is sent two digests to make
  up for a missed day.
- **Still open:** the EC2 crontab has no built-in failure alerting the
  way this workflow's schedule trigger got from GitHub for free. Not set
  up yet (a dead-man's-switch ping or a CloudWatch alarm would do it).

## Retention purge (KAN-482)

`workflows/retention-purge.yml` runs `app.scripts.purge_old_data` against
production **daily at 07:43 UTC** (off the hour, same reasoning as the
scrape). It deletes rows past their retention period and logs a count per
table, never a row. The periods live in one place,
`backend/app/services/retention.py`'s `RETENTION`, and the privacy policy's
retention section quotes the same numbers (KAN-474): change both together.
A rule whose table does not exist yet (`fill_events`, until KAN-476) is
skipped and logged as such.

- **It never runs from a PR.** Every run reaches the production database,
  so unlike the scrape and job alerts there is no `pull_request` trigger.
  Only the schedule, on `main`, deletes. A manual run (Actions → Retention
  purge → Run workflow, or `gh workflow run retention-purge.yml`) is always
  a dry run: it logs what it would delete and deletes nothing.
- **Secret:** `DATABASE_URL`, the one the scrape already uses.
- **A failed scheduled run opens an issue** titled "Retention purge failed"
  (or comments on the open one) with the run's link, so the team is told.
  Close it once fixed. GitHub also emails whoever last edited the cron line.
- **It stops silently after 60 days without a commit** to `main`, same as
  the scrape. Re-enable with `gh workflow enable retention-purge.yml`.

## Live canary (`workflows/live-canary.yml`, KAN-468)

The saved forms under `autofiller_extension/fill-engine/test/fixtures/forms/`
are frozen recordings, so a job system that changes its markup or API would
otherwise surface only as students' fix reports. Each night (and by hand:
`gh workflow run live-canary.yml`) the canary reads live forms and compares
them with those saved forms.

- **What it reads.** `autofiller_extension/test/canary/postings.json` names,
  per job system, one board, its pinned postings and the fields its form
  page must show. Each run lists the board's open postings with the job
  system's public API (never the production database) and reads `count`
  of them: the pinned ones still open, then listed ones. For each, the
  engine's own read gives the Question set (`questionSet`), the form is
  opened headless, and the engine's `readback` must find the `onPage`
  fields there (Ashby's `readQuestions` too, its host's fallback). The
  Question set must hold every field all of that system's saved
  `question-set.json` files share, with the same kind, and no kind they
  never have. A form that differs is read once more before it counts.
- **It never fills.** It types nothing, uploads nothing and presses no
  button. `test/canary.spec.ts` runs first and fails if `canary/*.mjs` calls
  any engine function but `jobOf`, `questionSet`, `readback` or
  `readQuestions`, or any of Playwright's fill, click or press calls.
- **A changed form opens an issue** "Live canary: `<site>` form changed"
  (or comments on the open one) naming each posting and its field-kind diff,
  with the default `GITHUB_TOKEN`. A crash before the comparison opens "Live
  canary failed". Close the issue once the engine is fixed.
- **A closed posting is not a change.** A pinned posting the board no longer
  lists is reported in the run's summary as "posting closed" and another
  listed one is read instead; replace it in `postings.json` when convenient.
- **Covered:** Greenhouse, Lever, Ashby, Rippling, Workable, the systems
  whose form opens with no sign-in and whose saved forms have a Question
  set.
- **Skipped, and why:**
  - **Workday, Oracle, iCIMS, SuccessFactors, TikTok:** the form sits behind
    an Apply button or a sign-in, which the canary never presses.
  - **Eightfold, Waymo:** no saved field list (Question set) to compare.
  - **SmartRecruiters:** a bot check (and its robots.txt); so is any other
    system that adds one.
- **Secret:** `FILL_ENGINE_TOKEN`, as in CI: without it the canary job is
  skipped and the `engine` job's summary says SKIPPED. The schedule runs only on `main`, and stops after 60 days
  without a commit there (`gh workflow enable live-canary.yml`).
- **Run it locally:** `cd autofiller_extension/test && npm ci && node
  canary/run.mjs` writes `canary-out/report.md` and `canary-out/issues/`.

## Publish extension to Chrome Web Store (`workflows/publish-extension.yml`, KAN-447)

Keeps the Store listing in step with `autofiller_extension/` (its own
`CLAUDE.md` has the extension itself), so published users run what a PR
here actually reviewed, never a build off someone's machine. Against the
Chrome Web Store API's **v2** endpoints (`chromewebstore.googleapis.com`)
— v1.1 (`www.googleapis.com/chromewebstore`) stopped taking requests on
2026-10-15. v2's resource name is `publishers/<PUBLISHER_ID>/items/<id>`,
never the item id alone, and upload/publish each return a `state`-style
enum (`uploadState`, `state`) rather than v1.1's `status` array. Two jobs:

- **`check-version-bump`**, every PR touching the extension's own files
  (`manifest.json`, `icons/`, `fonts/`, `src/`, `store/`; KAN-669): fails unless
  `autofiller_extension/store/store.json`'s `version` is strictly greater
  than `main`'s (`dpkg --compare-versions`) — the Store package's own
  version (`store/build.mjs`, KAN-463, writes it over whatever
  `manifest.json`'s own `version` says, which is the unpacked dev build's
  only; the two are deliberately separate numbers, so bumping the wrong
  one here is a real, easy mistake). The Store API refuses a re-upload of
  a version it already has, so this catches a forgotten bump before merge
  rather than after, with no PR left open to fix it from. **The bump is a
  one-line, by-hand part of the PR**, on purpose — not something this
  workflow writes and commits itself, which would need write-back
  permissions and risks a loop for little gained.
- **`publish`**, on a push to `main` that touches those same files (or by
  hand — **main only**: a push trigger is already branch-filtered, but `workflow_dispatch` has no such
  filter on GitHub's side, so the job itself checks `github.ref ==
  'refs/heads/main'` or a dispatch from any other branch would submit
  unreviewed code for real Store review). Runs `store/build.mjs` (the
  same Store package `extension-store-build` already builds and checks
  in CI, above — never a second, ad-hoc zip step here) and pushes the
  result through the Chrome Web Store API, then submits it for review.

An engine pointer move alone needs no bump and starts no publish, so Store
users get that engine with the next bump. To ship an engine fix sooner, bump
`store.json` in the pointer's PR: that PR then publishes the new pointer too.
These path filters skip the whole workflow, so GitHub reports no check for a
skipped PR. Do not make `check-version-bump` a required check, or those PRs
wait for it forever.

**This does not make an update live by itself.** The extension asks for
sensitive permissions (`cookies`, several hosts), so Google reviews every
submission by hand regardless of this workflow — a green run here means
"queued for review," not "published." A failed or stuck review needs a
human in the [Developer Dashboard](https://chrome.google.com/webstore/devconsole),
not a re-run.

- **Secrets:** `CHROME_CLIENT_ID`, `CHROME_CLIENT_SECRET`,
  `CHROME_REFRESH_TOKEN` (a Google Cloud OAuth client with the Chrome Web
  Store API enabled, and a refresh token for the account that owns the
  Store listing — a one-time human setup, not reproducible from this
  file), `CHROME_EXTENSION_ID` (the Store item id; this extension pins it
  via `manifest.json`'s `key`, so it matches the id Chrome already
  assigns the unpacked dev build, `cpklhdkoafegnndlafmiceehfloodjgi`) and
  **`CHROME_PUBLISHER_ID`** (Publisher > Settings in the Developer
  Dashboard — a different value from the item id, and new with the v2
  endpoints above; v1.1 never needed it) and **`FILL_ENGINE_TOKEN`** (a
  PAT with read access to the private `workitjobs/fill-engine` repo
  — the same secret `ci.yml`'s `extension-store-build` job uses; without
  it `publish`'s checkout can't read the submodule at all, since the
  default `GITHUB_TOKEN` has no cross-repo access, and the job fails at
  checkout rather than silently skipping, unlike CI's own gentler
  `engine-token.yml` skip-when-unset pattern — a real publish with no
  engine isn't something to skip quietly).
  **All six must be Actions *secrets*, never Actions *variables*:**
  a repo variable's value is plaintext, readable by anyone with
  Settings access and unmasked in logs — found live on 2026-10-31, all
  three sensitive values set as variables instead (the fourth, the
  Store item id, under a typo'd name a variable never read by this
  workflow at all). Fixed by resetting the OAuth client secret, minting
  a fresh refresh token (Google's Desktop-app loopback flow:
  `accounts.google.com/o/oauth2/v2/auth` with `redirect_uri=
  http://localhost:<port>`, copy the `code` off the failed redirect's
  address bar, then `POST oauth2.googleapis.com/token` for the
  `refresh_token` — the OAuth Playground's "use your own credentials"
  only works for a *Web application* client, which this one isn't),
  deleting the leaked variables, and `gh secret set`-ing all four as
  secrets. The workflow already read `secrets.*`, never `vars.*`, the
  whole time — so this cost no code change, only means the publish job
  silently couldn't have authenticated until the real secrets existed.
- **The API can only update an existing Store item.** The very first
  submission — store listing, screenshots, privacy-practice
  justifications — is a one-time manual step in the Dashboard; this
  workflow has nothing to push to until that exists.
- **One run at a time**, same reasoning as the other workflows: two
  overlapping publishes could submit two versions out of order.
- **Still open:** no notification when a submitted version clears (or
  fails) Google's review — that's checked by hand in the Dashboard for
  now.

## Company websites from Wikidata (`workflows/company-domains.yml`)

Runs `scraper/domain_pr.py --publish` daily at 07:29 UTC on `ubuntu-latest`.
It downloads the newest scheduled scrape's `metrics.json` artifact (hence
`actions: read`), looks up on Wikidata up to 150 of the companies whose jobs
have no `company_domain`, and adds the websites that pass its rules to
`scraper/checked_websites.csv` on one rolling PR from a
`codex/company-domains-after-<n>` branch, with `scraper/company-domains.json`
recording every board looked up. It never pushes to main and never merges.
A person checks each row's note (the Wikidata item and its description) and
removes the wrong ones before merging; the rules and why are in
`scraper/docs/logos.md`, "Wikidata proposals".

- **Like discovery, it needs "Allow GitHub Actions to create and approve pull
  requests"**, and its PR, opened with `github.token`, starts no CI until a
  person pushes to the branch.
- **A PR closed without merging pauses it**: its ledger never reached main, so
  every board in it would be proposed again. Reopen it, remove the rows you
  reject and merge it, ledger included.
- **It needs a scheduled scrape from the last week**, whose artifact it reads;
  with none it fails and says so.
- **It stops silently after 60 days without a commit** to `main`, like every
  schedule here (`gh workflow enable company-domains.yml`).
