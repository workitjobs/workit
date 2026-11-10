"""A plain Worker tile that fell back to the extension's frames is filmed again (KAN-751): a fake extension
(test_plain_tile_identity.Worker) and a fake ScreenCaptureKit helper whose window title can change mid-run, as
amazon.jobs' did during its sign-in's redirects. No browser, no Screen Recording."""

import base64
import json
import sys
import time
from itertools import pairwise

import pytest
from test_plain_tile_identity import BOFA, Worker, seen

from apply.plain import tile, window_capture
from apply.plain.tile import PortFrames

TAB_TITLE = "Log in or create account | Amazon.jobs"
FILMED = b"\xff\xd8\xff\xe0 amazon, filmed"
EXTENSION = b"\xff\xd8\xff\xe0 amazon, from its extension"

# Each aimed line: macOS's windows read again from FAKE_WINDOWS_FILE, so a test can change a title while it runs.
HELPER = '''import json, os, struct, sys
pid = int(sys.argv[sys.argv.index("--pid") + 1])
for line in sys.stdin:
    title = line.rstrip("\\n").split(" ", 6)[6]
    with open(os.environ["FAKE_WINDOWS_FILE"]) as listed:
        windows = json.load(listed)
    if os.environ.get("FAKE_HELPER") == "confused":  # films another Chrome's window whatever it is asked
        found = windows["other"]
    else:
        found = next((w for w in windows.values() if w["pid"] == pid and w["title"] == title), None)
    if found is None:
        print(json.dumps({"mismatch": "no one window of pid %d titled as its tab" % pid, "pid": pid}), file=sys.stderr,
              flush=True)
        continue
    print(json.dumps({"window": 7, "pid": found["pid"], "title": found["title"]}), file=sys.stderr, flush=True)
    frame = __import__("base64").b64decode(found["data"])
    for _ in range(3):
        sys.stdout.buffer.write(struct.pack(">I", len(frame)) + frame)
    sys.stdout.buffer.flush()
'''


@pytest.fixture
def macos(tmp_path, monkeypatch):
    """`macos(title)` sets the title macOS lists for the Worker's window (pid 1000); another Chrome (pid 2000) shows
    Bank of America's. RETRY is short, so a test sees several tries."""
    script, listed = tmp_path / "window-capture", tmp_path / "windows.json"
    script.write_text(f"#!{sys.executable}\n{HELPER}")
    script.chmod(0o700)
    monkeypatch.setenv("FAKE_WINDOWS_FILE", str(listed))
    monkeypatch.setattr(window_capture, "helper", lambda: script)
    monkeypatch.setattr(window_capture, "allowed", lambda: True)
    monkeypatch.setattr(window_capture, "chrome_of", lambda host_pid: {101: 1000}.get(host_pid))
    monkeypatch.setattr(tile, "RETRY", 0.5)
    monkeypatch.setattr(tile, "RETRY_MOST", 2.0)

    def title(shown: str) -> None:
        listed.write_text(json.dumps({
            "amazon": {"pid": 1000, "title": shown, "data": base64.b64encode(FILMED).decode()},
            "other": {"pid": 2000, "title": TAB_TITLE, "data": base64.b64encode(BOFA).decode()},
        }))
    title("Amazon IdPrism")
    return title


def amazon() -> Worker:
    return Worker(101, TAB_TITLE, {5: EXTENSION}, tab=5)


def test_a_tile_that_fell_back_is_filmed_again_once_macos_lists_the_tabs_title(macos):
    worker = amazon()
    with PortFrames(1, [worker].__getitem__, capture="native", chrome={0: 1000}.get) as frames:
        before = seen(frames, 0, 1.5)  # macOS still says "Amazon IdPrism": the helper refuses the window
        fell_back = dict(frames.native), worker.started[-1]["native"]
        macos(TAB_TITLE)  # the redirects are over
        after = seen(frames, 0, 3)

    assert before == [EXTENSION] and fell_back == ({}, False)
    assert after[-1] == FILMED and worker.started[-1]["native"] is True


def test_a_window_that_never_matches_is_tried_again_less_often_and_its_tile_never_blanks(macos):
    worker, tries = amazon(), []
    call = worker.call

    def timed(op, timeout=None, **params):
        if op == "tile.start" and params.get("native"):
            tries.append(time.monotonic())
        return call(op, timeout, **params)
    worker.call = timed
    with PortFrames(1, [worker].__getitem__, capture="native", chrome={0: 1000}.get) as frames:
        shown, deadline = [], time.monotonic() + 6
        while time.monotonic() < deadline:
            frame = frames.wait(0, 0, 0.05)[0]
            if frame is not None or shown:
                shown.append(frame)

    gaps = [later - earlier for earlier, later in pairwise(tries)]
    assert shown and None not in shown and set(shown) == {EXTENSION}  # once a frame showed, the tile always had one
    assert 3 <= len(tries) <= 6  # tried again, but not every turn
    assert all(later >= earlier - 0.3 for earlier, later in pairwise(gaps))  # each wait no shorter than the last
    assert gaps[-1] >= 1.5  # backed off: the waits grew from RETRY towards RETRY_MOST


def test_tries_after_a_fallback_never_show_another_chromes_window(macos, monkeypatch):
    monkeypatch.setenv("FAKE_HELPER", "confused")
    worker = amazon()
    with PortFrames(1, [worker].__getitem__, capture="native", chrome={0: 1000}.get) as frames:
        shown = seen(frames, 0, tile.FIRST_FRAME + 4)

    assert BOFA not in shown and shown == [EXTENSION]
    assert sum(1 for started in worker.started if started["native"]) >= 2  # it did try again
