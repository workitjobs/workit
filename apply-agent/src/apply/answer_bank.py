"""The Answer bank: one answer per one-off question (a required question no
Applicant profile fact or rule answers), by the question's wording, so the
same question gets the same answer on every form and costs no tokens again.

It lives on WorkIt (W11 of docs/desktop_application_auto_apply.md; ADR
0006), never in the data folder: the WorkIt extension fills from the same
bank. Each process reads it once into memory (`load`), and the window and
every Worker share that one object (they are threads: one lock). WorkIt's
rule decides what may enter the bank, never this module.

A bank with no WorkIt (`AnswerBank()`) is memory only: Test Person's, which
keeps no drafts (`drafts=False`), so a sample run never writes a made-up
person's answers anywhere; and the tests'."""

import threading
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from apply import masked
from apply.model import Question, one_line

FILE = "answer-bank.yaml"  # where the bank lived before W11, beside the Applicant profile: read once to move it
# A bank that failed to read tries again after each of these waits, then every RETRY_AFTER seconds.
RETRIES = (10.0,) * 6
RETRY_AFTER = 60.0


def key(question: str) -> str:
    """A question's wording as the bank files it: case, spacing, curly quotes
    and a required field's asterisk don't count."""
    text = question.casefold().replace("’", "'").replace("“", '"').replace("”", '"')
    return one_line(text).strip(" *")


@dataclass(frozen=True)
class Entry:
    question: str  # as a form showed it
    answer: str | list[str]  # a multi-select's answer is the options ticked
    own: bool = False  # the student's own answer, or a draft they reviewed; a model's draft until then
    none: bool = False  # a multi-select none of whose options holds (answer []): its boxes stay unticked


class Source(Protocol):
    """Where the bank is kept: WorkIt's `GET .../answer-bank`."""

    def read(self) -> tuple[dict[str, dict], int]:
        """Every entry by its key, and the bank's version."""
        ...


class WorkItSource:
    """The bank on WorkIt, as the signed-in student."""

    def __init__(self, client=None):
        self._client = client

    def read(self) -> tuple[dict[str, dict], int]:
        if self._client is None:
            from apply import (
                workit,  # imported here: the WorkIt client imports more than a bank in memory needs
            )
            self._client = workit.WorkIt()
        return self._client.answer_bank()


class AnswerBank:
    """The student's bank, in memory: read from `source`, or empty with none."""

    def __init__(self, source: Source | None = None, drafts: bool = True):
        self._source = source
        self._drafts = drafts
        self._entries: dict[str, Entry] = {}
        self._version = 0
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._wake = threading.Event()  # set to try a waiting read again at once (wake)
        self.problem = ""  # why the last read failed, while the bank waits to read
        if source is None:
            self._ready.set()

    @property
    def ready(self) -> bool:
        """Whether the bank has been read: a run waits for it."""
        return self._ready.is_set()

    def load(self) -> None:
        """Read the whole bank into memory. Raises what the read raises (WorkIt down, no login)."""
        if self._source is None:
            return
        answers, version = self._source.read()
        # Filed by this module's own fold of each question, whatever key WorkIt's own fold gave it.
        read = [(str(k), _entry(v)) for k, v in answers.items() if isinstance(v, dict) and "answer" in v]
        entries = {key(e.question) if e.question else k: e for k, e in read}
        with self._lock:
            self._entries, self._version = entries, version
        _mask(entries.values())
        self.problem = ""
        self._ready.set()

    def load_in_background(self) -> threading.Thread:
        """Read the bank in a thread of its own, again after each wait (RETRIES, then every RETRY_AFTER, or at once
        on `wake`) until it reads; meanwhile `problem` says why it hasn't."""
        def keep_trying() -> None:
            waits = iter(RETRIES)
            while True:
                try:
                    self.load()
                    return
                except Exception as error:  # WorkIt down or no login: the window says so, and Start waits
                    self.problem = f"Can't reach WorkIt, trying again ({type(error).__name__})."
                self._wake.wait(next(waits, RETRY_AFTER))
                self._wake.clear()

        thread = threading.Thread(target=keep_trying, daemon=True, name="answer-bank")
        thread.start()
        return thread

    def wake(self, wait: float = 0.0) -> bool:
        """Try a waiting read again now (the student just signed in, or pressed Start), and wait up to `wait`
        seconds for it. Whether the bank is read."""
        self._wake.set()
        return self._ready.wait(wait)

    def get(self, question: str) -> Entry | None:
        with self._lock:
            found = self._entries.get(key(question))
        return found if found is not None and _answered(found) else None

    def answers(self) -> dict[str, Entry]:
        """Every answer, by its key."""
        with self._lock:
            return {k: e for k, e in self._entries.items() if _answered(e)}

    def entries(self) -> list[Entry]:
        return list(self.answers().values())

    def own_lines(self) -> list[str]:
        """The student's own answers as "question: answer" lines: theirs for the truth check (a model's draft is no
        fact of theirs, even once it is in the bank)."""
        return [f"{e.question}: {_text(e.answer)}" for e in self.entries() if e.own]

    def add(self, question: Question, answer: str | list[str], company: str = "", *, wording: str | None = None,
            job_id: str | None = None) -> bool:
        """The model's draft answer to `question` on a form at `company` (the WorkIt job `job_id` when it is one),
        filed under `wording` (a bare date's section and label, fill_engine.Plan.filed), else under the question's
        label. False if the bank already has an answer to it, which stays, or keeps no drafts (Test Person's)."""
        if not self._drafts:
            return False
        filed = wording or question.label
        with self._lock:
            if key(filed) in self._entries:
                return False
            self._entries[key(filed)] = entry = _new(filed, answer, own=False)
        _mask([entry])
        return True

    def redraft(self, question: Question, answer: str | list[str]) -> bool:
        """The model's new draft to `question`, written again with context the student added (apply.regenerate), in
        place of its old draft: still the model's. The student's own answer stays. False when the bank keeps theirs,
        or keeps no drafts."""
        if not self._drafts:
            return False
        with self._lock:
            found = self._entries.get(key(question.label))
            if found is not None and found.own:
                return False
            self._entries[key(question.label)] = _new(question.label, answer, own=False)
        return True

    def answer(self, question: str, answer: str | list[str]) -> None:
        """The student's own answer to `question`, from the Apply window: it replaces any draft."""
        with self._lock:
            self._entries[key(question)] = entry = _new(question, answer, own=True)
        _mask([entry])

    def review(self, question: str) -> bool:
        """Mark `question`'s answer reviewed, unchanged: the student's from now on. False if the bank lacks it."""
        with self._lock:
            found = self._entries.get(key(question))
            if found is None:
                return False
            self._entries[key(question)] = Entry(found.question, found.answer, own=True, none=found.none)
            return True

    def delete(self, question: str) -> bool:
        """Take `question` out of the bank, so the next form that asks it gets a new draft. False if the bank
        lacks it."""
        with self._lock:
            return self._entries.pop(key(question), None) is not None


def _new(question: str, answer: str | list[str], own: bool) -> Entry:
    picked = [str(a).strip() for a in answer] if isinstance(answer, list) else str(answer).strip()
    return Entry(one_line(question), picked, own=own, none=picked == [])


def _entry(found: dict) -> Entry:
    """One entry as WorkIt serves it."""
    answer = found["answer"]
    return Entry(question=str(found.get("question") or ""),
                 answer=[str(a) for a in answer] if isinstance(answer, list) else str(answer),
                 own=found.get("own") is not False, none=found.get("none") is True and answer == [])


def _answered(entry: Entry) -> bool:
    """An empty answer is none, unless it says "none of these" for a multi-select."""
    return entry.none or entry.answer not in ("", [])


def _text(answer: str | list[str]) -> str:
    return "; ".join(answer) if isinstance(answer, list) else answer


def _mask(entries: Iterable[Entry]) -> None:
    """Apply's own prints never show the bank's answers (apply.masked)."""
    for entry in entries:
        for value in entry.answer if isinstance(entry.answer, list) else [entry.answer]:
            masked.KNOWN.add(value, "answer", masked.SHORTEST_ANSWER)
