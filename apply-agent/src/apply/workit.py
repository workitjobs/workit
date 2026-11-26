"""The WorkIt client: the one module in Apply that calls WorkIt (KAN-541).

Apply signs in to WorkIt as the student, with the same Supabase project as
WorkIt's web app and extension, through the student's own browser and no port
(KAN-723 W5, D12). Apply makes a PKCE verifier and opens WorkIt's
`/app-sign-in` page with its challenge in the default browser. The student
signs in there as they always do, and the page gives a one-time code: through
the app's `workit-auto-apply://` link, or pasted by hand (`login`, a Developer
checkout, which macOS can't hand a link). `trade` sends the code and the
verifier to `POST /apply-app/session`, which answers a new Supabase session of
Apply's own (`backend/app/services/app_sign_in.py`). Only Apply has that
session, so Apply can refresh it with no race against the web app (the
extension cannot, see its CLAUDE.md, KAN-465).

The session's refresh token is kept in the system's keychain (`keyring`,
item `apply-workit`, its account the Supabase URL), never in the repo and
never printed; the access token lives only in the process that uses it. The
access token lasts about one hour; `call` refreshes it at Supabase Auth when
it expires, and saves the new refresh token (Supabase rotates it on each
use). A lock file stops two processes from using one refresh token.

The API checks the bearer token itself (`backend/app/deps.py`,
`security.py`): the token's signature, audience and issuer, then the
account row.

A call to the live API or to the live Supabase Auth (the session's hourly
refresh) trusts only the certificate authorities Cloudflare uses
(`apply.workit_roots`, D28 and W7; Supabase is behind Cloudflare too), not
the computer's store, so a proxy the computer trusts can't read the session
or the Fill engine's download. Pinning the API alone left the refresh
token readable, and with it the download. A local stack (APPLY_WORKIT_*)
is not pinned.

The Applications Tracker's reads and writes (find or add a job by its
link, set a stage and the applied date, keep a Sent resume) are methods
that use `call`. So is the read of the student's tailored resume for a
job (KAN-547).

Apply's writes to the student's Applications Tracker (KAN-544) are `Write`s
sent through `WaitingWrites`: it adds the job by its link, sets the stage, and
for a submit keeps the file sent as the application's Sent resume. A write
that cannot reach WorkIt (no answer, or no live login) waits in
`APPLY_HOME/workit-queue.json` and goes with the next send or `flush`.
"""

import base64
import dataclasses
import email.utils
import fcntl
import hashlib
import json
import os
import re
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from datetime import time as dtime
from email.message import Message
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from apply.home import HOME
from apply.keychain import WORKIT, SystemKeychain

if TYPE_CHECKING:
    from apply.adapters import Keychain

# The login's lock (`.lock` beside it), and the file the session was kept in before 2026-11-15; the session is in
# the keychain now (WORKIT).
LOGIN = HOME / "workit-login.json"
# Writes to the Applications Tracker that could not reach WorkIt yet.
QUEUE = HOME / "workit-queue.json"
# Refresh an access token this many seconds before it expires, so it does not expire on its way.
EARLY = 60
TIMEOUT = 20
REPORT_TIMEOUT = 120  # seconds: a report's screenshots are megabytes on a home connection
# Cloudflare, in front of WorkIt's API, refuses Python-urllib's own user agent (error 1010).
USER_AGENT = "WorkIt-Apply/1"
# The page's link, as `apply login` may get it pasted in place of the code (`frontend/src/app/app-sign-in/`).
APP_LINK = "workit-auto-apply://"
# This process's access token for each WorkIt (its Supabase URL) and when it expires, shared by every client in
# the process, so a run refreshes once an hour, not once for each of its clients. Never on disk.
_ACCESS: dict[str, tuple[str, float]] = {}


@dataclass(frozen=True)
class Site:
    """Where WorkIt is: its web app, its API, and its Supabase project (URL and public anon key)."""

    web: str
    api: str
    auth: str
    anon_key: str


# The live WorkIt. The same public values as autofiller_extension/src/shared/config.js
# (test_workit_login checks this). The anon key is public by design (root CLAUDE.md).
LIVE = Site(
    web="https://workitjobs.ai",
    api="https://api.workitjobs.ai",
    auth="https://zhdrvdrojipkluhzgsea.supabase.co",
    anon_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpoZHJ2ZHJvamlwa2x1aHpnc2VhIiwicm9sZSI6"
             "ImFub24iLCJpYXQiOjE3ODgyOTU4NDksImV4cCI6MjEwMzg3MTg0OX0.fdYqIGXIXqNQXMsc9cF5_6ZHcx496SGSzheDCncAqnU",
)


def site() -> Site:
    """LIVE, or a local WorkIt that the APPLY_WORKIT_* variables name (for a developer's own stack)."""
    return Site(
        web=os.environ.get("APPLY_WORKIT_WEB") or LIVE.web,
        api=os.environ.get("APPLY_WORKIT_API") or LIVE.api,
        auth=os.environ.get("APPLY_WORKIT_AUTH") or LIVE.auth,
        anon_key=os.environ.get("APPLY_WORKIT_ANON_KEY") or LIVE.anon_key,
    )


class WorkItError(Exception):
    """WorkIt refused a call. `status` is its HTTP status, when it answered one."""

    def __init__(self, message: str = "", status: int | None = None):
        super().__init__(message)
        self.status = status


class NotLoggedIn(WorkItError):
    pass


class LoginExpired(WorkItError):
    """The session was signed out, or its refresh token was refused: sign in again."""


class Unreachable(WorkItError):
    """No answer from WorkIt (or Supabase Auth), or a server error, whose `status` it names."""


class CapReached(WorkItError):
    """WorkIt's daily cap refused the call (429; for Apply, the cap of 50 added jobs a day). `until` (epoch
    seconds) is when to try again: the response's Retry-After, else the next UTC day (WorkIt's caps count UTC
    days)."""

    def __init__(self, message: str, until: float):
        super().__init__(message, 429)
        self.until = until


class SignInOver(WorkItError):
    """WorkIt refused the sign-in's code: traded already, expired, or not this sign-in's. Sign in again."""


class Stage(StrEnum):
    """A stage of an application on WorkIt's Applications Tracker, as WorkIt
    names it (backend `dto.application_stage`). The one place Apply spells them."""

    SAVED = "saved"
    QUEUED = "queued"
    NEEDS_YOU = "needs_you"
    SKIPPED = "skipped"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"


# Applied or later: a record of an application sent (backend `dto.APPLIED_STAGES`). Apply never changes one.
APPLIED_STAGES = frozenset({Stage.APPLIED, Stage.INTERVIEWING, Stage.OFFER, Stage.REJECTED})


@dataclass(frozen=True)
class Account:
    """The signed-in account, as `GET /auth/me` returns it."""

    id: str
    email: str
    full_name: str
    account_type: str  # "applicant" (a student) or "company"


class WorkIt:
    def __init__(self, at: Site | None = None, login: Path = LOGIN, keychain: "Keychain | None" = None):
        """`login` names the lock beside it (`.lock`), and the session file Apply kept there before
        2026-11-15, deleted at the next save. `keychain` holds the refresh token (the system's by default)."""
        self.site = at or site()
        self.login = login
        self.keychain = keychain or SystemKeychain(WORKIT)
        self._account: Account | None = None  # the signed-in account, read once for the writes

    def logged_in(self) -> bool:
        """Whether the keychain holds a login. A keychain that won't answer is no login, as a missing one."""
        try:
            return self._refresh_token() is not None
        except NotLoggedIn:
            return False

    def me(self) -> Account:
        return _account(self.call("GET", "/auth/me"))

    def call(self, method: str, path: str, body: Any = None, timeout: float = TIMEOUT) -> Any:
        """One API call as the signed-in student; its JSON answer. A refused token is refreshed one time.
        Raises NotLoggedIn, LoginExpired, Unreachable, or WorkItError for another refusal. `timeout` is
        longer for a model call (apply.ask_model.WorkItAsk), which waits on WorkIt's whole model chain."""
        return self._call(method, path, body, timeout)[0]

    def _call(self, method: str, path: str, body: Any = None, timeout: float = TIMEOUT,
              binary: bool = False) -> tuple[Any, Message]:
        """`call`, with the answer's headers. With `binary`, a good answer is its bytes, not JSON."""
        for attempt in range(2):
            status, answer, headers = _send(method, self.site.api + path, body, self._bearer(refresh=attempt > 0),
                                            timeout=timeout, binary=binary)
            if status == 429:
                raise CapReached(f"{method} {path}: 429 {_detail(answer)}", _retry_at(headers.get("Retry-After")))
            if status == 401 and attempt == 0:
                continue
            if status == 401:
                raise LoginExpired("WorkIt refused the login")
            if status >= 400:
                raise WorkItError(f"{method} {path}: {status} {_detail(answer)}", status)
            return answer, headers

    # The Applications Tracker's reads and writes (KAN-545), as the signed-in student.

    def listed_by_link(self, url: str) -> tuple[str, str | None] | None:
        """The listed job at `url` and the student's stage on it (None: no application), or None when WorkIt
        does not list it. Writes nothing."""
        try:
            answer = self.call("POST", "/jobs/listed-by-link", {"url": url})
        except WorkItError as error:
            if error.status == 404:
                return None
            raise
        return str(answer["job_id"]), answer.get("stage")

    def applications(self, applicant_id: str) -> list[dict]:
        """Every application on the student's Applications Tracker, as WorkIt lists them (job, stage, applied_at)."""
        return self.call("GET", f"/applicants/{applicant_id}/applications")

    def add_by_link(self, url: str, company: str, title: str) -> tuple[str, str]:
        """Put the job at `url` on the student's Applications Tracker (an added job when WorkIt does not list it):
        its job id and the student's stage on it, saved when it is new there. `track_only` is Apply's form of
        the extension's Write with Claude add: any link, a closed job kept as it is, and no stage moved."""
        answer = self.call("POST", "/jobs/added-by-link",
                           {"url": url, "company": company, "title": title, "track_only": True})
        return str(answer["job_id"]), answer["stage"]

    def send_resume(self, applicant_id: str, job_id: str, path: Path) -> str:
        """Keep the file at `path` as a Sent resume to the job: its id."""
        answer = self.call("POST", f"/applicants/{applicant_id}/sent-resumes/file", {
            "job_posting_id": job_id, "file_name": path.name,
            "content": base64.b64encode(path.read_bytes()).decode()})
        return str(answer["id"])

    def set_stage(self, applicant_id: str, job_id: str, stage: str, applied_on: date | None = None) -> None:
        """Move the application to `stage` (applied or later); `applied_on` becomes its applied date."""
        body = {"stage": stage} | ({"applied_on": applied_on.isoformat()} if applied_on else {})
        self.call("PUT", f"/applicants/{applicant_id}/applications/{job_id}/stage", body)

    def link_resume(self, job_id: str, sent_resume_id: str) -> None:
        """Name the Sent resume the application went out with. Its stage and applied date stay."""
        self.call("POST", f"/jobs/{job_id}/applied", {"sent_resume_id": sent_resume_id})

    def unsave(self, job_id: str) -> None:
        """Delete the student's saved application on the job. WorkIt refuses (409) one past saved."""
        self.call("DELETE", f"/jobs/{job_id}/saved")

    def dequeue(self, applicant_id: str, job_id: str) -> None:
        """Delete the student's queued application on the job. WorkIt refuses (409) one past queued."""
        self.call("DELETE", f"/applicants/{applicant_id}/applications/{job_id}")

    def record_applied(self, link: str, company: str, title: str, resume: Path | None = None,
                       stage: Stage = Stage.APPLIED, applied_on: date | None = None) -> str | None:
        """Put the job at `link` on the student's Applications Tracker at `stage` (applied or later), with the
        file at `resume` kept as its Sent resume: add by link, keep the Sent resume, set the stage and the
        applied date (`applied_on`, else today), then name the Sent resume. Apply's submit writes and the Tracker
        Sheet import both use it. An application already applied or later stays as it is: answers its stage
        then, else None."""
        job, before = self.add_by_link(link, company, title)
        if before in APPLIED_STAGES:
            return before
        me = self.applicant_id()
        sent = self.send_resume(me, job, resume) if resume else None
        self.set_stage(me, job, stage, applied_on)
        if sent:
            self.link_resume(job, sent)
        return None

    def tailored_resume(self, url: str) -> bytes | None:
        """The PDF of the student's tailored resume for the listed job at `url` (Tailor, KAN-217), rendered now;
        None when WorkIt does not list the job or the student has no tailored resume for it (KAN-547). Writes
        nothing."""
        listed = self.listed_by_link(url)
        if listed is None:
            return None
        me = self.applicant_id()
        resume = next((r for r in self.call("GET", f"/applicants/{me}/built-resumes")
                       if r.get("job_posting_id") == listed[0]), None)
        if resume is None:
            return None
        return base64.b64decode(self.call("GET", f"/applicants/{me}/built-resumes/{resume['id']}/render")["pdf"])

    def send_report(self, report: dict) -> str:
        """Send report (D26, KAN-837): one Application's Record and masked Trace, as apply.report builds it, to
        WorkIt's `POST /apply-app/reports`, which keeps it until the team fixes its problem. Its id on WorkIt."""
        return str(self.call("POST", "/apply-app/reports", report, timeout=REPORT_TIMEOUT)["id"])

    def answer_bank(self) -> tuple[dict[str, dict], int]:
        """The student's whole Answer bank on WorkIt (W11, `GET .../answer-bank`), by each question's folded
        wording: {key: {question, answer, own, none?}}, and its version, from the ETag."""
        answer, headers = self._call("GET", f"/applicants/{self.applicant_id()}/answer-bank")
        version = re.fullmatch(r'\s*(?:W/)?"(\d+)"\s*', headers.get("ETag") or "")
        return answer, int(version.group(1)) if version else 0

    def change_answer_bank(self, entries: list[dict], deleted: list[str]) -> tuple[int, dict[str, str]]:
        """Save `entries` ({question, answer, review, choice, job_id | company}) to the student's Answer bank on
        WorkIt and delete the questions `deleted` (W11, `PATCH .../answer-bank`): the bank's new version, and why
        WorkIt's rule kept each entry it kept out, by question."""
        answer = self.call("PATCH", f"/applicants/{self.applicant_id()}/answer-bank",
                           {"set": entries, "delete": deleted})
        return int(answer["version"]), {str(q): str(why) for q, why in (answer.get("kept_out") or {}).items()}

    def applicant_profile(self) -> dict:
        """The student's Fill engine profile and policies on WorkIt (W11, `GET /apply-app/profile`), built as the
        extension builds them, and where each file it names is read (`files`)."""
        return self.call("GET", "/apply-app/profile")

    def save_answered(self, answered: dict, facts: dict) -> None:
        """What the student answered in Needs you, into their profile on WorkIt (`PATCH /apply-app/profile`): answers
        by question (an Essay fact's too), and facts the Fill engine read from an answer by dotted key."""
        self.call("PATCH", "/apply-app/profile", {"answered": answered, "facts": facts})

    def upload_profile(self, profile: dict, story_bank: str, voice: str) -> dict:
        """A Developer checkout's own files onto WorkIt, once (`apply upload`, `POST /apply-app/profile/upload`):
        WorkIt keeps only what it lacks, and answers how much it took."""
        return self.call("POST", "/apply-app/profile/upload",
                         {"profile": profile, "story_bank": story_bank, "voice": voice})

    def profile_file(self, where: dict) -> bytes:
        """A file the profile names, by its `files` entry: the default resume (an upload's bytes, or a built resume's
        PDF rendered now) or the transcript."""
        me = self.applicant_id()
        if "built_resume_id" in where:
            return base64.b64decode(self.call("GET", f"/applicants/{me}/built-resumes/{where['built_resume_id']}/render")["pdf"])
        path = (f"/applicants/{me}/resumes/{where['uploaded_resume_id']}/bytes" if "uploaded_resume_id" in where
                else f"/applicants/{me}/documents/transcript/bytes")
        return self._call("GET", path, binary=True)[0]

    def applicant_id(self) -> str:
        """The signed-in student's id, read once (`GET /auth/me`): the writes name it in their paths."""
        if self._account is None:
            self._account = self.me()
        return self._account.id

    def trade(self, code: str, verifier: str) -> Account:
        """The sign-in page's one-time `code` and this sign-in's PKCE `verifier`, traded for a session of
        Apply's own (`POST /apply-app/session`), which is kept; its account. For `login`, and W5's window.
        The page's `workit-auto-apply://` link, pasted in place of its code, is read for the code in it."""
        code = code.strip()
        if code.startswith(APP_LINK):
            code = parse_qs(urlsplit(code).query).get("code", [""])[0]
        status, answer, _ = _send("POST", self.site.api + "/apply-app/session", {"code": code, "verifier": verifier},
                                  None)
        if status in (400, 422):
            raise SignInOver(_detail(answer), status)
        if status >= 400:
            raise WorkItError(f"POST /apply-app/session: {status} {_detail(answer)}", status)
        with self._locked():  # a refresh in another process must not save its older login after this one
            self._save(answer)
        self._account = None
        return self.me()

    def sign_out(self) -> None:
        """End this login: its session at Supabase Auth (this one only, scope=local), then the keychain's item and
        this process's access token. WorkIt not answering still forgets it here."""
        if token := self._fresh():
            try:
                _send("POST", self.site.auth + "/auth/v1/logout?scope=local", None, token, apikey=self.site.anon_key)
            except Unreachable:
                pass  # forgotten here all the same; the session ends with its refresh token unused
        try:
            self.keychain.forget(self.site.auth)
        except RuntimeError as error:
            raise WorkItError(str(error)) from None
        _ACCESS.pop(self.site.auth, None)
        self._account = None

    def _bearer(self, refresh: bool) -> str:
        if not refresh and (fresh := self._fresh()):
            return fresh
        with self._locked():
            if not refresh and (fresh := self._fresh()):
                return fresh  # another thread refreshed while this one waited
            token = self._refresh_token()
            if token is None:
                raise NotLoggedIn("no WorkIt login in the keychain")
            status, answer, _ = _send("POST", self.site.auth + "/auth/v1/token?grant_type=refresh_token",
                                   {"refresh_token": token}, None, apikey=self.site.anon_key)
            if status != 200:
                raise LoginExpired(f"Supabase refused the refresh token: {_detail(answer)}")
            self._save(answer)
            return answer["access_token"]

    def _fresh(self) -> str | None:
        """This process's access token, while it has more than EARLY seconds left."""
        found = _ACCESS.get(self.site.auth)
        if found and found[1] - EARLY > time.time():
            return found[0]
        return None

    def _refresh_token(self) -> str | None:
        """The keychain's refresh token. A keychain that won't answer (a locked one, a Deny on macOS's prompt) is
        NotLoggedIn, never a plain WorkItError: callers keep a write waiting on that, and drop one WorkIt refused."""
        try:
            return self.keychain.password(self.site.auth)  # one item per WorkIt: a local stack's is its own
        except RuntimeError as error:
            raise NotLoggedIn(str(error)) from None

    def _save(self, session: dict) -> None:
        """The refresh token goes into the keychain, the access token stays in this process. Windows'
        Credential Manager keeps at most 2,560 bytes an item, less than an access token can be, and an
        access token kept nowhere can't be read from the disk."""
        try:
            self.keychain.save(self.site.auth, session["refresh_token"])
        except RuntimeError as error:
            # The refresh token just given is lost, and the one before was rotated: the login is over, and the
            # writes wait for the next one (NotLoggedIn's reason, _refresh_token).
            raise LoginExpired(str(error)) from None
        expires_at = session.get("expires_at") or time.time() + int(session.get("expires_in", 3600))
        _ACCESS[self.site.auth] = (session["access_token"], float(expires_at))
        self.login.unlink(missing_ok=True)  # the session file Apply kept before 2026-11-15

    @contextmanager
    def _locked(self):
        self.login.parent.mkdir(parents=True, exist_ok=True)
        with open(self.login.with_suffix(".lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield


# Each Applications Tracker stage Apply writes, as the tracker names it.
SHOWN = {Stage.APPLIED: "Applied", Stage.NEEDS_YOU: "Needs you"}


@dataclass(frozen=True)
class Write:
    """One change to the student's Applications Tracker: the job (by its link,
    company and title) goes to `stage` (Stage.APPLIED or NEEDS_YOU).
    `resume`, for applied, is the file the form was given, kept as the
    application's Sent resume. `application_id` is Apply's, so a later write
    for the same Application replaces one still waiting. `not_before` keeps
    a write WorkIt's daily cap refused (429) until the cap resets."""

    application_id: str
    link: str
    company: str
    title: str
    stage: str
    resume: str = ""
    not_before: float = 0.0  # epoch seconds: past WorkIt's daily cap, the write waits until then


def cap_wait(write: Write) -> str:
    """'waits for WorkIt's daily cap ... until <local time>' for a write the cap holds back now, else ''."""
    if write.not_before <= time.time():
        return ""
    when = datetime.fromtimestamp(write.not_before).strftime("%Y-%m-%d %H:%M")
    return f"waits for WorkIt's daily cap of added jobs until {when}"


class WaitingWrites:
    """The Waiting writes (GLOSSARY.md). Sends Writes to the Applications Tracker, and keeps each one that
    cannot reach WorkIt in a queue file until a later send or flush. One
    process at a time sends (a lock file), so a write is never sent twice
    at once."""

    def __init__(self, client: WorkIt | None = None, path: Path = QUEUE):
        self.client = client or WorkIt()
        self.path = path

    def send(self, write: Write) -> str:
        """Queue `write` (in place of a waiting one for the same Application), send every waiting write,
        and say in a few words where this one is."""
        with self._locked():
            waiting = [w for w in self._read() if w.application_id != write.application_id] + [write]
            self._keep(waiting)
            said = self._flush()
        return said.get(write.application_id, f"in your Applications Tracker as {SHOWN[write.stage]}")

    def flush(self) -> list[str]:
        """Send every waiting write, oldest first; what went wrong, a line each (nothing when all went or
        WorkIt still cannot be reached: those stay queued)."""
        with self._locked():
            return [said for said in self._flush().values() if said.startswith("not in")]

    def waiting(self) -> list[Write]:
        return self._read()

    def _flush(self) -> dict[str, str]:
        """Send the queue in order, until WorkIt cannot be reached. A write the daily cap holds back stays and
        is not sent before its `not_before`. What happened to each, by Application."""
        said, waiting, kept = {}, self._read(), []
        for at, write in enumerate(waiting):
            if cap_wait(write):
                said[write.application_id] = f"kept to send to your Applications Tracker: it {cap_wait(write)}"
                kept.append(write)
                continue
            try:
                said[write.application_id] = self._deliver(write)
            except (NotLoggedIn, LoginExpired) as error:
                for w in waiting[at:]:
                    said[w.application_id] = f"kept to send to your Applications Tracker later ({error}): " \
                                             "run `apply login`"
                break
            except Unreachable as error:
                for w in waiting[at:]:
                    said[w.application_id] = f"kept to send to your Applications Tracker later ({error})"
                break
            except CapReached as error:
                kept.append(dataclasses.replace(write, not_before=error.until))
                said[write.application_id] = f"kept to send to your Applications Tracker: it {cap_wait(kept[-1])}"
            except WorkItError as error:  # refused for good: sending it again would fail again
                said[write.application_id] = f"not in your Applications Tracker: WorkIt refused it ({error})"
            self._keep(kept + waiting[at + 1:])
        return said

    def _deliver(self, write: Write) -> str:
        if write.stage == Stage.APPLIED:
            resume = Path(write.resume) if write.resume else None
            before = self.client.record_applied(write.link, write.company, write.title,
                                                resume if resume and resume.is_file() else None)
            if before:
                return f"already {SHOWN.get(before, before)} in your Applications Tracker"
        else:
            job, _ = self.client.add_by_link(write.link, write.company, write.title)
            try:
                self.client.set_stage(self.client.applicant_id(), job, write.stage)
            except WorkItError as refused:
                if refused.status != 409:
                    raise
                return "already Applied in your Applications Tracker"
        return f"in your Applications Tracker as {SHOWN[write.stage]}"

    def _read(self) -> list[Write]:
        try:
            # A Hold an older Apply kept as queued goes as needs_you (KAN-544).
            return [Write(**{**w, "stage": Stage.NEEDS_YOU if w["stage"] == Stage.QUEUED else w["stage"]})
                    for w in json.loads(self.path.read_text())]
        except FileNotFoundError:
            return []

    def _keep(self, waiting: list[Write]) -> None:
        if not waiting:
            self.path.unlink(missing_ok=True)
            return
        part = self.path.with_suffix(".part")
        part.write_text(json.dumps([dataclasses.asdict(w) for w in waiting], indent=1))
        part.replace(self.path)

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_suffix(".lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield


def pkce() -> tuple[str, str]:
    """A new sign-in's PKCE verifier and its S256 challenge (RFC 7636): the page gets the challenge, and
    only this verifier trades the code the page gives."""
    verifier = secrets.token_urlsafe(64)
    return verifier, base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def sign_in_page(at: Site, challenge: str) -> str:
    """WorkIt's sign-in page for the app (`frontend/src/app/app-sign-in/`)."""
    return f"{at.web}/app-sign-in?challenge={challenge}"


def _paste(url: str) -> str:
    """A Developer checkout's sign-in: the page in the default browser, and the code it shows, pasted here.
    macOS hands the page's `workit-auto-apply://` link only to the built app (W8)."""
    # Straight to the terminal: the shell's masked output (apply.masked) hides the challenge, a long opaque value,
    # and a developer whose browser doesn't open needs the link. The challenge is no secret; its verifier is.
    print(f"Sign in to WorkIt in your browser ({url}), press Sign In to the App, then copy the code here.",
          file=sys.__stdout__ or sys.stdout)
    webbrowser.open(url)
    return input("Code: ")


def login(client: WorkIt, browser: Callable[[str], str] = _paste) -> Account:
    """Sign in to WorkIt in the student's own browser and keep the session: `apply login`. `browser(url)`
    opens WorkIt's sign-in page and returns the code it gave (`_paste` by default)."""
    verifier, challenge = pkce()
    return client.trade(browser(sign_in_page(client.site, challenge)), verifier)


def _send(method: str, url: str, body: Any, token: str | None, apikey: str | None = None,
          timeout: float = TIMEOUT, binary: bool = False) -> tuple[int, Any, Message]:
    """The status, JSON answer (with `binary`, a good answer's bytes) and headers. No answer, or a 5xx, is
    Unreachable."""
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if apikey:
        headers["apikey"] = apikey
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_pinned(url)) as response:
            status, raw, headers = response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        status, raw, headers = error.code, error.read(), error.headers
    except (OSError, urllib.error.URLError) as error:
        raise Unreachable(f"{urlsplit(url).netloc}: {getattr(error, 'reason', error)}") from None
    if status >= 500:
        raise Unreachable(f"{urlsplit(url).netloc}: {status}", status)
    if binary and status < 400:
        return status, raw, headers
    try:
        return status, json.loads(raw) if raw else None, headers
    except ValueError:
        return status, raw.decode(errors="replace")[:200], headers


# The hosts whose TLS trusts only Cloudflare's CAs: the live API, and the live Supabase Auth, which sees the session.
PINNED = frozenset(urlsplit(url).hostname for url in (LIVE.api, LIVE.auth))


def _pinned(url: str) -> ssl.SSLContext | None:
    """The TLS context of a PINNED host, which trusts only Cloudflare's CAs; None (the default) for any other."""
    return _pinned_context() if urlsplit(url).hostname in PINNED else None


@cache
def _pinned_context() -> ssl.SSLContext:
    from apply.workit_roots import ROOTS

    return ssl.create_default_context(cadata=ROOTS)


def _retry_at(retry_after: str | None) -> float:
    """When to try a capped call again: Retry-After (seconds or an HTTP date), else the next UTC midnight."""
    if retry_after:
        if retry_after.strip().isdigit():
            return time.time() + int(retry_after)
        try:
            return email.utils.parsedate_to_datetime(retry_after).timestamp()
        except (TypeError, ValueError):
            pass
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    return datetime.combine(tomorrow, dtime(), UTC).timestamp()


def _detail(answer: Any) -> str:
    if isinstance(answer, dict):
        return str(answer.get("error_description") or answer.get("detail") or answer.get("error") or answer)[:200]
    return str(answer)[:200]


def _account(answer: dict) -> Account:
    return Account(id=str(answer["id"]), email=answer["email"], full_name=answer.get("full_name", ""),
                   account_type=answer.get("account_type", ""))


def job_key(url: str) -> str:
    """One job's key, as WorkIt matches links (KAN-542): the Greenhouse job ID, else the link without its
    scheme, www., query, fragment and trailing slash, lower case."""
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    if (parts.hostname or "").lower().endswith("greenhouse.io"):
        if m := re.match(r"/[\w-]+/jobs/(\d+)(?:/|$)", parts.path):
            return f"greenhouse:{m[1]}"
        if parts.path.startswith("/embed/job_app") and query.get("token", [""])[0].isdigit():
            return f"greenhouse:{query['token'][0]}"
    if query.get("gh_jid", [""])[0].isdigit():
        return f"greenhouse:{query['gh_jid'][0]}"
    return re.sub(r"^[a-z][a-z0-9+.-]*://(www\.)?", "", url, flags=re.IGNORECASE).split("#")[0].split("?")[0].rstrip("/").lower()
