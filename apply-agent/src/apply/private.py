"""Private details and model calls (D8, KAN-723).

A model call is never sent the student's email, phone, street address or birth date: no answer needs them, since
the Fill engine types them from the profile. `mask` puts a placeholder in each one's place, wherever it is in what
a kind sends (a profile fact, an answer read back from the form, a page's text, the Story bank), and `put_back`
writes the values into the answer, so an answer that quotes one still holds it. Everything else goes, the
self-identification answers on the form included: the profile's own self-ID section stays out of the facts a call
is sent (essays.NOT_FACTS), and WorkIt's server masks any email or phone the text still holds (workit_scout's
Masked).

`sensitive` reads a written answer for what most people keep private, for Lisul to look at before the form goes:
an essay may mean to say it, so it is only ever flagged, never cut or written again.
"""

import json
import re

from apply.profile import ApplicantProfile

# Each private fact's placeholder, and what a flag calls it.
FACTS = {"@EMAIL@": ("identity.email", "your email address"),
         "@PHONE@": ("identity.phone", "your phone number"),
         "@STREET@": ("identity.home_address.line1", "your street address"),
         "@STREET2@": ("identity.home_address.line2", "your street address")}
# A value shorter than this (a second address line of "2" or "4B") would be found all over a prompt: it is not
# masked, and the server masks any phone or email by its pattern anyway.
SHORTEST = 5
# The profile keeps no birth date of its own: a form's question for it is answered once and kept by its wording.
BIRTH_DATE = re.compile(r"date of birth|birth ?date|\bdob\b", re.IGNORECASE)
BORN = "@BIRTH_DATE@"
# An essay that states a trait most people keep private: "as a first-generation student", "my disability".
SELF_STATED = re.compile(
    r"\b(?:as an?|i am an?|i'm an?|being an?)\s+(?:[\w-]+\s+)?(?:woman|man|mother|father|parent|immigrant|refugee"
    r"|veteran|first[- ]gen(?:eration)?|disabled|deaf|blind|neurodivergent|autistic|black|latin[oax]|hispanic|asian"
    r"|indigenous|gay|lesbian|bisexual|queer|trans(?:gender)?|non-?binary)\b"
    r"|\bmy (?:disability|diagnosis|religion|faith|sexual orientation|gender identity|immigration status)\b",
    re.IGNORECASE)
# Self-identification values that say nothing on their own ("decline", "No").
UNSAID = {"", "decline", "yes", "no", "true", "false", "none", "n/a", "i don't wish to answer", "prefer not to say"}


def values(profile: ApplicantProfile) -> dict[str, str]:
    """The profile's private values, by placeholder."""
    found = {p: str(profile.get(key)).strip() for p, (key, _) in FACTS.items()
             if len(str(profile.get(key) or "").strip()) >= SHORTEST}
    born = [str(a).strip() for q, a in (profile.get("answered_questions") or {}).items()
            if BIRTH_DATE.search(str(q)) and len(str(a).strip()) >= SHORTEST]
    return found | ({BORN: born[0]} if born else {})


def _hidden(text: str, private: dict[str, str]) -> str:
    for placeholder, value in sorted(private.items(), key=lambda pair: -len(pair[1])):  # a longer value first
        text = re.sub(re.escape(value), placeholder, text, flags=re.IGNORECASE)
    return text


def mask(data, private: dict[str, str]):
    """`data` (a kind's data: dicts, lists and text) with each private value as its placeholder."""
    if isinstance(data, str):
        return _hidden(data, private) if private else data
    if isinstance(data, dict):
        return {key: mask(value, private) for key, value in data.items()}
    if isinstance(data, list):
        return [mask(value, private) for value in data]
    return data


def put_back(answer, private: dict[str, str]):
    """`answer` with each placeholder as its value again."""
    text = json.dumps(answer)
    for placeholder, value in private.items():
        text = text.replace(placeholder, json.dumps(value)[1:-1])
    return json.loads(text)


def sensitive(text: str, profile: ApplicantProfile) -> tuple[str, ...]:
    """What `text` tells that most people keep private: a private fact of the profile, a self-identification
    answer it gave (its race, say), or a trait it states ("as a first-generation student"); () if none."""
    said, folded, digits = [], text.casefold(), re.sub(r"\D", "", text)
    for placeholder, value in values(profile).items():
        found = (digits and len(d := re.sub(r"\D", "", value)) >= 10 and d[-10:] in digits) if placeholder == "@PHONE@" \
            else value.casefold() in folded
        if found:
            said.append(FACTS[placeholder][1] if placeholder in FACTS else "your birth date")
    for key, value in (profile.get("voluntary_self_id") or {}).items():
        for one in value if isinstance(value, list) else [value]:
            if isinstance(one, str) and one.strip().casefold() not in UNSAID and len(one.strip()) > 3 \
                    and re.search(rf"\b{re.escape(one.strip())}\b", text, re.IGNORECASE):
                said.append(f"your {key.replace('_', ' ')} ({one.strip()})")
    said += [f'"{found.group(0)}"' for found in SELF_STATED.finditer(text)]
    return tuple(dict.fromkeys(said))
