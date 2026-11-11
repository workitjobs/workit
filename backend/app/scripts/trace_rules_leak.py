"""
Which account a leaked Rules table was served to (KAN-756), and that
account's fetches (KAN-772):

    uv run python -m app.scripts.trace_rules_leak <table.json>

The candidates are every account the fetch log (rules_fetches, 90 days)
shows fetching a job system the table holds; each is scored against the
table's watermark (services/rules_watermark.py trace). Prints the account
id, how many marks agree, and whether the decoy names it, then its fetch
history (a row per UTC day and job system, with the count), or that none
fits. It reads the database DATABASE_URL names and writes nothing.
"""

import argparse
import asyncio
import datetime
import json
import sys
from pathlib import Path

from app.db import get_sessionmaker
from app.queries.rules import fetch_history, fetched_by
from app.services.rules_watermark import Trace, trace

History = list[tuple[datetime.date, str, int]]


async def identify(table: dict) -> tuple[Trace, History] | None:
    """The account the fetch log and the table's watermark name, with its fetch history; None if none fits."""
    async with get_sessionmaker()() as db:
        found = trace(table, await fetched_by(db, sorted(table.get("systems") or {})))
        return found and (found, await fetch_history(db, found.account_id))


def describe(found: Trace, history: History) -> str:
    """The match and the account's fetches, as printed."""
    lines = [
        f"{found.account_id}  {found.agree}/{found.marks} marks agree, decoy {'matches' if found.decoy else 'absent'}",
        "",
        f"Fetches: {sum(n for *_, n in history)} in the log",
        "day (UTC)   job system       fetches",
    ]
    lines += [f"{day.isoformat()}  {system:<15}  {n}" for day, system, n in history]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Name the account a leaked Rules table was served to.")
    parser.add_argument("table", type=Path, help="the leaked table, as JSON")
    found = asyncio.run(identify(json.loads(parser.parse_args(argv).table.read_text(encoding="utf-8"))))
    if found is None:
        print("No account in the fetch log fits this table's marks.")
        return 1
    print(describe(*found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
