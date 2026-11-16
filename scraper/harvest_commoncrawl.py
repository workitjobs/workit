"""Harvest ATS board slugs from Common Crawl's CDX index.

A developer tool, run by hand like ``build_boards.py --resolve``. It queries the
CDX API for each ATS host pattern, extracts board tokens via ``board_keys()``,
deduplicates against ``boards.csv``, and writes ``commoncrawl-boards.json``.

    python3 harvest_commoncrawl.py                     # latest crawl, write the file
    python3 harvest_commoncrawl.py --crawl CC-MAIN-2026-43
    python3 harvest_commoncrawl.py --dry-run            # print counts, don't write
    python3 harvest_commoncrawl.py --dry-run --verbose  # also print per-URL hits
    python3 harvest_commoncrawl.py --direct             # bypass CDX API, read shards

The CDX API is a public query service. This script makes its own HTTP calls with
honest identification and a 1-second delay between requests, outside the
scraper's ``Robots`` system. Re-run when a new crawl is published (~every 5
weeks); review the diff and commit the output file.

When the CDX API is down (504), ``--direct`` reads the raw index shards on
``data.commoncrawl.org`` via HTTP Range requests, bypassing the query servers.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

# The scraper package is importable from the repo root when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workit_scraper.catalog import BOARDS_CSV, load_boards
from workit_scraper.providers.urls import board_keys

USER_AGENT = "workit-scraper/harvest (+https://github.com/workitjobs)"
COLLINFO = "https://index.commoncrawl.org/collinfo.json"
DATA_HOST = "https://data.commoncrawl.org"
DELAY_S = 1.0
MAX_RETRIES = 3
#: HTTP codes worth retrying; the CDX API is slow and 504s are common.
RETRY_CODES = {429, 500, 502, 503, 504}

# CDX URL patterns per ATS. Each is queried as the ``url`` parameter. Wildcards:
# ``*.host.com`` matches subdomains, ``host.com/*`` matches paths. One pattern
# per likely shape of board/posting URL on each hiring system's public host.
# ponytail: only greenhouse, lever, ashby, workable are in POOL_PAGES (the others
# lack read_name); the rest are stored in the JSON for future use but the channel
# silently skips them. Add a provider to POOL_PAGES when it gets read_name.
CDX_PATTERNS: list[tuple[str, str]] = [
    # Greenhouse
    ("greenhouse", "boards.greenhouse.io/*"),
    ("greenhouse", "job-boards.greenhouse.io/*"),
    ("greenhouse", "boards.eu.greenhouse.io/*"),
    ("greenhouse", "job-boards.eu.greenhouse.io/*"),
    # Lever
    ("lever", "jobs.lever.co/*"),
    ("lever", "jobs.eu.lever.co/*"),
    # Ashby
    ("ashby", "jobs.ashbyhq.com/*"),
    # Workable
    ("workable", "apply.workable.com/*"),
    # BambooHR
    ("bamboohr", "*.bamboohr.com/careers/*"),
    ("bamboohr", "*.bamboohr.com/jobs/*"),
    # Workday
    ("workday", "*.myworkdayjobs.com/*"),
    # Rippling
    ("rippling", "ats.rippling.com/*"),
    # iCIMS
    ("icims", "*.icims.com/jobs/*"),
    # SmartRecruiters
    ("smartrecruiters", "jobs.smartrecruiters.com/*"),
    ("smartrecruiters", "careers.smartrecruiters.com/*"),
    # JazzHR
    ("jazzhr", "*.applytojob.com/*"),
    # Pinpoint
    ("pinpoint", "*.pinpointhq.com/*"),
    # Jobvite
    ("jobvite", "jobs.jobvite.com/*"),
    # Recruitee
    ("recruitee", "*.recruitee.com/*"),
]

OUTPUT = Path(__file__).resolve().parent / "commoncrawl-boards.json"


def _get(url: str) -> bytes:
    """GET with retries and backoff for transient failures."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            time.sleep(DELAY_S * 2**attempt)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRY_CODES:
                raise
        except (TimeoutError, OSError) as exc:
            last_error = exc
    raise last_error  # type: ignore[misc]


def latest_crawl() -> str:
    """The most recent crawl ID from collinfo.json (explicitly allowed)."""
    data = json.loads(_get(COLLINFO))
    if not isinstance(data, list) or not data:
        raise ValueError("collinfo.json returned no crawls")
    return data[0]["id"].rstrip("/")


def _encode_pattern(pattern: str) -> str:
    """URL-encode the pattern, keeping ``*`` for CDX wildcards."""
    return quote(pattern, safe="*/:.-")


# ---------------------------------------------------------------------------
# Direct shard access — bypasses the CDX API when it's down (504).
#
# Common Crawl stores its CDX index as ~300 gzipped shard files on
# data.commoncrawl.org. ``cluster.idx`` is a sorted coarse index: one line
# per ~3,000-record block, giving its SURT key, shard file, byte offset and
# length. We stream that file, collect the blocks whose SURT key matches our
# ATS prefixes, then fetch each block with an HTTP Range request, decompress,
# and extract URLs from the CDXJ records inside.
# ---------------------------------------------------------------------------


def _pattern_to_surt(pattern: str) -> tuple[str, str | None]:
    """CDX URL pattern → (SURT prefix, optional path filter).

    ``boards.greenhouse.io/*`` → ``("io,greenhouse,boards)/", None)``
    ``*.bamboohr.com/careers/*`` → ``("com,bamboohr,", "/careers/")``
    """
    host, _, path = pattern.partition("/")
    if host.startswith("*."):
        surt = ",".join(reversed(host[2:].split("."))) + ","
        filt = "/" + path.rstrip("*") if path and path != "*" else None
        return surt, filt
    return ",".join(reversed(host.split("."))) + ")/", None


def _surt_groups() -> dict[str, list[tuple[str, str | None]]]:
    """Group CDX_PATTERNS by SURT prefix → [(ats_label, path_filter), ...]."""
    groups: dict[str, list[tuple[str, str | None]]] = {}
    for label, pattern in CDX_PATTERNS:
        surt, filt = _pattern_to_surt(pattern)
        groups.setdefault(surt, []).append((label, filt))
    return groups


def _get_range(url: str, start: int, length: int) -> bytes:
    """HTTP Range GET with retries."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            time.sleep(DELAY_S * 2**attempt)
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Range": f"bytes={start}-{start + length - 1}",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
    raise last_error  # type: ignore[misc]


def _stream_cluster_blocks(
    crawl: str,
    surt_prefixes: set[str],
    *,
    verbose: bool = False,
) -> dict[str, list[tuple[str, int, int]]]:
    """Stream ``cluster.idx`` and return matching blocks per SURT prefix.

    The file is ~100 MB, sorted by SURT key. We stream it line by line and
    keep only the blocks whose key starts with one of our prefixes, plus the
    block immediately before each prefix's first match (it may hold earlier
    records with the same prefix, since cluster.idx samples every ~3,000
    records). Streaming stops early once every prefix is done.
    """
    url = f"{DATA_HOST}/cc-index/collections/{crawl}/indexes/cluster.idx"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    result: dict[str, list[tuple[str, int, int]]] = {p: [] for p in surt_prefixes}
    prev_block: tuple[str, int, int] | None = None
    started: set[str] = set()
    finished: set[str] = set()

    if verbose:
        print(f"    streaming cluster.idx for {len(surt_prefixes)} prefixes ...")
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            key = parts[0].split(" ")[0]
            block = (parts[1], int(parts[2]), int(parts[3]))

            for prefix in surt_prefixes - finished:
                if key.startswith(prefix):
                    if prefix not in started:
                        started.add(prefix)
                        if prev_block:
                            result[prefix].append(prev_block)
                    result[prefix].append(block)
                elif prefix in started:
                    # Sorted past this prefix — it's done.
                    finished.add(prefix)

            if finished == surt_prefixes:
                break
            prev_block = block

    if verbose:
        for prefix, blocks in sorted(result.items()):
            print(f"    {prefix}: {len(blocks)} blocks")
    return result


def _parse_cdx_block(
    compressed: bytes,
    surt_prefix: str,
    path_filter: str | None,
) -> list[str]:
    """Decompress one CDX block and return URLs matching the SURT prefix."""
    try:
        data = gzip.decompress(compressed)
    except Exception:
        return []
    hit_urls: list[str] = []
    for line in data.decode("utf-8", errors="replace").splitlines():
        if not line:
            continue
        # CDXJ: SURT_KEY TIMESTAMP JSON
        sp1 = line.find(" ")
        if sp1 < 0:
            continue
        surt_key = line[:sp1]
        if not surt_key.startswith(surt_prefix):
            continue
        if path_filter:
            paren = surt_key.find(")")
            if paren < 0 or not surt_key[paren + 1 :].startswith(path_filter):
                continue
        sp2 = line.find(" ", sp1 + 1)
        if sp2 < 0:
            continue
        try:
            meta = json.loads(line[sp2 + 1 :])
        except json.JSONDecodeError:
            continue
        raw = meta.get("url", "")
        if raw:
            hit_urls.append(raw)
    return hit_urls


def harvest_direct(crawl: str, *, verbose: bool = False) -> dict[str, list[str]]:
    """Harvest by reading CDX shard files directly (no CDX API)."""
    groups = _surt_groups()

    print("  streaming cluster index ...")
    all_blocks = _stream_cluster_blocks(crawl, set(groups.keys()), verbose=verbose)

    found: dict[str, set[str]] = defaultdict(set)
    for surt_prefix, labels_filters in sorted(groups.items()):
        blocks = all_blocks.get(surt_prefix, [])
        labels_str = ", ".join(lf[0] for lf in labels_filters)
        if not blocks:
            print(f"  {surt_prefix} ({labels_str}): no blocks")
            continue

        # Deduplicate blocks (the prev_block may duplicate a matched one).
        seen: set[tuple[str, int, int]] = set()
        unique = [b for b in blocks if b not in seen and not seen.add(b)]  # type: ignore[func-returns-value]

        base = f"{DATA_HOST}/cc-index/collections/{crawl}/indexes"
        print(f"  {surt_prefix} ({labels_str}): {len(unique)} blocks ...")
        for i, (shard, offset, length) in enumerate(unique):
            time.sleep(DELAY_S)
            try:
                compressed = _get_range(f"{base}/{shard}", offset, length)
            except Exception as exc:
                code = getattr(exc, "code", type(exc).__name__)
                print(f"    block {i + 1}/{len(unique)}: {code}, skipping")
                continue
            for _label, filt in labels_filters:
                for url in _parse_cdx_block(compressed, surt_prefix, filt):
                    if not url.startswith("http"):
                        url = "https://" + url
                    for ats, token in board_keys(url):
                        found[ats].add(token)
            if verbose:
                print(f"    block {i + 1}/{len(unique)} done")

        for label, _ in labels_filters:
            count = len(found.get(label, set()))
            print(f"    {label}: {count} unique so far")

    return {ats: sorted(tokens) for ats, tokens in sorted(found.items())}


def cdx_query(crawl: str, pattern: str, *, verbose: bool = False) -> list[str]:
    """All URLs matching ``pattern`` in the given crawl, paginated."""
    base = f"https://index.commoncrawl.org/{crawl}-index"
    encoded = _encode_pattern(pattern)
    # Ask how many pages.
    time.sleep(DELAY_S)
    try:
        meta = json.loads(_get(f"{base}?url={encoded}&showNumPages=true"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            if verbose:
                print(f"    {pattern}: crawl index not found")
            return []
        raise
    pages = meta.get("pages", 0)
    if pages == 0:
        return []
    if verbose:
        print(f"    {pattern}: {pages} pages")
    urls: list[str] = []
    for page in range(pages):
        time.sleep(DELAY_S)
        try:
            body = _get(f"{base}?url={encoded}&output=json&page={page}")
        except (urllib.error.HTTPError, TimeoutError, OSError) as exc:
            code = getattr(exc, "code", type(exc).__name__)
            print(f"    {pattern} page {page}/{pages}: {code}, skipping")
            continue
        for line in body.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            raw = record.get("url", "")
            if raw:
                urls.append(raw)
    return urls


def harvest(crawl: str, *, verbose: bool = False) -> dict[str, list[str]]:
    """Return ``{ats: [token, ...]}`` from the given crawl."""
    found: dict[str, set[str]] = defaultdict(set)
    failed: list[str] = []
    for label, pattern in CDX_PATTERNS:
        print(f"  querying {pattern} ...")
        try:
            raw_urls = cdx_query(crawl, pattern, verbose=verbose)
        except Exception as exc:
            code = getattr(exc, "code", type(exc).__name__)
            print(f"    FAILED after {MAX_RETRIES} retries: {code}")
            failed.append(pattern)
            continue
        hits = 0
        for url in raw_urls:
            if not url.startswith("http"):
                url = "https://" + url
            for ats, token in board_keys(url):
                found[ats].add(token)
                hits += 1
        print(
            f"    {len(raw_urls)} URLs, {hits} board hits, "
            f"{len(found.get(label, set()))} unique {label} so far"
        )
    if failed:
        print(f"  {len(failed)} patterns failed: {', '.join(failed)}")
    return {ats: sorted(tokens) for ats, tokens in sorted(found.items())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crawl", help="crawl ID, e.g. CC-MAIN-2026-43; default: latest")
    parser.add_argument("--dry-run", action="store_true", help="print counts, don't write")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="bypass CDX API; read shards directly",
    )
    parser.add_argument(
        "--boards",
        type=Path,
        default=BOARDS_CSV,
        help="catalog to compare against",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    if args.crawl:
        crawl = args.crawl
    else:
        print("Fetching latest crawl ID ...")
        crawl = latest_crawl()
    print(f"Crawl: {crawl}")

    if args.direct:
        ats_map = harvest_direct(crawl, verbose=args.verbose)
    else:
        ats_map = harvest(crawl, verbose=args.verbose)

    known = {(b.ats, b.token) for b in load_boards(args.boards)} if args.boards.exists() else set()
    total, new_total = 0, 0
    for ats, tokens in sorted(ats_map.items()):
        new_count = sum(1 for t in tokens if (ats, t) not in known)
        total += len(tokens)
        new_total += new_count
        print(f"  {ats}: {len(tokens)} boards ({new_count} new)")
    print(f"Total: {total} boards, {new_total} new vs {len(known)} in catalog")

    if args.dry_run:
        print("Dry run; no file written.")
        return 0

    payload = {
        "crawl": crawl,
        "harvested_at": datetime.now(UTC).isoformat(),
        "ats": ats_map,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
