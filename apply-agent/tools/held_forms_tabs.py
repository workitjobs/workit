"""KAN-865, KAN-876 spikes: can a CDP Worker fill a form in a background tab while held forms wait?

Repeats every measurement in docs/research/held-forms-in-tabs.md. Research only: no product code
calls it. Saved forms only (the Fill engine's fixtures, served on 127.0.0.1 by `plain.demo.replay`,
which refuses every POST), filled as Test Person; nothing presses a Submit.

    uv run python tools/held_forms_tabs.py fill [--form lever-immuta]
    uv run python tools/held_forms_tabs.py sweep [--forms ...] [--out rows.jsonl]
    uv run python tools/held_forms_tabs.py workday [--forms workday-caci workday-xcel]
    uv run python tools/held_forms_tabs.py keepalive [--form oracle-macys] [--minutes 10] [--ping 30]
    uv run python tools/held_forms_tabs.py memory [--form lever-immuta] [--held 5] [--windows]
    uv run python tools/held_forms_tabs.py ticks
    uv run python tools/held_forms_tabs.py raw

The sweep, workday and keepalive cases also answer the page's requests to other hosts from the saved
form's HAR (GETs only, `serve_har`), and Chrome resolves no host but 127.0.0.1 (OFFLINE), so a
request nothing answers fails rather than reach a live site. The workday case's steps after sign-in
are the fake Workday's (tests/fake_workday.py), routed in the page.

Add --no-chrome-sandbox inside a container with no user namespaces (Chrome's own sandbox can't start).

Each case starts Chrome for Testing (Playwright's build, channel None) headed, with the CDP
Workers' own launch options (WorkerBrowsers.launch_options), on a scratch profile under
$TMPDIR/held-forms-tabs, and closes it after.
"""

import argparse
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import psutil
from playwright.sync_api import sync_playwright

from apply import fill_engine, submit_guard
from apply.browsers import WorkerBrowsers
from apply.home import SAMPLE
from apply.model import FillError, Posting
from apply.plain.demo import SAVED_FORMS, _saved, replay
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
    folder = SAVED_FORMS / target
    try:
        questions = fill_engine.read_questions(page, site)
    except FillError:  # the question set comes from the job system's API, saved beside the form (Greenhouse)
        if (folder / "question-set.json").exists():  # as the engine parsed it
            questions = fill_engine.question_set(json.loads((folder / "question-set.json").read_text()))
        elif (folder / "questions.json").exists():  # the API's own answer
            questions = fill_engine.parse_questions(site, (folder / "questions.json").read_text())
        else:  # or from the served page (Lever)
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


# Chrome resolves no host but the replay's: a request no route answers fails, so nothing reaches a live site.
OFFLINE = "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"


def serve_har(context, folder: Path) -> None:
    """Answer each of the page's requests to another host from the saved form's HAR, GETs only: the CDN scripts
    and API reads that `replay` (the form's own host only) leaves out, without which a page its scripts draw
    (Greenhouse's, Workable's) shows no form. A redirect is answered with where it leads. Every POST and every
    request the HAR doesn't hold is aborted; the replay on 127.0.0.1 answers its own."""
    saved, redirects = {}, {}
    for entry in json.loads((folder / "page.har").read_text())["log"]["entries"]:
        url, response = entry["request"]["url"].split("#")[0], entry["response"]
        if entry["request"]["method"] != "GET":
            continue
        if response.get("redirectURL"):
            redirects[url] = urllib.parse.urljoin(url, response["redirectURL"])
            continue
        content = response["content"]
        text = content.get("text", "")
        body = base64.b64decode(text) if content.get("encoding") == "base64" else text.encode()
        saved.setdefault(url, (response["status"], content.get("mimeType") or "", body))
    for url, target in redirects.items():
        while target in redirects and redirects[target] != target:
            target = redirects[target]
        if target in saved:
            saved.setdefault(url, saved[target])

    def answer(route):
        request = route.request
        if urllib.parse.urlsplit(request.url).hostname == "127.0.0.1":
            return route.continue_() if request.method == "GET" else route.abort()
        found = saved.get(request.url.split("#")[0]) if request.method == "GET" else None
        if not found:
            return route.abort()
        status, mime, body = found
        origin = request.headers.get("origin") or "*"
        route.fulfill(status=status, content_type=mime, body=body, headers={
            "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"})

    context.route("**/*", answer)


def saved_forms() -> list[str]:
    """Every saved form with a page.har, by name."""
    return sorted(p.name for p in SAVED_FORMS.iterdir() if (p / "page.har").exists())


def tried(page, target: str, real_url: str) -> dict:
    """`fill`, with an error kept as the result instead of raised: one form's failure ends no sweep. A page that
    never finished loading is loaded again once, in any case (`reloaded`): Greenhouse's replayed page left
    React unhydrated in about one load in three, in front as well as behind (2026-11-17)."""
    started = time.monotonic()
    reloaded = False
    while True:
        try:
            return {**fill(page, target, real_url), **({"reloaded": True} if reloaded else {})}
        except Exception as error:  # the sweep records every kind of failure
            if "never finished loading" in str(error) and not reloaded:
                reloaded = True
                page.reload()
                continue
            return {"error": f"{type(error).__name__}: {str(error).splitlines()[0][:160] if str(error) else ''}",
                    "seconds": round(time.monotonic() - started, 1), **({"reloaded": True} if reloaded else {})}


def case_sweep(targets: list[str], out: Path | None) -> None:
    """Each saved form, in one Worker's Chrome as Workers run: filled in front (it is then the held form),
    then again in a new tab behind it, then in a new window behind it, then, the control, in a new tab in front.
    One JSON line per form."""
    print(f"Chrome for Testing {sync_version()}; {len(targets)} saved forms")
    for target in targets:
        row = {"form": target}
        folder = _saved(target)
        with replay(folder) as (url, real_url), worker([OFFLINE]) as context:
            serve_har(context, folder)
            front = context.pages[0] if context.pages else context.new_page()
            front.set_default_timeout(20_000)
            front.goto(url)
            row["front"] = tried(front, target, real_url)
            if "error" in row["front"] or not row["front"]["questions"]:
                row["skipped"] = "not filled in front"
            else:
                for case, window in (("tab", False), ("window", True)):
                    behind = second_page(context, front, window)
                    behind.set_default_timeout(20_000)
                    behind.goto(url)
                    state = behind.evaluate("() => document.visibilityState")
                    row[case] = {**tried(behind, target, real_url), "visibility": state}
                again = context.new_page()  # the control: the same form again, in front of the held ones
                again.bring_to_front()
                again.set_default_timeout(20_000)
                again.goto(url)
                row["again, in front"] = tried(again, target, real_url)
        print(json.dumps(row), flush=True)
        if out:
            with out.open("a") as file:
                file.write(json.dumps(row) + "\n")


class OneTab:
    """The fake Workday as a JobSite whose form opens in `page` (a held form's tab or window), routed there."""

    def __init__(self, server, page):
        self.server, self.page = server, page
        page.route("**/*", server._handle)
        for script in server._init_scripts():
            page.add_init_script(script)
        submit_guard.on_open(page)  # as a Worker opens each page

    def fetch(self, url: str, body: bytes | None = None) -> bytes:
        return self.server.fetch(url, body)

    @contextmanager
    def open(self, url: str, worker: int = 0):
        self.page.goto(url)
        yield self.page


def workday_steps(page, target: str) -> dict:
    """Fill the saved Workday posting step by step in `page`, as the Workday Filler does: sign-in (an account
    made on the fake), then each step's questions planned for Test Person, Save and Continue to the next step,
    to Review. The steps after sign-in are tests/fake_workday.py's, served by a route on the page only; each
    step's names show 1.5 s late, as Workday's do live, so the Filler's wait for them is used on each step."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from fake_workday import FakeWorkdayServer
    from fakes import FakeClock, FakeMailbox

    from apply.accounts import Accounts
    from apply.keychain import InMemoryKeychain
    from apply.model import Handoff, MoreQuestions
    from apply.workday import WorkdayFiller

    folder = _saved(target)
    real_url = json.loads((folder / "page.har").read_text())["log"]["entries"][0]["request"]["url"]
    server = FakeWorkdayServer(folder, keychain=InMemoryKeychain(), mailbox=FakeMailbox(), step_name_delay=1.5)
    site = OneTab(server, page)
    now = datetime.now()  # noqa: DTZ005 (Accounts' clock is local time)
    accounts = Accounts(InMemoryKeychain(), server._mailbox, FakeClock(now), "test.person@example.com", target)
    profile = ApplicantProfile.load(SAMPLE / "applicant-profile.yaml")
    posting = Posting(target, "Saved form", "Intern", real_url)
    filler = WorkdayFiller(accounts)
    started = time.monotonic()
    row: dict = {"steps": []}
    try:
        questions = filler.question_set(real_url, site)
        row["signed in"] = round(time.monotonic() - started, 1)
        ticked: dict = {}  # the boxes Apply never ticks, ticked as the applicant would before Resume
        while True:
            planned = fill_engine.plan(questions, posting, profile)
            answers = {name: value for name, value in planned.answers.items() if value not in (None, "")} | ticked
            step_started = time.monotonic()
            try:
                readback = filler.fill(page, questions, answers)
                row["steps"].append(round(time.monotonic() - step_started, 1))
                break
            except MoreQuestions as more:
                row["steps"].append(round(time.monotonic() - step_started, 1))
                questions = questions + more.questions
            except Handoff as handoff:
                row["steps"].append(round(time.monotonic() - step_started, 1))
                to_tick = {name: "Yes" for name in fill_engine.attestations(questions)} | {
                    q.name: "Test Person" for q in questions if q.label == "Name"}
                if not str(handoff).startswith("Tick") or not to_tick.keys() - ticked.keys():
                    raise
                row.setdefault("handoffs", []).append(str(handoff)[:80])
                ticked |= to_tick
        problems = fill_engine.readback_problems(questions, answers, readback, planned.accepted)
        row.update(questions=len(questions), answered=len(answers), problems=len(problems),
                   shown=sum(1 for name in answers if readback.get(name) not in (None, "", [])))
    except Exception as error:  # a stop is the result
        row["error"] = f"{type(error).__name__}: {str(error).splitlines()[0][:160] if str(error) else ''}"
    row["step loads"] = list(server.step_loads)
    row["on"] = page.evaluate("() => document.querySelector('[data-automation-id=progressBar] [aria-current=step], h2')?.innerText || ''")
    row["submissions"] = len(server.submissions)
    row["seconds"] = round(time.monotonic() - started, 1)
    row["visibility"] = page.evaluate("() => document.visibilityState")
    return row


def case_workday(targets: list[str]) -> None:
    """Each saved Workday posting filled step by step: in front (then held there), in a new tab behind it, and
    in a new window behind it, in one Worker's Chrome as Workers run."""
    print(f"Chrome for Testing {sync_version()}")
    for target in targets:
        with worker([OFFLINE]) as context:
            front = context.pages[0] if context.pages else context.new_page()
            print(json.dumps({"form": target, "case": "front", **workday_steps(front, target)}), flush=True)
            for case, window in (("tab", False), ("window", True)):
                behind = second_page(context, front, window)
                print(json.dumps({"form": target, "case": case, **workday_steps(behind, target)}), flush=True)
            again = context.new_page()  # the control: a second form in front, the held ones behind it
            again.bring_to_front()
            print(json.dumps({"form": target, "case": "again, in front", **workday_steps(again, target)}), flush=True)


# What reaches a held page, counted by its own window listeners (where Oracle's idle timer listens), and
# the stay-signed-in button's presses.
HEARD = """() => { window.__heard = {mousemove: 0, trusted: 0, stay: 0};
  window.addEventListener('mousemove', (e) => { window.__heard.mousemove++; if (e.isTrusted) window.__heard.trusted++; }); }"""
# A session dialog in the generic rules' words (keepalive.WARNS, STAY_NAMES): its button counts its presses and
# closes it. No form and no field, so the Keeper's four checks let the press through.
DIALOG = """() => { const d = document.createElement('div'); d.setAttribute('role', 'dialog'); d.id = '__held_dialog';
  d.style.cssText = 'position:fixed;top:30%;left:30%;z-index:99999;background:#fff;border:2px solid #000;padding:20px';
  d.innerHTML = '<p>Your session is about to expire.</p>';
  const b = document.createElement('button'); b.textContent = 'Continue session';
  b.addEventListener('click', () => { window.__heard.stay++; d.remove(); }); d.appendChild(b);
  document.body.appendChild(d); }"""
HELD_READ = """() => ({...window.__heard, visibility: document.visibilityState,
  ceSessionExpire: localStorage.getItem('ceSessionExpire'), dialog: !!document.getElementById('__held_dialog')})"""


def case_keepalive(target: str, minutes: float, ping_s: float) -> None:
    """The held form's Keeper (keepalive.py) on `target` held behind a tab and behind a window of one Worker's
    Chrome, as Workers run, for `minutes`, with PING_S shortened to `ping_s`. Halfway, each held page shows a
    session dialog for the stay press. Per ping: whether the GET reached the server and the mouse move the
    page; at the end, whether the stay press reached the page."""
    import http.server

    from apply import keepalive

    gets = []  # each GET the replay answered that no page made (no Sec-Fetch-Mode): the Keeper's pings
    answered = http.server.BaseHTTPRequestHandler.send_response

    def counted(handler, code, message=None):
        if handler.command == "GET" and not handler.headers.get("Sec-Fetch-Mode"):
            gets.append(code)
        answered(handler, code, message)

    http.server.BaseHTTPRequestHandler.send_response = counted
    pinged = keepalive.ping
    pings: list[dict] = []

    def ping(page, site, activity=True):
        before, got = page.evaluate(HELD_READ), len(gets)
        pinged(page, site, activity)
        after = page.evaluate(HELD_READ)
        pings.append({"held": held[page], "at": round(time.monotonic() - start), "get": gets[got:],
                      "mouse moves heard": after["mousemove"] - before["mousemove"],
                      "ceSessionExpire moved": after["ceSessionExpire"] != before["ceSessionExpire"],
                      "visibility": after["visibility"]})
        print(json.dumps(pings[-1]), flush=True)

    keepalive.ping, keepalive.PING_S = ping, ping_s
    folder = _saved(target)
    print(f"Chrome for Testing {sync_version()}; form {target}; {minutes:g} min, a ping each {ping_s:g} s")
    with replay(folder) as (url, _), worker([OFFLINE]) as context:
        serve_har(context, folder)
        context.add_init_script(f"({HEARD})()")
        in_tab = context.pages[0] if context.pages else context.new_page()
        in_tab.goto(url)
        front = context.new_page()  # the next form's tab, in front of the held one
        front.goto("data:text/html,<title>front</title><p>the next form")
        in_window = second_page(context, front, window=True)
        in_window.goto(url)
        front.bring_to_front()
        held = {in_tab: "behind a tab", in_window: "behind a window"}
        print("held pages at the start:", {name: page.evaluate(HELD_READ) for page, name in held.items()})
        keepers = {page: keepalive.Keeper(target, lost=lambda why, name=name: print(f"[{name}] lost: {why}"),
                                          say=lambda line, name=name: print(f"[{name}] {line}"))
                   for page, name in held.items()}
        start = time.monotonic()
        shown = False
        while time.monotonic() - start < minutes * 60:
            if not shown and time.monotonic() - start > minutes * 30:
                shown = True
                for page in held:
                    page.evaluate(DIALOG)
                print("session dialogs shown at", round(time.monotonic() - start), "s", flush=True)
            for page, keeper in keepers.items():
                keeper.tick(page)
            front.wait_for_timeout(1000)
        for page, name in held.items():
            print(f"[{name}] at the end: {page.evaluate(HELD_READ)}; Keeper holding: {keepers[page].holding()!r}")
    http.server.BaseHTTPRequestHandler.send_response = answered


def chrome_root() -> psutil.Process:
    """The Worker's Chrome browser process: the one on its scratch profile with no `--type=`."""
    profile = str(SCRATCH / "worker-1")
    return next(p for p in psutil.process_iter(["cmdline"])
                if any(profile in a for a in (p.info["cmdline"] or []))
                and not any(a.startswith("--type=") for a in p.info["cmdline"]))


def chrome_memory() -> tuple[int, int, int]:
    """Total resident memory (bytes) of the Worker's Chrome, the browser and its children, how many processes
    that is, and their total unique memory (USS: the pages no other process shares, so it counts nothing twice)."""
    root = chrome_root()
    processes = [root, *root.children(recursive=True)]
    total = unique = 0
    for process in processes:
        try:
            full = process.memory_full_info()
            total, unique = total + full.rss, unique + full.uss
        except psutil.Error:
            pass
    return total, len(processes), unique


def case_memory(target: str, held: int, windows: bool = False) -> None:
    """Hold 1..`held` filled forms in one Worker's Chrome, each in a tab of its one window or, with `windows`,
    each in a window of its own; its total resident memory after each."""
    folder = _saved(target)
    print(f"Chrome for Testing {sync_version()}; form {target}; each held form in {'a window' if windows else 'a tab'}")
    with replay(folder) as (url, real_url), worker([]) as context:
        blank = context.pages[0] if context.pages else context.new_page()
        time.sleep(2)
        rss, _, uss = chrome_memory()
        print(f"0 held (one blank tab): {rss / 2**20:.0f} MiB; unique {uss / 2**20:.0f} MiB")
        pages = []
        for n in range(1, held + 1):
            page = blank if n == 1 else second_page(context, blank, window=True) if windows else context.new_page()
            page.goto(url)
            fill(page, target, real_url)
            pages.append(page)
            time.sleep(2)
            rss, processes, uss = chrome_memory()
            print(f"{n} held: {rss / 2**20:.0f} MiB in {processes} processes; unique {uss / 2**20:.0f} MiB")


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
    parser.add_argument("case", choices=("fill", "sweep", "workday", "keepalive", "memory", "ticks", "raw"))
    parser.add_argument("--form", default="lever-immuta")
    parser.add_argument("--forms", nargs="*", help="sweep: these saved forms (default: every one with a page.har)")
    parser.add_argument("--out", type=Path, help="sweep: also append each form's JSON line to this file")
    parser.add_argument("--held", type=int, default=5)
    parser.add_argument("--windows", action="store_true", help="memory: each held form in a window of its own")
    parser.add_argument("--minutes", type=float, default=10, help="keepalive: how long it runs")
    parser.add_argument("--ping", type=float, default=30, help="keepalive: PING_S, shortened from 240 s")
    parser.add_argument("--no-chrome-sandbox", action="store_true", help="for a container with no user namespaces")
    args = parser.parse_args()
    global CHROME_SANDBOX
    CHROME_SANDBOX = not args.no_chrome_sandbox
    if args.case == "fill":
        case_fill(args.form)
    elif args.case == "workday":
        case_workday(args.forms or ["workday-caci", "workday-xcel"])
    elif args.case == "keepalive":
        case_keepalive(args.form if args.form != "lever-immuta" else "oracle-macys", args.minutes, args.ping)
    elif args.case == "sweep":
        case_sweep(args.forms or saved_forms(), args.out)
    elif args.case == "memory":
        case_memory(args.form, args.held, args.windows)
    elif args.case == "ticks":
        case_ticks()
    else:
        case_raw()


if __name__ == "__main__":
    sys.exit(main())
