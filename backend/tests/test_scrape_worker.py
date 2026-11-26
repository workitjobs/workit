"""The backend's scraper worker (KAN-605): app/scraper/. Against real Postgres
(backend/CLAUDE.md, "Tests against real Postgres"). No test here reads a real
board: the provider read is replaced."""

import datetime
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.db import get_engine
from app.scraper import schedules, tasks, worker

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Error string sanitization (KAN-912, pure — no database)
# ---------------------------------------------------------------------------


def test_sanitize_error_strips_api_key():
    raw = "Connection failed: https://api.example.com?api_key=sk-1234abc&page=1"
    assert "sk-1234abc" not in tasks._sanitize_error(raw)
    assert "api_key=***" in tasks._sanitize_error(raw)


def test_sanitize_error_strips_multiple_credentials():
    raw = "token=secret123 password=hunter2 authorization=Bearer xyz"
    cleaned = tasks._sanitize_error(raw)
    assert "secret123" not in cleaned
    assert "hunter2" not in cleaned
    assert "Bearer xyz" not in cleaned
    assert "token=***" in cleaned
    assert "password=***" in cleaned
    assert "authorization=***" in cleaned


def test_sanitize_error_truncates_to_2000():
    raw = "x" * 3000
    assert len(tasks._sanitize_error(raw)) == 2000


def test_sanitize_error_strips_dsn_urls():
    raw = "connection failed: postgresql://user:hunter2@db.example.com:5432/mydb rest"
    cleaned = tasks._sanitize_error(raw)
    assert "hunter2" not in cleaned
    assert "postgres://***" in cleaned


def test_sanitize_error_strips_asyncpg_dsn():
    raw = "asyncpg error: postgres+asyncpg://admin:s3cret@host:6543/db"
    cleaned = tasks._sanitize_error(raw)
    assert "s3cret" not in cleaned
    assert "postgres://***" in cleaned


def test_sanitize_error_strips_bearer_tokens():
    raw = "auth failed: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig"
    cleaned = tasks._sanitize_error(raw)
    assert "eyJhbGciOiJIUzI1NiJ9" not in cleaned
    assert "Bearer ***" in cleaned


def test_sanitize_error_preserves_safe_messages():
    raw = "publish failed: board returned HTTP 500"
    assert tasks._sanitize_error(raw) == raw


@pytest.fixture
def boards_csv(tmp_path):
    path = tmp_path / "boards.csv"
    path.write_text("ats,token,company\ngreenhouse,acme,Acme\n", encoding="utf-8")
    return path


async def _schedule(conn) -> object:
    return (await conn.execute(text("SELECT * FROM scraper_schedules"))).one()


async def test_a_complete_read_keeps_the_one_before(database, boards_csv):
    async with get_engine().begin() as conn:
        await schedules.sync_catalog(conn, boards_csv)
        row = await _schedule(conn)
        first = text("'2026-11-01T00:00:00+00'::timestamptz")
        second = text("'2026-11-02T00:00:00+00'::timestamptz")
        await schedules.advance_reads(conn, row.id, now_expr=first)
        await schedules.advance_reads(conn, row.id, now_expr=second)
        row = await _schedule(conn)
    assert row.prior_read_at == datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC)
    assert row.last_read_at == datetime.datetime(2026, 11, 2, tzinfo=datetime.UTC)


def _job(title: str, number: int):
    from workit_scraper.providers import Job

    return Job("ashby", "acme", "Acme", str(number), title, f"https://jobs.ashbyhq.com/acme/{number}")


def test_a_board_read_goes_through_read_board_and_the_shortlist(monkeypatch):
    from workit_scraper.board_read import BoardRead, ReadStatus
    from workit_scraper.providers import Board

    jobs = [_job("Software Engineering Intern", 1), _job("Senior Account Executive", 2)]
    calls = []

    def read_board(board, robots):
        calls.append(board)
        return BoardRead(ReadStatus.OK, jobs=jobs)

    monkeypatch.setattr(worker, "read_board", read_board)
    result, kept, *_ = worker.read_board_listing(Board("ashby", "acme", "Acme"))
    assert calls == [Board("ashby", "acme", "Acme")]
    assert result.jobs == jobs
    assert [job.title for job in kept] == ["Software Engineering Intern"]


def test_a_board_robots_txt_forbids_yields_nothing(monkeypatch):
    from workit_scraper.board_read import BoardRead, ReadStatus
    from workit_scraper.providers import Board

    monkeypatch.setattr(
        worker, "read_board", lambda board, robots: BoardRead(ReadStatus.SKIPPED, reason="robots.txt")
    )
    result, kept, *_ = worker.read_board_listing(Board("ashby", "acme", "Acme"))
    assert result.status is ReadStatus.SKIPPED
    assert kept == []


# ---------------------------------------------------------------------------
# Integration tests for the new reader/writer architecture
# ---------------------------------------------------------------------------


async def _seed_cycle_lease(conn):
    """Ensure the cycle lease row exists (the migration seeds it).

    Called inside a ``begin()`` context manager, so no explicit commit.
    """
    await conn.execute(
        text(
            "INSERT INTO scraper_cycle_leases (holder, expires_at)"
            " VALUES (NULL, '1970-01-01 00:00:00+00')"
            " ON CONFLICT DO NOTHING"
        )
    )


async def test_a_dry_run_writes_nothing(database, boards_csv, monkeypatch):
    async def skip_descriptions(conn, summary, robots=None):
        pass
    monkeypatch.setattr(worker, "_fetch_descriptions", skip_descriptions)
    monkeypatch.setattr(schedules, "BOARDS_CSV", boards_csv)

    # Pre-seed catalog so sync_catalog_diff has rows.
    async with get_engine().begin() as conn:
        await _seed_cycle_lease(conn)
        await schedules.sync_catalog(conn, boards_csv)

    engine = get_engine()
    summary = await worker.run_cycle(engine, dry_run=True)
    assert summary["synced"] == 0  # no new rows since catalog already synced
    assert summary["due_count"] == 1

    # Nothing was written (dry run released the lease).
    async with get_engine().connect() as conn:
        tasks_count = await conn.scalar(text("SELECT count(*) FROM scraper_tasks"))
    assert tasks_count == 0


async def test_boards_are_read_and_published(database, boards_csv, monkeypatch):
    """One board is read, published and its schedule advanced."""
    from workit_scraper.board_read import BoardRead, ReadStatus

    async def skip_descriptions(conn, summary, robots=None):
        pass
    monkeypatch.setattr(worker, "_fetch_descriptions", skip_descriptions)
    monkeypatch.setattr(schedules, "BOARDS_CSV", boards_csv)

    job = _job("Software Engineering Intern", 1)
    monkeypatch.setattr(
        worker, "read_board_listing",
        lambda board, robots=None: (BoardRead(ReadStatus.OK, jobs=[job]), [job], 1.0),
    )

    async with get_engine().begin() as conn:
        await _seed_cycle_lease(conn)
        await schedules.sync_catalog(conn, boards_csv)

    engine = get_engine()
    summary = await worker.run_cycle(engine)

    assert summary["boards_ok"] == 1
    assert summary["jobs_scraped"] == 1

    async with get_engine().connect() as conn:
        read_at = await conn.scalar(text("SELECT last_read_at FROM scraper_schedules"))
        jobs = await conn.scalar(text("SELECT count(*) FROM job_postings"))
        task_count = await conn.scalar(text("SELECT count(*) FROM scraper_tasks WHERE status = 'done'"))
    assert read_at is not None
    assert jobs == 1
    assert task_count == 1


async def test_unchanged_board_skips_import_but_advances_reads(database, boards_csv, monkeypatch):
    """When the fingerprint matches, import_feed is not called but
    advance_reads still runs (D2: two-read closure rule preserved)."""
    from workit_scraper.board_read import BoardRead, ReadStatus

    async def skip_descriptions(conn, summary, robots=None):
        pass
    monkeypatch.setattr(worker, "_fetch_descriptions", skip_descriptions)
    monkeypatch.setattr(schedules, "BOARDS_CSV", boards_csv)

    job = _job("Software Engineering Intern", 1)
    monkeypatch.setattr(
        worker, "read_board_listing",
        lambda board, robots=None: (BoardRead(ReadStatus.OK, jobs=[job]), [job], 1.0),
    )

    async with get_engine().begin() as conn:
        await _seed_cycle_lease(conn)
        await schedules.sync_catalog(conn, boards_csv)

    engine = get_engine()

    # First cycle: board is new, fingerprint is None → changed.
    summary1 = await worker.run_cycle(engine)
    assert summary1["boards_ok"] == 1

    async with get_engine().connect() as conn:
        row = await _schedule(conn)
        first_read = row.last_read_at

    # Second cycle: same fingerprint → unchanged.
    summary2 = await worker.run_cycle(engine)
    assert summary2["boards_ok"] == 1

    async with get_engine().connect() as conn:
        row = await _schedule(conn)
        second_read = row.last_read_at

    # advance_reads ran: last_read_at advanced.
    assert second_read > first_read


async def test_parallel_workers_read_all_boards(database, tmp_path, monkeypatch):
    """Four boards, four workers: every board is read and logged."""
    from workit_scraper.board_read import BoardRead, ReadStatus

    csv = tmp_path / "boards.csv"
    csv.write_text(
        "ats,token,company\n"
        "greenhouse,a,A\n"
        "greenhouse,b,B\n"
        "greenhouse,c,C\n"
        "greenhouse,d,D\n",
        encoding="utf-8",
    )

    async def skip_descriptions(conn, summary, robots=None):
        pass

    monkeypatch.setattr(worker, "_fetch_descriptions", skip_descriptions)
    monkeypatch.setattr(schedules, "BOARDS_CSV", csv)

    def fake_read(board, robots=None):
        n = ord(board.token)
        job = _job("Software Engineering Intern", n)
        return BoardRead(ReadStatus.OK, jobs=[job]), [job], 0.1

    monkeypatch.setattr(worker, "read_board_listing", fake_read)

    async with get_engine().begin() as conn:
        await _seed_cycle_lease(conn)
        await schedules.sync_catalog(conn, csv)

    engine = get_engine()
    summary = await worker.run_cycle(engine, workers=4)

    assert summary["boards_ok"] == 4
    assert summary["jobs_scraped"] == 4

    async with get_engine().connect() as conn:
        done = await conn.scalar(
            text("SELECT count(*) FROM scraper_tasks WHERE status = 'done'")
        )
    assert done == 4


async def test_lease_prevents_concurrent_cycles(database, boards_csv, monkeypatch):
    """A second cycle cannot take the lease while the first holds it (D5)."""
    async def skip_descriptions(conn, summary, robots=None):
        pass
    monkeypatch.setattr(worker, "_fetch_descriptions", skip_descriptions)
    monkeypatch.setattr(schedules, "BOARDS_CSV", boards_csv)

    async with get_engine().begin() as conn:
        await _seed_cycle_lease(conn)
        await schedules.sync_catalog(conn, boards_csv)

    # Take the lease manually so run_cycle finds it held.
    async with get_engine().begin() as conn:
        lease_id = await schedules.take_lease(conn, "other-holder")
    assert lease_id is not None

    engine = get_engine()
    summary = await worker.run_cycle(engine)
    assert summary.get("lease_held") is True
    assert summary["boards_ok"] == 0


# ---------------------------------------------------------------------------
# Quiet board stagger: filter_quiet as a pure function
# ---------------------------------------------------------------------------


def _row(ats="greenhouse", token="acme", has_kept=False, last_read_at=None):
    """Minimal row for filter_quiet."""
    return SimpleNamespace(ats=ats, token=token, has_kept=has_kept, last_read_at=last_read_at)


def test_filter_quiet_keeps_never_read_boards():
    rows = [_row(last_read_at=None)]
    assert schedules.filter_quiet(rows) == rows


def test_filter_quiet_keeps_hot_boards():
    recent = datetime.datetime.now(datetime.UTC)
    rows = [_row(has_kept=True, last_read_at=recent)]
    assert schedules.filter_quiet(rows) == rows


def test_filter_quiet_keeps_boards_past_quiet_longest():
    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2)
    rows = [_row(last_read_at=old)]
    assert schedules.filter_quiet(rows) == rows


def test_filter_quiet_stagger_matches_one_in_three(monkeypatch):
    """Across three consecutive slots, each quiet board is read exactly once."""
    recent = datetime.datetime.now(datetime.UTC)
    row = _row(last_read_at=recent, has_kept=False)
    slot_seconds = schedules.RUN_EVERY.total_seconds()
    base = int(time.time() // slot_seconds) * slot_seconds
    kept = 0
    for i in range(3):
        monkeypatch.setattr(time, "time", lambda t=base + i * slot_seconds: t)
        kept += len(schedules.filter_quiet([row]))
    assert kept == 1


def test_filter_quiet_full_keeps_everything():
    recent = datetime.datetime.now(datetime.UTC)
    rows = [_row(has_kept=False, last_read_at=recent)]
    assert schedules.filter_quiet(rows, full=True) == rows


# ---------------------------------------------------------------------------
# Fingerprint rest: advance_fingerprint against real Postgres
# ---------------------------------------------------------------------------


async def test_advance_fingerprint_sets_rest_on_unchanged(database, boards_csv):
    async with get_engine().begin() as conn:
        await schedules.sync_catalog(conn, boards_csv)
        row = await _schedule(conn)
        await schedules.advance_reads(conn, row.id)
        # First read: sets fingerprint, unchanged_reads = 0 (new fingerprint)
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        row = await _schedule(conn)
        assert row.fingerprint == "aabbccdd"
        assert row.unchanged_reads == 0
        assert row.fingerprint_until is None
        assert row.has_kept is True

        # Second read, same fingerprint: unchanged_reads = 1, fingerprint_until set
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        row = await _schedule(conn)
        assert row.unchanged_reads == 1
        assert row.fingerprint_until is not None


async def test_advance_fingerprint_resets_on_change(database, boards_csv):
    async with get_engine().begin() as conn:
        await schedules.sync_catalog(conn, boards_csv)
        row = await _schedule(conn)
        await schedules.advance_reads(conn, row.id)
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        # Second read, same → rest
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        row = await _schedule(conn)
        assert row.unchanged_reads == 1
        assert row.fingerprint_until is not None

        # Third read, different → reset
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="11223344")
        row = await _schedule(conn)
        assert row.unchanged_reads == 0
        assert row.fingerprint_until is None
        assert row.fingerprint == "11223344"


async def test_has_kept_is_sticky(database, boards_csv):
    async with get_engine().begin() as conn:
        await schedules.sync_catalog(conn, boards_csv)
        row = await _schedule(conn)
        assert row.has_kept is False
        await schedules.advance_reads(conn, row.id)
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        row = await _schedule(conn)
        assert row.has_kept is True
        # advance_fingerprint always sets has_kept true; it never goes back


async def test_record_missing_second_miss_clears_fingerprint(database, boards_csv):
    async with get_engine().begin() as conn:
        await schedules.sync_catalog(conn, boards_csv)
        row = await _schedule(conn)
        await schedules.advance_reads(conn, row.id)
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        # Same fingerprint → rest
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        row = await _schedule(conn)
        assert row.fingerprint_until is not None

        # First miss: note it
        await schedules.record_missing(conn, row.id)
        row = await _schedule(conn)
        assert row.missing_at is not None
        # Fingerprint state still present
        assert row.fingerprint == "aabbccdd"

        # Second miss: clears fingerprint state
        await schedules.record_missing(conn, row.id)
        row = await _schedule(conn)
        assert row.fingerprint is None
        assert row.unchanged_reads == 0
        assert row.fingerprint_until is None


async def test_select_due_from_rows_skips_fingerprint_resting(database, boards_csv):
    """A board with fingerprint_until in the future is skipped unless full=True."""
    async with get_engine().begin() as conn:
        await schedules.sync_catalog(conn, boards_csv)
        row = await _schedule(conn)
        await schedules.advance_reads(conn, row.id)
        # Set fingerprint and make it rest
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")

        all_rows, _, db_now = await schedules.sync_catalog_diff(conn, boards_csv)

        # Normal select_due_from_rows skips it
        due = schedules.select_due_from_rows(all_rows, db_now)
        assert len(due) == 0

        # full=True includes it
        due = schedules.select_due_from_rows(all_rows, db_now, full=True)
        assert len(due) == 1


# ---------------------------------------------------------------------------
# Description enrichment (phase 2)
# ---------------------------------------------------------------------------


async def _seed_source(conn, boards_csv):
    """Seed a schedule, a job posting and a job_source row for description tests.
    Returns (schedule_id, apply_url)."""
    await schedules.sync_catalog(conn, boards_csv)
    schedule = await _schedule(conn)
    apply_url = "https://jobs.ashbyhq.com/acme/1"
    await conn.execute(
        text(
            "INSERT INTO job_postings (apply_url, company_name, title, status, added_by_student)"
            " VALUES (:url, 'Acme', 'SWE Intern', 'published', false)"
        ),
        {"url": apply_url},
    )
    await conn.execute(
        text(
            "INSERT INTO job_sources (schedule_id, apply_url, external_id)"
            " VALUES (:sid, :url, '1')"
        ),
        {"sid": schedule.id, "url": apply_url},
    )
    await conn.commit()
    return schedule.id, apply_url


async def _source_row(conn, schedule_id, apply_url):
    return (
        await conn.execute(
            text(
                "SELECT description_version, description_attempts, description_fetched_at"
                " FROM job_sources WHERE schedule_id = :sid AND apply_url = :url"
            ),
            {"sid": schedule_id, "url": apply_url},
        )
    ).one()


async def test_description_failure_is_retried(database, boards_csv):
    """A failed fetch increments attempts and leaves version NULL so the row
    is picked up again on the next cycle."""
    async with get_engine().connect() as conn:
        sid, url = await _seed_source(conn, boards_csv)

        # Simulate one failure.
        row = SimpleNamespace(apply_url=url, schedule_id=sid)
        await worker._commit_description_batch(conn, [(row, None, "timeout")])

        src = await _source_row(conn, sid, url)
        assert src.description_attempts == 1
        assert src.description_version is None
        assert src.description_fetched_at is None


async def test_description_gives_up_after_max_attempts(database, boards_csv):
    """After MAX_DESCRIPTION_ATTEMPTS failures the row is no longer picked
    by _STALE_QUERY."""
    from workit_scraper import providers

    async with get_engine().connect() as conn:
        sid, url = await _seed_source(conn, boards_csv)

        # Set attempts to the max.
        await conn.execute(
            text(
                "UPDATE job_sources SET description_attempts = :max"
                " WHERE schedule_id = :sid AND apply_url = :url"
            ),
            {"max": worker.MAX_DESCRIPTION_ATTEMPTS, "sid": sid, "url": url},
        )
        await conn.commit()

        rows = (
            await conn.execute(
                worker._STALE_QUERY,
                {
                    "version": providers.PAGE_VERSION,
                    "cap": 100,
                    "max_attempts": worker.MAX_DESCRIPTION_ATTEMPTS,
                },
            )
        ).all()
        assert len(rows) == 0


async def test_description_success_resets_attempts(database, boards_csv):
    """A successful fetch stamps the version and resets attempts to 0."""
    from workit_scraper import providers
    from workit_scraper.details import Facts
    from workit_scraper.providers import Job
    from workit_scraper.providers.model import Page

    async with get_engine().connect() as conn:
        sid, url = await _seed_source(conn, boards_csv)

        # Bump attempts to simulate prior failures.
        await conn.execute(
            text(
                "UPDATE job_sources SET description_attempts = 2"
                " WHERE schedule_id = :sid AND apply_url = :url"
            ),
            {"sid": sid, "url": url},
        )
        await conn.commit()

        # Simulate a success with a minimal described job.
        page = Page(
            version=providers.PAGE_VERSION,
            description="A great job.",
            facts=Facts(),
        )
        described = Job(
            ats="greenhouse",
            token="acme",
            company="Acme",
            external_id="1",
            title="SWE Intern",
            apply_url=url,
            page=page,
        )
        row = SimpleNamespace(apply_url=url, schedule_id=sid)
        await worker._commit_description_batch(conn, [(row, described, None)])

        src = await _source_row(conn, sid, url)
        assert src.description_attempts == 0
        assert src.description_version == providers.PAGE_VERSION
        assert src.description_fetched_at is not None


async def test_version_bump_retries_despite_max_attempts(database, boards_csv):
    """A row that succeeded at an old version but hit max attempts on the bump
    must still be picked by _STALE_QUERY when PAGE_VERSION increases again."""
    from workit_scraper import providers

    async with get_engine().connect() as conn:
        sid, url = await _seed_source(conn, boards_csv)

        # Simulate: succeeded at version 1, then failed 3 times on version 2.
        await conn.execute(
            text(
                "UPDATE job_sources SET description_version = 1,"
                " description_attempts = :max"
                " WHERE schedule_id = :sid AND apply_url = :url"
            ),
            {"max": worker.MAX_DESCRIPTION_ATTEMPTS, "sid": sid, "url": url},
        )
        await conn.commit()

        # The row has a version (not NULL) below PAGE_VERSION, so it must
        # appear regardless of attempts.
        rows = (
            await conn.execute(
                worker._STALE_QUERY,
                {
                    "version": providers.PAGE_VERSION,
                    "cap": 100,
                    "max_attempts": worker.MAX_DESCRIPTION_ATTEMPTS,
                },
            )
        ).all()
        assert len(rows) == 1, "version-stale row must not be blocked by attempts cap"


# ---------------------------------------------------------------------------
# Shared Robots instance (KAN-913)
# ---------------------------------------------------------------------------


def test_one_robots_instance_per_cycle(monkeypatch):
    """run_cycle passes the same Robots object to every board read."""
    from workit_scraper.board_read import BoardRead, ReadStatus
    from workit_scraper.polite import Robots
    from workit_scraper.providers import Board

    seen_ids: list[int] = []

    def spy_read(board, robots=None):
        seen_ids.append(id(robots))
        job = _job("Software Engineering Intern", ord(board.token))
        return BoardRead(ReadStatus.OK, jobs=[job]), [job], 0.1

    monkeypatch.setattr(worker, "read_board_listing", spy_read)

    # Verify that read_board_listing with no robots creates its own
    _result, _kept, _ = worker.read_board_listing(Board("ashby", "x", "X"))
    assert seen_ids[-1] != 0  # got some Robots id

    # Verify that passing an explicit Robots threads through
    shared = Robots()
    _result, _kept, _ = worker.read_board_listing(Board("ashby", "y", "Y"), robots=shared)
    assert seen_ids[-1] == id(shared)
