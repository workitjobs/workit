"""
The admins' anomaly report over the Rules table's fetch log, as a table
(KAN-772, services/rules_anomalies.py; GET /admin/rules-anomalies answers
the same as JSON):

    uv run python -m app.scripts.rules_anomalies [--days 7]

It reads the database DATABASE_URL names and writes nothing.
"""

import argparse
import asyncio
import sys

from app.db import get_sessionmaker
from app.schemas.rules_anomalies import RulesAnomalies
from app.services.rules_anomalies import report, table


async def _report(days: int) -> RulesAnomalies:
    async with get_sessionmaker()() as db:
        return await report(db, days)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flag accounts whose Rules table fetches look like scraping.")
    parser.add_argument("--days", type=int, default=7, choices=range(1, 31), metavar="1..30", help="how far back (default 7)")
    print(table(asyncio.run(_report(parser.parse_args(argv).days))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
