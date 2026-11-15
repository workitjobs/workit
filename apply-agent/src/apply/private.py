"""Private details and model calls (D8, KAN-723).

A model call is never sent the private details the student gave: their names, email, phone, street address, ZIP
code, birth date and links, and each reference's name, email and phone. No answer needs them, since the Fill
engine types them from the profile, and the model gets a placeholder instead. Only the exact values of those
fields are masked, never anything guessed from a question or a text: `mask` puts each one's placeholder wherever
it is in what a kind sends (a profile fact, an answer read back from the form, a page's text, the Story bank),
and `put_back` writes the values into the answer, so an answer that quotes one still holds it. A name matches in
its own case only, so the student named Will never masks "will"; every value matches as a whole word.
WorkIt's server masks any email or phone the text still holds (workit_scout's Masked).

`sensitive` reads a written answer for what most people keep private, for Lisul to look at before the form goes:
an essay may mean to say it, so it is only ever flagged, never cut or written again.
"""

import json
import re

from apply.profile import ApplicantProfile

# The student's private fields: each one's placeholder, and what an essay's flag calls it (None: never flagged: a
# cover letter signs with the name, and an essay box can ask for the ZIP code).
FIELDS = (("identity.legal_first_name", "@FIRST_NAME@", None),
          ("identity.legal_middle_name", "@MIDDLE_NAME@", None),
          ("identity.legal_last_name", "@LAST_NAME@", None),
          ("identity.preferred_first_name", "@PREFERRED_FIRST_NAME@", None),
          ("identity.preferred_last_name", "@PREFERRED_LAST_NAME@", None),
          ("identity.name_in_native_script", "@NATIVE_NAME@", None),
          ("identity.email", "@EMAIL@", "your email address"),
          ("identity.phone", "@PHONE@", "your phone number"),
          ("identity.home_address.line1", "@STREET@", "your street address"),
          ("identity.home_address.line2", "@STREET2@", "your street address"),
          ("identity.home_address.zip", "@ZIP@", None),  # an essay box may ask where they would move from
          ("identity.date_of_birth", "@BIRTH_DATE@", "your birth date"))
REFERENCES = "experience_facts.professional_references"  # each one's name, email and phone
# An essay that states a trait most people keep private: "as a first-generation student", "my disability".
SELF_STATED = re.compile(
    r"\b(?:as an?|i am an?|i'm an?|being an?)\s+(?:[\w-]+\s+)?(?:woman|man|mother|father|parent|immigrant|refugee"
    r"|veteran|first[- ]gen(?:eration)?|disabled|deaf|blind|neurodivergent|autistic|black|latin[oax]|hispanic|asian"
    r"|indigenous|gay|lesbian|bisexual|queer|trans(?:gender)?|non-?binary)\b"
    r"|\bmy (?:disability|diagnosis|religion|faith|sexual orientation|gender identity|immigration status)\b",
    re.IGNORECASE)
# Self-identification values that say nothing on their own ("decline", "No").
UNSAID = {"", "decline", "yes", "no", "true", "false", "none", "n/a", "i don't wish to answer", "prefer not to say"}

# A private value: the value, what an essay's flag calls it, and whether it matches in its own case only (a name).
Private = tuple[str, "str | None", bool]


def _text(value: object) -> str:
    text = str(value).strip() if isinstance(value, (str, int)) and not isinstance(value, bool) else ""
    return text if len(text) >= 2 else ""


def values(profile: ApplicantProfile) -> dict[str, Private]:
    """The private values the student gave, by placeholder."""
    found = {placeholder: (value, flag, "NAME" in placeholder) for key, placeholder, flag in FIELDS
             if (value := _text(profile.get(key)))}
    found |= {f"@LINK_{key.upper()}@": (value, None, False)
              for key, link in (profile.get("links") or {}).items() if (value := _text(link))}
    for n, reference in enumerate(profile.get(REFERENCES) or [], 1):
        for part in ("name", "email", "phone") if isinstance(reference, dict) else ():
            if value := _text(reference.get(part)):
                found[f"@REFERENCE{n}_{part.upper()}@"] = (value, f"a reference's {part}", part == "name")
    return found


def _found(value: str, case: bool) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(value)}(?!\w)", 0 if case else re.IGNORECASE)


def _hidden(text: str, private: dict[str, Private]) -> str:
    for placeholder, (value, _, case) in sorted(private.items(), key=lambda item: -len(item[1][0])):  # longest first
        text = _found(value, case).sub(placeholder, text)
    return text


def mask(data, private: dict[str, Private]):
    """`data` (a kind's data: dicts, lists and text) with each private value as its placeholder."""
    if isinstance(data, str):
        return _hidden(data, private) if private else data
    if isinstance(data, dict):
        return {key: mask(value, private) for key, value in data.items()}
    if isinstance(data, list):
        return [mask(value, private) for value in data]
    return data


def put_back(answer, private: dict[str, Private]):
    """`answer` with each placeholder as its value again."""
    text = json.dumps(answer)
    for placeholder, (value, _, _) in private.items():
        text = text.replace(placeholder, json.dumps(value)[1:-1])
    return json.loads(text)


def self_id(profile: ApplicantProfile) -> frozenset[str]:
    """The self-identification answers the student gave (voluntary_self_id), as plain text, but those that say
    nothing on their own (UNSAID: a decline, a yes or no). Until the Fill engine says which answers it took from
    them, a form's answer that is exactly one of these is how Apply knows it is a self-ID answer (D8)."""
    given = set()
    for value in (profile.get("voluntary_self_id") or {}).values():
        for one in value if isinstance(value, list) else [value]:
            if isinstance(one, str) and (text := " ".join(one.split()).casefold()) not in UNSAID and len(text) > 2:
                given.add(text)
    return frozenset(given)


def is_self_id(answer: object, given: frozenset[str]) -> bool:
    """Whether a form's answer is exactly one of the student's self-ID answers (`given`, from self_id()), or, for a
    multi-select, holds one. Left out of a call, not masked: the question's options beside a placeholder would
    name the one it hides."""
    picks = answer if isinstance(answer, list) else [answer]
    return any(isinstance(a, str) and " ".join(a.split()).casefold() in given for a in picks)


def sensitive(text: str, profile: ApplicantProfile) -> tuple[str, ...]:
    """What `text` tells that most people keep private: a private value of the student's or a reference's (never
    the name), a self-identification answer the profile gave (its race, say), or a trait it states ("as a
    first-generation student"); () if none."""
    said, digits = [], re.sub(r"\D", "", text)
    for placeholder, (value, flag, case) in values(profile).items():
        if flag and (len(d := re.sub(r"\D", "", value)) >= 10 and d[-10:] in digits if placeholder.endswith("PHONE@")
                     else _found(value, case).search(text)):
            said.append(flag)
    for key, value in (profile.get("voluntary_self_id") or {}).items():
        for one in value if isinstance(value, list) else [value]:
            if isinstance(one, str) and one.strip().casefold() not in UNSAID and len(one.strip()) > 3 \
                    and _found(one.strip(), False).search(text):
                said.append(f"your {key.replace('_', ' ')} ({one.strip()})")
    said += [f'"{found.group(0)}"' for found in SELF_STATED.finditer(text)]
    return tuple(dict.fromkeys(said))
