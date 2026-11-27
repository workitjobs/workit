"""The Safety level (GLOSSARY): one setting, "How careful should Apply be?", that sets several answer and hold
policies at once. It is asked once in the first run (apply.first_run), changed in the window's Settings, and kept
as `safety_level` in the developer's policies.yaml (a Developer checkout) or in the data folder's app.json (the
Student build, which reads no policies.yaml).

- careful: today's behaviour. Every attestation and acknowledgment is the applicant's to tick, an opinion question
  with no backed fact waits for them, every Ashby essay and the first ten Applications are held, nothing auto-submits.
- balanced: arbitration, GDPR and privacy acknowledgments are ticked and opinion questions are answered from the
  closest backed facts; the holds stay and nothing auto-submits.
- full_auto: balanced, and every certification, acknowledgment, release and consent box is ticked (truth
  certifications, "I have personally completed this application", reference and background-check releases, at-will,
  drug-test and security-check acknowledgments), a background check, drug screen or reference check an offer depends
  on is agreed to, an e-signature or self-ID form's signature is signed with the name and today's date, the
  review-only holds (High-stakes essays, the Calibration run) are lifted, and a ready form auto-submits, essays and
  all (Lisul, 2026-11-27). A box that states a fact ("I have a valid driver's license") still follows the profile.

A level only sets each policy's default: a key the applicant's policies.yaml sets itself wins over its level.

No level ever touches the hard guards (HARD_GUARDS): bot checks and captchas stay the applicant's, essays never invent
a fact or name the tools that wrote them, take-home tests are never done, and the company and daily caps hold. Nor does
any level tick a box aimed at bots or hidden from people (the Fill engine's traps): a person leaves those unticked.
"""

from pathlib import Path

from apply.home import HOME

# Where the window keeps what the first run and Settings chose (apply.first_run's STATE).
STATE = HOME / "app.json"
CAREFUL, BALANCED, FULL_AUTO = "careful", "balanced", "full_auto"
DEFAULT = CAREFUL
KEY = "safety_level"

LEVELS: dict[str, dict] = {
    CAREFUL: {
        "tick_arbitration": False,
        "tick_attestations": False,
        "willing_to_undergo_checks": None,
        "sign_self_id": False,
        "answer_opinion_questions": False,
        "hold_high_stakes_essays": True,
        "high_stakes_job_systems": ["ashby"],
        "calibration_run": 10,
        "auto_submit": False,
        "auto_submit_essays": False,
    },
    BALANCED: {
        "tick_arbitration": True,
        "tick_attestations": False,
        "willing_to_undergo_checks": None,
        "sign_self_id": False,
        "answer_opinion_questions": True,
        "hold_high_stakes_essays": True,
        "high_stakes_job_systems": ["ashby"],
        "calibration_run": 10,
        "auto_submit": False,
        "auto_submit_essays": False,
    },
    FULL_AUTO: {
        "tick_arbitration": True,
        "tick_attestations": True,
        "willing_to_undergo_checks": True,
        "sign_self_id": True,
        "answer_opinion_questions": True,
        "hold_high_stakes_essays": False,
        "high_stakes_job_systems": [],
        "calibration_run": 0,
        "auto_submit": True,
        "auto_submit_essays": True,
    },
}

# The window's words for each level (first run and Settings).
SAID = {
    CAREFUL: ("Careful", "You tick every acknowledgment and signature, answer opinion questions yourself, and approve "
                         "every Ashby essay and your first ten Applications. Nothing is submitted without you."),
    BALANCED: ("Balanced", "Apply ticks arbitration and privacy acknowledgments and answers opinion questions from your "
                           "own facts. Essays and your first ten Applications still wait for you."),
    FULL_AUTO: ("Full auto", "Apply also ticks every certification, acknowledgment and consent box, agrees to the "
                             "background and drug checks an offer depends on, signs e-signatures and self-identification forms with your "
                             "name and today's date, holds nothing "
                             "just for review, and (in a Developer checkout) submits a ready form after a 10-minute countdown."),
}
ALWAYS = ("At every level, Apply never does a bot check or captcha, never ticks a box meant to catch bots, never "
          "invents a fact or names the tools that wrote an essay, never does a take-home test, and keeps to the "
          "company and daily caps.")

# Policies a level must never set: what stays the applicant's, or stays capped, whatever they choose.
HARD_GUARDS = frozenset({"company_cap", "daily_cap", "captcha_wait_minutes", "page_gates", "live_runs",
                         "attest_from_sources", "employer_limits"})


def level_of(user: dict, state: Path | None = None) -> str | None:
    """The level the applicant chose: their policies.yaml's, else the data folder's app.json's; None when neither
    names a known one."""
    for chosen in (user.get(KEY), _kept(state).get(KEY) if state else None):
        if chosen in LEVELS:
            return chosen
    return None


def resolve(defaults: dict, user: dict, state: Path | None = None) -> dict:
    """The policies: `defaults`, then the chosen level's (DEFAULT when none is chosen), then the applicant's own
    keys (`user`), each over the last."""
    level = level_of(user, state) or DEFAULT
    return defaults | LEVELS[level] | user | {KEY: level}


def _kept(state: Path) -> dict:
    import json

    try:
        kept = json.loads(state.read_text())
    except (OSError, ValueError):
        return {}
    return kept if isinstance(kept, dict) else {}
