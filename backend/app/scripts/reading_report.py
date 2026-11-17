"""
How uploads were read, per day, from the reading log (KAN-898,
queries/resume_readings.py): for each reader and, for the parser, why its
reading was saved, how many readings, their mean time and the mean of the
model's fields the check against the text dropped. Shows how often
production falls back to the parser (KAN-806).

    uv run python -m app.scripts.reading_report [--days 14]

It reads the database DATABASE_URL names and writes nothing.
"""

import argparse
import asyncio
import sys

from app.db import get_sessionmaker
from app.queries.resume_readings import readings_by_day

_COLUMNS = ("day", "read_by", "reason", "readings", "seconds", "fields_dropped")


async def _rows(days: int) -> list[dict]:
    async with get_sessionmaker()() as db:
        return await readings_by_day(db, days=days)


def table(rows: list[dict]) -> str:
    """The rows as a plain text table, one line per day, reader and reason."""
    if not rows:
        return "No readings in that period."
    cells = [_COLUMNS] + [tuple("-" if r[c] is None else str(r[c]) for c in _COLUMNS) for r in rows]
    widths = [max(len(line[i]) for line in cells) for i in range(len(_COLUMNS))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(line, widths)).rstrip() for line in cells)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count resume readings by reader and reason per day.")
    parser.add_argument("--days", type=int, default=14, choices=range(1, 91), metavar="1..90",
                        help="how far back (default 14; the log keeps 90)")
    print(table(asyncio.run(_rows(parser.parse_args(argv).days))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
