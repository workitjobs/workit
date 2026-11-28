"""A branded plain Worker that sends no hello (a seed without the worker extension) fails the run's next launches
from that seed at once, with the same fix, not each after HELLO_WAIT: 16 links failed one by one in 8 minutes
(run7, 2026-11-26). A seed made again is tried anew. A played Chrome and bridge: needs no browser, in CI."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from apply.focus import NoKeeper
from apply.plain import launcher
from apply.plain.launcher import PlainWorkers


class _Bridge:
    """The Workers' socket, played: no Worker ever says hello, and each wait is counted."""

    def __init__(self, path: Path):
        self.path, self.waits = path, 0

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def wait_for(self, worker: int, timeout: float):
        self.waits += 1
        raise TimeoutError(f"no hello from plain Worker {worker + 1} in {timeout:.0f} s")


@pytest.fixture
def workers(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "KEEPER", NoKeeper())
    monkeypatch.setattr(launcher, "BRANDED", Path("/chrome"))
    started = []
    monkeypatch.setattr(launcher, "start_in_background",
                        lambda *a, **k: started.append(a) or SimpleNamespace(pid=os.getpid(), poll=lambda: 0))
    workers = PlainWorkers(tmp_path, kind="chrome", extension_dir=tmp_path)
    workers.bridge = _Bridge(tmp_path / "socket")  # its own, for its profiles folder (KAN-929's P5): played here
    workers.prepare = lambda worker=None: {}
    (workers.seed / "Default").mkdir(parents=True)
    (workers.seed / "Default" / "Preferences").write_text("{}")
    workers.started = started
    return workers


def test_after_one_worker_sends_no_hello_the_next_fails_at_once_with_the_same_fix(workers):
    """Fault: each launch from a seed with no worker extension waits its own HELLO_WAIT, the whole batch failing
    slowly, link by link."""
    with pytest.raises(TimeoutError) as first:
        workers.launch(0)
    with pytest.raises(TimeoutError) as second:
        workers.launch(1)
    assert workers.bridge.waits == 1 and len(workers.started) == 1  # no second Chrome, no second wait
    assert "`uv run apply plain seed`" in str(first.value) and str(first.value) in str(second.value)


def test_a_seed_made_again_is_tried_anew(workers):
    """Fault: once a Worker sent no hello, the run never tries a Worker again, even after `apply plain seed` fixed
    the seed."""
    with pytest.raises(TimeoutError):
        workers.launch(0)
    prefs = workers.seed / "Default" / "Preferences"
    os.utime(prefs, ns=(prefs.stat().st_atime_ns, prefs.stat().st_mtime_ns + 1_000_000))  # the seed, made again
    with pytest.raises(TimeoutError):
        workers.launch(1)
    assert workers.bridge.waits == 2
