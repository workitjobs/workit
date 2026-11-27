"""The Recording brief: what Lisul says in a video he records himself for a form's link question
(apply.asking.to_make), one bullet for each prompt the Posting lists for it (apply.description.asked), each
with one or two true talking points from the Story bank. OpenSesame asked for a YouTube link to a Creative
Project video that covers the prompts in its posting (2026-11-26): the writer typed an essay into the link
box instead, and never read the prompts.

One call of WorkIt's `recording.brief` kind writes the points (D5); each point must quote the Story bank or
the Stock answers word for word, checked in code, or it is dropped. The brief goes in the Missing fact's ask
and the rehearsal's Record, never on the form. A failed call still gives the prompts, with no points."""

from dataclasses import dataclass

from apply import description, essays
from apply.adapters import Claude, ClaudeError
from apply.applicant import as_applicant
from apply.model import Posting, Question, one_line
from apply.profile import ApplicantProfile

POINTS = 2  # talking points for one prompt at most (the kind's own POINTS)
HEADING = "Recording brief"


@dataclass(frozen=True)
class Brief:
    """What to cover in a video, prompt by prompt, and the true points to make for each."""

    question: str  # the form's link question
    prompts: tuple[tuple[str, tuple[str, ...]], ...]  # (prompt, its talking points), in the Posting's order
    note: str = ""  # why the points are missing, when the call failed

    def shown(self) -> str:
        """The brief as lines: a heading, then one bullet a prompt with its points under it."""
        lines = [f"{HEADING}: cover each prompt, in your own words"]
        for prompt, points in self.prompts:
            lines.append(f"- {prompt}")
            lines += [f"  - {point}" for point in points] or ["  - (nothing in your Story bank yet: your own point)"]
        return "\n".join(lines + ([self.note] if self.note else []))


def brief(claude: Claude, posting: Posting, q: Question, profile: ApplicantProfile, posting_text: str) -> Brief | None:
    """The Recording brief for the link question `q`, or None when the Posting lists no prompts for it."""
    found = description.asked(posting_text, q)
    if found is None:
        return None
    keys = {f"p{i}": prompt for i, prompt in enumerate(found.prompts, 1)}
    data = {"sources": essays.sources(profile, employer=posting.company),
            "posting": description.block(posting, posting_text, [q]), "question": one_line(q.label), "prompts": keys}
    try:
        given = as_applicant(claude, profile).ask_kind("recording.brief", data).get("points") or {}
    except ClaudeError:
        return Brief(one_line(q.label), tuple((prompt, ()) for prompt in found.prompts),
                     "(No talking points: the model call failed. Pick them from your Story bank.)")
    held = essays._quotable(essays.own_facts(profile, employer=posting.company))
    return Brief(one_line(q.label), tuple((prompt, _checked(given.get(key), held)) for key, prompt in keys.items()))


def _checked(points: object, held: str) -> tuple[str, ...]:
    """The points whose quote the sources hold word for word (essays._holds), at most POINTS, each said once."""
    kept = [one_line(str(p.get("say") or "")) for p in points or [] if isinstance(p, dict)
            and essays._holds(held, str(p.get("quote") or "")) and str(p.get("say") or "").strip()]
    return tuple(dict.fromkeys(kept))[:POINTS]
