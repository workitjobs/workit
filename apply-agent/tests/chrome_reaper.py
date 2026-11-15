"""Every Chrome a test starts for a plain Worker closes when its test process ends, even when that process is killed.

A plain Worker's Chrome runs on its own (`open -g -n` on the Mac, a session of its own elsewhere:
apply.plain.launcher.start_in_background), so it outlives a test process that dies before its fixtures stop it.
Each pytest run that a timeout, a stopped task or a second Ctrl-C ended left its Chrome for Testing windows open
(five of them, 2026-11-15). Playwright's own browsers close with their driver; these didn't.

`watch(profile)` lists one such Chrome by its profile folder, before it starts: a test process killed while the
Chrome starts (on the Mac, before its PID is known) still leaves none. The first call starts this file as a reaper
process beside the test process. It waits until that process is gone, then stops every process that runs with a
listed profile as its `--user-data-dir`: a test's profile is a temporary folder of its own, so no other process has
it. A test process that ends normally stopped its Chromes itself and deletes the list as it exits: the reaper then
stops nothing. POSIX only.
"""

import atexit
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_LIST: Path | None = None  # the profiles of this process's Chromes, one a line
_LOCK = threading.Lock()


def watch(profile: Path | str) -> None:
    """Stop the Chrome with `profile` if this process ends without stopping it."""
    global _LIST
    if os.name != "posix":
        return
    with _LOCK:
        if _LIST is None:
            fd, name = tempfile.mkstemp(prefix="apply-test-chromes-", suffix=".txt")
            os.close(fd)
            _LIST = Path(name)
            atexit.register(_LIST.unlink, missing_ok=True)  # ended normally: its fixtures stopped them
            subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve()), str(os.getpid()), name],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True, close_fds=True)
        with _LIST.open("a") as listed:
            listed.write(f"{profile}\n")


def reap(parent: int, listed: Path, poll: float = 0.5) -> None:
    """Wait until process `parent`, which started this one, is gone (this one's parent is then another), then stop
    each process that runs with a profile in `listed`."""
    while os.getppid() == parent:
        time.sleep(poll)
    try:
        profiles = {line for line in listed.read_text().splitlines() if line}
    except OSError:
        return  # it ended normally
    listed.unlink(missing_ok=True)
    for pid in running(profiles):
        stop(pid)


def running(profiles: set[str]) -> list[int]:
    """Each process whose command line names one of `profiles` as its whole `--user-data-dir`."""
    if not profiles:
        return []
    shown = subprocess.run(["ps", "-ww", "-Ao", "pid=,command="], capture_output=True, text=True).stdout
    found = []
    for line in shown.splitlines():
        pid, _, command = line.strip().partition(" ")
        words = command.split()
        if pid.isdigit() and any(f"--user-data-dir={profile}" in words for profile in profiles):
            found.append(int(pid))
    return found


def stop(pid: int, wait: float = 3.0) -> None:
    """SIGTERM, as Chrome quits cleanly on it, then SIGKILL after `wait` seconds if it hasn't."""
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        time.sleep(0.1)
        try:
            os.kill(pid, 0)
        except OSError:
            return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


if __name__ == "__main__":
    reap(int(sys.argv[1]), Path(sys.argv[2]))
