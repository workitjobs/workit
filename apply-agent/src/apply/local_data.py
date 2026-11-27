"""What WorkIt Auto Apply keeps of an application on the Mac, and when it goes (W11).

WorkIt keeps what each application sent (`PUT .../sent`), the Sent resume and the stage, so the Mac keeps an
application's working files only while its form is open: its Record (the held form's answers and screenshot), its
step-by-step trace, its dismissed flags and the tailored resume it was given. They go once WorkIt has what the
form sent (the applied write's `delivered`), or at once when the student lets the form go. What stays is the Worker
Chrome profiles and the keychain (the WorkIt sign-in, each job site's account and password).

`sweep` runs as the app opens: it deletes every application's files but an open form's (a crash, a quit, an older
version's), the copies of the profile's files (written again at each Start), and an older version's Tracker file,
after moving its Employer accounts into the keychain. A Developer checkout keeps its own files: only the Student
build calls these (`build.STUDENT`)."""

import re
import shutil
from pathlib import Path

from apply import batch, trace, tracker, verify
from apply.home import HOME
from apply.tailored import TAILORED
from apply.worker import SENT, sent_name

RECORDS = HOME / "rehearsals"  # each held form's Record, as `apply rehearse` keeps them
FILES = HOME / "files"  # the profile's resume and transcript, as WorkIt gave them at the last Start
# Developer files a version before W11 could leave in the app's data folder: never written now.
OLDER = ("tracker.json", "tracker.lock", "tracker.part")


def forget(company: str, application_id: str) -> None:
    """Delete what this Mac kept of one Application: its Record, its files under SENT, its tailored resume, its
    trace and its dismissed flags."""
    names = _names(company, application_id)
    for root, name in ((RECORDS, names[0]), (SENT, names[1])):
        for path in root.glob(f"*/{_escape(name)}"):
            _remove(path)
    _remove(TAILORED / _safe(application_id))
    for path in trace.TRACES.glob(f"*/{_escape(names[2])}"):
        _remove(path)
    verify.keep_dismissed({key for key in _open_ids()} - {application_id})


def forget_files() -> None:
    """The profile's resume and transcript copies, once a run ends: the next Start reads them from WorkIt again."""
    _remove(FILES)


def sweep(keychain) -> None:
    """As the app opens: every application's files but an open form's, the profile's file copies, and an older
    version's Tracker file, its Employer accounts moved into `keychain` first."""
    forms = batch.forms()
    kept = [_names(f.get("company") or "", str(f.get("application_id") or "")) for f in forms]
    for root, at in ((RECORDS, 0), (SENT, 1)):
        for path in root.glob("*/*"):
            if path.name not in {k[at] for k in kept}:
                _remove(path)
    for path in trace.TRACES.glob("*/*"):
        if path.name not in {k[2] for k in kept}:
            _remove(path)
    for path in TAILORED.glob("*"):
        if path.name not in {_safe(str(f.get("application_id") or "")) for f in forms}:
            _remove(path)
    for root in (RECORDS, SENT, trace.TRACES):
        for day in root.glob("*"):
            if day.is_dir() and not any(day.iterdir()):
                day.rmdir()
    verify.keep_dismissed(_open_ids())
    forget_files()
    _move_accounts(keychain)


def _move_accounts(keychain) -> None:
    """An older version's tracker.json: its Employer accounts join the keychain's list, then the file goes."""
    older = HOME / OLDER[0]
    if older.is_file():
        try:
            moved = tracker.FileTracker(older).employer_accounts()
        except Exception:  # a file that won't read: its accounts' passwords stay in the keychain all the same
            moved = []
        have = tracker.accounts_in(keychain)
        new = [a for a in moved if a.site not in {h.site for h in have}]
        if new:
            tracker.keep_accounts(keychain, have + new)
    for name in OLDER:
        (HOME / name).unlink(missing_ok=True)


def _names(company: str, application_id: str) -> tuple[str, str, str]:
    """An Application's Record folder, SENT folder and trace file names, as records.folder, worker.sent_name and
    trace.tracing make them."""
    slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-") or "company"
    return f"{slug}-{application_id}", sent_name(company, application_id), f"{trace._safe(application_id)}.jsonl"


def _open_ids() -> set[str]:
    return {str(f.get("application_id")) for f in batch.forms() if f.get("application_id")}


def _safe(application_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", application_id)


def _escape(name: str) -> str:
    return re.sub(r"([*?\[])", r"[\1]", name)


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)
