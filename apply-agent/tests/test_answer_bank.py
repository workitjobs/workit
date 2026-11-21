"""The Answer bank: one answer per one-off question, kept on WorkIt and read once into memory (W11)."""

import threading

import pytest

from apply import masked
from apply.answer_bank import AnswerBank
from apply.model import Question
from apply.workit import Unreachable

HEARD = Question("q1", "Tell us how you heard about Zipline", "text", required=True)
SAMPLES = Question("q2", "Will you be including a link on your resume to samples of projects you've worked on?",
                   "select", required=True, options=("Yes", "No"))
SKILLS = Question("q3", "Skill Areas (Select all that apply)", "multi_select", True, ("Finance", "Software", "Robotics"))


class Source:
    """WorkIt's bank as `GET .../answer-bank` serves it, or a read that fails until `fails` reads have."""

    def __init__(self, answers: dict | None = None, version: int = 7, fails: int = 0):
        self.answers, self.version, self.fails, self.reads = answers or {}, version, fails, 0

    def read(self) -> tuple[dict, int]:
        self.reads += 1
        if self.reads <= self.fails:
            raise Unreachable("WorkIt didn't answer")
        return self.answers, self.version


def test_a_draft_is_found_again_under_its_question_in_any_case_or_spacing():
    bank = AnswerBank()
    assert bank.add(HEARD, "From the Simplify list.", "Zipline")

    assert bank.get("  tell us how you heard about zipline * ").answer == "From the Simplify list."
    assert bank.get(HEARD.label).own is False  # the model's, until the student reviews it


def test_an_answer_in_the_bank_is_never_replaced_by_a_new_draft():
    bank = AnswerBank()
    bank.answer(SAMPLES.label, "No")
    bank.add(HEARD, "From the Simplify list.", "Zipline")

    assert not bank.add(SAMPLES, "Yes", "Roblox")
    assert not bank.add(HEARD, "From LinkedIn.", "Roblox")
    assert (bank.get(SAMPLES.label).answer, bank.get(HEARD.label).answer) == ("No", "From the Simplify list.")


def test_workers_drafting_at_once_lose_no_answer():
    bank = AnswerBank()
    questions = [Question(f"q{n}", f"Question {n}?", "text", True) for n in range(40)]
    threads = [threading.Thread(target=bank.add, args=(q, f"Draft {q.name}", "Acme")) for q in questions]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(e.answer for e in bank.entries()) == sorted(f"Draft {q.name}" for q in questions)


def test_the_students_answer_replaces_a_draft_and_review_makes_a_draft_theirs():
    bank = AnswerBank()
    bank.add(HEARD, "From the Simplify list.", "Zipline")
    bank.add(SAMPLES, "Yes", "Zipline")

    bank.answer(HEARD.label, "A friend on the avionics team.")
    assert bank.review(SAMPLES.label)
    bank.answer("Do you have a driver's license?", "Yes")  # one they add themselves

    assert [(e.answer, e.own) for e in bank.entries()] == [
        ("A friend on the avionics team.", True), ("Yes", True), ("Yes", True)]
    assert bank.own_lines()[0] == "Tell us how you heard about Zipline: A friend on the avionics team."
    assert not bank.review("Never asked?")


def test_a_redraft_replaces_the_models_draft_but_never_the_students_answer():
    bank = AnswerBank()
    bank.add(HEARD, "From the Simplify list.", "Zipline")
    bank.answer(SAMPLES.label, "No")

    assert bank.redraft(HEARD, "From a friend.")
    assert not bank.redraft(SAMPLES, "Yes")
    assert (bank.get(HEARD.label).answer, bank.get(SAMPLES.label).answer) == ("From a friend.", "No")


def test_a_deleted_answer_leaves_the_bank_so_the_model_drafts_it_again():
    bank = AnswerBank()
    bank.add(HEARD, "From the Simplify list.", "Zipline")

    assert bank.delete(HEARD.label.upper())
    assert bank.get(HEARD.label) is None and not bank.delete(HEARD.label)
    assert bank.add(HEARD, "From LinkedIn.", "Roblox")


def test_none_of_a_multi_selects_options_is_an_answer():
    bank = AnswerBank()
    bank.answer(SKILLS.label, [])

    entry = bank.get(SKILLS.label)
    assert (entry.answer, entry.none) == ([], True)


def test_a_bare_date_is_filed_under_its_section_never_its_label_alone():
    # Arrowstreet (live, 2026-11-04): "from (mm/dd/yyyy)" held the internship's start, for every From on every form.
    bank = AnswerBank()
    start = Question("q", "From (MM/DD/YYYY)", "text", True)

    assert bank.add(start, "06/01/2026", "Acme", wording="work experience / From (MM/DD/YYYY)")

    assert bank.get("From (MM/DD/YYYY)") is None
    assert bank.get("work experience / From (MM/DD/YYYY)").answer == "06/01/2026"


def test_test_persons_bank_keeps_no_drafts():
    bank = AnswerBank(drafts=False)

    assert not bank.add(HEARD, "From the Simplify list.", "Zipline")
    assert not bank.redraft(HEARD, "From a friend.")
    assert bank.entries() == []


def test_the_bank_reads_workits_entries_and_masks_their_answers():
    bank = AnswerBank(Source({
        "tell us how you heard about zipline": {"question": HEARD.label, "answer": "A friend at Zipline HQ.", "own": True},
        "skill areas (select all that apply)": {"question": SKILLS.label, "answer": [], "own": False, "none": True},
    }))
    assert not bank.ready

    bank.load()

    assert bank.ready
    assert [(e.question, e.own, e.none) for e in bank.entries()] == [(HEARD.label, True, False), (SKILLS.label, False, True)]
    assert "A friend at Zipline HQ." not in masked.KNOWN.scrub("They heard: A friend at Zipline HQ.")


def test_a_bank_that_cant_read_tries_again_in_the_background_and_at_once_on_wake(monkeypatch):
    monkeypatch.setattr("apply.answer_bank.RETRIES", (30.0,))
    source = Source({"q": {"question": "Q?", "answer": "Yes", "own": True}}, fails=2)
    bank = AnswerBank(source)
    with pytest.raises(Unreachable):
        bank.load()

    bank.load_in_background()

    assert bank.wake(5.0)  # the first try in the thread fails; the wake skips its 30 s wait
    assert bank.get("Q?").answer == "Yes" and bank.problem == ""
    assert source.reads == 3
