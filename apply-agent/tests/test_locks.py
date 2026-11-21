"""File locks across processes, with no `fcntl`, which Windows lacks (apply.locks; KAN-929, P1 of
docs/windows_desktop.md). Each test starts a second Python process: a lock that holds only inside one process
passes neither."""

import ast
import subprocess
import sys
import threading
from pathlib import Path

from apply import locks
from apply.tracker import FileTracker

# A second Apply process that writes the Tracker and stops between its read and its save, until told to go on.
HOLDER = """
import sys
from pathlib import Path

from apply import tracker

save = tracker.FileTracker._save


def save_when_told(self):
    print("read", flush=True)
    sys.stdin.readline()
    save(self)


tracker.FileTracker._save = save_when_told
tracker.FileTracker(Path(sys.argv[1])).add_request("https://holder.example/job")
"""


def test_a_tracker_write_waits_for_another_process_and_both_writes_land(tmp_path):
    """Fault: the lock does nothing, or `held` doesn't wait. This process's write then goes in while the other
    process holds the Tracker it read, and the other one's save drops it."""
    path = tmp_path / "tracker.json"
    holder = subprocess.Popen([sys.executable, "-c", HOLDER, str(path)], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline() == "read\n"
        with locks.tried(path.with_suffix(".lock")) as mine:
            assert not mine  # the try-once lock (`apply repair`'s) sees the other process's lock too
        writer = threading.Thread(target=FileTracker(path).add_request, args=("https://mine.example/job",),
                                  daemon=True)
        writer.start()
        writer.join(0.5)  # a write that takes no lock is done well within this
        assert writer.is_alive()
        holder.stdin.write("\n")
        holder.stdin.flush()
        assert holder.wait(10) == 0
        writer.join(10)
    finally:
        holder.kill()
    assert FileTracker(path).requests() == ["https://holder.example/job", "https://mine.example/job"]


def test_no_module_of_apply_imports_fcntl():
    """Fault: a module imports `fcntl` again. Windows has none, so no command, window or seed setup would start
    there: tracker.py's import stopped all three. It reads the source, since portalocker itself imports `fcntl` on
    macOS and Linux, so an import with `fcntl` blocked fails there whatever Apply does."""
    source = Path(locks.__file__).parent
    found = []
    for path in sorted(source.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name.split(".")[0] == "fcntl" for name in names):
                found.append(f"{path.relative_to(source)}:{node.lineno}")
    assert found == []
