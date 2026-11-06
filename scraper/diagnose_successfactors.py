"""Bounded, read-only Epiroc SuccessFactors listing diagnosis.

python scraper/diagnose_successfactors.py --output tasks/successfactors-diagnostic

The output directory must be new. No descriptions, full HTML, headers or
production state are retained. The deadline is soft: in-flight requests or
normal pacing/backoff can finish later, but no further HTTP call starts.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from workit_scraper import polite, web
from workit_scraper.providers import fetch
from workit_scraper.providers.model import Incomplete
from workit_scraper.providers.systems import successfactors as reader

TOKEN = "www.careerprofile.epiroc.com"
MAX_REQUESTS = 35
DEADLINE_SECONDS = 240
REQUEST_TIMEOUT_SECONDS = 15


class BudgetExceeded(RuntimeError):
    """No further request may start within the diagnostic budget."""


def diagnose(robots: polite.Robots) -> dict:
    """Exercise the actual reader while keeping only pagination evidence."""
    started = time.monotonic()
    requests = 0
    pages: list[dict] = []
    original_get = web.get
    original_text = fetch._get_text
    retries_before = fetch.retry_count()

    def check_budget() -> None:
        if requests >= MAX_REQUESTS or time.monotonic() - started >= DEADLINE_SECONDS:
            raise BudgetExceeded

    def bounded_get(url: str, *, timeout: float, headers=None) -> bytes:
        nonlocal requests
        check_budget()
        requests += 1
        return original_get(url, timeout=min(timeout, REQUEST_TIMEOUT_SECONDS), headers=headers)

    def capture(url: str) -> str:
        check_budget()
        if not robots.allows(url):
            raise PermissionError
        robots.pace(url)
        text = original_text(url)
        labels = re.findall(r'<span\b[^>]*class="paginationLabel"[^>]*>(.*?)</span>', text, re.S)
        labels = [
            " ".join(html.unescape(re.sub(r"<[^>]*>", "", label)).split()) for label in labels
        ]
        rows = reader._successfactors_rows(text)
        pages.append(
            {
                "startrow": int(parse_qs(urlsplit(url).query)["startrow"][0]),
                "pagination_labels": labels,
                "row_count": len(rows),
                "paths": [row[0] for row in rows],
            }
        )
        return text

    result: dict = {"token": TOKEN, "started_at": datetime.now(UTC).isoformat()}
    web.get, fetch._get_text = bounded_get, capture
    try:
        jobs = reader.successfactors(TOKEN, "Epiroc")
        result.update(status="complete", error=None, jobs=len(jobs))
    except Exception as error:
        # Exception text can contain arbitrary upstream content or request URLs.
        result.update(status=type(error).__name__, error=type(error).__name__)
        if isinstance(error, urllib.error.HTTPError):
            result["http_status"] = error.code
        elif isinstance(error, Incomplete):
            result["error"] = "Reader could not establish a complete listing"
        elif isinstance(error, BudgetExceeded):
            result["error"] = "Diagnostic request or time budget exhausted"
    finally:
        web.get, fetch._get_text = original_get, original_text
    result.update(
        requests=requests,
        retries=fetch.retry_count() - retries_before,
        elapsed_seconds=round(time.monotonic() - started, 3),
        pages=pages,
        total_unique=len({path for page in pages for path in page["paths"]}),
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
        "max_requests": MAX_REQUESTS,
        "soft_deadline_seconds": DEADLINE_SECONDS,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "board": result,
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"{TOKEN}: {result['status']}; {result['total_unique']} distinct paths; "
        f"{result['requests']} requests; {result['elapsed_seconds']}s"
    )


if __name__ == "__main__":
    main()
