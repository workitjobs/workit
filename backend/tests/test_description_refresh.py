"""Description enrichment preserves listing facts and board checkpoint isolation."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import text
from workit_scraper import providers
from workit_scraper.details import Facts
from workit_scraper.providers import Job, Page

from app.db import get_engine
from app.scraper import worker
from app.scraper.closures import update_sources
from tests.test_closures import URL_A, URL_B, _seed_posting, _seed_schedule

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "style, expected",
    [("remote", "Remote"), ("hybrid", "Hybrid"), ("onsite", "On site")],
)
def test_description_provider_receives_listing_work_style(monkeypatch, style, expected):
    row = SimpleNamespace(
        ats="rippling",
        token="acme",
        company="Acme",
        external_id="1",
        title="Intern",
        apply_url=URL_A,
        work_style=style,
    )
    describe = Mock(side_effect=lambda job: job)
    monkeypatch.setattr(providers, "describe", describe)
    robots = Mock()
    robots.allows.return_value = True

    _, job, error = worker._describe_one(row, robots)

    assert error is None
    assert job.work_style == expected
    assert describe.call_args.args[0].work_style == expected


async def test_phase_two_failure_rolls_back_before_closures(monkeypatch):
    conn = AsyncMock()
    for name, result in (
        ("sync_catalog", 0),
        ("expire_leases", 0),
        ("select_due", []),
        ("create_tasks", 0),
        ("claim_task", None),
    ):
        monkeypatch.setattr(worker, name, AsyncMock(return_value=result))
    monkeypatch.setattr(
        worker,
        "_fetch_descriptions",
        AsyncMock(side_effect=RuntimeError("commit failed")),
    )

    async def close(connection):
        connection.rollback.assert_awaited_once()
        return 2

    monkeypatch.setattr(worker, "detect_and_close", close)
    summary = await worker.run_cycle(conn)
    assert summary["jobs_closed"] == 2


def test_robots_failure_is_recorded_as_one_failed_description():
    row = SimpleNamespace(ats="greenhouse", token="acme", external_id="1")
    robots = Mock()
    robots.allows.side_effect = RuntimeError("robots unavailable")
    assert worker._describe_one(row, robots) == (row, None, "robots unavailable")


async def test_description_batches_include_partial_tail(monkeypatch):
    rows = list(range(5))
    conn = AsyncMock()
    conn.execute.return_value = SimpleNamespace(all=lambda: rows)
    monkeypatch.setattr(worker, "DESCRIPTION_BATCH_SIZE", 2)
    monkeypatch.setattr(
        worker, "_describe_one", lambda row, robots: (row, None, "failed")
    )
    commit = AsyncMock(side_effect=lambda connection, batch: (0, len(batch)))
    monkeypatch.setattr(worker, "_commit_description_batch", commit)
    summary = {"descriptions_fetched": 0, "descriptions_failed": 0}

    await worker._fetch_descriptions(conn, summary)

    batches = [call.args[1] for call in commit.await_args_list]
    assert [len(batch) for batch in batches] == [2, 2, 1]
    assert sorted(result[0] for batch in batches for result in batch) == rows
    assert summary["descriptions_failed"] == 5


async def test_no_page_is_a_failure_not_a_successful_fetch():
    conn = AsyncMock()
    row = SimpleNamespace(apply_url=URL_A, schedule_id="board")
    assert await worker._commit_description_batch(conn, [(row, None, None)]) == (0, 1)
    assert conn.execute.await_args.args[1]["fetched"] is False


async def test_stale_candidates_deduplicate_before_cap(database):
    async with get_engine().begin() as conn:
        boards = [await _seed_schedule(conn), await _seed_schedule(conn)]
        for url in (URL_A, URL_B):
            await _seed_posting(conn, url)
        for board in boards:
            await update_sources(conn, board, [(URL_A, "a"), (URL_B, "b")])
        rows = (
            await conn.execute(
                worker._STALE_QUERY, {"version": providers.PAGE_VERSION, "cap": 2}
            )
        ).all()
        assert {row.apply_url for row in rows} == {URL_A, URL_B}


async def test_description_update_preserves_work_style_and_other_board(database):
    async with get_engine().connect() as conn:
        board = await _seed_schedule(conn)
        other = await _seed_schedule(conn)
        await _seed_posting(conn, URL_A)
        await conn.execute(
            text(
                "UPDATE job_postings SET work_style = 'remote' WHERE apply_url = :url"
            ),
            {"url": URL_A},
        )
        for sid in (board, other):
            await update_sources(conn, sid, [(URL_A, "a")])
        row = SimpleNamespace(apply_url=URL_A, schedule_id=board)
        job = Job("greenhouse", "acme", "Acme", "a", "Intern", URL_A)
        job = replace(
            job, page=Page(providers.PAGE_VERSION, "Fresh description", Facts())
        )

        assert await worker._commit_description_batch(conn, [(row, job, None)]) == (
            1,
            0,
        )

        posting = (
            await conn.execute(
                text(
                    "SELECT description, work_style, salary_currency, salary_period "
                    "FROM job_postings WHERE apply_url = :url"
                ),
                {"url": URL_A},
            )
        ).one()
        assert posting.description == "Fresh description"
        assert posting.work_style == "remote"
        assert posting.salary_currency == "USD"
        assert posting.salary_period == "year"
        stamps = dict(
            (
                await conn.execute(
                    text("SELECT schedule_id, description_version FROM job_sources")
                )
            ).all()
        )
        assert stamps == {board: providers.PAGE_VERSION, other: None}


async def test_inline_upsert_stamps_newer_versions_and_preserves_other_stamps(database):
    async with get_engine().begin() as conn:
        board = await _seed_schedule(conn)
        postings = [(URL_A, "a"), (URL_B, "b")]
        await update_sources(conn, board, postings, inline_versions={URL_A: 2})
        first = (
            await conn.execute(
                text("SELECT * FROM job_sources WHERE apply_url = :url"), {"url": URL_A}
            )
        ).one()
        assert first.description_version == 2
        assert first.description_fetched_at is not None
        await update_sources(
            conn, board, postings, inline_versions={URL_A: 1, URL_B: 3}
        )
        rows = {
            row.apply_url: row
            for row in (await conn.execute(text("SELECT * FROM job_sources"))).all()
        }
        assert rows[URL_A].description_version == 2
        assert rows[URL_A].description_fetched_at == first.description_fetched_at
        assert rows[URL_B].description_version == 3
        await update_sources(conn, board, postings)
        assert (
            await conn.scalar(
                text(
                    "SELECT description_version FROM job_sources WHERE apply_url = :url"
                ),
                {"url": URL_B},
            )
            == 3
        )


@pytest.mark.parametrize(
    "old_description", [None, "Old description", "Fresh description"]
)
async def test_description_refresh_invalidates_only_changed_caches(
    database, old_description
):
    async with get_engine().connect() as conn:
        board = await _seed_schedule(conn)
        await _seed_posting(conn, URL_A)
        await update_sources(conn, board, [(URL_A, "a")])
        vector = "[" + ",".join(["1"] * 768) + "]"
        await conn.execute(
            text("""
                UPDATE job_postings
                SET description = :description,
                    embedding = CAST(:vector AS extensions.vector),
                    keywords = '[{"keyword": "Python", "kind": "skill"}]'::jsonb,
                    keywords_hash = 'cached-hash'
                WHERE apply_url = :url
            """),
            {"description": old_description, "vector": vector, "url": URL_A},
        )
        row = SimpleNamespace(apply_url=URL_A, schedule_id=board)
        job = replace(
            Job("greenhouse", "acme", "Acme", "a", "Intern", URL_A),
            page=Page(providers.PAGE_VERSION, "Fresh description", Facts()),
        )

        await worker._commit_description_batch(conn, [(row, job, None)])

        cached = (
            await conn.execute(
                text("""
                SELECT embedding::text AS embedding, keywords, keywords_hash
                FROM job_postings WHERE apply_url = :url
            """),
                {"url": URL_A},
            )
        ).one()
        if old_description == "Fresh description":
            assert cached.embedding == vector
            assert cached.keywords == [{"keyword": "Python", "kind": "skill"}]
            assert cached.keywords_hash == "cached-hash"
        else:
            assert tuple(cached) == (None, None, None)
