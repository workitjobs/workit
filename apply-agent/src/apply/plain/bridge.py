"""The plain Workers' bridge: Apply's end of the channel the host relays talk to.

It listens on the Worker profiles folder's channel (plain/channel.py: workers.sock, mode 0600, or a named pipe on
Windows) before any Worker starts. Each Worker's relay connects and passes the check in both directions, names
its Worker, and passes on the extension's hello; the bridge checks
the origin, the protocol and the engine, answers welcome or refuse, and keeps one
Connection per Worker. A Connection calls ops (`call`) and hands events to subscribers
(`on`). Messages over 512 KiB go as chunks, since Chrome takes at most 1 MB from a host.
See apply-agent/docs/plain-workers/PROTOCOL.md.

The hello's `features` says what the extension's code can do (KAN-643): Chrome keeps running the
code it loaded, so a Worker can be older than Apply. One that knows `extension.reload`, in a
profile with Developer mode on (`reloadable`: without it Chrome disables a reloaded unpacked
extension), is told to load its files again (`chrome.runtime.reload()`: tabs, pages and sign-ins
stay) before it is welcomed, once; one still older is welcomed as `stale`, and Apply says so in
one line.
"""

import itertools
import json
import socket
import struct
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from apply.plain import channel
from apply.plain.extension import EXTENSION_ORIGINS, code_hash, engine_identity

PROTOCOL = 1
CHUNK_CHARS = 200_000  # characters of JSON per chunk: at most 800 KB of UTF-8, under Chrome's 1 MB
CHUNK_OVER = 512 * 1024  # a message longer than this goes as chunks
CALL_TIMEOUT = 60.0  # s an op may take, beyond its own timeout
FEATURES = 6  # the worker extension's feature level Apply expects (background.js FEATURES)
RELOADS_FROM = 2  # the first level with the extension.reload op
SETS_FROM = 3  # the first level that reads Apply's files from the vendor set its welcome names (KAN-645)
PACKAGED = "vendor"  # the root a package's own generated files are at (extension.package, KAN-839)
STORE_STALE = ("the worker extension from the Chrome Web Store holds other guard and page files than this Apply "
               "({has}, Apply's {want}), and Apply can't change a store copy's files. Chrome updates it from the store "
               "within hours: then restart the Worker. Or update WorkIt Auto Apply if it is the older one")
RELOAD_WAIT = 10.0  # s a reloading extension may take to close its port
OUT_OF_DATE = "Worker extension is out of date: quit Apply and start it again"
# How to bring a folder of other code up to date (KAN-764): Apply updates it before a Worker starts, once no Chrome loads it.
STALE_FIX = ("Once no Chrome loads that folder, start Apply again: it updates the folder before a Worker starts. Or run "
             "`uv run apply plain seed`.")


def features(hello: dict) -> int:
    """A hello's feature level: 1 for an extension from before KAN-643, which sends none."""
    level = hello.get("features")
    return level if isinstance(level, int) else 1


class PortError(PlaywrightError):
    """An op the worker extension answered with an error; `kind` is its name (PROTOCOL.md)."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class PortTimeoutError(PortError, PlaywrightTimeoutError):
    """An op, or an auto-wait, that ran out of time."""

    def __init__(self, message: str, kind: str = "TimeoutError"):
        PortError.__init__(self, kind, message)


class WorkerGone(PortError):
    """The Worker's connection closed (its Chrome quit, or the extension restarted)."""

    def __init__(self, message: str):
        super().__init__("WorkerGone", message)


class Refused(Exception):
    """Apply refused a Worker's hello."""


class BridgeBusy(Exception):
    """Another Apply process is listening on the socket."""


def _frame(message: dict) -> bytes:
    body = json.dumps(message, ensure_ascii=False).encode()
    return struct.pack("=I", len(body)) + body


def _read_frame(sock: socket.socket) -> dict | None:
    head = _exact(sock, 4)
    if not head:
        return None
    body = _exact(sock, struct.unpack("=I", head)[0])
    return json.loads(body) if body is not None else None


def _exact(sock: socket.socket, size: int) -> bytes | None:
    data = bytearray()
    while len(data) < size:
        more = sock.recv(min(size - len(data), 1 << 20))
        if not more:
            return None
        data += more
    return bytes(data)


class _Slot:
    def __init__(self):
        self.done = threading.Event()
        self.message: dict | None = None


class Connection:
    """One Worker's port: `call` runs an op and returns its value; `on` subscribes to events."""

    def __init__(self, worker: int, sock: socket.socket, hello: dict, relay: dict):
        self.worker, self.hello, self.relay = worker, hello, relay
        self.stale = False  # its extension is older than Apply expects (the bridge sets it)
        self._sock = sock
        self._send_lock = threading.Lock()
        self._ids = itertools.count(1)
        self._pending: dict[int, _Slot] = {}
        self._handlers: dict[str, list[Callable[[dict], None]]] = {}
        self.closed = threading.Event()
        self.vendor: str | None = None  # the vendor set its welcome named, if its extension takes one

    def send(self, message: dict) -> None:
        text = json.dumps(message, ensure_ascii=False)
        with self._send_lock:
            if len(text.encode()) <= CHUNK_OVER:
                self._sock.sendall(_frame(message))
                return
            pieces = [text[i:i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)]
            for seq, data in enumerate(pieces):
                self._sock.sendall(_frame({"type": "chunk", "id": message.get("id", 0), "seq": seq,
                                           "of": len(pieces), "data": data}))

    def call(self, op: str, timeout: float | None = None, **params):
        """The value of op `op` with `params`. Raises PortError with the extension's error,
        PortTimeoutError past `timeout` s (default: the op's own timeout plus a minute), or
        WorkerGone when the Worker's connection closes."""
        if self.closed.is_set():
            raise WorkerGone(f"plain Worker {self.worker + 1} is gone")
        number = next(self._ids)
        slot = self._pending[number] = _Slot()
        try:
            self.send({"type": "call", "id": number, "op": op, "params": params})
            wait = timeout if timeout is not None else params.get("timeout", 0) / 1000 + CALL_TIMEOUT
            if not slot.done.wait(wait):
                raise PortTimeoutError(f"{op}: no answer from plain Worker {self.worker + 1} in {wait:.0f} s")
        finally:
            self._pending.pop(number, None)
        message = slot.message
        if message is None:
            raise WorkerGone(f"plain Worker {self.worker + 1} closed during {op}")
        if message["type"] == "error":
            error = message.get("error") or {}
            kind, text = error.get("name", "Crash"), error.get("message", "")
            if kind == "TimeoutError":
                raise PortTimeoutError(f"{op}: {text}")
            raise PortError(kind, f"{op}: {text}")
        return message.get("value")

    def on(self, event: str, handler: Callable[[dict], None]) -> None:
        """Call `handler(message)` for each event named `event` (on the reader thread: keep it short)."""
        self._handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable[[dict], None]) -> None:
        if handler in self._handlers.get(event, []):
            self._handlers[event].remove(handler)

    def _read(self) -> None:
        try:
            while (message := _read_frame(self._sock)) is not None:
                if message.get("type") in ("result", "error"):
                    slot = self._pending.get(message.get("id"))
                    if slot:
                        slot.message = message
                        slot.done.set()
                elif message.get("type") == "event":
                    for handler in list(self._handlers.get(message.get("event"), [])):
                        try:
                            handler(message)
                        except Exception:
                            pass
        except OSError:
            pass
        finally:
            self.closed.set()
            for slot in list(self._pending.values()):
                slot.done.set()
            for handler in list(self._handlers.get("close", [])):
                try:
                    handler({"type": "event", "event": "close"})
                except Exception:
                    pass

    def close(self) -> None:
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._sock.close()


class Bridge:
    """Listens for the Workers' relays. `start` before launching a Worker; `wait_for(k)` then
    gives that Worker's Connection once its hello passed."""

    def __init__(self, path: Path, engine: dict | None = None, expects: int = FEATURES):
        self.path = path
        self._engine = engine
        # The vendor set this Apply wrote into the Workers' extension folder ("vendor/sets/<id>"), named
        # in each welcome: a Worker whose extension takes it is never refused for another checkout's engine.
        self.vendor: str | None = None
        # The id of this Apply's packaged files (extension.packaged_files): a package whose hello names the same
        # id has them built in, and is welcomed to its own (PACKAGED); a store copy naming another is refused.
        self.packaged: str | None = None
        self.folder: Path | None = None  # the folder the Workers load the extension from (PlainWorkers.prepare)
        self.expects = expects  # the feature level a Worker's extension must have not to be stale
        # This Apply's worker extension code (extension.code_hash) and the folder Worker k loads it from (PlainWorkers):
        # a Worker whose folder holds other code is stale too, whatever its feature level says (KAN-764).
        self.code: str | None = None
        self.loaded: Callable[[int], Path | None] = lambda worker: None
        self._told: set[int] = set()  # Workers told their folder holds other code
        self._reloaded: set[int] = set()  # Workers told to reload once already
        self.reloadable: Callable[[int], bool] = lambda worker: False  # PlainWorkers: its profile's Developer mode
        self._warned = False
        self._server: channel.Listener | None = None
        self._workers: dict[int, Connection] = {}
        self._refused: dict[int, str] = {}
        self._changed = threading.Condition()

    @property
    def engine(self) -> dict:
        if self._engine is None:
            self._engine = engine_identity()
        return self._engine

    def start(self) -> None:
        if self._server:
            return
        try:
            self._server = channel.listen(self.path)
        except channel.Busy:
            raise BridgeBusy(f"another Apply is driving plain Workers on {self.path}") from None
        self.engine  # noqa: B018 - read the engine's identity before the first hello
        threading.Thread(target=self._accept, name="plain-bridge", daemon=True).start()

    def stop(self) -> None:
        server, self._server = self._server, None
        if server:
            server.close()
        for connection in list(self._workers.values()):
            connection.close()
        self._workers.clear()

    def _accept(self) -> None:
        while (server := self._server) is not None:
            try:
                sock = server.accept()
            except OSError:
                return
            threading.Thread(target=self._greet, args=(sock, server), daemon=True).start()

    def _greet(self, sock: socket.socket, server: channel.Listener) -> None:
        if not server.greet(sock):  # it doesn't know this channel's secret: no other message (channel.py)
            sock.close()
            return
        try:
            relay = _read_frame(sock)
            hello = _read_frame(sock)
        except (OSError, ValueError):
            sock.close()
            return
        if not relay or relay.get("type") != "relay" or not hello:
            sock.close()
            return
        worker = int(relay.get("worker", 0))
        level = features(hello)
        reason = self.refusal(relay, hello, engine=False)
        if not reason and RELOADS_FROM <= level < self.expects and worker not in self._reloaded and self.reloadable(worker):
            self._reloaded.add(worker)
            self._reload(worker, sock)  # it says hello again, with the code on disk: maybe one that takes a set
            return
        reason = reason or self.refusal(relay, hello)
        if reason:
            try:
                sock.sendall(_frame({"type": "refuse", "reason": reason}))
            except OSError:
                pass
            sock.close()
            with self._changed:
                self._refused[worker] = reason
                self._changed.notify_all()
            return
        connection = Connection(worker, sock, hello, relay)
        other = self.other_code(worker)
        connection.stale = level < self.expects or other is not None
        if other is not None and worker not in self._told:
            self._told.add(worker)
            print(f"Plain Worker {worker + 1}: {OUT_OF_DATE}. Its worker extension, in {other}, holds other code than "
                  f"this Apply's, so guard and fill fixes since then don't reach it. {STALE_FIX}", file=sys.stderr)
        elif connection.stale and not self._warned:
            self._warned = True
            print(f"Plain Worker {worker + 1}'s extension has features {level}, Apply expects {self.expects}. "
                  f"{OUT_OF_DATE}.", file=sys.stderr)
        welcome = {"type": "welcome", "worker": worker, "protocol": PROTOCOL}
        if self.packaged and hello.get("packaged") == self.packaged:
            welcome["vendor"] = PACKAGED  # its package holds this Apply's files: no set to write into a store copy
        elif self.vendor and features(hello) >= SETS_FROM:
            welcome["vendor"] = self.vendor
        connection.vendor = welcome.get("vendor")
        connection.send(welcome)
        with self._changed:
            old = self._workers.get(worker)
            self._workers[worker] = connection
            self._refused.pop(worker, None)
            self._changed.notify_all()
        if old:
            old.close()
        connection._read()
        with self._changed:
            if self._workers.get(worker) is connection:
                del self._workers[worker]
            self._changed.notify_all()

    def other_code(self, worker: int) -> Path | None:
        """The folder Worker `worker` loads the worker extension from, when its code isn't this Apply's; else None."""
        if not self.code:
            return None
        try:
            folder = self.loaded(worker)
            return folder if folder and code_hash(folder) != self.code else None
        except OSError:
            return None

    def _reload(self, worker: int, sock: socket.socket) -> None:
        """Tell Worker `worker`'s extension to reload (it answers, then its port closes), never
        registering this connection: wait_for gets the one after."""
        try:
            sock.sendall(_frame({"type": "welcome", "worker": worker, "protocol": PROTOCOL}))
            sock.sendall(_frame({"type": "call", "id": 1, "op": "extension.reload", "params": {}}))
            sock.settimeout(RELOAD_WAIT)
            while _read_frame(sock) is not None:
                pass
        except (OSError, ValueError):
            pass
        finally:
            sock.close()

    def reload(self, worker: int, timeout: float = 30.0) -> Connection:
        """Reload Worker `worker`'s extension from its folder now; its next Connection, once its
        hello passed. Its tabs, pages, sign-ins and guards stay (ops/guard.js: keepAcrossReload, KAN-657).
        A PortPage holds the old Connection: make a new one on the same tab."""
        old = self._workers.get(worker)
        if old is None:
            raise WorkerGone(f"plain Worker {worker + 1} is gone")
        if features(old.hello) < RELOADS_FROM or not self.reloadable(worker):
            raise PortError("NoReload", f"plain Worker {worker + 1}'s extension can't be reloaded in place")
        try:
            old.call("extension.reload", timeout=5)
        except WorkerGone:
            pass
        with self._changed:
            done = self._changed.wait_for(lambda: self._workers.get(worker) not in (None, old) or worker in self._refused,
                                          timeout)
            if worker in self._refused:
                raise Refused(self._refused.pop(worker))
            if not done:
                raise TimeoutError(f"no hello from plain Worker {worker + 1} in {timeout:.0f} s after its reload")
            return self._workers[worker]

    def refusal(self, relay: dict, hello: dict, engine: bool = True) -> str:
        """Why a Worker's hello is refused, or "" to welcome it (`engine`: also for its Fill engine)."""
        if relay.get("origin") not in EXTENSION_ORIGINS:
            return f"only the worker extension ({', '.join(EXTENSION_ORIGINS)}) may connect, not {relay.get('origin')!r}"
        if hello.get("type") != "hello" or hello.get("protocol") != PROTOCOL:
            return f"protocol {hello.get('protocol')!r}, Apply speaks {PROTOCOL}"
        has = hello.get("packaged")
        if has and hello.get("installType") not in (None, "development") and has != self.packaged:
            return STORE_STALE.format(has=has, want=self.packaged or "none")  # fails closed: no files Apply can check
        if not engine or (self.vendor and features(hello) >= SETS_FROM):
            return ""  # it reads Apply's own set, which holds this Apply's engine
        has = hello.get("engine") or {}
        if has.get("sha256") != self.engine["sha256"]:
            where = f" in {self.folder}" if self.folder else ""
            return (f"the worker extension has Fill engine {has.get('version') or 'none'}, Apply has "
                    f"{self.engine['version']}: its code{where} is from before vendor sets (KAN-645). Update that "
                    "checkout (`git pull`) and restart the Worker; until then, `uv run apply plain prepare` there")
        return ""

    def wait_for(self, worker: int, timeout: float = 30.0) -> Connection:
        """Worker `worker`'s Connection, once its hello passed. Raises Refused with the
        reason, or TimeoutError when no hello came in `timeout` s."""
        with self._changed:
            done = self._changed.wait_for(lambda: worker in self._workers or worker in self._refused, timeout)
            if worker in self._refused:
                raise Refused(self._refused.pop(worker))
            if not done:
                raise TimeoutError(f"no hello from plain Worker {worker + 1} in {timeout:.0f} s")
            return self._workers[worker]

    def connection(self, worker: int) -> Connection | None:
        return self._workers.get(worker)
