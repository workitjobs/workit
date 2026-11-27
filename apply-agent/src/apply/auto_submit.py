"""Auto-submit (ADR 0006): a held form Apply submits by itself, ten minutes after it is ready, unless the student
presses Cancel first.

It is the `auto_submit` policy, off by default, and a Developer checkout's only: the Student build reads no
policies.yaml, so it never auto-submits. A form goes only when nothing about it needs a person:

- it passed the Pre-submit check with no flags: no problem, no Missing fact, no legal hold, no answer left behind,
  and no reason to hold it (a review flag, an overused answer, the Calibration run);
- Claude wrote no Essay for it, in a text box or as a file, unless `auto_submit_essays` is on (the Safety level's
  full_auto): then an Essay that passed every check (no hold) goes too;
- it names its company;
- it never paused for the student (a sign-in, a captcha, an emailed code);
- it isn't for a Target company;
- its job system doesn't email a code after Submit (Greenhouse's security code);
- Apply didn't make an Employer account for it in this run (today);
- Apply has submitted to its job system before, so the job system's confirmation is a known one ("other", any
  careers site Apply doesn't know, never counts as known).

Once it counts down, any change Apply makes to the held page (an answer from the window, Ask Claude, a regenerated
answer) ends the countdown: what changed wasn't checked.

Anything else stays a Review card for the student to approve. The press itself is Approve and submit's
(apply.send_button), with its confirmation and its Handoff when none comes.
"""

from datetime import date

from apply.model import Status, is_company

WAIT_S = 600
TITLE = "WorkIt Auto Apply"
NOTICE = "Submitting {} in {} minutes. Open Auto Apply to cancel."
CANCELLED = "Auto-submit cancelled: it's yours to approve."
CHANGED_SAID = "Auto-submit stopped: an answer changed after the check, so it's yours to approve."
# Job systems that can email a code once Submit is pressed (apply.email_code): never auto-submitted.
CODES = frozenset({"greenhouse"})

FLAGGED = "the Pre-submit check flagged something"
HELD = "it's held for a review"
NO_COMPANY = "Apply couldn't tell which company it's for"
ESSAY = "it has an Essay"
PAUSED = "it paused for you"
TARGET = "it's a Target company"
CODE = "{} can email a code after Submit"
ACCOUNT = "Apply made its account today"
NEW_SYSTEM = "Apply hasn't submitted to {} before"
NOT_READY = "it isn't ready to submit"


def desktop(notifier):
    """macOS Notification Center, beside the run's own `notifier` (a checkout's `apply rehearse` only records its
    notices); None where the run already notifies there, or off a Mac."""
    import sys

    from apply.notify import MacNotifier

    return None if sys.platform != "darwin" or isinstance(notifier, MacNotifier) else MacNotifier()


def on(profile) -> bool:
    """Whether this checkout auto-submits at all: the policy, set to true on purpose, never in the Student build."""
    from apply import build

    return not build.STUDENT and profile.policy("auto_submit") is True


def why_not(done, ready: str, profile, tracker, today: date) -> str:
    """Why the held form `done` (rehearsal.Rehearsed) can't be auto-submitted; "" when it can. `ready` is the
    outcome of a form filled to its last page."""
    p = done.posting
    system = (p.job_system or "").lower()
    if done.outcome != ready:
        return NOT_READY
    if done.problems or done.missing or done.legal or done.left_behind:
        return FLAGGED
    if done.why:
        return HELD
    essay = done.saved and done.saved.essays or done.form and any(w.essay is not None for w in done.form.written)
    if essay and profile.policy("auto_submit_essays") is not True:  # with it, an essay that passed every check goes
        return ESSAY
    if done.history:
        return PAUSED
    if not (p.company or "").strip():
        return NO_COMPANY
    if any(is_company(p.company, name) for name in profile.policy("target_companies") or []):
        return TARGET
    if system in CODES:
        return CODE.format(p.job_system)
    if any(a.created == today and is_company(p.company, a.company) for a in tracker.employer_accounts()):
        return ACCOUNT
    if system in ("", "other") or not any(r.status == Status.SUBMITTED and (r.job_system or "").lower() == system
                             for r in tracker.rows()):
        return NEW_SYSTEM.format(p.job_system or "this job system")
    return ""
