"""Keep the computer awake while a run goes (KAN-885), so it never sleeps mid-form.

On the Mac, `caffeinate -dims -w <Apply's PID>`: no display, idle or system sleep (system sleep on AC power only, as
macOS allows) and the disk stays up. `-w` ends it with Apply however Apply ends, a crash or SIGKILL too, and the run's
end stops it at once. Windows and Linux: nothing yet (F4).
"""

import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager

CAFFEINATE = "/usr/bin/caffeinate"


def command(system: str = sys.platform, pid: int | None = None) -> list[str] | None:
    """The command that keeps this OS awake while process `pid` (default: this one) runs, or None."""
    if system != "darwin":
        return None
    return [CAFFEINATE, "-dims", "-w", str(pid or os.getpid())]


@contextmanager
def awake(system: str = sys.platform, popen: Callable[..., subprocess.Popen] = subprocess.Popen) -> Iterator[None]:
    """The computer stays awake inside this block. A caffeinate that can't start never stops the run."""
    arguments = command(system)
    process = None
    if arguments:
        try:
            process = popen(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as error:
            print(f"Couldn't keep the Mac awake ({error}): it may sleep during the run.", file=sys.stderr)
    try:
        yield
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(5)
            except subprocess.TimeoutExpired:
                process.kill()
