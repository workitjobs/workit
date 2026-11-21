"""WorkIt's Answer bank for the tests (W11): `GET .../answer-bank` alone (Source), or read and written (Server).
No test reaches the network."""

import threading

from apply.answer_bank import key
from apply.workit import Unreachable


class Source:
    """WorkIt's bank as `GET .../answer-bank` serves it, or a read that fails until `fails` reads have."""

    def __init__(self, answers: dict | None = None, version: int = 7, fails: int = 0):
        self.answers, self.version, self.fails, self.reads = answers or {}, version, fails, 0

    def read(self) -> tuple[dict, int]:
        self.reads += 1
        if self.reads <= self.fails:
            raise Unreachable("WorkIt didn't answer")
        return self.answers, self.version



class Server(Source):
    """WorkIt's bank, read and written: `PATCH .../answer-bank` keeps out the questions in `keeps_out` (its rule),
    gets no answer for the first `unanswered` writes, refuses each with `refusal`, waits for `gate` on the first
    write, and counts `others`' writes meanwhile into each reply's version."""

    def __init__(self, answers: dict | None = None, keeps_out: tuple = (), unanswered: int = 0,
                 refusal: Exception | None = None, gate: threading.Event | None = None, others: int = 0):
        super().__init__(answers)
        self.keeps_out, self.unanswered, self.refusal, self.gate, self.others = keeps_out, unanswered, refusal, gate, others
        self.sent: list[tuple[list[dict], list[str]]] = []

    def change(self, entries: list[dict], deleted: list[str]) -> tuple[int, dict[str, str]]:
        self.sent.append((entries, deleted))
        if self.gate is not None:
            self.gate.wait(5)
            self.gate = None
        if self.unanswered:
            self.unanswered -= 1
            raise Unreachable("api.workitjobs.ai: 502", 502)
        if self.refusal:
            raise self.refusal
        out = {e["question"]: "It names Zipline, so it stays on this form." for e in entries if e["question"] in self.keeps_out}
        self.answers |= {key(e["question"]): {"question": e["question"], "answer": e["answer"], "own": not e["review"]}
                         for e in entries if e["question"] not in out}
        for question in deleted:
            self.answers.pop(key(question), None)
        self.version += 1 + self.others
        return self.version, out

