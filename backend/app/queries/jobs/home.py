"""
Home's matches (KAN-425): Top Matches, the ones auto apply can fill, and the
Excellent Matches posting dates, from one scoring pass, kept per applicant
until something they depend on changes.

ONE PASS, NOT THREE. Home asked GET /jobs/recommended three times at once
(the top 12, the top 12 auto apply fills, and every recent Excellent Match a
page of 500 at a time), and the tracker scored a fourth. score_job_sets
picks every set's candidates in one statement and reads and scores each job
once, so each list is the one its own GET /jobs/recommended call returns.

KEPT UNTIL IT GOES STALE (queries/jobs/kept.py has the key): the route
serves KEPT while the bank, the job postings and the applicant's Tracker
are as they were, for at most HOME_CACHE_SECONDS.
"""

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import Job_Post
from app.queries.jobs.filters import AUTO_APPLY_SUPPORTED, JobFilters
from app.queries.jobs.kept import Kept
from app.queries.jobs.recommendations import score_job_sets
from app.schemas.auth import AuthenticatedAccount
from app.schemas.jobs import HomeMatches
from app.services.bank import Bank

# How long a kept result may be served when nothing in its key changed.
HOME_CACHE_SECONDS = 600
# The most applicants kept at once; the least recently read goes first.
HOME_CACHE_SIZE = 256

KEPT: Kept[HomeMatches] = Kept(HOME_CACHE_SECONDS, HOME_CACHE_SIZE)


async def home_matches(
    db: AsyncSession,
    account: AuthenticatedAccount,
    bank: Bank,
    *,
    posted_within: int,
    min_match: int,
    limit: int,
) -> HomeMatches:
    """Home's three lists from one scoring pass. Checks no ownership: the
    route has."""
    since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=posted_within)
    scored = await score_job_sets(
        db,
        account,
        bank,
        # The tracked jobs (saved, applied and after) stay out, as GET
        # /jobs/recommended leaves them out for a signed-in applicant
        # (read_filters).
        JobFilters(tracked_by=account.id),
        {
            "top": None,
            "auto_apply": AUTO_APPLY_SUPPORTED,
            "recent": Job_Post.posted_at >= since,
        },
    )
    return HomeMatches(
        top=scored["top"][:limit],
        auto_apply=scored["auto_apply"][:limit],
        strong_posted=[
            job.posted_at for job in scored["recent"] if job.match >= min_match and job.posted_at
        ],
    )
