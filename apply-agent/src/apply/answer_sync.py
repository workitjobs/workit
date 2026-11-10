"""The Answer bank's sync to WorkIt (KAN-746): each answer Apply saves,
changes or deletes goes to the student's answers on WorkIt, which the
extension fills from, with no import to run again.

- **Opt-in, off by default.** policies.yaml's `workit_sync: {answers: true}`
  turns it on (`enabled`). Off, the bank stamps nothing and sends nothing; a
  user with no WorkIt account never needs it.
- **What goes.** Each entry as the bank keeps it: question, answer, options,
  source, reviewed, the company it was first asked at, and `edited_at`, when
  Apply changed it (answer_bank.py stamps it). WorkIt applies the import's
  rules (backend services/apply_answers.py): only `source: lisul` is the
  student's own, and never an entry marked `reviewed: false`. So a draft
  Claude wrote goes as their Claude's, never as their words. An empty
  answer, or a multi-select's "none of these", deletes WorkIt's copy.
- **A newer edit wins.** WorkIt keeps its entry when it is newer, and names
  it in `kept`; an answer the student edited on WorkIt's site wins over an
  older Apply answer. An entry changed before the sync was on has no
  `edited_at`, so it never replaces one WorkIt has a time for.
- **WorkIt down, or no login.** Changes wait in `workit-answers-queue.json`
  (the newest per question) and go with the next change or `apply
  sync-answers`. A refusal (a 4xx) drops that batch and says so.
"""

import fcntl
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from apply import answer_bank
from apply.answer_bank import AnswerBank
from apply.home import HOME
from apply.workit import (
    CapReached,
    LoginExpired,
    NotLoggedIn,
    Unreachable,
    WorkIt,
    WorkItError,
)

QUEUE = HOME / "workit-answers-queue.json"
BATCH = 200  # WorkIt takes at most this many of each in one call


def enabled(policies: dict) -> bool:
    """policies.yaml's `workit_sync.answers`: off unless it is true."""
    return (policies.get("workit_sync") or {}).get("answers") is True


def payload(filed: str, entry: dict) -> dict:
    """An entry as WorkIt's `PATCH .../fill-answers` takes it."""
    answer = entry.get("answer")
    seen = entry.get("first_seen") if isinstance(entry.get("first_seen"), dict) else {}
    return {
        "question": str(entry.get("question") or filed).strip(),
        "answer": [str(a) for a in answer] if isinstance(answer, list) else "" if answer is None else str(answer),
        "options": [str(o) for o in entry.get("options") or ()],
        "source": str(entry.get("source") or answer_bank.CLAUDE),
        "reviewed": entry.get("reviewed") if isinstance(entry.get("reviewed"), bool) else None,
        "company": str(seen.get("company") or "") or None,
        "edited_at": _iso(entry.get("edited_at")),
    }


@dataclass
class Sent:
    saved: int = 0
    deleted: int = 0
    kept: list[str] = field(default_factory=list)  # WorkIt's entry was newer
    waiting: int = 0  # still in the queue: WorkIt could not be reached
    problems: list[str] = field(default_factory=list)


class AnswerSync:
    """Sends the bank's changes to WorkIt, and keeps what cannot go yet in a queue file."""

    def __init__(self, client: WorkIt | None = None, path: Path = QUEUE):
        self.client = client or WorkIt()
        self.path = path

    def changed(self, changed: dict[str, dict], deleted: list[str]) -> Sent:
        """answer_bank's on_change: queue the changed entries and deletes, then send all that waits."""
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        return self.send({k: ("answer", payload(k, e)) for k, e in changed.items()}
                         | {k: ("deleted", {"question": k, "edited_at": now}) for k in deleted})

    def push_all(self, bank: AnswerBank) -> Sent:
        """`apply sync-answers`: every entry in the bank, for catch-up."""
        return self.send({k: ("answer", payload(k, e)) for k, e in bank.raw().items()})

    def send(self, more: dict[str, tuple[str, dict]] | None = None) -> Sent:
        """Queue `more` (each in place of a waiting change to the same question), then send all that waits,
        oldest first, a batch at a time, until WorkIt cannot be reached."""
        with self._locked():
            waiting = self._read() | {answer_bank.key(k): v for k, v in (more or {}).items()}
            self._keep(waiting)
            sent = Sent()
            while waiting:
                batch = dict(list(waiting.items())[:BATCH])
                try:
                    said = self.client.sync_answers([b for kind, b in batch.values() if kind == "answer"],
                                                    [b for kind, b in batch.values() if kind == "deleted"])
                except (NotLoggedIn, LoginExpired, Unreachable, CapReached) as error:
                    sent.problems.append(f"waits to go to WorkIt ({type(error).__name__}: {error})")
                    break
                except WorkItError as error:  # refused for good: sending it again would fail again
                    sent.problems.append(f"WorkIt refused {len(batch)} answers ({error})")
                    said = {}
                sent.saved += int(said.get("saved") or 0)
                sent.deleted += int(said.get("deleted") or 0)
                sent.kept += list(said.get("kept") or ())
                waiting = {k: v for k, v in waiting.items() if k not in batch}
                self._keep(waiting)
            sent.waiting = len(waiting)
            return sent

    def waiting(self) -> int:
        return len(self._read())

    def _read(self) -> dict[str, tuple[str, dict]]:
        try:
            return {k: (v[0], v[1]) for k, v in json.loads(self.path.read_text()).items()}
        except (FileNotFoundError, ValueError):
            return {}

    def _keep(self, waiting: dict) -> None:
        if not waiting:
            self.path.unlink(missing_ok=True)
            return
        part = self.path.with_suffix(".part")
        part.write_text(json.dumps(waiting, indent=1))
        part.replace(self.path)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_suffix(".lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield


def bank(path: Path, policies: dict, sync: AnswerSync | None = None) -> AnswerBank:
    """The Answer bank at `path`, which sends its changes to WorkIt when policies.yaml turns the sync on."""
    if not enabled(policies):
        return AnswerBank(path)
    sync = sync or AnswerSync()

    def on_change(changed: dict[str, dict], deleted: list[str]) -> None:
        sent = sync.changed(changed, deleted)
        for problem in sent.problems:
            print(f"Answer bank: {problem}", file=sys.stderr)

    return AnswerBank(path, on_change=on_change)


def report(sent: Sent) -> str:
    """`apply sync-answers`' lines: counts and questions only, never an answer."""
    lines = [f"Sent to WorkIt: {sent.saved} saved, {sent.deleted} deleted."]
    if sent.kept:
        lines.append(f"Kept WorkIt's newer answer to {len(sent.kept)}: " + "; ".join(sent.kept))
    if sent.waiting:
        lines.append(f"{sent.waiting} wait in {QUEUE.name} for the next sync.")
    return "\n".join(lines + sent.problems)


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()
    if isinstance(value, date):
        return None
    return str(value) if value else None
