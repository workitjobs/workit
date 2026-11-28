"""
What an application sent (W11, routers/sent_applications.py): WorkIt Auto
Apply keeps each form's questions and answers on WorkIt at the student's
Submit, so nothing of it stays on their Mac. Real Postgres.
"""

import pytest
from sqlalchemy import text

from tests.test_tracker import (  # noqa: F401  (student is a fixture)
    _applied,
    _seed_posting,
    student,
)

pytestmark = pytest.mark.anyio

SENT = {"answers": [
    {"question": "Are you authorized to work in the US?", "answer": "Yes"},
    {"question": "Which tools have you used?", "answer": ["Git", "Docker"]},
    {"question": "Why Acme?", "answer": "I rode their trains for four years.", "ai": True},
]}


async def test_an_application_keeps_what_it_sent_and_loses_it_with_the_application(student, database):  # noqa: F811
    """Fault: a sent application was kept for a job not applied to, read back changed, replaced by a second send (a
    loop's way to fill form_questions), or outlived its application."""
    client, me = student
    queued = await _seed_posting(database)
    async with database() as session:
        await session.execute(text("INSERT INTO job_applications (applicant_id, job_id, stage, applied_at)"
                                   " VALUES (:me, :job, 'queued', NULL)"), {"me": me, "job": queued})
        await session.commit()
    job = await _applied(client, database)
    url = f"/applicants/{me}/applications/{job}/sent"

    not_sent = await client.put(f"/applicants/{me}/applications/{queued}/sent", json=SENT)
    none = await client.get(url)
    saved = await client.put(url, json=SENT)
    again = await client.put(url, json={"answers": [{"question": "Anything else?", "answer": "No"}]})
    got = (await client.get(url)).json()
    async with database() as session:
        await session.execute(text("DELETE FROM job_applications WHERE job_id = :job"), {"job": job})
        await session.commit()

    assert not_sent.status_code == 409 and none.status_code == 404
    assert saved.status_code == 204, saved.text
    assert again.status_code == 409
    assert got["answers"] == [{**a, "ai": a.get("ai", False)} for a in SENT["answers"]]
    assert (await client.get(url)).status_code == 404  # deleted with its application


async def test_each_questions_words_are_kept_once_for_every_application(student, database):  # noqa: F811
    """Fault: a question's words were stored again with each application that answered it, or an answer kept its key
    names, which made each sent application about twice its size."""
    client, me = student
    first, second = await _applied(client, database), await _applied(client, database)

    for job in (first, second):
        assert (await client.put(f"/applicants/{me}/applications/{job}/sent", json=SENT)).status_code == 204
    async with database() as session:
        kept = (await session.execute(text("SELECT count(*) FROM form_questions"))).scalar()
        stored = (await session.execute(text("SELECT answers FROM sent_applications WHERE job_id = :job"),
                                        {"job": first})).scalar()

    assert kept == 3
    assert [len(item) for item in stored] == [2, 2, 3] and all(isinstance(item[0], int) for item in stored)
    assert (await client.get(f"/applicants/{me}/applications/{second}/sent")).json()["answers"][2]["ai"] is True
