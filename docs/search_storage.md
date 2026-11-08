# Freeing Supabase storage from search

KAN-735. A plan, written 2026-11-08; nothing here is built yet except where
a step says so. It is the storage half of KAN-726
(`docs/scraper_gh_action/plan.md`), which moved scraping and embeddings to
the team computer and made the database grow.

The goal: stay on Supabase's free plan (500 MB) instead of paying for Pro.

## What we found

Every number below was measured read-only on 2026-11-08, before the
backfills (`docs/scraper_gh_action/plan.md`, The backfills).

### The database is over the plan

| | Size |
| --- | --- |
| The whole database | 648 MB |
| `job_postings` | 609 MB |
| Every other table together | under 40 MB |

`job_postings` holds 58,818 scraped jobs, 47,649 of them listed. On disk:

| Part | Size |
| --- | --- |
| `fts`, the stored search column | 217 MB |
| `description` | 150 MB |
| Other columns | about 15 MB |
| Free space left by updated rows | about 135 MB (on disk minus live data minus indexes) |
| Indexes (`job_postings_fts_idx`, the GIN index on `fts`, is 60 MB) | 84 MB |

The free space comes from imports: Postgres writes a new copy of a row on
every update and marks the old one dead. Autovacuum makes that space
reusable inside the table, but it never gives it back to the disk.

### A table rewrite does not fit on the disk

`VACUUM FULL job_postings`, which would return the free space, failed
twice on 2026-11-08:

- In Supabase's SQL editor, it hit the editor's time limit and was
  cancelled.
- From the team computer, with no time limit, it failed with
  `DiskFullError: could not extend file ... No space left on device`.

A rewrite (`VACUUM FULL`, `pg_repack`, `CLUSTER`, or an `ALTER TABLE` that
recomputes a stored column) builds the whole new table before it drops the
old one, and writes all of it to the WAL as well. So it needs room for
the old table, the new copy and the WAL at once. Postgres rolled back, and
nothing was lost; the database stayed writable.

### The WAL grows with big writes

The failed rewrite left the WAL (write-ahead log, Postgres's record of every
change) at 672 MB, 43 files of 16 MB, more than the data itself. All of it
was archived by Supabase's backups, and no replication slot held it. Postgres
keeps old WAL files for reuse, up to `max_wal_size` (1 GB on this project),
and removes them a few at a time at each checkpoint (every 5 minutes) while
traffic is low, down toward `min_wal_size` (128 MB). Our database role
cannot run `CHECKPOINT`, and WAL files are never deleted by hand.

So every large write (a rewrite, the vector backfill) costs disk twice, in
the table and in the WAL, until the WAL shrinks again. Check Supabase's disk
usage before each one.

## What the stored search column is for

`job_postings.fts` is a generated, stored `tsvector`
(`a70c641b2f99_weighted_fts_and_its_index.py`):

```sql
setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
setweight(to_tsvector('english', coalesce(description, '')), 'D')
```

It holds every word of the title and description in a base form
("engineers" is "engineer"), with each word's positions in the text and a
weight (A for the title, D for the description).

Two features read it, and both only ask whether a job holds a word (`@@`):

- **Jobs page search** (`word_matches`, `queries/jobs/filters.py`): each
  word left after companies, roles and facts must be in the job's text or
  its company's name. Search orders nothing (`queries/jobs/search.py`).
- **Skill overlap in match scores** (`queries/jobs/recommendations.py`):
  each bank skill is checked against each of up to 500 candidate jobs per
  set; Home asks for three sets at once, so up to about 1,500 jobs a
  request.

Nothing reads the positions or the weights:

- No query ranks jobs with `ts_rank` on `fts`. The weights were added so a
  ranking would put title matches first; search never ranked.
- Tailor's `ts_rank` (`rank_bullets`, `rank_shown` in `services/tailor.py`)
  ranks the student's bullets, building their words from each bullet's text
  at request time. It never reads `job_postings.fts`.
- `plainto_tsquery` makes no phrase query, so `@@` needs no positions.

The column is a speed cache: both features need each job's words, which
come from about 4,300 characters of description (median 4,265, 90th
percentile 6,620). Stored, a check is cheap. Not stored, Postgres builds
the words from the description at each check.

## The options

Measured on all 58,818 jobs:

| | `fts` | Saving | Results | Speed | Work |
| --- | --- | --- | --- | --- | --- |
| Today | 217 MB | none | | | |
| **A. Strip positions and weights** | 136 MB | 81 MB | the same | the same | a migration |
| **B. Drop the stored column** | none | 217 MB | the same | slower unless the queries change | a migration, two queries, timing tests |
| Only the first 4,000 characters | 185 MB (118 MB stripped) | 32 to 99 MB | worse | the same | a migration |
| Drop the GIN index | 217 MB | 60 MB | the same | every search scans 47,000 jobs | a migration |

The last two are not taken: more than half the descriptions are longer than
4,000 characters, so a search or a skill named late in a posting would stop
matching; and without the index every search reads every listed job.

### Option A: strip positions and weights

The column stays, generated from `strip(...)`:

```sql
strip(to_tsvector('english', coalesce(title, '')) ||
      to_tsvector('english', coalesce(description, '')))
```

- **Search and match scores:** the same jobs match, at the same speed. `@@`
  with `plainto_tsquery` reads only which words a job has.
- **Code:** none. `Job_Post.fts` in `app/models/jobs.py` changes its
  `Computed` expression to match the migration.
- **Migration:** drop and add the column (a generated column's expression
  cannot be altered in place on every Postgres version, as
  `a70c641b2f99` notes), then rebuild `job_postings_fts_idx`. Adding a
  stored generated column rewrites the table: the new copy is about 385 MB
  plus its WAL, which does not fit until the WAL has shrunk and the disk
  has room.
- **Lost:** a later feature that ranks jobs by text, or searches phrases,
  would need the positions back. Nothing does today.

### Option B: drop the stored column, keep the index

The column goes; the GIN index is built on the same expression instead
(`CREATE INDEX ... USING gin ((<expression>))`), so the index stays about
60 MB.

- **Search:** the same matches. A query uses the index only if it writes
  the index's exact expression, so `word_matches` changes to that
  expression. When Postgres walks jobs newest first and checks each one
  instead of using the index, every check builds the words from the
  description: a rare word could make a search much slower.
- **Match scores:** the skill overlap must build each candidate's words
  once, not once per skill (a subquery or `LATERAL`), or a student with 20
  skills makes Home take seconds. Even once, it adds an estimated 0.1 to
  0.5 seconds to Home and Best Match on Supabase's shared CPU. Measure it
  before deciding.
- **Code:** `filters.py`, `recommendations.py`, `models/jobs.py` (the
  column and its index), `docs/search.md`, and the matching CLAUDE.md.
- **Migration:** `DROP COLUMN` is instant but frees nothing until the table
  is rewritten; the rewrite's new copy is about 250 MB plus its WAL, the
  smallest of any option.

### Which one

A is the safe choice: no change to results or speed, a migration only.
B saves 136 MB more, at the cost of request time on every Home and Best
Match load, and it is the one whose rewrite is most likely to fit.

## The other storage steps

From KAN-726's plan, largest saving first:

1. **Return the free space** (`VACUUM FULL` or `pg_repack`, about
   135 MB): blocked by disk, as above. Postgres reuses that space for new
   rows anyway, so the vector backfill for listed jobs (about 145 MB) fills
   mostly free space and grows the file little.
2. **The search column**: options A and B above.
3. **Embed listed jobs only**, and clear a job's vector when it closes
   (about 33 MB). **Built** in KAN-726 (PR #494): `_embed_jobs` reads
   published jobs only, `_close_missing` clears the vector, and a job that
   comes back counts as changed, so its run embeds it again.
4. **`halfvec(768)`**: half precision halves every vector (about 70 MB for
   the listed jobs) with almost no change in scores. A migration on both
   vector columns and their casts; best before the vector backfill.
5. **Retention for closed jobs**: delete closed jobs no application names
   after some days, through the retention purge (`services/retention.py`,
   and the privacy policy's retention section with it). About 70 MB today,
   and the only step that stops the table growing with every close.

What the backfills add if nothing changes: keywords about 650 bytes a job
(about 30 MB for every listed job), vectors about 3 KB a job (about
145 MB for the listed jobs).

## Order

1. Wait for the WAL to shrink; check Supabase's disk usage.
2. Decide A or B, and whether `halfvec` goes in the same migration (one
   rewrite instead of two).
3. Write the migration and code on this ticket's branch; apply it to a
   local Postgres first (`backend/alembic/CLAUDE.md`), and time search and
   Home for B.
4. Apply it to the shared database at a quiet time, between scrapes, by a
   person, with the disk checked first. The rewrite locks `job_postings`
   while it runs.
5. Then the vector backfill, in parts (`--embed-limit 5000`), checking the
   disk between parts.
