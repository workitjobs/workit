"""File locks that work on every OS (KAN-929, P1 of docs/windows_desktop.md): never `fcntl`, which Windows lacks.

Each data file that two Apply processes may write (a run, the window, `apply ask`) has a lock file of its own beside
it, `<name>.lock`, that holds nothing. Files that work on their own never share a lock; files that must change
together do (the Sheet takes the Tracker's, sheet.locked).

- A lock file is made at first use, in the data folder beside its data file: never in the app's package, which is
  read-only. The OS releases a lock when its process ends, so a crash leaves only an empty file.
- A lock file is opened to append, so taking a lock never empties a file, even one named by mistake.
- Never lock the data file itself: on Windows a lock also stops every other handle from reading the locked bytes,
  Apply's own too.
- portalocker does the locking: `fcntl.flock` on macOS and Linux, as Apply did before, so an older Apply on the same
  data folder still waits for this one; `msvcrt.locking` on Windows. Its Windows lock is exclusive only (a shared
  one needs pywin32), so every lock here is exclusive.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import portalocker


@contextmanager
def held(path: Path) -> Iterator[None]:
    """Hold the lock file `path` until the block ends. Waits as long as another process holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as lock:
        while True:
            try:
                portalocker.lock(lock, portalocker.LockFlags.EXCLUSIVE)
                break
            except portalocker.AlreadyLocked:  # Windows tries for about 10 s, then gives up: wait again
                continue
        try:
            yield
        finally:
            portalocker.unlock(lock)


@contextmanager
def tried(path: Path) -> Iterator[bool]:
    """Take the lock file `path` only if no other process holds it, and hold it until the block ends. Yields
    whether it took it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as lock:
        try:
            portalocker.lock(lock, portalocker.LockFlags.EXCLUSIVE | portalocker.LockFlags.NON_BLOCKING)
        except portalocker.AlreadyLocked:
            yield False
            return
        try:
            yield True
        finally:
            portalocker.unlock(lock)
