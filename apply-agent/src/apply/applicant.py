"""Who Claude writes as: the applicant the Applicant profile names.

Prompts, the answering guides and the cover letter's slots say NAME where the
applicant's first name goes and SCHOOL where their school goes. as_applicant
wraps a Claude so every call it is sent says the profile's own name and school
instead, wherever the prompt was built.
"""

import json
import re

from apply.profile import ApplicantProfile

NAME, SCHOOL = "@NAME@", "@SCHOOL@"

# A self-identification (EEO) question: its answer never reaches a model call (D8).
SELF_ID = re.compile(r"gender|\bsex\b|pronoun|\brac(e|ial)\b|ethnic|hispanic|latin[oax]|veteran|disabilit|sexual orientation"
                     r"|transgender|lgbt|self[- ]?identif|demographic|\bage\b|date of birth|birth ?date", re.IGNORECASE)
# The profile facts that say who the applicant is or where they live (D8). No model call needs them: the Fill engine
# fills them from the profile, so a call is sent none of them, as a fact or as an answer on the form.
WHO = ("legal_first_name", "legal_middle_name", "legal_last_name", "preferred_first_name", "preferred_last_name",
       "name_pronunciation", "name_in_native_script", "email", "phone", "home_address.line1", "home_address.line2",
       "home_address.zip")


def first_name(profile: ApplicantProfile) -> str:
    """The name they go by, else their legal first name."""
    return profile.get("identity.preferred_first_name") or profile.get("identity.legal_first_name") or "the applicant"


def _plain(value: object) -> str:
    return " ".join(str(value).split()).casefold() if isinstance(value, (str, int)) else ""


def personal(profile: ApplicantProfile) -> frozenset[str]:
    """The answers a form shows that say who the applicant is (WHO), as plain text: each fact, and the name in
    full, so an answer that is exactly one of them is never sent."""
    said = {key: _plain(profile.get(f"identity.{key}")) for key in WHO}
    firsts = (said["legal_first_name"], said["preferred_first_name"])
    lasts = (said["legal_last_name"], said["preferred_last_name"])
    full = {" ".join(filter(None, (first, middle, last))) for first in firsts for last in lasts if first and last
            for middle in ("", said["legal_middle_name"])}
    return frozenset(filter(None, {*said.values(), *full}))


def kept_out(label: str, answer: object, who: frozenset[str]) -> bool:
    """Whether an answer on the form stays out of every model call (D8): a self-identification answer, or one
    that is exactly who the applicant is (`who`, from personal())."""
    return bool(SELF_ID.search(label)) or (isinstance(answer, str) and _plain(answer) in who)


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
        self._claude, self._profile = claude, profile

    def ask_kind(self, kind: str, data: dict) -> dict:
        """`kind` said as the applicant: WorkIt adds the pronouns note and names the school from what this
        sends, and the name, which stays NAME in every prompt WorkIt builds (D8), goes back into the answer."""
        said = {"pronouns": str(self._profile.get("identity.pronouns") or "they/them/theirs").strip(),
                "school": self._profile.get("education.school") or ""}
        given = self._claude.ask_kind(kind, {**data, **said})
        return json.loads(json.dumps(given).replace(NAME, json.dumps(first_name(self._profile))[1:-1]))

    def __getattr__(self, name: str):
        return getattr(self._claude, name)
