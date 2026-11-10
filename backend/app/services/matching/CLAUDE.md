# CLAUDE.md — job matching

How a listed job is scored against one applicant's experience bank (KAN-139;
the bank replaced the default resume in KAN-212). Loaded on
top of `../../../CLAUDE.md` (the Python API) and the repo root's. Read it before
changing anything in this folder or the columns it reads.

## The design (agreed 2026-10-09)

The pipeline is all open jobs, then hard filters, then candidates, then a score
per candidate, then a ranked list with a freshness boost. The filters are being
built separately (KAN-170), so scoring comes first and takes whatever list of
candidates it is given.

**It must work for any field, not only software.** A hand-written skill
vocabulary was tried first and dropped, because it built computer science into
the matcher. Learning terms from the postings alone fails too: a scratch test on
the 1,096-job feed came back mostly equal-opportunity boilerplate ("race",
"religion") and company phrases ("giving insurers").

| Component | How | Status |
|---|---|---|
| Semantic similarity | Qwen3 embeddings (`qwen3-embedding:4b`, made on the team computer, KAN-726) of the posting and of the experience bank, compared in Postgres (`1 - (job.embedding <=> bank.embedding)`) | Built — `scoring.py`, queried in `queries/jobs/recommendations.py` |
| Skill overlap | Each distinct bank skill searched for in the posting on its own (`fts @@ plainto_tsquery(skill)`); the fraction found, never compared with other results | Built — `scoring.py`, queried in `queries/jobs/recommendations.py` |
| Title fit | Word overlap between the job title and the bank's Experience titles and first field of study, stop words removed | Built — `scoring.py` `title_fit()` |
| Eligibility | Years of experience check; an additive part (1.0 / 0.5 / 0.0), never a gate | Built — `scoring.py` `eligibility()` |
| Freshness | `max(0.7, 1.0 - 0.3 * days_old / 300)`, future dates count as today — newer postings rank higher, old ones don't drop below 70% | Built — `scoring.py` `freshness()` |

Nothing in this folder may assume what a software job is. Two consequences:

- **No "missing skill" caveats yet.** They need each job's own skill list, which
  only a taxonomy covering every field (ESCO, O*NET) can supply.
- **When other fields arrive:** leave soft skills out ("communication" is on
  every resume), and treat required licenses (RN, CPA, CDL) as eligibility, not
  skills.

## Embeddings — `embeddings.py`

- **One model, on one machine** (KAN-726,
  `../../../../docs/scraper_gh_action/plan.md`). Vectors from two models
  can't be compared, so every job and bank vector is Ollama's
  `qwen3-embedding:4b`, cut to `dto.EMBEDDING_DIMENSIONS` (768), made only on
  the team computer: its scheduled import embeds jobs and its bank job
  (`app/scripts/embed_banks.py`) embeds banks. Every other machine (the
  deployed API, the job alerts, laptops) keeps the default provider `none`
  and only reads vectors. Before this, laptops wrote Nomic vectors and the
  job alerts Gemini ones into the same columns; migration `e8c3f1a7b925`
  cleared them all.
- **Changing either one changes the database too.**
  - A new size needs a migration changing both columns' type (`ALTER COLUMN
    embedding TYPE extensions.vector(N) USING NULL`).
  - A new model at the same size requires clearing both columns before vectors
    from the new model are written; there is no model-provenance column.
  - A wrong size fails loudly: Postgres refuses the vector. A new model next to
    old vectors fails **silently**: the scores are wrong and nothing errors.
  - After either, the import re-embeds every job, and the migration also
    sets every `experience_banks.embedding` to NULL, so the bank job
    re-embeds each bank (`e8c3f1a7b925` is the pattern).
  - **A longer vector is cut, not refused** (`_shortened`): Qwen3's 4B
    answers 2,560 values, and its Matryoshka training makes the first 768
    stand alone; they are scaled back to length 1. A model without that
    training would need a migration to its own width instead.
- **Providers, picked by `EMBEDDING_PROVIDER`, each called through
  httpx.** `none` (the default) embeds nothing and sends nothing: `embed()`
  returns `None` at once, as for a provider that is down. `ollama` calls
  Ollama's native `/api/embed`, at `http://localhost:11434` unless
  `OLLAMA_EMBEDDING_URL` says otherwise, with `OLLAMA_EMBEDDING_MODEL`
  (`qwen3-embedding:4b`; `ollama pull qwen3-embedding:4b`). `gemini` calls
  Gemini's native REST API (`batchEmbedContents`): the OpenAI-compatible
  endpoint documents neither the vector size nor batching. This keeps
  `workit_scout/llm.py` the only module that imports `openai`. Gemini's key
  travels in the `x-goog-api-key` header, so it never shows up in a logged
  URL. Every writer to one database must use the same provider and model.
- **A bank is embedded as a query** (`embed(..., query=True)`): Ollama gets
  `OLLAMA_EMBEDDING_QUERY_PREFIX`, a one-line task, before each bank text,
  since Qwen3 embeds the asking side better with one. A posting never gets
  it. Both bank paths pass it; a new one must too.
- **`embed()` takes at most `BATCH_SIZE` (100) texts and never raises on a
  provider failure.** No key, a refusal (429 is Gemini's free-tier quota), an
  unreachable provider or a malformed response all return `None`. The caller
  stores nothing and tries again later, and a job or bank without a vector
  scores neutral on meaning. An upload or an import must never fail because
  the provider is down.
- **Only the bank's text and public postings are sent**, never identity data
  (name, email, phone, address, links). That is Scout's rule
  (`../../../../scout/CLAUDE.md`), because Gemini's free tier may train on what
  it receives. `bank_input.bank_text()` is where that boundary lives (below).
- **A posting is embedded from its title and the sections that say what the
  job is** (`job_text`, KAN-229): Overview, Responsibilities,
  Requirements and Preferred Qualifications. The scraper stores a description
  under those fixed headings, each alone on its line, with legal text left
  out (`../../../../scraper/docs/sections.md`). Pay and Details are stored but
  not embedded, and so is the intro when there is an Overview. **Benefits, How
  to Apply and About the Company** come last, for the job posting's page
  (2026-10-18): `_matched_part` stops at their headings, and `job_part`, which
  the keywords (`services/keywords.py`) and Tailor (`services/tailor.py`) read
  too, never includes them, so a perks list never steers a match, a keyword or
  a tailored resume. A description with only an intro under none of the job's
  headings reads the intro alone, never the perks after it. Without one,
  the intro is embedded first: it is where most such postings state the role
  ("Garda is seeking a Software Engineer Intern..."). Left out always, it cost
  52 role and requirement lines in the scraper's 50 gold postings, more than
  the old 6,000-character cut did (PR review, 2026-10-17). A description with
  none of those exact lines (the scraper's whole-text fallback) is embedded
  whole; one stored before KAN-229 that uses such a word as a heading of its
  own is read from that line. **The headings are part of the feed's
  contract**: renamed in the scraper alone, every posting quietly embeds its
  whole description again.
- **Texts are cut to 6,000 characters**, a limit kept from Nomic, which
  read about 2,048 tokens. Qwen3 reads far more; raising the cut changes
  every vector, so it waits for a reason.

## When things are embedded

- **Jobs: ahead of time, by the import.** Each scheduled run embeds only the
  new or changed postings (embedding IS NULL), never inside a user's request.
  Embedding on request would make the first person after each import wait
  for hundreds of vectors. Embedding runs **after** the import transaction
  commits, so the upsert stays fast and a dry-run never calls the provider. A
  changed job's embedding is cleared in the upsert's `set_` dict, so it gets
  a fresh vector. Each batch of 100 is committed independently; if the
  provider goes down mid-run, the next scheduled run picks up the rest.
- **Banks: by the bank job, soon after each change** (KAN-726,
  `app/scripts/embed_banks.py`). Every entry, bullet or skill change keeps
  the vector and marks it stale (`services/bank.py`'s `clear_embedding`:
  only `updated_at` moves), and its commit sends `pg_notify` on
  `bank_dirty`. The job on the team computer listens, waits a minute for
  more, then embeds every stale bank, ones with no vector first; it also
  sweeps on start, on reconnect and every 6 hours. Only one job works at a
  time (a Postgres advisory lock on its listening connection); another
  waits on standby. Recommendations score on
  the stale vector meanwhile: clearing it, as before, scored the student
  with no semantic part at all until the next embed.
- **A stale bank is one whose `updated_at` moved past `embedded_at`**
  (`bank_vectors.STALE`), or one with no vector. `embedded_at` is the bank
  version the vector was made from (its `updated_at` when read), not the
  time of the write: a change whose transaction began before the write and
  committed after it would carry an earlier time and look embedded.
- **A recommendations request embeds only a bank with no vector**, and only
  where its process has a provider; the deployed API's is `none`, so it
  embeds nothing and reads what the job stored. Its call has a 10-second
  timeout (`REQUEST_EMBED_SECONDS`), so a provider that is down costs
  seconds, not the request.
- **A vector is stored only for the version read** (`bank_vectors.store`):
  the write is conditional on `updated_at` still being the value read, so a
  change that landed while the model ran leaves the bank stale, and its
  notify brings it back. **Storing keeps `updated_at` as it was** (KAN-425):
  `updated_at` is the bank's last change, and Home's kept matches are
  keyed on it, so a bump there made the first return after every bank
  change score again (`tests/test_recommended.py` caught it).
- **An empty bank (no entries, no skills) answers 404** and costs no call.

## What the recommender reads from the bank — `bank_input.py`

Pure functions over a loaded `services.bank.Bank` (KAN-212). Only the data
the recommender reads changed; the scoring did not.

- **`bank_text()`, the embedding input**, in order: skills; each Experience and
  Projects entry's section, title and organization with its original
  bullets, newest first across the two (Present first, then by end month).
  Education and the other sections stay out (KAN-254). Never a bullet
  variant, a link, a location, a grade or a date. The
  text then passes through `workit_scout.identity` with the profile's
  identity fields (`identity=` is required, with no empty default, so a
  caller cannot skip loading the profile), and is cut at 6,000 characters, so the oldest entries go
  first. One embedding per bank; per-entry embeddings are out of scope until
  matches prove poor.
- **Years of experience** sum Experience entries only (Leadership, Projects
  and the rest never count), both end months included (Jun to Aug is three
  months). Present counts up to this month, an end still to come is cut at
  this month, and an entry with no start month adds nothing.
- **The expected graduation date** is the latest end month on any Education
  entry, past or expected. It is computed and passed to `eligibility()`,
  which does not compare it yet (Still open).

## Candidates

`GET /jobs/recommended` applies `GET /jobs`' filters (`matching()` in
`queries/jobs/filters.py`), the hard-filter stage, then `score_jobs`
(`queries/jobs/recommendations.py`) scores at most `CANDIDATES` (500) of what
is left: the nearest to the bank by embedding, ordered in SQL with jobs that
have no vector last, or the newest when the bank has no vector. Python scoring never runs over
the whole feed.

- **The query ranks on the vector alone, then reads the picked rows whole**
  (KAN-425). A subquery reads each filtered job's id, distance and posting
  date and ranks them; only the kept rows are joined back for the listing
  columns and the skill text search. With the skills in the ranking query,
  Postgres ran every skill's search on every listed job before the cap,
  reading each posting's text once per skill (438,713 buffers against
  52,803), and a pass took 10 to 15 s on the shared database instead of 4
  to 6. Keep anything costly per row out of the ranking subquery.
- **`score_job_sets` serves several candidate sets from one scan**: each
  named set is a condition on top of the filters, ranked and capped on its
  own (a window per set), so each list equals what its own `score_jobs`
  call returns, and a job in two sets is scored once. `score_jobs` is the
  one-set case.
- **Home asks once** (`GET /jobs/recommended/{id}/home`,
  `queries/jobs/home.py`): the top `limit`, the top `limit` auto apply
  fills, and the posting dates of the recent ones scoring at least
  `min_match`. The result is kept in the process for `HOME_CACHE_SECONDS`
  (600) under the bank's `updated_at`, the newest `job_postings.updated_at`
  (every import write, embedding and closing sets it) and a hash of the
  applicant's applied jobs; any change there is a new key. Only Home reads
  the kept result: `fetch_recommended` and auto apply's callers score
  fresh every time, as before.
- **The scan itself is the cost, and the shared database's compute sets
  it.** 18,000 vectors took 4.4 to 6.7 s there with every page in memory,
  and 22 to 43 ms on a laptop's Postgres (2026-10-28). An HNSW index is no
  answer at this size (Still open). The cost of the cap: a job ranked past it by semantic alone
can't surface on its skills or title. The Jobs page's Best Match order sends
its filter row's picks as those filters: the seeker's saved preferences on a
fresh visit (KAN-231, KAN-288).

## The columns

`job_postings.embedding` and `experience_banks.embedding` are `vector(768)`, and
`job_postings.fts` is a generated `tsvector`. `../../models/CLAUDE.md` has the
details, including why their migration must reach the database **before** the
code that maps them is deployed.

## Configuration

Only the team computer sets `EMBEDDING_PROVIDER=ollama`, with Ollama at
`OLLAMA_EMBEDDING_URL` and `qwen3-embedding:4b` pulled. If Ollama is
unavailable, embedding returns no vector, and the import and the bank job try
again on their next run. Tests: `tests/test_embeddings.py`,
`tests/test_embed_banks.py`, the notify in `tests/test_bank.py`.

## Scoring — `scoring.py`

Pure functions, no DB access. Weights: `W_SEMANTIC=0.45`, `W_SKILL=0.25`,
`W_TITLE=0.15`, `W_ELIGIBILITY=0.15`. When no embedding exists, semantic
weight is redistributed across the others. Final score is
`round(weighted_sum * freshness * 100)`, clamped 0-100. `compute_breakdown()`
returns each part's weight and points too, sent as `score_breakdown`; equal
scores sort by the unrounded score, then job id.

## Highlights — `highlights.py`

Takes the bank's skill names and field of study. Picks up to 3 reasons from a
priority list: the skills the posting mentions (only those), title alignment,
strong semantic fit (positive), then years mismatch and start term mismatch
(negative). Positives sort before negatives, and a negative is never cut by
the cap of 3.

**Each highlight is a short label and its sentence** (2026-11-09): `text`
is a few words that fit one line of a card's match rail ("Uses 3 of your
skills", "Fits your major", "Asks for 5+ years"), and `detail` is the whole
sentence ("Posting mentions your skills: Python, SQL, Go"), the label's
tooltip. The rail showed the sentences until then, which wrapped to four
lines and were cut short once it limited each reason to two.

**A job none of those rules speak for gets caveats** (KAN-256), so a weak
score never shows with no reasons, on the Jobs page card or the application
page: "No skills in common" when the bank has skills and the posting
mentions none, and "Unlike your past roles"
when the title fit is 0.3 or less and the bank has titles or a field of
study to compare (`has_titles`; without them a low fit is a blank, not a
finding). Neither names a skill the job wants: that is the "missing skill"
caveat above, which needs each job's own skill list.

## Recommendations — `fetch_recommended()` and `GET /jobs/recommended/{applicant_id}`

Both in `routers/jobs.py`. `fetch_recommended(db, account, filters=,
min_match=, limit=, offset=)` loads the experience bank, has
`queries/jobs/recommendations.py`'s `score_jobs` score and sort the jobs,
then applies `min_match` and the page; it returns `list[ScoredJob]`, best
first. The route checks ownership and calls it. Python code that needs
recommendations (auto apply's queue) calls the function, not the route. It
checks no ownership itself, so its caller must.

It scores against the **experience bank**, never an uploaded resume. It takes
the account, not only its id, because the bank's embedding text reads the
student's identity (`load_identity`). A bank with no entries and no skills
raises `EmptyBank`, which the route answers as a 404.

- **It scores every listed job each call, then sorts and slices**, and
  keeps nothing between calls (Home's kept result is its own route's). Every
  query parameter that narrows the list (the Jobs page's filters,
  `min_match`) applies before `offset`, so a page never comes back short with
  more matches behind it.
- **`min_match` (0–100, default 0)** drops jobs scored below it. Auto apply
  asks for 60 (`auto-apply/architecture.md`, "Match (built)"). It moves with the
  weights: retune it when they change.

## Still open

- **An HNSW index on `job_postings.embedding` is not worth it yet**
  (assessed 2026-10-28, KAN-425). On a laptop Postgres 17 with pgvector
  0.8.2 (the shared database's version), 18,000 vectors: the exact top 500
  took 22 to 43 ms, HNSW with `hnsw.iterative_scan = relaxed_order` 22 to
  75 ms, and HNSW found 428 of the exact 500 (random vectors, its worst
  case). So the index saves little at this size and changes which jobs
  reach the cap. It also needs the query rewritten to `ORDER BY embedding
  <=> :vec` ascending with a `LIMIT` per set (today's ranking window never
  uses an index), a second read for the jobs with no vector, and a build of
  about 27 s locally. Storing the vectors inline (`SET STORAGE PLAIN`, then
  rewriting the rows) cut the exact scan by a third locally, and moved the
  vectors into the table's own pages (70 MB there, against 1.2 MB with them
  out of line). Look first at the database's compute (the same scan is 100
  times slower there than on a laptop), and revisit HNSW past about 100,000
  postings. A migration for it was written and checked with `--sql`, never
  applied or committed: `CREATE INDEX CONCURRENTLY ... USING hnsw (embedding
  extensions.vector_cosine_ops)` in an autocommit block.

- **Applying the migration that creates the columns.** It's `4485d7a7a712`,
  and it goes on the shared database right after its PR merges, before the
  deployment is live (`../../models/CLAUDE.md` says why).
- **Overlapping Experience dates count twice** in the bank's years of
  experience (`bank_input.years_of_experience`). `scoring.experience_years()`
  merges overlaps but reads a parsed resume, so the bank does not use it yet.
- **Scoring weights and the freshness boost** are guesses until there is real
  data to tune them on.
- **Grad date vs start term** is not compared yet. The bank's expected
  graduation date reaches `eligibility()`, which only checks years of
  experience; comparing it is a scoring change, out of KAN-212's scope.
