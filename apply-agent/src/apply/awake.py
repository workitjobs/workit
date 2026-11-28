"""Keep the computer awake while a run goes (KAN-885), so it never sleeps mid-form.

On the Mac, `caffeinate -dims -w <Apply's PID>`: no display, idle or system sleep (system sleep on AC power only, as
macOS allows) and the disk stays up. `-w` ends it with Apply however Apply ends, a crash or SIGKILL too, and the run's
end stops it at once. On Windows, SetThreadExecutionState (KAN-929's P11): the system and the display stay on while
the thread that asked runs, and Windows clears it when that thread ends, a crash too. It is one call through ctypes,
so no library. Linux: nothing yet.
"""

import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager

CAFFEINATE = "/usr/bin/caffeinate"
# SetThreadExecutionState's flags: keep this state till it changes, and keep the system and the display on.
ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002


def command(system: str = sys.platform, pid: int | None = None) -> list[str] | None:
    """The command that keeps this OS awake while process `pid` (default: this one) runs, or None."""
    if system != "darwin":
        return None
    return [CAFFEINATE, "-dims", "-w", str(pid or os.getpid())]


def execution_state(flags: int) -> int:
    """Windows' SetThreadExecutionState for this thread: the state before, or 0 when Windows refused."""
    import ctypes

    call = ctypes.windll.kernel32.SetThreadExecutionState
    call.argtypes, call.restype = [ctypes.c_uint], ctypes.c_uint
    return call(flags)


@contextmanager
def awake(system: str = sys.platform, popen: Callable[..., subprocess.Popen] = subprocess.Popen,
          state: Callable[[int], int] = execution_state) -> Iterator[None]:
    """The computer stays awake inside this block. A keep-awake that can't start never stops the run."""
    if system == "win32":
        if not state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED):
            print("Couldn't keep Windows awake: it may sleep during the run.", file=sys.stderr)
        try:
            yield
        finally:
            state(ES_CONTINUOUS)  # sleep as usual again
        return
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
