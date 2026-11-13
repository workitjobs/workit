"""Reading JazzHR company job boards: its reader, its page reader and its record.

JazzHR hosts company boards at ``{slug}.applytojob.com/apply``, HTML with
titles, URLs and locations but no descriptions or dates. Each kept posting's
detail page carries a schema.org ``JobPosting`` in JSON-LD: the description,
``datePosted``, ``baseSalary``, ``employmentType`` and ``jobLocation``.

robots.txt on every ``{slug}.applytojob.com`` disallows only ``/cb``.
"""

from __future__ import annotations

import html
import re
from dataclasses import replace

from workit_scraper import details
from workit_scraper.providers import fetch
from workit_scraper.providers.fetch import _iso
from workit_scraper.providers.model import Job, Provider
from workit_scraper.providers.registry import job_url, listing_url
from workit_scraper.providers.text import (
    _described,
    _ld_pay,
    _ld_place,
    _ld_posting,
    _page,
    _work_style,
)

#: A job link on the listing page: /apply/{10-char-id}/{slug}
_JAZZHR_JOB = re.compile(
    r'href="(https?://[a-z0-9_.-]+\.applytojob\.com/apply/([A-Za-z0-9]+)/[^"]+)"',
    re.I,
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
        # Title is in the <a> tag's text: search from after the matched href
        # to skip any > inside earlier attributes.
        title_start = text.find(">", match.end()) + 1
        title_end = text.find("</a>", title_start)
        raw = text[title_start:title_end] if title_end > title_start else ""
        title = html.unescape(raw).strip()
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
    posting = _ld_posting(text)
    full, roles = _described(posting.get("description"))
    stated_pay = _ld_pay(posting.get("baseSalary"))
    places = _ld_place(posting.get("jobLocation"))
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
