"""KAN-865 spike: can a CDP Worker fill a form in a background tab while held forms wait?

Repeats every measurement in docs/research/held-forms-in-tabs.md. Research only: no product code
calls it. Saved forms only (the Fill engine's fixtures, served on 127.0.0.1 by `plain.demo.replay`,
which refuses every POST), filled as Test Person; nothing presses a Submit.

    uv run python tools/held_forms_tabs.py fill [--form lever-immuta]
    uv run python tools/held_forms_tabs.py memory [--form lever-immuta] [--held 5]
    uv run python tools/held_forms_tabs.py ticks
    uv run python tools/held_forms_tabs.py raw

Add --no-chrome-sandbox inside a container with no user namespaces (Chrome's own sandbox can't start).

Each case starts Chrome for Testing (Playwright's build, channel None) headed, with the CDP
Workers' own launch options (WorkerBrowsers.launch_options), on a scratch profile under
$TMPDIR/held-forms-tabs, and closes it after.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import psutil
from playwright.sync_api import sync_playwright

from apply import fill_engine
from apply.browsers import WorkerBrowsers
from apply.home import SAMPLE
from apply.model import FillError, Posting
from apply.plain.demo import _saved, replay
from apply.profile import ApplicantProfile

SCRATCH = Path(tempfile.gettempdir()) / "held-forms-tabs"
NO_THROTTLE = ["--disable-background-timer-throttling", "--disable-renderer-backgrounding"]
# Playwright adds these three to every Chrome it launches, a CDP Worker's too. Chrome's own defaults
# need them taken out (ignore_default_args); "as Workers run" keeps them.
PLAYWRIGHTS = [*NO_THROTTLE, "--disable-backgrounding-occluded-windows"]
CASES = {  # name: (Playwright's three left in, extra flags, the second form in a new window instead of a tab)
    "Chrome defaults, tab": (False, [], False),
    "Chrome defaults + no-throttle flags, tab": (False, NO_THROTTLE, False),
    "Chrome defaults, window": (False, [], True),
    "as Workers run (Playwright flags), tab": (True, [], False),
}
WINDOW = 3.0  # s each count runs
CHROME_SANDBOX = True  # off with --no-chrome-sandbox: a container without user namespaces can't start it

# Counts animation frames and 0.1 s timer ticks from the moment it runs (run again, it starts the count
# again, never a second loop); read with COUNTED.
COUNTER = """() => { const again = !!window.__held; window.__held = {frames: 0, ticks: 0}; if (again) return;
  const frame = () => { window.__held.frames++; requestAnimationFrame(frame); }; requestAnimationFrame(frame);
  setInterval(() => window.__held.ticks++, 100); }"""
COUNTED = "() => ({...window.__held, visibility: document.visibilityState})"
# The same counts with no CDP client attached: each 3 s the page writes them to its title, which
# Chrome's /json/list shows without attaching to the page.
TITLED = ("data:text/html,<script>let f=0,t=0;const r=()=>{f++;requestAnimationFrame(r)};requestAnimationFrame(r);"
          "setInterval(()=>t++,100);setInterval(()=>{document.title=NAME+' '+document.visibilityState+"
          "' frames='+f+' ticks='+t;f=0;t=0},3000)</script>")


@contextmanager
def worker(extra: list[str], playwrights: bool = True):
    """A CDP Worker's Chrome, headed, as WorkerBrowsers.open starts it, plus `extra` flags; without
    Playwright's three background flags unless `playwrights`."""
    shutil.rmtree(SCRATCH, ignore_errors=True)
    browsers = WorkerBrowsers(profiles=SCRATCH, headless=False, channel=None)
    options = browsers.launch_options(0)
    options["args"] = options["args"] + extra
    options["chromium_sandbox"] = CHROME_SANDBOX
    if not playwrights:
        options["ignore_default_args"] = PLAYWRIGHTS
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(SCRATCH / "worker-1", **options)
        try:
            yield context
        finally:
            context.close()


def second_page(context, front, window: bool):
    """A blank page behind `front`: a new tab of its window, or a new window of the same Chrome. The held
    form's tab or window is brought back to the front after, as a held form would be."""
    if window:
        session = context.new_cdp_session(front)
        with context.expect_page() as opened:
            session.send("Target.createTarget", {"url": "about:blank", "newWindow": True, "background": True})
        session.detach()
        behind = opened.value
    else:
        behind = context.new_page()
    front.bring_to_front()
    return behind


def counts(page, seconds: float = WINDOW) -> dict:
    """Frames and ticks on `page` over `seconds`."""
    page.evaluate(COUNTER)
    page.wait_for_timeout(seconds * 1000)
    return page.evaluate(COUNTED)


def fill(page, target: str, real_url: str) -> dict:
    """Fill the saved form on `page` as Test Person, as `apply plain fill` does; what came back."""
    profile = ApplicantProfile.load(SAMPLE / "applicant-profile.yaml")
    site = fill_engine.job_of(real_url)["site"]
    try:
        questions = fill_engine.read_questions(page, site)
    except FillError:  # Lever: its questions come from the served page
        questions = fill_engine.parse_questions(site, page.evaluate("() => document.documentElement.outerHTML"))
    planned = fill_engine.plan(questions, Posting(target, "Saved form", "Intern", real_url), profile)
    answers = {name: value for name, value in planned.answers.items() if value not in (None, "")}
    left = 0
    started = time.monotonic()
    for _ in range(5):  # a field that needs the job system's live API (Lever's location search) is left
        try:
            readback = fill_engine.fill(page, site, questions, answers)
            break
        except FillError as error:
            name = str(error).split(":", 1)[0]
            if name not in answers:
                raise
            answers.pop(name)
            left += 1
    took = time.monotonic() - started
    problems = fill_engine.readback_problems(questions, answers, readback, planned.accepted)
    shown = sum(1 for name in answers if readback.get(name) not in (None, "", []))
    return {"questions": len(questions), "answered": len(answers), "shown": shown, "problems": len(problems),
            "left": left, "seconds": round(took, 1)}


def screencast_frames(context, page, seconds: float = WINDOW) -> int:
    """Frames the CDP screencast (what a tile shows) sends for `page` over `seconds`, with the page
    changing (a counter in its title box) so each frame is new."""
    session = context.new_cdp_session(page)
    got = []

    def frame(event):
        got.append(1)
        session.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})

    session.on("Page.screencastFrame", frame)
    session.send("Page.startScreencast", {"format": "jpeg", "quality": 50, "everyNthFrame": 1})
    page.evaluate("""() => { const box = document.createElement('div'); box.id = '__held_box';
      box.style.cssText = 'position:fixed;top:0;left:0;z-index:99999;background:#ff0;font:20px sans-serif';
      document.body.appendChild(box); let n = 0; setInterval(() => box.textContent = String(n++), 50); }""")
    # The sync API delivers a CDP event only while the script is inside a Playwright call: time.sleep
    # made none, so frames were neither delivered nor acknowledged (3 frames in 3 s, in front too).
    page.wait_for_timeout(seconds * 1000)
    session.send("Page.stopScreencast")
    session.detach()
    return len(got)


def case_fill(target: str) -> None:
    """Each case: a held form in front, a second form filled behind it (a tab or a window)."""
    folder = _saved(target)
    print(f"Chrome for Testing {sync_version()}; form {target}")
    with replay(folder) as (url, real_url):
        for name, (playwrights, extra, window) in CASES.items():
            with worker(extra, playwrights) as context:
                front = context.pages[0] if context.pages else context.new_page()
                front.goto(url)
                in_front = fill(front, target, real_url)
                print(f"[{name}] in front: fill {in_front}, counts {counts(front)}, "
                      f"screencast {screencast_frames(context, front)}")
                behind = second_page(context, front, window)
                behind.goto(url)
                state = behind.evaluate("() => document.visibilityState")
                filled = fill(behind, target, real_url)
                print(f"[{name}] behind ({state} while filling): fill {filled}, counts {counts(behind)}, "
                      f"screencast {screencast_frames(context, behind)}")


def chrome_root() -> psutil.Process:
    """The Worker's Chrome browser process: the one on its scratch profile with no `--type=`."""
    profile = str(SCRATCH / "worker-1")
    return next(p for p in psutil.process_iter(["cmdline"])
                if any(profile in a for a in (p.info["cmdline"] or []))
                and not any(a.startswith("--type=") for a in p.info["cmdline"]))


def chrome_memory() -> tuple[int, int]:
    """Total resident memory (bytes) of the Worker's Chrome, the browser and its children, and how
    many processes that is."""
    root = chrome_root()
    processes = [root, *root.children(recursive=True)]
    total = 0
    for process in processes:
        try:
            total += process.memory_info().rss
        except psutil.Error:
            pass
    return total, len(processes)


def case_memory(target: str, held: int) -> None:
    """Hold 1..`held` filled forms in one Worker's Chrome; its total resident memory after each."""
    folder = _saved(target)
    print(f"Chrome for Testing {sync_version()}; form {target}")
    with replay(folder) as (url, real_url), worker([]) as context:
        blank = context.pages[0] if context.pages else context.new_page()
        time.sleep(2)
        print(f"0 held (one blank tab): {chrome_memory()[0] / 2**20:.0f} MiB")
        pages = []
        for n in range(1, held + 1):
            page = blank if n == 1 else context.new_page()
            page.goto(url)
            fill(page, target, real_url)
            pages.append(page)
            time.sleep(2)
            rss, processes = chrome_memory()
            print(f"{n} held: {rss / 2**20:.0f} MiB in {processes} processes")


def case_ticks() -> None:
    """Frames and ticks for a plain page in front and behind, per case, with no form."""
    for name, (playwrights, extra, window) in CASES.items():
        with worker(extra, playwrights) as context:
            front = context.pages[0] if context.pages else context.new_page()
            front.goto("data:text/html,<title>front</title><p>front")
            behind = second_page(context, front, window)
            behind.goto("data:text/html,<p>behind")
            print(f"[{name}] front {counts(front)}; behind {counts(behind)}; "
                  f"front screencast {screencast_frames(context, front)}; "
                  f"behind screencast {screencast_frames(context, behind)}")


def case_raw() -> None:
    """Two tabs of a Chrome that no Playwright drives, read through /json/list; then the same Chrome
    with Playwright attached (connect_over_cdp), which turns on focus emulation in each page."""
    with sync_playwright() as playwright:
        chrome = playwright.chromium.executable_path
        for name, extra in (("Chrome defaults", []), ("no-throttle flags", NO_THROTTLE)):
            shutil.rmtree(SCRATCH, ignore_errors=True)
            profile = SCRATCH / "raw"
            args = [chrome, f"--user-data-dir={profile}", "--remote-debugging-port=0", "--no-first-run", *extra,
                    *([] if CHROME_SANDBOX else ["--no-sandbox"]),
                    TITLED.replace("NAME", "'front'"), TITLED.replace("NAME", "'behind'")]  # the first is in front
            process = subprocess.Popen(args, stderr=subprocess.DEVNULL)
            try:
                port_file = profile / "DevToolsActivePort"
                while not port_file.exists():
                    if process.poll() is not None:  # Chrome exited before it opened its port
                        sys.exit(f"[{name}] Chrome exited with {process.returncode}")
                    time.sleep(0.1)
                port = port_file.read_text().split()[0]
                time.sleep(7)  # two counting windows, the first one partly before the pages loaded
                print(f"[{name}] no client attached: {titles(port)}")
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                browser.contexts[0].pages[0].wait_for_timeout(7000)
                print(f"[{name}] Playwright attached: {titles(port)}")
                browser.close()
            finally:
                process.terminate()
                process.wait()


def titles(port: str) -> list[str]:
    """Each page's title, from Chrome's /json/list: no CDP client attaches to read it."""
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list") as reply:
        return [target["title"] for target in json.load(reply) if target["type"] == "page"]


def sync_version() -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(chromium_sandbox=CHROME_SANDBOX)
        try:
            return browser.version
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("case", choices=("fill", "memory", "ticks", "raw"))
    parser.add_argument("--form", default="lever-immuta")
    parser.add_argument("--held", type=int, default=5)
    parser.add_argument("--no-chrome-sandbox", action="store_true", help="for a container with no user namespaces")
    args = parser.parse_args()
    global CHROME_SANDBOX
    CHROME_SANDBOX = not args.no_chrome_sandbox
    if args.case == "fill":
        case_fill(args.form)
    elif args.case == "memory":
        case_memory(args.form, args.held)
    elif args.case == "ticks":
        case_ticks()
    else:
        case_raw()


if __name__ == "__main__":
    sys.exit(main())
