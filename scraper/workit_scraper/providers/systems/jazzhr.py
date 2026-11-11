"""Reading JazzHR company job boards: its reader, its page reader and its record.

JazzHR hosts company boards at ``{slug}.applytojob.com/apply``, HTML with
titles, URLs and locations but no descriptions or dates. Each kept posting's
detail page carries a schema.org ``JobPosting`` in JSON-LD: the description,
``datePosted``, ``baseSalary``, ``employmentType`` and ``jobLocation``.

robots.txt on every ``{slug}.applytojob.com`` disallows only ``/cb``.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import replace

from workit_scraper import details
from workit_scraper.providers import fetch
from workit_scraper.providers.fetch import _iso
from workit_scraper.providers.model import Job, Provider
from workit_scraper.providers.registry import job_url, listing_url
from workit_scraper.providers.text import (
    _described,
    _page,
    _place,
    _work_style,
)

#: A job link on the listing page: /apply/{10-char-id}/{slug}
_JAZZHR_JOB = re.compile(
    r'href="(https?://[a-z0-9_.-]+\.applytojob\.com/apply/([A-Za-z0-9]+)/[^"]+)"',
    re.I,
)

#: The JSON-LD JobPosting block on a detail page.
_LD_JSON = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)

#: Location entries on the listing page: inside <ul> under the job link.
_LOCATION = re.compile(r"<li>\s*([^<]+?)\s*</li>")


def jazzhr(token: str, company: str) -> list[Job]:
    """Every posting on a JazzHR board, in one request.

    The listing page is HTML with job titles, links and locations. An inactive
    board returns a page with no job links — not a 404 — so it reads as an
    empty board.
    """
    text = fetch._get_text(listing_url("jazzhr", token))
    jobs: dict[str, Job] = {}
    # Walk the page: each job link is followed by a <ul> with the location.
    for match in _JAZZHR_JOB.finditer(text):
        url, job_id = match.groups()
        if job_id in jobs:
            continue
        # The location <ul> sits after this link, within ~200 chars.
        after = text[match.end() : match.end() + 500]
        loc_match = _LOCATION.search(after)
        location = html.unescape(loc_match[1]).strip() if loc_match else None
        # Title is in the <a> tag's text: find the closing </a>.
        title_start = text.find(">", match.start()) + 1
        title_end = text.find("</a>", title_start)
        title = html.unescape(text[title_start:title_end]).strip() if title_end > title_start else ""
        jobs[job_id] = Job(
            ats="jazzhr",
            token=token,
            company=company,
            external_id=job_id,
            title=title,
            apply_url=html.unescape(url),
            location=location or None,
        )
    return list(jobs.values())


def describe_jazzhr(job: Job) -> Job:
    """The same JazzHR posting with what its JSON-LD JobPosting says:
    description, date, pay, employment type and places."""
    text = fetch._get_text(job_url("jazzhr", job.token, job.external_id))
    posting = _jazzhr_posting(text)
    full, roles = _described(posting.get("description"))
    stated_pay = _jazzhr_pay(posting.get("baseSalary"))
    places = _jazzhr_place(posting.get("jobLocation"))
    stated_style = _work_style(None, places or job.location)

    return replace(
        job,
        posted_at=_iso(posting.get("datePosted")) or job.posted_at,
        page=_page(
            job.title,
            full,
            roles=roles,
            stated_type=details.job_type_label(posting.get("employmentType")),
            stated_style=stated_style,
            stated_pay=stated_pay,
            offices=(places,) if places else (),
        ),
    )


def _jazzhr_posting(page: str) -> dict:
    """The page's JobPosting from its JSON-LD, or {} when it has none."""
    for match in _LD_JSON.finditer(page):
        try:
            found = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        for item in found if isinstance(found, list) else [found]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return {}


def _jazzhr_pay(salary: object) -> details.Pay | None:
    """Structured pay from a JazzHR ``baseSalary``."""
    if not isinstance(salary, dict):
        return None
    value = salary.get("value")
    if not isinstance(value, dict):
        return None
    unit = (value.get("unitText") or "").upper()
    period_map = {"HOUR": "hour", "WEEK": "week", "MONTH": "month", "YEAR": "year"}
    period = period_map.get(unit)
    if not period:
        return None
    return details.Pay.from_interval(
        salary.get("currency"),
        value.get("minValue"),
        value.get("maxValue"),
        period,
    )


def _jazzhr_place(location: object) -> str | None:
    """A place from the JSON-LD's ``jobLocation``."""
    if isinstance(location, list):
        location = location[0] if location else None
    if not isinstance(location, dict):
        return None
    address = location.get("address") or {}
    if not isinstance(address, dict):
        return None
    return _place(
        address.get("addressLocality"),
        address.get("addressRegion"),
    ) or None


PROVIDER = Provider(
    listing_url="https://{token}.applytojob.com/apply",
    read=jazzhr,
    apply_link=re.compile(
        r"([a-z0-9_.-]+)\.applytojob\.com/", re.I
    ),
    job_url="https://{token}.applytojob.com/apply/{job_id}",
    describe=describe_jazzhr,
    subdomains="applytojob.com",
)
