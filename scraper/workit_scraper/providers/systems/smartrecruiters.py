"""Reading SmartRecruiters company job boards: its reader, its page reader and its
record.

SmartRecruiters has a public, keyless JSON API at api.smartrecruiters.com. Its
list carries titles, locations and dates but no descriptions, so each kept
posting's own page is read once (`describe_smartrecruiters`). Invalid slugs
return 200 with ``totalFound: 0`` -- they cannot raise `BoardNotFound`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace

from workit_scraper import details
from workit_scraper.providers import fetch
from workit_scraper.providers.fetch import _iso
from workit_scraper.providers.model import Job, Provider
from workit_scraper.providers.registry import job_url, listing_url
from workit_scraper.providers.text import _described, _page, _work_style

#: Postings per SmartRecruiters request (API's max).
SR_PAGE = 100

#: SmartRecruiters' ``period`` values mapped to `details._INTERVAL`'s keys.
_SR_PERIOD = {
    "HOURLY": "hour",
    "WEEKLY": "week",
    "MONTHLY": "month",
    "YEARLY": "year",
}


def smartrecruiters(
    token: str, company: str, *, pace: Callable[[str], None] = lambda url: None
) -> list[Job]:
    """Every posting on a SmartRecruiters board, paged 100 at a time."""
    jobs: list[Job] = []
    offset = 0
    first = True
    while True:
        url = f"{listing_url('smartrecruiters', token)}?limit={SR_PAGE}&offset={offset}"
        if not first:
            pace(url)
        first = False
        payload = fetch._get_json(url)
        assert isinstance(payload, dict)
        total = int(payload.get("totalFound") or 0)
        content = payload.get("content") or []
        for row in content:
            loc = row.get("location") or {}
            parts = [loc.get("city"), loc.get("region"), loc.get("country")]
            location = loc.get("fullLocation") or ", ".join(
                str(p) for p in parts if p
            ) or None
            # Clean empty slots: "London, , UK" -> "London, UK"
            if location:
                location = re.sub(r",\s*,", ",", location).strip(", ")
            dept = row.get("department") or {}
            jobs.append(
                Job(
                    ats="smartrecruiters",
                    token=token,
                    company=company,
                    external_id=str(row.get("id") or row.get("uuid") or ""),
                    title=(row.get("name") or "").strip(),
                    apply_url=f"https://jobs.smartrecruiters.com/{token}/{row.get('id', '')}",
                    location=location or None,
                    department=dept.get("label") if isinstance(dept, dict) else None,
                    posted_at=_iso(row.get("releasedDate")),
                )
            )
        if not content or offset + len(content) >= total:
            break
        offset += SR_PAGE
    return jobs


def describe_smartrecruiters(job: Job) -> Job:
    """The same SmartRecruiters posting with its description and card facts."""
    payload = fetch._get_json(job_url("smartrecruiters", job.token, job.external_id))
    assert isinstance(payload, dict)
    sections = (payload.get("jobAd") or {}).get("sections") or {}
    html_parts = []
    for key in ("jobDescription", "qualifications", "additionalInformation"):
        section = sections.get(key) or {}
        text = section.get("text")
        if text:
            html_parts.append(text)
    full, roles = _described("<br>".join(html_parts) if html_parts else None)

    # Compensation: SmartRecruiters sends HOURLY/WEEKLY/MONTHLY/YEARLY;
    # details._INTERVAL wants the lowercase word.
    comp = payload.get("compensation") or {}
    period = _SR_PERIOD.get(comp.get("period") or "")
    stated_pay = details.Pay.from_interval(
        comp.get("currency"), comp.get("min"), comp.get("max"), period
    ) if comp.get("currency") and period else None

    # Employment type
    toe = payload.get("typeOfEmployment") or {}
    stated_type = details.job_type_label(toe.get("id")) if isinstance(toe, dict) else None

    # Work style from location
    loc = payload.get("location") or {}
    if loc.get("remote"):
        stated_style = "Remote"
    elif loc.get("hybrid"):
        stated_style = "Hybrid"
    else:
        stated_style = _work_style(None, job.location)

    return replace(
        job,
        page=_page(
            job.title,
            full,
            roles=roles,
            stated_type=stated_type,
            stated_style=stated_style,
            stated_pay=stated_pay,
        ),
    )


PROVIDER = Provider(
    listing_url="https://api.smartrecruiters.com/v1/companies/{token}/postings",
    read=smartrecruiters,
    apply_link=re.compile(
        r"(?:jobs|careers)\.smartrecruiters\.com/([a-zA-Z0-9_.-]+)", re.I
    ),
    job_url="https://api.smartrecruiters.com/v1/companies/{token}/postings/{job_id}",
    describe=describe_smartrecruiters,
    paged=True,
    skip_robots=True,
)
