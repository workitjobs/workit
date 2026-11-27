"""The application to-do store (apply.todos): one to-do per mail thread, the user's status kept, and the developer
flag that keeps the tracker off for everyone else. No browser, no network."""

from datetime import date, datetime

import pytest

from apply import build, todos
from apply.todos import DISMISSED, DONE, OPEN, Source, Todo, TodoStore

ARRIVED = datetime(2026, 11, 20, 9, 0)


def todo(thread: str = "t1", arrived: datetime = ARRIVED, **fields) -> Todo:
    made = {"kind": "assessment", "company": "Acme", "role": "Software Engineer Intern", "due": date(2026, 11, 27),
            "link": "https://www.hackerrank.com/test/abc", "source": Source("Acme <jobs@acme.com>", "Your assessment",
                                                                            arrived, "1800000000000000001")}
    return Todo(thread=thread, **(made | fields))


def test_a_new_thread_is_added_and_read_back_whole(tmp_path):
    # Fault: a field lost on the way to the file and back (a date saved as text, the source dropped).
    store = TodoStore(tmp_path / "todos.json")

    assert store.put(todo(found=ARRIVED)) == "added"

    assert store.all() == [todo(found=ARRIVED)]


def test_a_later_mail_in_a_thread_updates_its_todo_and_keeps_the_users_status(tmp_path):
    # Fault: dedupe by thread broken (a second to-do), or a newer mail reopening a dismissed one.
    store = TodoStore(tmp_path / "todos.json")
    store.put(todo())
    store.mark("t1", DISMISSED)

    later = todo(arrived=datetime(2026, 11, 22, 9, 0), due=date(2026, 11, 30), link=None)

    assert store.put(later) == "updated"
    [kept] = store.all()
    assert (kept.status, kept.due, kept.link) == (DISMISSED, date(2026, 11, 30), "https://www.hackerrank.com/test/abc")


def test_the_same_or_an_older_mail_changes_nothing(tmp_path):
    # Fault: a re-scan of mail already read overwriting what a newer mail said.
    store = TodoStore(tmp_path / "todos.json")
    store.put(todo(arrived=datetime(2026, 11, 22)))

    assert store.put(todo(arrived=datetime(2026, 11, 21), kind="form")) == "kept"
    assert store.get("t1").kind == "assessment"


def test_open_todos_come_first_by_due_date(tmp_path):
    store = TodoStore(tmp_path / "todos.json")
    store.put(todo("late", due=date(2026, 12, 5)))
    store.put(todo("none", due=None))
    store.put(todo("soon", due=date(2026, 11, 25)))
    store.put(todo("done", due=date(2026, 11, 21)))
    store.mark("done", DONE)

    assert [t.thread for t in store.all()] == ["soon", "late", "none", "done"]


def test_marking_takes_only_a_known_todo_and_status(tmp_path):
    store = TodoStore(tmp_path / "todos.json")
    store.put(todo())

    with pytest.raises(ValueError):
        store.mark("t1", "snoozed")
    with pytest.raises(KeyError):
        store.mark("nope", DONE)
    assert store.mark("t1", OPEN).status == OPEN


def test_the_tracker_is_on_only_in_a_developer_checkout_with_the_flag(monkeypatch):
    # Fault: the flag ignored (on for everyone), or the Student build turning it on from the environment.
    assert not todos.enabled({})
    assert not todos.enabled({todos.FLAG: "0"})
    assert todos.enabled({todos.FLAG: "1"})
    monkeypatch.setattr(build, "STUDENT", True)
    assert not todos.enabled({todos.FLAG: "1"})


def test_shown_links_the_source_mail_in_gmail():
    shown = todo().shown()

    assert shown["kind_label"] == "Online assessment"
    assert shown["source"]["url"] == f"https://mail.google.com/mail/u/0/#all/{1800000000000000001:x}"
    assert todo(source=Source("a", "b", ARRIVED)).shown()["source"]["url"] is None
