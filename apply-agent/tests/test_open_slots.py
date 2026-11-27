"""A rehearsal's places among the open forms (rehearsal.OPEN_FORMS) and its Workers' turns, with each fill faked:
every path a job ends on gives its place back once, and the next queued job starts. No browser."""

import threading
import time
from contextlib import contextmanager
from datetime import datetime

import pytest
from fakes import FakeClaude, FakeClock, FakeMailbox, RecordingBoard, ScriptedUsage
from test_run_answers import profile_with

from apply import fill_engine, rehearsal
from apply.adapters import Adapters
from apply.feed import SimplifyFeed
from apply.model import Posting, Status
from apply.profile import ApplicantProfile
from apply.tracker import InMemoryTracker

NOW = datetime(2026, 11, 26, 9, 30)
WAIT = 20.0  # seconds a test waits for the run to reach a state before it fails


class Page:
    """A form's page, open until the test or the run closes it."""

    def __init__(self):
        self.closed = False

    def is_closed(self) -> bool:
        return self.closed


class Site:
    """No browser: rehearsal._rehearse is faked, so nothing opens through it."""

    def fetch(self, url, body=None):
        return b""

    @contextmanager
    def open(self, url, worker=0):
        yield Page()


class Run:
    """The faked fills of one rehearsal: each link's `plan` says how its fill ends, and `open` holds the tiles whose
    page waits on the student now."""

    def __init__(self, plans: dict[str, list[str]]):
        self.plans = plans  # link -> how each fill of it ends, in turn
        self.started: list[str] = []  # each fill's link, as it started
        self.open: set[int] = set()  # tiles with a page open now
        self.most = 0  # the most pages open at once
        self.lock = threading.Lock()

    def fill(self, url, site, adapters, profile, calibration, accounts, n, *args, **kw) -> rehearsal.Rehearsed:
        with self.lock:
            self.started.append(url)
            how = self.plans[url].pop(0)
        posting = Posting(f"id-{n}", "Company", "Role", url)
        if how == "raises":
            raise RuntimeError("the filler broke")
        if how in ("held", "failed here", "not eligible here"):  # its page stays open for the student
            site._page = Page()
            with self.lock:
                self.open.add(n)
                self.most = max(self.most, len(self.open))
        adapters.board.update(n, status="filling" if how == "held" else how, again=False)
        outcome = {"held": rehearsal.READY, "already": rehearsal.ALREADY,
                   "not eligible": rehearsal.OUTCOMES[Status.NOT_ELIGIBLE],
                   "not eligible here": rehearsal.OUTCOMES[Status.NOT_ELIGIBLE]}.get(how, rehearsal.FAILED)
        return rehearsal.Rehearsed(posting, outcome, how)

    def closed(self, n: int) -> None:
        with self.lock:
            self.open.discard(n)


def fake_hold(run: Run):
    """_Kept.hold, with no page of its own: it waits while its page is open, until the run ends or the student lets
    it go (the Board's let_go_asked)."""

    def hold(self, release, *args, resume=None, let_go=lambda: False, **kw):
        while not release.is_set():
            if self._page is None or self._page.is_closed() or let_go():
                return ""
            if resume and resume(self._page):
                return rehearsal.RESUME
            time.sleep(0.02)
        return ""
    return hold


@pytest.fixture
def faked(monkeypatch):
    monkeypatch.setattr(fill_engine, "ready", lambda: None)

    def made(plans: dict[str, list[str]]) -> Run:
        run = Run(plans)
        monkeypatch.setattr(rehearsal, "_rehearse", run.fill)
        monkeypatch.setattr(rehearsal._Kept, "hold", fake_hold(run))
        close = rehearsal._Kept.close

        def closing(self):
            if self._page is not None:
                run.closed(self.n)
            close(self)
        monkeypatch.setattr(rehearsal._Kept, "close", closing)
        made_kept = rehearsal._Kept.__init__

        def kept(self, site, worker, shown=lambda tab: None):
            made_kept(self, site, worker, shown)
            self.n = worker
        monkeypatch.setattr(rehearsal._Kept, "__init__", kept)
        return run
    return made


class Board(RecordingBoard):
    """The window: Stop applying, and Not applying to this one on each tile named in `let_go`."""

    def __init__(self):
        super().__init__()
        self.let_go: set[int] = set()

    def stopping(self, stop):
        self.stop = stop

    def let_go_asked(self, worker: int) -> bool:
        return worker in self.let_go


def start(links: list[str], board: Board, tmp_path, workers: int = 1) -> threading.Thread:
    adapters = Adapters(feed=SimplifyFeed(lambda: b"[]"), site=Site(), claude=FakeClaude(), tracker=InMemoryTracker(),
                        mailbox=FakeMailbox(), usage=ScriptedUsage(), clock=FakeClock(NOW), board=board)
    profile = ApplicantProfile.load(profile_with(tmp_path))
    thread = threading.Thread(target=rehearsal.rehearse, args=(links, adapters, profile, workers),
                              kwargs={"keep_open": True, "out": lambda line: None}, daemon=True)
    thread.start()
    return thread


def until(check, what: str) -> None:
    ending = time.monotonic() + WAIT
    while not check():
        if time.monotonic() > ending:
            pytest.fail(f"waited {WAIT:.0f} s for {what}")
        time.sleep(0.02)


def end(board: Board, thread: threading.Thread) -> None:
    board.stop()
    thread.join(WAIT)
    assert not thread.is_alive()


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")  # the job that raises
def test_each_way_a_job_fails_gives_its_place_back_and_the_next_queued_job_starts(monkeypatch, faked, tmp_path):
    """Fault: a job that failed, raised, was already applied to, or was ruled out with no page left kept its place
    among the open forms, so jobs stayed queued with Workers free (run10, 2026-11-26: five failed jobs, one form
    filling, three queued)."""
    monkeypatch.setattr(rehearsal, "OPEN_FORMS", 1)
    ends = ["raises", "failed", "already", "not eligible"]  # none leaves a page open
    links = [f"https://jobs.example/{k}" for k in range(len(ends) + 1)]
    run = faked({link: [how] for link, how in zip(links, ends + ["held"])})
    board = Board()
    thread = start(links, board, tmp_path)

    until(lambda: links[-1] in run.started, "the last queued job to start")
    end(board, thread)
    assert run.started == links  # each started in turn, a place freed by the one before


def test_a_failed_form_still_open_holds_its_place_until_let_go_and_never_twice(monkeypatch, faked, tmp_path):
    """Fault: a place given back twice (once as the student lets the form go, once as its thread ends) lets two
    forms open under a cap of one."""
    monkeypatch.setattr(rehearsal, "OPEN_FORMS", 1)
    links = [f"https://jobs.example/{k}" for k in range(3)]
    run = faked({links[0]: ["failed here"], links[1]: ["held"], links[2]: ["held"]})
    board = Board()
    thread = start(links, board, tmp_path, workers=3)

    until(lambda: run.started == links[:1], "the first job to start")
    time.sleep(0.5)
    assert run.started == links[:1]  # its page is open for the student: it waits on them, so nothing else opens
    board.let_go.add(0)
    until(lambda: len(run.started) == 2, "the second job to start once the first was let go")
    time.sleep(0.5)
    assert len(run.started) == 2 and run.most == 1  # the first's place came back once: only one job took it
    end(board, thread)


def test_fill_it_anyway_takes_a_place_again_before_it_fills(monkeypatch, faked, tmp_path):
    """Fault: a ruled-out job whose page is gone waits for Fill it anyway holding no place, then fills past the cap."""
    monkeypatch.setattr(rehearsal, "OPEN_FORMS", 1)
    links = ["https://jobs.example/ruled-out", "https://jobs.example/next"]
    run = faked({links[0]: ["not eligible", "held"], links[1]: ["held"]})
    pressed = []

    class Pressing(Board):
        def resumed(self, worker: int) -> bool:  # Fill it anyway, pressed once the next job holds the place
            if worker == 0 and links[1] in run.started and not pressed:
                pressed.append(True)
                return True
            return False

    board = Pressing()
    thread = start(links, board, tmp_path, workers=2)

    until(lambda: pressed, "Fill it anyway to be pressed")
    time.sleep(0.5)
    assert run.started == links  # the ruled-out job waits for the next one's place
    board.let_go.add(1)
    until(lambda: run.started == links + links[:1], "the ruled-out job to fill again")
    assert run.most == 1
    end(board, thread)
