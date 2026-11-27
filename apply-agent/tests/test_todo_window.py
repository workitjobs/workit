"""The application to-do tracker in WorkIt Auto Apply's window (developer only): the bridge's methods the page calls,
the same through `apply window`, its schedule, and every one of them refusing while the developer flag is off. No
window, no browser, no mail: the scan is a stand-in."""

import threading
from datetime import date, datetime

import pytest
from test_app_control import board, through  # noqa: F401 (the window's board fixture)

from apply import app_window, build, todo_scan, todos, workit
from apply.app_window import Bridge
from apply.todos import Source, Todo, TodoStore
from apply.workit import WorkIt


@pytest.fixture
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(todos, "TODOS", tmp_path / "todos.json")
    monkeypatch.setenv(todos.FLAG, "1")
    made = TodoStore()
    made.put(Todo("t1", "assessment", "Glean", "Software Engineer Intern", date(2026, 10, 22),
                  "https://www.hackerrank.com/test/abc", Source("Glean <support@hackerrankforwork.com>",
                                                                "Glean has invited you", datetime(2026, 10, 16))))
    return made


def test_the_page_lists_marks_and_scans_todos(board, store, monkeypatch):
    # Fault: a bridge method missing or naming the wrong to-do, or a scan going twice at once.
    scans = []
    monkeypatch.setattr(todo_scan, "live", lambda: scans.append(1) or todo_scan.Scan(read=3, added=1))
    bridge = Bridge(board, WorkIt(workit.LIVE))

    listed = bridge.todos()
    assert listed["enabled"] and [t["id"] for t in listed["todos"]] == ["t1"]
    assert bridge.mark_todo("t1", "done")["todo"]["status"] == "done"
    assert "error" in bridge.mark_todo("nope", "done") and "error" in bridge.mark_todo("t1", "snoozed")

    scanned = bridge.scan_todos(wait=True)
    assert scans == [1] and scanned["scan"]["read"] == 3 and not scanned["scanning"]
    bridge._todo_scanning.acquire()
    assert bridge.scan_todos() == {"scanning": True} and scans == [1]
    # `apply window todo-scan` (wait) during a scheduled scan waits for it and lists, without a second scan.
    threading.Timer(0.05, bridge._todo_scanning.release).start()
    waited = bridge.scan_todos(wait=True)
    assert scans == [1] and waited["enabled"] and not waited["scanning"]


def test_off_nothing_lists_scans_or_marks(board, store, monkeypatch):
    # Fault: the developer flag not checked by one of the page's methods, or the Student build reaching apply.todos.
    monkeypatch.setattr(todo_scan, "live", lambda: pytest.fail("scanned with the tracker off"))
    bridge = Bridge(board, WorkIt(workit.LIVE))
    for off in ({todos.FLAG: ""}, {"STUDENT": True}):
        if todos.FLAG in off:
            monkeypatch.delenv(todos.FLAG)
        else:
            monkeypatch.setenv(todos.FLAG, "1")
            monkeypatch.setattr(build, "STUDENT", True)
        assert bridge.todos()["enabled"] is False
        assert bridge.scan_todos()["enabled"] is False
        assert bridge.mark_todo("t1", "done")["enabled"] is False
        assert not app_window.todos_on()
    assert store.get("t1").status == "open"


def test_the_window_scans_on_open_and_again_on_its_schedule(board, store, monkeypatch):
    scans, slept = [], []
    monkeypatch.setattr(todo_scan, "live", lambda: scans.append(1) or todo_scan.Scan())

    def sleep(seconds):
        slept.append(seconds)
        if len(slept) == 2:
            raise SystemExit

    with pytest.raises(SystemExit):
        app_window._scan_todos_often(Bridge(board, WorkIt(workit.LIVE)), sleep)
    assert scans == [1, 1] and slept == [todo_scan.EVERY] * 2


def test_apply_window_lists_and_marks_todos_through_the_folder(board, store, tmp_path):
    # Fault: an action that reaches no bridge method, or a 200 for a refusal.
    assert [t["id"] for t in through(board, "todos", None, tmp_path)["todos"]] == ["t1"]
    assert through(board, "todo-mark", {"id": "t1", "status": "dismissed"}, tmp_path)["todo"]["status"] == "dismissed"
    assert through(board, "todo-mark", {"id": "nope", "status": "done"}, tmp_path)["status"] == 400


def test_the_todo_commands_send_their_actions(monkeypatch, capsys):
    from apply import app_control, cli

    sent = []
    monkeypatch.setattr(app_window, "running", lambda: 4242)
    monkeypatch.setattr(app_control, "ask", lambda action, body=None, **kw: sent.append((action, body)) or
                        {"status": 200})
    for argv in (["todos"], ["todo-done", "t1"], ["todo-dismiss", "t1"], ["todo-open", "t1"], ["todo-scan"]):
        with pytest.raises(SystemExit) as done:
            cli.main(["window", *argv])
        assert done.value.code == 0
    capsys.readouterr()
    assert sent == [("todos", None), ("todo-mark", {"id": "t1", "status": "done"}),
                    ("todo-mark", {"id": "t1", "status": "dismissed"}), ("todo-mark", {"id": "t1", "status": "open"}),
                    ("todo-scan", None)]


def test_apply_app_todos_turns_the_flag_on(monkeypatch):
    from apply import cli, student

    monkeypatch.delenv(todos.FLAG, raising=False)
    monkeypatch.setattr(student, "app", lambda: None)
    monkeypatch.setattr(app_window, "line_by_line", lambda *s: None)
    cli.main(["app", "--todos"])
    assert todos.enabled()
