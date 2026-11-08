"""
The bank job (KAN-726, app/scripts/embed_banks.py): which banks a sweep
embeds, in what order, and what it stores. Real Postgres; `embed` is faked,
so no model runs. The listening loop around it is not tested here: the
notify it wakes on is (tests/test_bank.py).
"""

import uuid

import pytest
from sqlalchemy import text

from app.scripts import embed_banks
from app.services.matching import bank_vectors

pytestmark = pytest.mark.anyio

VECTOR = [0.1] * 768


async def _student(database, *, skill: str | None = "Python") -> uuid.UUID:
    applicant_id = uuid.uuid4()
    async with database() as session:
        await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": applicant_id})
        await session.execute(
            text("INSERT INTO applicant_profiles (id, email, full_name) VALUES (:id, :email, 'Sam Seeker')"),
            {"id": applicant_id, "email": f"sam{applicant_id.hex[:6]}@example.com"},
        )
        await session.execute(
            text("INSERT INTO experience_banks (applicant_id) VALUES (:id)"), {"id": applicant_id}
        )
        if skill:
            await session.execute(
                text("INSERT INTO bank_skills (id, applicant_id, name) VALUES (:s, :id, :n)"),
                {"s": uuid.uuid4(), "id": applicant_id, "n": skill},
            )
        await session.commit()
    return applicant_id


async def _set(database, applicant_id, sql: str) -> None:
    async with database() as session:
        await session.execute(text(f"UPDATE experience_banks SET {sql} WHERE applicant_id = :id"), {"id": applicant_id})
        await session.commit()


async def _state(database, applicant_id) -> tuple[bool, bool]:
    async with database() as session:
        bank = (await session.execute(
            text("SELECT * FROM experience_banks WHERE applicant_id = :id"), {"id": applicant_id}
        )).one()
        stale = await session.scalar(
            text("SELECT count(*) FROM experience_banks WHERE applicant_id = :id AND (embedding IS NULL"
                 " OR embedded_at IS NULL OR embedded_at <> updated_at)"),
            {"id": applicant_id},
        )
    return bank.embedding is not None, bool(stale)


@pytest.fixture
def embedded(monkeypatch):
    """Stands in for the model: records each batch and answers one vector a text."""
    batches: list[list[str]] = []

    async def embed(texts, *, timeout=None, query=False):
        assert query
        batches.append(list(texts))
        return [VECTOR for _ in texts]

    monkeypatch.setattr(embed_banks, "embed", embed)
    return batches


async def test_a_sweep_embeds_new_banks_first_then_the_oldest_change(database, embedded):
    changed = await _student(database, skill="Go")
    new = await _student(database, skill="Rust")
    fresh = await _student(database, skill="C")
    # `changed` has a vector from an older version; `fresh` one of its current.
    await _set(database, changed, "embedding = CAST(:v AS extensions.vector), embedded_at = updated_at - interval '1 day'"
               .replace(":v", "'[" + ",".join(["0.2"] * 768) + "]'"))
    await _set(database, fresh, "embedding = CAST(:v AS extensions.vector), embedded_at = updated_at"
               .replace(":v", "'[" + ",".join(["0.2"] * 768) + "]'"))

    assert await embed_banks.sweep(embed_banks.get_sessionmaker()) == 2
    [batch] = embedded
    assert [("Rust" in t, "Go" in t) for t in batch] == [(True, False), (False, True)]
    assert await _state(database, new) == (True, False)
    assert await _state(database, changed) == (True, False)
    assert await _state(database, fresh) == (True, False)


async def test_an_empty_bank_is_passed_over(database, embedded):
    empty = await _student(database, skill=None)
    assert await embed_banks.sweep(embed_banks.get_sessionmaker()) == 0
    assert embedded == []
    assert await _state(database, empty) == (False, True)


async def test_a_failed_embed_stores_nothing(database, monkeypatch):
    student = await _student(database)

    async def down(texts, *, timeout=None, query=False):
        return None

    monkeypatch.setattr(embed_banks, "embed", down)
    assert await embed_banks.sweep(embed_banks.get_sessionmaker()) == 0
    assert await _state(database, student) == (False, True)


async def test_a_bank_changed_while_embedding_stays_stale(database, monkeypatch):
    student = await _student(database)

    async def embed_then_change(texts, *, timeout=None, query=False):
        # The student saves while the model runs.
        await _set(database, student, "updated_at = now() + interval '1 second'")
        return [VECTOR for _ in texts]

    monkeypatch.setattr(embed_banks, "embed", embed_then_change)
    assert await embed_banks.sweep(embed_banks.get_sessionmaker()) == 0
    assert await _state(database, student) == (False, True)


async def test_store_keeps_updated_at_and_stamps_the_version(database):
    student = await _student(database)
    async with database() as session:
        read_at = await session.scalar(
            text("SELECT updated_at FROM experience_banks WHERE applicant_id = :id"), {"id": student}
        )
        assert await bank_vectors.store(session, student, read_at, VECTOR)
        await session.commit()
        row = (await session.execute(
            text("SELECT updated_at, embedded_at FROM experience_banks WHERE applicant_id = :id"), {"id": student}
        )).one()
    assert row.updated_at == row.embedded_at == read_at


def test_it_refuses_to_run_with_no_provider(monkeypatch, capsys):
    from app.config import Settings

    monkeypatch.setattr(embed_banks, "get_settings", lambda: Settings(_env_file=None, embedding_provider="none"))
    assert embed_banks.main(["--once"]) == 1
    assert "EMBEDDING_PROVIDER is none" in capsys.readouterr().err
