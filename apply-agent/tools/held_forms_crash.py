"""KAN-866 spike: do held forms survive a Worker's Chrome crash?

Repeats every case in docs/research/held-forms-after-a-crash.md. Research only: no product code calls it. Saved
forms only (the Fill engine's fixtures, served on 127.0.0.1 by `plain.demo.replay`, which refuses every POST),
filled as Test Person; nothing presses a Submit.

    uv run python tools/held_forms_crash.py chrome [--worker plain|cdp|both] [--end kill|quit|both] [--settle 5]
                                                   [--restore]
    uv run python tools/held_forms_crash.py reopen [--end kill|quit|both]

`chrome`: one Worker holds two filled saved forms in two tabs. Its Chrome is ended (SIGKILL, or Apply's own stop:
SIGTERM for a plain Worker, Playwright's close for a CDP Worker) and started again on the same profile as Apply
starts it. It prints which tabs came back and how many of each form's filled values came back.
- plain Worker: `PlainWorkers` (Chrome for Testing with --load-extension, plain/launcher.py's "testing"), so
  `--restore-last-session` and `--no-startup-window`, as Workers run.
- CDP Worker: Playwright's `launch_persistent_context` with `WorkerBrowsers.launch_options`, as `WorkerBrowsers.open`.

`--restore` starts Chrome again with its own session restore on (a plain Worker without `--no-startup-window`, a CDP
Worker with `--restore-last-session`): what Chrome kept, which Apply doesn't ask for today.

`reopen`: runs `tests/test_reopen.py -k killed` (Apply killed with two held fake Greenhouse forms in one plain
Worker, then `apply reopen`), with the Worker's Chrome ended by SIGKILL instead of the test's SIGTERM for `kill`.

On Linux (the Sandcastle container) Chrome for Testing needs two switches more, `LINUX`: it has no usable sandbox
there, and with `--no-startup-window` and no window it quits at once (exit 0), where the Mac keeps it running.
"""

import argparse
import ctypes
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import ExitStack
from pathlib import Path

from apply.browsers import WorkerBrowsers, chrome_pid
from apply.chrome_finder import FOR_TESTING_LINUX, chrome_for_testing
from apply.plain.demo import _filled, _saved, replay
from apply.plain.launcher import PlainWorkers
from apply.plain.page import PortPage

FORMS = ("lever-immuta", "lever-shieldai")  # one held form in each tab
LINUX = ("--no-sandbox", "--keep-alive-for-test") if sys.platform.startswith("linux") else ()
APPLY = Path(__file__).resolve().parents[1]
PR_SET_CHILD_SUBREAPER = 36  # prctl(2), Linux
BACK = 15.0  # s after the restart for restored tabs to load

# Every field a person could have filled: name or id, and its value (a box's checked state). Files and hidden
# fields are left out: Chrome never restores a file, and a hidden one is the page's.
SNAPSHOT = """() => { const out = {};
  for (const el of document.querySelectorAll('input, textarea, select')) {
    const type = (el.type || '').toLowerCase();
    if (['hidden', 'file', 'submit', 'button', 'reset', 'image'].includes(type)) continue;
    const key = (el.name || el.id || '') + (type === 'radio' || type === 'checkbox' ? '=' + el.value : '');
    if (!key) continue;
    const value = type === 'radio' || type === 'checkbox' ? el.checked : el.value;
    if (value !== '' && value !== false) out[key] = value;
  }
  return out; }"""


def compare(before: dict, after: dict | None) -> str:
    """How many of the values filled before the end are on the page after it."""
    if after is None:
        return f"tab not back (0 of {len(before)} values)"
    same = sum(1 for key, value in before.items() if after.get(key) == value)
    return f"tab back, {same} of {len(before)} values back"


def report(worker: str, end: str, before: dict, tabs: list[str], after: dict) -> None:
    print(f"[{worker}, {end}] tabs after the restart: {tabs}")
    for url, values in before.items():
        print(f"[{worker}, {end}] {url}: {compare(values, after.get(url))}")


class Workers(PlainWorkers):
    """Plain Workers as Apply starts them; once `restoring`, with no `--no-startup-window`, so Chrome's own session
    restore (`--restore-last-session`) opens the last session's tabs."""

    restoring = False

    def arguments(self, worker: int) -> list[str]:
        arguments = super().arguments(worker)
        return [a for a in arguments if a != "--no-startup-window"] if self.restoring else arguments


def plain_case(end: str, settle: float, restore: bool) -> None:
    """Two filled saved forms in two tabs of one plain Worker, its Chrome ended, then launched again as Apply does
    (`restore`: with Chrome's session restore)."""
    folder = Path(tempfile.mkdtemp(prefix="hfc-", dir="/tmp"))  # short: a socket path is capped at 104 bytes
    workers = Workers(folder, kind="testing", test_flags=LINUX)
    worker = "plain, restore" if restore else "plain"
    with ExitStack() as stack:
        served = [(target, *stack.enter_context(replay(_saved(target)))) for target in FORMS]
        try:
            running = workers.launch(0)
            connection, before = running.connection, {}
            for n, (target, url, real_url) in enumerate(served):
                if n == 0:
                    page = PortPage.first(connection)
                else:
                    page = PortPage(connection, connection.call("tabs.create", url="about:blank")["tab"])
                page.goto(url)
                print(f"[{worker}, {end}] {_filled(page, target, url, real_url)[0]}")
                before[url] = page.evaluate(SNAPSHOT)
            time.sleep(settle)  # Chrome writes its session on a timer
            if end == "kill":
                os.kill(running.pid, signal.SIGKILL)
                running.process.wait(10)
                workers.running.pop(0).connection.close()
            else:
                workers.stop(0)  # Apply's own stop: SIGTERM, then SIGKILL after 10 s
            workers.restoring = restore
            running = workers.launch(0)  # the same profile, the same command line
            time.sleep(BACK)
            tabs = running.connection.call("tabs.query")
            after = {}
            for tab in tabs:
                if tab["url"] in before:
                    after[tab["url"]] = PortPage(running.connection, tab["tab"]).evaluate(SNAPSHOT)
            report(worker, end, before, [t["url"] for t in tabs], after)
        finally:
            workers.stop_all()


def cdp_case(end: str, settle: float, restore: bool) -> None:
    """Two filled saved forms in two tabs of one CDP Worker, its Chrome ended, then launched again as Apply does
    (`restore`: with `--restore-last-session` added)."""
    from playwright.sync_api import Error, sync_playwright

    sys.path.insert(0, str(Path(__file__).parent))
    from held_forms_tabs import fill  # KAN-865's: the same fill on a Playwright page

    folder = Path(tempfile.mkdtemp(prefix="hfc-cdp-"))
    profile = folder / "worker-1"
    options = WorkerBrowsers(profiles=folder, headless=False, channel=None).launch_options(0)
    options["chromium_sandbox"] = not LINUX
    worker = "cdp, restore" if restore else "cdp"
    with ExitStack() as stack, sync_playwright() as playwright:
        served = [(target, *stack.enter_context(replay(_saved(target)))) for target in FORMS]
        context = playwright.chromium.launch_persistent_context(profile, **options)
        before = {}
        for n, (target, url, real_url) in enumerate(served):
            page = context.pages[0] if n == 0 and context.pages else context.new_page()
            page.goto(url)
            print(f"[{worker}, {end}] {target}: fill {fill(page, target, real_url)}")
            before[url] = page.evaluate(SNAPSHOT)
        time.sleep(settle)
        if end == "kill":
            os.kill(chrome_pid(profile), signal.SIGKILL)
            try:
                context.close()
            except Error:
                pass
        else:
            context.close()  # WorkerBrowsers.open's own end: Playwright closes the browser
        if restore:
            options["args"] = [*options["args"], "--restore-last-session"]
        context = playwright.chromium.launch_persistent_context(profile, **options)
        try:
            time.sleep(BACK)
            after = {page.url: page.evaluate(SNAPSHOT) for page in context.pages if page.url in before}
            report(worker, end, before, [page.url for page in context.pages], after)
        finally:
            context.close()


def linux_browsers() -> Path:
    """On Linux, a Playwright browsers folder whose Chrome for Testing is a wrapper that adds `LINUX`, so the reopen
    test's own plain Workers (in its child process too) can start in the container. Elsewhere, Playwright's own."""
    real = chrome_for_testing()
    if not LINUX:
        return real.parents[2]
    folder = Path(tempfile.mkdtemp(prefix="hfc-browsers-"))
    wrapper = folder / real.parents[1].name / FOR_TESTING_LINUX.replace("*", "")
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text(f"#!/bin/sh\nexec {real} {' '.join(LINUX)} \"$@\"\n")
    wrapper.chmod(0o755)
    return folder


# `reopen`'s pytest run, with a plugin that ends the Worker's Chrome by SIGKILL where the test sends SIGTERM. It imports
# nothing of Apply's before tests/conftest.py has set the tests' own data folder.
REOPEN = """import signal, sys, types, pytest
class Kill:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            item.module.signal = types.SimpleNamespace(SIGTERM=signal.SIGKILL)
sys.exit(pytest.main(["-q", "tests/test_reopen.py", "-k", "killed"], plugins=[Kill()] if sys.argv[1] == "kill" else []))
"""


def reap(test: int) -> None:
    """Reap every process orphaned under this one, but `test`, which `communicate` waits for. The container's PID 1
    (`sleep`) reaps nothing, so a killed Chrome stayed a zombie, and the test's `os.kill(pid, 0)` took it for running."""
    ctypes.CDLL(None).prctl(PR_SET_CHILD_SUBREAPER, 1)
    while True:
        try:
            dead = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError:
            return
        if dead and dead.si_pid != test:
            os.waitpid(dead.si_pid, 0)
        else:
            time.sleep(0.2)


def reopen_case(end: str) -> None:
    """`tests/test_reopen.py -k killed`, with the Worker's Chrome ended by `end`."""
    env = {k: v for k, v in os.environ.items() if k not in ("APPLY_HOME", "APPLY_PROFILES")}
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(linux_browsers())
    print(f"[reopen, {end}] tests/test_reopen.py -k killed")
    test = subprocess.Popen([sys.executable, "-c", REOPEN, end], cwd=APPLY, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if LINUX:
        threading.Thread(target=reap, args=(test.pid,), daemon=True).start()
    said = test.communicate()[0].strip().splitlines()
    print("\n".join(f"[reopen, {end}] {line}" for line in said[-15:]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("case", choices=("chrome", "reopen"))
    parser.add_argument("--worker", choices=("plain", "cdp", "both"), default="both")
    parser.add_argument("--end", choices=("kill", "quit", "both"), default="both")
    parser.add_argument("--restore", action="store_true",
                        help="start Chrome again with its own session restore on: what it kept, not what Apply does")
    parser.add_argument("--settle", type=float, default=5.0, help="s between the last fill and the end")
    args = parser.parse_args()
    ends = ("kill", "quit") if args.end == "both" else (args.end,)
    for end in ends:
        if args.case == "reopen":
            reopen_case(end)
            continue
        if args.worker in ("plain", "both"):
            plain_case(end, args.settle, args.restore)
        if args.worker in ("cdp", "both"):
            cdp_case(end, args.settle, args.restore)
    print(json.dumps({"python": sys.version.split()[0], "platform": sys.platform}))


if __name__ == "__main__":
    sys.exit(main())
