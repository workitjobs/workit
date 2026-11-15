"""A plain Worker's Chrome a test started closes when its test process is killed (tests/chrome_reaper.py), and never
a process with another profile. Stand-ins only: each "Chrome" is a sleeping Python whose command line shows its
profile as Chrome's does. No browser: in CI."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

TESTS = Path(__file__).parent
# A test process: it watches two profiles, says so, then ends as `how` says ("killed": it waits to be).
TEST_PROCESS = """import sys, time
sys.path.insert(0, sys.argv[1])
import chrome_reaper
chrome_reaper.watch(sys.argv[2])
chrome_reaper.watch(sys.argv[3])
print(chrome_reaper._LIST, flush=True)
if sys.argv[4] == "killed":
    time.sleep(60)
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="the reaper is POSIX only")


def chrome(profile: Path) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", f"--user-data-dir={profile}"])


def start_test_process(how: str, profiles: list[Path]) -> tuple[subprocess.Popen, Path]:
    process = subprocess.Popen([sys.executable, "-c", TEST_PROCESS, str(TESTS), *map(str, profiles), how],
                               stdout=subprocess.PIPE, text=True)
    return process, Path(process.stdout.readline().strip())


def gone(process: subprocess.Popen, within: float) -> bool:
    try:
        process.wait(timeout=within)
        return True
    except subprocess.TimeoutExpired:
        return False


def test_a_killed_test_process_leaves_no_chrome_open_and_no_other_process_stopped(tmp_path):
    left, other = chrome(tmp_path / "plain-1"), chrome(tmp_path / "plain-10")  # "plain-1" is a part of its path
    try:
        process, listed = start_test_process("killed", [tmp_path / "plain-1", tmp_path / "plain-2"])
        process.kill()  # as a timeout or a stopped task kills pytest: no fixture, no atexit runs
        process.wait()
        assert gone(left, within=10)  # the reaper stopped it
        assert not gone(other, within=1)  # never a process whose profile is another, though its path starts the same
        assert not listed.exists()
    finally:
        for p in (left, other):
            if p.poll() is None:
                p.kill()


def test_a_test_process_that_ends_normally_leaves_the_reaper_nothing(tmp_path):
    """It stopped its Chromes itself (its fixtures, atexit) and deleted the list: the reaper stops nothing."""
    one, two = chrome(tmp_path / "plain-1"), chrome(tmp_path / "plain-2")
    try:
        process, listed = start_test_process("exit", [tmp_path / "plain-1", tmp_path / "plain-2"])
        assert process.wait(timeout=10) == 0 and not listed.exists()
        time.sleep(1.5)  # the reaper's look after its parent went
        assert one.poll() is None and two.poll() is None
    finally:
        for p in (one, two):
            if p.poll() is None:
                p.kill()


def test_every_plain_worker_a_test_starts_is_watched_before_it_starts(monkeypatch, tmp_path):
    """conftest wraps launcher.start_in_background, which every PlainWorkers.launch goes through: the profile is
    listed before Chrome starts, so a test process killed while it starts still leaves no Chrome."""
    import chrome_reaper

    from apply.plain import launcher

    order = []
    monkeypatch.setattr(chrome_reaper, "watch", lambda profile: order.append(("watched", profile)))

    def popen(arguments, **options):
        order.append(("started", arguments[0]))
        return type("P", (), {"pid": 4242})()
    started = launcher.start_in_background(["/x/chrome"], tmp_path, tmp_path / "plain-1.log", "linux", popen)
    assert started.pid == 4242 and order == [("watched", tmp_path), ("started", "/x/chrome")]
