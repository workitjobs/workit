"""Every Chrome a test starts closes when its test process ends: when it finishes, and when it is killed.

A plain Worker's Chrome runs on its own (`open -g -n` on the Mac, a session of its own elsewhere:
apply.plain.launcher.start_in_background), so it outlives a test process that ends before its fixtures stop it.
Each pytest run that a timeout, a stopped task or a second Ctrl-C ended left its Chrome for Testing windows open
(five of them, 2026-11-15). Playwright's own browsers close with their driver; these didn't.

`watch(profile)` lists one such Chrome by its profile folder, before it starts (conftest calls it). The first call
starts this file as a reaper, outside the test process's tree: a middle process starts it and exits at once, so a
stop that kills a process and everything under it (a stopped task) never reaches it. The reaper waits for the end of
a pipe whose write end only the test process holds, so it hears that process end however it ends: a normal finish,
an exception, a second Ctrl-C, SIGKILL. Then it stops every browser that still runs with a listed profile as its
whole `--user-data-dir`, a fixture's leftover too. A test's profile is a temporary folder of its own, so no other
process has it. Chrome's own helpers (`--type=`) exit with their browser and are never signalled. POSIX only.
"""

import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_LIST: Path | None = None  # the profiles of this process's Chromes, one a line
_ALIVE: int | None = None  # the pipe's write end: open for as long as this process lives, never passed to a child
_LOCK = threading.Lock()


def watch(profile: Path | str) -> None:
    """Stop the Chrome with `profile` if it still runs when this process ends."""
    global _LIST, _ALIVE
    if os.name != "posix":
        return
    with _LOCK:
        if _LIST is None:
            fd, name = tempfile.mkstemp(prefix="apply-test-chromes-", suffix=".txt")
            os.close(fd)
            hear, _ALIVE = os.pipe()  # neither end is inheritable: only the reaper is given its end
            subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "detach", str(hear), name],
                           pass_fds=(hear,), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, start_new_session=True, check=False)
            os.close(hear)
            _LIST = Path(name)
        with _LIST.open("a") as listed:
            listed.write(f"{profile}\n")


def detach(hear: int, listed: str) -> None:
    """The middle process: start the reaper, and end, so the reaper's parent is the OS's, not the test process."""
    subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve()), "reap", str(hear), listed],
                     pass_fds=(hear,), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def reap(hear: int, listed: Path) -> None:
    """Wait for the end of the pipe (the test process is gone: nothing holds its write end), then stop each browser
    that still runs with a profile in `listed`."""
    while os.read(hear, 1):
        pass
    try:
        profiles = {line for line in listed.read_text().splitlines() if line}
    except OSError:
        profiles = set()
    listed.unlink(missing_ok=True)
    for pid in running(profiles):
        stop(pid)


def running(profiles: set[str]) -> list[int]:
    """Each browser (not a helper of Chrome's, `--type=`) whose `--user-data-dir` is one of `profiles`, whole."""
    if not profiles:
        return []
    shown = subprocess.run(["ps", "-ww", "-Ao", "pid=,command="], capture_output=True, text=True).stdout
    found = []
    for line in shown.splitlines():
        pid, _, command = line.strip().partition(" ")
        command = f" {command} "
        if pid.isdigit() and " --type=" not in command \
                and any(f" --user-data-dir={profile} " in command for profile in profiles):
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
    if sys.argv[1] == "detach":
        detach(int(sys.argv[2]), sys.argv[3])
    else:
        reap(int(sys.argv[2]), Path(sys.argv[3]))
