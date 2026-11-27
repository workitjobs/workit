"""The default probe: what a typical applicant would write for each idea-driven
essay on a form, so the plan can steer away from it and the sameness check
can measure against it (research/sources/answer-types/g-sameness.md, P1).

One Sonnet call per form, given only the posting, the Company material and
the questions: never a fact about Lisul, so it gives the true mode. Each
answer is cached on disk by company and question, outside the repo beside
Apply's other local state, so a question seen again costs no call."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from apply import brief, description
from apply.home import HOME
from apply.model import Posting, one_line

CACHE = HOME / "default-probes"
# The Question types whose answer turns on an idea or an angle, where the first idea is everyone's.
TYPES = frozenset({"why-company", "what-youd-build", "why-role", "values", "why-field", "opinion", "about-me"})

@dataclass(frozen=True)
class Typical:
    """The typical applicant's answer to one question, and the angles most take."""

    answer: str
    angles: tuple[str, ...] = ()


def typical(claude, posting: Posting, questions: Mapping[str, str], company: str = "",
            posting_text: str = "") -> dict[str, Typical]:
    """The Typical answer to each of `questions` (the question as asked, by
    key), from the cache, else one Sonnet call for those not cached. An
    empty `questions` costs no call."""
    found = {key: hit for key, asked in questions.items() if (hit := _cached(posting.company, asked))}
    if missing := {key: asked for key, asked in questions.items() if key not in found}:
        # WorkIt's probe.typical kind (D5, KAN-723): its prompt is on the server.
        data = {"posting": description.block(posting, posting_text), "company": company, "questions": dict(missing)}
        given = claude.ask_kind("probe.typical", data).get("typical") or {}
        for key, asked in missing.items():
            said = given.get(key) if isinstance(given.get(key), dict) else {}
            angles = said.get("angles") if isinstance(said.get("angles"), list) else []
            found[key] = Typical(str(said.get("answer") or "").strip(),
                                 tuple(one_line(str(a)) for a in angles if str(a).strip()))
            if found[key].answer:
                _keep(posting.company, asked, found[key])
    return {key: found[key] for key in questions}


def _path(company: str, asked: str) -> Path:
    digest = hashlib.sha1(one_line(asked).casefold().encode()).hexdigest()[:16]
    return CACHE / (brief.slug(company) or "unnamed") / f"{digest}.json"


def _cached(company: str, asked: str) -> Typical | None:
    path = _path(company, asked)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Typical(str(raw["answer"]), tuple(raw.get("angles") or ()))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _keep(company: str, asked: str, found: Typical) -> None:
    path = _path(company, asked)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"question": one_line(asked), "answer": found.answer, "angles": list(found.angles)},
                               indent=1), encoding="utf-8")
