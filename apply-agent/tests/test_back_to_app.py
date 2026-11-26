"""After a captcha the student did in a Worker's own window, the Apply window comes back (KAN-855): a breath after
Apply sees it done (captcha.BACK_AFTER_S), and only while that Worker's window is still the front one, so it never
takes the student from another app. No browser: in CI."""

import threading
from types import SimpleNamespace

import pytest

from apply import browsers, captcha, cli, dashboard, focus
from apply.browsers import WorkerBrowsers
from apply.dashboard import Dashboard, NoFrames
from apply.plain.launcher import PlainWorkers


class Board:
    def __init__(self):
        self.back, self.came = [], threading.Event()

    def update(self, worker, **caption):
        pass

    def resumed(self, worker) -> bool:
        return False

    def come_back(self, worker) -> bool:
        self.back.append(worker)
        self.came.set()
        return True


@pytest.mark.parametrize("done", [True, False])
def test_the_app_comes_back_a_breath_after_the_captcha_is_done(monkeypatch, done):
    monkeypatch.setattr(captcha, "BACK_AFTER_S", 0.2)
    monkeypatch.setattr(captcha, "pending", lambda page: True)  # a challenge on view as the wait begins
    monkeypatch.setattr(captcha, "wait", lambda page, pressed, minutes: done)
    board = Board()
    waiter = captcha.Waiter(board, 1, None, SimpleNamespace(policy=lambda key: None), dict)
    assert waiter("Do the captcha", SimpleNamespace()) is done
    assert board.back == []  # not at once: the fill goes on, and the student sees the page go on first
    assert board.came.wait(1.0) is done
    assert board.back == ([1] if done else [])  # a wait that ended without it (time out, page closed): never


def test_the_app_comes_back_once_and_only_for_a_captcha_on_view(monkeypatch):
    """KAN-855's second review: a wait with no challenge on view ends at once (KAN-760) and calls no one back; a
    challenge that comes back again on the same form pulls the student back once at most."""
    monkeypatch.setattr(captcha, "BACK_AFTER_S", 0.05)
    monkeypatch.setattr(captcha, "wait", lambda page, pressed, minutes: True)
    on_view = [False]
    monkeypatch.setattr(captcha, "pending", lambda page: on_view[0])
    board = Board()
    waiter = captcha.Waiter(board, 0, None, SimpleNamespace(policy=lambda key: None), dict)
    assert waiter("Do the captcha", SimpleNamespace()) and not board.came.wait(0.3)  # nothing on view: no call back
    on_view[0] = True
    assert waiter("Do the captcha", SimpleNamespace()) and board.came.wait(1.0) and board.back == [0]
    board.came.clear()
    assert waiter("Do the captcha", SimpleNamespace()) and not board.came.wait(0.3)  # the same form again: no more


def test_the_window_comes_back_only_while_the_workers_window_is_in_front(monkeypatch, tmp_path):
    raised, front = [], {0: True, 1: False}
    tries = []
    monkeypatch.setattr(dashboard, "raise_window", lambda window, timeout=10.0: tries.append(timeout) or raised.append(window) or True)
    back = cli._back_to_window(SimpleNamespace(in_front=lambda worker: front[worker]), tmp_path / "dashboard")
    with Dashboard(2, NoFrames(), back=back) as board:
        assert board.come_back(0) and raised == [tmp_path / "dashboard"]
        assert tries == [0]  # one try at once after the check: never a while later, over an app he switched to
        assert not board.come_back(1) and len(raised) == 1  # he went on to another app: it stays there
    with Dashboard(1, NoFrames()) as board:
        assert not board.come_back(0)  # a window with no way back (a test's, the Student build's before W5)
    assert cli._back_to_window(SimpleNamespace(), tmp_path) is None  # a site that can't tell: never


def test_a_worker_is_in_front_when_its_chrome_is_the_front_app(monkeypatch, tmp_path):
    monkeypatch.setattr(browsers, "chrome_pid", lambda profile: 4242 if profile.name == "worker-1" else None)
    monkeypatch.setattr(focus.KEEPER, "front", lambda: 4242)
    cdp = WorkerBrowsers(tmp_path / "profiles", headless=False, channel=None)
    assert cdp.in_front(0) and not cdp.in_front(1)
    assert not WorkerBrowsers(tmp_path / "profiles", headless=True, channel=None).in_front(0)  # no window at all
    monkeypatch.setattr(focus.KEEPER, "front", lambda: 7)
    plain = PlainWorkers(tmp_path / "plain", kind="testing")
    plain.running[0] = SimpleNamespace(pid=7)
    plain.running[1] = SimpleNamespace(pid=8)
    assert plain.in_front(0) and not plain.in_front(1) and not plain.in_front(2)


def test_off_the_mac_no_worker_is_ever_in_front():
    """Windows and Linux have no FocusKeeper (W4): it can't tell the front app, so the window never comes back by
    itself, and no macOS command runs."""
    assert focus.NoKeeper().front() is None
