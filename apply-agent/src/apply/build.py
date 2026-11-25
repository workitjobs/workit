"""Which build of Apply this is (KAN-723, W3): a Developer checkout, or the Student build, which is WorkIt Auto
Apply (D14 in docs/desktop_application_auto_apply.md).

The Student build's script writes `STUDENT = True` here before it compiles, and compiles from `apply.student`
with every module in DEVELOPER left out (Nuitka's --nofollow-import-to, W8). Nothing at run time sets it: no
policy, no setting, no environment variable, no key. Code reads it as `build.STUDENT` when it runs, never copies it
at import, so a test can set it.

A module in DEVELOPER is never imported at the top of a module on the Student path, only inside a function that
the Student build never reaches (`tests/test_student_build.py`).
"""

STUDENT = False

# Left out of the Student build. Each one is a developer part: `claude -p` and every path that drives a page with
# it, Repairs, reading Gmail, the phone push and the Mac's notifications, the Daily sweep, the Dock keeper, the
# retired Tracker Sheet, and the commands that only run from a terminal.
DEVELOPER = frozenset({
    "apply.claude_cli",  # `claude -p`: ask_model: claude, research, drive, Claude Code's usage
    "apply.local_prompts",  # WorkIt's prompts built from a checkout's backend, for `apply app --max-plan`
    "apply.claude_fill",  # drive: Claude fill
    "apply.rescue",  # drive: Rescue
    "apply.ask",  # drive: Ask Claude, and `apply ask`
    "apply.repair",  # Repairs
    "apply.repairer",
    "apply.gmail",  # mail (D9: an emailed code is the student's to type)
    "apply.email_code",
    "apply.employer_mail",
    "apply.notify",  # the Mac's notifications and the ntfy phone push (D10)
    "apply.schedule",  # the Daily sweep
    "apply.dock_app",  # the Dock keeper (W5's window replaces it)
    "apply.sheet",  # the retired Tracker Sheet
    "apply.sheet_import",
    "apply.tracker_cleanup",  # `apply clean-tracker`
    "apply.doctor",
    "apply.cli",  # every command that runs from a terminal
})

# The Student build's policies, laid over policies.default.yaml. It reads no policies.yaml, so every key is the
# default's; these stay so even if a default changes. Only keys the Student path reads: live_runs, repair,
# records_remote and resume_source are read only by modules in DEVELOPER.
STUDENT_POLICIES = {
    "ask_model": "workit",  # WorkIt's Model route (W1, D5): the app holds no model key
    "fill_engine": "workit",  # WorkIt's signed download (W7, D3): the app ships no engine
    "ask_models": {},
    "phone_push": False,
}
