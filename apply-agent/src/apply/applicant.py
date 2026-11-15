"""Who Claude writes as: the applicant the Applicant profile names.

Prompts, the answering guides and the cover letter's slots say NAME where the
applicant's first name goes and SCHOOL where their school goes. as_applicant
wraps a Claude so every call it is sent says the profile's own name and school
instead, wherever the prompt was built, and is sent none of their private
details (apply.private). Every adapter a run, the window or a command uses is
wrapped once where it is built, so no kind skips it.
"""

import json
import re

from apply import private
from apply.profile import ApplicantProfile

NAME, SCHOOL = "@NAME@", "@SCHOOL@"

# The pronouns WorkIt takes with a kind (backend apply_prompts/kind.py, Data.pronouns): one short line. Free text
# longer than that would make WorkIt refuse every call; the neutral default goes in its place.
PRONOUNS = re.compile(r"[^\n\r<>{}]{1,40}")


def first_name(profile: ApplicantProfile) -> str:
    """The name they go by, else their legal first name."""
    return profile.get("identity.preferred_first_name") or profile.get("identity.legal_first_name") or "the applicant"


def named(text: str, profile: ApplicantProfile) -> str:
    """`text` with NAME and SCHOOL said as the profile gives them."""
    return (text.replace(NAME, first_name(profile))
            .replace(SCHOOL, profile.get("education.school") or "their school"))


def pronouns_note(profile: ApplicantProfile) -> str:
    """The line that tells Claude which pronouns to use for the applicant.
    Without it, Claude guesses from the name, and a plan or a reason can call
    a they/them applicant "he"."""
    pronouns = str(profile.get("identity.pronouns") or "they/them/theirs").strip()
    return (f"\n\n{NAME}'s pronouns are {pronouns}. Wherever you write about {NAME} in the third person "
            "(a plan, a note, a reason), use these pronouns only.")


class as_applicant:
    """`claude`, with every ask said as `profile`'s applicant (named), and
    told the applicant's pronouns."""

    def __init__(self, claude, profile: ApplicantProfile):
        # Wrapped once: a run's adapter already is, and essays.py wraps what a test hands it too.
        self._claude, self._profile = (claude._claude if isinstance(claude, as_applicant) else claude), profile

    def ask_kind(self, kind: str, data: dict) -> dict:
        """`kind` said as the applicant: WorkIt adds the pronouns note and names the school from what this
        sends; the private details go as placeholders (apply.private), and they and the name, which stays NAME
        in every prompt WorkIt builds (D8), go back into the answer."""
        pronouns = str(self._profile.get("identity.pronouns") or "").strip()
        said = {"pronouns": pronouns if PRONOUNS.fullmatch(pronouns) else "they/them/theirs",
                "school": self._profile.get("education.school") or ""}
        hidden = private.values(self._profile)
        given = private.put_back(self._claude.ask_kind(kind, {**private.mask(data, hidden), **said}), hidden)
        return json.loads(json.dumps(given).replace(NAME, json.dumps(first_name(self._profile))[1:-1]))

    def __getattr__(self, name: str):
        return getattr(self._claude, name)
