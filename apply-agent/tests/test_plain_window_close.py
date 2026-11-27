"""Each form's plain Worker Chrome stops once the form is done with (sent, let go, closed, skipped, already applied,
or the rehearsal moving on), and no Chrome stays that no form holds: a run of 17 links left 17 Chromes on blank tabs
(live, 2026-11-26). Played Workers and a played rehearsal: needs no browser, in CI."""

import threading
import time
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest
from fakes import FakeClaude, FakeClock, FakeMailbox, RecordingBoard, ScriptedUsage
from test_run_answers import profile_with

from apply import fill_engine, rehearsal
from apply.adapters import Adapters
from apply.feed import SimplifyFeed
from apply.model import Posting
from apply.plain.site import PlainSite
from apply.profile import ApplicantProfile
from apply.tracker import InMemoryTracker

URL = "https://jobs.example.com/apply"


class _Connection:
    """A plain Worker's port, played: its tabs."""

    def __init__(self):
        self.closed, self.tabs, self.worker = threading.Event(), [1], 0

    def on(self, event: str, handler) -> None:
        pass

    def call(self, name: str, **given):
        if name == "tabs.query":
            return [{"tab": t, "url": "about:blank"} for t in self.tabs]
        if name == "tabs.create":
            self.tabs.append(max(self.tabs, default=0) + 1)
            return {"tab": self.tabs[-1]}
        if name == "tabs.get":
            return {"url": "about:blank", "title": ""}
        if name == "tabs.close":
            self.tabs = [t for t in self.tabs if t != given["tab"]]
        return None


class _Workers:
    """Plain Workers, played: each launch is a running Chrome, each stop is said."""

    def __init__(self):
        self.profiles, self.running, self.stopped = None, {}, []
        self.bridge = SimpleNamespace(connection=lambda k: None)

    def launch(self, worker: int):
        self.running[worker] = SimpleNamespace(connection=_Connection())
        return self.running[worker]

    def refresh(self, worker: int, others: bool = False) -> list[str]:
        return []

    def stop(self, worker: int) -> None:
        if self.running.pop(worker, None):
            self.stopped.append(worker)

    def position(self, worker: int) -> tuple[int, int]:
        return 0, 0


@pytest.fixture
def site():
    return PlainSite(_Workers(), fetcher=object())


def test_a_workers_chrome_stops_once_its_form_is_done_with(site):
    """Fault: release() leaves the Chrome up on its blank tab, a window for each ended form till the run ends."""
    with site.open(URL, worker=0):
        pass
    assert site.release(0) == [0]
    assert site.workers.stopped == [0] and not site.workers.running


def test_a_chrome_another_form_still_holds_stays_till_that_form_is_done_too(site):
    """Fault: release() stops a Worker whose other form (`--into`) is still held for the student."""
    with site.open(URL, worker=0):
        with site.open(URL + "?b", worker=0):
            pass
        assert site.release(0) == []  # the first form is still open in it
        assert 0 in site.workers.running
    assert site.release(0) == [0]


def test_any_chrome_no_form_holds_stops_with_the_next_form_done(site):
    """Fault: release() looks only at its own Worker, so a Chrome another path left up idle stays for good."""
    site.workers.launch(1)  # up, no form in it
    with site.open(URL, worker=0):
        assert site.release(2) == [1]  # Worker 0's form is open: only the idle one goes
    assert site.workers.running.keys() == {0}


class _Page:
    def __init__(self):
        self.closed = False

    def is_closed(self) -> bool:
        return self.closed


class _Site:
    """A job site, played: each page it opens stays open till its link's site closes it; each release is heard
    with whether that page was closed by then."""

    def __init__(self):
        self.pages, self.released = [], []

    @contextmanager
    def open(self, url: str, worker: int = 0):
        page = _Page()
        self.pages.append(page)
        try:
            yield page
        finally:
            page.closed = True

    def release(self, worker: int) -> None:
        self.released.append((worker, all(p.closed for p in self.pages)))


def _rehearse(monkeypatch, tmp_path, outcome: str, keep_open: bool, site: _Site, board=None) -> None:
    """One link rehearsed whose fill opens a page on `site` and ends with `outcome`."""
    monkeypatch.setattr(fill_engine, "ready", lambda: None)
    monkeypatch.setattr(rehearsal, "guard", lambda page: None)

    def fill(url, kept, *rest, **more):
        with kept.open(url):
            pass
        return rehearsal.Rehearsed(Posting("", "Example", "", url), outcome, "")
    monkeypatch.setattr(rehearsal, "_rehearse", fill)
    adapters = Adapters(feed=SimplifyFeed(lambda: b"[]"), site=site, claude=FakeClaude(), tracker=InMemoryTracker(),
                        mailbox=FakeMailbox(), usage=ScriptedUsage(), clock=FakeClock(datetime(2026, 11, 26, 9)),
                        board=board or RecordingBoard())
    rehearsal.rehearse([URL], adapters, ApplicantProfile.load(profile_with(tmp_path)), 1, keep_open=keep_open,
                       out=lambda line: None, on_done=getattr(board, "on_done", lambda: None))


def test_a_rehearsals_form_lets_its_chrome_go_once_its_page_closed(monkeypatch, tmp_path):
    """Fault: the link's end closes its page but never releases its Worker: its Chrome stays on about:blank."""
    site = _Site()
    _rehearse(monkeypatch, tmp_path, rehearsal.FAILED, keep_open=False, site=site)
    assert site.released == [(0, True)]


def test_an_already_applied_link_lets_its_chrome_go_before_the_run_ends(monkeypatch, tmp_path):
    """Fault: an already-applied link's page (opened to find its form) and Chrome stay till the whole run ends."""
    site, seen = _Site(), []

    class Board(RecordingBoard):
        def stopping(self, stop) -> None:
            self.stop = stop

        def on_done(self) -> None:  # every link ended: what was released by then, then Stop applying
            deadline = time.monotonic() + 5
            while not site.released and time.monotonic() < deadline:
                time.sleep(0.05)
            seen.append(list(site.released))
            self.stop()

    _rehearse(monkeypatch, tmp_path, rehearsal.ALREADY, keep_open=True, site=site, board=Board())
    assert seen[0] == [(0, True)]


def test_a_link_sent_in_still_goes_to_a_worker_whose_chrome_stopped(monkeypatch, tmp_path):
    """Fault: once a Worker's Chrome stopped with its form, the window's links sent in (`apply app <link>`) are refused
    as for a CDP Worker, and wait for the next run."""
    site, took = _Site(), []
    site.running, site.plain = (lambda worker: False), (lambda worker: True)

    class Board(RecordingBoard):
        def taking(self, into) -> None:
            self.into = into

        def stopping(self, stop) -> None:
            self.stop = stop

        def on_done(self) -> None:
            took.append(self.into("https://jobs.example.com/other/apply", 0))
            self.stop()

    _rehearse(monkeypatch, tmp_path, rehearsal.ALREADY, keep_open=True, site=site, board=Board())
    assert len(took) == 1 and took[0]["worker"] == 0 and "already" not in took[0]  # taken, with a tile of its own


def test_a_run_ends_once_its_last_form_closed_though_an_already_applied_tile_waits(monkeypatch, tmp_path):
    """Fault: an already-applied link's thread waits for the run's release, which only Ctrl-C or Stop gave, so a run
    whose every held form was sent or closed by hand never ended (run7, 2026-11-26)."""
    monkeypatch.setattr(fill_engine, "ready", lambda: None)
    monkeypatch.setattr(rehearsal, "guard", lambda page: None)
    outcomes = {URL: rehearsal.ALREADY, URL + "?b": rehearsal.FAILED}  # the failed one's page closed: nothing held

    def fill(url, kept, *rest, **more):
        if outcomes[url] != rehearsal.ALREADY:
            with kept.open(url):
                pass
        return rehearsal.Rehearsed(Posting("", "Example", "", url), outcomes[url], "")
    monkeypatch.setattr(rehearsal, "_rehearse", fill)
    adapters = Adapters(feed=SimplifyFeed(lambda: b"[]"), site=_Site(), claude=FakeClaude(), tracker=InMemoryTracker(),
                        mailbox=FakeMailbox(), usage=ScriptedUsage(), clock=FakeClock(datetime(2026, 11, 26, 9)),
                        board=RecordingBoard())
    profile = ApplicantProfile.load(profile_with(tmp_path))
    run = threading.Thread(target=rehearsal.rehearse, args=(list(outcomes), adapters, profile, 2), daemon=True,
                           kwargs={"keep_open": True, "out": lambda line: None})
    run.start()
    run.join(10)
    assert not run.is_alive()
