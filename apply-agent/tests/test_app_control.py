"""WorkIt Auto Apply's window read and driven from a terminal (apply.app_control): what the window shows, and its
buttons through their own routes, over the window's request folder. No window and no browser: in CI."""

import json
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


def test_submit_through_the_folder_is_the_buttons_own_route_with_its_refusals(board, tmp_path):
    """Fault: submit reaches the run some other way than POST /submit, so a form still missing an answer is pressed,
    or an approved one is never handed to the run."""
    held(board, 0, ACME, missing=["When can you start?"], required={"When can you start?": True})
    held(board, 1, GLOBEX)

    refused = through(board, "submit", {"id": "tile-0"}, tmp_path)
    assert refused["status"] == 409 and "needs your answers" in refused["error"]
    assert not board.submit_asked(0)
    assert through(board, "submit", {"id": "tile-1"}, tmp_path) == {"status": 200, "message": "Submitting it."}
    assert board.submit_asked(1)
    assert not list(tmp_path.iterdir())  # nothing left behind


def test_a_request_taken_too_late_does_nothing(board, tmp_path):
    """Fault: a submit the command gave up on is pressed later, when the window next looks."""
    held(board, 0, ACME)
    app_control._write(tmp_path / "1-1.request", {"action": "submit", "body": {"id": "tile-0"}, "expires": 0})
    for thread in app_control.serve(Bridge(board, WorkIt(workit.LIVE)), tmp_path):
        thread.join()
    assert json.loads((tmp_path / "1-1.reply").read_text())["status"] == 408
    assert not board.submit_asked(0)


def test_a_request_that_isnt_one_is_answered_400(board, tmp_path):
    """Fault: a request the window can't read is never answered, so the command waits and can't tell it did nothing."""
    app_control._write(tmp_path / "1-1.request", {"action": "submit", "body": {"id": "tile-0"}, "expires": "soon"})
    for thread in app_control.serve(Bridge(board, WorkIt(workit.LIVE)), tmp_path):
        thread.join()
    assert json.loads((tmp_path / "1-1.reply").read_text())["status"] == 400
    assert not list(tmp_path.glob("*.taken"))


def test_only_the_windows_buttons_are_actions(board, tmp_path):
    """Fault: a request names any route (/start, /closed, /dismiss), so the folder reaches past the buttons."""
    for action in ("/start", "closed", "dismiss"):
        assert through(board, action, {}, tmp_path)["status"] == 404
    assert through(board, "state", None, tmp_path)["state"]["window"]["shows"] == "sign-in"
    assert not list(tmp_path.iterdir())  # nothing left behind


def test_the_command_asks_yes_before_submit_then_sends_it_to_the_window(board, monkeypatch, capsys):
    """Fault: `apply window submit` goes without --yes, or names another action or form than the one it was given;
    or a shut window is waited on."""
    from apply import app_window, cli

    held(board, 0, ACME)
    with pytest.raises(SystemExit) as shut:
        cli.main(["window", "submit", "tile-0", "--yes"])
    assert shut.value.code == 1 and "isn't open" in capsys.readouterr().out

    monkeypatch.setattr(app_window, "running", lambda: 4242)
    with pytest.raises(SystemExit) as unsure:
        cli.main(["window", "submit", "tile-0"])
    assert unsure.value.code == 1 and "--yes" in capsys.readouterr().out
    assert not list(app_control.CONTROL.glob("*"))

    with watching(board), pytest.raises(SystemExit) as sent:
        cli.main(["window", "submit", "tile-0", "--yes"])
    out = capsys.readouterr().out  # the route's own line first: in the window's process, not the command's
    assert sent.value.code == 0 and json.loads(out[out.index("{"):])["message"] == "Submitting it."
    assert board.submit_asked(0)


def test_the_command_sends_each_buttons_own_body(monkeypatch, capsys, tmp_path):
    """Fault: `apply window answer` or `stop` sends a body its route doesn't take (a file not as /answer reads it, a
    stop of every held form for --new-only), or stop goes without --yes."""
    from apply import app_window, cli

    sent = []
    monkeypatch.setattr(app_window, "running", lambda: 4242)
    monkeypatch.setattr(app_control, "ask", lambda action, body: sent.append((action, body)) or {"status": 200})
    resume = tmp_path / "cv.pdf"
    resume.write_bytes(b"%PDF")
    for argv in (["answer", "1", "Resume", "--file", str(resume)], ["answer", "1", "When can you start?", "June"],
                 ["stop", "--new-only"], ["stop"], ["stop", "--yes"], ["remove", ACME]):
        with pytest.raises(SystemExit):
            cli.main(["window", *argv])
    capsys.readouterr()
    assert sent == [("answer", {"id": "1", "question": "Resume", "answer": "",
                                "file": {"name": "cv.pdf", "data": "JVBERg=="}}),
                    ("answer", {"id": "1", "question": "When can you start?", "answer": "June"}),
                    ("stop", {"new_only": True}), ("stop", {}), ("remove", {"link": ACME})]


def test_a_code_through_the_folder_reaches_the_run_once_with_its_case(board, tmp_path):
    """Fault: /code changes the code's case or drops a character, hands it to the run twice, or takes what is no code
    or a form that isn't held (sent already)."""
    held(board, 0, ACME)
    held(board, 1, GLOBEX)
    board.update(1, status="submitted")

    assert through(board, "code", {"id": "tile-0", "code": "Ox N!"}, tmp_path)["status"] == 400
    assert through(board, "code", {"id": "tile-1", "code": "OxNbtPnI"}, tmp_path)["status"] == 409
    assert through(board, "code", {"id": "tile-0", "code": " OxNb tPnI "}, tmp_path) == {
        "status": 200, "message": "Entering the code."}
    assert through(board, "code", {"id": "tile-0", "code": "OxNbtPnI"}, tmp_path)["status"] == 409  # one at a time
    assert board.code_given(0) == "OxNbtPnI" and board.code_given(0) == ""
    board.update(0, coding=False, code_said="The job site says the code is wrong")
    [job] = [j for j in through(board, "state", None, tmp_path)["state"]["needs_you"] if j["tile"] == "tile-0"]
    assert job["code_said"] == "The job site says the code is wrong" and job["coding"] is False


def test_the_code_command_asks_yes_then_waits_for_the_job_sites_answer(monkeypatch, capsys):
    """Fault: `apply window code` goes without --yes, sends the code to another form, or reports it sent before the
    job site confirmed it, or a wrong code as done."""
    from apply import app_window, cli

    monkeypatch.setattr(app_window, "running", lambda: 4242)
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    sent, states = [], []

    def ask(action, body=None):
        sent.append((action, body))
        if action == "code":
            return {"status": 200, "message": "Entering the code."}
        job = states.pop(0) if states else {}
        return {"status": 200, "state": {"needs_you": [{"tile": "tile-3", "id": "7", **job}]}}

    monkeypatch.setattr(app_control, "ask", ask)
    with pytest.raises(SystemExit) as unsure:
        cli.main(["window", "code", "tile-3", "OxNbtPnI"])
    assert unsure.value.code == 1 and not sent

    states[:] = [{}, {"coding": True}, {"coding": False, "code_said": "The job site says the code is wrong"}]
    with pytest.raises(SystemExit) as wrong:
        cli.main(["window", "code", "7", "OxNbtPnI", "--yes"])  # by its id: the first state names its tile
    assert wrong.value.code == 1 and "wrong" in capsys.readouterr().out
    assert sent[1] == ("code", {"id": "tile-3", "code": "OxNbtPnI"})

    states[:] = [{"coding": True}, {"coding": True, "status": "submitted"}]
    with pytest.raises(SystemExit) as done:
        cli.main(["window", "code", "tile-3", "OxNbtPnI", "--yes"])
    assert done.value.code == 0 and "confirmed" in capsys.readouterr().out


def test_send_anyway_hands_its_reason_to_the_run_once_and_nothing_else_gives_way(board, tmp_path):
    """Fault: an override reason is lost on the way (the Record never says why it was sent), handed to the run twice
    or to the next form on the tile, or lets a form still missing a required answer through."""
    held(board, 0, ACME, missing=["When can you start?"], required={"When can you start?": True})
    held(board, 1, GLOBEX)

    refused = through(board, "submit", {"id": "tile-0", "override": "The pay is mine"}, tmp_path)
    assert refused["status"] == 409 and not board.override_given(0)
    assert through(board, "submit", {"id": "tile-1", "override": "  $30/hr is\nmy policy  "}, tmp_path)["status"] == 200
    assert board.submit_asked(1) and board.override_given(1) == "$30/hr is my policy" and board.override_given(1) == ""

    assert through(board, "submit", {"id": "tile-1", "override": "again"}, tmp_path)["status"] == 200
    board.update(1, status="filling")  # the next Application on the tile: none of the last one's reason
    assert board.override_given(1) == ""


def test_the_submit_command_sends_its_override_and_never_an_empty_one(monkeypatch, capsys):
    """Fault: `apply window submit --override` drops its reason, or sends one with no words in it."""
    from apply import app_window, cli

    sent = []
    monkeypatch.setattr(app_window, "running", lambda: 4242)
    monkeypatch.setattr(app_control, "ask", lambda action, body=None: sent.append((action, body)) or {"status": 200})
    with pytest.raises(SystemExit):
        cli.main(["window", "submit", "tile-2", "--yes", "--override", "Pay from policies.yaml"])
    with pytest.raises(SystemExit) as empty:
        cli.main(["window", "submit", "tile-2", "--yes", "--override", "  "])
    assert empty.value.code == 1 and "needs a reason" in capsys.readouterr().out
    assert sent == [("submit", {"id": "tile-2", "override": "Pay from policies.yaml"})]


def test_a_form_sent_anyway_says_why_in_its_tracker_row():
    """Fault: a form the student sent past the review's hold is kept as any other sent form, so no one can tell."""
    from apply import rehearsal
    from apply.model import Posting
    from apply.tracker import InMemoryTracker

    done = rehearsal.Rehearsed(Posting(id="a1", company="Relay", title="SWE Intern", url=ACME),
                               rehearsal.READY, overridden="Pay from policies.yaml")
    tracker = InMemoryTracker()
    rehearsal._keep_submission(tracker, done, None)
    assert tracker.get("a1").reason == rehearsal.SUBMITTED_BY_LISUL + "; sent past the Pre-submit review's hold: " \
                                       "Pay from policies.yaml"


def test_the_code_command_on_a_form_held_at_its_sign_in_says_the_fill_goes_on(monkeypatch, capsys):
    """Fault: `apply window code` at a sign-in (Oracle's one-time code) says Submit was pressed, when none was."""
    from apply import app_window, cli

    monkeypatch.setattr(app_window, "running", lambda: 4242)
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    states = [{"ask": "sign-in", "coding": True}, {"ask": "", "status": "filling", "coding": False}]

    def ask(action, body=None):
        if action == "code":
            return {"status": 200, "message": "Entering the code."}
        return {"status": 200, "state": {"needs_you": [{"tile": "tile-0", **states.pop(0)}]}}

    monkeypatch.setattr(app_control, "ask", ask)
    with pytest.raises(SystemExit) as done:
        cli.main(["window", "code", "tile-0", "482913", "--yes"])
    said = capsys.readouterr().out
    assert done.value.code == 0 and "signed you in" in said and "Submit was pressed" not in said
