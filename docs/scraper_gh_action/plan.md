# Moving the scheduled scrape to our own computer

KAN-726. Agreed on 2026-11-08; Decisions 1 to 4 are built. The computer's
setup and the cutover are by hand (Setting up the computer, The cutover,
below). Not built: the shorter PR run.

It moves the scheduled scrape and import (`.github/workflows/scrape.yml`, KAN-160) off
GitHub's hosted runners onto a team computer, and moves keyword extraction
and embeddings from hosted APIs to local models on that computer.

The computer: AMD Ryzen 9 9900X (12 cores), RTX 3080 (10 GB VRAM; 12 GB on
some cards), 32 GB RAM.

## Why move

- **Run time.** The scrape has had to fit inside its job timeout, so the
  scraper stops reading pages, starting boards and reading boards at fixed
  deadlines (`PAGES_UNTIL_S`, `BOARDS_UNTIL_S`, `READS_UNTIL_S` in
  `scraper/workit_scraper/__main__.py`). A run that hits the timeout saves no
  store, so the next one repeats its work.
- **GitHub runs about half the schedule**, a median 102 minutes late
  (`.github/CLAUDE.md`, "Still open").
- **Hosted model quotas run out**, and GitHub's runners cannot run a local
  model, so keywords and embeddings had to use APIs.
- Note: the repo is public, so GitHub's hosted runners are free with no
  minutes limit. What stopped us was the timeouts, the late schedule and the
  API quotas, not a minutes bill.

## Decision 1: a self-hosted GitHub Actions runner

The computer runs GitHub's runner program. It keeps an outgoing HTTPS
connection to GitHub and waits for jobs. GitHub keeps the schedule, the
queue, the concurrency group, the logs, the secrets and the failure emails;
when a run starts, GitHub sends the job to the computer, which checks out the
repo and runs every step (scrape, import, models, database writes).

Chosen over our own cron job, which would have to rebuild the logs, failure
alerts, secrets handling and the one-run-at-a-time rule.

- **Only scheduled and manual runs go to the computer.** The PR run stays on
  `ubuntu-latest`. The repo is public, a PR run executes the PR's code, and on
  our computer a stranger's PR could run anything with access to its files
  and `.env`:

  ```yaml
  runs-on: ${{ github.event_name == 'pull_request' && 'ubuntu-latest' || 'self-hosted' }}
  ```

- **Start times.** The runner does not fix GitHub's late and skipped
  scheduled runs. A local cron that only runs `gh workflow run scrape.yml`
  starts each run on time; the runner then picks it up at once.
- **Limits can relax.** With no hosted timeout, the scraper's deadlines and
  `--keywords-limit` (default 100) can go up. A change to the cron still
  changes `RUN_EVERY` in `scraper/workit_scraper/store.py`.
- **The store** (`scraper/jobs.json`) can stay in the Actions cache as now,
  or live on the computer's disk; decide when building.

### The university network

The computer may sit on a university network. The runner needs only outgoing
HTTPS, so it usually works behind a campus firewall. Check before relying on
it:

- **The database port.** The import reaches Supabase on 5432 or 6543, not
  443. Some campus firewalls block these. Test from the computer first.
- **Campus policy.** Many universities forbid servers or bulk scraping. Ask
  IT. A company job board that blocks the university's address blocks every
  student behind it, not only us.
- **Sign-in Wi-Fi.** A login page or expiring session drops the runner. Use a
  wired connection.
- **HTTPS-inspecting proxies** break connections to GitHub or the boards;
  they show as certificate errors.

## Decision 2: keywords on a local model

`qwen3.5:9b` on Ollama, for keyword extraction only, set as
`SCOUT_ENDPOINTS_SMALL` pointing at `http://localhost:11434/v1` in the
workflow. A hosted endpoint can stay after it in the chain as a fallback.

Changing the keyword model is safe: a different model gives a somewhat
different list, but nothing breaks, and each posting's keywords are saved
once and reused (`keywords_hash`). The API's own keyword paths (the keyword
match, Tailor, a company job's save) keep the hosted chain on Cloudflare,
since whichever path reads a posting first caches its keywords.

Compare the local model's keywords with the current output on a sample of
postings before switching.

**The backfill needs no new script.** `import_jobs --keywords-only` extracts
keywords for every published scraped job with none, each job committing on
its own; a reply that fails its schema is tried again next run, and a model
that stops answering ends the run with what it wrote.

Run it on the computer from a checkout with the root `.env`, which gives it
`DATABASE_URL` (the shared database: the run writes real rows). The model is
not in the code but in `SCOUT_ENDPOINTS_SMALL`, and the local value lives in
`scrape.yml`, which a run typed by hand never reads; the `.env` names the
hosted chain. So override both chains in the shell, which beats the `.env`:
the small chain and the default chain after it both point at the local
model (an endpoint in both is tried once), so a failed local call never
falls back to Groq's quota.

```
cd backend
LOCAL='[{"base_url":"http://localhost:11434/v1","model":"qwen3.5:9b","reasoning_effort":"none"}]'
SCOUT_ENDPOINTS_SMALL="$LOCAL" SCOUT_ENDPOINTS="$LOCAL" \
  uv run python -m app.scripts.import_jobs --keywords-only --keywords-limit 20
```

Then run it again with `--keywords-limit 100000`: there is no "all", and the
default is 100. The run of 20 times it: a 9B model likely takes seconds per
job, so thousands take hours. Keywords that hosted models already wrote
stay.

## Decision 3: embeddings on a local model, made only on the computer

### The rule that drives this

Job vectors and experience bank vectors are compared directly in Postgres,
so **every vector in the database must come from one model**. Vectors from
two models at the same width give no error, only wrong scores
(`backend/app/services/matching/CLAUDE.md`). There is no column recording
which model made a vector, so a model change clears both columns first.

### Option C: the computer embeds jobs and banks; the API never embeds

- The import embeds jobs, as now (`import_jobs` embeds, then extracts
  keywords, after its commit).
- A separate job on the computer, run every few minutes by a plain local
  timer (not GitHub's schedule, which is too unreliable for that), embeds
  every bank whose vector is stale (Decision 4).
- The API only reads stored vectors: `EMBEDDING_PROVIDER` defaults to
  `none`, which embeds nothing and calls nothing.
- **Every other writer stops embedding too**, by the same default: the job
  alerts set `EMBEDDING_PROVIDER=gemini` and wrote Gemini bank vectors, and
  a laptop's API defaulted to Ollama's Nomic against the shared database.
  `job-alerts.yml` no longer sets it; the EC2 crontab's environment must
  drop it by hand (The cutover).

Rejected:

- **A. Gemini for jobs and banks.** Least work (one line in `scrape.yml`),
  but it keeps the quota problem.
- **B. A local model that the API reaches through a Cloudflare Tunnel.**
  Works on a campus network (outgoing only), but recommendations depend on
  the computer being up for every request.
- **A model on Cloudflare.** Containers have no GPU; Workers AI is another
  hosted API.

### The model

**`qwen3-embedding:4b`** (about 2.5 GB, high on the public MTEB
benchmarks), now the code's default `OLLAMA_EMBEDDING_MODEL`.
`nomic-embed-text:v1.5`, the old default, was dropped: it is small and
older, and its results were judged too weak.

- **The width: 768, no migration.** Qwen3's 4B answers 2,560 values; its
  training makes the first part of a vector stand alone, so `embed()` keeps
  the first 768 and scales them to length 1 (`_shortened`). Moving to 1024
  later is a migration to `vector(1024)` on both columns and a clear.
- **An instruction on the bank side, built.** A bank is the query, a
  posting the document; `embed(..., query=True)` puts
  `OLLAMA_EMBEDDING_QUERY_PREFIX` before each bank's text.
- **Still open: no side-by-side test.** It was picked from benchmarks.
  Before or soon after the cutover, embed 20 to 50 real jobs and a few
  banks and check that the top matches make sense; `qwen3-embedding:0.6b`
  and `embeddinggemma` are the alternatives, each a clear and re-embed.

Ollama loads a model on first call, keeps it about 5 minutes and unloads it
when VRAM runs short, so the embedding model and `qwen3.5:9b` need no
manual sequencing; the two fit in 10 GB together anyway.

### The backfill

Jobs: `uv run python -m app.scripts.import_jobs --embeddings-only` with no
`--embed-limit`, on the computer, embeds every scraped job with no vector.
Banks: the bank job sweeps every stale bank when it starts.

### Why every scheduled import embedded 0 before KAN-726

`scrape.yml` passed `GEMINI_API_KEY` but never set `EMBEDDING_PROVIDER`.
The default was `ollama`, GitHub's runner has no Ollama, and a failed embed
stores nothing, so no scraped job had a vector. Bank embedding on the
deployed API likely failed the same way unless `CF_API_SECRETS_JSON` set
the provider, so it retried on every visit.

## Decision 4: a stale bank vector stays until its replacement is ready

Before KAN-726, every bank change set `experience_banks.embedding` to NULL
(`services/bank.py`, `clear_embedding`). Under option C that opens a window,
growing with scale, in which the student's matches score with no semantic
part at all.

Instead, a bank change keeps the old vector and only marks it stale. The
mark already exists: every bank change sets `updated_at`, and storing a
vector sets `embedded_at` and keeps `updated_at` as it was (KAN-425). So:

- **Stale** means `embedded_at IS NULL OR embedded_at < updated_at`. No new
  column and no migration.
- `clear_embedding` stops clearing `embedding` and `embedded_at`; it only
  sets `updated_at`.
- The bank job embeds the stale rows and writes only if `updated_at` is
  still the value it read (the existing conditional write), so a change
  that lands while the model runs leaves the row stale for the next pass.
- Recommendations read whatever vector is stored: the last version of the
  bank until the new one is ready, which is far closer than none.
- A model change still clears both columns, because an old-model vector is
  not merely stale but incomparable. Agreed for the move to Qwen3: clear
  every existing vector and embed again, so no old vector lowers quality.

### New banks first, and how long they wait

- **Order.** The bank job embeds banks that never had a vector first (a new
  student), then changed banks, oldest change first:
  `ORDER BY embedded_at IS NULL DESC, updated_at`. A new student with no
  vector still gets matches, scored without the semantic part.
- **Chosen (2026-11-08): Postgres `LISTEN`/`NOTIFY`, with a backup check
  every 6 hours** (traffic is near zero today; shorten it if that changes). The server cannot easily call the computer, but
  the computer can listen: it holds an outgoing connection to Supabase with
  `LISTEN`, and the API sends `NOTIFY` when a bank changes, so the computer
  embeds within seconds. Outgoing only, so it works on a campus network.
  - **The listener uses the session pooler** (IPv4, port 5432). The
    transaction pooler (6543) does not support `LISTEN`, and the direct
    connection is IPv6 only without Supabase's IPv4 add-on, which a campus
    network may not route.
  - **The API sends it in `clear_embedding`**:
    `pg_notify('bank_dirty', <applicant id>)`. Postgres delivers it only on
    commit, and `NOTIFY` works through the API's transaction pooler, so the
    API needs no new connection.
  - **The listener reconnects by itself**; campus networks and the pooler
    drop idle connections.
  - **The backup check** (one small query) also runs each time the listener
    starts or reconnects, so messages lost while the computer was off or the
    connection was down are caught on its return; the 6-hourly run is for
    the rare rest.
  - **Notifications are grouped, not handled one by one.** The first one
    starts a wait of about 60 seconds; every notification in that time
    joins it, and then each dirty bank is embedded once, in one batch. At
    most one batch starts per minute. Without this, a student saving ten
    edits in a row embeds their bank ten times.
  - **Cost to the computer:** the work grows with the number of bank
    changes, not with wake-ups; a poll would do the same embeds later. An
    idle connection uses no CPU or GPU, one bank is well under a second of
    GPU, and Ollama unloads the model after about 5 idle minutes (a shorter
    `keep_alive` frees the GPU sooner). The scrape, not the listener, is
    what loads the computer.
  - Rejected as the main path: a check every 30 to 60 seconds alone. It
    works, but waits longer and queries more for the same result.
- While the computer is off, new students get no semantic part, and changed
  banks keep their last vector, until it is back.

Built with it: the `Experience_Bank` docstring
(`backend/app/models/bank.py`) and the "When things are embedded" rules in
`backend/app/services/matching/CLAUDE.md`. `embedded_at` holds the bank
version the vector was made from (the `updated_at` read), not the time of
the write: a change whose transaction began before the write but committed
after it would carry an earlier time, and the stale check would miss it.

## Who runs what

All of it merges to `main`: every machine runs the same code, and what a
machine does comes from its environment and from which processes it starts.

| Machine | Starts | Its `EMBEDDING_PROVIDER` |
| --- | --- | --- |
| The team computer | the GitHub runner (scrape, import, keywords, job vectors) and the bank job (`embed_banks`) | `ollama`: `scrape.yml` sets it for the import; the computer's root `.env` sets it for the bank job |
| The deployed API (Cloudflare) | the API | unset, so `none`: reads vectors, makes none |
| Job alerts (EC2) | the digest | unset, so `none` |
| Laptops | the API, tests | unset, so `none` |

The bank job runs only where someone starts it, and it refuses to start
with `none`. Sharing `DATABASE_URL` and `DIRECT_URL` sends no one else a
notification: Postgres delivers a `NOTIFY` only to a connection that ran
`LISTEN` on its channel, and only the bank job does. A second bank job
started anywhere waits on standby: each holds a Postgres advisory lock on
its listening connection (`embed_banks.LOCK_KEY`), so only one works, and
the standby takes over when the first one's connection is gone.

## Setting up the computer

A person does this once, on the computer, with admin rights on the repo.

1. **Install** Git (on Windows, Git for Windows: the job runs bash, and it
   must be on the runner's PATH), uv and Ollama, then
   `ollama pull qwen3.5:9b` and `ollama pull qwen3-embedding:4b`.
   `curl http://localhost:11434/v1/models` lists them when Ollama is up.
2. **Ollama starts on boot.** The Linux installer makes a systemd service.
   On Windows the app starts at sign-in only, so add `ollama serve` as a
   Task Scheduler task at startup, or keep a user signed in. Turn sleep off.
   On Windows, run the task as SYSTEM with the machine variable
   `OLLAMA_MODELS` set to the folder the models were pulled into
   (`%USERPROFILE%\.ollama\models`), and delete the Ollama app's shortcut
   from the Startup folder, or the app starts a second server on the same
   port at sign-in. A task under a Microsoft account fails with "The user
   name or password is incorrect" even with the right password; SYSTEM
   needs none.
3. **Check the network** (The university network, above): from the
   computer, connect to the `DATABASE_URL` host on port 6543, for example
   `python -c "import socket; socket.create_connection(('<pooler host>', 6543), 5)"`.
4. **Add the runner**: the repo's Settings, Actions, Runners, New
   self-hosted runner, pick the OS, and run the commands that page shows.
   When `config` asks for additional labels, enter `workit-scraper`: the
   workflow picks the runner by it.
5. **Run it as a service**, so it survives a reboot: on Linux
   `sudo ./svc.sh install` then `sudo ./svc.sh start` in the runner's
   folder; on Windows answer yes to running it as a service during
   `config`. **On Windows, also allow scripts machine-wide** in an admin
   PowerShell: `Set-ExecutionPolicy RemoteSigned -Scope LocalMachine`.
   The service runs as Network Service, which gets the machine's policy,
   and Windows' default blocks every script: the first dry run
   (2026-11-08) failed at `setup-python`, whose installer is
   `setup.ps1`. **Then install Python once as admin**: past the policy,
   that installer still failed ("Error happened during Python
   installation"), since it installs for all users and Network Service is
   no admin. Download `setup-python`'s own package for the version a run
   asks for (its log names the zip, from `actions/python-versions`), unzip
   it, and in an admin PowerShell in that folder run
   `$env:RUNNER_TOOL_CACHE = 'C:\actions-runner\_work\_tool'; .\setup.ps1`.
   Every run then finds Python in the tool cache and skips the installer.
   A version bump in `scrape.yml` needs this again. Not chosen: running the
   service as Local System, which gives every run full control of the
   computer. **Then put Git's bash on the runner's PATH**: Git for Windows
   adds only `Git\cmd` to the machine PATH, and the scrape step failed with
   "bash: command not found". In an admin PowerShell, set the runner's
   PATH in its `.env` file and restart the service:
   `Set-Content C:\actions-runner\.env ('PATH=C:\Program Files\Git\bin;' + [Environment]::GetEnvironmentVariable('Path','Machine')) -Encoding ASCII`,
   then `Restart-Service actions.runner.*`. The runner loads `.env` when it
   starts; a `.path` file did nothing for the service on Windows. Its PATH
   replaces the machine PATH, so a later change to the machine PATH needs
   this again. The same file holds `PYTHONUTF8=1`, which `scrape.yml` also
   sets: the first full dry run imported fine, then failed printing a place
   name in Windows' default encoding.
6. **Fork PRs need approval**: Settings, Actions, General, "Require
   approval for all external contributors". The workflow already sends PR
   runs to GitHub's runner; this is a second guard.
7. **Try it**: `gh workflow run scrape.yml --ref <branch> -f dry_run=true`
   runs the branch's workflow on the computer and writes nothing (a dry run
   calls no model). The real run waits for the cutover, below.
8. **A checkout for the bank job**: clone the repo on `main`, run
   `uv sync` in `backend/`, and give it a root `.env` with `DATABASE_URL`,
   `DIRECT_URL` (the session pooler, port 5432, where it listens) and
   `EMBEDDING_PROVIDER=ollama`. The session pooler is IPv4, so a campus
   network reaches it; check port 5432 as in step 3. **Its own clone, never
   a developer's checkout or a worktree of one**: the task runs whatever
   that folder has checked out, a worktree cannot hold `main` while the
   main checkout does, and this `.env` is the only one that sets
   `ollama`, so a developer's API stays at `none`. On the team computer
   it is `C:\workit-bank-job`. Nobody edits code there. **On Windows, keep
   its Python inside the checkout**, since the task runs as SYSTEM:

   ```powershell
   cd C:\workit-bank-job\backend
   $env:UV_PYTHON_INSTALL_DIR = 'C:\workit-bank-job\.python'; uv sync --managed-python
   ```

   A plain `uv sync` points `.venv` at a Python under the user's own
   `AppData`, and run as SYSTEM the job stopped at once with "No Python at
   ..." (2026-11-08). Add `.python/` and `bank-job.log` to the checkout's
   `.git/info/exclude`.
9. **Make the bank job a service**, not started until the cutover. On Linux,
   a systemd unit:

   ```ini
   [Unit]
   Description=WorkIt bank job
   After=network-online.target ollama.service

   [Service]
   WorkingDirectory=/path/to/checkout/backend
   ExecStart=/path/to/uv run python -m app.scripts.embed_banks
   Restart=always
   RestartSec=30

   [Install]
   WantedBy=multi-user.target
   ```

   On Windows, a Task Scheduler task at startup, as SYSTEM, in an admin
   PowerShell. It runs the checkout's own Python, not `uv run`, so uv
   keeps no second cache in SYSTEM's folder; it starts 2 minutes after
   boot, so Ollama is up for its first sweep; and Task Scheduler keeps no
   output, so it writes a log:

   ```powershell
   $a = New-ScheduledTaskAction -Execute 'cmd.exe' -WorkingDirectory 'C:\workit-bank-job\backend' -Argument '/c C:\workit-bank-job\backend\.venv\Scripts\python.exe -u -m app.scripts.embed_banks >> C:\workit-bank-job\bank-job.log 2>&1'
   $t = New-ScheduledTaskTrigger -AtStartup; $t.Delay = 'PT2M'
   $s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable
   $p = New-ScheduledTaskPrincipal -UserId SYSTEM -LogonType ServiceAccount -RunLevel Highest
   Register-ScheduledTask -TaskName 'WorkIt bank job' -Action $a -Trigger $t -Settings $s -Principal $p
   ```

   Its log says "Listening on bank_dirty", then one line a sweep. The
   task's restart setting covers only a task that fails to launch, not a
   job that exits: a job that stops (ended in Task Manager, a fatal error)
   stays stopped until `Start-ScheduledTask 'WorkIt bank job'` or the next
   boot. The job itself never exits on a lost connection; it reconnects.

### After a merge to main

The runner needs nothing: each run checks out the commit it runs. The bank
job runs from its own checkout, so a merge that changes `backend/` or
`scout/` reaches it only when a person, on the computer, runs:

```powershell
cd C:\workit-bank-job; git pull; cd backend
$env:UV_PYTHON_INSTALL_DIR = 'C:\workit-bank-job\.python'; uv sync --managed-python
```

**Never a plain `uv sync` there.** Without `UV_PYTHON_INSTALL_DIR` uv
picks the user's own Python and rebuilds `.venv`: on 2026-11-08 it emptied
`site-packages`, stopped at `Scripts` (the running job held it open), and
left a job that would fail on its next start. To repair, stop the task,
delete `backend\.venv`, and run the two lines above. Then, in an admin
PowerShell,
`Stop-ScheduledTask 'WorkIt bank job'; Start-ScheduledTask 'WorkIt bank job'`,
and checks the log (`Get-Content C:\workit-bank-job\bank-job.log -Tail 20`)
for "Listening on bank_dirty". Until then the old code keeps embedding. A
merge that needs a migration first follows that migration's order, as the
API does (`backend/CLAUDE.md`, Deployment). A change to the embedding model
or its prefix is a model change: clear both columns first (Decision 3).

While the runner is offline, scheduled runs wait in the queue and nothing
is scraped; GitHub cancels a job that waits 24 hours. While the bank job is
off, changed banks keep their last vector and new banks score without the
semantic part; it catches up when it starts.

## The cutover

In this order, because merging moves the scrape to the runner and makes
every other machine stop embedding:

1. **Before merging**: make sure `CF_API_SECRETS_JSON` sets no
   `EMBEDDING_PROVIDER` (remove it if it does, then rerun the deploy so the
   secret takes), and drop `EMBEDDING_PROVIDER=gemini` from the EC2
   crontab's environment. The computer's setup, steps 1 to 9, is done and
   the runner is online.
2. **Merge.** The API deploys with `none`, and the next scheduled scrape
   runs on the computer.
3. **Apply the migration** `e8c3f1a7b925` (`uv run alembic upgrade head`,
   by a person): it clears every old vector. Do it right after the deploy;
   job vectors the computer wrote in between are cleared too, and made again
   in step 5.
4. **Start the bank job.** Its first sweep embeds every bank.
5. **Backfill the jobs** on the computer (The backfills, below): the jobs
   from before the cutover, which scheduled runs never read.

Done on 2026-11-08: steps 2 to 4 (15 of 16 banks embedded; the 16th has no
entries or skills). Step 5 is next.

## The backfills

Once, after the cutover, by a person on the computer, in a normal
PowerShell. They write to the shared database, so Claude never runs them.
Each job commits on its own, so a stopped run loses nothing: run the same
command again and it goes on with the jobs still missing.

```powershell
cd C:\workit-bank-job\backend
```

The bank job's checkout is the right place: its `.env` sets
`EMBEDDING_PROVIDER=ollama` and no hosted Scout chain, so a failed local
call never spends Groq's quota. Call its Python directly; it needs no
`uv sync` (above).

**Job vectors first.** Time a small batch, then the rest:

```powershell
.\.venv\Scripts\python.exe -m app.scripts.import_jobs --embeddings-only --embed-limit 200
.\.venv\Scripts\python.exe -m app.scripts.import_jobs --embeddings-only
```

**Who does which jobs.** A scheduled import embeds and reads keywords for
its own jobs only, the ones it inserted or changed, so a new job is ready
after one run. Every older job missing either one is the backlog, and only
these backfills read it. Without them, jobs from before the cutover never
get a vector or keywords. Hold the vector backfill until the storage plan
below is decided; new jobs get vectors meanwhile.

**Then keywords on the local model** (Decision 2). Set the small chain in
the same window, time 20 jobs and compare them with keywords a hosted
model wrote, then run the rest with a limit above the job count (there is
no "all"):

```powershell
$env:SCOUT_ENDPOINTS_SMALL = '[{"base_url": "http://localhost:11434/v1", "model": "qwen3.5:9b", "reasoning_effort": "none"}]'
.\.venv\Scripts\python.exe -m app.scripts.import_jobs --keywords-only --keywords-limit 20
.\.venv\Scripts\python.exe -m app.scripts.import_jobs --keywords-only --keywords-limit 50000
```

One call took about 7 seconds in a test, so the 46,819 listed jobs with
none (2026-11-08) can take days; leave the window open, or rerun it.

**Side by side with the scrape.** The scrape itself is network-bound and
pays no GPU. The import's two model passes, the bank job and the
backfills share the one GPU: both models fit in its 10 GB together, so
nothing reloads, but each call is slower while another runs, and the
total time is about the same as running them one after another. A
backfill rarely meets a scheduled import on the same job, since the import
reads only its own; when it does, the model runs twice and both write the
same result.

## Storage on Supabase's free plan

The free plan allows 500 MB; the database was 639 MB on 2026-11-08,
measured read-only before the backfills. Nearly all of it is
`job_postings` (600 MB on disk, 58,818 scraped rows, 47,649 listed):

| Part | Size |
| --- | --- |
| `fts`, the stored search column (generated) | 217 MB |
| `description` | 150 MB |
| Other columns | about 15 MB |
| Free space left by updated rows (600 on disk, 381 live, minus indexes) | about 135 MB |
| Indexes (the `fts` GIN index is 60 MB) | 84 MB |

What the backfills add:

- **Keywords:** about 650 bytes a job, so about 30 MB for every listed
  job. Small.
- **Vectors:** `vector(768)` is about 3 KB a job, so about 145 MB for the
  listed jobs and 180 MB for all scraped ones. Postgres puts them in the
  free space first, so the file grows by less, but it still grows.

A plan to stay on the free plan, largest saving first. None is built:

1. **Reclaim the free space**: `VACUUM FULL job_postings`, or `pg_repack`
   (on Supabase) to avoid a long lock, run by a person after the
   backfills. About 135 MB, at once. Ordinary autovacuum reuses that space
   but never returns it.
2. **Make `fts` smaller**: index only the start of a long description
   (`left(description, N)` in the generated column), or drop the stored
   column for an expression index with the same weights. Up to 217 MB, but
   it changes how search ranks (`docs/search.md`): test it there first.
3. **Embed listed jobs only**, and clear a job's vector when it closes:
   the 11,183 closed jobs would hold about 33 MB of vectors no student
   sees. **Built** (2026-11-08): `_embed_jobs` reads published jobs only,
   and `_close_missing` clears the vector; a job that comes back counts as
   changed, so its run embeds it again. Every scoring query reads `LISTED`
   jobs only, so nothing reads a closed job's vector. Keywords stay on a
   closed job: they are small, and a tailored resume's match against its
   own closed posting reads them.
4. **`halfvec(768)`**: half precision halves every vector (about 70 MB
   for the listed jobs) with almost no change in scores. A migration on
   both vector columns and their casts.
5. **Retention for closed jobs**: delete closed jobs no application
   names after some days, through the retention purge
   (`services/retention.py`). About 70 MB today, and it stops the table
   growing with every closed posting.

## Not now: a shorter PR run

Documented, not being built. `scrape.yml` also runs on a PR to `main` that
changes `scrape.yml`, `scraper/**`, `backend/app/scripts/import_jobs.py` or
`backend/app/schemas/jobs.py`. It scrapes every board in
`scraper/boards.csv` (about 5,000) and imports with `--dry-run`, which reads
the real database, reports what would change and writes nothing; a dry run
calls no model. It proves a scraper change before merge, and takes as long
as a scheduled run.

To make it a few minutes, with flags that exist already:

1. **Scrape a sample.** Pass `--boards scraper/pr_boards.csv`, a committed
   list of one or two boards per hiring system, on PRs only.
2. **Import with `--dry-run --allow-mass-close`.** A sample feed lacks most
   stored jobs, which the import would refuse as a mass close; the dry run
   rolls everything back, so the flag is safe there.
3. **Skip saving the scraper's store on PRs.**

Lost: a bug that shows only at full scale, or on a board outside the sample,
is caught by the next scheduled run instead of before the merge. The
mass-close guard still protects scheduled runs.

## What was built

- `scrape.yml`: scheduled and manual runs on the runner; keywords from
  local `qwen3.5:9b`; jobs embedded with `EMBEDDING_PROVIDER: ollama`.
- `EMBEDDING_PROVIDER` defaults to `none`; `job-alerts.yml` no longer sets
  `gemini`.
- `embeddings.py`: `qwen3-embedding:4b` by default, cut to 768; banks sent
  with the query prefix.
- `services/bank.py`: a change keeps the vector, moves `updated_at` and
  sends `pg_notify('bank_dirty', <applicant id>)` in its `RETURNING`, so
  the editor's save stays one statement.
- `services/matching/bank_vectors.py`: the stale rule and the conditional
  store, shared by the request path and the bank job.
- `app/scripts/embed_banks.py`: the bank job.
- Migration `e8c3f1a7b925`: clears every vector.
