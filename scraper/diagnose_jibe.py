"""Read-only, bounded reproduction of KAN-722's joinus.ies-co.com board.

Run from the repository root with a new output directory:
python scraper/diagnose_jibe.py --output tasks/jibe-diagnostic

The 240-second deadline is soft: in-flight requests and ordinary pacing/backoff
may finish after it, but no further HTTP call starts. Captures retain only
pagination counts and posting identifiers, not descriptions, headers or URLs.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from workit_scraper import polite, shortlist, web
from workit_scraper.providers import fetch
from workit_scraper.providers.model import Incomplete
from workit_scraper.providers.systems import jibe as jibe_module

TOKEN = "joinus.ies-co.com"
PAGE_SIZE = 100
MAX_REQUESTS = 30
DEADLINE_SECONDS = 240
REQUEST_TIMEOUT_SECONDS = 15


class BudgetExceeded(RuntimeError):
    """No further request may start within the diagnostic budget."""


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if isinstance(value, (int, str)) else None
    except ValueError:
        return None


def diagnose(robots: polite.Robots) -> dict:
    """Run the real reader and shortlist without any production persistence."""
    started = time.monotonic()
    requests = 0
    pages: list[dict] = []
    original_get = web.get
    original_json = fetch._get_json
    original_page_size = jibe_module.JIBE_PAGE
    retries_before = fetch.retry_count()

    def check_budget() -> None:
        if requests >= MAX_REQUESTS or time.monotonic() - started >= DEADLINE_SECONDS:
            raise BudgetExceeded

    def bounded_get(url: str, *, timeout: float, headers=None) -> bytes:
        nonlocal requests
        check_budget()
        requests += 1
        return original_get(url, timeout=min(timeout, REQUEST_TIMEOUT_SECONDS), headers=headers)

    def capture(url: str) -> object:
        check_budget()
        if not robots.allows(url):
            raise PermissionError
        robots.pace(url)
        payload = original_json(url)
        query = parse_qs(urlsplit(url).query)
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        jobs = jobs if isinstance(jobs, list) else []
        identifiers = []
        for job in jobs:
            row = job.get("data") if isinstance(job, dict) else None
            row = row if isinstance(row, dict) else {}
            identifiers.append(
                {
                    key: str(row[key])
                    for key in ("slug", "req_id", "ats_code")
                    if isinstance(row.get(key), (int, str))
                }
            )
        pages.append(
            {
                "page": _integer(query.get("page", [None])[0]),
                "limit": PAGE_SIZE,
                "totalCount": _integer(payload.get("totalCount"))
                if isinstance(payload, dict)
                else None,
                "row_count": len(jobs),
                "identifiers": identifiers,
            }
        )
        return payload

    result: dict = {"token": TOKEN, "started_at": datetime.now(UTC).isoformat()}
    web.get = bounded_get
    fetch._get_json = capture
    jibe_module.JIBE_PAGE = PAGE_SIZE
    try:
        jobs = jibe_module.jibe(TOKEN, "IES")
        qualifying = shortlist.pick(jobs, is_new=lambda job: False)
        result.update(status="complete", error=None, jobs=len(jobs), qualifying=len(qualifying))
    except Exception as error:
        # Messages can include request URLs or arbitrary upstream response text.
        result.update(status=type(error).__name__, error=type(error).__name__)
        if isinstance(error, urllib.error.HTTPError):
            result["http_status"] = error.code
        elif isinstance(error, Incomplete):
            result["error"] = "Reader could not establish a complete listing"
        elif isinstance(error, BudgetExceeded):
            result["error"] = "Diagnostic request or time budget exhausted"
    finally:
        web.get = original_get
        fetch._get_json = original_json
        jibe_module.JIBE_PAGE = original_page_size
    result.update(
        requests=requests,
        retries=fetch.retry_count() - retries_before,
        elapsed_seconds=round(time.monotonic() - started, 3),
        pages=pages,
        total_unique=len(
            {
                row.get("slug") or row.get("req_id")
                for page in pages
                for row in page["identifiers"]
                if row.get("slug") or row.get("req_id")
            }
        ),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("--output must name a directory that does not already exist")
    result = diagnose(polite.Robots())
    report = {
        "page_size": PAGE_SIZE,
        "max_requests": MAX_REQUESTS,
        "soft_deadline_seconds": DEADLINE_SECONDS,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "board": result,
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"{TOKEN}: {result['status']}; {result['total_unique']} distinct IDs; "
        f"{result.get('qualifying', 'unknown')} qualifying; "
        f"{result['requests']} requests; {result['elapsed_seconds']}s"
    )


if __name__ == "__main__":
    main()
