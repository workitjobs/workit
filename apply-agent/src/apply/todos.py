"""Application to-dos (developer only): what the user's mail asks them to do for a job application, kept as one
list in the data folder, one to-do per mail thread.

A to-do is one of KINDS: an online assessment, a form, a questionnaire, an interview to schedule, an account or
verification step, a document request, or an offer. `apply.todo_scan` reads mail and finds them; this module only
keeps them. Each has its company, role, kind, due date, link and the mail it came from, and a status the user sets:
open, done or dismissed.

Dedupe is by thread: a later mail in a thread updates that thread's to-do (its kind, due date, link, source), never
adds a second one, and never reopens one the user marked done or dismissed. A mail Apply reads again changes nothing.
Then by `Todo.key`: an invite and its reminder come in two threads but name the same company, kind and assessment or
form ("Ramp 2025 Coding Assessment"), so they are one to-do with every mail in its `sources`, the earliest due date,
the latest link, and the status the user set on either.

The tracker is a developer feature behind a flag: it is on only in a Developer checkout (never `build.STUDENT`) with
FLAG set in the environment (`apply app --todos` sets it). Off, nothing scans, the window's methods refuse, and the
page shows no To-dos. The store is plain JSON (`todos.json`, under a lock file, saved whole), as the Tracker is.
"""

import dataclasses
import json
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from apply import build, locks
from apply.home import HOME

FLAG = "APPLY_DEV_TODOS"  # set by a Developer checkout's `apply app --todos`
TODOS = HOME / "todos.json"
OFF = (f"The application to-do tracker is a developer feature and is off: open the window with "
       f"`uv run apply app --todos` (or set {FLAG}=1) in a Developer checkout.")

# What a to-do asks the user to do, as the window names it.
KINDS = {
    "assessment": "Online assessment",
    "form": "Form",
    "questionnaire": "Questionnaire",
    "interview": "Schedule interview",
    "account": "Account or verification",
    "documents": "Documents requested",
    "offer": "Offer",
}
OPEN, DONE, DISMISSED = "open", "done", "dismissed"
STATUSES = (OPEN, DONE, DISMISSED)
# The assessment or form a subject names, which its invite and its reminder name alike: "Ramp invited you to take
# Ramp 2025 Coding Assessment" and "Reminder: Ramp is waiting for your Ramp 2025 Coding Assessment result".
TASK = re.compile(r"(?:[A-Z0-9][\w&+.'-]*\s+){0,6}(?:Assessment|Challenge|Test|Assignment|Form|Questionnaire|Survey)\b")
TASK_FILLER = re.compile(r"^(?:(?:your|the|a|an|our|this|new)\s+)+", re.IGNORECASE)


def enabled(environ=os.environ) -> bool:
    """Whether the tracker is on: a Developer checkout with FLAG set. Read when it runs, never at import."""
    return not build.STUDENT and (environ.get(FLAG) or "").strip().lower() not in ("", "0", "false", "no", "off")


@dataclass(frozen=True)
class Source:
    """The mail a to-do came from: enough for the user to find it, never its text."""

    sender: str
    subject: str
    arrived: datetime
    message_id: str = ""  # Gmail's message id (X-GM-MSGID), for a link to the mail
    thread: str = ""  # the mail's thread; "" is the to-do's own


@dataclass(frozen=True)
class Todo:
    """One thing to do, from one mail thread or more (`thread`, its id: the first one's). `source` is its latest mail,
    `sources` every mail it came from, oldest first (empty means only `source`)."""

    thread: str
    kind: str
    company: str
    role: str
    due: date | None
    link: str | None
    source: Source
    status: str = OPEN
    found: datetime | None = None  # when a scan first found it
    by: str = "rules"  # what read it: "rules" (the heuristics) or "model"
    sources: tuple[Source, ...] = ()

    @property
    def mails(self) -> tuple[Source, ...]:
        """Every mail, oldest first, each with its thread."""
        return tuple(m if m.thread else dataclasses.replace(m, thread=self.thread)
                     for m in self.sources or (self.source,))

    @property
    def key(self) -> str:
        """What a to-do from another thread must share to be this one: its company, kind and the assessment or form
        name a subject gives. "" when a subject names none: then only its thread joins mail to it."""
        names = (TASK.search(m.subject) for m in self.mails)
        name = next((TASK_FILLER.sub("", n[0]) for n in names if n), "")
        company = _words(self.company)
        return f"{company}|{self.kind}|{_words(name)}" if company and name else ""

    def shown(self) -> dict:
        """As the window and `apply window todos` show it."""
        return {"id": self.thread, "kind": self.kind, "kind_label": KINDS.get(self.kind, self.kind),
                "company": self.company, "role": self.role, "due": self.due.isoformat() if self.due else None,
                "link": self.link, "status": self.status, "by": self.by,
                "source": {"sender": self.source.sender, "subject": self.source.subject,
                           "arrived": self.source.arrived.isoformat(), "message_id": self.source.message_id,
                           "url": gmail_url(self.source.message_id)},
                "sources": [{"sender": m.sender, "subject": m.subject, "arrived": m.arrived.isoformat(),
                             "message_id": m.message_id, "url": gmail_url(m.message_id)} for m in reversed(self.mails)],
                "found": self.found.isoformat() if self.found else None}


def gmail_url(message_id: str) -> str | None:
    """The mail in Gmail's web app, by its X-GM-MSGID (decimal, Gmail's own links use hex)."""
    if not message_id.isdigit():
        return None
    return f"https://mail.google.com/mail/u/0/#all/{int(message_id):x}"


class TodoStore:
    """The to-dos as one JSON file. Each call reads the file and each write saves it again, atomically, under a lock
    file: the window's scan and `apply window` share it."""

    def __init__(self, path: Path | None = None):
        self.path = path or TODOS  # read when made, so a test can move it

    def all(self) -> list[Todo]:
        """Every to-do, open first, then by due date (none last), then newest mail first."""
        with self._held(write=False) as todos:
            listed = list(todos.values())
        return sorted(listed, key=_order)

    def get(self, thread: str) -> Todo | None:
        """The to-do with this id, or the one a mail of this thread joined."""
        with self._held(write=False) as todos:
            return _of_thread(todos, thread)

    def seen(self, thread: str, arrived: datetime) -> bool:
        """Whether a to-do holds a mail of `thread` that arrived at `arrived` or later: a scan reads it no more."""
        with self._held(write=False) as todos:
            return any(m.thread == thread and m.arrived >= arrived for t in todos.values() for m in t.mails)

    def put(self, todo: Todo) -> str:
        """Keep `todo`: one per thread, and one per `Todo.key` across threads. A new one is "added". A newer mail in a
        known thread, or a mail of a new thread with a known key, joins that to-do and is "updated"; the status the
        user set stays. An older or the same mail of a known thread is "kept" and changes nothing."""
        with self._held(write=True) as todos:
            known = _of_thread(todos, todo.thread) or _of_key(todos, todo.key)
            if known is None:
                todos[todo.thread] = todo
                return "added"
            if any(m.thread == todo.thread and m.arrived >= todo.source.arrived for m in known.mails):
                return "kept"
            todos[known.thread] = _joined(known, todo)
            return "updated"

    def lend_links(self) -> int:
        """Give each to-do with no link the link of the newest to-do of the same company and kind that has one: a
        confirmation that says the assessment comes in another mail ("Confirmation on your Application +
        CodeSignal") opens that mail's assessment. Returns how many it gave one."""
        with self._held(write=True) as todos:
            linked = sorted((t for t in todos.values() if t.link and t.company),
                            key=lambda t: t.source.arrived, reverse=True)
            lent = 0
            for thread, todo in todos.items():
                if todo.link or not todo.company:
                    continue
                donor = next((t for t in linked if t.kind == todo.kind
                              and t.company.casefold() == todo.company.casefold()), None)
                if donor is not None:
                    todos[thread] = dataclasses.replace(todo, link=donor.link)
                    lent += 1
            return lent

    def mark(self, thread: str, status: str) -> Todo:
        """Set a to-do's status: done, dismissed, or open again. Raises KeyError for no such to-do, ValueError for
        no such status."""
        if status not in STATUSES:
            raise ValueError(f"No such status: {status}. Use one of: {', '.join(STATUSES)}.")
        with self._held(write=True) as todos:
            if (known := _of_thread(todos, thread)) is None:
                raise KeyError(thread)
            todos[known.thread] = dataclasses.replace(known, status=status)
            return todos[known.thread]

    @contextmanager
    def _held(self, write: bool) -> Iterator[dict[str, Todo]]:
        with locks.held(self.path.with_suffix(".lock")):
            todos = self._load()
            yield todos
            if write:
                part = self.path.with_suffix(".part")
                part.write_text(json.dumps({"todos": [dataclasses.asdict(t) for t in todos.values()]}, indent=1,
                                           default=_plain), encoding="utf-8")
                part.chmod(0o600)
                os.replace(part, self.path)

    def _load(self) -> dict[str, Todo]:
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        joined: dict[str, Todo] = {}
        for todo in sorted((_todo(t) for t in saved.get("todos", [])), key=lambda t: t.mails[0].arrived):
            known = _of_key(joined, todo.key)  # to-dos kept apart before keys joined them
            if known is None:
                joined[todo.thread] = todo
            else:
                joined[known.thread] = _joined(known, todo)
        return joined


def _of_thread(todos: dict[str, Todo], thread: str) -> Todo | None:
    return todos.get(thread) or next((t for t in todos.values() if any(m.thread == thread for m in t.mails)), None)


def _of_key(todos: dict[str, Todo], key: str) -> Todo | None:
    return next((t for t in todos.values() if key and t.key == key), None) if key else None


def _joined(known: Todo, new: Todo) -> Todo:
    """`new`'s mails joined to `known`, which keeps its id. The latest mail gives the kind, company, role, link and
    source, each the other's when it has none. Within one thread the latest due date stands (a later mail can move
    it); across threads the earliest does. A done or dismissed status on either stays."""
    latest, other = (new, known) if new.source.arrived > known.source.arrived else (known, new)
    one_thread = any(m.thread == new.thread for m in known.mails)
    dues = [d for d in (known.due, new.due) if d]
    due = (latest.due or other.due) if one_thread else min(dues, default=None)
    found = [f for f in (known.found, new.found) if f]
    return dataclasses.replace(
        latest, thread=known.thread, source=latest.mails[-1], status=known.status if known.status != OPEN else new.status,
        company=latest.company or other.company, role=latest.role or other.role, due=due,
        link=latest.link or other.link, found=min(found, default=None),
        sources=tuple(sorted({*known.mails, *new.mails}, key=lambda m: m.arrived)))


def _order(todo: Todo) -> tuple:
    return (todo.status != OPEN, todo.due is None, todo.due or date.max, -todo.source.arrived.timestamp())


def _plain(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def _words(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _todo(saved: dict) -> Todo:
    def source(kept: dict) -> Source:
        return Source(**{**kept, "arrived": datetime.fromisoformat(kept["arrived"])})

    return Todo(**{**saved,
                   "due": date.fromisoformat(saved["due"]) if saved.get("due") else None,
                   "found": datetime.fromisoformat(saved["found"]) if saved.get("found") else None,
                   "source": source(saved["source"]),
                   "sources": tuple(source(s) for s in saved.get("sources", []))})
