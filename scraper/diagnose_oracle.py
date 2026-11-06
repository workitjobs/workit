"""Read-only, bounded reproduction of KAN-722's four Oracle incomplete boards.

Run from the repository root with a new output directory, for example:
python scraper/diagnose_oracle.py --output tasks/oracle-diagnostic --page-size 200

The deadline is soft: an in-flight request or normal pacing/backoff may finish
after it. No new HTTP call starts after the deadline. Captures contain only
pagination metadata and posting IDs, never full responses, headers or URLs.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

from workit_scraper import polite, web
from workit_scraper.providers import fetch
from workit_scraper.providers.model import Incomplete
from workit_scraper.providers.systems import oracle as oracle_module

TOKENS = (
    "ebwg.fa.us2/CX",
    "eofe.fa.us2/CX_1001",
    "fa-eomf-saasfaprod1.fa.ocs/CX_1002",
    "hdpn.fa.us6/CX_1",
)
MAX_REQUESTS = 30
DEADLINE_SECONDS = 180
REQUEST_TIMEOUT_SECONDS = 15


class BudgetExceeded(RuntimeError):
    """No further request may start within this board's diagnostic budget."""


def _integer(value: object) -> int | None:
    """Keep numeric metadata without persisting unexpected response text."""
    if isinstance(value, bool):
        return None
    try:
        return int(value) if isinstance(value, (int, str)) else None
    except ValueError:
        return None


def diagnose(token: str, page_size: int, robots: polite.Robots) -> dict:
    """Run the existing reader, intercepting only requests and safe captures."""
    started_at = datetime.now(UTC).isoformat()
    started = time.monotonic()
    requests = 0
    pages: list[dict] = []
    original_get = web.get
    original_json = fetch._get_json
    original_page_size = oracle_module.ORACLE_PAGE
    retries_before = fetch.retry_count()

    def check_budget() -> None:
        if requests >= MAX_REQUESTS or time.monotonic() - started >= DEADLINE_SECONDS:
            raise BudgetExceeded

    def bounded_get(url: str, *, timeout: float, headers=None) -> bytes:
        nonlocal requests
        check_budget()
        requests += 1
        # Retain web.get's User-Agent and refusal of cross-origin redirects.
        return original_get(url, timeout=min(timeout, REQUEST_TIMEOUT_SECONDS), headers=headers)

    def capture(url: str) -> object:
        check_budget()
        if not robots.allows(url):
            raise PermissionError
        robots.pace(url)
        payload = original_json(url)
        # The URL is constructed by the reader; only its numeric offset is kept.
        offset = int(url.rsplit("offset=", 1)[1].split(",", 1)[0])
        items = payload.get("items") if isinstance(payload, dict) else None
        found = items[0] if isinstance(items, list) and items else {}
        found = found if isinstance(found, dict) else {}
        rows = found.get("requisitionList")
        rows = rows if isinstance(rows, list) else []
        ids = [
            str(row["Id"])
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("Id"), (int, str))
        ]
        pages.append(
            {
                "requested_offset": offset,
                "requested_limit": page_size,
                "TotalJobsCount": _integer(found.get("TotalJobsCount")),
                "Offset": _integer(found.get("Offset")),
                "Limit": _integer(found.get("Limit")),
                "row_count": len(rows),
                "ids": ids,
            }
        )
        return payload

    result: dict = {"token": token, "started_at": started_at}
    web.get = bounded_get
    fetch._get_json = capture
    oracle_module.ORACLE_PAGE = page_size
    try:
        jobs = oracle_module.oracle(token, token)
        result.update(status="complete", error=None, jobs=len(jobs))
    except Exception as error:
        # Exception messages may contain request URLs or response text. Capture
        # only controlled labels; page counts provide the incomplete-read detail.
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
        oracle_module.ORACLE_PAGE = original_page_size
    result.update(
        requests=requests,
        retries=fetch.retry_count() - retries_before,
        elapsed_seconds=round(time.monotonic() - started, 3),
        pages=pages,
        total_unique=len({job_id for page in pages for job_id in page["ids"]}),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument("--page-size", type=int, choices=(100, 200), default=200)
    args = parser.parse_args()
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("--output must name a directory that does not already exist")

    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "page_size": args.page_size,
        "max_requests_per_board": MAX_REQUESTS,
        "soft_deadline_seconds_per_board": DEADLINE_SECONDS,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "boards": [],
    }
    robots = polite.Robots()
    for token in TOKENS:
        result = diagnose(token, args.page_size, robots)
        report["boards"].append(result)
        (args.output / "summary.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"{token}: {result['status']}; {result['total_unique']} distinct IDs; "
            f"{result['requests']} requests; {result['elapsed_seconds']}s",
            flush=True,
        )


if __name__ == "__main__":
    main()
