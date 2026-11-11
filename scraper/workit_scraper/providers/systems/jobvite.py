"""Reading Jobvite company job boards: its reader, its page reader and its record.

Jobvite hosts company boards at ``jobs.jobvite.com/{slug}``, HTML with titles,
URLs and locations in a ``<table>`` but no descriptions or dates. Each kept
posting's detail page carries a schema.org ``JobPosting`` in JSON-LD: the
description, ``datePosted``, ``baseSalary``, ``employmentType`` and
``jobLocation``.

A nonexistent slug redirects to ``search.jobvite.com``, which ``web.get``
refuses as cross-origin: that is Jobvite's 404.

robots.txt on ``jobs.jobvite.com`` returns 404 (no restrictions per RFC 9309).
"""

from __future__ import annotations

import html
import json
import re
import urllib.error
from dataclasses import replace

from workit_scraper import details
from workit_scraper.providers import fetch
from workit_scraper.providers.fetch import _iso
from workit_scraper.providers.model import BoardNotFound, Job, Provider
from workit_scraper.providers.registry import job_url, listing_url
from workit_scraper.providers.text import (
    _described,
    _page,
    _place,
    _work_style,
)

#: A job link on the listing page: /{slug}/job/{id}
_JOBVITE_JOB = re.compile(
    r'<a[^>]*href="/([a-z0-9-]+)/job/([a-zA-Z0-9]+)"[^>]*>\s*(.*?)\s*</a>',
    re.S,
)

#: Location text in the table cell after the job link.
_LOCATION = re.compile(
    r'<td[^>]*class="jv-job-list-location"[^>]*>(.*?)</td>', re.S
)

#: The JSON-LD JobPosting block on a detail page.
_LD_JSON = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)


def jobvite(token: str, company: str) -> list[Job]:
    """Every posting on a Jobvite board, in one request.

    The listing page is an HTML table with job titles, links and locations.
    A nonexistent board redirects cross-origin, which ``web.get`` raises as
    an ``HTTPError``; that is Jobvite's 404.
    """
    url = listing_url("jobvite", token)
    try:
        text = fetch._get_text(url)
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            raise BoardNotFound(url) from error
        raise
    jobs: dict[str, Job] = {}
    for match in _JOBVITE_JOB.finditer(text):
        slug, job_id, title_html = match.groups()
        if slug != token or job_id in jobs:
            continue
        title = html.unescape(title_html).strip()
        # Location: the next <td class="jv-job-list-location"> after this match.
        after = text[match.end() : match.end() + 500]
        loc_match = _LOCATION.search(after)
        location = _jobvite_location(loc_match.group(1)) if loc_match else None
        jobs[job_id] = Job(
            ats="jobvite",
            token=token,
            company=company,
            external_id=job_id,
            title=title,
            apply_url=f"https://jobs.jobvite.com/{token}/job/{job_id}",
            location=location,
        )
    return list(jobs.values())


def _jobvite_location(cell: str) -> str | None:
    """A location from the listing's ``<td>`` content, which may carry a
    ``<div class="jv-meta">N Locations</div>`` instead of a city/state."""
    # Strip tags and collapse whitespace.
    text = re.sub(r"<[^>]+>", " ", cell)
    text = " ".join(text.split()).strip()
    # "2 Locations" etc. is not a place.
    if re.match(r"\d+ Locations?$", text, re.I):
        return None
    # Normalise "Chicago,  Illinois" → "Chicago, Illinois".
    text = re.sub(r"\s*,\s*", ", ", text).strip(", ")
    return text or None


def describe_jobvite(job: Job) -> Job:
    """The same Jobvite posting with what its JSON-LD JobPosting says:
    description, date, pay, employment type and places."""
    text = fetch._get_text(job_url("jobvite", job.token, job.external_id))
    posting = _jobvite_posting(text)
    full, roles = _described(posting.get("description"))
    stated_pay = _jobvite_pay(posting.get("baseSalary"))
    places = _jobvite_place(posting.get("jobLocation"))
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


def _jobvite_posting(page: str) -> dict:
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


def _jobvite_pay(salary: object) -> details.Pay | None:
    """Structured pay from a Jobvite ``baseSalary``.

    Jobvite's JSON-LD baseSalary is often incomplete (empty currency, empty
    unitText, only maxValue set).  Values are strings, not numbers."""
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
    low = _num(value.get("minValue"))
    high = _num(value.get("maxValue"))
    currency = salary.get("currency") or None
    return details.Pay.from_interval(currency, low, high, period)


def _num(v: object) -> float | None:
    """A JSON value that may be a number or a numeric string, or None."""
    if isinstance(v, (int, float)) and v:
        return float(v)
    if isinstance(v, str) and v:
        try:
            f = float(v)
            return f if f > 0 else None
        except ValueError:
            return None
    return None


def _jobvite_place(location: object) -> str | None:
    """A place from the JSON-LD's ``jobLocation``."""
    locs = location if isinstance(location, list) else [location] if location else []
    for loc in locs:
        if not isinstance(loc, dict):
            continue
        address = loc.get("address") or {}
        if not isinstance(address, dict):
            continue
        place = _place(
            address.get("addressLocality"),
            address.get("addressRegion"),
        )
        if place:
            return place
    return None


PROVIDER = Provider(
    listing_url="https://jobs.jobvite.com/{token}",
    read=jobvite,
    apply_link=re.compile(r"//jobs\.jobvite\.com/([a-z0-9-]+)/job/", re.I),
    job_url="https://jobs.jobvite.com/{token}/job/{job_id}",
    describe=describe_jobvite,
)
