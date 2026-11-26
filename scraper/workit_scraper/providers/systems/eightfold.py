"""Reading Eightfold AI company job boards: its reader, its page reader and its
record.

Eightfold hosts company boards at ``{tenant}.eightfold.ai``. Its JSON API at
``/api/pcsx/search`` and ``/api/pcsx/position_details`` is explicitly allowed by
every tenant's robots.txt (``Allow: /api/pcsx``), so no ``skip_robots`` is
needed. The search API returns 10 postings per page with no descriptions; each
kept posting's detail is read once (``describe_eightfold``).

Token format: ``tenant/domain`` (compound, like Oracle's ``host/site``). Each
tenant needs its company's domain for the API's ``domain=`` parameter (e.g.
``micron/micron.com``).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from workit_scraper.providers import fetch
from workit_scraper.providers.model import (
    BoardNotFound,
    Incomplete,
    Job,
    Provider,
    TooLarge,
)
from workit_scraper.providers.registry import job_url, listing_url
from workit_scraper.providers.text import _described, _page, _work_style

#: Fixed page size returned by the Eightfold search API.
EIGHTFOLD_PAGE = 10
#: Cap: 500 requests at 10 per page; matches Workday/Oracle cap.
EIGHTFOLD_MAX = 5000


def _eightfold_style(value: object) -> str | None:
    """Map Eightfold's ``workLocationOption`` to the card's work style."""
    text = str(value or "").strip().lower()
    if text == "onsite":
        return "On site"
    if text == "remote":
        return "Remote"
    if text == "hybrid":
        return "Hybrid"
    return None


def _ts(value: object) -> str | None:
    """Unix seconds to ISO 8601 UTC. Eightfold's ``postedTs`` is seconds, not
    the milliseconds ``_iso`` expects."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), UTC).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def eightfold(
    token: str, company: str, *, pace: Callable[[str], None] = lambda url: None
) -> list[Job]:
    """Every posting on an Eightfold board, paged 10 at a time."""
    tenant, domain = token.split("/")
    url_base = listing_url("eightfold", token)
    seen: dict[str, Job] = {}
    offset = 0
    total: int | None = None
    first = True

    while True:
        url = f"{url_base}&start={offset}"
        if not first:
            pace(url)
        first = False
        payload = fetch._get_json(url)
        assert isinstance(payload, dict)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BoardNotFound(url)

        positions = data.get("positions")
        if total is None:
            count = data.get("count")
            if count is None or positions is None:
                raise BoardNotFound(url)
            total = int(count)
            if total > EIGHTFOLD_MAX:
                raise TooLarge(f"{token}: {total} postings")

        if not positions:
            break

        for row in positions:
            rid = str(row.get("id", ""))
            if rid in seen:
                continue
            locs = row.get("locations") or []
            std_locs = row.get("standardizedLocations") or []
            location = "; ".join(locs) if locs else (std_locs[0] if std_locs else None)
            pos_url = row.get("positionUrl") or ""
            seen[rid] = Job(
                ats="eightfold",
                token=token,
                company=company,
                external_id=rid,
                title=(row.get("name") or "").strip(),
                apply_url=f"https://{tenant}.eightfold.ai{pos_url}?domain={domain}",
                location=location or None,
                department=row.get("department"),
                posted_at=_ts(row.get("postedTs")),
                work_style=_eightfold_style(row.get("workLocationOption")),
            )

        offset += EIGHTFOLD_PAGE
        if offset >= total:
            break

    if total and len(seen) < total:
        raise Incomplete(f"{token}: got {len(seen)} of {total}")
    return list(seen.values())


def describe_eightfold(job: Job) -> Job:
    """The same Eightfold posting with its description and card facts."""
    payload = fetch._get_json(job_url("eightfold", job.token, job.external_id))
    assert isinstance(payload, dict)
    data = payload.get("data") or {}
    full, roles = _described(data.get("jobDescription"))

    stated_style = job.work_style or _work_style(None, job.location)

    return replace(
        job,
        page=_page(
            job.title,
            full,
            roles=roles,
            stated_style=stated_style,
        ),
    )


PROVIDER = Provider(
    listing_url="https://{tenant}.eightfold.ai/api/pcsx/search?domain={domain}",
    read=eightfold,
    # Matches our constructed apply URLs (with ?domain=), not curated-list
    # URLs (without it): the domain is not in the URL path, so links from the
    # curated lists stay in UNREAD_CAUSES.  Boards are added manually.
    apply_link=re.compile(
        r"//([a-z0-9-]+)\.eightfold\.ai/careers/[^\s?#]+\?"
        r"(?:[^\s#]*&)?domain=([a-z0-9.-]+)",
        re.I,
    ),
    job_url=(
        "https://{tenant}.eightfold.ai/api/pcsx/position_details"
        "?position_id={job_id}&domain={domain}"
    ),
    describe=describe_eightfold,
    paged=True,
    subdomains="eightfold.ai",
    budget_s=12 * 60,
)
