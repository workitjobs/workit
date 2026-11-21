"""
Write early, reuse saved answers, keep the student's edits (KAN-379), spec
seam 2: the connector driven by the official MCP client as the student's
Claude drives it, and the batch tab's calls as the extension makes them,
against this run's throwaway test database (never Supabase).

Reading a job's questions from its link is the Fill engine's, in the
extension (autofiller_extension/test/write-early.spec.ts); what reaches
WorkIt is the same PUT .../questions a tab sends, only before any tab opens.
Filling a question from a saved answer is the engine's Plan, in the
extension, with GET .../answer-bank (pipeline.answer_bank) as its Answer bank:
the student's whole bank (W11), which holds only answers to one-off
questions (a choice, a field the tab never sent, or one the Plan marks
`essay: false`) and none about one company (app/auto_apply/answer_bank.py).
"""

import uuid

import pytest

from tests.test_connector import (
    PROUD,
    WHY,
    WRITTEN,
    _api,
    _signed_in_as,
    _student_queues,
    _tab_asks,
    claude,
)
from tests.test_connector_checks import _company

pytestmark = pytest.mark.anyio

GOALS = {"name": "question_9", "label": "What are you looking to gain from an internship?", "required": True, "max_length": None}
ROBOT = "I built a line-following robot with two friends, and it placed second at a regional contest."


# A one-off choice nothing else fills (KAN-369): its answer enters the Answer bank, where a question in words the
# tab sent may be an essay and stays on its application (W11).
SHIFTS = {"name": "question_2", "label": "Which shifts can you work?", "required": True, "max_length": None,
          "kind": "choice", "options": ["Mornings", "Nights"]}


async def _pick(applicant, job: str, name: str, answer: str) -> None:
    """Their Claude's save of a choice: an option, with no plan or claim check."""
    async with claude(applicant) as client:
        result = await client.call_tool("save_answers", {"job_id": job, "answers": [{"name": name, "answer": answer}]})
    assert not result.is_error, result.content


def filed(question: dict) -> str:
    """The question's key in the Answer bank: its wording as the Fill engine matches it."""
    return " ".join(question["label"].lower().split()).strip(" *")


def theirs(question: dict, answer, own: bool = True) -> dict:
    """One bank entry as GET .../answer-bank serves it."""
    return {"question": question["label"], "answer": answer, "own": own}


@pytest.fixture
async def running():
    """The API with its lifespan running (tests/test_connector.py's)."""
    from app.deps import get_current_account
    from app.main import app

    async with app.router.lifespan_context(app):
        yield
    app.dependency_overrides.pop(get_current_account, None)


@pytest.fixture
async def applicant(database) -> uuid.UUID:
    from tests.test_built_resumes import _seed_applicant

    async with database() as session:
        return await _seed_applicant(session)


async def _bank(me: str, job: str) -> dict:
    """The saved answers a job's form may reuse, as the extension reads them for its Plan."""
    _signed_in_as(uuid.UUID(me.rsplit("/", 1)[1]))
    async with _api() as extension:
        res = await extension.get(f"{me}/applications/{job}/answer-bank")
    assert res.status_code == 200, res.text
    return res.json()


async def _student_answers(me: str, job: str, question: dict, answer: str, own: bool = True) -> None:
    """The student's words in a batch tab's field (the extension's call on their edit): `own` when
    they wrote into a field WorkIt didn't fill, or replaced what it filled; false for an edit of it."""
    res = await _student_edits(me, job, question, answer, own)
    assert res.status_code == 200, res.text


async def _student_edits(me: str, job: str, question: dict, answer: str, own: bool):
    _signed_in_as(uuid.UUID(me.rsplit("/", 1)[1]))
    async with _api() as extension:
        return await extension.put(
            f"{me}/applications/{job}/answers",
            json={"name": question["name"], "label": question["label"], "answer": answer, "own": own},
        )


async def _save(applicant, job: str, name: str, answer: str) -> None:
    async with claude(applicant) as client:
        result = await client.call_tool("save_answers", {"job_id": job, "answers": [{"name": name, "answer": answer, **WRITTEN}]})
    assert not result.is_error, result.content


async def _next_job(applicant) -> str | None:
    async with claude(applicant) as client:
        return (await client.call_tool("get_next_application", {})).structured_content["job_id"]


async def test_questions_read_at_queueing_reach_claude_before_any_tab_opens(running, applicant, database):
    # The extension read the third job's questions from its link when it was
    # queued: no tab for it has opened or filled (no PUT .../fill).
    me, (_, _, third) = await _student_queues(database, applicant, 3)
    await _tab_asks(me, third, GOALS)

    async with claude(applicant) as client:
        got = (await client.call_tool("get_next_application", {})).structured_content

    assert got["job_id"] == third
    assert [q["question"] for q in got["questions"]] == [GOALS["label"]]


async def test_an_application_with_no_question_left_unanswered_is_never_offered(running, applicant, database):
    me, (nothing, answered, by_student, left) = await _student_queues(database, applicant, 4)
    # Its form asks nothing written: no questions were sent.
    await _tab_asks(me, nothing)
    await _tab_asks(me, answered, PROUD)
    await _tab_asks(me, by_student, GOALS)
    await _tab_asks(me, left, WHY)
    await _save(applicant, answered, "question_8", ROBOT)
    # The student wrote this one in the tab before their Claude got to it.
    await _student_answers(me, by_student, GOALS, "Work on a team that ships software people use.")

    assert await _next_job(applicant) == left
    await _save(applicant, left, "question_7", "Acme builds the software I want to build.")
    assert await _next_job(applicant) is None


async def test_a_saved_answer_is_offered_to_later_forms_and_never_reaches_claude(running, applicant, database):
    """The next form's tab plans with the answer bank: the engine fills the
    saved question itself, so the tab sends only what is left to write."""
    me, (first, second) = await _student_queues(database, applicant, 2)
    await _company(database, second, "Globex")
    await _tab_asks(me, first, SHIFTS, PROUD)
    await _pick(applicant, first, SHIFTS["name"], "Nights")
    await _save(applicant, first, "question_8", ROBOT)

    bank = await _bank(me, second)
    # Saved by the question's wording, as the Fill engine's Answer bank takes it, and flagged for the student's
    # review (own: false); the answer in words stays on its application.
    assert bank == {filed(SHIFTS): theirs(SHIFTS, "Nights", own=False)}
    # The second form asks the same question in its own case and spacing, and one more.
    same = {**SHIFTS, "name": "question_3", "label": "  which SHIFTS can you work? "}
    await _tab_asks(me, second, *[q for q in (same, GOALS) if not _engine_banks(bank, q["label"])])

    async with claude(applicant) as client:
        got = (await client.call_tool("get_next_application", {})).structured_content
    assert got["job_id"] == second
    assert [q["question"] for q in got["questions"]] == [GOALS["label"]]


def _engine_banks(bank: dict, label: str) -> bool:
    """Whether the Fill engine's Answer bank lookup finds `label` (its own
    rule: any case or spacing; planner.ts, `banked`)."""
    def norm(text: str) -> str:
        return " ".join(text.lower().split()).strip(" *")

    return any(norm(filed) == norm(label) for filed in bank)


async def test_the_students_edit_replaces_the_answer_and_is_reused_from_then_on(running, applicant, database):
    me, (first, second, third) = await _student_queues(database, applicant, 3)
    for job in (first, second):
        await _tab_asks(me, job, SHIFTS)
    await _pick(applicant, first, SHIFTS["name"], "Mornings")

    await _student_answers(me, first, SHIFTS, "Nights")

    # Their pick replaces their Claude's in the application, and a later save there never replaces it.
    assert (await _tab_asks(me, first))[0]["answer"] == "Nights"
    await _pick(applicant, first, SHIFTS["name"], "Mornings")
    assert (await _tab_asks(me, first))[0]["answer"] == "Nights"
    # Their Claude answers the same question on another form, later: the student's pick stays in the bank.
    await _pick(applicant, second, SHIFTS["name"], "Mornings")
    assert (await _bank(me, third))[filed(SHIFTS)] == theirs(SHIFTS, "Nights")


async def test_an_edit_to_a_field_a_saved_answer_filled_is_kept_for_later_forms(running, applicant, database):
    # The tab sent no question for it (the engine filled it from the bank); the student changed it.
    me, (first, second) = await _student_queues(database, applicant, 2)
    await _student_answers(me, first, GOALS, "To learn how a real team ships.")

    assert await _bank(me, second) == {filed(GOALS): theirs(GOALS, "To learn how a real team ships.")}
    # It asks the student's Claude for nothing.
    assert await _next_job(applicant) is None


async def test_every_save_of_a_field_the_tab_never_sent_reaches_the_bank(running, applicant, database):
    """The extension saves after each 2-second pause: the bank holds the
    last words, never the first save's half of them."""
    me, (first, second) = await _student_queues(database, applicant, 2)
    await _student_answers(me, first, GOALS, "To learn")
    await _student_answers(me, first, GOALS, "To learn how a real team ships.")

    assert await _bank(me, second) == {filed(GOALS): theirs(GOALS, "To learn how a real team ships.")}


async def test_an_edit_is_kept_only_for_the_students_own_application(running, applicant, database):
    from tests.test_connector import _another_students_application

    me, (job,) = await _student_queues(database, applicant, 1)
    other, theirs = await _another_students_application(database)
    _signed_in_as(applicant)
    async with _api() as extension:
        not_mine = await extension.put(f"{other}/applications/{theirs}/answers", json={"name": "q", "label": "Why?", "answer": "x", "own": True})
        no_application = await extension.put(f"{me}/applications/{uuid.uuid4()}/answers", json={"name": "q", "label": "Why?", "answer": "x", "own": True})
        blank = await extension.put(f"{me}/applications/{job}/answers", json={"name": "q", "label": "Why?", "answer": "  ", "own": True})
        no_bank = await extension.get(f"{me}/applications/{uuid.uuid4()}/answer-bank")

    assert not_mine.status_code == 403
    assert no_application.status_code == 404
    assert blank.status_code == 422
    assert no_bank.status_code == 404


async def test_undo_deletes_the_students_saved_answer_and_only_theirs(running, applicant, database):
    """The guess card's Undo (KAN-369): DELETE .../answers?name= takes back an
    answer the student saved with Looks right; later forms no longer fill it."""
    from tests.test_connector import _another_students_application

    me, (first, second) = await _student_queues(database, applicant, 2)
    await _student_answers(me, first, GOALS, "Yes")
    other, theirs = await _another_students_application(database)
    _signed_in_as(applicant)
    async with _api() as extension:
        not_mine = await extension.delete(f"{other}/applications/{theirs}/answers", params={"name": GOALS["name"]})
        no_application = await extension.delete(f"{me}/applications/{uuid.uuid4()}/answers", params={"name": GOALS["name"]})
        undone = await extension.delete(f"{me}/applications/{first}/answers", params={"name": GOALS["name"]})
        again = await extension.delete(f"{me}/applications/{first}/answers", params={"name": GOALS["name"]})

    assert (not_mine.status_code, no_application.status_code) == (403, 404)
    assert (undone.status_code, again.status_code) == (204, 204)
    assert await _bank(me, second) == {}


async def test_undo_on_a_question_the_tab_sent_leaves_it_for_claude(running, applicant, database):
    me, (job,) = await _student_queues(database, applicant, 1)
    await _tab_asks(me, job, GOALS)
    await _student_answers(me, job, GOALS, "To learn how a real team ships.")
    async with _api() as extension:
        assert (await extension.delete(f"{me}/applications/{job}/answers", params={"name": GOALS["name"]})).status_code == 204

    assert (await _tab_asks(me, job))[0]["answer"] is None
    assert await _next_job(applicant) == job


async def test_an_edit_of_claudes_answer_stays_claudes_and_is_checked(running, applicant, database):
    """The student touched up the answer their Claude wrote: the words are still mostly Claude's, so
    they are kept as Claude's (never offered as the student's own, e.g. on a form that bans AI text)
    and pass the same checks as Claude's save."""
    me, (first, second, third) = await _student_queues(database, applicant, 3)
    await _company(database, second, "Globex")
    limited = {**PROUD, "max_length": 120}
    await _tab_asks(me, first, limited)
    await _save(applicant, first, "question_8", ROBOT)

    edited = ROBOT.replace("two friends", "two close friends")
    await _student_answers(me, first, limited, edited, own=False)
    too_long = await _student_edits(me, first, limited, edited + " It also won the judges' prize for its design.", own=False)
    names_globex = await _student_edits(me, first, limited, edited.replace("regional contest", "Globex contest"), own=False)

    assert (await _tab_asks(me, first))[0]["answer"] == edited
    # A question in words the tab sent may be an essay: it stays on its application (W11).
    assert await _bank(me, third) == {}
    assert too_long.status_code == 422 and "120" in too_long.text
    assert names_globex.status_code == 422 and "Globex" in names_globex.text


async def test_the_forms_own_limit_sends_a_too_long_saved_answer_back_to_claude(running, applicant, database):
    """Questions read early carry no limit, so Claude's answer was saved against none. When the tab
    sends the form's own limit, an answer over it is dropped, never filled, and Claude writes it again
    within the limit."""
    me, (job,) = await _student_queues(database, applicant, 1)
    await _tab_asks(me, job, {**PROUD, "max_length": None})
    await _save(applicant, job, "question_8", ROBOT)

    asked = await _tab_asks(me, job, {**PROUD, "max_length": 60})

    assert asked[0]["answer"] is None
    async with claude(applicant) as client:
        got = (await client.call_tool("get_next_application", {})).structured_content
    assert got["job_id"] == job
    assert got["questions"] == [{"name": "question_8", "question": PROUD["label"], "required": False, "max_length": 60, "description": None, "kind": "text", "options": None, "rewrite": None, "type": "best-project", "default_length": None}]
    # One within the limit stays.
    short = "I built a robot that placed second at a contest."
    await _save(applicant, job, "question_8", short)
    assert (await _tab_asks(me, job, {**PROUD, "max_length": 60}))[0]["answer"] == short


async def test_claudes_answer_enters_the_bank_only_if_it_holds_without_its_posting(running, applicant, database):
    """Fields the tab never sent, which a saved answer of their Claude's
    filled, touched up by the student (own false): still their Claude's
    text, so it enters the bank only if it holds on any other form."""
    from tests.test_connector import _describe

    me, (first, second) = await _student_queues(database, applicant, 2)
    await _describe(database, first, "Our robots cut warehouse costs by 75%.")
    goals = "I want to learn how a real team ships software."
    # Fine on the first application: its posting holds the number.
    await _student_answers(me, first, PROUD, "I built a robot like yours, and I would help cut costs by 75%.", own=False)
    await _student_answers(me, first, GOALS, goals, own=False)

    # On any other form the first would state a number nothing there supports.
    assert await _bank(me, second) == {filed(GOALS): theirs(GOALS, goals, own=False)}


async def test_a_form_outside_a_batch_gets_the_whole_bank_and_no_answer_about_one_company(running, applicant, database):
    """A fill outside a batch has no application, so no job: it gets the
    student's whole bank, whatever company it names. An answer about one
    company never entered it: it stays on its application (W11)."""
    me, (first,) = await _student_queues(database, applicant, 1)
    await _company(database, first, "Acme")
    await _tab_asks(me, first, WHY)
    await _student_answers(me, first, PROUD, "My own words about my robot.")  # a field the tab never sent
    await _student_answers(me, first, WHY, "Acme builds the trains I rode as a kid.")

    async def bank(query: str) -> dict:
        _signed_in_as(applicant)
        async with _api() as extension:
            res = await extension.get(f"{me}/answer-bank{query}")
        assert res.status_code == 200, res.text
        return res.json()

    mine = {filed(PROUD): theirs(PROUD, "My own words about my robot.")}
    assert await bank("") == mine
    assert await bank("?company=Globex") == mine
    assert await bank("?company=acme") == mine
    assert (await _tab_asks(me, first))[0]["answer"] == "Acme builds the trains I rode as a kid."


async def test_the_students_own_words_skip_the_writing_checks_but_not_another_employers_name(
    running, applicant, database
):
    """Checks meant for their Claude's text (machine-made words, long
    sentences, numbers) don't keep the student's own words out of the bank;
    naming the company of another of their applications still does."""
    me, (first, second, third) = await _student_queues(database, applicant, 3)
    for job, company in zip((first, second, third), ("Globex", "Hooli", "Initech")):
        await _company(database, job, company)
    # Fields the tab never sent: the engine filled them, and the student wrote over it.
    mine = ("I am passionate about robots — my team and I spent 40 nights building one that followed a line "
            "around the gym floor faster than any other robot at the contest that spring and we placed second.")
    await _student_answers(me, first, PROUD, mine)
    await _student_answers(me, first, GOALS, "I want to ship software at Initech that riders use.")

    assert await _bank(me, second) == {filed(PROUD): theirs(PROUD, mine)}
    # Initech's own form gets none either: the answer stays on the application it was written for.
    assert await _bank(me, third) == {filed(PROUD): theirs(PROUD, mine)}
