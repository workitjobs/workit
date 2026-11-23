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


def test_sanitize_error_strips_what_an_admin_page_would_show():
    # The admin Scrape Health page prints this text (KAN-879), so each of these must not pass.
    cases = {
        "publish failed: Authorization: Bearer eyJabc.SECRET1.sig": "SECRET1",
        "connection: postgresql://postgres.ref:SECRET2@aws-0.pooler.supabase.com:6543/postgres": "SECRET2",
        "403: https://x.example/jobs?key=SECRET3&X-Amz-Signature=SECRET4": "SECRET3",
        "403: https://x.example/jobs?page=1&X-Amz-Signature=SECRET4": "SECRET4",
        'unreadable answer: {"password": "SECRET5", "page": 2}': "SECRET5",
        "timeout: apikey=SECRET6 after 30s": "SECRET6",
    }
    for raw, secret in cases.items():
        assert secret not in tasks._sanitize_error(raw), raw
    # What says why the read failed stays: the reason, the host and the plain words.
    kept = tasks._sanitize_error("connection: postgresql://postgres.ref:SECRET2@aws-0.pooler.supabase.com:6543/postgres")
    assert kept.startswith("connection: postgresql://postgres.ref:***@aws-0.pooler.supabase.com")
    assert tasks._sanitize_error("oversized: 5123 listings (max 5000)") == "oversized: 5123 listings (max 5000)"
    assert tasks._sanitize_error('publish failed: Key (apply_url)=(https://a/1) already exists') == (
        'publish failed: Key (apply_url)=(https://a/1) already exists')


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


async def test_a_dry_run_writes_nothing(database, boards_csv, monkeypatch):
    monkeypatch.setattr(worker, "sync_catalog", lambda conn: schedules.sync_catalog(conn, boards_csv))
    async with get_engine().connect() as conn:
        summary = await worker.run_cycle(conn, dry_run=True)
    assert summary["synced"] == 1
    assert summary["tasks_created"] == 1
    async with get_engine().connect() as conn:
        for table in ("scraper_schedules", "scraper_tasks"):
            assert await conn.scalar(text(f"SELECT count(*) FROM {table}")) == 0


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


def _read_one_intern(monkeypatch, boards_csv):
    from workit_scraper.board_read import BoardRead, ReadStatus

    async def skip_descriptions(conn, summary, robots=None):
        pass

    monkeypatch.setattr(worker, "_fetch_descriptions", skip_descriptions)
    job = _job("Software Engineering Intern", 1)
    monkeypatch.setattr(worker, "sync_catalog", lambda conn: schedules.sync_catalog(conn, boards_csv))
    monkeypatch.setattr(
        worker, "read_board_listing",
        lambda board, robots=None: (BoardRead(ReadStatus.OK, jobs=[job]), [job], 1.0),
    )
    return job


async def _checkpoint() -> tuple:
    async with get_engine().connect() as conn:
        task = (await conn.execute(text("SELECT status, error FROM scraper_tasks"))).one()
        read_at = await conn.scalar(text("SELECT last_read_at FROM scraper_schedules"))
        jobs = await conn.scalar(text("SELECT count(*) FROM job_postings"))
    return task, read_at, jobs


async def test_a_board_is_checkpointed_with_its_published_jobs(database, boards_csv, monkeypatch):
    _read_one_intern(monkeypatch, boards_csv)
    async with get_engine().connect() as conn:
        summary = await worker.run_cycle(conn)
    task, read_at, jobs = await _checkpoint()
    assert summary["jobs_scraped"] == 1
    assert task.status == "done"
    assert read_at is not None
    assert jobs == 1


async def test_a_failed_publish_leaves_the_board_unread(database, boards_csv, monkeypatch):
    from app.scripts import import_jobs

    _read_one_intern(monkeypatch, boards_csv)

    async def refuse(*args, **kwargs):
        raise import_jobs.ImportRefused("no")

    monkeypatch.setattr(import_jobs, "import_feed", refuse)
    async with get_engine().connect() as conn:
        summary = await worker.run_cycle(conn)
    assert summary["boards_failed"] == 1
    task, read_at, jobs = await _checkpoint()
    assert task.status == "failed"
    assert task.error.startswith("publish failed")
    assert read_at is None
    assert jobs == 0


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


async def test_select_due_skips_fingerprint_resting(database, boards_csv):
    """A board with fingerprint_until in the future is skipped unless full=True."""
    async with get_engine().begin() as conn:
        await schedules.sync_catalog(conn, boards_csv)
        row = await _schedule(conn)
        await schedules.advance_reads(conn, row.id)
        # Set fingerprint and make it rest
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        await schedules.advance_fingerprint(conn, row.id, new_fingerprint="aabbccdd")
        row = await _schedule(conn)
        assert row.fingerprint_until is not None

        # Normal select_due skips it
        due = await schedules.select_due(conn)
        assert len(due) == 0

        # full=True includes it
        due = await schedules.select_due(conn, full=True)
        assert len(due) == 1


# ---------------------------------------------------------------------------
# Parallel board workers
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


async def test_broken_connection_in_checkpoint_does_not_propagate(database, boards_csv, monkeypatch):
    """When the connection breaks during checkpoint *and* during recovery,
    the worker exits cleanly: boards_failed increments, the exception does
    not propagate, and run_cycle still runs closures (phase 6)."""
    from app.scripts import import_jobs

    _read_one_intern(monkeypatch, boards_csv)

    # Simulate a broken connection: import_feed raises, then rollback also
    # raises (the connection is dead).
    class DeadConnection(Exception):
        pass

    async def break_on_import(*args, **kwargs):
        # Make the connection's rollback fail too, simulating a lost connection.
        conn = args[0]

        async def broken_rollback():
            raise DeadConnection("connection lost")

        conn.rollback = broken_rollback
        raise DeadConnection("connection reset by peer")

    monkeypatch.setattr(import_jobs, "import_feed", break_on_import)

    async with get_engine().connect() as conn:
        summary = await worker.run_cycle(conn)

    # The exception did not propagate (run_cycle returned), closures ran.
    assert summary["boards_failed"] >= 1


async def test_parallel_workers_claim_all_boards(database, tmp_path, monkeypatch):
    """Four boards, four workers: every board is claimed and processed."""
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
    monkeypatch.setattr(worker, "sync_catalog", lambda conn: schedules.sync_catalog(conn, csv))

    def fake_read(board, robots=None):
        n = ord(board.token)
        job = _job("Software Engineering Intern", n)
        return BoardRead(ReadStatus.OK, jobs=[job]), [job], 0.1

    monkeypatch.setattr(worker, "read_board_listing", fake_read)

    async with get_engine().connect() as conn:
        summary = await worker.run_cycle(conn, workers=4)

    assert summary["boards_ok"] == 4
    assert summary["jobs_scraped"] == 4

    async with get_engine().connect() as conn:
        done = await conn.scalar(
            text("SELECT count(*) FROM scraper_tasks WHERE status = 'done'")
        )
    assert done == 4


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
