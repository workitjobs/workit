"""Application to-dos (developer only): what the user's mail asks them to do for a job application, kept as one
list in the data folder, one to-do per mail thread.

A to-do is one of KINDS: an online assessment, a form, a questionnaire, an interview to schedule, an account or
verification step, a document request, or an offer. `apply.todo_scan` reads mail and finds them; this module only
keeps them. Each has its company, role, kind, due date, link and the mail it came from, and a status the user sets:
open, done or dismissed.

Dedupe is by thread: a later mail in a thread updates that thread's to-do (its kind, due date, link, source), never
adds a second one, and never reopens one the user marked done or dismissed. A mail Apply reads again changes nothing.

The tracker is a developer feature behind a flag: it is on only in a Developer checkout (never `build.STUDENT`) with
FLAG set in the environment (`apply app --todos` sets it). Off, nothing scans, the window's methods refuse, and the
page shows no To-dos. The store is plain JSON (`todos.json`, under a lock file, saved whole), as the Tracker is.
"""

import dataclasses
import json
import os
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


@dataclass(frozen=True)
class Todo:
    """One thing to do, from one mail thread (`thread`, its id)."""

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

    def shown(self) -> dict:
        """As the window and `apply window todos` show it."""
        return {"id": self.thread, "kind": self.kind, "kind_label": KINDS.get(self.kind, self.kind),
                "company": self.company, "role": self.role, "due": self.due.isoformat() if self.due else None,
                "link": self.link, "status": self.status, "by": self.by,
                "source": {"sender": self.source.sender, "subject": self.source.subject,
                           "arrived": self.source.arrived.isoformat(), "message_id": self.source.message_id,
                           "url": gmail_url(self.source.message_id)},
                "found": self.found.isoformat() if self.found else None}


def gmail_url(message_id: str) -> str | None:
    """The mail in Gmail's web app, by its X-GM-MSGID (decimal, Gmail's own links use hex)."""
    if not message_id.isdigit():
        return None
    return f"https://mail.google.com/mail/u/0/#all/{int(message_id):x}"


class TodoStore:
    """The to-dos as one JSON file. Each call reads the file and each write saves it again, atomically, under a lock
    file: the window's scan and `apply window` share it."""

    def __init__(self, path: Path = TODOS):
        self.path = path

    def all(self) -> list[Todo]:
        """Every to-do, open first, then by due date (none last), then newest mail first."""
        with self._held(write=False) as todos:
            listed = list(todos.values())
        return sorted(listed, key=_order)

    def get(self, thread: str) -> Todo | None:
        with self._held(write=False) as todos:
            return todos.get(thread)

    def put(self, todo: Todo) -> str:
        """Keep `todo`, one per thread. A new thread is "added". A newer mail in a known thread updates its kind, due
        date, link, company, role and source and is "updated"; the status the user set stays. An older or the same
        mail is "kept" and changes nothing."""
        with self._held(write=True) as todos:
            known = todos.get(todo.thread)
            if known is None:
                todos[todo.thread] = todo
                return "added"
            if todo.source.arrived <= known.source.arrived:
                return "kept"
            todos[todo.thread] = dataclasses.replace(
                todo, status=known.status, found=known.found,
                company=todo.company or known.company, role=todo.role or known.role,
                due=todo.due or known.due, link=todo.link or known.link)
            return "updated"

    def mark(self, thread: str, status: str) -> Todo:
        """Set a to-do's status: done, dismissed, or open again. Raises KeyError for no such to-do, ValueError for
        no such status."""
        if status not in STATUSES:
            raise ValueError(f"No such status: {status}. Use one of: {', '.join(STATUSES)}.")
        with self._held(write=True) as todos:
            todos[thread] = dataclasses.replace(todos[thread], status=status)
            return todos[thread]

    @contextmanager
    def _held(self, write: bool) -> Iterator[dict[str, Todo]]:
        with locks.held(self.path.with_suffix(".lock")):
            todos = self._load()
            yield todos
            if write:
                part = self.path.with_suffix(".part")
                part.write_text(json.dumps({"todos": [dataclasses.asdict(t) for t in todos.values()]}, indent=1,
                                           default=_plain))
                part.chmod(0o600)
                os.replace(part, self.path)

    def _load(self) -> dict[str, Todo]:
        try:
            saved = json.loads(self.path.read_text())
        except FileNotFoundError:
            return {}
        return {t["thread"]: _todo(t) for t in saved.get("todos", [])}


def _order(todo: Todo) -> tuple:
    return (todo.status != OPEN, todo.due is None, todo.due or date.max, -todo.source.arrived.timestamp())


def _plain(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def _todo(saved: dict) -> Todo:
    source = saved["source"]
    return Todo(**{**saved,
                   "due": date.fromisoformat(saved["due"]) if saved.get("due") else None,
                   "found": datetime.fromisoformat(saved["found"]) if saved.get("found") else None,
                   "source": Source(**{**source, "arrived": datetime.fromisoformat(source["arrived"])})})
