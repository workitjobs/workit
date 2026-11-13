"""Reading Pinpoint company job boards: its reader and its record.

Pinpoint has a documented public JSON API at
``{slug}.pinpointhq.com/postings.json`` that returns every open posting in one
request, with descriptions, pay, workplace type and employment type. Its
robots.txt disallows only ``/mydata``, ``/admin`` and ``/companies``.
"""

from __future__ import annotations

import re

from workit_scraper import details
from workit_scraper.providers import fetch
from workit_scraper.providers.model import BoardNotFound, Job, Provider
from workit_scraper.providers.registry import listing_url
from workit_scraper.providers.text import _listed_page, _work_style

#: Pinpoint's ``compensation_frequency`` → `details._INTERVAL` keys.
_PP_PERIOD = {
    "hour": "hour",
    "day": None,  # no daily in _INTERVAL; let details.read find it
    "week": "week",
    "two_weeks": None,  # no biweekly; let the description catch it
    "month": "month",
    "year": "year",
}


def pinpoint(token: str, company: str) -> list[Job]:
    """Every posting on a Pinpoint board, in one request."""
    url = listing_url("pinpoint", token)
    payload = fetch._get_json(url)
    assert isinstance(payload, dict)
    data = payload.get("data")
    if not isinstance(data, list):
        raise BoardNotFound(url)
    jobs: list[Job] = []
    for row in data:
        title = (row.get("title") or "").strip()
        loc = row.get("location") or {}
        location = loc.get("name") if isinstance(loc, dict) else None
        job_obj = row.get("job")
        dept = job_obj.get("department") or {} if isinstance(job_obj, dict) else {}
        dept_name = dept.get("name") if isinstance(dept, dict) else None

        # Pay: structured fields when visible.
        stated_pay = None
        if row.get("compensation_visible"):
            period = _PP_PERIOD.get(row.get("compensation_frequency") or "")
            if period:
                stated_pay = details.Pay.from_interval(
                    row.get("compensation_currency"),
                    row.get("compensation_minimum"),
                    row.get("compensation_maximum"),
                    period,
                )

        # Description: concatenate the HTML sections.
        parts = []
        for key in ("description", "key_responsibilities", "skills_knowledge_expertise"):
            text = row.get(key)
            if text:
                parts.append(text)
        markup = "<br>".join(parts) if parts else None

        jobs.append(
            Job(
                ats="pinpoint",
                token=token,
                company=company,
                external_id=str(row.get("id") or ""),
                title=title,
                apply_url=row.get("url") or "",
                location=location,
                department=dept_name,
                page=_listed_page(
                    title,
                    markup,
                    stated_type=details.job_type_label(row.get("employment_type")),
                    stated_style=_work_style(row.get("workplace_type"), location),
                    stated_pay=stated_pay,
                ),
            )
        )
    return jobs


PROVIDER = Provider(
    listing_url="https://{token}.pinpointhq.com/postings.json",
    read=pinpoint,
    apply_link=re.compile(r"([a-z0-9_.-]+)\.pinpointhq\.com/", re.I),
    subdomains="pinpointhq.com",
)
