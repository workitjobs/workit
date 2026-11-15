"""Every Chrome a test starts closes when its test process ends, however it ends (tests/chrome_reaper.py), and never
a process with another profile. Stand-ins only: each "Chrome" is a sleeping Python whose command line shows its
profile as Chrome's does. No browser: in CI."""

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).parent
# A test process: it watches each profile given, says where its list is, then ends as `how` says.
TEST_PROCESS = """import sys, time
sys.path.insert(0, sys.argv[1])
import chrome_reaper
for profile in sys.argv[3:]:
    chrome_reaper.watch(profile)
print(chrome_reaper._LIST, flush=True)
if sys.argv[2] == "killed":
    time.sleep(60)
if sys.argv[2] == "ctrl-c":
    raise KeyboardInterrupt
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="the reaper is POSIX only")


def chrome(profile: Path, *flags: str) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", *flags, f"--user-data-dir={profile}"])


def start_test_process(how: str, profiles: list[Path]) -> tuple[subprocess.Popen, Path]:
    process = subprocess.Popen([sys.executable, "-c", TEST_PROCESS, str(TESTS), how, *map(str, profiles)],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return process, Path(process.stdout.readline().strip())


def gone(process: subprocess.Popen, within: float) -> bool:
    try:
        process.wait(timeout=within)
        return True
    except subprocess.TimeoutExpired:
        return False


@pytest.fixture
def chromes():
    started = []
    yield lambda profile, *flags: started.append(chrome(profile, *flags)) or started[-1]
    for process in started:
        if process.poll() is None:
            process.kill()


def kill_tree(process: subprocess.Popen) -> None:
    """A stopped task's kill: the process and every process under it, found by parent PID."""
    under = subprocess.run(["pgrep", "-P", str(process.pid)], capture_output=True, text=True).stdout.split()
    for pid in [process.pid, *map(int, under)]:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


@pytest.mark.parametrize("how", ["killed", "tree killed", "ctrl-c", "exit"])
def test_a_chrome_left_running_closes_however_its_test_process_ends(tmp_path, chromes, how):
    """SIGKILL (a timeout), a kill of the whole tree (a stopped task), an interrupt during the fixtures' stop (a second
    Ctrl-C), and a normal finish whose fixture never stopped its Chrome: each Chrome is stopped once the process is
    gone, and never one whose profile is another, though its path starts the same."""
    left, other = chromes(tmp_path / "plain-1"), chromes(tmp_path / "plain-10")
    process, listed = start_test_process("killed" if "killed" in how else how, [tmp_path / "plain-1", tmp_path / "plain-2"])
    if how == "killed":
        process.kill()
    elif how == "tree killed":
        kill_tree(process)
    process.wait()
    assert gone(left, within=10)
    assert not gone(other, within=1)
    assert not listed.exists()


def test_a_profile_whose_path_has_a_space_is_stopped_too(tmp_path, chromes):
    left = chromes(tmp_path / "Jane Doe" / "plain-1")
    process, _ = start_test_process("killed", [tmp_path / "Jane Doe" / "plain-1"])
    process.kill()
    process.wait()
    assert gone(left, within=10)


def test_chromes_own_helpers_are_never_signalled_only_the_browser(tmp_path, chromes):
    """A helper (--type=renderer) exits with its browser: signalled from an old list, a reused PID could be another's."""
    from chrome_reaper import running

    browser, helper = chromes(tmp_path / "plain-1"), chromes(tmp_path / "plain-1", "--type=renderer")
    found = running({str(tmp_path / "plain-1")})
    assert browser.pid in found and helper.pid not in found


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


def test_any_chrome_a_test_starts_through_subprocess_is_watched(monkeypatch, tmp_path):
    """conftest's Popen hook: a Chrome command (network_block's test) with a profile of its own, whatever started it."""
    import chrome_reaper

    watched = []
    monkeypatch.setattr(chrome_reaper, "watch", watched.append)
    with pytest.raises(OSError):  # no such binary: the hook has run by then
        subprocess.Popen([str(tmp_path / "Google Chrome for Testing"), f"--user-data-dir={tmp_path / 'p'}"])
    with pytest.raises(OSError):
        subprocess.Popen([str(tmp_path / "not-a-browser"), f"--user-data-dir={tmp_path / 'q'}"])
    assert watched == [str(tmp_path / "p")]
