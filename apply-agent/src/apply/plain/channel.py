"""The channel between Apply and the processes that talk to it (KAN-929, P4 of docs/windows_desktop.md): each plain
Worker's host relay (bridge.Bridge, host.py) and Claude's MCP server for a drive (tools.ToolServer, mcp.py).

- macOS and Linux: a Unix socket file, mode 0600, bound under umask 0177.

Both ends prove that they know the channel's secret before any other message. A Listener writes a new random secret
beside its address when it starts (`secret_path`, mode 0600), `Listener.greet` checks each new connection, and
`connect` checks the listener. So a stranger can't connect, a stranger can't pass for Apply to a host whose Apply
has gone (Workers outlive it), and an old answer fails a new challenge:

    listener -> client:   a random challenge (SIZE bytes)
    client   -> listener: HMAC(secret, "client" + challenge), then its own random challenge
    listener -> client:   HMAC(secret, "server" + the client's challenge)

Each side compares with hmac.compare_digest and closes on a wrong answer, or on none within GREET_WAIT s.

Stdlib only: the host (host.py) loads this file by its path, and imports nothing else of Apply's.
"""

import hashlib
import hmac
import os
import secrets
import socket
from pathlib import Path

SIZE = 32  # bytes of the secret, of each challenge and of each answer (HMAC-SHA256)
GREET_WAIT = 5.0  # s each side waits for the other's part of the check


class Busy(Exception):
    """Another process listens on the channel's address."""


class NotApply(ConnectionError):
    """The listener didn't prove that it knows the channel's secret."""


def secret_path(path: Path) -> Path:
    """Where the channel at `path` keeps its secret: beside it (workers.sock: workers.key)."""
    return path.with_suffix(".key")


class Listener:
    """A channel's listening end at `path`. `accept` gives each new connection, which `greet` checks before any
    other message; `close` stops listening and removes the socket file and the secret."""

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
        self._secret = _new_secret(secret_path(path))  # only once this listener holds the address: never another's

    def accept(self) -> socket.socket:
        return self._server.accept()[0]

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
        self._server.close()
        self.path.unlink(missing_ok=True)
        secret_path(self.path).unlink(missing_ok=True)


def connect(path: Path) -> socket.socket:
    """A connection to the channel listening at `path`, once the listener proved that it knows the channel's secret.
    Raises FileNotFoundError when no channel's secret is there, NotApply when the listener fails the check."""
    secret = bytes.fromhex(secret_path(path).read_text().strip())
    stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        stream.connect(str(path))
        stream.settimeout(GREET_WAIT)
        challenge = _exact(stream, SIZE)
        if challenge is None:
            raise NotApply(f"the channel at {path} sent no challenge")
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
    with os.fdopen(os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
        file.write(secret.hex())
    os.replace(part, where)
    return secret
