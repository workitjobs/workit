"""
The bank job (KAN-726): embed every experience bank whose vector is stale,
on the team computer, the one machine that makes vectors
(docs/scraper_gh_action/plan.md, Decisions 3 and 4).

    uv run python -m app.scripts.embed_banks          # listen, embed, until stopped
    uv run python -m app.scripts.embed_banks --once   # one sweep, then exit

It reads the root .env like the API: EMBEDDING_PROVIDER must name a real
provider (`ollama` on that computer), DATABASE_URL is where it reads and
writes banks, and DIRECT_URL (the session pooler, port 5432) is where it
listens, since the transaction pooler cannot hold a LISTEN. Every other
machine leaves EMBEDDING_PROVIDER at `none` and never runs this.

How it runs:

- A bank change commits a NOTIFY on `bank.BANK_CHANNEL`. The first one wakes
  the job; it waits `DEBOUNCE_S` for more (a student saving ten edits sends
  ten), then sweeps once, so each changed bank is embedded once and at most
  one sweep starts a minute.
- A sweep embeds every stale bank (`bank_vectors.STALE`), banks that never
  had a vector first (new students), then the oldest change first.
- It also sweeps on start, on every reconnect and every `BACKUP_S`, which
  catches the notifies sent while it was off or disconnected.
- It checks its connection every `PING_S` and reconnects when it is gone: a
  campus network or the pooler can drop an idle connection without a word.
"""

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import datetime

import asyncpg
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db import get_sessionmaker
from app.models.bank import Experience_Bank
from app.services.bank import BANK_CHANNEL, load_bank
from app.services.identity import load_applicant_identity
from app.services.matching import bank_vectors
from app.services.matching.bank_input import bank_text
from app.services.matching.embeddings import BATCH_SIZE, embed

logger = logging.getLogger(__name__)

DEBOUNCE_S = 60.0
BACKUP_S = 6 * 60 * 60.0
PING_S = 5 * 60.0
RETRY_MAX_S = 5 * 60.0


async def stale_banks(session: AsyncSession) -> list[tuple[uuid.UUID, datetime]]:
    """Each stale bank's id and the version (updated_at) read now, banks
    with no vector first, then the oldest change first."""
    rows = await session.execute(
        select(Experience_Bank.applicant_id, Experience_Bank.updated_at)
        .where(bank_vectors.STALE)
        .order_by(
            Experience_Bank.embedding.is_(None).desc(),
            Experience_Bank.updated_at,
            Experience_Bank.applicant_id,
        )
    )
    return [(row.applicant_id, row.updated_at) for row in rows]


async def sweep(sessionmaker: async_sessionmaker[AsyncSession]) -> int:
    """Embed every stale bank, BATCH_SIZE at a time; the number stored.
    Stops at the first failed embed (the provider is down): the next wake
    tries again. A bank with no text (no entries, no skills) or no profile
    is passed over and stays stale, since there is nothing to send."""
    stored = 0
    async with sessionmaker() as session:
        todo = await stale_banks(session)
        await session.commit()
        for start in range(0, len(todo), BATCH_SIZE):
            texts: list[str] = []
            kept: list[tuple[uuid.UUID, datetime]] = []
            for applicant_id, read_at in todo[start:start + BATCH_SIZE]:
                identity = await load_applicant_identity(session, applicant_id)
                if identity is None:
                    continue
                text = bank_text(await load_bank(session, applicant_id), identity=identity)
                if text:
                    texts.append(text)
                    kept.append((applicant_id, read_at))
            # No transaction stays open across the model call.
            await session.commit()
            if not texts:
                continue
            vectors = await embed(texts, query=True)
            if not vectors:
                logger.warning("Embedding failed; %d stale banks wait for the next sweep", len(todo) - start)
                return stored
            for (applicant_id, read_at), vector in zip(kept, vectors):
                # False when the bank changed meanwhile: it stays stale, and
                # its notify brings it back.
                stored += await bank_vectors.store(session, applicant_id, read_at, vector)
            await session.commit()
    return stored


async def _sweep_logged(sessionmaker: async_sessionmaker[AsyncSession], why: str) -> None:
    try:
        stored = await sweep(sessionmaker)
    except Exception:
        # A database error ends this sweep only; the job keeps listening.
        logger.exception("Sweep (%s) failed", why)
        return
    logger.info("Sweep (%s): stored %d bank vectors", why, stored)


def _listen_dsn() -> str:
    """DIRECT_URL as asyncpg takes it: a plain postgresql:// URL."""
    return get_settings().migration_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _wait(events: list[asyncio.Event], timeout: float) -> None:
    """Return when any event is set, or after `timeout`."""
    waiters = [asyncio.create_task(event.wait()) for event in events]
    try:
        await asyncio.wait(waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for waiter in waiters:
            waiter.cancel()


async def _serve(conn: asyncpg.Connection, sessionmaker, woken: asyncio.Event) -> None:
    """Sweep after each burst of notifies, and every BACKUP_S, until the
    connection is gone."""
    lost = asyncio.Event()
    conn.add_termination_listener(lambda _conn: lost.set())
    loop = asyncio.get_running_loop()
    next_backup = loop.time() + BACKUP_S
    while not lost.is_set():
        await _wait([woken, lost], timeout=min(PING_S, max(0.0, next_backup - loop.time())))
        if lost.is_set():
            return
        if woken.is_set():
            await asyncio.sleep(DEBOUNCE_S)
            # Cleared before the sweep: a notify during it wakes the next one.
            woken.clear()
            await _sweep_logged(sessionmaker, "notified")
        elif loop.time() >= next_backup:
            await _sweep_logged(sessionmaker, "backup")
            next_backup = loop.time() + BACKUP_S
        else:
            # Quiet: check the connection is still there.
            await asyncio.wait_for(conn.execute("SELECT 1"), timeout=30)


async def run() -> None:
    sessionmaker = get_sessionmaker()
    woken = asyncio.Event()
    retry = 5.0
    while True:
        try:
            conn = await asyncpg.connect(_listen_dsn(), timeout=30)
        except (TimeoutError, OSError, asyncpg.PostgresError) as exc:
            logger.warning("Cannot listen (%s); trying again in %.0f s", exc, retry)
            await asyncio.sleep(retry)
            retry = min(retry * 2, RETRY_MAX_S)
            continue
        retry = 5.0
        try:
            await conn.add_listener(BANK_CHANNEL, lambda *_args: woken.set())
            logger.info("Listening on %s", BANK_CHANNEL)
            # Catch up on what changed while not listening.
            await _sweep_logged(sessionmaker, "start")
            await _serve(conn, sessionmaker, woken)
        except (TimeoutError, OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
            logger.warning("Lost the connection (%s); reconnecting", exc)
        finally:
            if not conn.is_closed():
                conn.terminate()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="embed_banks", description=__doc__.split("\n\n")[0])
    parser.add_argument("--once", action="store_true", help="sweep once, then exit")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if get_settings().embedding_provider == "none":
        print("EMBEDDING_PROVIDER is none, so nothing would be embedded. Set it to ollama "
              "on the team computer (docs/scraper_gh_action/plan.md).", file=sys.stderr)
        return 1
    if args.once:
        print(f"stored {asyncio.run(sweep(get_sessionmaker()))} bank vectors")
        return 0
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
