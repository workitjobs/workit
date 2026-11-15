"""The answering guides, copied from Apply (apply-agent/answering/) with its
prompts (D5): the rules for every answer (answering/README.md) and one guide
per Question type (answering/types/<type>.md). A guide's front matter is data
both sides read: Apply classifies a question and checks a plan with it. Its
body is prompt text, which only the server sends.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).with_name("answering")


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
