"""WorkIt Auto Apply's window with no port (KAN-858, W5 step 2; D11, D12): the Apply window's routes answered through
pywebview's bridge in this process, its tiles' frames and files, and the sign-in, against a fake WorkIt. No window
and no browser: in CI. tests/test_app_window_page.py runs the page's shim in Chromium."""

import base64

import pytest
from fake_workit import FakeWorkIt

from apply import app_window, dashboard, workit
from apply.app_window import SHIM, Bridge
from apply.dashboard import NO_PORT, Dashboard
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
    """Fault: the window keeps no verifier, or never shows the Apply window after the code."""
    with FakeWorkIt() as fake:
        opened, window = [], Window()
        bridge = Bridge(board, WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain), opened.append)
        bridge._window = window
        assert "error" in bridge.trade("a code")  # no sign-in started

        url = bridge.sign_in()
        assert opened == [url] and url.startswith(f"{fake.url}/app-sign-in?challenge=")
        assert "error" in bridge.trade("not the page's code")
        assert "error" in bridge.trade(fake.browser(url))  # a refused code spends the sign-in: press it again

        url = bridge.sign_in()
        assert bridge.trade(fake.browser(url)) == {"email": "test.person@example.com"}
        assert bridge.signed_in() and window.loaded == [app_window.page(board)]

