"""The plain Workers' native messaging host: relays one worker extension's port to Apply.

Chrome starts it when the worker extension calls connectNative("com.workit.apply_worker"),
through the wrapper that the host's manifest names (launcher.install_host), and gives it the
caller's origin. The host finds its Worker from the Chrome that started it (`browser_of`): the
nearest process above it that is a browser, whose `--user-data-dir` is that Worker's profile,
APPLY_PROFILES/plain-<k>. Its wrapper names no Worker: on Windows one registry key names one
wrapper for every Worker, and Chrome starts it through cmd.exe (docs/windows_desktop.md, P5).
It connects to that profiles folder's channel (channel.socket_path: a Unix socket, or a named
pipe on Windows), passes the check in both directions with the secret beside it, says which
Worker it is, then relays frames both ways unchanged: Chrome's framing (a 4-byte length in
native byte order, then UTF-8 JSON) is also the channel's.

Run with `python -I` by Apply's own Python, it imports the standard library and psutil (a
process's arguments, on every OS), and loads channel.py by its path: nothing else of Apply's.
The compiled app has no Python: its own program runs this relay when APP_FLAG comes first
(scripts/app_entry.py, W8).
"""

import importlib.util
import json
import os
import re
import struct
import sys
import threading
from pathlib import Path

import psutil

PROTOCOL = 1
APP_FLAG = "--worker-host"  # the compiled app's program, started with this first, is this relay
TO_CHROME = 1024 * 1024  # Chrome's limit on a message from a host
WORKER_PROFILE = re.compile(r"plain-([1-9][0-9]*)")  # Worker k's profile, plain-<k+1> (PlainWorkers.profile)


def read_exact(stream, size: int) -> bytes:
    data = b""
    while len(data) < size:
        more = stream.read(size - len(data)) if hasattr(stream, "read") else stream.recv(size - len(data))
        if not more:
            return b""
        data += more
    return data


def frames(stream):
    """Each frame (its 4-byte head and body) read from `stream`, until it ends."""
    while (head := read_exact(stream, 4)):
        body = read_exact(stream, struct.unpack("=I", head)[0])
        if len(body) != struct.unpack("=I", head)[0]:
            return
        yield head + body


def _channel(compiled: bool = "__compiled__" in globals()):
    """The channel (plain/channel.py). A checkout loads channel.py beside this file by its path, so the host imports
    nothing else of Apply's. The compiled app (W8) has no .py file: its program has the channel compiled in."""
    if compiled:
        from apply.plain import channel

        return channel
    spec = importlib.util.spec_from_file_location("apply_channel", Path(__file__).with_name("channel.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile_of(arguments: list[str] | None) -> Path | None:
    """The profile of a process with these arguments, when it is a browser (no `--type=`: not one of its helpers):
    its `--user-data-dir`. Else None."""
    if not arguments or any(a.startswith("--type=") for a in arguments):
        return None
    return next((Path(a.partition("=")[2]) for a in arguments if a.startswith("--user-data-dir=")), None)


def browser_of(pid: int) -> tuple[int, Path] | None:
    """The Chrome that started process `pid` (a native messaging host), and its profile: the nearest process above
    it that is a browser on a profile. Not only its parent: Chrome on Windows starts a .bat host through cmd.exe
    (Chromium's launch_context_win.cc). None when `pid` is gone or no browser is above it."""
    try:
        above = psutil.Process(pid).parents()
    except psutil.Error:
        return None
    for process in above:
        try:
            profile = profile_of(process.cmdline())
        except psutil.Error:  # gone, or another user's (launchd, a service): no Chrome of this user's
            continue
        if profile is not None:
            return process.pid, profile
    return None


def main(argv: list[str]) -> None:
    chrome = browser_of(os.getpid())
    worker = chrome and WORKER_PROFILE.fullmatch(chrome[1].name)
    if not worker:  # the seed's Chrome, say: on Windows every Chrome of this user's finds the host
        sys.exit(f"Apply's worker host: no plain Worker's Chrome started it ({chrome and chrome[1]})")
    profile = chrome[1]
    origin = next((a for a in argv if a.startswith("chrome-extension://")), "")
    channel = _channel()
    apply = channel.connect(channel.socket_path(profile.parent))
    first = json.dumps({"type": "relay", "protocol": PROTOCOL, "worker": int(worker[1]) - 1, "origin": origin,
                        "host_pid": os.getpid()}).encode()
    apply.sendall(struct.pack("=I", len(first)) + first)

    def up() -> None:  # Chrome -> Apply
        for frame in frames(sys.stdin.buffer):
            apply.sendall(frame)
        os._exit(0)

    threading.Thread(target=up, daemon=True).start()
    out = sys.stdout.buffer
    for frame in frames(apply):  # Apply -> Chrome
        if len(frame) - 4 > TO_CHROME:  # Chrome would close the port: Apply must chunk
            continue
        out.write(frame)
        out.flush()
    os._exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
