"""Exercise the recommendation queries through pgvector's real bind
processor, with a stand-in session that records each statement. The
database tests are in tests/test_recommended.py."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pgvector.sqlalchemy import HALFVEC, VECTOR
from sqlalchemy.dialects.postgresql.asyncpg import dialect

from app.deps import AccountType
from app.models.dto import bank_section
from app.queries.jobs import recommendations
from app.routers import jobs
from app.services.bank import Bank, Entry
from tests.test_jobs import ROW


def _bank(skills):
    """A bank with these skills and one project, so it is never empty."""
    project = SimpleNamespace(section=bank_section.projects, title="Maze robot",
                              organization=None, field_of_study=None, degree=None,
                              start_month=None, end_month=None, award_date=None, end_kind=None)
    return Bank(entries=[Entry(row=project, bullets=[])],
                skills=[SimpleNamespace(name=s) for s in skills])


def _setup(monkeypatch, skills, embedding):
    monkeypatch.setattr(jobs, "load_bank", AsyncMock(return_value=_bank(skills)))
    monkeypatch.setattr(recommendations, "load_identity", AsyncMock(return_value=SimpleNamespace(remove=lambda t: t)))
    return SimpleNamespace(embedding=embedding, updated_at=datetime.now(UTC))


class Session:
    """Answers score_jobs' statements: each candidates query with
    `candidates` (as the index would, then as the exact ranking would), the
    read with `rows`. Keeps each statement compiled for asyncpg."""

    def __init__(self, bank_row, candidates, rows):
        self.bank_row, self.candidates, self.rows = bank_row, candidates, rows
        self.statements = []
        self.get = AsyncMock(return_value=bank_row)
        self.commit = AsyncMock()

    async def execute(self, query):
        compiled = query.compile(dialect=dialect())
        self.statements.append(compiled)
        sql = str(compiled)
        if "set_config" in sql:
            return Mock()
        if "set_name" in sql:
            return [SimpleNamespace(set_name="all", id=job_id) for job_id in self.candidates]
        if "matched_skills" in sql:
            return Mock(all=Mock(return_value=self.rows))
        return Mock()  # the update that stores a new bank embedding

    def sql(self, part: str) -> list[str]:
        return [str(s) for s in self.statements if part in str(s)]


def _scored(db, applicant_id, filters=None):
    return asyncio.run(jobs.fetch_recommended(
        db, SimpleNamespace(id=applicant_id, account_type=AccountType.APPLICANT),
        filters=filters or jobs.JobFilters(), limit=20,
    ))


@pytest.mark.parametrize("skills", [["Python", "SQL", "python", "  "], []])
def test_skill_coverage_is_partial_and_independent_of_other_results(monkeypatch, skills):
    applicant_id = uuid4()
    bank_row = _setup(monkeypatch, skills, [.125] * 768)
    posted = datetime.now(UTC)
    target = SimpleNamespace(**vars(ROW), semantic=.8,
                             matched_skills=["python", None] if skills else None, _posted_at=posted)
    other = SimpleNamespace(**{**vars(target), "id": uuid4(), "matched_skills": ["python", "SQL"] if skills else None})

    def run(rows):
        db = Session(bank_row, [row.id for row in rows], rows)
        return _scored(db, applicant_id), db

    alone = run([target])[0][0]
    together, db = run([target, other])
    same = next(job for job in together if job.id == str(ROW.id))
    assert alone.score_breakdown.skill_overlap.value == same.score_breakdown.skill_overlap.value
    assert alone.score_breakdown.skill_overlap.weight == same.score_breakdown.skill_overlap.weight
    assert alone.score_breakdown.skill_overlap.value == (.5 if skills else 0)
    assert alone.match == same.match
    if skills:
        [sql] = db.sql("matched_skills")
        assert sql.count("plainto_tsquery") == 2
        assert sql.count("@@") == 2
        assert "ts_rank" not in sql
        assert together[0].id == str(other.id)


@pytest.mark.parametrize("stored", [True, False])
def test_recommendation_vector_can_be_bound(monkeypatch, stored):
    applicant_id = uuid4()
    vector = [0.125] * 768
    bank_row = _setup(monkeypatch, ["Python"], vector if stored else None)
    embed = AsyncMock(return_value=[vector])
    monkeypatch.setattr(recommendations, "embed", embed)
    row = SimpleNamespace(**vars(ROW), semantic=0.8, matched_skills=["Python"], _posted_at=ROW.posted_at)
    db = Session(bank_row, [ROW.id], [row])

    result = _scored(db, applicant_id)
    assert len(result) == 1
    payload = result[0].model_dump(mode="json")
    breakdown = payload["score_breakdown"]
    assert payload["match"] == breakdown["final_score"]
    assert breakdown["semantic"]["value"] == 0.8
    assert breakdown["semantic"]["weight"] == 0.45
    assert breakdown["semantic"]["points"] > 0
    # The bank reaches the index's query as a halfvec and the read as a
    # vector, each bound whole.
    bound = {}
    for compiled in db.statements:
        for name, value in compiled.params.items():
            bind_type = compiled.binds[name].type
            if isinstance(bind_type, VECTOR | HALFVEC):
                text = bind_type.bind_processor(dialect())(value)
                bound.setdefault(type(bind_type).__name__, []).append(len(text.strip("[]").split(",")))
    assert set(bound) == {"VECTOR", "HALFVEC"}
    assert {n for lengths in bound.values() for n in lengths} == {768}
    if stored:
        embed.assert_not_awaited()
        db.commit.assert_not_awaited()
    else:
        embed.assert_awaited_once()
        db.commit.assert_awaited_once()


def test_candidates_come_from_the_index_and_short_sets_are_ranked_exactly(monkeypatch):
    # KAN-915: the nearest CANDIDATES by the halfvec the HNSW index holds,
    # with sorting off so the planner reads the index; a set the index can't
    # fill is ranked again by the full vector, the jobs with none last.
    applicant_id = uuid4()
    db = Session(_setup(monkeypatch, ["Python"], [0.125] * 768), [], [])
    _scored(db, applicant_id)

    first, exact = db.sql("set_name")
    assert "ORDER BY CAST(job_postings.embedding AS HALFVEC(768)) <=>" in first
    assert "LIMIT" in first
    order = db.sql("set_config")
    assert "'enable_sort', 'off'" in order[0] and "'enable_sort', 'on'" in order[1]
    # NULLS LAST matters: Postgres puts NULL first under DESC, so jobs with no
    # embedding would otherwise fill the cap ahead of the real matches.
    assert "job_postings.embedding <=> $" in exact
    assert ") DESC NULLS LAST, job_postings.posted_at DESC NULLS LAST, job_postings.id" in exact
    assert "HALFVEC" not in exact


def test_a_full_set_is_not_ranked_again(monkeypatch):
    applicant_id = uuid4()
    monkeypatch.setattr(recommendations, "CANDIDATES", 2)
    db = Session(_setup(monkeypatch, ["Python"], [0.125] * 768), [uuid4(), uuid4()], [])
    _scored(db, applicant_id)
    assert len(db.sql("set_name")) == 1


def test_named_jobs_and_a_bank_with_no_vector_skip_the_index(monkeypatch):
    applicant_id = uuid4()
    monkeypatch.setattr(recommendations, "embed", AsyncMock(return_value=None))
    db = Session(_setup(monkeypatch, ["Python"], None), [], [])
    _scored(db, applicant_id)
    [newest] = db.sql("set_name")
    assert "ORDER BY job_postings.posted_at DESC NULLS LAST" in newest
    assert not db.sql("set_config")

    db = Session(_setup(monkeypatch, ["Python"], [0.125] * 768), [], [])
    _scored(db, applicant_id, jobs.JobFilters(job_ids=[ROW.id]))
    [exact] = db.sql("set_name")
    assert "HALFVEC" not in exact and "DESC NULLS LAST" in exact
    assert not db.sql("set_config")


def test_skills_are_matched_only_on_the_candidates_reading_each_text_once(monkeypatch):
    # The candidates query reads no text; the read matches every skill on
    # the picked rows, against each row's terms read once (KAN-915: once per
    # skill was 129,000 TOAST reads for 258 skills).
    applicant_id = uuid4()
    db = Session(_setup(monkeypatch, ["Python", "SQL"], [0.125] * 768), [ROW.id], [])
    _scored(db, applicant_id)
    assert all("plainto_tsquery" not in sql for sql in db.sql("set_name"))
    [read] = db.sql("matched_skills")
    assert read.count("plainto_tsquery") == 2
    assert read.count("strip(job_postings.fts)") == 1
    assert "OFFSET" in read
    assert "picked._terms @@ plainto_tsquery" in read


def test_the_bank_embed_in_a_request_has_a_short_timeout(monkeypatch):
    applicant_id = uuid4()
    embed = AsyncMock(return_value=None)
    monkeypatch.setattr(recommendations, "embed", embed)
    _scored(Session(_setup(monkeypatch, ["Python"], None), [], []), applicant_id)
    assert embed.await_args.kwargs["timeout"] == recommendations.REQUEST_EMBED_SECONDS
