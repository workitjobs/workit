"""
Layer 2, the student's Answer bank (W11 of
docs/desktop_application_auto_apply.md; models/CLAUDE.md, "The Answer
bank"): one bank for each student, which WorkIt Auto Apply and the WorkIt
extension read whole and fill any form from.

- **What enters.** The student's answers, with no flag, and a model's
  answers to one-off questions (WorkIt Auto Apply's drafts, the student's
  Claude's choices), flagged `review: true` until the student reviews
  them. A flagged answer still fills later forms (the engine reads it as
  not `own`, so a form that bans AI-written text never takes it). Never an
  essay: the callers send only one-off questions.
- **One rule, the server's, runs when an answer is saved, never when it
  is read** (`Rule.kept_out`, then `_unsupported`). An answer stays on its
  application, and fills only that form, when its question follows another
  ("If yes, please explain."), asks about a company or the role, or names
  (or a text answer names) the form's company or the company of one of
  the student's applications. The places the student worked or studied
  don't count, but the form's own company always does. A model's text
  also stays out when it names any company WorkIt knows, or states a
  number or claim the student's own data doesn't hold (checked with no
  posting: a fact only one posting gave would be made up on any other
  form). Plain code, no model. So every answer in the bank is safe on
  every form, and a reader takes it whole.
- **A student's first read fills their row** from what WorkIt held before
  the bank (`_first_fill`): their brought Apply answers
  (`applicant_profiles.fill_answers`) and the answers saved to one-off
  questions on their applications, the student's own first, each through
  the rule. Nothing is run by hand after the migration.
- `PATCH .../answer-bank` (`change`) commits; `keep` and `drop` are the
  other steps' writes into the bank, which flush and leave the commit to
  them. A bank past its caps refuses `change`; `keep` then saves nothing to
  the bank and the step's own save goes on.
"""

import json
import logging
import re
import uuid
from collections.abc import Collection, Iterable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_apply import briefs, checks, truth
from app.auto_apply.queries import (
    fetch_application_companies,
    fetch_brought_answers,
    fetch_company_names,
    fetch_form_companies,
    fetch_one_off_answers,
    fetch_profile_facts,
    fetch_saved_answers,
)
from app.auto_apply.stages import NotFound
from app.queries import answer_banks
from app.queries.answer_banks import MAX_BYTES, MAX_ENTRIES, Stored, TooBig
from app.schemas.applications import BankEntry, SavedAnswer
from app.schemas.profile import ApplyAnswer
from app.services.apply_answers import is_own, wording
from app.services.bank import Bank, load_bank

__all__ = ["Kept", "Rule", "Stored", "TooBig", "change", "drop", "from_apply", "keep", "key", "own_words", "read",
           "rule_for", "served"]

log = logging.getLogger(__name__)

FOLLOWS = "It follows another question, so it stays on this form."
ROLE_OR_COMPANY = "It asks about one company or role, so it stays on this form."
THEIRS = "The student's own answer to it stays."
NAMES_A_COMPANY = "It names a company, so it stays on its form."
UNSUPPORTED = "It states something the student's own data doesn't hold, so it stays on this form."
# The longest model text the content checks read: about 8 ms of plain-code regexes. A one-off draft
# averages about 200 bytes; a longer one stays on its form unread, so no save holds the API for long.
CHECKED_MAX = 1000


def key(question: str) -> str:
    """A question's key in the bank: its wording as the Fill engine's Answer
    bank matches it (case, spacing, curly quotes and a trailing asterisk
    don't count; fit.ts `norm`)."""
    return wording(question)


@dataclass(frozen=True)
class Kept:
    """One answer for the bank: the question as the form words it, the
    answer (a list for the options picked; [] is "none of these"), `review`
    for a Claude answer the student hasn't reviewed, `choice` when it is a
    pick from the form's options (the rule reads its question alone), and
    the form's company, when it came from a form."""

    question: str
    answer: str | list[str]
    review: bool = False
    choice: bool = False
    company: str | None = None


@dataclass(frozen=True)
class Rule:
    """The company rule for one student: the companies of their applications,
    the places they worked or studied, and, when their Claude's text is to be
    checked, the keys of every company WorkIt knows but those places
    (briefs.company_key)."""

    companies: tuple[str, ...]
    places: tuple[str, ...]
    known: frozenset[str] = frozenset()

    def kept_out(self, kept: Kept) -> str | None:
        """Why `kept` stays on its form instead of entering the bank, or None."""
        if checks.FOLLOW_UP.search(kept.question):
            return FOLLOWS
        if checks.ABOUT_THE_COMPANY.search(kept.question):
            return ROLE_OR_COMPANY
        said = "" if kept.choice else "; ".join(kept.answer) if isinstance(kept.answer, list) else kept.answer
        form = (kept.company or "").strip()
        for name in dict.fromkeys(n.strip() for n in (form, *self.companies) if n and n.strip()):
            # Their own employer or school is their story on any form; never the form's own company.
            if name.casefold() != form.casefold() and any(checks.names(place, name) for place in self.places):
                continue
            if checks.names(kept.question, name) or (said and checks.names(said, name)):
                return f"It names {name}, so it stays on this form."
        # Their Claude names no company in an answer for any form; the student's own words may name one they like.
        if kept.review and said and companies_named(said, self.known):
            return NAMES_A_COMPANY
        return None


async def rule_for(db: AsyncSession, applicant_id: uuid.UUID, bank: Bank, claude_text: bool = False) -> Rule:
    """The company rule for the student, whose experience bank is `bank`;
    with `claude_text`, one that also knows every company WorkIt knows (a
    longer read), for a model's text."""
    # Here, not at the top: written.py imports this module.
    from app.auto_apply.written import places

    theirs = tuple(places(bank))
    own = {briefs.company_key(place) for place in theirs}
    known = frozenset(
        key for name in await fetch_company_names(db) if (key := briefs.company_key(name)) and key not in own
    ) if claude_text else frozenset()
    return Rule(companies=tuple(await fetch_application_companies(db, applicant_id)), places=theirs, known=known)


def _checked(kept: Kept) -> bool:
    """Whether the content checks read `kept`: a model's text, not a pick."""
    return kept.review and not kept.choice and isinstance(kept.answer, str)


async def _unsupported(
    db: AsyncSession, applicant_id: uuid.UUID, bank: Bank, entries: list[Kept], mine: Iterable[str] | None = None,
) -> list[bool]:
    """For each of `entries`, in order, whether it is a model's text that
    states something the student's own data doesn't hold: what WorkIt's
    writing checks find (checks.problems: a number, words a machine writes)
    or the truth check finds (truth.py: a number, name, date or outcome),
    with the student's own data as the only sources, never a posting. Plain
    code, no model; a text over CHECKED_MAX is not read and counts as
    unsupported. `mine` is the student's own answers in the bank, read from
    their row when not given (the first fill gives them: it has no row
    yet). Reads the student's data only when there is such an answer."""
    if not any(map(_checked, entries)):
        return [False] * len(entries)
    # Here, not at the top: written.py imports this module.
    from app.auto_apply.written import bank_facts, bank_sources

    sources = tuple(bank_sources(bank))
    if mine is None:
        stored = await answer_banks.fetch(db, applicant_id)
        mine = [_text(e["answer"]) for e in (stored.answers if stored else {}).values() if not e.get("review")]
    own = [*bank_facts(bank), *await fetch_profile_facts(db, applicant_id),
           *(_text(s.answer) for s in await fetch_saved_answers(db, applicant_id) if s.own), *mine]
    return [
        _checked(k) and (
            len(k.answer) > CHECKED_MAX
            or bool(checks.problems(k.answer, checks.Context(sources=(*sources, k.question), question=k.question)))
            or bool(truth.unsupported(k.answer, own, (*sources, k.question)))
        )
        for k in entries
    ]


def _text(answer: str | list[str]) -> str:
    return "; ".join(answer) if isinstance(answer, list) else answer


def companies_named(text: str, known: Collection[str]) -> set[str]:
    """The keys of the `known` companies `text` names: each run of up to
    four capitalized words (a possessive's "'s" and the punctuation that
    ends a run dropped) folded as briefs.company_key folds a company's name."""
    named: set[str] = set()
    run: list[str] = []
    for word in [*text.split(), ""]:
        bare = re.sub(r"(['\u2019]s)?[,.;:!?)\"\u201d]*$", "", word.lstrip("(\"\u201c"))
        if bare[:1].isupper() or bare[:1].isdigit():
            run.append(bare)
        if not (bare[:1].isupper() or bare[:1].isdigit()) or not word.endswith(bare):
            for start in range(len(run)):
                for end in range(start + 1, min(start + 4, len(run)) + 1):
                    if len(key := briefs.company_key(" ".join(run[start:end]))) > 1 and key in known:
                        named.add(key)
            run = []
    return named


def _entry(kept: Kept) -> dict:
    answer = [str(a) for a in kept.answer] if isinstance(kept.answer, list) else kept.answer.strip()
    return {"question": kept.question.strip(), "answer": answer, **({"review": True} if kept.review else {})}


def served(answers: dict) -> dict[str, SavedAnswer]:
    """The bank as the Fill engine's Answer bank takes it, by key: `own`
    for every answer but a flagged one, `none` for "none of these"."""
    return {
        filed: SavedAnswer(question=entry["question"], answer=entry["answer"], own=not entry.get("review"),
                           none=True if entry["answer"] == [] else None)
        for filed, entry in answers.items()
    }


async def _first_fill(db: AsyncSession, applicant_id: uuid.UUID) -> dict:
    """The row a student's first read makes: their own answers first, the
    newest first (saved on applications, then brought from Apply), then their
    Claude's, flagged (choices saved on applications, and Apply's drafts,
    which passed Apply's checks); one a key, each through the rule, within
    the caps."""
    saved = [s for s in await fetch_one_off_answers(db, applicant_id) if s.own or s.choice]
    brought = await fetch_brought_answers(db, applicant_id)
    newest = sorted([*(s for s in saved if s.own), *(s for s in brought if s.own)],
                    key=lambda s: s.at.timestamp() if s.at else float("-inf"), reverse=True)
    ordered = [Kept(question=s.question, answer=s.answer, review=not s.own, choice=s.choice, company=s.company)
               for s in (*newest, *(s for s in saved if not s.own), *(s for s in brought if not s.own))]
    bank = await load_bank(db, applicant_id)
    rule = await rule_for(db, applicant_id, bank, any(map(_checked, ordered)))
    unsupported = await _unsupported(db, applicant_id, bank, ordered, [_text(k.answer) for k in ordered if not k.review])
    answers: dict = {}
    size = 2
    for kept, unheld in zip(ordered, unsupported, strict=True):
        filed = key(kept.question)
        if not filed or filed in answers or unheld or rule.kept_out(kept):
            continue
        entry = _entry(kept)
        size += len(json.dumps({filed: entry}, ensure_ascii=False).encode()) - 1
        if len(answers) >= MAX_ENTRIES or size > MAX_BYTES:
            break
        answers[filed] = entry
    return answers


async def _ensure(db: AsyncSession, applicant_id: uuid.UUID) -> bool:
    """Makes the student's row from what WorkIt held before, if they have
    none. False with no profile (no row can be made). Flushes."""
    if await answer_banks.fetch_version(db, applicant_id) is not None:
        return True
    if not await answer_banks.has_profile(db, applicant_id):
        return False
    await answer_banks.create(db, applicant_id, await _first_fill(db, applicant_id))
    return True


async def read(db: AsyncSession, applicant_id: uuid.UUID, held: int | None = None) -> Stored | None:
    """The student's whole bank and its version, or None when `held` is that
    version (nothing changed: the reader keeps its copy). A student with no
    profile has an empty bank, version 0. Commits the first read's row."""
    if held is not None and await answer_banks.fetch_version(db, applicant_id) == held:
        return None
    stored = await answer_banks.fetch(db, applicant_id)
    if stored is None:
        if not await _ensure(db, applicant_id):
            return None if held == 0 else Stored(answers={}, version=0)
        await db.commit()
        stored = await answer_banks.fetch(db, applicant_id)
    return None if stored.version == held else stored


async def own_words(db: AsyncSession, applicant_id: uuid.UUID) -> list[str]:
    """The student's own answers in the bank, as text: what the truth check
    takes as theirs. Reads what a first read would hold without writing it."""
    stored = await answer_banks.fetch(db, applicant_id)
    answers = stored.answers if stored else await _first_fill(db, applicant_id)
    return [_text(e["answer"]) for e in answers.values() if not e.get("review") and e["answer"] not in ("", [])]


@dataclass
class Changed:
    """The bank's version after a write, and why each answer it kept out
    stays on its form, by question."""

    version: int
    kept_out: dict[str, str]


async def _merge(db: AsyncSession, applicant_id: uuid.UUID, entries: Collection[Kept], deleted: Iterable[str]) -> Changed:
    entries = list(entries)
    bank = await load_bank(db, applicant_id)
    rule = await rule_for(db, applicant_id, bank, any(map(_checked, entries)))
    # Each entry on its own: two with one question (the student's and a model's) never decide for each other.
    why = [rule.kept_out(kept) for kept in entries]
    unsupported = await _unsupported(db, applicant_id, bank, [k for k, w in zip(entries, why) if w is None])
    unheld = iter(unsupported)
    kept_out: dict[str, str] = {}
    written: dict = {}
    for kept, reason in zip(entries, why):
        if reason is None and next(unheld):
            reason = UNSUPPORTED
        if reason:
            kept_out[kept.question] = reason
        elif filed := key(kept.question):
            written[filed] = _entry(kept)
    # Their Claude's answer never replaces the student's own: theirs is the one later forms take.
    for filed in await answer_banks.reviewed_keys(db, applicant_id, [k for k, e in written.items() if e.get("review")]):
        kept_out[written.pop(filed)["question"]] = THEIRS
    gone = list(dict.fromkeys(filed for q in deleted if (filed := key(q))))
    async with db.begin_nested():  # a refused merge rolls back to here, the step's own writes kept
        version = await answer_banks.merge(db, applicant_id, written, gone)
    return Changed(version=version, kept_out=kept_out)


async def change(
    db: AsyncSession, applicant_id: uuid.UUID, entries: Collection[BankEntry], deleted: Collection[str],
) -> Changed | None:
    """PATCH .../answer-bank: saves `entries` (each through the rule, with
    the company of the form its `job_id` names, read from WorkIt's own
    database) and deletes the questions `deleted`, and commits. None with
    no profile. Raises NotFound when a `job_id` names no application of the
    student's, and TooBig past the caps, with nothing saved either way."""
    if not await _ensure(db, applicant_id):
        return None
    jobs = {e.job_id for e in entries if e.job_id is not None}
    companies = await fetch_form_companies(db, applicant_id, jobs) if jobs else {}
    if jobs - companies.keys():
        raise NotFound("No application for that job.")
    changed = await _merge(db, applicant_id, [
        Kept(question=e.question, answer=e.answer, review=e.review, choice=isinstance(e.answer, list) or e.choice,
             company=companies.get(e.job_id) if e.job_id else None)
        for e in entries
    ], deleted)
    await db.commit()
    return changed


async def keep(
    db: AsyncSession, applicant_id: uuid.UUID, entries: Collection[Kept], deleted: Collection[str] = (),
) -> dict[str, str]:
    """Another step's answers into the bank (an application's one-off
    answers, Apply's sync): each through the rule, which answers why it kept
    each one out, and the questions `deleted` out of it. A bank past its caps
    takes none of them, and says so in the log only: the step's own save
    goes on. Flushes; the step commits."""
    if not (entries or deleted) or not await _ensure(db, applicant_id):
        return {}
    try:
        return (await _merge(db, applicant_id, entries, deleted)).kept_out
    except TooBig:
        log.warning("answer bank full for %s: %d answers not banked", applicant_id, len(entries))
        return {}


def from_apply(answers: Iterable[ApplyAnswer]) -> tuple[list[Kept], list[str]]:
    """Apply's Answer bank entries (its sync, its import) as the bank keeps
    them: a `lisul` entry not marked unreviewed as the student's, the rest
    flagged (services/apply_answers.py, `is_own`), and the questions of the
    empty ones (a multi-select's "none of these" among them), to delete."""
    kept: list[Kept] = []
    empty: list[str] = []
    for a in answers:
        if a.answer in ("", []) or (isinstance(a.answer, str) and not a.answer.strip()):
            empty.append(a.question)
            continue
        kept.append(Kept(question=a.question, answer=a.answer, review=not is_own(a.source, a.reviewed),
                         choice=isinstance(a.answer, list) or bool(a.options), company=a.company))
    return kept, empty


async def drop(db: AsyncSession, applicant_id: uuid.UUID, question: str, answer: str, *, own_only: bool = True) -> None:
    """Takes `question` out of the bank when the bank holds `answer` for it
    (the student took that answer back on its form); a different answer
    there (saved later, or elsewhere) stays, and with `own_only` (the Undo of
    their own words) so does their Claude's. Flushes; the step commits."""
    stored = await answer_banks.fetch(db, applicant_id)
    entry = (stored.answers if stored else {}).get(filed := key(question))
    if not entry or (own_only and entry.get("review")):
        return
    held = "; ".join(entry["answer"]) if isinstance(entry["answer"], list) else entry["answer"]
    if held and held == answer.strip():
        async with db.begin_nested():
            await answer_banks.merge(db, applicant_id, {}, [filed])
