"""WorkIt Auto Apply's window with no port (KAN-858, W5 step 2; D11, D12): the Apply window's routes answered through
pywebview's bridge in this process, its tiles' frames and files, and the sign-in, against a fake WorkIt. No window
and no browser: in CI. tests/test_app_window_page.py runs the page's shim in Chromium."""

import base64
import sys
import types

import pytest
from fake_workit import FakeWorkIt

from apply import app_window, build, dashboard, first_run, workit
from apply.answer_bank import AnswerBank
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


def test_only_a_posting_a_tile_lists_opens_in_the_browser(board):
    """Fault: the page names any link, or a non-web one, and it opens on the computer."""
    opened = []
    bridge = Bridge(board, WorkIt(workit.LIVE), opened.append)
    assert not bridge.open_posting("https://jobs.example/1") and opened == []
    board.update(0, posting_url="https://jobs.example/1")
    board.update(1, posting_url="file:///etc/hosts")
    assert bridge.open_posting("https://jobs.example/1") and opened == ["https://jobs.example/1"]
    assert not bridge.open_posting("file:///etc/hosts") and not bridge.open_posting("https://jobs.example/2")
    assert opened == ["https://jobs.example/1"]


def test_the_shim_comes_before_the_pages_scripts(board):
    """Fault: the page's first fetch goes out before the shim replaces fetch, to an address with no server."""
    page = app_window.page(board)
    assert page.index(SHIM) < page.index("const workers")


def test_the_apps_window_shows_the_student_page_with_the_shim_and_the_token_before_its_scripts(board):
    """Fault: the app's window still shows the developer page, or the student page's first fetch goes out before the
    shim replaces fetch, or without the window's token, so every edit is refused."""
    bridge = Bridge(board, WorkIt(workit.LIVE), start=lambda links, show, jobs: None)
    page = bridge._page()
    assert page == app_window.student_page(board)
    assert "What should we apply to?" in page and "const workers" not in page
    script = page.index("<script type=\"module\"")
    assert page.index(SHIM) < script
    assert page.index(f'window.APPLY_TOKEN = "{board.token}"') < script


def test_a_student_page_built_without_its_charset_meta_still_gets_the_shim_and_token_first(board, tmp_path, monkeypatch):
    """Fault: a build that writes <meta charset> another way leaves the shim and token out, so the page runs the mock."""
    built = tmp_path / "index.html"
    built.write_text('<!doctype html><meta charset=UTF-8><script type="module">go()</script>', encoding="utf-8")
    monkeypatch.setattr(app_window, "STUDENT_PAGE", built)
    page = app_window.student_page(board)
    script = page.index('<script type="module"')
    assert page.index(SHIM) < script
    assert page.index(f'window.APPLY_TOKEN = "{board.token}"') < script


def test_a_window_that_runs_nothing_keeps_the_developer_page(board):
    """Fault: a Developer checkout's window, which has no queue or Start, loses the developer page."""
    assert Bridge(board, WorkIt(workit.LIVE))._page() == app_window.page(board)


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


class Link:
    """apply.sign_in_link, as the bridge uses it: the helper's link, handed once."""

    def __init__(self):
        self.calls: list[str] = []
        self.handed: str | None = None

    def ready(self) -> bool:
        self.calls.append("ready")
        return True

    def clear(self) -> None:
        self.calls.append("clear")
        self.handed = None

    def take(self) -> str | None:
        link, self.handed = self.handed, None
        return link


def test_the_sign_in_pages_link_signs_the_window_in_with_nothing_pasted(board, tmp_path):
    """Fault: the page's Open WorkIt Auto Apply led nowhere from a checkout (macOS hands workit-auto-apply:// only to
    a bundle), so a student who isn't an admin, shown no code, couldn't sign in."""
    with FakeWorkIt() as fake:
        window, link, fronts = Window(), Link(), []
        bridge = Bridge(board, WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain), lambda url: None,
                        Steps(SHOWN), link=link, forward=lambda: fronts.append(1))
        bridge._window = window
        link.handed = "workit-auto-apply://signed-in?code=stale"
        assert bridge.take_link() == {} and link.handed  # no sign-in started: nothing taken

        url = bridge.sign_in()
        assert link.calls == ["ready", "clear"] and link.handed is None  # registered, and the old link forgotten
        assert bridge.take_link() == {} and fronts == []  # the student hasn't pressed Open WorkIt Auto Apply yet
        link.handed = "workit-auto-apply://signed-in?code=" + fake.browser(url)
        assert bridge.take_link() == {"email": "test.person@example.com"}
        assert bridge.signed_in() and window.loaded == [FIRST_RUN]
        assert fronts == [1]  # Fault: the window stayed behind the browser, so the student didn't see it sign in


def test_a_link_for_another_sign_in_signs_nothing_in(board, tmp_path):
    """Fault: a link another program wrote for the helper to hand on signs the window in to its account."""
    with FakeWorkIt() as fake:
        link = Link()
        bridge = Bridge(board, WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain), lambda url: None,
                        Steps(SHOWN), link=link, forward=lambda: None)
        other = fake.browser(workit.sign_in_page(fake.site, workit.pkce()[1]))  # a code for someone else's challenge
        bridge.sign_in()
        link.handed = f"workit-auto-apply://signed-in?code={other}"
        assert "error" in bridge.take_link() and not bridge.signed_in()


def test_the_apps_page_loads_no_web_font(board):
    """Fault: the window asks Google Fonts for its font, a request the privacy page doesn't name."""
    assert "fonts.googleapis.com" in board.page() and "fonts.googleapis.com" not in app_window.page(board)



def test_start_shows_the_runs_window_then_the_queue_again_and_says_why_one_stopped(board):
    """Fault: a second run started over the first, a pick from Find jobs during a run refused or dropped instead of
    joining it, the window left on a finished run, or a run that couldn't start (no engine, W7) said nothing."""
    import threading

    from apply.adapters import SetupError

    shown, go, runs = [], threading.Event(), []

    def start(links, show, jobs):
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
    # One run at a time: a start during it joins it as a link sent in does; this run takes none, so it waits.
    assert bridge.start(["https://jobs.lever.co/acme/2"]) == {"added": 1}
    assert bridge._waiting == ["https://jobs.lever.co/acme/2"]
    for _ in range(100):
        if shown:
            break
        threading.Event().wait(0.02)
    assert runs == [["https://jobs.lever.co/acme/1"]]
    assert window.loaded[-1] == app_window.student_page(shown[0])  # the run's own board
    go.set()
    for _ in range(100):
        if not bridge.status()["running"]:
            break
        threading.Event().wait(0.02)
    assert window.loaded[-1] == app_window.student_page(board)  # the idle board: the queue again
    bridge.start(["https://jobs.lever.co/acme/3"])
    for _ in range(100):
        if bridge.status()["said"]:
            break
        threading.Event().wait(0.02)
    assert bridge.status() == {"running": False, "said": "WorkIt refused this Fill engine."}


def test_stop_applying_through_the_bridge_returns_the_window_to_the_queue(board):
    """KAN-874. Fault: the shim can't reach /stop, or the window stays on a stopped run's board."""
    import threading

    shown, stopped = [], threading.Event()

    def start(links, show, jobs):
        with Dashboard(len(links), OneFrame(), serve=False) as run_board:
            run_board.stopping(stopped.set)  # as rehearsal.rehearse hands it its stop
            show(run_board)
            shown.append(run_board)
            stopped.wait(5)

    window = Window()
    bridge = Bridge(board, WorkIt(workit.LIVE), start=start)
    bridge._window = window
    bridge.start(["https://jobs.lever.co/acme/1"])
    for _ in range(100):
        if shown:
            break
        threading.Event().wait(0.02)
    assert bridge.request("POST", "/stop", {"X-Apply-Token": "guessed"}, "")["status"] == 403
    assert not stopped.is_set()
    assert bridge.request("POST", "/stop", {"X-Apply-Token": shown[0].token}, "")["status"] == 204
    for _ in range(100):
        if not bridge.status()["running"]:
            break
        threading.Event().wait(0.02)
    assert window.loaded[-1] == app_window.student_page(board)  # the idle board: the queue again


def test_the_queue_is_the_students_open_queued_jobs_oldest_first(board, tmp_path):
    """Fault: a closed job in the queue, a job board's page where its employer's form was named, a job without the
    logo sources the website draws it with, or a Start of a queued job that doesn't name its WorkIt job (the Answer
    bank's drafts name their form by it, W11), while a pasted link names one."""
    import threading

    from fake_workit import Reply

    rows = [
        {"job": {"id": "j3", "apply_url": "https://www.linkedin.com/jobs/3", "form_url": "https://jobs.lever.co/acme/3",
                 "company": "Acme", "title": "Intern", "logo_url": "https://www.google.com/s2/favicons?domain=acme.com",
                 "company_domain": "acme.com"}, "open": True},
        {"job": {"id": "j2", "apply_url": "https://boards.greenhouse.io/x/2", "company": "X", "title": "Gone"},
         "open": False},
        {"job": {"id": "j1", "apply_url": "https://boards.greenhouse.io/y/1", "company": "Y", "title": "Analyst"},
         "open": True},
    ]
    started, ran = [], threading.Event()

    def start(links, show, jobs):
        started.append(jobs)
        ran.set()

    with FakeWorkIt() as fake:
        fake.route("GET", f"/applicants/{fake.account['id']}/applications",
                   lambda seen, fake: Reply(200, rows) if seen.path.endswith("stage=queued") else Reply(400))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        bridge = Bridge(board, client, start=start)
        assert bridge.queue() == [
            {"url": "https://boards.greenhouse.io/y/1", "company": "Y", "title": "Analyst", "logo_url": None,
             "company_domain": None},
            {"url": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern",
             "logo_url": "https://www.google.com/s2/favicons?domain=acme.com", "company_domain": "acme.com"},
        ]
        bridge.start(["https://jobs.lever.co/acme/3", "https://jobs.lever.co/pasted/9"])
        assert ran.wait(5)
    assert started == [{"https://jobs.lever.co/acme/3": "j3"}]


def test_find_jobs_lists_the_students_matches_with_their_filters_and_logos(board, tmp_path):
    """Find jobs. Fault: the filters the student picked never reach WorkIt, a filter WorkIt doesn't take is passed
    on, a card lacks its match or facts, or a run started from a match loses its logo."""
    from fake_workit import Reply

    rows = [{"id": "j1", "apply_url": "https://www.linkedin.com/jobs/3", "form_url": "https://jobs.lever.co/acme/3",
             "company": "Acme", "title": "Intern", "company_domain": "acme.com", "logo_url": None, "match": 91,
             "highlights": [{"text": "Uses 4 of your skills", "met": True}], "job_type": "internship",
             "work_style": "hybrid", "location": "New York, NY", "salary_min": 40, "salary_max": 50,
             "salary_period": "hour", "start_term": "Summer 2027", "posted_at": "2026-11-14T00:00:00+00:00",
             "description": "not for the card"}]
    asked = []
    with FakeWorkIt() as fake:
        fake.route("GET", f"/applicants/{fake.account['id']}/auto-apply/matches",
                   lambda seen, fake: (asked.append(seen.path), Reply(200, rows))[1])
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        bridge = Bridge(board, client, start=lambda links, show, jobs: None)
        jobs = bridge.matches({"job_type": ["internship"], "work_style": ["hybrid", "remote"], "q": "",
                               "min_pay": 1})
        assert asked[0].endswith("?size=30&job_type=internship&work_style=hybrid&work_style=remote")
        assert jobs == [{"url": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern",
                         "logo_url": None, "company_domain": "acme.com"}
                        | {key: rows[0].get(key) for key in app_window.MATCH_FACTS}]
        assert bridge._queued["https://jobs.lever.co/acme/3"]["company_domain"] == "acme.com"
        fake.route("GET", f"/applicants/{fake.account['id']}/auto-apply/matches",
                   lambda seen, fake: Reply(404, {"detail": "Your experience bank is empty"}))
        assert "Add your experience" in bridge.matches()["error"]


def test_applied_is_what_the_student_applied_to_on_workit_newest_first(board, tmp_path):
    """Fault (story 36): the Applied page lists only this run's jobs, not what the student applied to before."""
    from fake_workit import Reply

    rows = [
        {"job": {"apply_url": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern",
                 "company_domain": "acme.com"}, "stage": "applied", "applied_at": "2026-11-14T10:00:00Z", "open": False},
        {"job": {"apply_url": "https://www.linkedin.com/jobs/2", "form_url": "https://boards.greenhouse.io/y/1",
                 "company": "Y", "title": "Analyst"}, "stage": "applied", "applied_at": None, "open": True},
    ]
    with FakeWorkIt() as fake:
        fake.route("GET", f"/applicants/{fake.account['id']}/applications",
                   lambda seen, fake: Reply(200, rows) if seen.path.endswith("stage=applied") else Reply(400))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        assert Bridge(board, client).applied() == [
            {"url": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern", "logo_url": None,
             "company_domain": "acme.com", "applied_at": "2026-11-14T10:00:00Z"},
            {"url": "https://boards.greenhouse.io/y/1", "company": "Y", "title": "Analyst", "logo_url": None,
             "company_domain": None, "applied_at": None},
        ]
        fake.route("GET", f"/applicants/{fake.account['id']}/applications", lambda seen, fake: Reply(500))
        assert "error" in Bridge(board, client).applied()


def test_an_applied_jobs_chrome_title_takes_the_title_it_was_queued_with(board, tmp_path):
    """Fault: a title Apply wrote to WorkIt from a sign-in wall's page (model.job_title) shows on the Applied page,
    or a job no queue names keeps it where its listing names the role."""
    from fake_workit import Reply

    amazon = {"apply_url": "https://www.amazon.jobs/en/jobs/10593521/", "company": "Amazon"}
    rows = {"queued": [{"job": amazon | {"id": "j1", "title": "Software Dev Engineer Intern"}, "open": True}],
            "applied": [{"job": amazon | {"title": "Log in or create account | Amazon.jobs"}, "applied_at": None},
                        {"job": {"apply_url": "https://jobs.lever.co/a/1", "company": "A", "title": "Sign in"},
                         "applied_at": None},
                        {"job": {"apply_url": "https://jobs.lever.co/b/2", "company": "B", "title": "Log in"},
                         "applied_at": None}]}
    named = {"https://jobs.lever.co/a/1": {"title": "Data Intern"}}
    with FakeWorkIt() as fake:
        fake.route("GET", f"/applicants/{fake.account['id']}/applications",
                   lambda seen, fake: Reply(200, rows[seen.path.rsplit("=", 1)[-1]]))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        asked = []
        bridge = Bridge(board, client, name=lambda link: asked.append(link) or named.get(link, {}))
        bridge.queue()
        assert [job["title"] for job in bridge.applied()] == ["Software Dev Engineer Intern", "Data Intern", ""]
        bridge.applied()
        assert asked == ["https://jobs.lever.co/a/1", "https://jobs.lever.co/b/2"]  # each link read once


def test_a_runs_window_draws_each_queued_job_with_the_logo_the_queue_gave(board, tmp_path):
    """Fault: a job ticked in the queue lost its logo once its run started (KAN-871)."""
    from fake_workit import Reply

    rows = [{"job": {"id": "j3", "apply_url": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern",
                     "logo_url": "https://www.google.com/s2/favicons?domain=acme.com", "company_domain": "acme.com"},
             "open": True}]
    with FakeWorkIt() as fake:
        fake.route("GET", f"/applicants/{fake.account['id']}/applications", lambda seen, fake: Reply(200, rows))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        bridge = Bridge(board, client, start=lambda links, show, jobs: None)
        bridge.queue()
    with Dashboard(1, OneFrame(), serve=False) as run_board:
        bridge.show_board(run_board)
        run_board.update(0, company="Acme", link="https://jobs.lever.co/acme/3", status="filling")
        tile = run_board.state()["tiles"][0]
    assert (tile["company_domain"], tile["logo_url"]) == ("acme.com", "https://www.google.com/s2/favicons?domain=acme.com")


def test_a_runs_window_names_each_job_waiting_to_start_as_the_queue_did(board, tmp_path):
    """KAN-874. Fault: the jobs waiting to start show as bare links, so the student can't tell which to remove."""
    from fake_workit import Reply

    rows = [{"job": {"id": "j3", "apply_url": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern",
                     "logo_url": "https://www.google.com/s2/favicons?domain=acme.com", "company_domain": "acme.com"},
             "open": True}]
    with FakeWorkIt() as fake:
        fake.route("GET", f"/applicants/{fake.account['id']}/applications", lambda seen, fake: Reply(200, rows))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        bridge = Bridge(board, client, start=lambda links, show, jobs: None)
        bridge.queue()
    with Dashboard(2, OneFrame(), serve=False) as run_board:
        bridge.show_board(run_board)
        run_board.run(waiting=["https://jobs.lever.co/acme/3", "https://jobs.example/pasted"])
        run_board.update(0, company="Acme Corp", link="https://jobs.lever.co/acme/3", status="filling")
        state = run_board.state()
    assert state["run"]["waiting"] == [
        {"link": "https://jobs.lever.co/acme/3", "company": "Acme", "title": "Intern", "company_domain": "acme.com",
         "logo_url": "https://www.google.com/s2/favicons?domain=acme.com"},
        {"link": "https://jobs.example/pasted"},  # a pasted link: no WorkIt job to name it
    ]
    assert state["tiles"][0]["company"] == "Acme Corp"  # the queue's name never covers the form's own


def test_a_run_rehearses_its_links_with_the_students_worker_count_and_closes_its_workers(monkeypatch, tmp_path):
    """Fault: a run that ignores the Worker count (D24: one to four), shows no window of its own, or leaves its plain
    Workers' Chromes running after it, or lets the Mac sleep mid-run."""
    from contextlib import contextmanager, nullcontext
    from types import SimpleNamespace

    from apply import first_run, student, worker_tiles
    from apply.keychain import InMemoryKeychain
    from apply.tracker import InMemoryTracker

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", no_server)
    monkeypatch.setattr(worker_tiles, "frames_for", lambda site, tiles: nullcontext(OneFrame()))
    closed, shown, rehearsed = [], [], []
    monkeypatch.setattr(worker_tiles, "close_workers", closed.append)
    monkeypatch.setattr(student, "AnswersTab", lambda *a, **k: None)
    state = tmp_path / "app.json"
    state.write_text('{"workers": 9}')
    monkeypatch.setattr(first_run, "STATE", state)
    site = SimpleNamespace(show=lambda worker: True, plain=lambda worker: False)
    made = SimpleNamespace(site=site, answer_bank=None, tracker=InMemoryTracker(), keychain=InMemoryKeychain(),
                           everyday=lambda url: None, board=None)
    profile = SimpleNamespace(get=lambda key: None)

    awake = []

    @contextmanager
    def keep_awake():
        awake.append(True)
        yield
        awake.append(False)

    def rehearse(links, adapters, profile, workers):
        rehearsed.append((links, workers, adapters.board is shown[0], awake == [True]))

    runs = student.Runs(profile, AnswerBank(), make=lambda profile, bank: made, rehearse=rehearse, keep_awake=keep_awake)
    runs.run(["https://jobs.lever.co/acme/1", "https://jobs.lever.co/acme/2"], shown.append)
    assert rehearsed == [(["https://jobs.lever.co/acme/1", "https://jobs.lever.co/acme/2"], first_run.MOST_WORKERS, True,
                          True)]
    assert awake == [True, False]  # the Mac stays awake for the run, and no longer (KAN-885)
    assert shown[0].url == NO_PORT and closed == [site]
    # History's link goes to the student's Applications Tracker on WorkIt, opened in the default browser.
    assert shown[0].state()["context"]["tracker_url"] == f"{workit.site().web}/applications"


def test_a_runs_board_takes_the_students_answer_through_the_route(monkeypatch, tmp_path):
    """Fault: a Student run's board has no answer, so /answer is 404 and the page's question card can't save."""
    from contextlib import nullcontext
    from types import SimpleNamespace

    from apply import first_run, student, worker_tiles
    from apply.keychain import InMemoryKeychain
    from apply.tracker import InMemoryTracker

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", no_server)
    monkeypatch.setattr(worker_tiles, "frames_for", lambda site, tiles: nullcontext(OneFrame()))
    monkeypatch.setattr(worker_tiles, "close_workers", lambda site: None)
    monkeypatch.setattr(first_run, "STATE", tmp_path / "app.json")
    saved = []
    tab = SimpleNamespace(save_answered=lambda question, answer: saved.append((question, answer)))
    monkeypatch.setattr(student, "AnswersTab", lambda *a, **k: tab)
    site = SimpleNamespace(show=lambda worker: True, plain=lambda worker: False)
    made = SimpleNamespace(site=site, answer_bank=None, tracker=InMemoryTracker(), keychain=InMemoryKeychain(),
                           everyday=lambda url: None, board=None)
    replies = []

    def rehearse(links, adapters, profile, workers):
        board = adapters.board
        board.update(0, company="Acme", posting_url=links[0], status="filling", missing=["When can you start?"])
        body = '{"id": "live-0", "question": "When can you start?", "answer": "June 2027"}'
        replies.append(Bridge(board, WorkIt(workit.LIVE)).request("POST", "/answer", {"X-Apply-Token": board.token}, body))

    student.Runs(SimpleNamespace(get=lambda key: None), AnswerBank(), make=lambda profile, bank: made, rehearse=rehearse) \
        .run(["https://jobs.lever.co/acme/1"], lambda board: None)
    assert replies[0]["status"] == 200, replies[0]
    assert saved == [("When can you start?", "June 2027")]


def test_closing_asks_first_only_while_forms_wait_for_the_student_naming_how_many(monkeypatch):
    """Fault: quitting closes held forms with no question, or asks with nothing held, or a submitted form counts."""
    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", no_server)
    window = type("Closing", (), {"confirm_close": False, "localization": {"global.quitConfirmation": "Quit?"}})()
    with Dashboard(3, OneFrame(), serve=False) as run_board:
        bridge = Bridge(run_board, WorkIt(workit.LIVE))
        app_window.guard_close(window, bridge)
        assert window.confirm_close is False
        run_board.update(0, status="ready", again=True)
        app_window.guard_close(window, bridge)
        assert window.confirm_close is True
        assert window.localization["global.quitConfirmation"] == app_window.close_words(1) == (
            "Quit WorkIt Auto Apply? Your filled form waiting for you will close. Nothing gets submitted.")
        run_board.update(1, status="missing fact", again=True)
        run_board.update(2, status="submitted", again=True)  # sent: it waits for no one
        app_window.guard_close(window, bridge)
        assert "Your 2 filled forms waiting" in window.localization["global.quitConfirmation"]
        run_board.update(0, again=False)
        run_board.update(1, again=False)  # let go: nothing held, nothing asked
        app_window.guard_close(window, bridge)
        assert window.confirm_close is False


def test_remove_all_my_data_only_in_the_student_build_and_never_during_a_run(board, tmp_path, monkeypatch):
    """Fault: a Developer checkout's own data folder deleted, data removed under a running run, or the login left in
    the keychain after the folder went."""
    from types import SimpleNamespace

    from apply import build, first_run

    home = tmp_path / "WorkIt Auto Apply"
    (home / "profiles" / "plain-seed").mkdir(parents=True)
    forgot = []
    client = SimpleNamespace(sign_out=lambda: forgot.append(True), logged_in=lambda: True)
    window = Window()
    window.destroy = lambda: None
    bridge = Bridge(board, client, remove=lambda forget: first_run.remove_all_data(forget, home))
    bridge._window = window

    assert bridge.remove_data()["said"].startswith("Only WorkIt Auto Apply removes its data")
    assert home.exists() and forgot == []
    monkeypatch.setattr(build, "STUDENT", True)
    bridge._running.set()
    assert "error" in bridge.remove_data() and home.exists()
    bridge._running.clear()
    assert bridge.remove_data()["said"].startswith("Removed")
    assert not home.exists() and forgot == [True]


def test_report_a_problem_sends_only_the_report_the_window_showed(board, tmp_path):
    """Fault: a report sent with no Review Report, with words other than those shown, or twice from one press."""
    from fake_workit import Reply

    with FakeWorkIt() as fake:
        fake.route("POST", "/apply-app/reports", lambda seen, fake: Reply(200, {"id": "report-1"}))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        bridge = Bridge(board, client)
        assert "error" in bridge.send_report()
        assert "error" in bridge.review_report("app", "  ")
        assert bridge.review_report("app", "The window froze.", contact_ok=True) == {
            "parts": ["Your words, and WorkIt may email you about them"]}
        assert bridge.send_report()["said"].startswith("Sent.")
        assert "error" in bridge.send_report()  # one press, one report
    [sent] = [seen.body for seen in fake.requests if seen.path == "/apply-app/reports"]
    assert sent == {"category": "app", "note": "The window froze.", "contact_ok": True}


def test_report_this_application_finds_the_record_of_a_form_the_run_held(board, monkeypatch, tmp_path):
    """Fault: a form held in this run, which a rehearsal keeps no Tracker row for, reported without its record, an
    Application the computer has nothing of reported as if it had, or another form's Send Report sending it."""
    from apply import student

    monkeypatch.setattr(student, "RECORDS", tmp_path / "rehearsals")
    for day in ("2026-11-14", "2026-11-15"):
        record = tmp_path / "rehearsals" / day / "acme-gh-1"
        record.mkdir(parents=True)
        (record / "answers.json").write_text(f'{{"day": "{day}"}}')
    board.update(0, company="Acme", role="Intern", job_system="greenhouse", application_id="gh-1", status="ready",
                 posting_url="https://boards.greenhouse.io/acme/jobs/1")
    bridge = Bridge(board, WorkIt(workit.LIVE))
    shown = bridge.review_report("form", "It picked the wrong school.", application_id="gh-1")
    assert shown["parts"][1:] == ["Which application: Acme, Intern", "answers.json (1 KB)"]
    assert bridge._report["outcome"] == "held" and bridge._report["files"] == {"answers.json": '{"day": "2026-11-15"}'}
    # Send Report from Settings' form or another Application's card: not the report this card reviewed.
    assert "error" in bridge.send_report() and "error" in bridge.send_report("gh-2")
    assert "error" in bridge.review_report("form", "It picked the wrong school.", application_id="gh-2")


@pytest.mark.parametrize("quit_by", ["SIGTERM", "SIGINT", "SIGHUP"])
def test_kill_closes_the_window_instead_of_raising_inside_cocoa(quit_by):
    """Fault: `kill <pid>` raised KeyboardInterrupt inside a Cocoa callback, and macOS showed "python quit
    unexpectedly"; Ctrl-C did the same, and a closed terminal ended the app at once: no `finally` ran, and its
    Workers' Chromes stayed open."""
    import os
    import signal

    number = getattr(signal, quit_by)

    class Closable:
        closed = False

        def destroy(self):
            self.closed = True

    import time

    window, before = Closable(), {n: signal.getsignal(n) for n in app_window.QUITS}
    try:
        app_window.closing(window)
        os.kill(os.getpid(), number)
        deadline = time.monotonic() + 2
        while not window.closed and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        signal.set_wakeup_fd(-1)
        for n, handler in before.items():
            signal.signal(n, handler)

    assert window.closed


def test_app_pages_stay_light():
    """The student page is light only, so sign-in, first run and Settings never turn dark beside it."""
    for page in (app_window.SIGN_IN, app_window.FIRST_RUN, app_window.SETTINGS):
        assert "prefers-color-scheme: dark" not in page
        assert '<meta name="color-scheme" content="light">' in page
    assert "prefers-color-scheme: dark" in app_window.STYLE  # the Developer dashboard keeps its dark scheme


def test_links_sent_in_start_a_run_once_signed_in_then_join_it_or_wait(board, tmp_path):
    """`apply app <link>...`. Fault: links sent while signed out are lost, a link is taken twice, a non-link starts a
    run, or a link sent during a run that takes none is dropped instead of starting the next run."""
    import threading

    inbox, runs, go, took = tmp_path / "inbox", [], threading.Event(), []

    def start(links, show, jobs):
        runs.append(links)
        with Dashboard(len(links), OneFrame(), serve=False) as run_board:
            if len(runs) == 1:
                run_board.taking(lambda url, worker: took.append(url) or {"tile": 1, "worker": worker})
            show(run_board)
            go.wait(5)

    def wait(done):
        for _ in range(100):
            if done():
                return
            threading.Event().wait(0.02)

    steps = Steps(SHOWN)
    bridge = Bridge(board, WorkIt(workit.LIVE), first_run=steps, start=start)
    bridge.signed_in = lambda: True
    app_window.send_links(["https://jobs.lever.co/acme/1", "not a link", "https://jobs.lever.co/acme/1"], inbox)
    bridge._take_inbox(inbox)
    assert not runs and list(inbox.glob("*.json"))  # first run isn't done: they wait in the inbox
    steps.now = READY
    bridge._take_inbox(inbox)
    wait(lambda: runs)
    assert runs == [["https://jobs.lever.co/acme/1"]] and not list(inbox.glob("*"))
    app_window.send_links(["https://jobs.lever.co/acme/2"], inbox)
    bridge._take_inbox(inbox)
    assert took == ["https://jobs.lever.co/acme/2"]  # into the run going, beside its forms
    go.set()
    wait(lambda: not bridge.status()["running"])
    go.clear()
    bridge._start = lambda links, show, jobs: (runs.append(links), go.wait(5))
    bridge._running.set()  # a run whose board takes no links
    app_window.send_links(["https://jobs.lever.co/acme/3"], inbox)
    bridge._take_inbox(inbox)
    assert len(runs) == 1 and bridge._waiting == ["https://jobs.lever.co/acme/3"]
    bridge._running.clear()
    bridge._take_inbox(inbox)  # the next run takes it
    wait(lambda: len(runs) == 2)
    assert runs[-1] == ["https://jobs.lever.co/acme/3"]
    go.set()


def test_links_given_on_lines_of_one_argument_are_each_a_link():
    # zsh passes `apply app $links` as one argument, its links on lines of their own (live, 2026-11-25).
    one = "https://jobs.lever.co/acme/1\nhttps://jobs.lever.co/acme/2\n"
    assert app_window.links_given([one, "https://jobs.lever.co/acme/3"]) == (
        ["https://jobs.lever.co/acme/1", "https://jobs.lever.co/acme/2", "https://jobs.lever.co/acme/3"], [])
    assert app_window.links_given(["acme.com/jobs/1"]) == ([], ["acme.com/jobs/1"])


def test_running_names_only_a_live_windows_pid(tmp_path):
    import os

    note = tmp_path / "app.pid"
    assert app_window.running(note) is None
    note.write_text(str(os.getpid()))
    assert app_window.running(note) == os.getpid()
    note.write_text("2147483646")
    assert app_window.running(note) is None


def test_the_dock_badge_never_breaks_a_run_off_a_mac_or_without_pyobjc(monkeypatch):
    monkeypatch.setattr(app_window.sys, "platform", "linux")
    app_window.badge(3)  # no Dock: nothing happens
    monkeypatch.setattr(app_window.sys, "platform", "darwin")
    monkeypatch.setitem(sys.modules, "AppKit", None)  # pyobjc missing: importing it raises ImportError
    app_window.badge(3)


def test_the_dock_badge_shows_the_count_and_nothing_for_zero(monkeypatch):
    labels = []

    class DockTile:
        def setBadgeLabel_(self, label):
            labels.append(label)

    appkit = types.SimpleNamespace(NSApplication=types.SimpleNamespace(sharedApplication=lambda: types.SimpleNamespace(dockTile=DockTile)))
    helper = types.SimpleNamespace(callAfter=lambda call: call())
    monkeypatch.setattr(app_window.sys, "platform", "darwin")
    monkeypatch.setitem(sys.modules, "AppKit", appkit)
    monkeypatch.setitem(sys.modules, "PyObjCTools", types.SimpleNamespace(AppHelper=helper))
    monkeypatch.setitem(sys.modules, "PyObjCTools.AppHelper", helper)
    app_window.badge(3)
    app_window.badge(0)
    assert labels == ["3", ""]


def test_a_checkouts_window_shows_workits_name_and_logo_and_the_built_app_keeps_its_bundles(monkeypatch, tmp_path):
    # Fault: `apply app` from a checkout shows Python's name and a blank page in the Dock, or the Student build's
    # bundle icon is replaced.
    icons, info = [], {"CFBundleName": "Python"}
    image = object()
    app = types.SimpleNamespace(setApplicationIconImage_=icons.append)
    appkit = types.SimpleNamespace(
        NSApplication=types.SimpleNamespace(sharedApplication=lambda: app),
        NSImage=types.SimpleNamespace(alloc=lambda: types.SimpleNamespace(
            initWithContentsOfFile_=lambda path: image if path == str(app_window.ICON) else None)))
    foundation = types.SimpleNamespace(NSBundle=types.SimpleNamespace(
        mainBundle=lambda: types.SimpleNamespace(infoDictionary=lambda: info)))
    monkeypatch.setattr(app_window.sys, "platform", "darwin")
    monkeypatch.setitem(sys.modules, "AppKit", appkit)
    monkeypatch.setitem(sys.modules, "Foundation", foundation)
    assert app_window.ICON.is_file()
    assert app_window.look_like_the_app() is True
    assert icons == [image] and info["CFBundleName"] == app_window.TITLE
    assert app_window.look_like_the_app(tmp_path / "app-icon.png") is False  # the built app: no logo beside its code
    monkeypatch.setattr(build, "STUDENT", True)
    assert app_window.look_like_the_app() is False
    assert icons == [image]


def test_settings_shows_the_claude_switch_only_to_a_max_plan_developer_window(monkeypatch):
    from apply import claude_cli, student

    monkeypatch.delenv(student.MAX_PLAN, raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    with Dashboard(1, OneFrame(), serve=False) as board:
        bridge = Bridge(board, WorkIt(workit.LIVE))
        assert "claude" not in bridge.settings_state()  # WorkIt's Model route answers: no Claude to choose
        monkeypatch.setenv(student.MAX_PLAN, "1")
        monkeypatch.setattr(claude_cli, "dropped", None)
        assert bridge.settings_state()["claude"] == {"best": True, "login": "your claude login", "dropped": None}
        assert bridge.set_best_model(False) == {"best": False}
        assert bridge.settings_state()["claude"]["best"] is False


def test_settings_shows_and_changes_the_safety_level():
    """Fault: Settings showing another level than the one read, or a level no policy knows kept."""
    from apply import profile

    with Dashboard(1, OneFrame(), serve=False) as board:
        bridge = Bridge(board, WorkIt(workit.LIVE))
        assert bridge.settings_state()["safety"] == "careful"
        assert bridge.set_safety_level("full_auto") == {"safety": "full_auto"}
        assert bridge.settings_state()["safety"] == "full_auto"
        assert profile.load_policies()["auto_submit"] is True
        assert "error" in bridge.set_safety_level("yolo") and bridge.settings_state()["safety"] == "full_auto"
    assert all(f'data-level="{level}"' in app_window.FIRST_RUN and f'<option value="{level}">' in app_window.SETTINGS
               for level in ("careful", "balanced", "full_auto"))


def test_settings_offers_automatic_workers_until_the_student_picks_a_count(tmp_path, monkeypatch):
    """Fault: Settings showing a count the student never picked as their choice, or its Automatic not going back
    to the count from the computer's memory."""
    monkeypatch.setattr(first_run, "STATE", tmp_path / "app.json")
    monkeypatch.setattr(first_run, "memory", lambda: 8 * first_run.GB)
    with Dashboard(1, OneFrame(), serve=False) as board:
        bridge = Bridge(board, WorkIt(workit.LIVE))
        assert bridge.settings_state() | {"notices": None, "safety": None} == {
            "workers": 0, "automatic": 2, "notices": None, "safety": None}
        assert bridge.set_workers(3) == {"workers": 3} and bridge.settings_state()["workers"] == 3
        assert bridge.set_workers(0) == {"workers": 2} and bridge.settings_state()["workers"] == 0


def test_a_reply_to_a_page_that_was_replaced_is_dropped_and_any_other_error_still_raises():
    """Fault: a js_api method's return that comes back after load_html replaced its page (a long `matches` wait,
    then Go on) raises JavascriptException in pywebview's reply thread, and its traceback floods the log."""
    class JavascriptException(Exception):
        pass

    class Window:
        def evaluate_js(self, script):
            if "missing" in script or "broken" in script:
                raise JavascriptException({"name": "TypeError" if "missing" in script else "ReferenceError"})
            return "ran"

    window = Window()
    app_window.late_replies(window)
    assert window.evaluate_js(app_window.REPLY + 'matches"]["missing"]({value: "[]"})') is None
    assert window.evaluate_js(app_window.REPLY + 'matches"]["7"]({value: "[]"})') == "ran"
    with pytest.raises(JavascriptException):
        window.evaluate_js("broken()")
    with pytest.raises(JavascriptException):
        window.evaluate_js("missing()")  # not a reply: its error is the page's own


def test_the_apps_output_goes_out_a_line_at_a_time_even_to_a_file(tmp_path):
    """Fault: under nohup stdout is a file, so the run's lines sat in a block buffer and its log couldn't be followed."""
    import io

    from apply import masked

    with open(tmp_path / "app.log", "w") as log:
        app_window.line_by_line(masked._Scrubbing(log))
        assert log.line_buffering
        log.write("Took a link\n")
        assert (tmp_path / "app.log").read_text() == "Took a link\n"
    app_window.line_by_line(io.StringIO())  # a stream that can't change stays as it is


def test_links_sent_in_are_taken_once_per_posting(tmp_path):
    """Fault: a Greenhouse job sent in by its board link, then by its embed link (one token), was queued twice."""
    inbox = tmp_path / "inbox"
    app_window.send_links(["https://job-boards.greenhouse.io/acme/jobs/6270727004"], inbox)
    app_window.send_links(["https://job-boards.greenhouse.io/embed/job_app?for=acme&token=6270727004",
                           "https://jobs.lever.co/acme/2"], inbox)
    assert app_window.take_links(inbox) == ["https://job-boards.greenhouse.io/acme/jobs/6270727004",
                                            "https://jobs.lever.co/acme/2"]


def test_a_second_kill_while_it_closes_ends_the_app_after_its_chromes_stopped(monkeypatch):
    """Fault: every quit signal stayed a no-op once the first closed the window: a stuck close left only `kill -9`,
    which skips the exit sweep, and the Workers' Chromes stayed open."""
    import os
    import signal
    import threading
    import time

    ended, swept = threading.Event(), []
    monkeypatch.setattr(app_window.atexit, "_run_exitfuncs", lambda: swept.append(True))
    monkeypatch.setattr(app_window.os, "_exit", lambda code: (swept.append(code), ended.set()))

    class Stuck:
        def destroy(self):
            pass  # the window never goes

    before = {n: signal.getsignal(n) for n in app_window.QUITS}
    try:
        app_window.closing(Stuck())
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(0.2)
        assert not ended.is_set()  # one: the window closes, the app goes on with its `finally`s
        os.kill(os.getpid(), signal.SIGINT)
        ended.wait(2)
    finally:
        signal.set_wakeup_fd(-1)
        for n, handler in before.items():
            signal.signal(n, handler)

    assert swept == [True, 128 + signal.SIGINT]


def test_a_window_that_closes_while_a_quit_reads_the_window_list_leaves_the_read_whole():
    """Fault: pywebview's Cocoa quit reads each window's close question from its live dict of windows, and a window
    our close thread destroys mid-question leaves it, so the app died with `dictionary changed size during
    iteration` (run7, 2026-11-26)."""
    view = types.SimpleNamespace(instances={"main": "window", "other": "window"})
    app_window.steady_windows("darwin", view)
    app_window.steady_windows("darwin", view)  # once only: run() may be called again
    asked = []
    for uid in view.instances:  # applicationShouldTerminate_ reads each, a close dialog up
        asked.append(uid)
        view.instances.pop("other", None)  # windowWillClose_ of the window our close thread destroyed
    for window in view.instances.values():
        view.instances.pop("main")
    assert asked == ["main", "other"] and view.instances == {}  # pywebview stops the app on `instances == {}`
    assert type(view.instances) is app_window.SteadyWindows
