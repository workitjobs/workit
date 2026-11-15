"""WorkIt Auto Apply's window with no port (KAN-858, W5 step 2; D11, D12): the Apply window's routes answered through
pywebview's bridge in this process, its tiles' frames and files, and the sign-in, against a fake WorkIt. No window
and no browser: in CI. tests/test_app_window_page.py runs the page's shim in Chromium."""

import base64

import pytest
from fake_workit import FakeWorkIt

from apply import app_window, dashboard, workit
from apply.app_window import FIRST_RUN, SHIM, Bridge
from apply.dashboard import NO_PORT, Dashboard
from apply.first_run import READY, SHOWN
from apply.workit import WorkIt

JPEG = b"\xff\xd8\xff\xe0 a frame"


class OneFrame:
    """Worker 0 has shown frame number 3."""

    def frame(self, worker, tab=None):
        return JPEG

    def wait(self, worker, after, timeout, tab=None):
        return (JPEG, 3) if after < 3 else (None, after)

    def input(self, worker, event, tab=None):
        return None

    def chooser(self, worker, tab=None):
        return None

    def field_error(self, worker):
        return ""


class Window:
    """pywebview's window, as the bridge uses it."""

    def __init__(self):
        self.loaded: list[str] = []

    def load_html(self, html: str) -> None:
        self.loaded.append(html)


class Steps:
    """First run (apply.first_run.FirstRun), at the step a test sets."""

    def __init__(self, now: str):
        self.now = now

    def step(self) -> str:
        return self.now

    def state(self) -> dict:
        return {"step": self.now, "lines": [], "running": False, "waiting": False, "failed": ""}


def no_server(*_, **__):
    raise AssertionError("the window opened a port")


@pytest.fixture
def board(monkeypatch):
    # Fault: Dashboard(serve=False) still binds 127.0.0.1, so a program on the computer could reach the routes.
    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", no_server)
    with Dashboard(1, OneFrame(), serve=False) as made:
        yield made


def test_the_window_opens_no_port(board):
    assert board.url == NO_PORT


def test_a_request_through_the_bridge_meets_the_servers_own_checks(board):
    """Fault: the bridge drops the page's headers or body, or answers past the routes' token checks."""
    bridge = Bridge(board, WorkIt(workit.LIVE))
    state = bridge.request("GET", "/state?front=1")
    assert state["status"] == 200 and "tiles" in state["body"]
    assert bridge.request("POST", "/start", {}, "not the token")["status"] == 403
    assert bridge.request("POST", "/start", {}, board.token)["status"] == 204
    assert bridge.request("GET", "/ask/1")["status"] == 403  # no X-Apply-Token header
    assert bridge.request("GET", "/ask/1", {"x-apply-token": board.token})["status"] == 404  # past the check


def test_the_frame_streams_are_never_served_through_the_bridge(board):
    """Fault: /frames through the bridge, an answer that never ends, which held the page's request forever."""
    assert Bridge(board, WorkIt(workit.LIVE)).request("GET", "/frames")["status"] == 404


def test_the_tiles_get_only_frames_newer_than_they_have(board, monkeypatch):
    """Fault: a frame sent again, or none sent at all."""
    monkeypatch.setattr(app_window, "FRAMES_WAIT", 0.05)
    bridge = Bridge(board, WorkIt(workit.LIVE))
    [frame] = bridge.frames({})
    assert (frame["tile"], frame["number"], base64.b64decode(frame["jpeg"])) == (0, 3, JPEG)
    assert bridge.frames({"0": 3}) == []


def test_only_a_file_a_tile_lists_opens(board, tmp_path):
    """Fault: any path the page names opens on the computer."""
    sent = tmp_path / "resume.pdf"
    sent.write_bytes(b"%PDF-1.4")
    opened = []
    bridge = Bridge(board, WorkIt(workit.LIVE), opened.append)
    assert not bridge.open("/file/0/0") and opened == []
    board.update(0, files=[{"label": "Resume", "path": str(sent)}])
    assert bridge.open("/file/0/0") and opened == [sent.as_uri()]
    assert not bridge.open("/file/0/1")


def test_the_shim_comes_before_the_pages_scripts(board):
    """Fault: the page's first fetch goes out before the shim replaces fetch, to an address with no server."""
    page = app_window.page(board)
    assert page.index(SHIM) < page.index("const workers")


def test_sign_in_opens_workits_page_and_its_code_signs_the_window_in(board, tmp_path):
    """Fault: the window keeps no verifier, shows the Apply window before first run is done, or never after it."""
    with FakeWorkIt() as fake:
        opened, window, steps = [], Window(), Steps(SHOWN)
        bridge = Bridge(board, WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain), opened.append, steps)
        bridge._window = window
        assert "error" in bridge.trade("a code")  # no sign-in started

        url = bridge.sign_in()
        assert opened == [url] and url.startswith(f"{fake.url}/app-sign-in?challenge=")
        assert "error" in bridge.trade("not the page's code")
        assert "error" in bridge.trade(fake.browser(url))  # a refused code spends the sign-in: press it again

        url = bridge.sign_in()
        assert bridge.trade(fake.browser(url)) == {"email": "test.person@example.com"}
        assert bridge.signed_in() and window.loaded == [FIRST_RUN]
        bridge.go_on()
        assert window.loaded == [FIRST_RUN]  # a step is left: still first run
        steps.now = READY
        bridge.go_on()
        assert window.loaded == [FIRST_RUN, app_window.page(board)]


def test_the_apps_page_loads_no_web_font(board):
    """Fault: the window asks Google Fonts for its font, a request the privacy page doesn't name."""
    assert "fonts.googleapis.com" in board.page() and "fonts.googleapis.com" not in app_window.page(board)



def test_start_shows_the_runs_window_then_the_queue_again_and_says_why_one_stopped(board):
    """Fault: a second run started over the first, the window left on a finished run, or a run that couldn't
    start (no engine, W7) said nothing."""
    import threading

    from apply.adapters import SetupError

    shown, go, runs = [], threading.Event(), []

    def start(links, show):
        runs.append(links)
        with Dashboard(len(links), OneFrame(), serve=False) as run_board:
            show(run_board)
            shown.append(run_board)
            go.wait(5)
        if len(runs) == 2:
            raise SetupError("WorkIt refused this Fill engine.")

    window = Window()
    bridge = Bridge(board, WorkIt(workit.LIVE), start=start)
    bridge._window = window
    assert "error" in bridge.start([])
    assert bridge.start(["https://jobs.lever.co/acme/1"]) == {"started": 1}
    assert "error" in bridge.start(["https://jobs.lever.co/acme/2"])  # one run at a time
    for _ in range(100):
        if shown:
            break
        threading.Event().wait(0.02)
    assert window.loaded[-1] == app_window.page(shown[0], usage=True)  # the run's tiles, with no queue
    go.set()
    for _ in range(100):
        if not bridge.status()["running"]:
            break
        threading.Event().wait(0.02)
    assert window.loaded[-1] == app_window.page(board, panel=True, usage=True)  # the queue again
    bridge.start(["https://jobs.lever.co/acme/3"])
    for _ in range(100):
        if bridge.status()["said"]:
            break
        threading.Event().wait(0.02)
    assert bridge.status() == {"running": False, "said": "WorkIt refused this Fill engine."}


def test_the_queue_is_the_students_open_queued_jobs_oldest_first(board, tmp_path):
    """Fault: a closed job in the queue, or a job board's page where its employer's form was named."""
    from fake_workit import Reply

    rows = [
        {"job": {"apply_url": "https://www.linkedin.com/jobs/3", "form_url": "https://jobs.lever.co/acme/3",
                 "company": "Acme", "title": "Intern"}, "open": True},
        {"job": {"apply_url": "https://boards.greenhouse.io/x/2", "company": "X", "title": "Gone"}, "open": False},
        {"job": {"apply_url": "https://boards.greenhouse.io/y/1", "company": "Y", "title": "Analyst"}, "open": True},
    ]
    with FakeWorkIt() as fake:
        fake.route("GET", f"/applicants/{fake.account['id']}/applications",
                   lambda seen, fake: Reply(200, rows) if seen.path.endswith("stage=queued") else Reply(400))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        assert Bridge(board, client).queue() == [
            {"url": "https://boards.greenhouse.io/y/1", "company": "Y", "title": "Analyst"},
            {"url": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern"},
        ]


def test_a_run_rehearses_its_links_with_the_students_worker_count_and_closes_its_workers(monkeypatch, tmp_path):
    """Fault: a run that ignores the Worker count (D24: one to three), shows no window of its own, or leaves its plain
    Workers' Chromes running after it."""
    from contextlib import nullcontext
    from types import SimpleNamespace

    from apply import student, worker_tiles
    from apply.keychain import InMemoryKeychain
    from apply.tracker import InMemoryTracker

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", no_server)
    monkeypatch.setattr(worker_tiles, "frames_for", lambda site, tiles: nullcontext(OneFrame()))
    closed, shown, rehearsed = [], [], []
    monkeypatch.setattr(worker_tiles, "close_workers", closed.append)
    monkeypatch.setattr(student, "AnswersTab", lambda *a, **k: None)
    state = tmp_path / "app.json"
    state.write_text('{"workers": 9}')
    monkeypatch.setattr(student, "STATE", state)
    site = SimpleNamespace(show=lambda worker: True, plain=lambda worker: False)
    made = SimpleNamespace(site=site, answer_bank=None, tracker=InMemoryTracker(), keychain=InMemoryKeychain(),
                           everyday=lambda url: None, board=None)
    profile = SimpleNamespace(get=lambda key: None)

    def rehearse(links, adapters, profile, workers):
        rehearsed.append((links, workers, adapters.board is shown[0]))

    runs = student.Runs(profile, make=lambda profile: made, rehearse=rehearse)
    runs.run(["https://jobs.lever.co/acme/1", "https://jobs.lever.co/acme/2"], shown.append)
    assert rehearsed == [(["https://jobs.lever.co/acme/1", "https://jobs.lever.co/acme/2"], student.MOST_WORKERS, True)]
    assert shown[0].url == NO_PORT and closed == [site]
