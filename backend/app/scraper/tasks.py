"""Task log for the scraper worker.

After the reader/writer rewrite (D4), scraper_tasks is a log of finished
reads.  The worker inserts one row per board (status done or failed,
started_at, finished_at, boards_s, error) in one bulk INSERT per batch.
No create/claim/mark cycle: boards come from an in-memory asyncio.Queue.
"""

from __future__ import annotations

import re

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from app.models.scraper import Scraper_Task

_tasks = Scraper_Task.__table__

# Matches key=value pairs where the key looks like a credential.
# Longest alternatives first so access_token wins over bare token.
# The value may sit in quotes (a JSON body), and "Bearer"/"Basic" is part of
# it: masking only that word left the token after it in the text. A bare
# "key" counts only as a whole word, so "monkey=1" and Postgres's
# "Key (apply_url)=(...)" stay as they are.
_CREDENTIAL_RE = re.compile(
    r"(access_token|refresh_token|api_key|apikey|authorization|password|secret|signature|token"
    r"|(?<![A-Za-z_])key)"
    r"""["']?\s*[=:]\s*["']?(?:(?:bearer|basic)\s+)?[^\s&"']+""",
    re.IGNORECASE,
)
# The password in a URL's sign-in part: postgresql://user:password@host.
_URL_PASSWORD_RE = re.compile(r"(://[^\s/:@]+:)[^\s/@]+@")


# Bearer tokens that asyncpg embeds in auth-failure messages.
_BEARER_RE = re.compile(
    r"Bearer\s+[A-Za-z0-9._\-]+",
    re.IGNORECASE,
)


def _sanitize_error(error: str) -> str:
    """Strip credential-like values from an error string, then truncate.

    The admin Scrape Health page prints this text (KAN-879), so a new shape
    of secret gets a case in tests/test_scrape_worker.py before it gets a
    pattern here.
    """
    cleaned = _URL_PASSWORD_RE.sub(r"\1***@", error)
    cleaned = _CREDENTIAL_RE.sub(lambda m: m.group(1) + "=***", cleaned)
    cleaned = _BEARER_RE.sub("Bearer ***", cleaned)
    return cleaned[:2000]


async def bulk_log_tasks(conn: AsyncConnection, results: list[dict]) -> int:
    """Insert one task-log row per board result in a single statement (D4).

    Each dict must have schedule_id, status ('done' or 'failed'), started_at,
    finished_at, and optionally boards_s, error. Error strings are sanitized
    through _sanitize_error (H3).

    Returns the count of rows inserted.
    """
    if not results:
        return 0
    rows = []
    for r in results:
        row = {
            "schedule_id": r["schedule_id"],
            "status": r["status"],
            "started_at": r["started_at"],
            "finished_at": r["finished_at"],
        }
        if r.get("boards_s") is not None:
            row["boards_s"] = r["boards_s"]
        if r.get("error"):
            row["error"] = _sanitize_error(r["error"])
        rows.append(row)
    result = await conn.execute(insert(_tasks).values(rows))
    return result.rowcount
