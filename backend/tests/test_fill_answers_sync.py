"""
Apply's sync of its Answer bank (KAN-746): PATCH .../fill-answers as Apply
sends it, then the answer bank as the extension reads it (GET
.../answer-bank), against this run's throwaway test database. Every value
here is made up.
"""

import datetime
import uuid

import pytest

from app.services import apply_answers
from tests.test_import_apply_profile import (  # noqa: F401
    _api,
    _get,
    _signed_in_as,
    applicant,
    running,
)

pytestmark = pytest.mark.anyio

NOW = datetime.datetime.now(datetime.UTC)
DAY = datetime.timedelta(days=1)
LANGUAGE = "What is your favorite programming language?"


def _entry(question: str, answer, at: datetime.datetime | None, source: str = "lisul", reviewed=True, **more) -> dict:
    return {"question": question, "answer": answer, "source": source, "reviewed": reviewed,
            "edited_at": at.isoformat() if at else None, **more}


async def _sync(student, answers=(), deleted=(), as_=None):
    _signed_in_as(as_ or student)
    async with _api() as apply:
        res = await apply.patch(f"/applicants/{student}/fill-answers",
                                json={"answers": list(answers), "deleted": list(deleted)})
    return res


@pytest.fixture
async def job(running, applicant, database) -> str:  # noqa: F811
    """One queued application at Hooli, whose form reads the answer bank."""
    from tests.test_connector import _student_queues
    from tests.test_connector_checks import _company

    _, (queued,) = await _student_queues(database, applicant, 1)
    await _company(database, queued, "Hooli")
    return queued


async def _bank(student, job) -> dict:
    return (await _get(student, f"/applications/{job}/answer-bank")).json()


async def test_a_synced_answer_reaches_the_extension_s_bank_and_only_the_student_s_are_own(applicant, job):  # noqa: F811
    res = await _sync(applicant, [
        _entry(LANGUAGE, "Rust, for its compiler's help.", NOW - DAY),
        _entry("What drew you to logistics?", "Watching a warehouse route its trucks.", NOW - DAY,
               source="claude", reviewed=False),
        # Hand-marked lisul but unreviewed: not the student's word yet.
        _entry("What do you build on weekends?", "Small robots that sort marbles.", NOW - DAY, reviewed=False),
        _entry("Which shifts can you work?", ["Mornings"], NOW - DAY, options=["Mornings", "Nights"]),
    ])

    assert res.status_code == 200, res.text
    assert res.json() == {"saved": 4, "deleted": 0, "kept": []}
    assert await _bank(applicant, job) == {
        LANGUAGE: {"answer": "Rust, for its compiler's help.", "own": True},
        "Which shifts can you work?": {"answer": ["Mornings"], "own": True},
        "What drew you to logistics?": {"answer": "Watching a warehouse route its trucks.", "own": False},
        "What do you build on weekends?": {"answer": "Small robots that sort marbles.", "own": False},
    }


async def test_a_newer_edit_wins_and_an_older_one_is_kept_out(applicant, job):  # noqa: F811
    await _sync(applicant, [_entry(LANGUAGE, "Go, for its tooling.", NOW - DAY)])

    older = await _sync(applicant, [_entry(LANGUAGE.upper(), "Perl.", NOW - 2 * DAY)])
    undated = await _sync(applicant, [_entry(LANGUAGE, "COBOL.", None)])

    assert older.json() == {"saved": 0, "deleted": 0, "kept": [LANGUAGE.upper()]}
    assert undated.json()["kept"] == [LANGUAGE]
    assert (await _bank(applicant, job))[LANGUAGE]["answer"] == "Go, for its tooling."

    newer = await _sync(applicant, [_entry(LANGUAGE.lower(), "Zig.", NOW)])
    assert newer.json()["saved"] == 1
    bank = await _bank(applicant, job)
    assert bank[LANGUAGE.lower()]["answer"] == "Zig." and LANGUAGE not in bank  # one entry per wording


async def test_an_answer_edited_on_workit_is_never_beaten_by_an_older_apply_answer(running, applicant, database):  # noqa: F811
    from tests.test_connector import _student_queues, _tab_asks
    from tests.test_connector_saved_answers import _student_answers

    me, (first, second) = await _student_queues(database, applicant, 2)
    question = {"name": "question_1", "label": LANGUAGE, "required": True, "max_length": None}
    await _tab_asks(me, first, question)
    await _student_answers(me, first, question, "Rust, typed on WorkIt.")  # saved now

    await _sync(applicant, [_entry(LANGUAGE, "Python, from an older Apply edit.", NOW - DAY)])
    bank = (await _get(applicant, f"/applications/{second}/answer-bank")).json()
    assert bank[LANGUAGE] == {"answer": "Rust, typed on WorkIt.", "own": True}

    # A later edit in Apply is the newer one, and wins.
    await _sync(applicant, [_entry(LANGUAGE, "Python, edited in Apply after.", datetime.datetime.now(datetime.UTC))])
    bank = (await _get(applicant, f"/applications/{second}/answer-bank")).json()
    assert bank[LANGUAGE] == {"answer": "Python, edited in Apply after.", "own": True}


async def test_a_delete_takes_an_answer_out_unless_the_stored_one_is_newer(applicant, job):  # noqa: F811
    await _sync(applicant, [_entry(LANGUAGE, "Go.", NOW - DAY), _entry("Which shifts?", "Nights", NOW - DAY)])

    res = await _sync(applicant, deleted=[{"question": LANGUAGE, "edited_at": NOW.isoformat()},
                                          {"question": "Which shifts?", "edited_at": (NOW - 2 * DAY).isoformat()}])
    emptied = await _sync(applicant, [_entry("Which shifts?", [], NOW)])  # none of its options: no answer

    assert res.json() == {"saved": 0, "deleted": 1, "kept": ["Which shifts?"]}
    assert emptied.json()["deleted"] == 1
    assert await _bank(applicant, job) == {}


async def test_only_the_student_syncs_their_own_answers(running, applicant, database):  # noqa: F811
    res = await _sync(applicant, [_entry(LANGUAGE, "Go.", NOW)], as_=uuid.uuid4())

    assert res.status_code == 403


async def test_a_sync_past_its_caps_is_refused(running, applicant, database):  # noqa: F811
    too_many = await _sync(applicant, [_entry(f"Question {n}?", "Yes.", NOW) for n in range(201)])
    too_long = await _sync(applicant, [_entry(LANGUAGE, "x" * 20001, NOW)])

    assert (too_many.status_code, too_long.status_code) == (422, 422)


def test_a_clock_ahead_of_the_server_counts_as_now():
    stored = {LANGUAGE: {"answer": "Go.", "own": True, "edited_at": NOW.isoformat()}}

    merged = apply_answers.merge(stored, [(LANGUAGE, {"answer": "Zig.", "own": True}, NOW + 365 * DAY)], NOW)

    assert apply_answers.edited_at(merged.answers[LANGUAGE]) == NOW
    later = apply_answers.merge(merged.answers, [(LANGUAGE, {"answer": "Rust.", "own": True}, NOW + DAY / 2)], NOW + DAY)
    assert later.answers[LANGUAGE]["answer"] == "Rust."
