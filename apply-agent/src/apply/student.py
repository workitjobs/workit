"""The Student build's own path (KAN-723, W3): WorkIt Auto Apply is compiled from this module, with every module in
`apply.build.DEVELOPER` left out. It fills and holds forms as `apply rehearse` does, and never submits.

`adapters()` gives a run everything outside Apply, with each developer part replaced by one that does nothing:
no `claude -p` (no drive, no research), no Gmail, no notifications or phone push, and no Repairs. W5's window
starts here (`app`, which `uv run apply app` runs) and calls `rehearsal.rehearse` with them.
"""

from apply import (  # noqa: F401 (rehearsal: W5 runs it)
    already_applied,
    answer_sync,
    answering,
    app_window,
    captcha,
    home,
    rehearsal,
    tailored,
)
from apply.adapters import Adapters, ClaudeError, UsageReading
from apply.answer_bank import FILE as ANSWER_BANK
from apply.answers_tab import AnswersTab
from apply.applicant import as_applicant
from apply.ask_model import live_claude
from apply.clock import SystemClock
from apply.dashboard import Dashboard, NoFrames
from apply.feed import live_feed
from apply.home import HOME
from apply.keychain import SystemKeychain
from apply.plain.site import live_site
from apply.profile import ApplicantProfile
from apply.records import FolderRecords
from apply.tracker import InMemoryTracker
from apply.workit import WorkIt

RECORDS = HOME / "rehearsals"  # each held form's Record, as `apply rehearse` keeps them
NO_MODEL = "WorkIt Auto Apply doesn't {what}: a person does it, or WorkIt's Model route"
NO_MAIL = "WorkIt Auto Apply reads no email: type the code or open the link from your inbox yourself"


class NoClaude:
    """The Student build's stand-in for `claude -p` (apply.claude_cli), which it doesn't have. A text call goes to
    the hosted models in front of it (ask_model.HostedAsk), never here; a model never drives a page or researches
    the web in the app (D2, D13). It is also the run's usage, which W1 reads from the Model route."""

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


def adapters(profile: ApplicantProfile) -> Adapters:
    """What a Student build's run touches. The policies are the Student build's own (apply.build.STUDENT_POLICIES)."""
    policies = profile.policies()
    claude = NoClaude()
    site = live_site(policies)
    answering.refresh(WorkIt())  # WorkIt's Question types, for the run's essays
    return Adapters(
        feed=live_feed(),
        tracker=InMemoryTracker(),
        site=site,
        claude=as_applicant(live_claude(policies, claude), profile),  # no private detail in a kind (apply.private)
        mailbox=NoMailbox(),
        usage=claude,
        clock=SystemClock(),
        records=FolderRecords(RECORDS),
        notifier=Silent(),
        phone=None,
        keychain=SystemKeychain(),
        repairs=NoRepairs(),
        answer_bank=answer_sync.bank(profile.folder / ANSWER_BANK, policies),
        signed_in=site.signed_in(),
        tailored=tailored.from_workit(),
        everyday=captcha.to_everyday_chrome,
        applied_before=already_applied.Check(),
    )


def app() -> None:
    """WorkIt Auto Apply: its window (apply.app_window), with no port. It signs the student in, then shows the Apply
    window with their answers (W5 step 2). First run, the queue and a run join it in W5's next steps."""
    if home.fill_from_sample():
        print(f"No Applicant profile yet: WorkIt Auto Apply runs as Test Person from {HOME} till yours is there.")
    profile = ApplicantProfile.load(HOME / "applicant-profile.yaml")
    answers = AnswersTab(answer_sync.bank(profile.folder / ANSWER_BANK, profile.policies()), profile)
    with Dashboard(0, NoFrames(), answers, sample=profile.get("sample_data") is True, serve=False) as board:
        app_window.run(board)
