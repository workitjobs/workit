"""Measure a frozen Greenhouse batch without changing the production catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from workit_scraper import polite, providers, shortlist, web
from workit_scraper.board_read import ReadStatus, read_board, reported_name
from workit_scraper.providers import fetch

MAX_REQUESTS = 200
MAX_SECONDS = 300
MAX_DETAILS = 20


class BudgetExceeded(RuntimeError):
    """The isolated pilot may not start more requests."""


def tokens_from(manifest):
    tokens = manifest.get("tokens")
    if (
        manifest.get("provider") != "greenhouse"
        or not isinstance(tokens, list)
        or not 1 <= len(tokens) <= 20
        or any(not isinstance(t, str) or not re.fullmatch(r"[a-z0-9_-]+", t) for t in tokens)
        or len(set(tokens)) != len(tokens)
    ):
        raise ValueError("manifest must contain 1..20 distinct Greenhouse tokens")
    return tokens


def run(tokens, existing_urls, robots):
    started = time.monotonic()
    requests = 0
    original_get = web.get
    retry_start = fetch.retry_count()
    report = {"started_at": datetime.now(UTC).isoformat(), "boards": []}
    seen = set(existing_urls)

    def exhausted():
        return requests >= MAX_REQUESTS or time.monotonic() - started >= MAX_SECONDS

    def bounded(url, *, timeout, headers=None):
        nonlocal requests
        if exhausted():
            raise BudgetExceeded
        requests += 1
        return original_get(url, timeout=min(timeout, 15), headers=headers)

    web.get = bounded
    try:
        for token in tokens:
            board_start, request_start = time.monotonic(), requests
            row = {"token": token, "status": "deferred", "qualifying_urls": [], "new_urls": []}
            report["boards"].append(row)
            if exhausted():
                continue
            board = providers.Board("greenhouse", token, token)
            phase = time.monotonic()
            result = read_board(board, robots)
            row.update(
                listing_seconds=round(time.monotonic() - phase, 3),
                listing_requests=requests - request_start,
                status=result.status.name.lower(),
                reason=result.reason,
            )
            if result.status is ReadStatus.OK:
                row["raw_postings"] = len(result.jobs)
                phase, before = time.monotonic(), requests
                name = reported_name(board, robots)
                row.update(
                    company=name,
                    name_seconds=round(time.monotonic() - phase, 3),
                    name_requests=requests - before,
                )
                candidates = sorted(
                    (j for j in result.jobs if shortlist.classify(j.title)),
                    key=lambda j: j.external_id,
                )
                row.update(title_candidates=len(candidates), detail_failed=0, detail_disallowed=0)
                described, attempted = [], 0
                phase, before = time.monotonic(), requests
                if name:
                    for job in candidates:
                        if attempted >= MAX_DETAILS or exhausted():
                            break
                        attempted += 1
                        url = providers.job_url(job.ats, job.token, job.external_id)
                        if not robots.allows(url):
                            row["detail_disallowed"] += 1
                            continue
                        robots.pace(url)
                        try:
                            job = providers.describe(replace(job, company=name))
                            if job.description and job.description.strip():
                                described.append(job)
                            else:
                                row["detail_failed"] += 1
                        except Exception:
                            row["detail_failed"] += 1
                row.update(
                    described=len(described),
                    detail_deferred=len(candidates) - attempted,
                    detail_requests=requests - before,
                    detail_seconds=round(time.monotonic() - phase, 3),
                )
                urls = sorted(
                    {r.apply_url for r in shortlist.pick(described, is_new=lambda _: False)}
                )
                row["qualifying_urls"] = urls
                row["new_urls"] = sorted(set(urls) - seen)
                row["existing_feed_overlap"] = len(set(urls) & existing_urls)
                seen.update(urls)
                row["status"] = "validated" if name else "needs_company"
            row.update(
                seconds=round(time.monotonic() - board_start, 3), requests=requests - request_start
            )
            print(token, row["status"], len(row["new_urls"]), "new URLs", flush=True)
    finally:
        web.get = original_get
    report.update(
        requests=requests,
        retries=fetch.retry_count() - retry_start,
        seconds=round(time.monotonic() - started, 3),
        qualifying_urls=sorted({u for r in report["boards"] for u in r["qualifying_urls"]}),
        new_urls=sorted(seen - existing_urls),
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--existing-feed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_raw, feed_raw = args.manifest.read_bytes(), args.existing_feed.read_bytes()
    tokens = tokens_from(json.loads(manifest_raw))
    feed = json.loads(feed_raw)
    rows = feed if isinstance(feed, list) else feed["jobs"]
    existing = {r["apply_url"] for r in rows}
    args.output.mkdir(parents=True, exist_ok=False)
    report = run(tokens, existing, polite.Robots())
    report.update(
        manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
        existing_feed_sha256=hashlib.sha256(feed_raw).hexdigest(),
        existing_feed_urls=len(existing),
        limits={"requests": MAX_REQUESTS, "seconds": MAX_SECONDS, "details_per_board": MAX_DETAILS},
    )
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(len(report["new_urls"]), "distinct qualifying URLs absent from the supplied feed")


if __name__ == "__main__":
    main()
