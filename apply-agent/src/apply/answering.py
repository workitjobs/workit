"""The Question types Apply's own code reads: one file per type
(answering/types/<type>.md), each only its YAML front matter.

The writing guidance itself, each type's body and the rules for every answer,
is prompt text on WorkIt's server (backend/app/apply_prompts/answering/, D5),
which has the same front matter: a change to it goes into both copies. Apply
reads the front matter to run its own steps:
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

import re
from dataclasses import dataclass
from functools import cache

import yaml

from apply.home import CODE

# A form's note that bans AI-written text says nothing about the question's type.
NO_AI = re.compile(r"\(?\s*(please,? )?(do not|don't|no) (use )?ai( text)?[.!)]*|in your own words,?")

ROOT = CODE / "answering"  # generic: in the checkout, not the data folder

# classify tries types in this order, so the more specific win: a letter or an
# "anything else" box before everything, a pick before an idea, both before why-company,
# and why-company late, since most questions mention the company.
PRIORITY = (
    "cover-letter",
    "anything-else",
    "ai-tools",
    "values",
    "not-on-resume",
    "about-me",
    "preference",
    "what-youd-build",
    "failure",
    "opinion",
    "why-field",
    "named-area",
    "best-project",
    "why-role",
    "why-company",
)


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


def _front(text: str) -> dict:
    """A type file's front matter; the line after it only points to the server's copy."""
    _, front, _ = text.split("---\n", 2)
    return yaml.safe_load(front) or {}


@cache
def load() -> dict[str, TypeGuide]:
    """Every type's guide, by type name."""
    guides = {}
    for path in sorted((ROOT / "types").glob("*.md")):
        front = _front(path.read_text())
        guides[front["type"]] = TypeGuide(
            type=front["type"], company_link=front["company_link"], stock=bool(front["stock"]),
            high_stakes=bool(front["high_stakes"]), length=tuple(front["length"]),
            match=tuple(front.get("match") or ()),
            slots=tuple(Slot(s["name"], s["required"], s["holds"]) for s in front.get("slots") or ()))
    return guides


@cache
def _patterns() -> tuple[tuple[str, tuple[re.Pattern, ...]], ...]:
    guides = load()
    return tuple((t, tuple(re.compile(p) for p in guides[t].match)) for t in PRIORITY)


def classify(question_text: str) -> str:
    """The Question type of `question_text`: the first type in PRIORITY with a
    match pattern found in it, else "general"."""
    text = NO_AI.sub(" ", " ".join(question_text.lower().replace("’", "'").split())).strip()
    for name, patterns in _patterns():
        if any(p.search(text) for p in patterns):
            return name
    return "general"


