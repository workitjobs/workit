"""The Student build's own path (KAN-723, W3): WorkIt Auto Apply is compiled from this module, with every module in
`apply.build.DEVELOPER` left out. It fills and holds forms as `apply rehearse` does, and never submits.

`adapters()` gives a run everything outside Apply, with each developer part replaced by one that does nothing:
no `claude -p` (no drive, no research), no Gmail, no notifications or phone push, and no Repairs. W5's window
starts here (`app`, which `uv run apply app` runs) and calls `rehearsal.rehearse` with them.
"""

import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

from apply import (
    already_applied,
    answering,
    app_window,
    captcha,
    home,
    rehearsal,
    tailored,
    worker_tiles,
)
from apply.accounts_tab import AccountsTab
from apply.adapters import Adapters, ClaudeError, SetupError, UsageReading
from apply.answer_bank import AnswerBank, WorkItSource
from apply.answers_tab import AnswersTab, saving_answers
from apply.applicant import as_applicant
from apply.ask_model import live_claude
from apply.awake import awake
from apply.browsers import ProfileInUse
from apply.clock import SystemClock
from apply.dashboard import Dashboard, NoFrames
from apply.feed import live_feed
from apply.first_run import workers
from apply.home import HOME
from apply.keychain import SystemKeychain
from apply.plain.site import live_site
from apply.profile import ApplicantProfile, load_policies
from apply.records import FolderRecords
from apply.tracker import FileTracker, WorkItTracker
from apply.worker import sent_resume
from apply.workit import WaitingWrites, WorkIt, WorkItError, site

RECORDS = HOME / "rehearsals"  # each held form's Record, as `apply rehearse` keeps them
NO_MODEL = "WorkIt Auto Apply doesn't {what}: a person does it, or WorkIt's Model route"
NO_MAIL = "WorkIt Auto Apply reads no email: type the code or open the link from your inbox yourself"


class NoClaude:
    """The Student build's stand-in for `claude -p` (apply.claude_cli), which it doesn't have. A text call goes to
    the hosted models in front of it (ask_model.HostedAsk), never here; a model never drives a page or researches
    the web in the app (D2, D13). Its usage is never limited: the run's is WorkIt's Usage cap (WorkItAsk.reading)."""

    def ask(self, **_) -> dict:
        raise ClaudeError(NO_MODEL.format(what="call claude -p"))

    def drive(self, **_):
        raise ClaudeError(NO_MODEL.format(what="let a model drive the form"))

    def research(self, **_) -> dict:
        raise ClaudeError(NO_MODEL.format(what="research companies on the web"))

    def spent(self) -> int:
        return 0

    def reading(self) -> UsageReading:
        return UsageReading()


class NoMailbox:
    """No Gmail (apply.gmail): the student types an emailed code or opens an emailed link (D9)."""

    def unavailable(self) -> str | None:
        return NO_MAIL

    def find_code(self, **_) -> None:
        return None

    def find_mailed_code(self, **_) -> None:
        return None

    def find_link(self, **_) -> None:
        return None


class Silent:
    """No notifications (apply.notify): the window shows what waits on the student."""

    def notify(self, title: str, message: str) -> None:
        pass


class NoRepairs:
    """No Repairs (apply.repair): nothing is kept for one. The Student path keeps none (keep_repair_requests), so
    this only fills the slot, which would otherwise load apply.repair."""

    def add(self, request) -> bool:
        return False


def adapters(profile: ApplicantProfile, bank: AnswerBank) -> Adapters:
    """What a Student build's run touches, with the app's one Answer bank. The policies are the Student build's own
    (apply.build.STUDENT_POLICIES)."""
    policies = profile.policies()
    site = live_site(policies)
    answering.refresh(WorkIt())  # WorkIt's Question types, for the run's essays
    asks = as_applicant(live_claude(policies, NoClaude()), profile)  # no private detail in a kind (apply.private)
    resume = Path(str(profile.get("files.resume_pdf") or "")).name
    return Adapters(
        feed=live_feed(),
        # Apply's Tracker in the data folder, as a Developer checkout's: the Employer accounts (and so their
        # passwords' keychain items, for Remove All My Data) outlive a launch, and the student's own Submit is
        # written to their Applications Tracker on WorkIt with the resume the form was given (KAN-544).
        tracker=WorkItTracker(FileTracker(), WaitingWrites(), lambda application: sent_resume(application, resume)),
        site=site,
        claude=asks,
        mailbox=NoMailbox(),
        usage=asks,  # WorkIt's Usage cap: the run pauses there until it resets (ask_model.WorkItAsk.reading)
        clock=SystemClock(),
        records=FolderRecords(RECORDS),
        notifier=Silent(),
        phone=None,
        keychain=SystemKeychain(),
        repairs=NoRepairs(),
        answer_bank=bank,
        signed_in=site.signed_in(),
        tailored=tailored.from_workit(),
        everyday=captcha.to_everyday_chrome,
        applied_before=already_applied.Check(),
    )


def tracker_url() -> str:
    """The student's Applications Tracker on WorkIt, which History's link opens in the default browser: every
    application is there, not only this Mac's."""
    return f"{site().web}/applications"


# How long Start waits for an Answer bank that hasn't read yet, as it tries again.
BANK_WAIT = 5.0

# A stopped run ends once its Workers' Chromes have let go of their profiles, so a Start right after Stop finds them
# free (KAN-874): a fill under way when Stop came runs on to its own end. At most FREE_WAIT seconds, looked at each
# FREE_POLL.
FREE_WAIT = 60.0
FREE_POLL = 0.5


def free(site) -> None:
    """Wait till no Worker profile of `site` is open in a Chrome, at most FREE_WAIT seconds."""
    refuse = getattr(site, "refuse_in_use", None)
    ending = time.monotonic() + FREE_WAIT
    while refuse:
        try:
            refuse()
            return
        except ProfileInUse:
            if time.monotonic() >= ending:
                return
            time.sleep(FREE_POLL)


class Runs:
    """The window's runs (W5 step 4): each Start rehearses its links in the Workers and shows the run's own Apply
    window, its tiles, while it goes. Apply never presses Submit: each form is held for the student."""

    def __init__(self, profile: ApplicantProfile, bank: AnswerBank,
                 make: Callable[[ApplicantProfile, AnswerBank], Adapters] = adapters,
                 rehearse: Callable[..., object] = rehearsal.rehearse,
                 keep_awake: Callable[[], AbstractContextManager] = awake,
                 refresh: Callable[[], None] = lambda: None):
        """`refresh` puts the student's profile in as each Start begins: WorkIt's (`profile_from_workit`) in the
        app."""
        self._profile, self._bank, self._make, self._rehearse, self._awake = profile, bank, make, rehearse, keep_awake
        self._refresh = refresh
        self._site = None  # the run's Workers, to stop when the app quits

    def run(self, links: list[str], show: Callable[[Dashboard], None], jobs: dict[str, str] | None = None) -> None:
        """Rehearse `links` with the run's own Apply window shown (`show`), till every form it held is closed. `jobs`
        names the WorkIt job of each link from the student's Auto Apply queue. A run waits for the Answer bank
        (W11): one that hasn't read yet is tried again, a few seconds at most. Then it reads the profile."""
        if not self._bank.wake(BANK_WAIT):
            raise SetupError("Your Answer bank hasn't come from WorkIt yet: WorkIt Auto Apply keeps trying. "
                             "Press Start again in a moment.")
        self._refresh()
        with self._awake():  # the Mac never sleeps mid-run (KAN-885)
            self._rehearse_shown(links, show, jobs or {})

    def _rehearse_shown(self, links: list[str], show: Callable[[Dashboard], None], jobs: dict[str, str]) -> None:
        made = self._make(self._profile, self._bank)
        made.jobs = jobs
        self._site = site = made.site
        try:
            answers = AnswersTab(made.answer_bank, self._profile, held=made.tracker.rows)
            accounts = AccountsTab(made.tracker.employer_accounts, made.keychain, rows=made.tracker.rows,
                                   everyday=made.everyday)
            in_front = getattr(site, "in_front", None)
            with worker_tiles.frames_for(site, len(links)) as frames, \
                    Dashboard(len(links), frames, answers, show=getattr(site, "show", None),
                              quiet=getattr(site, "plain", None), everyday=made.everyday, accounts=accounts,
                              sample=self._profile.get("sample_data") is True, tracker_url=tracker_url(),
                              back=(lambda worker: in_front(worker) and app_window.bring_forward()) if in_front else None,
                              notify=app_window.notify, answer=saving_answers(lambda: made.tracker, answers),
                              serve=False) as board:
                made.board = board
                show(board)
                self._rehearse(links, made, self._profile, workers())
        finally:
            self.close()
            free(site)

    def close(self) -> None:
        """Stop the run's plain Workers' Chromes, which outlive the app (worker_tiles.close_workers)."""
        if self._site is not None:
            worker_tiles.close_workers(self._site)
            self._site = None


# The files the student's profile names, as WorkIt gave them at the last Start: the default resume, the transcript.
FILES = HOME / "files"


def profile_from_workit(profile: ApplicantProfile, client: WorkIt | None = None) -> None:
    """The student's profile and policies from WorkIt (W11: the app keeps no profile file and no Test Person), read
    at each Start, so an edit on WorkIt's website reaches the next run. The files it names are read too and kept in
    FILES, which a form's upload takes by their path. Raises SetupError, with nothing changed, when WorkIt doesn't
    answer."""
    client = client or WorkIt()
    try:
        got = client.applicant_profile()
        facts = got["profile"]
        for key, fact in (("resume", "resume_pdf"), ("transcript", "unofficial_transcript_pdf")):
            if where := got["files"].get(key):
                FILES.mkdir(parents=True, exist_ok=True)
                path = FILES / Path(where["name"]).name  # a name, never a path WorkIt could steer
                path.write_bytes(client.profile_file(where))
                facts.setdefault("files", {})[fact] = str(path)
    except WorkItError as error:
        raise SetupError(f"Your profile didn't come from WorkIt ({error}). Press Start again in a moment.") from None
    got["policies"].pop("how_heard", None)  # "How did you hear about us?" stays Apply's: the extension answers "WorkIt"
    profile.refresh(facts, layered(load_policies(), got["policies"]))


def to_workit(changes: list[tuple]) -> None:
    """A profile save, into the student's profile on WorkIt: their Needs you answers, and the facts the Fill engine
    read from them. A file's path is this Mac's, never sent."""
    answered = {question: answer for kind, question, answer in changes if kind == "answered"}
    facts = {key: value for kind, key, value in changes if kind != "answered" and not key.startswith("files.")}
    if answered or facts:
        WorkIt().save_answered(answered, facts)


def layered(under: dict, over: dict) -> dict:
    """`over` laid over `under`, section by section, as the extension lays them (WorkIt's policies over the Student
    build's own): an empty value leaves `under`'s, so WorkIt's empty high_stakes_job_systems keeps Apply's [ashby]."""
    out = dict(under)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = layered(out[key], value)
        elif value not in (None, "", [], {}):
            out[key] = value
    return out


def app() -> None:
    """WorkIt Auto Apply: its window (apply.app_window), with no port. It signs the student in, takes them through
    first run, then shows their Auto Apply queue and runs it (W5). The profile and the Answer bank are WorkIt's
    (W11): the bank is read in the background, so the window opens at once while it reads, and the profile at each
    Start."""
    HOME.mkdir(parents=True, exist_ok=True)
    home.STORY_BANK.touch()  # an empty Story bank, which every essay reads: the app has no Test Person's (W11)
    profile = ApplicantProfile({}, HOME, load_policies(), saver=to_workit)
    bank = AnswerBank(WorkItSource())
    bank.load_in_background()
    answers = AnswersTab(bank, profile)
    runs = Runs(profile, bank, refresh=lambda: profile_from_workit(profile))
    try:
        with Dashboard(0, NoFrames(), answers, tracker_url=tracker_url(), serve=False) as board:
            app_window.run(board, start=runs.run)
    finally:
        runs.close()
        bank.close()  # the changes still on their way to WorkIt get a few seconds
