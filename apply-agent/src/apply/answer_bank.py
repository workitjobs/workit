"""The Answer bank: one answer per one-off question (a required question no
Applicant profile fact or rule answers), by the question's wording, so the
same question gets the same answer on every form and costs no tokens again.

It lives on WorkIt (W11 of docs/desktop_application_auto_apply.md; ADR
0006), never in the data folder: the WorkIt extension fills from the same
bank. Each process reads it once into memory (`load`), and the window and
every Worker share that one object (they are threads: one lock). WorkIt's
rule decides what may enter the bank, never this module.

Every change goes to WorkIt through one sender thread, one PATCH for each
change, in order, and memory changes only from WorkIt's reply: no form
fills an answer WorkIt's rule kept out. The model's drafts never wait (the
form that drafted one holds it); the student's own changes go ahead of
them and wait for the reply (EDIT_WAIT), so the Answers view says whether
WorkIt saved each. A reply whose version is not the bank's own plus one
says another writer saved meanwhile: the bank is read again.

A bank with no WorkIt (`AnswerBank()`) is memory only: Test Person's, which
keeps no drafts (`drafts=False`), so a sample run never writes a made-up
person's answers anywhere; and the tests'."""

import sys
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from apply import masked
from apply.model import Question, one_line

# A bank that failed to read tries again after each of these waits, then every RETRY_AFTER seconds.
RETRIES = (10.0,) * 6
RETRY_AFTER = 60.0
# A change WorkIt didn't answer (no reply, a 5xx) is sent again after each of these waits, then dropped; a draft
# dropped is drafted again the next time a form asks. A refusal (a 4xx) is dropped at once.
SEND_RETRIES = (1.0, 5.0, 30.0)
# How long the student's change waits for WorkIt's reply, and how long the sender has at quit.
EDIT_WAIT = 10.0
QUIT_WAIT = 5.0
NO_ANSWER = "Not saved: WorkIt didn't answer."


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


class NotSaved(Exception):
    """WorkIt didn't save the student's change: its rule kept it out (`status` 400, with the rule's reason), it
    refused it, or it didn't answer (503)."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class Source(Protocol):
    """Where the bank is kept: WorkIt's `GET` and `PATCH .../answer-bank`."""

    def read(self) -> tuple[dict[str, dict], int]:
        """Every entry by its key, and the bank's version."""
        ...

    def change(self, entries: list[dict], deleted: list[str]) -> tuple[int, dict[str, str]]:
        """Save `entries` and delete the questions `deleted`: the bank's new version, and why WorkIt's rule kept
        each entry it kept out, by question."""
        ...


class WorkItSource:
    """The bank on WorkIt, as the signed-in student."""

    def __init__(self, client=None):
        self._client = client

    def read(self) -> tuple[dict[str, dict], int]:
        return self._workit().answer_bank()

    def change(self, entries: list[dict], deleted: list[str]) -> tuple[int, dict[str, str]]:
        return self._workit().change_answer_bank(entries, deleted)

    def _workit(self):
        if self._client is None:
            from apply import (
                workit,  # imported here: the WorkIt client imports more than a bank in memory needs
            )
            self._client = workit.WorkIt()
        return self._client


@dataclass(eq=False)
class _Change:
    """One change for the sender: `entry` to save as PATCH takes it, or `question` to delete when it is None."""

    filed: str  # the question's key
    question: str
    entry: dict | None
    student: bool = False  # the student's own: ahead of the drafts, and waited for
    tries: int = 0
    due: float = 0.0  # when it may go (time.monotonic): later while it waits to be sent again
    given_up: bool = False  # the student's view stopped waiting: never sent again
    said: str = ""  # once done: "" saved, else why not ("Not saved: ...")
    done: threading.Event = field(default_factory=threading.Event)

    def body(self) -> tuple[list[dict], list[str]]:
        return ([self.entry], []) if self.entry is not None else ([], [self.question])


class AnswerBank:
    """The student's bank, in memory: read from `source`, or empty with none."""

    def __init__(self, source: Source | None = None, drafts: bool = True):
        self._source = source
        self._drafts = drafts
        self._entries: dict[str, Entry] = {}
        self._version = 0
        # One lock for the memory and the changes waiting to go, so a check and its change are one step; the
        # sender waits on it for the next change.
        self._lock = threading.Condition()
        self._waiting: list[_Change] = []
        self._sending: _Change | None = None
        self._sender: threading.Thread | None = None
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
        """The model's draft answer to `question` on a form at `company` (the WorkIt job `job_id` when it is one:
        WorkIt's rule reads that job's company itself), filed under `wording` (a bare date's section and label,
        fill_engine.Plan.filed), else under the question's label; sent to WorkIt, flagged for the student's review.
        False if the bank has an answer to it already, which stays, or one on its way, or keeps no drafts (Test
        Person's), or the draft is blank."""
        picked = _picked(answer)
        if not self._drafts or picked == "":
            return False
        form = {"job_id": job_id} if job_id else {"company": company.strip()} if company.strip() else {}
        change = _set(wording or question.label, picked, own=False, choice=bool(question.options), form=form)
        with self._lock:
            if change.filed in self._entries or any(c.filed == change.filed for c in self._unsent()):
                return False
            self._go(change)
        return True

    def redraft(self, question: Question, answer: str | list[str]) -> bool:
        """The model's new draft to `question`, written again with context the student added (apply.regenerate), in
        place of its old draft: still the model's, flagged. The student's own answer stays. False when the bank keeps
        theirs, or keeps no drafts."""
        picked = _picked(answer)
        if not self._drafts or picked == "":
            return False
        change = _set(question.label, picked, own=False, choice=bool(question.options))
        with self._lock:
            found = self._entries.get(change.filed)
            if found is not None and found.own:
                return False
            self._go(change)
        return True

    def answer(self, question: str, answer: str | list[str]) -> None:
        """The student's own answer to `question` (the Apply window, Ask Claude's offer): it replaces any draft.
        Raises NotSaved when WorkIt doesn't save it."""
        self._wait(_set(question, _picked(answer), own=True, student=True))

    def review(self, question: str) -> bool:
        """Mark `question`'s answer reviewed, unchanged: the student's from now on. False if the bank lacks it;
        raises NotSaved when WorkIt doesn't save it."""
        with self._lock:
            found = self._entries.get(key(question))
        if found is None:
            return False
        self._wait(_set(found.question, found.answer, own=True, student=True))
        return True

    def delete(self, question: str) -> bool:
        """The student takes `question` out of the bank, so the next form that asks it gets a new draft. False if
        the bank lacks it; raises NotSaved when WorkIt doesn't delete it."""
        with self._lock:
            if key(question) not in self._entries:
                return False
        self._wait(_Change(key(question), one_line(question), None, student=True))
        return True

    def drop_draft(self, question: str) -> None:
        """The pre-submit review found the model's draft to `question` wrong: out of the bank, so it never fills
        another form. The student's own answer stays."""
        with self._lock:
            found = self._entries.get(key(question))
            if found is not None and not found.own:
                self._go(_Change(key(question), found.question, None))

    def close(self, wait: float = QUIT_WAIT) -> None:
        """At quit: the changes still waiting get up to `wait` seconds to reach WorkIt."""
        ending = time.monotonic() + wait
        with self._lock:
            while (self._waiting or self._sending) and (left := ending - time.monotonic()) > 0:
                self._lock.wait(left)

    # The sender.

    def _wait(self, change: _Change) -> None:
        with self._lock:
            self._go(change)
        if not change.done.wait(EDIT_WAIT):
            change.given_up = True
            raise NotSaved(NO_ANSWER, 503)
        if change.said:
            raise NotSaved(change.said, 503 if change.said == NO_ANSWER else 400)

    def _go(self, change: _Change) -> None:
        """Under the lock. With no WorkIt the change is the bank's at once; else it waits for the sender: the
        student's after the student's other changes, ahead of every draft, and in place of a waiting draft to the
        same question."""
        if self._source is None:
            self._saved(change, None, {})
            return
        if change.student:
            self._waiting = [c for c in self._waiting if c.student or c.filed != change.filed]
            self._waiting.insert(sum(c.student for c in self._waiting), change)
        else:
            self._waiting.append(change)
        if self._sender is None:
            self._sender = threading.Thread(target=self._send_all, daemon=True, name="answer-bank-sender")
            self._sender.start()
        self._lock.notify_all()

    def _unsent(self) -> list[_Change]:
        return [*self._waiting, *([self._sending] if self._sending else [])]

    def _send_all(self) -> None:
        # Imported here, as WorkItSource imports the client.
        from apply.workit import Unreachable

        while True:
            with self._lock:
                self._sending = change = self._next()
            try:
                version, kept_out = self._source.change(*change.body())
            except Exception as error:  # no answer is sent again; a refusal, a lost login or a bug is dropped
                with self._lock:
                    self._sending = None
                    if isinstance(error, Unreachable) and change.tries < len(SEND_RETRIES) and not change.given_up:
                        change.due, change.tries = time.monotonic() + SEND_RETRIES[change.tries], change.tries + 1
                        self._again(change)
                    else:
                        self._dropped(change, error, isinstance(error, Unreachable))
                    self._lock.notify_all()
                continue
            with self._lock:
                self._sending = None
                stale = self._saved(change, version, kept_out)
                self._lock.notify_all()
            if stale:
                try:
                    self.load()
                except Exception:  # the old version stays, so the next version check reads the bank (W11 rule 6)
                    pass

    def _next(self) -> _Change:
        """Under the lock: the first change that may go now, none ahead of it to the same question. Waits for one."""
        while True:
            for gone in [c for c in self._waiting if c.given_up]:
                self._waiting.remove(gone)
                gone.done.set()
            now = time.monotonic()
            for n, change in enumerate(self._waiting):
                if change.due <= now and all(c.filed != change.filed for c in self._waiting[:n]):
                    return self._waiting.pop(n)
            self._lock.notify_all()  # close() waits for this: nothing to send now
            due = min((c.due for c in self._waiting), default=None)
            self._lock.wait(None if due is None else due - now)

    def _again(self, change: _Change) -> None:
        """Under the lock: `change` back at the head of its kind, to be sent again; a draft the student changed
        meanwhile goes, since theirs takes its place."""
        if not change.student and any(c.student and c.filed == change.filed for c in self._waiting):
            change.done.set()
            return
        self._waiting.insert(0 if change.student else sum(c.student for c in self._waiting), change)

    def _dropped(self, change: _Change, error: Exception, unanswered: bool) -> None:
        """Under the lock: a change WorkIt didn't save, said in the log by its question alone, masked."""
        why = type(error).__name__ + (f" {error.status}" if getattr(error, "status", None) else "")
        print(f"Answer bank: not saved to WorkIt ({why}): {masked.KNOWN.scrub(change.question)}", file=sys.stderr)
        change.said = NO_ANSWER if unanswered else f"Not saved: WorkIt refused it ({why})."
        change.done.set()

    def _saved(self, change: _Change, version: int | None, kept_out: dict[str, str]) -> bool:
        """Under the lock: WorkIt's reply to `change` into memory (no change when its rule kept the entry out).
        Whether another writer saved meanwhile, so the bank is read again."""
        if kept_out:  # one entry to a PATCH: its reason
            change.said = f"{KEPT_OUT}{next(iter(kept_out.values()))}"
        elif change.entry is None:
            self._entries.pop(change.filed, None)
        else:
            self._entries[change.filed] = entry = _new(change.question, change.entry["answer"],
                                                        own=not change.entry["review"])
            _mask([entry])
        stale = version is not None and version != self._version + 1
        if version is not None and not stale:
            self._version = version
        change.done.set()
        return stale


KEPT_OUT = "Not saved: WorkIt keeps it out of your Answer bank. "


def _picked(answer: str | list[str]) -> str | list[str]:
    """An answer as the bank keeps it: stripped, a list of the options ticked with no empty one."""
    return [p for a in answer if (p := str(a).strip())] if isinstance(answer, list) else str(answer).strip()


def _set(question: str, answer: str | list[str], own: bool, *, choice: bool = False, form: dict | None = None,
         student: bool = False) -> _Change:
    """A change that saves `answer` to `question`: the student's own, or the model's, flagged for review. `choice`
    for a pick from the form's options, and `form` names the form it came from (`job_id` or `company`): WorkIt's
    rule reads them, and keeps neither."""
    asked = one_line(question)
    entry = {"question": asked, "answer": answer, "review": not own, "choice": choice or isinstance(answer, list)}
    return _Change(key(asked), asked, entry | (form or {}), student=student)


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
