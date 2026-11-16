"""
KAN-298's daily digest: one applicant's best new matches, as one bell
notification and one email, from one computed list -- never scored twice.
Reuses auto apply's own matching and batch-picking rather than a second
implementation (auto-apply/architecture.md, "Match (built)" and "The
batch"): `fetch_recommended` scores every listed job against the
experience bank, `pick_batch` takes the best `BATCH_SIZE` keeping one
posting per company+title. Unlike auto apply's own batch, this never
restricts to Greenhouse: a digest links to WorkIt's own job page, never
`apply_url`, so it needs no ATS-specific knowledge at all.

The one caller is app/scripts/send_job_alerts.py.
"""

import logging
import re
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_apply.pipeline import BATCH_SIZE, MIN_MATCH
from app.auto_apply.rules import pick_batch
from app.config import get_settings
from app.models.jobs import Job_Post
from app.models.notification import Notification
from app.queries.jobs.filters import JobFilters
from app.routers.jobs import EmptyBank, fetch_recommended
from app.schemas.auth import AuthenticatedAccount
from app.schemas.jobs import ScoredJob
from app.services.email import send_email
from app.services.notices import is_suppressed

logger = logging.getLogger(__name__)


async def build_digest(db: AsyncSession, account: AuthenticatedAccount) -> list[ScoredJob]:
    """This applicant's best new matches, best first, up to BATCH_SIZE, one
    per company+title. Raises EmptyBank for an account with nothing to
    score against -- the caller skips it, the same way every other
    fetch_recommended caller does."""
    scored = await fetch_recommended(
        db,
        account,
        # Every job with an application at any stage stays out, the same
        # rule auto apply's own batch follows: a digest that kept nagging
        # about a job the student already applied to, skipped or even just
        # saved would train them to ignore it.
        filters=JobFilters(no_application_by=account.id),
        min_match=MIN_MATCH,
        # Every match, not a page: pick_batch drops repeats before it takes
        # BATCH_SIZE, same reasoning auto_apply/pipeline.py's own _matches
        # uses this exact limit for.
        limit=sys.maxsize,
    )
    return pick_batch(scored, BATCH_SIZE)


def _title(count: int) -> str:
    """The digest's heading, in the bell and the email alike: one job is
    one match ("Your 1 Best Match Today"), never "1 Best Matches"."""
    return f"Your {count} Best {'Match' if count == 1 else 'Matches'} Today"


# Band colors copied from frontend/src/app/globals.css's --color-match-* tokens
# (frontend/CLAUDE.md, "A match score is red, orange, yellow or green"), so the
# digest's badge reads the same as the Jobs page's ring.
_MATCH_BANDS = (
    (80, "#139564"),  # excellent
    (65, "#b98600"),  # good
    (40, "#d9620d"),  # fair
)
_MATCH_WEAK = "#c02a3d"


def _match_color(match: int) -> str:
    for floor, color in _MATCH_BANDS:
        if match >= floor:
            return color
    return _MATCH_WEAK


# Only two facts the scraper actually states, as short tags (never an
# "industry" guess: WorkIt stores no such field, see job_alerts.py's module
# docstring note below).
_WORK_STYLE_LABELS = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}
_JOB_TYPE_LABELS = {
    "full_time": "Full-Time",
    "part_time": "Part-Time",
    "contract": "Contract",
    "internship": "Internship",
}


# A degree level is the same kind of field WorkIt stores nowhere (KAN-790):
# no column, no migration -- this reads the posting's own description text
# live instead of adding one. Only an explicit "degree"/"pursuing" phrase
# right next to the level counts, so a miss (no tag) is far likelier than a
# wrong one; a posting that just mentions "PhD" in passing (a founder's bio,
# a lab name) gets no tag. Checked highest first: a posting naming several
# levels usually reads "PhD preferred, Master's considered," and the
# strongest ask is the one worth showing.
_DEGREE_LEVELS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PhD", re.compile(r"\b(ph\.?d\.?|doctoral)\s+(degree|candidate|student)s?\b|pursuing\s+(a|your)\s+ph\.?d\b", re.IGNORECASE)),
    ("Master's", re.compile(r"master'?s\s+degree\b|pursuing\s+(a|your)\s+master'?s\b", re.IGNORECASE)),
    ("Bachelor's", re.compile(r"bachelor'?s\s+degree\b|pursuing\s+(a|your)\s+bachelor'?s\b|undergraduate\s+degree\b", re.IGNORECASE)),
)


def _degree_label(description: str | None) -> str | None:
    if not description:
        return None
    for label, pattern in _DEGREE_LEVELS:
        if pattern.search(description):
            return label
    return None


async def _fetch_descriptions(db: AsyncSession, job_ids: list[str]) -> dict[str, str]:
    """The picked batch's own description text, by job id -- fetched once
    here rather than widening LISTING_COLUMNS (what fetch_recommended
    selects for every other caller, Home and the Jobs page included), so
    only the handful of jobs this digest actually emails pays for it."""
    if not job_ids:
        return {}
    rows = (
        await db.execute(select(Job_Post.id, Job_Post.description).where(Job_Post.id.in_(job_ids)))
    ).all()
    return {str(row.id): row.description for row in rows if row.description}


# A straight-on fist, sleeve and arched purple handle -- redrawn (2026-11-15)
# from the student's own sketch (basic-briefcasehold-mockup.jpg) after the
# diagonal-sleeve version still didn't land: a frontal hand gripping a
# rounded arch whose two legs plug straight into the frame's top border,
# rather than a side-on sleeve holding a flat bar. No image-generation tool
# is available here, so this is hand-authored vector art, checked against
# a real headless-Chrome render (not just reasoned about) before being kept.
_BRIEFCASE_HANDLE = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAx"
    "NjAgMTgwIj4KPHBhdGggZD0iTTQwIDE4MCBMNDAgMTQwIFE0MCAxMDAgODAgMTAwIFExMjAg"
    "MTAwIDEyMCAxNDAgTDEyMCAxODAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzZkM2ZkOCIgc3Ry"
    "b2tlLXdpZHRoPSIyMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49"
    "InJvdW5kIi8+CjxyZWN0IHg9IjU4IiB5PSIwIiB3aWR0aD0iNDQiIGhlaWdodD0iNjYiIHJ4"
    "PSIxMCIgZmlsbD0iIzNmYTc1ZSIvPgo8bGluZSB4MT0iNTkiIHkxPSI1NiIgeDI9IjEwMSIg"
    "eTI9IjU2IiBzdHJva2U9IiMyYzgyNDkiIHN0cm9rZS13aWR0aD0iMiIvPgo8ZWxsaXBzZSBj"
    "eD0iMTA0IiBjeT0iMTA0IiByeD0iNyIgcnk9IjExIiBmaWxsPSIjYmY3ZTQ1IiB0cmFuc2Zv"
    "cm09InJvdGF0ZSgyMCAxMDQgMTA0KSIvPgo8cmVjdCB4PSI1NCIgeT0iNjAiIHdpZHRoPSI1"
    "MiIgaGVpZ2h0PSI0MiIgcng9IjE2IiBmaWxsPSIjYmY3ZTQ1Ii8+CjxyZWN0IHg9IjU3IiB5"
    "PSI5MCIgd2lkdGg9IjEwIiBoZWlnaHQ9IjM2IiByeD0iNSIgZmlsbD0iI2JmN2U0NSIvPgo8"
    "cmVjdCB4PSI2OSIgeT0iODUiIHdpZHRoPSIxMCIgaGVpZ2h0PSI0OSIgcng9IjUiIGZpbGw9"
    "IiNiZjdlNDUiLz4KPHJlY3QgeD0iODEiIHk9Ijg1IiB3aWR0aD0iMTAiIGhlaWdodD0iNDki"
    "IHJ4PSI1IiBmaWxsPSIjYmY3ZTQ1Ii8+CjxyZWN0IHg9IjkzIiB5PSI5MCIgd2lkdGg9IjEw"
    "IiBoZWlnaHQ9IjM2IiByeD0iNSIgZmlsbD0iI2JmN2U0NSIvPgo8L3N2Zz4K"
)


def _job_tags(job: ScoredJob, description: str | None) -> list[str]:
    tags = []
    if job.work_style:
        tags.append(_WORK_STYLE_LABELS.get(job.work_style.value, job.work_style.value))
    if job.job_type:
        tags.append(_JOB_TYPE_LABELS.get(job.job_type.value, job.job_type.value))
    degree = _degree_label(description)
    if degree:
        tags.append(degree)
    return tags[:3]


def _job_row_html(job: ScoredJob, web_url: str, description: str | None) -> str:
    link = f"{web_url}/jobs/{job.id}"
    color = _match_color(job.match)
    logo = (
        f'<img src="{job.logo_url}" width="40" height="40" alt="" '
        f'style="border-radius:8px;display:block;object-fit:contain">'
        if job.logo_url
        else (
            f'<div style="width:40px;height:40px;border-radius:8px;background:#efe9fc;'
            f'color:#6d3fd8;font-size:16px;font-weight:600;text-align:center;line-height:40px">'
            f"{job.company[:1].upper()}</div>"
        )
    )
    tags = "".join(
        f'<span style="display:inline-block;font-size:12px;color:#6b6478;background:#f5f5f5;'
        f'border-radius:999px;padding:2px 10px;margin:4px 6px 0 0">{tag}</span>'
        for tag in _job_tags(job, description)
    )
    return f"""
    <tr>
      <td style="padding:16px 0;border-bottom:1px solid #e5e1f5">
        <table style="width:100%;border-collapse:collapse"><tr>
          <td style="width:40px;vertical-align:top">{logo}</td>
          <td style="padding-left:12px;vertical-align:top">
            <a href="{link}" style="font-size:16px;font-weight:600;color:#1a1625;text-decoration:none">{job.title}</a>
            <div style="font-size:14px;color:#6b6478;margin-top:2px">{job.company}</div>
            <div>{tags}</div>
          </td>
          <td style="width:90px;text-align:right;vertical-align:top">
            <div style="display:inline-block;font-size:13px;font-weight:600;color:{color};
              background:#f5f5f5;border-radius:999px;padding:3px 10px">{job.match}% match</div>
            <div style="margin-top:10px">
              <a href="{link}" style="display:inline-block;font-size:13px;font-weight:600;color:#ffffff;
                background:#6d3fd8;border-radius:999px;padding:6px 16px;text-decoration:none">Apply</a>
            </div>
          </td>
        </tr></table>
      </td>
    </tr>"""


def _digest_html(jobs: list[ScoredJob], web_url: str, descriptions: dict[str, str] | None = None) -> str:
    descriptions = descriptions or {}
    rows = "".join(_job_row_html(job, web_url, descriptions.get(job.id)) for job in jobs)
    content = f"""
      <table style="width:100%;border-collapse:collapse"><tr>
        <td style="vertical-align:middle">
          <h1 style="font-size:20px;color:#1a1625;margin:0">{_title(len(jobs))}</h1>
        </td>
        <td style="width:40px;text-align:right;vertical-align:middle">
          <img src="{web_url}/workit-icon.svg" width="32" height="32" alt="WorkIt">
        </td>
      </tr></table>
      <p style="font-size:13px;color:#9890a3;margin-top:8px">
        This email provides quick summaries of best matched jobs. Reading the full
        description for better insight of the company and position offered is recommended.
      </p>
      <table style="width:100%;border-collapse:collapse;margin-top:8px">{rows}</table>
      <p style="font-size:14px;color:#1a1625;margin-top:28px;text-align:center">
        To look at more job offerings, visit
        <a href="{web_url}/jobs" style="display:inline-block;font-weight:600;color:#ffffff;
          background:#6d3fd8;border-radius:999px;padding:6px 16px;text-decoration:none;margin-left:4px">WorkIt!</a>
      </p>
      <p style="font-size:12px;color:#9890a3;margin-top:24px;text-align:center">
        Turn these off any time in <a href="{web_url}/settings" style="color:#9890a3">Settings</a>.
      </p>"""
    # The briefcase frame (from the student's mockup): a hand in a cuffed
    # sleeve, gripping the case by its handle, centered above a thick rounded
    # border. The hand is one small inline image (_BRIEFCASE_HANDLE, a flat
    # SVG data URI: sleeve, cuff, fist and the handle bar it holds) -- Outlook
    # can't render it (no SVG support) and shows nothing there, but still
    # draws the plain border below, so the frame itself never breaks. A soft
    # shadow under the card sells the "hand is holding this up" read; it is
    # a plain box-shadow, so a client that ignores it (Outlook) just shows a
    # flat card, never a broken one.
    return f"""
    <table role="presentation" width="504" cellpadding="0" cellspacing="0" style="margin:0 auto">
      <tr><td align="center">
        <img src="{_BRIEFCASE_HANDLE}" width="128" height="144" alt=""
          style="display:block;margin-bottom:-12px;position:relative;z-index:1">
      </td></tr>
      <tr><td>
        <table role="presentation" width="504" cellpadding="0" cellspacing="0"
          style="border:6px solid #6d3fd8;border-radius:20px;box-shadow:0 14px 24px -10px rgba(109,63,216,0.35)">
          <tr><td style="padding:22px 18px;font-family:sans-serif">{content}</td></tr>
        </table>
      </td></tr>
    </table>"""


async def send_job_alert(db: AsyncSession, account: AuthenticatedAccount) -> bool:
    """Builds the digest and, when it isn't empty, writes one Notification
    row and sends one email from it. Returns whether anything went out --
    an empty digest (zero new matches above MIN_MATCH) sends and writes
    nothing, so the bell never shows a hollow "0 matches today"."""
    jobs = await build_digest(db, account)
    if not jobs:
        return False

    web_url = get_settings().web_url.rstrip("/")
    db.add(
        Notification(
            applicant_id=account.id,
            type="job_alert",
            title=_title(len(jobs)),
            body=f"{jobs[0].title} at {jobs[0].company} ({jobs[0].match}% match), and {len(jobs) - 1} more."
            if len(jobs) > 1
            else f"{jobs[0].title} at {jobs[0].company} ({jobs[0].match}% match).",
            data=[
                {"job_id": job.id, "title": job.title, "company": job.company, "match": job.match}
                for job in jobs
            ],
        )
    )
    await db.commit()

    if await is_suppressed(db, account.email):
        # Bounced or complained before (app/services/notices.py): the bell
        # still shows the digest, but no email goes out.
        return True
    descriptions = await _fetch_descriptions(db, [job.id for job in jobs])
    sent = await send_email(
        account.email,
        f"Your {len(jobs)} best job {'match' if len(jobs) == 1 else 'matches'} today",
        _digest_html(jobs, web_url, descriptions),
    )
    if not sent:
        logger.warning("job alert email failed for %s; the bell notification was still written", account.id)
    return True


__all__ = ["EmptyBank", "build_digest", "send_job_alert"]
