"""The worker extension's store copy (KAN-839): a running store copy keeps its built-in files when the Fill
engine on disk changes. It gets the engine again, never a vendor set its folder can't hold (the
adversarial review of 2026-11-14). No browser: in CI."""

import threading
from types import SimpleNamespace

from apply.plain.bridge import FEATURES, PACKAGED
from apply.plain.launcher import PlainWorker, PlainWorkers


class Calls:
    def __init__(self, vendor):
        self.vendor, self.calls = vendor, []
        self.hello = {"features": FEATURES}
        self.closed = threading.Event()

    def call(self, op, **params):
        self.calls.append(op)
        return {"name": params.get("name"), "bytes": 1}


def test_a_running_store_copy_gets_the_new_engine_and_never_a_vendor_set(tmp_path, monkeypatch):
    workers = PlainWorkers(tmp_path / "profiles", kind="testing")
    connection = Calls(vendor=PACKAGED)
    connection.engine_kept = "an older engine's sha256"
    workers.running[0] = PlainWorker(0, tmp_path / "p", SimpleNamespace(pid=1), connection, folder=None)
    monkeypatch.setattr(PlainWorkers, "prepare", lambda self, worker=None: setattr(self.bridge, "vendor", "vendor/sets/new"))
    workers.bridge._engine = {"version": "0.9.0+new", "sha256": "x"}
    said = workers.refresh(0)
    assert "vendor.use" not in connection.calls and connection.calls == ["cdp.keep"]
    assert said == ["the Fill engine changed on disk: its pages load 0.9.0+new now"]
    assert connection.vendor == PACKAGED
