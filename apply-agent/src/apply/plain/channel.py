"""The channel between Apply and the processes that talk to it (KAN-929, P4 of docs/windows_desktop.md): each plain
Worker's host relay (bridge.Bridge, host.py) and Claude's MCP server for a drive (tools.ToolServer, mcp.py). One API,
with an entry for each OS, picked by `system` (`listen`, `connect`):

- macOS and Linux: a Unix socket file at the channel's path, mode 0600, bound under umask 0177 (SocketListener).
- Windows: a named pipe, since Python on Windows has no AF_UNIX. multiprocessing.connection makes and opens it (the
  code that multiprocessing itself uses there), named from the same path (`pipe_name`): one profiles folder always
  gives the same pipe, and two folders never share one. Windows refuses to make a pipe a second time
  (FILE_FLAG_FIRST_PIPE_INSTANCE, which Python sets), so a second Apply on one folder is Busy (ConnectionListener).
  The pipe sends whole messages, and `Messages` reads them as the stream of bytes that the Bridge reads. Tests on
  macOS and Linux run ConnectionListener over a Unix socket in place of the pipe, so all but the pipe's own calls
  run in CI.

Both ends prove that they know the channel's secret before any other message. A Listener writes a new random secret
beside its path when it starts (`secret_path`, mode 0600), `Listener.greet` checks each new connection, and
`connect` (`prove`) checks the listener. So a stranger can't connect (any user can open a named pipe for reading),
a stranger can't pass for Apply to a host whose Apply has gone (Workers outlive it), and an old answer fails a new
challenge:

    listener -> client:   a random challenge (SIZE bytes)
    client   -> listener: HMAC(secret, "client" + challenge), then its own random challenge
    listener -> client:   HMAC(secret, "server" + the client's challenge)

Each side compares with hmac.compare_digest and closes on a wrong answer, or on none within GREET_WAIT s.

Stdlib only: a checkout's host (host.py) loads this file by its path, and imports nothing else of Apply's.
"""

import hashlib
import hmac
import io
import os
import secrets
import socket
import sys
import threading
from pathlib import Path
from typing import Self

SIZE = 32  # bytes of the secret, of each challenge and of each answer (HMAC-SHA256)
GREET_WAIT = 5.0  # s each side waits for the other's part of the check
SOCKET = "workers.sock"
SOCKET_PATH_MOST = 100  # macOS caps a Unix socket path at 104 bytes


class Busy(Exception):
    """Another process listens on the channel's address."""


class NotApply(ConnectionError):
    """The listener didn't prove that it knows the channel's secret."""


def socket_path(profiles: Path, system: str = sys.platform) -> Path:
    """The Workers' channel for the profiles folder `profiles`: the Bridge listens there, and each Worker's host
    finds it from its Chrome's profile (host.py). `profiles`/workers.sock, or, when that path is too long for a
    socket, one under /tmp/apply-<uid>/ (0700) named by a hash of `profiles`: always /tmp, never $TMPDIR, since
    the host runs in its Chrome's environment (on the Mac, launchd's: Chrome starts through `open`). On Windows
    the path only names the channel's pipe and holds its secret beside it (pipe_name), so it has no length to
    keep under, and Windows has no os.getuid."""
    path = profiles / SOCKET
    if system == "win32" or len(str(path).encode()) <= SOCKET_PATH_MOST:
        return path
    name = hashlib.sha256(str(profiles.resolve()).encode()).hexdigest()[:16]
    return Path("/tmp") / f"apply-{os.getuid()}" / f"{name}.sock"


def secret_path(path: Path) -> Path:
    """Where the channel at `path` keeps its secret: beside it (workers.sock: workers.key)."""
    return path.with_suffix(".key")


def pipe_name(path: Path) -> str:
    """Windows' named pipe for the channel at `path`: one name for one path, and none that two paths share."""
    return r"\\.\pipe\workit-apply-" + hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]


def listen(path: Path, system: str = sys.platform) -> "Listener":
    """The channel's listening end for `path`: a named pipe on Windows, else a Unix socket file at `path`."""
    if system == "win32":
        return ConnectionListener(pipe_name(path), "AF_PIPE", path)
    return SocketListener(path)


def connect(path: Path, system: str = sys.platform):
    """A connection to the channel listening at `path`, once the listener proved that it knows the channel's secret.
    Raises FileNotFoundError when no channel is there, NotApply when the listener fails the check."""
    opened = open_connection(pipe_name(path), "AF_PIPE") if system == "win32" else open_socket(path)
    return prove(opened, path)


class Listener:
    """A channel's listening end. `accept` gives each new connection, which `greet` checks before any other message;
    `close` stops listening and removes the secret."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._secret = _new_secret(secret_path(path))  # only once this listener holds the address: never another's

    def accept(self):
        raise NotImplementedError

    def greet(self, stream) -> bool:
        """Whether a new connection's other end proved that it knows the secret; this end then proves it too."""
        try:
            stream.settimeout(GREET_WAIT)
            challenge = secrets.token_bytes(SIZE)
            stream.sendall(challenge)
            answer = _exact(stream, 2 * SIZE)  # its proof, then its own challenge
            if answer is None or not hmac.compare_digest(answer[:SIZE], _mac(self._secret, b"client", challenge)):
                return False
            stream.sendall(_mac(self._secret, b"server", answer[SIZE:]))
            stream.settimeout(None)
        except OSError:
            return False
        return True

    def close(self) -> None:
        secret_path(self.path).unlink(missing_ok=True)


class SocketListener(Listener):
    """macOS and Linux: a Unix socket file at `path`."""

    def __init__(self, path: Path):
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
        super().__init__(path)

    def accept(self) -> socket.socket:
        return self._server.accept()[0]

    def close(self) -> None:
        self._server.close()
        self.path.unlink(missing_ok=True)
        super().close()


class ConnectionListener(Listener):
    """Windows: a named pipe through multiprocessing.connection ("AF_PIPE"), read through `Messages`. Tests on macOS
    and Linux run it over "AF_UNIX"."""

    def __init__(self, address: str, family: str, path: Path):
        from multiprocessing.connection import Listener as Connections

        self._address, self._family, self._closing = address, family, False
        self._accepting = threading.Lock()  # held while an accept waits: close waits for it to give its pipe back
        try:
            self._listener = Connections(address, family)
        except OSError as error:  # Windows: the pipe is made already (FILE_FLAG_FIRST_PIPE_INSTANCE)
            raise Busy(f"another process listens on {address} ({error})") from None
        super().__init__(path)

    def accept(self) -> "Messages":
        with self._accepting:
            connection = self._listener.accept()
            if self._closing:  # close's own connection, which woke this accept
                connection.close()
                raise OSError("the channel is closed")
        return Messages(connection)

    def close(self) -> None:
        self._closing = True
        try:  # a blocked accept doesn't wake when the listener closes: its pipe would stay, and none could be made again
            open_connection(self._address, self._family).close()
        except OSError:
            pass
        # The woken accept holds its end of the pipe till it closes it, and Windows makes no pipe of that name till
        # then: without this wait, a channel made again at once on the same path is Busy.
        if self._accepting.acquire(timeout=1):
            self._accepting.release()
        self._listener.close()
        super().close()


def open_socket(path: Path) -> socket.socket:
    """A Unix socket connection to `path`, before the check."""
    stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        stream.connect(str(path))
    except OSError:
        stream.close()
        raise
    return stream


def open_connection(address: str, family: str) -> "Messages":
    """A multiprocessing connection (a named pipe on Windows), before the check."""
    from multiprocessing.connection import Client

    return Messages(Client(address, family))


def prove(stream, path: Path):
    """`stream`, once the listener at `path` proved that it knows the channel's secret, which is read from beside
    `path`. Closes `stream` and raises NotApply when the listener fails the check."""
    try:
        stream.settimeout(GREET_WAIT)
        challenge = _exact(stream, SIZE)
        if challenge is None:
            raise NotApply(f"the channel at {path} sent no challenge")
        # Only now: a listener writes its new secret just after it takes the address, and challenges only after
        # that. Read sooner, a host that connected in between had the Apply before's secret.
        secret = bytes.fromhex(secret_path(path).read_text(encoding="utf-8").strip())
        mine = secrets.token_bytes(SIZE)
        stream.sendall(_mac(secret, b"client", challenge) + mine)
        proof = _exact(stream, SIZE)
        if proof is None or not hmac.compare_digest(proof, _mac(secret, b"server", mine)):
            raise NotApply(f"the channel at {path} did not prove that it knows its secret")
        stream.settimeout(None)
    except BaseException:
        stream.close()
        raise
    return stream


class Messages:
    """A multiprocessing connection, which sends whole messages (Windows' named pipe), as the stream of bytes that
    the Bridge and the ToolServer read: sendall, recv, settimeout, shutdown, close, makefile."""

    def __init__(self, connection):
        self._connection, self._buffer, self._timeout = connection, b"", None

    def sendall(self, data: bytes) -> None:
        self._connection.send_bytes(bytes(data))  # one at a time: the Bridge sends under its lock, as the pipe needs

    def recv(self, size: int) -> bytes:
        """Up to `size` bytes; b"" once either end closed. A close here cancels a read blocked on another thread,
        and Python then raises RuntimeError ("shouldn't get here"), not EOFError: every failure counts as closed."""
        while not self._buffer:
            try:
                ready = self._timeout is None or self._connection.poll(self._timeout)
                if ready:
                    self._buffer = self._connection.recv_bytes()
            except (EOFError, OSError, RuntimeError):
                return b""
            if not ready:
                raise TimeoutError("timed out")
        data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data

    def settimeout(self, seconds: float | None) -> None:
        self._timeout = seconds

    def shutdown(self, how: int | None = None) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def makefile(self, mode: str = "r", encoding: str | None = None) -> io.TextIOWrapper:
        """The stream as a text file for reading lines (the ToolServer, mcp.py)."""
        return io.TextIOWrapper(io.BufferedReader(_Raw(self)), encoding=encoding)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class _Raw(io.RawIOBase):
    def __init__(self, stream: Messages):
        self._stream = stream

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        data = self._stream.recv(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def _mac(secret: bytes, role: bytes, challenge: bytes) -> bytes:
    """One side's answer: the role keeps one side's answer from serving as the other's."""
    return hmac.new(secret, role + challenge, hashlib.sha256).digest()


def _exact(stream, size: int) -> bytes | None:
    """`size` bytes from `stream`, or None when it closed first."""
    data = b""
    while len(data) < size:
        more = stream.recv(size - len(data))
        if not more:
            return None
        data += more
    return data


def _new_secret(where: Path) -> bytes:
    """A new random secret in a file only this user may read, written whole: a reader never sees half of one."""
    secret = secrets.token_bytes(SIZE)
    part = where.with_name(where.name + ".part")
    part.unlink(missing_ok=True)
    with os.fdopen(os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as file:
        file.write(secret.hex())
    os.replace(part, where)
    return secret
