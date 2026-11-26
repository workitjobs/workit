"""WorkIt Auto Apply's window read from a terminal (apply.app_control): what the window shows, over the window's
request folder. No window and no browser: in CI."""

import threading
import time
from contextlib import contextmanager

import pytest

from apply import app_control, dashboard, workit
from apply.app_window import Bridge
from apply.dashboard import Dashboard
from apply.workit import WorkIt


class NoFrames:
    def frame(self, worker, tab=None):
        return None

    def wait(self, worker, after, timeout, tab=None):
        return None, after

    def input(self, worker, event, tab=None):
        return None

    def chooser(self, worker, tab=None):
        return None

    def field_error(self, worker):
        return ""


@pytest.fixture
def board(monkeypatch):
    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", lambda *a, **k: pytest.fail("the window opened a port"))
    with Dashboard(2, NoFrames(), serve=False) as made:
        yield made


ACME = "https://jobs.lever.co/acme/1"
GLOBEX = "https://boards.greenhouse.io/globex/jobs/2"
LEGAL = {"field": "Will you require sponsorship?", "why": "the profile says no sponsorship", "kind": "review",
         "holds": True, "dismissed": False}
DISMISSED = {"field": "GPA", "why": "not in the profile", "kind": "review", "holds": True, "dismissed": True}


def held(board, k, url, **caption):
    # An id with a hyphen in it, as an Application of the student's own has.
    board.update(k, company="Acme", role="Intern", posting_url=url, application_id=f"own-{k}a1b2", status="filling")
    board.update(k, status="ready to submit", again=True, **caption)


def test_the_state_is_the_windows_with_every_held_forms_answers_flags_and_screenshot(board, tmp_path):
    """Fault: the state drops a held form's answers, its Pre-submit flags, its legal hold, Auto-submit's reason or its
    screenshot; lists a dismissed flag as holding; or sorts a check after a form ready to submit; or misses the Record of an id
    with a hyphen in it."""
    held(board, 0, ACME, answers=[{"question": "Why us?", "answer": "Because.", "from": "written", "kind": "textarea"},
                                  {"question": "Email", "answer": "a@b.co", "from": "profile", "kind": "text"}],
         verification={"state": "flagged", "flags": [LEGAL, DISMISSED]}, auto_said="Waiting for you: it has an Essay.")
    held(board, 1, GLOBEX)
    record = tmp_path / "2026-11-26" / "acme-own-0a1b2"
    record.mkdir(parents=True)
    (record / "form.png").write_bytes(b"png")

    state = app_control.view(board.state(), {"shows": "apply"}, [record])

    check, ready = state["needs_you"]
    assert (check["tile"], check["ask"], check["company"], check["url"]) == ("tile-0", "check", "Acme", ACME)
    assert check["answers"][0] == {"question": "Why us?", "answer": "Because.", "source": "written",
                                   "kind": "textarea", "topic": ""}
    assert check["essays"] == [{"question": "Why us?", "text": "Because."}]
    assert [f["field"] for f in check["flags"]] == [LEGAL["field"]]
    assert check["legal_holds"] == [{"field": LEGAL["field"], "why": LEGAL["why"]}]
    assert check["why_not"] == "Waiting for you: it has an Essay."
    assert check["screenshot"] == str(record / "form.png") and check["held"]
    assert (ready["tile"], ready["ask"], ready["screenshot"]) == ("tile-1", "submit", "")


def test_a_question_waiting_names_the_item_and_question_answer_posts(board):
    """Fault: a Needs-you question shows without the item id and the question that /answer takes."""
    held(board, 0, ACME, missing=["When can you start?"], required={"When can you start?": True})

    [job] = app_control.view(board.state())["needs_you"]
    assert (job["ask"], job["id"], job["tile"]) == ("question", "1", "tile-0")
    assert job["missing"][0]["question"] == "When can you start?" and job["missing"][0]["required"]


@contextmanager
def watching(board, folder=app_control.CONTROL):
    """The window's watch on `folder`, as app_window.run starts it, while the block runs."""
    bridge, stop = Bridge(board, WorkIt(workit.LIVE)), threading.Event()

    def watch():
        while not stop.is_set():
            for thread in app_control.serve(bridge, folder):
                thread.join()
            time.sleep(0.01)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stop.set()
        watcher.join()


def through(board, action, body=None, folder=app_control.CONTROL):
    """`action` as the command sends it, answered by the window's watch."""
    with watching(board, folder):
        return app_control.ask(action, body, folder, 5.0)


def test_the_state_comes_through_the_windows_folder_and_nothing_else_does(board, tmp_path):
    """Fault: a request names any route (/start, /closed), so the folder reaches past what the window shows."""
    for action in ("/start", "closed"):
        assert through(board, action, {}, tmp_path)["status"] == 404
    assert through(board, "state", None, tmp_path)["state"]["window"]["shows"] == "sign-in"
    assert not list(tmp_path.iterdir())  # nothing left behind
