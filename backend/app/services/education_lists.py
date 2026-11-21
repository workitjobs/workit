"""
The schools and fields of study the Education form suggests as a student
types (GET /education/schools, /education/fields; 2026-11-17).

The lists are data/schools.tsv and data/fields_of_study.tsv, built from the
US Department of Education's directory and CIP list and Hipo's world list by
scripts/build_education.py (its docstring says where each comes from). They
are suggestions only: the form keeps whatever the student types, so a school
the lists lack still saves, and nothing here checks a saved value.

Pure: no database, no network. Each file is read once per process and folded
for search up front, so a search is a scan of about 12,000 short strings.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
SCHOOLS_FILE = DATA / "schools.tsv"
FIELDS_FILE = DATA / "fields_of_study.tsv"

# How many suggestions a search answers: the dropdown shows about six, and
# more than this is a list nobody reads.
LIMIT = 8
# A search needs this many folded characters: one letter matches a tenth of
# every school.
MIN_QUERY = 2


def fold(text: str) -> str:
    """Accents off, case folded, punctuation as spaces: "Université Laval" and
    "universite laval" are one, and "St. John's" reads "st john s"."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    return " ".join(re.sub(r"[^0-9a-z]+", " ", plain).split())


@dataclass(frozen=True)
class _Item:
    name: str
    place: str | None
    # 0 four-year, 1 two-year, 2 other US, 3 outside the US; fields are 0.
    rank: int
    folded: str
    words: tuple[str, ...]
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Suggestion:
    name: str
    place: str | None = None


def _rows(path: Path) -> list[list[str]]:
    return [
        line.split("\t")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]


@lru_cache(maxsize=1)
def _schools() -> tuple[_Item, ...]:
    items = []
    for _source, rank, name, place, aliases in _rows(SCHOOLS_FILE):
        folded = fold(name)
        items.append(
            _Item(
                name=name,
                place=place or None,
                rank=int(rank),
                folded=folded,
                words=tuple(folded.split()),
                aliases=tuple(fold(a) for a in aliases.split("|") if a),
            )
        )
    return tuple(items)


@lru_cache(maxsize=1)
def _fields() -> tuple[_Item, ...]:
    items = []
    for _code, title in _rows(FIELDS_FILE):
        folded = fold(title)
        items.append(
            _Item(
                name=title, place=None, rank=0, folded=folded, words=tuple(folded.split()), aliases=()
            )
        )
    return tuple(items)


def _words_lead(tokens: list[str], words: tuple[str, ...] | list[str]) -> bool:
    # Every typed word starts some word of the name, in any order: "stony
    # brook" and "brook stony" both find Stony Brook University.
    return all(any(w.startswith(t) for w in words) for t in tokens)


def _score(query: str, tokens: list[str], item: _Item) -> int | None:
    """How well a name answers the search, lowest best; None for no match."""
    if item.folded == query:
        return 0
    if item.folded.startswith(query):
        return 1
    if _words_lead(tokens, item.words):
        return 2
    # An alias the student typed ("SBU", "SUNY Stony Brook", "UCLA").
    for alias in item.aliases:
        if alias == query or alias.startswith(query) or _words_lead(tokens, alias.split()):
            return 3
    if query in item.folded:
        return 4
    return None


def _search(items: tuple[_Item, ...], text: str, limit: int) -> list[Suggestion]:
    query = fold(text)
    if len(query) < MIN_QUERY:
        return []
    tokens = query.split()
    scored = []
    for item in items:
        score = _score(query, tokens, item)
        if score is not None:
            # Better matches first; among equal ones a four-year school before
            # a two-year one, then the shorter, more likely name.
            scored.append((score, item.rank, len(item.name), item.name, item))
    scored.sort(key=lambda s: s[:4])
    return [Suggestion(name=s[4].name, place=s[4].place) for s in scored[:limit]]


def search_schools(text: str, limit: int = LIMIT) -> list[Suggestion]:
    return _search(_schools(), text, limit)


def search_fields(text: str, limit: int = LIMIT) -> list[Suggestion]:
    return _search(_fields(), text, limit)
