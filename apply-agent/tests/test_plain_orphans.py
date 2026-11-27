"""A plain Worker's Chrome that a gone Apply left running is reclaimed at the next start (KAN-885); one a live Apply
owns, one no Apply noted, and a process that only took a stale lock's PID are never stopped. Stand-in processes play
Chrome and the gone Apply: needs no browser, in CI."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import psutil
import pytest

from apply.browsers import ProfileInUse
from apply.plain import launcher
from apply.plain.launcher import OWNER, PlainWorkers, orphan, own, reclaim
from apply.plain.site import PlainSite

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Chrome's SingletonLock is a symlink on POSIX only")

SLEEP = "import time; time.sleep(60)"


@pytest.fixture(autouse=True)
def quick_stop(monkeypatch):
    monkeypatch.setattr(launcher, "STOP_WAIT", 2.0)


def chrome(profile: Path, *arguments: str) -> psutil.Process:
    """A stand-in for Chrome holding `profile`: its command line names the folder, and the lock names its PID. A shell
    starts it and ends, so, like a Worker's Chrome that `open` started, it is no child of this process."""
    profile.mkdir(parents=True, exist_ok=True)
    command = shlex.join([sys.executable, "-c", SLEEP, f"--user-data-dir={profile}", *arguments])
    shown = subprocess.run(["/bin/sh", "-c", f"{command} >/dev/null 2>&1 & echo $!"], capture_output=True, text=True,
                           check=True)
    process = psutil.Process(int(shown.stdout))
    lock = profile / "SingletonLock"
    lock.unlink(missing_ok=True)
    os.symlink(f"host-{process.pid}", lock)
    return process


def gone_owner(profile: Path) -> None:
    """Note an Apply that has since ended as `profile`'s owner."""
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    started = psutil.Process(process.pid).create_time()
    process.wait()
    (profile / OWNER).write_text(json.dumps({"pid": process.pid, "started": started}))


def ended(process: psutil.Process) -> bool:
    try:
        process.wait(5)
    except psutil.TimeoutExpired:
        return False
    return True


@pytest.fixture
def started():
    processes = []
    yield processes
    for process in processes:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass


def test_a_chrome_whose_apply_is_gone_is_reclaimed(tmp_path, started):
    profile = tmp_path / "plain-1"
    started.append(process := chrome(profile))
    gone_owner(profile)
    assert orphan(profile) == process.pid
    assert reclaim(profile)
    assert ended(process)


def test_a_chrome_a_live_apply_owns_is_kept(tmp_path, started):
    profile = tmp_path / "plain-1"
    started.append(process := chrome(profile))
    own(profile)  # this test process: alive
    assert orphan(profile) is None
    assert not reclaim(profile)
    assert process.is_running()


def test_a_chrome_no_apply_noted_is_kept(tmp_path, started):
    profile = tmp_path / "plain-1"
    started.append(process := chrome(profile))
    assert not reclaim(profile)
    assert process.is_running()


def test_an_owner_pid_the_os_gave_to_another_process_counts_as_gone(tmp_path, started):
    profile = tmp_path / "plain-1"
    started.append(process := chrome(profile))
    me = psutil.Process()
    (profile / OWNER).write_text(json.dumps({"pid": me.pid, "started": me.create_time() - 3600}))
    assert orphan(profile) == process.pid


def test_a_stale_lock_whose_pid_is_another_chrome_is_never_stopped(tmp_path, started):
    """The lock names a PID that is now the student's own Chrome, on its own profile: not this Worker's."""
    profile = tmp_path / "plain-1"
    started.append(student := chrome(tmp_path / "student-chrome"))
    profile.mkdir()
    os.symlink(f"host-{student.pid}", profile / "SingletonLock")
    gone_owner(profile)
    assert not reclaim(profile)
    assert student.is_running()


def test_a_chrome_helper_is_never_taken_for_the_browser(tmp_path, started):
    profile = tmp_path / "plain-1"
    started.append(helper := chrome(profile, "--type=renderer"))
    gone_owner(profile)
    assert not reclaim(profile)
    assert helper.is_running()


def test_a_run_reclaims_orphans_and_still_refuses_a_live_runs_profile(tmp_path, started):
    site = PlainSite(PlainWorkers(tmp_path, kind="testing"), fetcher=object())
    started.append(left := chrome(tmp_path / "plain-1"))
    gone_owner(tmp_path / "plain-1")
    started.append(live := chrome(tmp_path / "plain-2"))
    own(tmp_path / "plain-2")
    with pytest.raises(ProfileInUse, match="plain-2") as refused:
        site.refuse_in_use()
    assert "plain-1" not in str(refused.value)
    assert ended(left)
    assert live.is_running()


def test_stop_all_stops_a_chrome_still_starting(tmp_path, started):
    """The app quits while a Worker's Chrome is up but hasn't said hello yet: the quit's stop_all closes it too."""
    workers = PlainWorkers(tmp_path, kind="testing")
    started.append(process := chrome(tmp_path / "plain-1"))
    workers._starting[0] = launcher.Chrome(process.pid)
    workers.stop_all()
    assert ended(process)
    assert not workers._starting


def test_this_apply_exiting_stops_every_chrome_it_started(tmp_path, started):
    """Fault: an Apply that exits without its own stop (an exception, a quit by signal) leaves its Workers' Chromes up,
    since they run on their own."""
    workers = PlainWorkers(tmp_path, kind="testing")
    started.append(process := chrome(tmp_path / "plain-1"))
    workers._starting[0] = launcher.Chrome(process.pid)
    launcher.stop_everyone()  # what atexit runs
    assert ended(process)


def test_the_app_closes_every_chrome_a_gone_apply_left_as_it_starts(tmp_path, started, monkeypatch):
    """Fault: after a crash, the Chromes it left (one per form) stay open till a run reaches each profile."""
    from apply import student

    for name in ("plain-1", "plain-7"):
        started.append(chrome(tmp_path / name))
        gone_owner(tmp_path / name)
    monkeypatch.setenv("APPLY_PROFILES", str(tmp_path))
    student.reclaim_left()
    assert all(ended(process) for process in started)
