"""The channel between Apply and the processes that talk to it (KAN-929, P4 of docs/windows_desktop.md): each plain
Worker's host relay (bridge.Bridge, host.py) and Claude's MCP server for a drive (tools.ToolServer, mcp.py).

- macOS and Linux: a Unix socket file, mode 0600, bound under umask 0177.

Stdlib only: the host (host.py) loads this file by its path, and imports nothing else of Apply's.
"""

import os
import socket
from pathlib import Path


class Busy(Exception):
    """Another process listens on the channel's address."""


class Listener:
    """A channel's listening end at `path`. `accept` gives each new connection; `close` stops listening and removes
    the socket file."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.name.startswith("apply-"):
            path.parent.chmod(0o700)
        if path.exists():
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.connect(str(path))
                raise Busy(f"another process listens on {path}")
            except (ConnectionRefusedError, FileNotFoundError):
                path.unlink(missing_ok=True)
            finally:
                probe.close()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        old = os.umask(0o177)
        try:
            server.bind(str(path))
        finally:
            os.umask(old)
        path.chmod(0o600)
        server.listen(16)
        self._server = server

    def accept(self) -> socket.socket:
        return self._server.accept()[0]

    def close(self) -> None:
        self._server.close()
        self.path.unlink(missing_ok=True)


def connect(path: Path) -> socket.socket:
    """A connection to the channel listening at `path`."""
    stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        stream.connect(str(path))
    except OSError:
        stream.close()
        raise
    return stream
