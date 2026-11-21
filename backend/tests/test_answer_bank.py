"""
The student's Answer bank (W11, app/auto_apply/answer_bank.py): GET
.../answer-bank as the extension and WorkIt Auto Apply read it (the whole
bank, its version as the ETag, 304 when nothing changed), PATCH
.../answer-bank as the app's Answers view and Apply's drafts write it, and
what enters it from an application (one-off questions only, never one about
a company). Against this run's throwaway test database; every value is made
up.
"""

import uuid

import pytest

from app.auto_apply.answer_bank import Kept, Rule
from app.queries import answer_banks
from tests.test_connector import _student_queues, _tab_asks
from tests.test_connector_checks import _company
from tests.test_connector_saved_answers import SHIFTS as SHIFTS_ASKED
from tests.test_connector_saved_answers import _student_answers, filed
from tests.test_import_apply_profile import (  # noqa: F401  (fixtures)
    _api,
    _get,
    _signed_in_as,
    applicant,
    running,
)

pytestmark = pytest.mark.anyio

SHIFTS = "Which shifts can you work?"
REMOTE = "Are you open to working in person?"
HEARD = {"name": "question_5", "label": "How did you first hear about us?", "required": True, "max_length": None}


async def _change(student, body: dict, as_=None):
    _signed_in_as(as_ or student)
    async with _api() as app:
        return await app.patch(f"/applicants/{student}/answer-bank", json=body)


async def _read(student, version: str | None = None):
    _signed_in_as(student)
    async with _api() as reader:
        return await reader.get(f"/applicants/{student}/answer-bank",
                                headers={"If-None-Match": version} if version else {})


async def test_the_bank_is_read_whole_and_again_only_when_it_changed(running, applicant, database):  # noqa: F811
    first = await _read(applicant)
    assert (first.status_code, first.json()) == (200, {})
    assert first.headers["cache-control"] == "private, no-cache"

    same = await _read(applicant, first.headers["etag"])
    assert (same.status_code, same.content, same.headers["etag"]) == (304, b"", first.headers["etag"])

    saved = await _change(applicant, {"set": [{"question": REMOTE, "answer": "Yes", "choice": True}]})
    assert saved.status_code == 200, saved.text
    after = await _read(applicant, first.headers["etag"])
    assert after.status_code == 200
    assert after.headers["etag"] == f'"{saved.json()["version"]}"' != first.headers["etag"]
    assert after.json() == {filed({"label": REMOTE}): {"question": REMOTE, "answer": "Yes", "own": True}}
    # An application's form reads the same bank, and its version.
    _, (job,) = await _student_queues(database, applicant, 1)
    on_form = await _get(applicant, f"/applications/{job}/answer-bank")
    assert (on_form.json(), on_form.headers["etag"]) == (after.json(), after.headers["etag"])


async def test_the_app_saves_reviews_and_deletes_answers(running, applicant, database):  # noqa: F811
    res = await _change(applicant, {"set": [
        {"question": SHIFTS, "answer": ["Mornings"]},
        {"question": "What do you build on weekends?", "answer": "Small robots that sort marbles.", "review": True},
        {"question": "Which of these apply to you?", "answer": []},
    ]})
    assert res.json() | {"version": None} == {"version": None, "kept_out": {}}

    bank = (await _read(applicant)).json()
    # Claude's draft fills later forms at once, not as the student's own; [] is "none of these".
    assert bank["what do you build on weekends?"]["own"] is False
    assert bank["which of these apply to you?"] == {"question": "Which of these apply to you?", "answer": [], "own": True,
                                                    "none": True}

    # Reviewed: the app sends the entry again with no flag.
    await _change(applicant, {"set": [{"question": "What do you build on weekends?",
                                       "answer": "Small robots that sort marbles."}],
                              "delete": [SHIFTS.upper()]})
    bank = (await _read(applicant)).json()
    assert bank["what do you build on weekends?"]["own"] is True
    assert filed({"label": SHIFTS}) not in bank


async def test_claudes_draft_never_replaces_the_students_own_answer(running, applicant, database):  # noqa: F811
    await _change(applicant, {"set": [{"question": REMOTE, "answer": "No", "choice": True}]})

    res = await _change(applicant, {"set": [{"question": REMOTE, "answer": "Yes", "choice": True, "review": True}]})

    assert res.json()["kept_out"] == {REMOTE: "The student's own answer to it stays."}
    assert (await _read(applicant)).json()[filed({"label": REMOTE})]["answer"] == "No"


async def test_an_answer_about_one_company_is_kept_out_and_says_why(running, applicant, database):  # noqa: F811
    _, (job, initech) = await _student_queues(database, applicant, 2)
    await _company(database, job, "Hooli")
    await _company(database, initech, "Initech")

    res = await _change(applicant, {"set": [
        {"question": "Why do you want to work here?", "answer": "To build search."},
        {"question": "What do you want to work on?", "answer": "Search, as at Hooli."},
        # The form's company comes from WorkIt's own record of the application its job_id names.
        {"question": "Will you need them to sponsor a visa?", "answer": "No, not at Initech.", "job_id": initech},
        {"question": "If yes, please explain.", "answer": "I interned there."},
        {"question": "How did you hear about us?", "answer": "Hooli's careers page", "choice": True},
    ]})

    assert res.json()["kept_out"] == {
        "Why do you want to work here?": "It asks about one company or role, so it stays on this form.",
        "What do you want to work on?": "It names Hooli, so it stays on this form.",
        "Will you need them to sponsor a visa?": "It names Initech, so it stays on this form.",
        "If yes, please explain.": "It follows another question, so it stays on this form.",
    }
    # A choice is the form's own option: only its question is read.
    assert list((await _read(applicant)).json()) == ["how did you hear about us?"]


async def test_a_form_the_student_has_no_application_for_saves_nothing(running, applicant, database):  # noqa: F811
    from tests.test_connector import _another_students_application

    _, theirs = await _another_students_application(database)

    for job in (theirs, str(uuid.uuid4())):
        res = await _change(applicant, {"set": [{"question": SHIFTS, "answer": "Nights", "choice": True, "job_id": job},
                                                {"question": REMOTE, "answer": "Yes", "choice": True}]})
        assert res.status_code == 404, res.text
    assert (await _read(applicant)).json() == {}


async def test_a_models_text_enters_only_if_the_students_own_data_holds_it(running, applicant, database):  # noqa: F811
    """Plain code, no model: a number, name or outcome no fact of the
    student's states stays on its form, checked with no posting; the
    student's own words are theirs to give."""
    claim = "I wrote 40 tests for the billing service, and the team still runs them."
    res = await _change(applicant, {"set": [
        {"question": "How many tests did you write last summer?", "answer": claim, "review": True},
        {"question": "Which tools do you use most?", "answer": "Mostly Kubernetes and Terraform.", "review": True},
        {"question": "What do you build on weekends?", "answer": "Small robots that sort marbles.", "review": True},
        {"question": "How many hackathons have you joined?", "answer": claim},
        # A text longer than any one-off draft is not read at all, so no save holds the API for long.
        {"question": "Anything else we should know?", "answer": "I like robots. " * 70, "review": True},
        # One question twice: the model's draft never decides for the student's own answer.
        {"question": "How many teams have you led?", "answer": "Two."},
        {"question": "How many teams have you led?", "answer": "I led 9 teams of 30.", "review": True},
    ]})

    why = "It states something the student's own data doesn't hold, so it stays on this form."
    assert res.json()["kept_out"] == {"How many tests did you write last summer?": why, "Which tools do you use most?": why,
                                      "Anything else we should know?": why, "How many teams have you led?": why}
    bank = (await _read(applicant)).json()
    assert sorted(e["question"] for e in bank.values()) == [
        "How many hackathons have you joined?", "How many teams have you led?", "What do you build on weekends?"]
    assert bank["how many teams have you led?"]["answer"] == "Two."


async def test_a_save_holds_at_most_100_answers(running, applicant, database):  # noqa: F811
    too_many = await _change(applicant, {"set": [{"question": f"Question {n}?", "answer": "Yes"} for n in range(101)]})

    assert too_many.status_code == 422


async def test_only_the_student_writes_their_bank_and_only_with_a_profile(running, applicant, database):  # noqa: F811
    nobody = uuid.uuid4()
    not_mine = await _change(applicant, {"set": [{"question": REMOTE, "answer": "Yes"}]}, as_=nobody)
    no_profile = await _change(nobody, {"set": [{"question": REMOTE, "answer": "Yes"}]})
    _signed_in_as(nobody)
    async with _api() as reader:
        not_theirs = await reader.get(f"/applicants/{applicant}/answer-bank")
        empty = await reader.get(f"/applicants/{nobody}/answer-bank")

    assert (not_mine.status_code, no_profile.status_code, not_theirs.status_code) == (403, 404, 403)
    assert (empty.status_code, empty.json(), empty.headers["etag"]) == (200, {}, '"0"')


async def test_a_bank_past_its_caps_is_refused_whole_and_a_form_save_still_saves(
    running, applicant, database, monkeypatch,  # noqa: F811
):
    monkeypatch.setattr(answer_banks, "MAX_ENTRIES", 2)
    await _change(applicant, {"set": [{"question": f"Question {n}?", "answer": "Yes"} for n in range(2)]})

    too_many = await _change(applicant, {"set": [{"question": "Question 2?", "answer": "Yes"}]})
    me, (job,) = await _student_queues(database, applicant, 1)
    await _student_answers(me, job, HEARD, "A friend who interned there.")

    assert too_many.status_code == 413
    assert len((await _read(applicant)).json()) == 2
    assert (await _tab_asks(me, job))[0]["answer"] == "A friend who interned there."


async def test_a_question_in_words_the_tab_sent_stays_on_its_application(running, applicant, database):  # noqa: F811
    """The tab sends essays and short one-off questions alike, and the row
    can't tell them apart: only a choice, and a field the tab never sent
    (one a saved answer or a guess filled), enter the bank."""
    me, (first,) = await _student_queues(database, applicant, 1)
    essay = {**HEARD, "name": "question_6", "label": "Tell us about a time you failed."}
    short = {**HEARD, "name": "question_7", "label": "Which teams interest you most?"}
    await _tab_asks(me, first, essay, short, SHIFTS_ASKED)
    for question, answer in ((essay, "My own words."), (short, "Infrastructure."), (SHIFTS_ASKED, "Nights")):
        await _student_answers(me, first, question, answer)
    await _student_answers(me, first, HEARD, "A friend who interned there.")  # never sent

    assert sorted((await _read(applicant)).json()) == sorted([filed(SHIFTS_ASKED), filed(HEARD)])


async def test_the_first_read_fills_the_bank_from_what_workit_held(running, applicant, database):  # noqa: F811
    """A student who had answers before the bank existed: Apply's synced ones
    (fill_answers) and the one-off answers saved on applications."""
    from sqlalchemy import text

    me, (job,) = await _student_queues(database, applicant, 1)
    await _company(database, job, "Hooli")
    choice = {"name": "question_2", "label": SHIFTS, "required": True, "max_length": None, "kind": "choice",
              "options": ["Mornings", "Nights"]}
    await _tab_asks(me, job, choice)
    await _student_answers(me, job, choice, "Nights")
    _signed_in_as(applicant)
    async with _api() as apply:
        synced = await apply.patch(f"/applicants/{applicant}/fill-answers", json={"answers": [
            {"question": REMOTE, "answer": "Yes", "options": ["Yes", "No"], "source": "lisul"},
            {"question": "Why Hooli?", "answer": "Search.", "source": "lisul"},
            {"question": "What drew you to logistics?", "answer": "Watching trucks.", "source": "claude"},
        ]})
    assert synced.status_code == 200, synced.text
    # As a database from before the bank: its saves made no row.
    async with database() as session:
        await session.execute(text("DELETE FROM answer_banks"))
        await session.commit()

    bank = (await _read(applicant)).json()

    assert bank == {
        filed({"label": SHIFTS}): {"question": SHIFTS, "answer": "Nights", "own": True},
        filed({"label": REMOTE}): {"question": REMOTE, "answer": "Yes", "own": True},
        "what drew you to logistics?": {"question": "What drew you to logistics?", "answer": "Watching trucks.", "own": False},
    }
    assert (await _read(applicant)).headers["etag"] == '"1"'


async def test_the_first_fill_keeps_the_students_answer_beside_a_draft_of_the_same_question(
    running, applicant, database,  # noqa: F811
):
    """Their own answer on a form and an Apply draft word one question alike:
    the draft fails its check, and the student's answer still fills the bank."""
    from sqlalchemy import text

    me, (job,) = await _student_queues(database, applicant, 1)
    question = {"name": "question_4", "label": "How many hackathons have you joined?"}  # a field the tab never sent
    await _student_answers(me, job, question, "Three.")
    _signed_in_as(applicant)
    async with _api() as apply:
        synced = await apply.patch(f"/applicants/{applicant}/fill-answers", json={"answers": [
            {"question": question["label"], "answer": "I have joined 12 hackathons.", "source": "claude"}]})
    assert synced.status_code == 200, synced.text
    async with database() as session:
        await session.execute(text("DELETE FROM answer_banks"))
        await session.commit()

    assert (await _read(applicant)).json() == {filed(question): {"question": question["label"], "answer": "Three.", "own": True}}


RULE = Rule(companies=("Hooli", "Acme"), places=("Acme",), known=frozenset({"initech"}))


@pytest.mark.parametrize(("kept", "why"), [
    (Kept("Why do you want to join our team?", "To learn."), "It asks about one company or role, so it stays on this form."),
    (Kept("What do you want to build?", "Search at Hooli."), "It names Hooli, so it stays on this form."),
    (Kept("Have you worked at Acme before?", "Yes", choice=True, company="Acme"), "It names Acme, so it stays on this form."),
    (Kept("What did you learn last summer?", "At Acme I learned to test.", review=True), None),
    (Kept("What did you learn last summer?", "At Initech I learned to test.", review=True),
     "It names a company, so it stays on its form."),
    (Kept("What did you learn last summer?", "At Initech I learned to test."), None),
    (Kept("How did you hear about us?", "Hooli's careers page", choice=True), None),
    (Kept("What excites you about this role?", "Boats.", company="Globex"), "It asks about one company or role, so it stays on this form."),
    (Kept("Why Globex?", "Boats.", company="Globex"), "It names Globex, so it stays on this form."),
    (Kept("Tell us about a project you are proud of.", "At Globex's hackathon I built a boat.", company="Globex"),
     "It names Globex, so it stays on this form."),
    (Kept("Tell us about a project you are proud of.", "I built a boat.", company="Globex"), None),
    (Kept("What is your greatest strength?", "I finish things."), None),
    (Kept("If yes, please explain.", "I interned there."), "It follows another question, so it stays on this form."),
    (Kept('If you answered "No", which agency?', "Acme Staffing"), "It follows another question, so it stays on this form."),
    (Kept("Other (please specify)", "A friend"), "It follows another question, so it stays on this form."),
    (Kept("If applicable, list your GPA.", "3.8"), None),
])
def test_the_company_rule(kept, why):
    """A follow-up never enters; the form's own company always counts; the
    places the student worked or studied count only as another company; a
    model's text names no company WorkIt knows, while their own words may."""
    assert RULE.kept_out(kept) == why
