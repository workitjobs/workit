"""The plain Workers' native messaging host: relays one worker extension's port to Apply.

Chrome starts it when the worker extension calls connectNative("com.workit.apply_worker"),
through the wrapper in that Worker profile's NativeMessagingHosts folder, which adds
`--socket <path> --worker <k>`; Chrome adds the caller's origin. It connects to Apply's
channel (plain/channel.py: the Unix socket at <path>, or its named pipe on Windows) and passes the
check in both directions with the secret beside <path>, says which Worker it is, then relays frames
both ways unchanged: Chrome's framing (a 4-byte length in native byte order, then UTF-8 JSON) is
also the channel's.

Stdlib only, run with `python3 -I`, so it needs nothing from Apply's environment.
"""

import importlib.util
import json
import os
import struct
import sys
import threading
from pathlib import Path

PROTOCOL = 1
TO_CHROME = 1024 * 1024  # Chrome's limit on a message from a host


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


def _channel():
    """channel.py beside this file, loaded by its path: the host imports nothing else of Apply's."""
    spec = importlib.util.spec_from_file_location("apply_channel", Path(__file__).with_name("channel.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> None:
    path = argv[argv.index("--socket") + 1]
    worker = int(argv[argv.index("--worker") + 1])
    origin = next((a for a in argv if a.startswith("chrome-extension://")), "")
    apply = _channel().connect(Path(path))
    first = json.dumps({"type": "relay", "protocol": PROTOCOL, "worker": worker, "origin": origin,
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
