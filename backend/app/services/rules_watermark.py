"""
The per-account watermark on a served Rules table (KAN-756): each account's
copy differs from every other's only in choices that change nothing the
engine does, so a leaked copy names the account it was served to.

Three channels, each set by a hash of the account id alone (deterministic:
the same account always gets the same copy):

- **Regex spellings.** Outside a character class and a `{...}`, a space is
  also `[ ]`, `\\d` is also `[0-9]`, and `\\s+` / `\\s*` are also `\\s{1,}` /
  `\\s{0,}`: the same regex, so every `test` and `exec` answers the same,
  capture groups included. Each such place in an answer rule's or a site's
  pattern is one bit. Patterns with the `v` flag are left alone (their
  classes read `[ ]` differently).
- **Selector list order.** A CSS selector list (`a, b, c`) matches the union
  of its parts in document order whatever their order, so the order of a
  list's parts is free. Only a string every part of which reads as a
  selector counts as a list (`_is_selector_list`); a wording never does.
- **A decoy.** One never-matching part, `[data-v-<10 hex>]`, joins one list of
  each site: an attribute no page carries (Vue's scoped attributes have 8
  hex digits), the first 40 bits of the account's hash in plain sight.

The engine's code must use these strings only as whole selectors or whole
parts of a list (tests/test_rules_watermark.py checks its source for that).
Never anything encoded or encrypted: the table stays plain, readable data
(the Chrome Web Store's line). Diffing two accounts' copies shows the
channels; that only strips a copy, it never frames another account.

`trace` reads a leaked table back: every channel is checked against each
candidate account's expected choices, and the best agreement wins.
"""

import copy
import hashlib
import re
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

_MARK = b"workit-rules-watermark-v1"

# A regex place that can be spelled two ways: (plain, marked) for each kind.
_SPELLINGS = {"space": (" ", "[ ]"), "digit": (r"\d", "[0-9]"), "some": (r"\s+", r"\s{1,}"), "any": (r"\s*", r"\s{0,}")}

_QUANTIFIER = re.compile(r"\{\d+(?:,\d*)?\}")
_DECOY = re.compile(r"^\[data-v-([0-9a-f]{10})\]$")
_TAGS = frozenset(["a", "button", "div", "form", "h1", "h2", "h3", "h4", "h5", "h6", "iframe", "input", "label", "li", "ol", "option", "p", "section", "select", "span", "table", "td", "textarea", "tr", "ul"])
# A custom element's tag (SmartRecruiters' spl-input): lower case, with a hyphen.
_CUSTOM = re.compile(r"^[a-z][a-z0-9]*-[a-z0-9-]+$")
# What only a selector has: a class or id (.name, #name), an attribute ([...]), a pseudo-class (:name), a child
# combinator. A wording's full stop or colon ("Mr., Mrs.", "Note: x") is none of them.
_CSS_TOKEN = re.compile(r"[.#][A-Za-z_-]|\[|:[a-z]|>")
# One part of a list: a compound selector and its combinators, made only of CSS's characters.
_PART = re.compile(r"""^[A-Za-z0-9_\-.#\[\]=\"'^$*~|:()>+ ]+$""")


def _bits(account_id: uuid.UUID, slot: str) -> Iterator[int]:
    """The account's endless bit stream for one place in the table."""
    counter = 0
    while True:
        digest = hashlib.blake2b(b"\0".join([_MARK, account_id.bytes, slot.encode(), str(counter).encode()])).digest()
        for byte in digest:
            for k in range(8):
                yield (byte >> k) & 1
        counter += 1


def _pick(bits: Iterator[int], n: int) -> int:
    """A number below n from 16 of the stream's bits."""
    return sum(next(bits) << k for k in range(16)) % n


def fingerprint(account_id: uuid.UUID) -> str:
    """The account's 40-bit decoy id, as 10 hex digits."""
    return hashlib.blake2b(_MARK + b"\0decoy\0" + account_id.bytes, digest_size=5).hexdigest()


# --- Regex spellings ---


def _regex_places(source: str) -> list[str | tuple[str, bool]]:
    """`source` cut into raw text and the places a spelling can change: (kind, spelled the marked way)."""
    out: list[str | tuple[str, bool]] = []
    i, n, in_class = 0, len(source), False
    while i < n:
        c = source[i]
        if in_class:
            step = 2 if c == "\\" else 1
            out.append(source[i:i + step])
            in_class = c != "]"
            i += step
            continue
        if c == "\\":
            nxt = source[i + 1:i + 2]
            if nxt == "d":
                out.append(("digit", False))
                i += 2
            elif nxt == "s" and source[i + 2:i + 3] in ("+", "*"):
                out.append(("some" if source[i + 2] == "+" else "any", False))
                i += 3
            elif nxt == "s" and source[i + 2:i + 6] in ("{1,}", "{0,}"):
                out.append(("some" if source[i + 3] == "1" else "any", True))
                i += 6
            else:
                out.append(source[i:i + 2])
                i += 2
        elif source.startswith("[0-9]", i):
            out.append(("digit", True))
            i += 5
        elif source.startswith("[ ]", i):
            out.append(("space", True))
            i += 3
        elif c == "[":
            out.append(c)
            in_class = True
            i += 1
            # In JS a class ends at its first unescaped ], even a leading one ([] and [^] are whole classes).
        elif quantifier := _QUANTIFIER.match(source, i):  # {2}, {0,60}: copied whole (a lone { is a literal)
            out.append(quantifier.group())
            i = quantifier.end()
        elif c == " ":
            out.append(("space", False))
            i += 1
        else:
            out.append(c)
            i += 1
    return out


def _spell(places: list[str | tuple[str, bool]], marks: Iterable[bool] | None = None) -> str:
    """The source again: each place spelled as `marks` says, or plain without them."""
    marks = iter(marks) if marks is not None else None
    return "".join(p if isinstance(p, str) else _SPELLINGS[p[0]][int(next(marks)) if marks else 0] for p in places)


def _pattern_slot(pattern: dict[str, Any]) -> str:
    return f"re\0{pattern.get('flags', '')}\0{_spell(_regex_places(pattern['source']))}"


def _markable(pattern: Any) -> bool:
    return isinstance(pattern, dict) and isinstance(pattern.get("source"), str) and "v" not in str(pattern.get("flags", ""))


# --- Selector lists ---


def _parts(selector: str) -> list[str]:
    """A selector's top-level, comma-separated parts, stripped (commas inside (), [] and quotes stay)."""
    parts, depth, quote, start, i = [], 0, "", 0, 0
    while i < len(selector):
        c = selector[i]
        if c == "\\":
            i += 2
            continue
        if quote:
            quote = "" if c == quote else quote
        elif c in "\"'":
            quote = c
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(selector[start:i].strip())
            start = i + 1
        i += 1
    parts.append(selector[start:].strip())
    return parts


def _is_selector(part: str) -> bool:
    if not part or not _PART.match(part):
        return False
    return bool(_CSS_TOKEN.search(part)) or all(word in _TAGS or _CUSTOM.match(word) for word in part.split())


def _is_selector_list(value: Any) -> bool:
    """Whether a string is a CSS selector list of two or more parts, each one a selector."""
    if not isinstance(value, str):
        return False
    return _all_selectors(_parts(value))


def _all_selectors(parts: list[str]) -> bool:
    return len(parts) >= 2 and all(_is_selector(p) for p in parts)


def _list_slot(parts: list[str]) -> str:
    return "css\0" + "\0".join(sorted(parts))


def _order(account_id: uuid.UUID, parts: list[str]) -> list[str]:
    """The account's order of a list's parts: a shuffle of their sorted order by its bits."""
    order, bits = sorted(parts), _bits(account_id, _list_slot(parts))
    for i in range(len(order) - 1, 0, -1):
        j = _pick(bits, i + 1)
        order[i], order[j] = order[j], order[i]
    return order


# --- Walking a table ---


def _patterns(table: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Every pattern in the table ({source, flags?}): the answer rules' and each site's."""
    for rule in table.get("answers") or []:
        if isinstance(rule, dict) and _markable(rule.get("pattern")):
            yield rule["pattern"]
    for data in (table.get("systems") or {}).values():
        yield from (p for p in ((data or {}).get("patterns") or {}).values() if _markable(p))


def _strings(table: dict[str, Any]) -> Iterator[tuple[str, dict[str, str], str]]:
    """Each site's strings: (site, its strings, a name), in name order."""
    for site, data in sorted((table.get("systems") or {}).items()):
        strings = (data or {}).get("strings") or {}
        for name in sorted(strings):
            yield site, strings, name


def watermark(table: dict[str, Any], account_id: uuid.UUID) -> dict[str, Any]:
    """A copy of `table` carrying the account's watermark, which the engine fills with exactly as the original."""
    marked = copy.deepcopy(table)
    for pattern in _patterns(marked):
        places = _regex_places(pattern["source"])
        pattern["source"] = _spell(places, _bits(account_id, _pattern_slot(pattern)))
    lists: dict[str, list[tuple[dict[str, str], str]]] = {}
    for site, strings, name in _strings(marked):
        if _is_selector_list(strings[name]):
            parts = [p for p in _parts(strings[name]) if not _DECOY.match(p)]
            strings[name] = ", ".join(_order(account_id, parts))
            lists.setdefault(site, []).append((strings, name))
    for site, found in lists.items():
        bits = _bits(account_id, f"decoy\0{site}")
        strings, name = found[_pick(bits, len(found))]
        parts = _parts(strings[name])
        parts.insert(_pick(bits, len(parts) + 1), f"[data-v-{fingerprint(account_id)}]")
        strings[name] = ", ".join(parts)
    return marked


# --- Reading a leaked table back ---


@dataclass(frozen=True)
class Trace:
    """Who a leaked table was served to, as sure as its marks allow."""

    account_id: uuid.UUID
    agree: int  # marks that agree with this account's
    marks: int  # marks read
    decoy: bool  # its decoy names this account

    @property
    def share(self) -> float:
        return self.agree / self.marks if self.marks else 0.0


def score(table: dict[str, Any], account_id: uuid.UUID) -> Trace:
    """How many of a table's marks agree with what `account_id` was served."""
    agree = marks = 0
    for pattern in _patterns(table):
        places = _regex_places(pattern["source"])
        expected = _bits(account_id, _pattern_slot(pattern))
        for place in places:
            if not isinstance(place, str):
                agree += int(place[1]) == next(expected)
                marks += 1
    decoy = False
    for _site, strings, name in _strings(table):
        if not isinstance(strings[name], str):
            continue
        parts = _parts(strings[name])
        decoy = decoy or any((m := _DECOY.match(p)) and m.group(1) == fingerprint(account_id) for p in parts)
        parts = [p for p in parts if not _DECOY.match(p)]
        if not _all_selectors(parts):
            continue
        rank = {p: i for i, p in enumerate(_order(account_id, parts))}
        # Every pair of parts is a mark: in the account's order, or not.
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                agree += rank[parts[i]] < rank[parts[j]]
                marks += 1
    return Trace(account_id, agree, marks, decoy)


# A random account agrees with about half of a table's marks; the one it was served to with all of them.
# A match needs this share of at least MIN_MARKS marks (the answer rules alone carry over a thousand).
MIN_SHARE = 0.9
MIN_MARKS = 64


def trace(table: dict[str, Any], candidates: Iterable[uuid.UUID]) -> Trace | None:
    """The candidate account a leaked table was served to, or None when no candidate's marks fit."""
    best = max((score(table, c) for c in candidates), key=lambda t: (t.decoy, t.share), default=None)
    if best is None or not (best.decoy or (best.marks >= MIN_MARKS and best.share >= MIN_SHARE)):
        return None
    return best
