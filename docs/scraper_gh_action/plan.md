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
with `none`. A laptop that set `ollama` and ran it would write the same
model's vectors, so nothing breaks, but there is no reason to.

## Setting up the computer

A person does this once, on the computer, with admin rights on the repo.

1. **Install** Git (on Windows, Git for Windows: the job runs bash, and it
   must be on the runner's PATH), uv and Ollama, then
   `ollama pull qwen3.5:9b` and `ollama pull qwen3-embedding:4b`.
   `curl http://localhost:11434/v1/models` lists them when Ollama is up.
2. **Ollama starts on boot.** The Linux installer makes a systemd service.
   On Windows the app starts at sign-in only, so add `ollama serve` as a
   Task Scheduler task at startup, or keep a user signed in. Turn sleep off.
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
   `config`.
6. **Fork PRs need approval**: Settings, Actions, General, "Require
   approval for all external contributors". The workflow already sends PR
   runs to GitHub's runner; this is a second guard.
7. **Try it**: `gh workflow run scrape.yml --ref <branch> -f dry_run=true`
   runs the branch's workflow on the computer and writes nothing (a dry run
   calls no model). The real run waits for the cutover, below.
8. **A checkout for the bank job**: clone the repo, run `uv sync` in
   `backend/`, and give it a root `.env` with `DATABASE_URL`, `DIRECT_URL`
   (the session pooler, port 5432, where it listens) and
   `EMBEDDING_PROVIDER=ollama`. The session pooler is IPv4, so a campus
   network reaches it; check port 5432 as in step 3.
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

   On Windows, a Task Scheduler task at startup that runs
   `uv run python -m app.scripts.embed_banks` in `backend\`, restarting on
   failure. Its log says "Listening on bank_dirty", then one line a sweep.

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
5. **Backfill the jobs** on the computer:
   `EMBEDDING_PROVIDER=ollama uv run python -m app.scripts.import_jobs --embeddings-only`
   in the bank job's checkout. Then the keyword backfill (Decision 2).

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
