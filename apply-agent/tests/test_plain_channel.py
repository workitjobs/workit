"""The channel between Apply and its hosts and its MCP server (apply.plain.channel; KAN-929, P4 of
docs/windows_desktop.md): the check in both directions before any message, and the Windows entry's named pipe. No
browser: in CI. Each test names the fault that it alone turns red.

Each test runs on the entries its OS has. macOS and Linux: the Unix socket ("socket"), and "connections", the
Windows entry's own classes (ConnectionListener, Messages) over multiprocessing connections on a Unix socket in
place of the pipe. Windows: the named pipe ("pipe")."""

import os
import secrets
import shutil
import socket
import struct
import tempfile
import threading
import time
from contextlib import suppress
from pathlib import Path

import pytest

from apply.plain import channel

ENTRIES = ["socket", "connections"] if os.name == "posix" else ["pipe"]


@pytest.fixture(params=ENTRIES)
def entry(request) -> str:
    return request.param


@pytest.fixture
def folder():
    """A short folder: macOS caps a Unix socket's path at 104 bytes, and pytest's own folders are longer."""
    made = Path(tempfile.mkdtemp(prefix="apc-", dir="/tmp" if os.name == "posix" else None))
    yield made
    shutil.rmtree(made, ignore_errors=True)


def listening(entry: str, path: Path) -> channel.Listener:
    if entry == "socket":
        return channel.SocketListener(path)
    if entry == "connections":
        return channel.ConnectionListener(str(path), "AF_UNIX", path)
    return channel.listen(path)


def opened(entry: str, path: Path):
    """A connection that skips the check: a stranger's, until `channel.prove` checks it."""
    if entry == "socket":
        stream = channel.open_socket(path)
    elif entry == "connections":
        stream = channel.open_connection(str(path), "AF_UNIX")
    else:
        stream = channel.open_connection(channel.pipe_name(path), "AF_PIPE")
    stream.settimeout(5)
    return stream


def bare(entry: str, path: Path):
    """A listener that knows no secret, at the channel's address: an impostor's. `accept()` gives a stream."""
    if entry == "socket":
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        server.listen(1)
        return type("Bare", (), {"accept": lambda self: server.accept()[0], "close": lambda self: server.close()})()
    from multiprocessing.connection import Listener

    connections = Listener(str(path) if entry == "connections" else channel.pipe_name(path),
                           "AF_UNIX" if entry == "connections" else "AF_PIPE")
    return type("Bare", (), {"accept": lambda self: channel.Messages(connections.accept()),
                             "close": lambda self: connections.close()})()


@pytest.fixture
def listener(entry, folder):
    made = listening(entry, folder / "c.sock")
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


def test_a_message_goes_both_ways_once_both_ends_know_the_secret(entry, listener):
    """Fault: the check fails between two ends that both know the secret, or a frame comes through cut. The Bridge
    reads a frame's 4-byte head, then its body, and the host sends both as one of the pipe's whole messages, so
    Messages must keep what a read didn't take."""
    thread, done = greeted(listener)
    client = channel.prove(opened(entry, listener.path), listener.path)
    thread.join(5)
    server = done["stream"]
    server.settimeout(5)
    client.settimeout(5)  # a frame cut short fails here, never waits for good
    for sender, reader, body in ((client, server, b'{"type": "hello"}'),
                                 (server, client, secrets.token_bytes(3 * 1024 * 1024))):  # over Chrome's 1 MB
        threading.Thread(target=sender.sendall, args=(struct.pack("=I", len(body)) + body,), daemon=True).start()
        head = channel._exact(reader, 4)
        assert channel._exact(reader, struct.unpack("=I", head)[0]) == body


def test_a_client_without_the_secret_is_refused_and_told_nothing(entry, listener):
    """Fault: greet lets in a client that can't answer the challenge. Then a program that isn't Apply's host could
    drive a Worker's Chrome (on Windows, any user can open a named pipe)."""
    thread, done = greeted(listener)
    stranger = opened(entry, listener.path)
    channel._exact(stranger, channel.SIZE)  # the challenge
    stranger.sendall(secrets.token_bytes(2 * channel.SIZE))  # a guess at the answer, and its own challenge
    thread.join(5)
    assert done["stream"] is None
    assert stranger.recv(channel.SIZE) == b""  # closed: no proof back, and no other message


def test_a_client_that_says_nothing_is_dropped(entry, listener, monkeypatch):
    """Fault: greet waits for an answer for good (the pipe's reads take no timeout but the poll Messages adds), so a
    stranger that opens the channel and says nothing holds a Bridge thread for ever."""
    monkeypatch.setattr(channel, "GREET_WAIT", 0.3)
    thread, done = greeted(listener)
    silent = opened(entry, listener.path)
    thread.join(5)
    assert not thread.is_alive() and done["stream"] is None
    silent.close()


def test_a_listener_without_the_secret_is_refused_by_the_client(entry, folder):
    """Fault: connect trusts a listener that can't prove it knows the secret. A Worker outlives its Apply, so another
    program could take the channel's address and drive the Worker's Chrome through its next host."""
    path = folder / "c.sock"
    channel.secret_path(path).write_text(secrets.token_hex(channel.SIZE))  # what Apply wrote before it went
    impostor = bare(entry, path)

    def answer():
        stream = impostor.accept()
        stream.sendall(secrets.token_bytes(channel.SIZE))  # a challenge
        channel._exact(stream, 2 * channel.SIZE)
        stream.sendall(secrets.token_bytes(channel.SIZE))  # a proof it can't compute

    threading.Thread(target=answer, daemon=True).start()
    try:
        with pytest.raises(channel.NotApply):
            channel.prove(opened(entry, path), path)
    finally:
        impostor.close()


def test_an_old_answer_fails_a_new_challenge(entry, listener):
    """Fault: the listener's challenge isn't new for each connection, so a program that saw one exchange could
    connect again with the answer it saw."""
    secret = bytes.fromhex(channel.secret_path(listener.path).read_text())
    thread, done = greeted(listener)
    seen = opened(entry, listener.path)
    answer = channel._mac(secret, b"client", channel._exact(seen, channel.SIZE)) + secrets.token_bytes(channel.SIZE)
    seen.sendall(answer)
    thread.join(5)
    assert done["stream"] is not None  # the right answer passes

    thread, done = greeted(listener)
    again = opened(entry, listener.path)
    channel._exact(again, channel.SIZE)
    again.sendall(answer)  # the answer it saw, to a new challenge
    thread.join(5)
    assert done["stream"] is None


def test_a_drive_reads_its_lines_through_the_channel(entry, listener):
    """Fault: a line read (`makefile`, as the ToolServer and mcp.py read each tool call) loses or joins lines that
    came in separate messages, or stops at a message's end."""
    thread, done = greeted(listener)
    client = channel.prove(opened(entry, listener.path), listener.path)
    thread.join(5)
    client.sendall(b'{"name": "browser_click"}\n{"na')
    client.sendall(b'me": "browser_type"}\n')
    lines = done["stream"].makefile("r", encoding="utf-8")
    assert [lines.readline(), lines.readline()] == ['{"name": "browser_click"}\n', '{"name": "browser_type"}\n']


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e != "connections"])
def test_a_close_wakes_a_reader_blocked_on_another_thread(entry, folder):
    """Fault: closing a connection leaves its reader blocked, so a Worker that Apply stops (Connection.close) keeps a
    thread waiting for good. On Windows a close cancels the pipe's pending read (Python raises RuntimeError there).
    Not on "connections": on macOS and Linux only a socket's shutdown wakes a blocked read, and those have none."""
    listener = listening(entry, folder / "c.sock")
    try:
        thread, done = greeted(listener)
        client = channel.prove(opened(entry, listener.path), listener.path)
        thread.join(5)
        server = done["stream"]
        read = threading.Thread(target=server.recv, args=(1,), daemon=True)
        read.start()
        server.shutdown(socket.SHUT_RDWR)
        server.close()
        read.join(5)
        assert not read.is_alive()
        client.close()
    finally:
        listener.close()


def test_a_closed_channel_listens_again_in_the_same_process(entry, folder):
    """Fault: a channel closed while its accept is blocked can't be made again on the same path in the same process
    (a run after the seed's setup gets Busy). On Windows the blocked accept holds the pipe, which only the next test's
    wake frees; macOS and Linux free a socket's path as it closes, so this fault shows on Windows."""
    path = folder / "c.sock"
    first = listening(entry, path)

    def blocked():  # as the Bridge's accept thread; what its accept gives is the next test's
        with suppress(OSError):
            first.accept()

    threading.Thread(target=blocked, daemon=True).start()
    first.close()
    second = listening(entry, path)
    try:
        thread, done = greeted(second)
        channel.prove(opened(entry, path), path)
        thread.join(5)
        assert done["stream"] is not None
    finally:
        second.close()


def test_close_wakes_an_accept_and_waits_till_it_gave_the_pipe_back(folder, monkeypatch):
    """Fault: ConnectionListener.close doesn't wake its blocked accept, returns before the woken accept closed its
    end of the pipe, or the woken accept hands close's own connection on as a new one. On Windows a pipe's accept
    stays blocked when the listener closes, and Windows makes no pipe of that name while the woken accept's end is
    open, so a channel made again at once on that path is Busy. macOS wakes a blocked accept as its socket closes, so
    a fake listener plays Windows' pipe here: only a connection wakes it, and its thread takes a while to run."""
    waiting, arrived, gave_back = threading.Event(), threading.Event(), threading.Event()

    class Pipe:  # multiprocessing's Listener as Windows' named pipe behaves
        def __init__(self, address, family):
            pass

        def accept(self):
            waiting.set()
            arrived.wait()
            time.sleep(0.2)  # timed on purpose: the woken thread runs again later than close's own steps take
            return Woken()

        def close(self):
            pass  # wakes nothing

    class Woken:  # the accept's end of close's own connection
        def close(self):
            gave_back.set()

    class Gone:  # close's end of it
        def close(self):
            pass

    monkeypatch.setattr("multiprocessing.connection.Listener", Pipe)
    monkeypatch.setattr(channel, "open_connection", lambda address, family: (arrived.set(), Gone())[1])
    listener = channel.ConnectionListener(r"\\.\pipe\test", "AF_PIPE", folder / "c.sock")
    got = {}

    def accept():
        try:
            got["connection"] = listener.accept()
        except OSError:
            got["connection"] = None

    accepting = threading.Thread(target=accept, daemon=True)
    accepting.start()
    waiting.wait(5)
    listener.close()
    assert gave_back.is_set()  # before close returned
    accepting.join(5)
    assert got == {"connection": None}  # it raised: close's own connection is no new one
