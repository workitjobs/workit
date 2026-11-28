"""The Question types Apply's own code reads, as WorkIt serves them (GET /apply-app/types, KAN-723).

Each type's guide lives once, on WorkIt's server (backend/app/apply_prompts/answering/, D5): its body is the
writing guidance, prompt text that only the server sends, and its front matter is data both sides read. Apply
fetches the front matter and the order to try the types in when a run starts (`refresh`) and keeps the last
copy in the data folder (CACHE), so a change reaches every app with the API's deploy, and a run with WorkIt
down uses the copy it has. It reads the front matter to run its own steps:
  match         lowercase regexes that pick a question's type (classify):
                "Why do you want to work at Figma?" is why-company, and the
                type goes to WorkIt with the question
  slots         the parts a great answer of the type holds: the Essay plan
                must back each required one with quoted lines (see Slot), or
                the plan asks Lisul for the fact
  length        the default words when the form states none (the length gate)
  company_link  "never" types (about-me) may tie no company fact
  stock         whether the type keeps an approved core answer (apply.stock)
  high_stakes   whether its answer holds the Application for review
"""

import json
import re
from dataclasses import dataclass
from functools import cache

from apply import home

# A form's note that bans AI-written text says nothing about the question's type.
NO_AI = re.compile(r"\(?\s*(please,? )?(do not|don't|no) (use )?ai( text)?[.!)]*|in your own words,?")

# The last copy of WorkIt's Question types, as GET /apply-app/types answered it.
CACHE = home.HOME / "question-types.json"
NO_TYPES = ("Apply has no Question types yet: it fetches them from WorkIt when a run starts, so sign in "
            "(uv run apply login) and start again")


@dataclass(frozen=True)
class Slot:
    """One part of a great answer. `required` is True (no backing holds the
    question), False (no backing leaves it out) or "asked" (required only when
    the question asks for this part)."""

    name: str
    required: bool | str
    holds: str


@dataclass(frozen=True)
class TypeGuide:
    type: str
    company_link: str  # "same-kind" or "never"
    stock: bool
    high_stakes: bool
    length: tuple[int, int]
    match: tuple[str, ...]
    slots: tuple[Slot, ...]


def refresh(workit) -> None:
    """Fetch WorkIt's Question types into CACHE. Signed out, or with WorkIt not answering, the copy Apply has
    stays."""
    from apply.workit import WorkItError

    if not workit.logged_in():
        return
    try:
        served = workit.call("GET", "/apply-app/types")
    except (WorkItError, OSError):
        return
    if isinstance(served, dict) and served.get("types") and served.get("order"):
        CACHE.write_text(json.dumps(served, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        _served.cache_clear()
        _patterns.cache_clear()


@cache
def _served() -> tuple[dict[str, TypeGuide], tuple[str, ...]]:
    try:
        served = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Imported here: adapters imports modules that import this one.
        from apply.adapters import SetupError

        raise SetupError(NO_TYPES) from None
    guides = {name: TypeGuide(type=name, company_link=t["company_link"], stock=bool(t["stock"]),
                              high_stakes=bool(t["high_stakes"]), length=tuple(t["length"]), match=tuple(t["match"]),
                              slots=tuple(Slot(s["name"], s["required"], s["holds"]) for s in t["slots"]))
              for name, t in served["types"].items()}
    return guides, tuple(served["order"])


def load() -> dict[str, TypeGuide]:
    """Every type's guide, by type name."""
    return _served()[0]


@cache
def _patterns() -> tuple[tuple[str, tuple[re.Pattern, ...]], ...]:
    guides, order = _served()
    return tuple((t, tuple(re.compile(p) for p in guides[t].match)) for t in order if t in guides)


def classify(question_text: str) -> str:
    """The Question type of `question_text`: the first type, in WorkIt's order, with a
    match pattern found in it, else "general"."""
    text = NO_AI.sub(" ", " ".join(question_text.lower().replace("’", "'").split())).strip()
    for name, patterns in _patterns():
        if any(p.search(text) for p in patterns):
            return name
    return "general"
