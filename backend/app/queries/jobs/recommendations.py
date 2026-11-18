"""
GET /jobs/recommended's scoring: the feed's jobs, narrowed by the same
filters, scored against one experience bank and sorted best first. The
scores themselves are services/matching's (its CLAUDE.md); this reads the
columns they need and embeds the bank on demand.

TWO READS (KAN-915). The first picks each set's CANDIDATES ids: the nearest
to the bank from the HNSW index over the job vectors (c48811c7e5af), never
by reading every listed job's vector. The second reads only those rows, by
primary key, with each posting's search terms read once for all the skills.
On 2026-11-18 one statement did both, reading all 41,489 vectors from TOAST
(45 s) and each candidate's terms once per skill (258 skills, 4 to 8 s):
a pass took 69 to 77 s on the shared database.
"""

import datetime
import uuid
from collections.abc import Mapping

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import case, cast, func, literal, select, text, union_all
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from app.models import dto
from app.models.bank import Experience_Bank
from app.models.jobs import Job_Post
from app.queries.jobs.filters import LISTED, JobFilters, matching
from app.queries.jobs.listings import LISTING_COLUMNS, to_listing
from app.schemas.auth import AuthenticatedAccount
from app.schemas.jobs import Highlight, ScoredJob
from app.services.bank import Bank
from app.services.identity import load_identity
from app.services.matching import bank_input, bank_vectors
from app.services.matching.bank_input import bank_text
from app.services.matching.embeddings import embed
from app.services.matching.highlights import generate_highlights
from app.services.matching.scoring import (
    compute_breakdown,
    eligibility,
    freshness,
    title_fit,
)

# How many filtered jobs are scored per request. They are the nearest to the
# bank by embedding (or the newest, with no vector), picked in SQL, so the
# Python scoring below never runs over the whole feed.
# ponytail: a fixed cap; a job ranked past it by semantic alone can't surface
# on its skills or title. Raise it, or pre-score skills in SQL, if that bites.
CANDIDATES = 500
# A posting with more required skills than this is not penalised for the excess.
SKILL_CEILING = 12

# Each job vector as the HNSW index holds it (c48811c7e5af): a halfvec, so
# an ORDER BY on this distance reads the index. Spelled as the index is, or
# the planner can't match it.
JOB_HALF = cast(Job_Post.embedding, HALFVEC(dto.EMBEDDING_DIMENSIONS))
NEWEST = Job_Post.posted_at.desc().nulls_last()

# Read the nearest from the index, whatever the filters. With enable_sort off
# the planner never takes "read every filtered job, then sort", which it
# prices as cheap because it can't see that each vector is a TOAST read
# (3 KB, out of line). The iterative scan keeps reading the index until
# LIMIT rows pass the filters, or hnsw.max_scan_tuples (20,000) were read;
# then the set comes back short and is ranked exactly (_candidates). LOCAL,
# and put back at once, so no other statement in the request is planned
# without sorts.
_INDEX_ORDER = text(
    "SELECT set_config('enable_sort', 'off', true),"
    " set_config('hnsw.iterative_scan', 'relaxed_order', true)"
)
_PLANNER_DEFAULTS = text(
    "SELECT set_config('enable_sort', 'on', true),"
    " set_config('hnsw.iterative_scan', 'off', true)"
)

# The bank embed inside a request: short, so a missing or slow provider
# degrades to scoring without the semantic part instead of hanging the
# function (matching/CLAUDE.md).
REQUEST_EMBED_SECONDS = 10.0


async def _bank_embedding(db: AsyncSession, account: AuthenticatedAccount, bank: Bank) -> list[float] | None:
    """The bank's stored embedding, even when stale: the bank job on the team
    computer replaces it (KAN-726). Only a bank with no vector yet is
    embedded here, and only where this process has a provider: the deployed
    API's is `none` (the default), so it reads and never embeds.
    None when there is no bank row or no vector."""
    bank_row = await db.get(
        Experience_Bank, account.id, options=[undefer(Experience_Bank.embedding)]
    )
    if bank_row is None or bank_row.embedding is not None:
        return bank_row.embedding if bank_row else None
    text = bank_text(bank, identity=await load_identity(db, account))
    vectors = await embed([text], timeout=REQUEST_EMBED_SECONDS, query=True) if text else None
    if not vectors:
        return None
    await bank_vectors.store(db, account.id, bank_row.updated_at, vectors[0])
    try:
        await db.commit()
    except Exception:
        await db.rollback()
    return vectors[0]


async def score_jobs(
    db: AsyncSession, account: AuthenticatedAccount, bank: Bank, filters: JobFilters
) -> list[ScoredJob]:
    '''
    every job these filters keep, scored against this bank, best first.
    Jobs without embeddings still appear, scored on the other components
    '''
    return (await score_job_sets(db, account, bank, filters, {"all": None}))["all"]


async def score_job_sets(
    db: AsyncSession,
    account: AuthenticatedAccount,
    bank: Bank,
    filters: JobFilters,
    sets: Mapping[str, ColumnElement[bool] | None],
) -> dict[str, list[ScoredJob]]:
    '''
    the jobs these filters keep, scored against this bank, best first, once
    per named set: a set is the jobs its condition also keeps (None: all of
    them), each capped at CANDIDATES as score_jobs caps one. One statement
    picks every set's candidates, and a job in two sets is read and scored
    once: Home asks for its three lists at once (home_matches).
    '''
    bank_embedding = await _bank_embedding(db, account, bank)

    # Deduplicate case-insensitively so repeated skills cannot change the score.
    skills = list({s.strip().casefold(): s.strip()
                   for s in bank_input.skills(bank) if s.strip()}.values())

    picked = await _candidates(db, filters, sets, bank_embedding)
    ids = list({job_id for set_ids in picked.values() for job_id in set_ids})
    rows = await _read(db, ids, bank_embedding, skills) if ids else []

    now = datetime.datetime.now(datetime.UTC)
    titles = bank_input.titles(bank)
    field_of_study = bank_input.field_of_study(bank)
    years_exp = bank_input.years_of_experience(bank, now.date())
    graduation = bank_input.expected_graduation(bank)

    by_id: dict[uuid.UUID, ScoredJob] = {}
    for row in rows:
        semantic_val = row.semantic
        matched_skills = [skill for skill in (row.matched_skills or []) if skill is not None]
        skill_norm = (
            min(1.0, len(matched_skills) / min(len(skills), SKILL_CEILING))
            if skills else 0.0
        )
        t_fit = title_fit(row.title, titles, field_of_study)
        days_old = (now - row._posted_at).total_seconds() / 86400 if row._posted_at else 30.0
        fresh = freshness(days_old)
        elig = eligibility(
            graduation, row.start_term, row.min_years_experience, years_exp
        )
        breakdown = compute_breakdown(semantic_val, skill_norm, t_fit, elig, fresh)
        highlights = generate_highlights(
            row.title, row.min_years_experience, row.start_term,
            skills, field_of_study, semantic_val, skill_norm, t_fit, elig,
            matched_skills=matched_skills,
            has_titles=bool(titles or field_of_study),
        )

        listing = to_listing(row)
        by_id[row.id] = ScoredJob(
            **listing.model_dump(exclude={"match", "highlights"}),
            match=breakdown.final_score,
            score_breakdown=breakdown,
            highlights=[Highlight(**h) for h in highlights],
        )

    # A job that closed between the two reads is left out of every set.
    scored = {
        name: [by_id[job_id] for job_id in set_ids if job_id in by_id]
        for name, set_ids in picked.items()
    }
    # Best first; ties broken by the unrounded score, then id, so pages are stable
    for jobs in scored.values():
        jobs.sort(key=lambda s: (-s.match, -s.score_breakdown.score_before_rounding, s.id))
    return scored


async def _candidates(
    db: AsyncSession,
    filters: JobFilters,
    sets: Mapping[str, ColumnElement[bool] | None],
    bank_embedding: list[float] | None,
) -> dict[str, list[uuid.UUID]]:
    '''
    each set's CANDIDATES ids: the nearest to the bank, or the newest when
    the bank has no vector. From the HNSW index (no TOAST read but the
    vectors' own pages) unless the filters name their jobs (job_ids: the
    feed's 50, one job's page), which are few enough to rank exactly. A set
    the index can't fill (fewer jobs than the cap, or too few near the bank
    for the scan to reach) is ranked exactly over its own jobs, which then
    also brings in the jobs with no vector, after the rest, as before.
    '''
    where = {
        name: [LISTED, *matching(filters), *(() if cond is None else (cond,))]
        for name, cond in sets.items()
    }
    if bank_embedding is None:
        return await _ids(db, {
            name: select(Job_Post.id).where(*w).order_by(NEWEST, Job_Post.id).limit(CANDIDATES)
            for name, w in where.items()
        })
    if filters.job_ids is not None:
        return await _ids(db, {name: _nearest_exactly(w, bank_embedding) for name, w in where.items()})

    nearest = JOB_HALF.cosine_distance(bank_embedding)
    await db.execute(_INDEX_ORDER)
    picked = await _ids(db, {
        name: select(Job_Post.id).where(*w).order_by(nearest).limit(CANDIDATES)
        for name, w in where.items()
    })
    await db.execute(_PLANNER_DEFAULTS)
    short = {
        name: _nearest_exactly(where[name], bank_embedding)
        for name, set_ids in picked.items()
        if len(set_ids) < CANDIDATES
    }
    if short:
        picked |= await _ids(db, short)
    return picked


def _nearest_exactly(where: list[ColumnElement[bool]], bank_embedding: list[float]) -> Select:
    '''
    the CANDIDATES nearest of these jobs by every one's full vector, read
    from TOAST: the jobs with no vector last, newest first. Ordered by the
    similarity, which no index serves, so it is never the index's guess.
    '''
    semantic = literal(1.0) - Job_Post.embedding.cosine_distance(bank_embedding)
    return (
        select(Job_Post.id)
        .where(*where)
        .order_by(semantic.desc().nulls_last(), NEWEST, Job_Post.id)
        .limit(CANDIDATES)
    )


async def _ids(db: AsyncSession, queries: Mapping[str, Select]) -> dict[str, list[uuid.UUID]]:
    '''
    each named query's ids, from one statement: each query runs as its own
    subquery, keeping its ORDER BY and LIMIT, under UNION ALL
    '''
    parts = []
    for name, query in queries.items():
        sub = query.subquery()
        parts.append(select(literal(name).label("set_name"), sub.c.id))
    statement = parts[0] if len(parts) == 1 else union_all(*parts)
    picked: dict[str, list[uuid.UUID]] = {name: [] for name in queries}
    for row in await db.execute(statement):
        picked[row.set_name].append(row.id)
    return picked


async def _read(
    db: AsyncSession,
    ids: list[uuid.UUID],
    bank_embedding: list[float] | None,
    skills: list[str],
) -> list:
    '''
    the picked jobs' listing columns, similarity and the skills each one's
    text names, read by primary key. Still listed: one can close between
    the two reads.
    '''
    semantic = (
        literal(1.0) - Job_Post.embedding.cosine_distance(bank_embedding)
        if bank_embedding is not None
        else literal(None)
    )
    picked = (
        select(
            *LISTING_COLUMNS,
            semantic.label("semantic"),
            # posted_at for freshness
            Job_Post.posted_at.label("_posted_at"),
            # The posting's terms without positions, which plainto_tsquery's
            # AND of words never reads, read from TOAST into memory once.
            func.strip(Job_Post.fts).label("_terms"),
        )
        .where(Job_Post.id.in_(ids), LISTED)
        # OFFSET 0 keeps Postgres from folding this into the select below,
        # which would put Job_Post.fts back in each skill's match and read
        # the row's terms from TOAST once per skill (KAN-915: 129,000 reads
        # for 258 skills on 500 rows).
        .offset(0)
        .subquery("picked")
    )
    terms = picked.c._terms
    # Match skills independently, so partial coverage earns credit. This is
    # independent of other results and remains stable when filters change.
    if skills:
        skill_matches = array([
            case((terms.bool_op("@@")(func.plainto_tsquery("english", skill)), literal(skill)), else_=None)
            for skill in skills
        ]).label("matched_skills")
    else:
        skill_matches = literal(None).label("matched_skills")
    columns = [column for column in picked.c if column.key != "_terms"]
    return list((await db.execute(select(*columns, skill_matches))).all())
