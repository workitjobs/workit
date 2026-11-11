"""
The truth check (KAN-748): the claims in a written answer that none of the
student's sources hold. Simplify's users say its AI "will lie by default",
and Apply's own stock essays once held a made-up test count and a tool that
"went into use" when it had not.

    unsupported(answer, sources) -> each claim no source holds, with its
                                    sentence, word for word; empty when clean

Plain code, no model: it finds what plain code can find, and leaves
judgment to the Claude path each side has (the claim check and the
pre-submit review). It looks for four kinds of claim:

- **number**: a number no source states ("40 tests"). A year counts.
- **name**: a tool, employer, product or other name no source names: a run
  of capitalized words, a word with a capital inside it ("PyTorch"), an
  acronym ("CUDA"), or one capitalized word inside a sentence. The first
  word of a sentence alone is never one: it is capitalized either way.
- **date**: a month or season with its year ("summer 2025") that no
  source's dates cover. A year no source holds is a number claim only.
- **outcome**: an effect of the work ("went into use", "deployed", "won",
  "cut the time") that no fact about the same project or role states
  (KAN-750). The project is the one the sentence names, else the one the
  nearest sentence before it names: a section's heading ("## Hitachi Rail:
  Software Intern", a bank entry or a Story bank section) or a name a fact
  gives. A fact is about the headings it sits under and the names it gives.
  An outcome in a sentence whose project none of that tells is a claim.

It leans toward passing: a source holds a name in any case, and an outcome
when any fact about that project states that kind of effect. A claim it
finds is not proof of a lie, only a thing the student did not give: the
answer is flagged for the student to read before Submit, never refused or
rewritten.

Stdlib only, on purpose: this file is in two places, byte for byte, so
WorkIt and Apply run one check: `backend/app/auto_apply/truth.py`, the
original, and `apply-agent/src/apply/truth.py`, its copy (Apply's tests
compare the two). Change the backend's, then copy it to Apply.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

KINDS = {"number": "a number", "name": "a name", "date": "a date", "outcome": "an outcome"}


@dataclass(frozen=True)
class Claim:
    """One claim no source holds: its kind (KINDS), its words as the answer
    says them, and the answer's sentence that holds it, word for word."""

    kind: str
    text: str
    sentence: str

    def said(self) -> str:
        """The claim for a person: `"40" (a number)`."""
        return f'"{self.text}" ({KINDS[self.kind]})'


def unsupported(answer: str, own: str | Iterable[str], others: str | Iterable[str] = ()) -> list[Claim]:
    """Each claim in `answer` that no source holds, in the order the answer
    makes them, each once. `own` are the texts the student gave: their
    profile, resume or experience, answer bank and story bank. `others` are
    the rest an answer may name or count from: the posting, the company's
    checked facts, the question. A date or an outcome is the student's, so
    only `own` holds one: every posting says "deploy" and "ship". Either may
    be one text or several; an outcome stands only on a fact about its
    project (_facts: give each project its own "## " heading)."""
    texts = [s for s in ([own] if isinstance(own, str) else own) if s]
    theirs = "\n".join(texts)
    held = "\n".join([theirs, *(s for s in ([others] if isinstance(others, str) else others) if s)])
    plain = _plain(held)
    known = {_normal(n) for n in _numbers(held)}
    spans = [span for text in texts for line in text.splitlines() for span in _spans(line)]
    facts = _facts(texts) if any(said.search(answer) for said, _ in OUTCOMES) else []
    found: list[Claim] = []
    about: list[str] = []  # the project the last sentence that named one named
    for sentence in _sentences(answer):
        named = names(sentence)
        found += [Claim("number", n, sentence) for n in _numbers(sentence) if _normal(n) not in known]
        found += [Claim("name", name, sentence) for name in named if not _held(name, plain)]
        for m in DATED.finditer(sentence):
            if _normal(m.group(2)) in known and _plain(m.group()) not in _plain(theirs) and not _covered(m, spans):
                found.append(Claim("date", m.group(), sentence))
        about = _about(named, facts) or about
        for said, backed in OUTCOMES:
            if (m := said.search(sentence)) and not any(
                backed.search(line) and any(_same(a, n) for a in about for n in (*heads, *given))
                for heads, given, line in facts
            ):
                found.append(Claim("outcome", m.group(), sentence))
    seen: set[tuple[str, str]] = set()
    return [c for c in found if (c.kind, c.text.casefold()) not in seen and not seen.add((c.kind, c.text.casefold()))]


def reason(claims: Iterable[Claim]) -> str:
    """One flag's reason for the student, naming each claim."""
    return (f"Not in your experience or the posting: {'; '.join(c.said() for c in claims)}. "
            "Make sure each one is true before you submit.")


# Numbers, as the answer writes them: "1,200", "3.8", "30%". A digit inside
# a word ("S3", "EC2") is part of a name.
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*%?")


def _numbers(text: str) -> list[str]:
    return [n.rstrip(".,") for n in NUMBER.findall(text)]


def _normal(number: str) -> str:
    """A number in one form: "1,200" as "1200", "3.80" as "3.8", "30%" as "30"."""
    number = number.rstrip("%").replace(",", "")
    return number.rstrip("0").rstrip(".") if "." in number else number


# Names.

WORD = re.compile(r"[A-Za-z0-9][\w+#&'’-]*(?:\.[A-Za-z0-9][\w+#-]*)*")
# Words that open a sentence or join a name with a capital and are no name of their own.
OPENERS = {"a", "an", "the", "in", "at", "on", "for", "with", "during", "after", "before", "when", "while", "since",
           "because", "as", "my", "our", "his", "her", "their", "this", "that", "these", "those", "then", "there",
           "it", "we", "i", "if", "so", "but", "and", "also", "from", "by", "to", "of", "both", "each", "every", "one",
           "what", "why", "how", "dear", "sincerely", "best", "thanks", "thank", "yes", "no", "you", "your", "here",
           "today", "now", "once", "later", "first", "next", "finally", "outside", "beyond", "over", "through"}
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
SEASONS = {"spring": (3, 4, 5), "summer": (6, 7, 8), "fall": (9, 10, 11), "autumn": (9, 10, 11), "winter": (12, 1, 2)}
# Capitalized words that are no claim: days, months, seasons, languages people speak.
COMMON = {*MONTHS, *SEASONS, "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
          "english", "spanish", "french", "chinese", "mandarin", "hindi", "internet", "ok", "okay", "mr", "ms", "dr"}
# Acronyms everyone uses, which name no tool or employer.
EVERYDAY = {"AI", "ML", "API", "APIs", "UI", "UX", "CS", "US", "USA", "GPA", "PhD", "BS", "BA", "MS", "ID", "IT", "HR",
            "QA", "PM", "SWE", "CEO", "CTO", "OK", "TA", "STEM", "FAQ", "PR", "PRs", "ETA", "U.S", "U.S.A", "U.K"}


def names(sentence: str, heading: bool = False) -> list[str]:
    """The names one sentence gives, each once: runs of capitalized words (a
    possessive's "'s" and the words that open or close them dropped), words
    with a capital inside ("PyTorch", "iOS") and acronyms ("CUDA"). A word
    that opens the sentence (or follows a colon, a quote or a bullet) is
    part of a name only with a capital inside it: it is capitalized either
    way. In a `heading` every capitalized word is."""
    found: list[str] = []
    run: list[str] = []

    def close() -> None:
        while run and run[0].casefold() in OPENERS | {"of", "&"}:
            run.pop(0)
        while run and run[-1].casefold() in OPENERS | {"of", "&"}:
            run.pop()
        if run:
            found.append(" ".join(run))
        run.clear()

    words = list(WORD.finditer(sentence))
    for i, m in enumerate(words):
        word = re.sub(r"['’]s$", "", m.group())
        if re.fullmatch(r"I(?:['’]\w+)?", word):
            close()
            continue
        before = sentence[words[i - 1].end():m.start()] if i else ""
        opens = i == 0 or re.search(r"[:;\"“(•*]|\s-\s", before) is not None
        if re.search(r"\S", before):
            close()  # punctuation between words ends a name: "Python, Kafka"
        if heading and word[:1].isupper() and word.casefold() not in OPENERS | COMMON:
            run.append(word)  # "Hitachi Rail: Software Intern"
        elif _strong(word) or (word[:1].isupper() and not opens and word.casefold() not in COMMON) \
                or (run and word.casefold() in {"of", "&"}):
            run.append(word)
        else:
            close()
    close()
    return list(dict.fromkeys(n for n in found if n.casefold() not in COMMON and n not in EVERYDAY and n != "I"))


def _strong(word: str) -> bool:
    """A word that is a name wherever it stands: a capital inside it, or an acronym."""
    return re.search(r"[a-z][A-Z]|^[A-Z][A-Z0-9]+$|^[A-Z]{2,}[a-z]?s?$", word) is not None and word not in EVERYDAY


def _held(name: str, plain: str) -> bool:
    """Whether the sources hold `name`, whole or as names side by side ("IEEE
    Stony Brook Micromouse"), each piece as a whole word in any case."""
    words = _plain(name).split()
    piece = lambda part: re.search(rf"(?<![\w]){re.escape(' '.join(part))}(?![\w])", plain) is not None
    split = [True] + [False] * len(words)  # split[j]: words[:j] cut into held pieces
    for j in range(1, len(words) + 1):
        split[j] = any(split[i] and piece(words[i:j]) for i in range(j) if words[i] not in {"of", "&"})
    return split[-1]


# Which project a sentence is about (KAN-750).

HEADING = re.compile(r"\s*(#{1,6})\s+(.*)")
TAG = re.compile(r"\s*</?[\w-]+>\s*")  # "</story_bank>": the end of every section


Fact = tuple[list[str], list[str], str]  # a line's headings' names, the names it gives, the line


def _facts(texts: Iterable[str]) -> list[Fact]:
    """Each line of the student's texts with the names it is about: those of
    the headings it sits under (a section runs to the next heading of its
    level or above, or to a tag line) and those it gives itself."""
    facts: list[Fact] = []
    for text in texts:
        heads: list[tuple[int, list[str]]] = []
        for line in text.splitlines():
            if m := HEADING.fullmatch(line):
                heads = [h for h in heads if h[0] < len(m.group(1))] + [(len(m.group(1)), names(m.group(2), heading=True))]
            elif TAG.fullmatch(line):
                heads = []
            facts.append(([n for _, given in heads for n in given], [n for s in _sentences(line) for n in names(s)], line))
    return facts


def _about(named: list[str], facts: list[Fact]) -> list[str]:
    """The names in a sentence that tell its project: those a heading gives
    (a project or role, not a tool it shares with others), else those a
    fact gives."""
    return [n for n in named if any(_same(n, h) for heads, _, _ in facts for h in heads)] \
        or [n for n in named if any(_same(n, g) for _, given, _ in facts for g in given)]


def _same(a: str, b: str) -> bool:
    """Whether two names name one thing: the shorter is whole words of the
    longer, in any case ("Hitachi" and "Hitachi Rail")."""
    short, long = sorted((_plain(a), _plain(b)), key=len)
    return re.search(rf"(?<![\w]){re.escape(short)}(?![\w])", long) is not None


# Dates: a month or season and its year.

_WHEN = (r"(january|february|march|april|may|june|july|august|september|october|november|december"
         r"|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec|spring|summer|fall|autumn|winter)\.?\s+(?:of\s+)?((?:19|20)\d\d)")
DATED = re.compile(rf"\b{_WHEN}\b", re.IGNORECASE)
# A source's span: one date to another, or to the present.
SPAN = re.compile(rf"\b{_WHEN}\b(?:\s*(?:-|–|—|to|until|through)\s*(?:{_WHEN}\b|(present|now|current|today)))?",
                  re.IGNORECASE)


def _months(word: str, year: str) -> list[int]:
    """The months a month or season of `year` names, as year * 12 + month."""
    word, y = word.casefold().rstrip("."), int(year)
    if word in SEASONS:
        return [y * 12 + m for m in SEASONS[word]]
    return [y * 12 + next(n for n, m in enumerate(MONTHS, 1) if m.startswith(word[:3]))]


def _spans(line: str) -> list[tuple[int, int]]:
    spans = []
    for m in SPAN.finditer(line):
        start = _months(m.group(1), m.group(2))
        end = _months(m.group(3), m.group(4)) if m.group(3) else [10**6] if m.group(5) else start
        spans.append((min(start), max(end)))
    return spans


def _covered(m: re.Match, spans: list[tuple[int, int]]) -> bool:
    return any(lo <= month <= hi for month in _months(m.group(1), m.group(2)) for lo, hi in spans)


# Outcomes: (what the answer says, what a source must say for it to stand).
OUTCOMES = [(re.compile(said, re.IGNORECASE), re.compile(backed, re.IGNORECASE)) for said, backed in (
    ((r"\b(?:went|go(?:es)?|put|came|moved)\s+in(?:to)?\s+(?:daily\s+|active\s+)?(?:use|production|service)\b"
      r"|\b(?:still|now)\s+in\s+(?:use|production)\b|\bin\s+(?:daily|active)\s+use\b"
      r"|\bused\s+(?:daily|every\s+day|in\s+production)\b|\b(?:still|now)\s+(?:uses?|runs?)\b"),
     (r"\bin(?:to)?\s+(?:daily\s+|active\s+)?(?:use|production|service)\b|\bused\s+(?:daily|every\s+day|in\s+production|by)\b"
      r"|\bdeploy|\badopt|\brolled\s+out|\blaunch|\bshipped|\breleased|\bis\s+live\b|\bwent\s+live\b"
      r"|\bstill\s+(?:uses?|runs?)\b")),
    (r"\bdeploy(?:ed|ing|ment|s)?\b", r"\bdeploy"),
    (r"\badopted\b", r"\badopt"),
    (r"\b(?:shipped|launched|rolled\s+out|released)\b", r"\b(?:ship|launch|roll(?:ed)?\s+out|releas|deploy)"),
    (r"\b(?:cut(?!\s+corners)|reduced|lowered|decreased|halved|shrank|sped\s+up)\b",
     r"\b(?:cut|reduc|lower|decreas|halv|shr[ai]nk|sped|speed|faster)"),
    (r"\b(?:increased|improved|boosted|doubled|tripled)\b", r"\b(?:increas|improv|boost|doubl|tripl|gr[eo]w)"),
    (r"\b(?:won(?!['’]t)|awarded|first\s+place|second\s+place|third\s+place|finalist|runner[- ]up)\b",
     r"\b(?:won|win|award|place|finalist|prize|runner[- ]up|honou?r)"),
    (r"\b(?:praised|recogni[sz]ed\s+(?:by|for)|promoted|commended)\b", r"\b(?:prais|recogni[sz]|promot|commend)"),
    (r"\b(?:published|merged)\b", r"\b(?:publish|merg)"),
)]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _plain(text: str) -> str:
    return " ".join(text.replace("’", "'").casefold().split())
