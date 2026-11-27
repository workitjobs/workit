"""WorkIt Auto Apply's window, read and driven from a terminal (`uv run apply window ...`): what the window shows, and
its buttons, for an agent with no screen to look at. A Developer checkout's window only (apply.build.DEVELOPER).

The running window watches CONTROL every CONTROL_EVERY (`watch`, started by app_window.run). A command writes one
request file there, whole before it is named `.request`; the window takes it, answers it in a thread of its own and
writes the reply beside it, whole before it is named `.reply`. A request names an action, never a path: `state`
(what the window shows, through its own /state), `applied`, or one of ROUTES. Each of ROUTES goes through the same
route the page's button posts to (Bridge.request, with the board's token, as the page sends it), so its rules and
refusals are the button's: Approve and submit is POST /submit, and the run presses the form's Submit as for the
button (apply.send_button), reads the job site's confirmation and makes a Handoff without one.

A request carries when it expires: one the window takes too late is refused, so a submit a command gave up on is
never pressed later. The command removes its request when it gives up, if the window hasn't taken it.

`view` is the student page's own sorting (window/src/view.ts: Needs you, Still working on, Applied, Didn't go
through), with every filled form's answers, flags, Missing facts, Essays, Auto-submit's reason and its Record's
screenshot. A command prints it through apply.masked, as every command does: a profile or Answer bank value shows
as its key."""

import json
import os
import sys
import threading
import time
from pathlib import Path

from apply.home import HOME

CONTROL = HOME / "app-control"
CONTROL_EVERY = 0.25  # how often the window looks for a request
ASK_WAIT = 30.0  # how long a command waits for the window's reply: /answer may save to WorkIt first
REPLY_KEPT = 300.0  # a reply no command read (it gave up) is removed after this long

# Each action and the route its button posts to. The body is the page's own (window/src/bridge.ts).
ROUTES = {"submit": "/submit", "cancel": "/auto-cancel", "skip": "/let-go", "fill-again": "/fill-again",
          "answer": "/answer", "remove": "/remove", "stop": "/stop"}

# What a to-do asks of the student, by its verdict's kind, and the order the window lists them in (view.ts's ASKS,
# ORDER): a sign-in blocks every job on its site, so it comes first; a form to submit is done, so it comes last.
ASKS = {"needs sign-in": "sign-in", "missing fact": "question", "needs code": "code", "captcha": "captcha",
        "check": "check", "held": "approve", "blocked": "finish", "handoff": "finish"}
ORDER = ["sign-in", "question", "code", "captcha", "check", "approve", "finish", "submit"]


def _write(path: Path, data: dict) -> None:
    """`data` as JSON at `path`, only the user's to read, written whole before it takes its name."""
    part = path.with_suffix(".part")
    part.write_text(json.dumps(data), encoding="utf-8")
    part.chmod(0o600)
    part.rename(path)


# The command's side.

def ask(action: str, body: dict | None = None, folder: Path = CONTROL, timeout: float = ASK_WAIT) -> dict:
    """One action of the running window, and its reply: the route's answer with its `status`, or {status, error}."""
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = f"{time.time_ns()}-{os.getpid()}"
    request, reply = folder / f"{name}.request", folder / f"{name}.reply"
    _write(request, {"action": action, "body": body or {}, "expires": time.time() + timeout})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if reply.exists():
            got = json.loads(reply.read_text(encoding="utf-8"))
            reply.unlink(missing_ok=True)
            return got
        time.sleep(0.05)
    try:
        request.unlink()
    except FileNotFoundError:  # taken: it may have been done
        return {"status": 504, "error": "The window took it but didn't answer in time. Read the state to see what "
                                         "happened before you ask again."}
    return {"status": 504, "error": "The window didn't answer. A window opened before `apply window` existed never "
                                     "does: quit it and open it again (`uv run apply app`)."}


# The window's side.

def watch(bridge, folder: Path = CONTROL, every: float = CONTROL_EVERY) -> None:
    """Answer each request in `folder`, till the window closes (a daemon thread of app_window.run's)."""
    while True:
        try:
            serve(bridge, folder)
        except Exception as error:  # a bad request never ends the watch
            print(f"Couldn't take a request from {folder}: {type(error).__name__}: {error}", file=sys.stderr)
        time.sleep(every)


def serve(bridge, folder: Path = CONTROL) -> list[threading.Thread]:
    """Take each request waiting in `folder` and answer it in a thread of its own, so a slow one (an answer saved to
    WorkIt) holds up no other; remove replies no command read. The threads, for a test to join."""
    if not folder.is_dir():
        return []
    for old in folder.glob("*.reply"):
        try:
            if time.time() - old.stat().st_mtime > REPLY_KEPT:
                old.unlink()
        except OSError:
            pass
    threads = []
    for request in sorted(folder.glob("*.request")):
        taken = request.with_suffix(".taken")
        try:
            request.rename(taken)  # once: the command can no longer take it back
        except OSError:
            continue
        thread = threading.Thread(target=_answer, args=(bridge, taken), daemon=True, name="control-request")
        thread.start()
        threads.append(thread)
    return threads


def _answer(bridge, taken: Path) -> None:
    try:
        request = json.loads(taken.read_text(encoding="utf-8"))
        if not isinstance(request, dict) or not isinstance(request.get("body", {}), dict):
            raise TypeError
        expires = float(request.get("expires") or 0)
    except (OSError, ValueError, TypeError):
        reply = {"status": 400, "error": "Not a request."}
    else:
        if expires < time.time():
            reply = {"status": 408, "error": "Too late: the command stopped waiting, so nothing was done."}
        else:
            try:
                reply = handle(bridge, str(request.get("action")), request.get("body") or {})
            except Exception as error:
                reply = {"status": 500, "error": f"{type(error).__name__}: {error}"}
    taken.unlink(missing_ok=True)
    _write(taken.with_suffix(".reply"), reply)


def handle(bridge, action: str, body: dict) -> dict:
    """One action, as the window's page does it: `state` and `applied` read what the window shows; each of ROUTES
    posts its button's route with the board's token."""
    if action == "state":
        got = bridge.request("GET", "/state")
        if got["status"] != 200:
            return {"status": got["status"], "error": got["body"]}
        return {"status": 200, "state": view(json.loads(got["body"]), screen(bridge), _records())}
    if action == "applied":
        got = bridge.applied()
        return {"status": 502, **got} if isinstance(got, dict) else {"status": 200, "applied": got}
    if action not in ROUTES:
        return {"status": 404, "error": f"No such action: {action}. Use one of: state, applied, {', '.join(ROUTES)}."}
    board = bridge._dashboard
    got = bridge.request("POST", ROUTES[action], {"X-Apply-Token": board.token, "Content-Type": "application/json"},
                         json.dumps(body))
    try:
        said = json.loads(got["body"]) if got["body"] else {}
    except ValueError:
        said = {"error": got["body"]}
    return {"status": got["status"], **(said if isinstance(said, dict) else {"reply": said})}


def screen(bridge) -> dict:
    """What the window shows as a whole: sign-in, first run, or the Apply window; and whether a run goes."""
    from apply.first_run import READY

    shows = "sign-in" if not bridge.signed_in() else "apply" if bridge._first.step() == READY else "first-run"
    return {"pid": os.getpid(), "shows": shows} | bridge.status()


def _records() -> list[Path]:
    """Every Record folder on this Mac, oldest day first: one is named `...-<its Application's id>`."""
    # Here: apply.student imports app_window, which starts this.
    from apply.student import RECORDS

    return sorted(RECORDS.glob("*/*"), key=lambda path: path.parent.name)


# What the window shows (window/src/view.ts), for an agent.

def _key(shown: dict) -> str:
    """One job, one key: its posting, else its company and role, else its own id (view.ts's keyOf)."""
    if shown.get("posting_url"):
        return str(shown["posting_url"])
    if shown.get("company") and shown.get("role"):
        return f"{shown['company']}|{shown['role']}"
    return str(shown.get("id"))


def _classify(shown: dict) -> tuple[str, str]:
    """(status, ask) as the window sorts a job (view.ts's classify)."""
    tone = shown.get("tone")
    if tone == "filling":
        return "filling", ""
    if tone == "verifying":
        return "checking", ""
    if tone == "ready":
        return "todo", "submit"
    if tone == "submitted":
        return "submitted", ""
    if tone == "needs":
        return "todo", ASKS.get(str(shown.get("kind") or ""), "finish")
    return "stopped", ""


def view(state: dict, shows: dict | None = None, records: list[Path] | None = None) -> dict:
    """Dashboard.state() as the window shows it: each job once, its tile (the form as it is now) over its item (how
    it ended, and the questions the student answers it through), sorted into Needs you (most blocking first), Still
    working on, Applied and Didn't go through; the jobs waiting to start; and the run as a whole."""
    from apply import verify  # here: verify imports the fill engine

    records = records or []
    tiles: dict[str, tuple[int, dict]] = {}
    items: dict[str, dict] = {}
    for k, tile in enumerate(state.get("tiles") or []):
        if tile.get("tone") != "idle":
            tiles.setdefault(_key(tile), (k, tile))
    for item in state.get("items") or []:
        items.setdefault(_key(item), item)
    jobs = []
    for key in dict.fromkeys([*tiles, *items]):
        k, tile = tiles.get(key, (None, None))
        item = items.get(key)
        if tile is None and item.get("tone") == "idle":
            continue
        if (tile or item).get("let_go"):
            continue  # not applying to it: the window shows it no more
        shown = (item or {}) | (tile or {})
        status, asked = _classify(shown)
        if item and item.get("answered") and (tile is None or status == "todo"):
            continue  # answered in the window: it waits on the student no more
        jobs.append(_job(shown, status, asked, k, tile, item, records, verify))
    run = dict(state.get("run") or {})
    waiting = [{"link": w.get("link"), "company": w.get("company") or "", "title": w.get("title") or ""}
               for w in run.pop("waiting", None) or []]
    return {
        "window": shows or {},
        "summary": state.get("summary") or "",
        "run": run,
        "needs_you": sorted((j for j in jobs if j["ask"]), key=lambda j: ORDER.index(j["ask"])),
        "working": [j for j in jobs if j["status"] in ("filling", "checking")],
        "applied": [j for j in jobs if j["status"] == "submitted"],
        "stopped": [j for j in jobs if j["status"] == "stopped"],
        "waiting": waiting,
    }


def _job(shown: dict, status: str, asked: str, k: int | None, tile: dict | None, item: dict | None,
         records: list[Path], verify) -> dict:
    """One job as an agent reads it: what names it (`tile` for submit, cancel, skip and fill-again; `id` for answer),
    where it is, and its filled form."""
    held_flags = [f for f in (shown.get("verification") or {}).get("flags") or []
                  if f.get("holds") and not f.get("dismissed")]
    # The page's own (view.ts): the item's questions, else the tile's. Only these does /answer take.
    questions = (item or {}).get("questions")
    if questions is None:
        questions = (tile or {}).get("questions")
    questions = questions or []
    named = str(shown.get("application_id") or "")
    record = next((path for path in reversed(records) if named and path.name.endswith(f"-{named}")), None)
    answers = [{"question": a.get("question"), "answer": a.get("answer"), "source": a.get("from"),
                "kind": a.get("kind") or "", "topic": a.get("topic") or ""} for a in shown.get("answers") or []]
    job = {
        "tile": f"tile-{k}" if tile is not None else None,
        "id": None if item is None or item.get("id") is None else str(item["id"]),
        "company": shown.get("company") or "", "title": shown.get("role") or "",
        "url": shown.get("posting_url") or shown.get("link") or "", "link": shown.get("link") or "",
        "system": shown.get("system") or "", "application_id": shown.get("application_id") or "",
        "status": status, "ask": asked, "stage": shown.get("label") or "", "doing": shown.get("doing") or "",
        "detail": shown.get("detail") or "", "since": shown.get("since") or shown.get("at"),
        "held": bool(tile and tile.get("again")) and status != "submitted",
    }
    if shown.get("asked"):
        job["progress"] = {"filled": shown.get("filled") or 0, "asked": shown["asked"]}
    if asked:
        job["needs"] = {key: shown.get(key) or "" for key in ("do", "why", "then")}
    if status == "stopped":
        job["retry"] = job["tile"] if tile and (tile.get("again") or tile.get("askable") or tile.get("refill")) else None
    if shown.get("submitting") or shown.get("submit_said"):
        job["submitting"], job["submit_said"] = bool(shown.get("submitting")), shown.get("submit_said") or ""
    if shown.get("auto_at") or shown.get("auto_said"):
        job["auto_submit_at"], job["why_not"] = shown.get("auto_at"), shown.get("auto_said") or ""
    job |= {
        "verified": bool(shown.get("verified")),
        "flags": [{"field": f.get("field") or "", "why": f.get("why") or "", "kind": f.get("kind") or ""}
                  for f in held_flags],
        "legal_holds": [{"field": f.get("field") or "", "why": f.get("why") or ""} for f in held_flags
                        if verify.legal(verify.Flag(f.get("field") or "", f.get("why") or "", f.get("kind") or ""))],
        "notes": shown.get("notes") or [],
        "missing": [{"question": q, "required": (shown.get("required") or {}).get(q, True),
                     "choices": (shown.get("choices") or {}).get(q), "planned": (shown.get("planned") or {}).get(q),
                     "where": (shown.get("where") or {}).get(q)} for q in questions],
        "answers": answers,
        "essays": shown.get("essays") or [{"question": a["question"], "text": a["answer"]}
                                          for a in answers if a["source"] == "written"],
        "fixed": shown.get("fixed") or [],
        "files": [{"label": f.get("label") or "", "name": f.get("name") or ""} for f in shown.get("files") or []],
        "record": str(record) if record else shown.get("record") or "",
        "screenshot": str(record / "form.png") if record and (record / "form.png").is_file() else "",
    }
    return job
