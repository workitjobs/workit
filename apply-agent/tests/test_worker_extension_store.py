"""The worker extension's store version (KAN-839). Students run the copy the Chrome Web Store publishes, so a
change to what its package holds reaches them only through a new store release. No browser: in CI.

- store.json records, for its version, what that version's package holds (extension.store_stamp): the hash of
  the extension's own code and the set id of its built-in files (the guards, the fixed page functions,
  Playwright's injected script). A change to either fails here until store.json's version is bumped and its
  record updated: the reminder that the change needs a store release (apply-agent/CLAUDE.md).
- A running store copy keeps its built-in files when the Fill engine on disk changes: it gets the engine
  again, never a vendor set its folder can't hold."""

import json
import subprocess
import sys
import threading
from types import SimpleNamespace

from apply.plain import extension
from apply.plain.bridge import FEATURES, PACKAGED
from apply.plain.launcher import PlainWorker, PlainWorkers

RELEASE = """The worker extension's store package changed: {changed}.
Students' store copy keeps the old one until a new version is published on the Chrome Web Store. So:
  1. bump "version" in apply-agent/worker-extension/store.json;
  2. set its "code" to "{code}" and its "files" to "{files}";
  3. after merge, `uv run apply plain package` and upload the zip (docs/plain-workers/worker-extension-todo.md);
  4. release an app that needs it only once the store has published it."""


def test_store_json_records_what_its_version_holds():
    stamp = extension.store_stamp()
    recorded = json.loads(extension.STORE.read_text())
    changed = [f"{key} {recorded.get(key)} -> {stamp[key]}" for key in stamp if recorded.get(key) != stamp[key]]
    assert not changed, RELEASE.format(changed="; ".join(changed), **stamp)


def test_the_stamp_is_the_same_in_every_process_whatever_its_tokens():
    """Each Apply process makes the guards' tokens anew (submit_guard.TOKENS): two processes, one stamp."""
    stamp = "from apply.plain import extension; import json; print(json.dumps(extension.store_stamp()))"
    two = [subprocess.run([sys.executable, "-c", stamp], capture_output=True, text=True, check=True).stdout for _ in range(2)]
    assert two[0] == two[1] == json.dumps(extension.store_stamp()) + "\n"


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


def test_store_json_names_the_package_and_the_package_carries_its_licenses():
    meta = json.loads(extension.STORE.read_text())
    assert meta["name"] == "WorkIt Auto Apply Worker" and meta["version"]
    for name in extension.LICENSES:
        assert (extension.EXTENSION_DIR / name).is_file()
