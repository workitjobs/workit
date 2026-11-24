"""The channel between Apply and its hosts and its MCP server (apply.plain.channel; KAN-929, P4 of
docs/windows_desktop.md): the check in both directions before any message. No browser: in CI. Each test names the
fault that it alone turns red."""

import os
import secrets
import shutil
import socket
import tempfile
import threading
from pathlib import Path

import pytest

from apply.plain import channel


@pytest.fixture
def folder():
    """A short folder: macOS caps a Unix socket's path at 104 bytes, and pytest's own folders are longer."""
    made = Path(tempfile.mkdtemp(prefix="apc-", dir="/tmp" if os.name == "posix" else None))
    yield made
    shutil.rmtree(made, ignore_errors=True)


@pytest.fixture
def listener(folder):
    made = channel.Listener(folder / "c.sock")
    yield made
    made.close()


def greeted(listener) -> tuple[threading.Thread, dict]:
    """The next connection, checked in a thread of its own as the Bridge checks it: `done["stream"]` once it passed,
    None (and closed) once it failed."""
    done = {}

    def run():
        stream = listener.accept()
        if listener.greet(stream):
            done["stream"] = stream
        else:
            stream.close()
            done["stream"] = None

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, done


def raw(path: Path) -> socket.socket:
    """A connection that skips the check: a stranger's."""
    stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stream.connect(str(path))
    stream.settimeout(5)
    return stream


def test_a_message_goes_both_ways_once_both_ends_know_the_secret(listener):
    """Fault: the check fails between two ends that both know the secret, or a long message comes through cut."""
    thread, done = greeted(listener)
    client = channel.connect(listener.path)
    thread.join(5)
    server = done["stream"]
    client.sendall(b"ping")
    assert channel._exact(server, 4) == b"ping"
    big = secrets.token_bytes(3 * 1024 * 1024)  # over Chrome's 1 MB: the Bridge sends such messages as chunks
    threading.Thread(target=server.sendall, args=(big,), daemon=True).start()
    assert channel._exact(client, len(big)) == big


def test_a_client_without_the_secret_is_refused_and_told_nothing(listener):
    """Fault: greet lets in a client that can't answer the challenge. Then a program that isn't Apply's host could
    drive a Worker's Chrome (on Windows, any user can open a named pipe)."""
    thread, done = greeted(listener)
    stranger = raw(listener.path)
    channel._exact(stranger, channel.SIZE)  # the challenge
    stranger.sendall(secrets.token_bytes(2 * channel.SIZE))  # a guess at the answer, and its own challenge
    thread.join(5)
    assert done["stream"] is None
    assert stranger.recv(channel.SIZE) == b""  # closed: no proof back, and no other message


def test_a_listener_without_the_secret_is_refused_by_the_client(folder):
    """Fault: connect trusts a listener that can't prove it knows the secret. A Worker outlives its Apply, so another
    program could take the channel's address and drive the Worker's Chrome through its next host."""
    path = folder / "c.sock"
    channel.secret_path(path).write_text(secrets.token_hex(channel.SIZE))  # what Apply wrote before it went
    impostor = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    impostor.bind(str(path))
    impostor.listen(1)

    def answer():
        stream = impostor.accept()[0]
        stream.sendall(secrets.token_bytes(channel.SIZE))  # a challenge
        channel._exact(stream, 2 * channel.SIZE)
        stream.sendall(secrets.token_bytes(channel.SIZE))  # a proof it can't compute

    threading.Thread(target=answer, daemon=True).start()
    try:
        with pytest.raises(channel.NotApply):
            channel.connect(path)
    finally:
        impostor.close()


def test_an_old_answer_fails_a_new_challenge(listener):
    """Fault: the listener's challenge isn't new for each connection, so a program that saw one exchange could
    connect again with the answer it saw."""
    secret = bytes.fromhex(channel.secret_path(listener.path).read_text())
    thread, done = greeted(listener)
    seen = raw(listener.path)
    answer = channel._mac(secret, b"client", channel._exact(seen, channel.SIZE)) + secrets.token_bytes(channel.SIZE)
    seen.sendall(answer)
    thread.join(5)
    assert done["stream"] is not None  # the right answer passes

    thread, done = greeted(listener)
    again = raw(listener.path)
    channel._exact(again, channel.SIZE)
    again.sendall(answer)  # the answer it saw, to a new challenge
    thread.join(5)
    assert done["stream"] is None
