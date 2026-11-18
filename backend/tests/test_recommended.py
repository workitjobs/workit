"""
Seam-1 tests for GET /jobs/recommended (KAN-212): the recommender reads the
experience bank, never an uploaded resume. A bank with no vector is embedded
on its first request; a changed one keeps its stale vector for the bank job
(KAN-726). What is sent is checked at `embed`, which the route calls, so no
network is needed.
"""

import uuid

import httpx
import pytest
from sqlalchemy import text

from app.deps import get_current_account, get_signed_in_applicant_id
from app.main import app
from app.schemas.auth import AccountType, AuthenticatedAccount

pytestmark = pytest.mark.anyio

VECTOR = [0.1] * 768


async def _seed_applicant(session) -> uuid.UUID:
    applicant_id = uuid.uuid4()
    await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": applicant_id})
    await session.execute(
        text(
            "INSERT INTO applicant_profiles (id, email, full_name, phone_number)"
            " VALUES (:id, :email, 'Sam Seeker', '631-555-0100')"
        ),
        {"id": applicant_id, "email": f"sam{applicant_id.hex[:6]}@example.com"},
    )
    await session.commit()
    return applicant_id


@pytest.fixture
def gemini(monkeypatch):
    """Stands in for Gemini: records each text sent and answers one vector."""
    sent: list[str] = []

    async def embed(texts, *, timeout=None, query=False):
        assert query, "a bank is always embedded as a query (KAN-726)"
        sent.extend(texts)
        return [VECTOR for _ in texts]

    monkeypatch.setattr("app.queries.jobs.recommendations.embed", embed)
    return sent


@pytest.fixture
async def student(database):
    """A signed-in applicant and an API client. Yields (client, applicant id, email)."""
    async with database() as session:
        applicant_id = await _seed_applicant(session)
    email = f"sam{applicant_id.hex[:6]}@example.com"
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=applicant_id,
        email=email,
        full_name="Sam Seeker",
        account_type=AccountType.APPLICANT,
        onboarding_completed=True,
    )
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, applicant_id, email
    finally:
        app.dependency_overrides.pop(get_current_account, None)


async def _add(client, applicant_id, path: str, body: dict) -> None:
    res = await client.post(f"/applicants/{applicant_id}/bank/{path}", json=body)
    assert res.status_code == 201, res.text


def _recommended(client, applicant_id):
    return client.get(f"/jobs/recommended/{applicant_id}")


async def test_a_new_bank_is_embedded_once_and_a_change_waits_for_the_bank_job(student, gemini):
    # KAN-726: a request embeds only a bank that never had a vector; after a
    # change it keeps scoring on the stale one, which the bank job replaces.
    client, me, _ = student
    await _add(client, me, "skills", {"name": "Python"})

    assert (await _recommended(client, me)).status_code == 200
    assert (await _recommended(client, me)).status_code == 200
    assert len(gemini) == 1  # kept, not remade, while the bank is unchanged

    await _add(client, me, "skills", {"name": "ROS"})
    assert (await _recommended(client, me)).status_code == 200
    assert len(gemini) == 1


async def test_the_embedding_input_follows_the_spec(student, gemini, database):
    client, me, email = student
    # An upload the recommender must ignore.
    async with database() as session:
        await session.execute(
            text(
                "INSERT INTO resumes (id, applicant_id, status, raw_text)"
                " VALUES (:id, :a, 'parsed', 'Sam Seeker. Skills: COBOL')"
            ),
            {"id": uuid.uuid4(), "a": me},
        )
        await session.commit()

    await _add(client, me, "skills", {"name": "Python", "group": "Languages"})
    await _add(client, me, "skills", {"name": "ROS"})
    await _add(client, me, "entries", {
        "section": "education", "title": "Stony Brook University", "location": "Stony Brook, NY",
        "degree": "BS", "field_of_study": "Computer Science", "gpa": 3.7,
        "start_month": "2023-09", "end_month": "2027-05", "end_kind": "expected",
    })
    await _add(client, me, "entries", {
        "section": "experience", "title": "Robotics Intern", "organization": "Acme",
        "location": "Austin, TX", "start_month": "2025-06", "end_kind": "present",
        "bullets": ["Wrote ROS nodes for arms.", f"Mailed {email} weekly reports."],
    })
    await _add(client, me, "entries", {
        "section": "projects", "title": "WorkIt", "link": "https://github.com/sam/workit",
        "start_month": "2024-01", "end_month": "2024-05",
        "bullets": ["Built a job board."],
    })

    assert (await _recommended(client, me)).status_code == 200
    assert gemini == [(
        "Skills: Python, ROS\n"
        "Experience: Robotics Intern, Acme\n"
        "- Wrote ROS nodes for arms.\n"
        "- Mailed [email] weekly reports.\n"
        "Projects: WorkIt\n"
        "- Built a job board."
    )]


async def test_the_embedding_input_is_cut_at_6000_characters(student, gemini):
    client, me, _ = student
    for i in range(20):
        await _add(client, me, "entries", {
            "section": "experience", "title": f"Role {i}", "organization": f"Org {i}",
            "bullets": ["Did a long and detailed piece of work " * 10] * 3,
        })
    assert (await _recommended(client, me)).status_code == 200
    (sent,) = gemini
    assert 5900 < len(sent) <= 6000


async def test_only_experience_entries_count_toward_years(student, gemini, database):
    client, me, _ = student
    async with database() as session:
        await session.execute(
            text(
                "INSERT INTO job_postings (title, company_name, apply_url, status, experience_level, min_years_experience)"
                " VALUES ('Engineer', 'Acme', 'https://jobs.example/e', 'published', 'new_grad', 3)"
            )
        )
        await session.commit()
    # Two years of Experience, plus three of Leadership that must not count.
    await _add(client, me, "entries", {
        "section": "experience", "title": "Engineer", "organization": "Acme",
        "start_month": "2023-01", "end_month": "2024-12",
    })
    await _add(client, me, "entries", {
        "section": "leadership", "title": "President", "organization": "Club",
        "start_month": "2020-01", "end_month": "2022-12",
    })

    (job,) = (await _recommended(client, me)).json()
    assert {
        "text": "Asks for 3+ years",
        "detail": "Asks for 3+ years experience",
        "met": False,
    } in job["highlights"]


async def test_an_empty_bank_has_no_recommendations(student, gemini):
    client, me, _ = student
    res = await _recommended(client, me)
    assert res.status_code == 404
    assert "experience bank" in res.json()["detail"]
    assert gemini == []


async def test_another_students_recommendations_are_forbidden(student, database):
    client, _, _ = student
    async with database() as session:
        other = await _seed_applicant(session)
    assert (await _recommended(client, other)).status_code == 403


async def _seed_postings(database) -> dict[str, str]:
    """Three listed postings: one auto apply fills, posted today; one it
    can't, posted today; one it can't, posted 200 days ago. Ids by name."""
    ids = {}
    async with database() as session:
        for name, url, days in [
            ("filled", "https://boards.greenhouse.io/acme/jobs/1", 0),
            ("recent", "https://jobs.example/recent", 0),
            ("old", "https://jobs.example/old", 200),
        ]:
            ids[name] = str((await session.execute(
                text(
                    "INSERT INTO job_postings (title, company_name, apply_url, status, experience_level, posted_at)"
                    " VALUES ('Python Engineer', 'Acme', :url, 'published', 'new_grad',"
                    " now() - make_interval(days => :days)) RETURNING id"
                ),
                {"url": url, "days": days},
            )).scalar())
        await session.commit()
    return ids


def _home(client, applicant_id):
    return client.get(f"/jobs/recommended/{applicant_id}/home?posted_within=30&min_match=0")


async def test_home_matches_are_the_three_recommended_lists(student, gemini, database):
    # One pass (KAN-425) must give each list its own GET /jobs/recommended
    # call: the top, the ones auto apply fills, and the recent ones' dates.
    client, me, _ = student
    ids = await _seed_postings(database)
    await _add(client, me, "skills", {"name": "Python"})

    res = await _home(client, me)
    assert res.status_code == 200, res.text
    home = res.json()

    def listed(query: str):
        return client.get(f"/jobs/recommended/{me}?{query}")

    top, filled, recent = [(await listed(q)).json() for q in (
        "limit=12", "limit=12&auto_apply=true", "posted_within=30&min_match=0&limit=500",
    )]
    assert [j["id"] for j in home["top"]] == [j["id"] for j in top]
    assert [j["match"] for j in home["top"]] == [j["match"] for j in top]
    assert [j["id"] for j in home["auto_apply"]] == [j["id"] for j in filled] == [ids["filled"]]
    assert home["strong_posted"] == [j["posted_at"] for j in recent]
    assert len(home["strong_posted"]) == 2


async def test_home_matches_are_kept_until_the_bank_or_applied_jobs_change(
    student, gemini, database, monkeypatch
):
    from app.queries.jobs import home

    client, me, _ = student
    ids = await _seed_postings(database)
    await _add(client, me, "skills", {"name": "Python"})
    passes = []
    score_job_sets = home.score_job_sets

    async def counted(*args, **kwargs):
        passes.append(1)
        return await score_job_sets(*args, **kwargs)

    monkeypatch.setattr(home, "score_job_sets", counted)

    assert (await _home(client, me)).status_code == 200
    assert (await _home(client, me)).status_code == 200
    assert len(passes) == 1  # the return visit is served from the kept result

    await _add(client, me, "skills", {"name": "SQL"})
    assert (await _home(client, me)).status_code == 200
    assert len(passes) == 2  # a bank change scores again

    async with database() as session:
        await session.execute(
            text("INSERT INTO job_applications (applicant_id, job_id, stage) VALUES (:a, :j, 'applied')"),
            {"a": me, "j": ids["recent"]},
        )
        await session.commit()
    res = await _home(client, me)
    assert len(passes) == 3  # so does marking a job applied, which drops out
    assert ids["recent"] not in [j["id"] for j in res.json()["top"]]


async def test_another_students_home_matches_are_forbidden(student, database):
    client, _, _ = student
    async with database() as session:
        other = await _seed_applicant(session)
    assert (await _home(client, other)).status_code == 403


def _vector(near: int) -> str:
    """A job vector whose first `near` of 768 values agree with VECTOR's sign:
    768 is the bank's own direction, fewer is further from it."""
    return "[" + ",".join(["0.1"] * near + ["-0.1"] * (768 - near)) + "]"


async def _seed_vectors(database) -> dict[str, str]:
    """Listed postings at known distances from the bank's VECTOR, and one the
    import has not embedded yet. "far" and "none" are the recent ones. Ids
    by name."""
    ids = {}
    async with database() as session:
        for name, near, days in [
            ("nearest", 768, 200), ("near", 700, 200), ("far", 500, 0),
            ("farthest", 300, 200), ("none", None, 0),
        ]:
            ids[name] = str((await session.execute(
                text(
                    "INSERT INTO job_postings (title, company_name, apply_url, status, experience_level,"
                    " posted_at, embedding) VALUES ('Engineer', 'Acme', :url, 'published', 'new_grad',"
                    " now() - make_interval(days => :days), CAST(:vector AS vector))"
                    " RETURNING id"
                ),
                {"url": f"https://jobs.example/{name}", "days": days,
                 "vector": None if near is None else _vector(near)},
            )).scalar())
        await session.commit()
    return ids


async def test_the_candidates_are_the_nearest_jobs_from_the_index(student, gemini, database, monkeypatch):
    # KAN-915: a set's CANDIDATES are its nearest jobs by the HNSW index; a
    # job with no vector comes in only when the index can't fill the set.
    from app.queries.jobs import recommendations

    client, me, _ = student
    ids = await _seed_vectors(database)
    await _add(client, me, "skills", {"name": "Python"})
    monkeypatch.setattr(recommendations, "CANDIDATES", 2)

    res = await client.get(f"/jobs/recommended/{me}")
    assert res.status_code == 200, res.text
    assert {j["id"] for j in res.json()} == {ids["nearest"], ids["near"]}

    # Two recent jobs, one with a vector: the index finds one, so the set is
    # ranked exactly over its own jobs, the one with no vector after it.
    res = await client.get(f"/jobs/recommended/{me}?posted_within=30")
    assert {j["id"] for j in res.json()} == {ids["far"], ids["none"]}


async def test_the_nearest_query_reads_the_hnsw_index(database):
    # The ORDER BY must be spelled as the index's expression, or the planner
    # sorts every listed job's vector, read from TOAST (45 s on the shared
    # database). Sorting off, as _candidates turns it off.
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    from app.models.jobs import Job_Post
    from app.queries.jobs import recommendations
    from app.queries.jobs.filters import LISTED

    query = (
        select(Job_Post.id).where(LISTED)
        .order_by(recommendations.JOB_HALF.cosine_distance(VECTOR))
        .limit(recommendations.CANDIDATES)
    )
    sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    async with database() as session:
        await session.execute(recommendations._INDEX_ORDER)
        plan = "\n".join((await session.execute(text("EXPLAIN " + sql))).scalars())
        await session.execute(recommendations._PLANNER_DEFAULTS)
        assert (await session.execute(text("SHOW enable_sort"))).scalar() == "on"
    assert "job_postings_embedding_hnsw_idx" in plan, plan


async def test_best_match_is_kept_for_load_more_and_back(student, gemini, database, monkeypatch):
    # KAN-915: the scored list is kept per applicant and filters, so the next
    # page, Back and another min_match read it; a change to the bank or the
    # Tracker, or other filters, score again.
    from app.routers import jobs

    client, me, _ = student
    await _seed_vectors(database)
    await _add(client, me, "skills", {"name": "Python"})
    passes = []
    score_jobs = jobs.score_jobs

    async def counted(*args, **kwargs):
        passes.append(1)
        return await score_jobs(*args, **kwargs)

    monkeypatch.setattr(jobs, "score_jobs", counted)
    # The Jobs page's filters read the viewer on their own (read_filters).
    monkeypatch.setitem(app.dependency_overrides, get_signed_in_applicant_id, lambda: me)

    def page(query: str = ""):
        return client.get(f"/jobs/recommended/{me}?limit=2{query}")

    first = (await page()).json()
    assert len(passes) == 1
    assert (await page()).json() == first  # Back, or the same page again
    more = (await page("&offset=2")).json()  # Load More
    assert len(passes) == 1
    assert len({j["id"] for j in first + more}) == 4
    strong = (await page("&min_match=50")).json()
    assert all(j["match"] >= 50 for j in strong)
    assert len(passes) == 1

    await page("&posted_within=30")
    assert len(passes) == 2  # other filters are another list

    async with database() as session:
        await session.execute(
            text("INSERT INTO job_applications (applicant_id, job_id, stage, applied_at)"
                 " VALUES (:a, :j, 'saved', NULL)"),
            {"a": me, "j": first[0]["id"]},
        )
        await session.commit()
    after_save = (await page()).json()
    assert len(passes) == 3  # a Save takes the job off the Jobs page
    assert first[0]["id"] not in [j["id"] for j in after_save]

    await _add(client, me, "skills", {"name": "SQL"})
    await page()
    assert len(passes) == 4  # a bank change scores again
