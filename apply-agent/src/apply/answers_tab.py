"""The Answers tab of the Apply window: everything Apply answers from, in
one place for Lisul to read, and his edits to what is his to edit.

It shows the Answer bank (his one-off answers, each Claude-drafted or his),
his answers to Missing facts and his Stock answers, all three editable, and
the rest of the Applicant profile to read. An essay of a Question type that
takes a Stock answer, written for a held Application, is offered as one:
only his click keeps it (apply.stock), and kept ones are editable too. A key that looks like it holds a
secret is never shown, and a file shows by its name alone.

The bank is written only through AnswerBank, whose locks keep a run's
Workers and the window from losing each other's answers. Each edit waits
for WorkIt's reply (W11): a refusal says why, and the window keeps the
student's text. The profile is written only
through ApplicantProfile. While a run goes, the tab edits the run's own
profile, so the run's next save keeps his edit; with no run, it reads the
profile file afresh for every view and edit."""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from ruamel.yaml.scalarstring import (
    FoldedScalarString,
    LiteralScalarString,
    SingleQuotedScalarString,
)

from apply import answering, stock
from apply.answer_bank import AnswerBank, Entry, NotSaved
from apply.model import Status
from apply.profile import ANSWERED, SECRET, ApplicantProfile

STOCK = "stock_answers"
# How long a question or an answer may be, and how many options a multi-select may tick.
MAX_QUESTION, MAX_ANSWER, MAX_CHOICES = 1_000, 20_000, 100


class Refused(ValueError):
    """An edit the tab won't make, with the HTTP status that says why: 400
    (not a valid answer), 404 (no such entry), 409 (one is there already)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class AnswersTab:
    def __init__(self, bank: AnswerBank, profile: ApplicantProfile | Path, today: Callable[[], date] = date.today,
                 held: Callable[[], list] | None = None):
        """`held` gives the Tracker's rows, read once (a Sheet read takes seconds)."""
        self._bank = bank
        self._profile = profile
        self._today = today
        self._held = held
        self._rows: list | None = None

    def view(self) -> dict:
        """What the tab shows, read again from the bank and the profile."""
        facts = self._profile_now().facts()
        return {
            "bank": [_shown(entry) for entry in self._bank.entries()],
            # While the bank hasn't come from WorkIt yet (W11), why: it is tried again by itself.
            "bank_note": "" if self._bank.ready else self._bank.problem or "Reading your answers from WorkIt.",
            "answered": [{"question": q, "answer": _text(a)} for q, a in (facts.get(ANSWERED) or {}).items()
                         if not SECRET.search(str(q))],
            "stock": [{"key": k, "answer": _text(a)} for k, a in (facts.get(STOCK) or {}).items()
                      if not SECRET.search(str(k))],
            "stock_types": [{"type": s.type, "answer": s.text, "company": s.from_company, "question": s.from_question,
                             "approved": s.approved.isoformat() if s.approved else ""} for s in stock.approved()],
            "stock_offers": self._offers(),
            "profile": [{"section": section, "facts": _flat(value, files=section == "files")}
                        for section, value in facts.items()
                        if section not in (ANSWERED, STOCK) and not SECRET.search(str(section))],
        }

    def save(self, question: str, answer: str | list[str]) -> None:
        """Lisul's answer to a question in the bank: his from now on, reviewed."""
        self._bank_ready()
        question, answer = _question(question), _answer(answer)
        if not self._has(question):
            raise Refused("That question is no longer in the Answer bank.", 404)
        _saved(self._bank.answer, question, answer)

    def add(self, question: str, answer: str | list[str]) -> None:
        """A question Lisul adds to the bank himself, with his answer."""
        self._bank_ready()
        question, answer = _question(question), _answer(answer)
        if self._has(question):
            raise Refused("That question is already in the Answer bank: edit it there.", 409)
        _saved(self._bank.answer, question, answer)

    def review(self, question: str) -> None:
        self._bank_ready()
        if not _saved(self._bank.review, _question(question)):
            raise Refused("That question is no longer in the Answer bank.", 404)

    def delete(self, question: str) -> None:
        """Take a question out of the bank: it is drafted again the next time a form asks."""
        self._bank_ready()
        if not _saved(self._bank.delete, _question(question)):
            raise Refused("That question is no longer in the Answer bank.", 404)

    def save_answered(self, question: str, answer: str) -> None:
        """Lisul's answer to a Missing fact, saved into the Applicant profile."""
        question, answer = _question(question), _answer(answer, choices=False)
        try:
            self._profile_now().save_answered(question, _scalar(answer))
        except ValueError as refused:  # a question that looks like it asks for a secret
            raise Refused(str(refused)) from refused

    def save_skipped(self, question: str) -> None:
        """Lisul's Skip of an optional question: an empty answer in the Applicant profile, so the engine's plan leaves
        it blank on every later form and never asks it again (KAN-759). An answer he writes later replaces it."""
        try:
            self._profile_now().save_answered(_question(question), "")
        except ValueError as refused:
            raise Refused(str(refused)) from refused

    def save_stock(self, key: str, answer: str) -> None:
        """One of Lisul's Stock answers, saved into the Applicant profile in the style it had."""
        profile, answer = self._profile_now(), _answer(answer, choices=False)
        was = (profile.get(STOCK) or {}).get(key) if isinstance(key, str) else None
        if was is None:
            raise Refused("There is no such Stock answer.", 404)
        style = next((s for s in (FoldedScalarString, LiteralScalarString) if isinstance(was, s)), None)
        try:
            profile.save_fact(f"{STOCK}.{key}", style(answer) if style else _scalar(answer))
        except ValueError as refused:
            raise Refused(str(refused)) from refused

    def keep_stock(self, type: str, company: str, question: str, answer: str) -> None:
        """Lisul's click on "Save as stock answer?": the offered essay, as he
        left it, becomes the Stock answer of its type."""
        answer = _answer(answer, choices=False)
        if not any(o["type"] == type and o["company"] == company and o["question"] == question for o in self._offers()):
            raise Refused("That essay is no longer offered as a Stock answer.", 404)
        stock.propose(type, answer, company, question)
        stock.approve(type, self._today())

    def save_stock_type(self, type: str, answer: str) -> None:
        """His own wording of a kept Stock answer."""
        answer = _answer(answer, choices=False)
        if not isinstance(type, str) or stock.get(type) is None:
            raise Refused("There is no such Stock answer.", 404)
        stock.edit(type, answer)

    def _offers(self) -> list[dict]:
        """Each held Application's essays whose Question type takes a Stock
        answer and has none kept yet."""
        from apply import (
            essays,  # imported here: essays imports the adapters, which import this tab
        )
        if self._rows is None:
            try:
                self._rows = list(self._held()) if self._held else []
            except Exception:  # the Sheet unreachable: no offers, the rest of the tab still shows
                self._rows = []
        guides, kept, offers = answering.load(), {s.type for s in stock.approved()}, []
        for row in self._rows:
            if row.status != Status.HELD or not row.essay:
                continue
            for essay in essays.from_cell(row.essay, essays.headings(row.essay)):
                type = answering.classify(essay.question.label)
                if essay.text and type in guides and guides[type].stock and type not in kept:
                    offers.append({"type": type, "company": row.company, "question": essay.question.label,
                                   "answer": essay.text})
        return offers

    def _bank_ready(self) -> None:
        """An edit waits for the bank to come from WorkIt (W11): one made before would be lost when it lands."""
        if not self._bank.ready:
            raise Refused(self._bank.problem or "Your answers are still coming from WorkIt: try again in a moment.", 503)

    def _has(self, question: str) -> bool:
        return self._bank.get(question) is not None

    def _profile_now(self) -> ApplicantProfile:
        return self._profile if isinstance(self._profile, ApplicantProfile) else ApplicantProfile.load(self._profile)


def _question(question: object) -> str:
    if not isinstance(question, str) or not question.strip():
        raise Refused("Give the question.")
    if len(question) > MAX_QUESTION:
        raise Refused(f"A question may be at most {MAX_QUESTION:,} characters.")
    return question.strip()


def _answer(answer: object, choices: bool = True) -> str | list[str]:
    """An answer as Lisul gave it: text, or (for a choice) the options he picked."""
    if choices and isinstance(answer, list) and all(isinstance(a, str) for a in answer):
        picked = [a.strip() for a in answer if a.strip()]
        if not picked:
            raise Refused("Pick at least one option, or write an answer.")
        if len(picked) > MAX_CHOICES:
            raise Refused(f"An answer may pick at most {MAX_CHOICES} options.")
        if any(len(a) > MAX_ANSWER for a in picked):
            raise Refused(f"An answer may be at most {MAX_ANSWER:,} characters.")
        return picked
    if not isinstance(answer, str) or not answer.strip():
        raise Refused("Write an answer.")
    if len(answer) > MAX_ANSWER:
        raise Refused(f"An answer may be at most {MAX_ANSWER:,} characters.")
    return answer.strip()


def _scalar(text: str) -> str:
    """Quoted when a YAML reader would take it for true or false ("Yes", "No")."""
    bool_like = text.casefold() in ("yes", "no", "y", "n", "on", "off", "true", "false")
    return SingleQuotedScalarString(text) if bool_like else text


def _shown(entry: Entry) -> dict:
    """An entry as the Answers tab draws it: a choice's answer is edited as text, and the Fill engine maps it to
    each form's options (W11), so no options come with it."""
    return {"question": entry.question, "answer": entry.answer, "options": [],
            "source": "lisul" if entry.own else "claude", "reviewed": entry.own}


def _flat(value: Any, prefix: str = "", files: bool = False) -> list[list[str]]:
    """A section's facts as [dotted key, readable value] pairs, secrets left out."""
    if not isinstance(value, dict):
        return [[prefix, _text(value, files)]]
    pairs = []
    for k, v in value.items():
        if SECRET.search(str(k)):
            continue
        name = f"{prefix}.{k}" if prefix else str(k)
        pairs += _flat(v, name, files) if isinstance(v, dict) and v else [[name, _text(v, files)]]
    return pairs


def _text(value: Any, files: bool = False) -> str:
    """A fact as Lisul reads it: a list on one line, a list of records a line each."""
    if value is None or value == {} or value == []:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        rows = [_text(v, files) for v in value]
        return ("\n" if any(isinstance(v, dict) for v in value) else
                "; " if any(isinstance(v, list) for v in value) else ", ").join(rows)
    if isinstance(value, dict):
        return " · ".join(f"{k}: {_text(v, files)}" for k, v in value.items() if not SECRET.search(str(k)) and v not in (None, ""))
    return Path(str(value)).name if files else str(value)


def _saved(change: Callable[..., Any], *args: Any) -> Any:
    """One change to the bank; WorkIt's refusal, or its silence, as the tab's Refused."""
    try:
        return change(*args)
    except NotSaved as unsaved:
        raise Refused(str(unsaved), unsaved.status) from unsaved


def saving_answers(tracker: Callable[[], object], tab: AnswersTab) -> Callable[[dict, str, str], str]:
    """Save Lisul's answer typed in the Apply window (Needs you, or the
    student page's question card) where Apply reads it: a run's
    Missing fact in its Tracker row's Answer cell, as if he typed it in the
    Sheet, so the next check fills that Application again with it; a
    rehearsal's into his Applicant profile, for every form after, or, for
    what an essay asked him, in memory for that form's essays alone
    (essays.TOLD), never saved. A
    bare date (From, To) is that form's alone: never saved by its label.
    The same for his answer typed on the held form itself (Board.typed).
    An empty answer is his Skip of an optional question (KAN-759): kept as
    an empty answer in his profile, so no later form asks it again. The
    window's `answer` in a Developer checkout's runs and a Student run's
    (apply.student.Runs) alike."""
    from apply import (  # imported here: essays imports the adapters, which import this module
        essays,
        on_page,
    )
    def answer(item: dict, question: str, text: str) -> str:
        if not text.strip():
            if question.startswith(essays.ASK) or on_page.bare(question):
                return "Skipped: it's optional, so this form leaves it blank."
            tab.save_skipped(question)
            return "Skipped: the form leaves it blank, and Apply won't ask it again."
        if item.get("status") == "missing fact" and item.get("application_id"):
            tracker().answer(item["application_id"], text)
            return f"Saved your answer for {item.get('company') or 'it'}: it goes on at the next check."
        if question.startswith(essays.ASK):
            essays.tell(item.get("posting_url") or "", question, text)
            return "Kept for this application only: the essay is written with it next time."
        if on_page.bare(question):  # a bare From or To: true of one section of this form only (KAN-595)
            return "Kept on this form only: a bare date isn't saved to your facts without what it is for."
        tab.save_answered(question, text)
        return "Saved to your facts: every form that asks it gets this answer."
    return answer
