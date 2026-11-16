"""The answering guides, moved from Apply with its prompts (D5): the rules for
every answer (answering/README.md) and one guide per Question type
(answering/types/<type>.md). This is their one copy. A guide's front matter is
data both sides read: the prompts list its slots and length, and Apply
classifies a question and checks a plan with it, from the copy it fetches
(`served`, GET /apply-app/types) and keeps in its data folder. Its body is
prompt text, which only the server sends.
"""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).with_name("answering")

# Apply classifies a question by trying the types in this order, so the more specific win: a letter or an
# "anything else" box before everything, a pick before an idea, both before why-company, and why-company late,
# since most questions mention the company. "general" is the fallback, which no pattern picks.
ORDER = ("cover-letter", "anything-else", "ai-tools", "values", "not-on-resume", "about-me", "preference",
         "what-youd-build", "failure", "opinion", "why-field", "named-area", "best-project", "why-role", "why-company")


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
    body: str

def _split(text: str) -> tuple[dict, str]:
    """Front matter and body of a guidance file."""
    _, front, body = text.split("---\n", 2)
    return yaml.safe_load(front) or {}, body.strip()

@cache
def load() -> dict[str, TypeGuide]:
    """Every type's guide, by type name."""
    guides = {}
    for path in sorted((ROOT / "types").glob("*.md")):
        front, body = _split(path.read_text())
        guides[front["type"]] = TypeGuide(
            type=front["type"], company_link=front["company_link"], stock=bool(front["stock"]),
            high_stakes=bool(front["high_stakes"]), length=tuple(front["length"]),
            match=tuple(front.get("match") or ()),
            slots=tuple(Slot(s["name"], s["required"], s["holds"]) for s in front.get("slots") or ()), body=body)
    return guides

@cache
def served() -> str:
    """Every type's front matter and the order Apply tries them in, as the JSON GET /apply-app/types answers:
    {"order": [...], "types": {type: {company_link, stock, high_stakes, length, match, slots}}}. Never a body."""
    types = {t: {"company_link": g.company_link, "stock": g.stock, "high_stakes": g.high_stakes, "length": list(g.length),
                 "match": list(g.match), "slots": [{"name": s.name, "required": s.required, "holds": s.holds} for s in g.slots]}
             for t, g in load().items()}
    return json.dumps({"order": list(ORDER), "types": types}, sort_keys=True)


@cache
def rules(lean: bool = False) -> str:
    """The rules for every answer. `lean` (a smaller model's prompt, apply.ask_model): each numbered rule cut to its
    bold lead and the sentence after it, the Length section whole, and no Types list."""
    text = (ROOT / "README.md").read_text().strip()
    if not lean:
        return text
    text = re.split(r"^## Types\n", text, flags=re.MULTILINE)[0].strip()
    length = text.index("## Length")
    cut = lambda m: m[1] + (first[0] if (first := re.match(r"\s*[^.!?]*[.!?]", m[2])) else "")
    return re.sub(r"^(\d+\. \*\*.+?\*\*)(.*)$", cut, text[:length], flags=re.MULTILINE) + text[length:]

LEAN_SECTIONS = ("Order", "Rules")

def guide_text(types: Iterable[str], lean: bool = False) -> str:
    """The guidance bodies of `types`, each once, headed by its name, for the prompt. `lean` keeps only each
    guide's LEAN_SECTIONS: the reader's quotes, Pairs and Model letters are examples a smaller model's
    prompt can't hold (apply.ask_model)."""
    guides = load()
    body = lambda t: guides[t].body if not lean else "\n\n".join(
        section.strip() for section in re.split(r"^(?=## )", guides[t].body, flags=re.MULTILINE)
        if section.startswith(tuple(f"## {name}\n" for name in LEAN_SECTIONS)))
    return "\n\n".join(f"# Question type: {t}\n\n{body(t)}" for t in dict.fromkeys(types))
