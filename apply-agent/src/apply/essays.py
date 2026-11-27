"""Claude-written answers: every essay one form asks (and a cover letter, to
the template in apply.cover_letter), planned in one Opus call (each essay's
type, parts, story, company fact, angle and slots, each slot backed by lines
quoted from the sources, checked in code) and then written in one Opus call
from the plan's slots only (one Sonnet call when the form has no essays). Facts about Lisul come from the Story bank
and Stock answers only (and their approved core answer of each type, apply.stock); facts about the company come only from its Company
material (apply.company), and each essay ties at most one of them to the applicant.

The same call drafts the form's one-off questions for the Answer bank (short
factual, yes/no and choice questions no rule answers) from their Applicant
profile facts, the Story bank and the Company material already read: one
call per Application, and a small one when the form has no essays.

The questions and the Company material are text from the employer. They are
given to Claude as data, never as instructions; questions aimed at AI agents
never get here (the planner hands them off).
"""

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from apply import answer_bank as answers
from apply import (
    answering,
    asking,
    cover_letter,
    description,
    fill_engine,
    private,
    probe,
    sameness,
    stock,
    story_map,
    truth,
    writing,
)
from apply import home as data_folder  # essays.home() is the applicant's town
from apply.adapters import Claude, lean
from apply.applicant import as_applicant
from apply.model import Posting, Question, is_company, one_line
from apply.profile import ApplicantProfile
from apply.records import SECRET

# The text fields' kinds, as a question names them to Claude.
FIELDS = {"text": "single-line", "textarea": "multi-line"}
DESCRIBED = 400  # characters of a question's description Claude is shown

# A number in an essay: a count, a percentage, a year, a score.
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
# Words that give away how an essay was written: it speaks of Lisul's files
# ("my materials don't say"), hedges about what they lack, or cites the posting
# to its employer ("your posting lists"). An essay saying one is drafted again
# once, and held if it still does.
GIVEAWAY = re.compile(r"""\b(?:
    my\ (?:materials|sources|notes|story\ bank|stock\ answers?)
  | (?:the\ )?story\ bank | stock\ answers?
  | my\ r[eé]sum[eé]\ (?:does\ not|doesn['’]t|do\ not|don['’]t|never|says\ nothing)
  | (?:your|this)\ (?:job\ )?(?:posting|listing|job\ description|job\ ad)
  | the\ (?:job\ )?(?:posting|listing|job\ description|description)\ (?:itself\ )?
      (?:says|said|lists|listed|mentions|mentioned|states|stated|notes|noted|asks|asked|describes|calls\ for|highlights)
  | I\ should\ be\ upfront | to\ be\ upfront
  | rather\ not\ (?:invent|make\ up) | (?:invent|make\ up)\ a\ reason
  | don['’]t\ (?:yet\ )?say\ why | doesn['’]t\ (?:yet\ )?say\ why
  | as\ an\ AI
)\b""", re.IGNORECASE | re.VERBOSE)
PLAN_FIELDS = ("type", "parts", "story", "company_fact", "angle", "link_kind", "slots")
CATCH_ALL = "anything-else"  # the type of a catch-all box ("Additional information"): always blank when optional
REUSABLE = {"anything-else", "cover-letter"}  # types whose answer may lead with a story another answer leads with
QUOTED = 20  # characters a slot's quote needs, so a stray word never backs a slot
ASK = "Essay fact: "  # opens a question for Lisul that a required slot no line backs puts in the Needs you tab


@dataclass(frozen=True)
class Backed:
    """One slot of an Essay plan and the source lines that back it, word for word."""

    slot: str
    quotes: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    """An Essay plan: what one answer will say, picked before it is written."""

    type: str  # its Question type
    parts: tuple[str, ...] = ()  # the separate asks in the question, in order
    story: str = ""  # the Story bank heading or line it leads with, as the bank writes it
    company_fact: str = ""  # the Company brief fact it ties to them, by its name between ** **
    angle: str = ""  # the point it makes, away from the typical applicant's answer
    link_kind: str = ""  # the problem kind its story and company fact share (the story map's), never shown to the writer
    slots: tuple[Backed, ...] = ()  # the slots of its type the sources back, in the guide's order
    asks: tuple[str, ...] = ()  # for each required slot no line backs, the question for Lisul (ASK opens each)

    def shown(self) -> dict:
        return {"type": self.type, "parts": list(self.parts), "story": self.story,
                "company_fact": self.company_fact, "angle": self.angle,
                "slots": {b.slot: list(b.quotes) for b in self.slots}}


@dataclass(frozen=True)
class Essay:
    question: Question
    text: str
    unsupported: tuple[str, ...] = ()  # numbers it states that no source backs (apply.truth)
    needs_lisul: bool = False  # Claude says the question asks for more than the sources hold
    giveaways: tuple[str, ...] = ()  # words that give away how it was written (GIVEAWAY)
    named: str = ""  # its Named fact: the Company brief line it ties to Lisul, as the brief writes it
    plan: "Plan | None" = None  # its Essay plan, as checked
    failed: tuple[str, ...] = ()  # the code gates it fails (apply.gates)
    claims: tuple[str, ...] = ()  # the names, dates and outcomes it states that no source backs (apply.truth)
    sensitive: tuple[str, ...] = ()  # what it tells that most keep private (apply.private): held, never cut


@dataclass(frozen=True)
class Draft:
    """Claude's answer to a one-off question, for the form and the Answer bank."""

    question: Question
    answer: str | list[str]  # an option of the question's, or several for a multi-select; "" when unusable
    needs_lisul: bool = False  # Claude can't answer it from the sources, or its answer isn't one to use
    facts: tuple[str, ...] = ()  # the profile keys and Story bank lines it drew on, as Claude named them

    @property
    def shown(self) -> str:
        return ", ".join(self.answer) if isinstance(self.answer, list) else self.answer


def write(claude: Claude, posting: Posting, questions: list[Question], profile: ApplicantProfile,
          company: str = "", posting_text: str = "") -> list[Essay]:
    """One Claude call answering every question in `questions`. `company` is
    the Application's <company> block (apply.company.gather), if any;
    `posting_text` the Posting's own text (apply.description)."""
    return answer(claude, posting, questions, [], profile, company, posting_text)[0]


BANK_EDITS = 2  # times one answer() starts again on a Story bank edit, so an edit made each minute can't loop it


def bank_stamp() -> tuple[int, int] | None:
    """When the Story bank last changed, as its mtime and size; None when there is none."""
    try:
        found = data_folder.STORY_BANK.stat()
    except OSError:
        return None
    return found.st_mtime_ns, found.st_size


def answer(claude: Claude, posting: Posting, essays: list[Question], drafts: list[Question], profile: ApplicantProfile,
           company: str = "", posting_text: str = "",
           redraft: dict[Question, tuple[str, ...]] | None = None,
           answered: Mapping[Question, object] | None = None,
           planned: Mapping[Question, "Plan"] | None = None,
           redo: Mapping[Question, tuple[str, str]] | None = None,
           sections: Mapping[str, str] | None = None) -> tuple[list[Essay], list[Draft]]:
    """`_answer`, from the Story bank as it is when it returns. Its plan, draft, claim check and
    editor read the bank once, at the start, and take minutes: an edit Lisul saves meanwhile
    would leave his removed facts in the answers. So when the bank changed while it ran, it
    plans and writes again from the new bank, up to BANK_EDITS times (ENFOS, 2026-11-26: the
    WorkIt facts moved out of the bank at 19:50:03, and the editor's passes at 19:50:24 and
    19:50:55 still kept them, read at 19:48)."""
    for tries in range(BANK_EDITS + 1):
        stamp = bank_stamp()
        result = _answer(claude, posting, essays, drafts, profile, company, posting_text, redraft, answered,
                         planned, redo, sections)
        if bank_stamp() == stamp or tries == BANK_EDITS:
            return result
        planned = None  # its plans quote the old bank


def _answer(claude: Claude, posting: Posting, essays: list[Question], drafts: list[Question], profile: ApplicantProfile,
            company: str = "", posting_text: str = "",
            redraft: dict[Question, tuple[str, ...]] | None = None,
            answered: Mapping[Question, object] | None = None,
            planned: Mapping[Question, "Plan"] | None = None,
            redo: Mapping[Question, tuple[str, str]] | None = None,
            sections: Mapping[str, str] | None = None) -> tuple[list[Essay], list[Draft]]:
    """One Claude call writing every essay in `essays` and drafting every
    one-off question in `drafts`, after one call planning the essays (plan),
    unless `planned` gives their Plans already. `company` is the Application's <company>
    block (apply.company.gather), if any; `posting_text` the Posting's own
    text (apply.description), which the call gets in its <posting> block.
    `answered` is the form's answers already planned, by Question: the
    essays see those form_answers lets through, in a <form_answers> block.
    An essay that gives away how it was written is drafted again once, in a
    second call; `redraft` names, for that call, what each essay gave away.
    `redo` gives, by Question, the earlier answer and the context Lisul typed
    when he asked for it again (apply.regenerate): the plan and the draft
    both see them, in a <redo> block.
    `sections` gives each bare date's section by Question name (fill_engine.Plan.sections):
    its draft is told what the date is for, and to ask Lisul when nothing says.

    Each essay is drafted once, from its plan's slots; one whose plan asks
    Lisul for a fact (a required slot no line backs) is not written, and
    comes back empty with those asks in its plan. The draft gets the claim
    check and the editor's pass, whose loop is flagged what the code gates
    (apply.gates) and the sameness checks find; an essay's `failed` holds
    the gates it still fails after it, so its Application is held.

    Claude calls per form with essays: the default probe 0-1 Sonnet (only
    for idea-driven types, and none when cached), the plan 1 Opus (+1 when
    it fails its check), the draft 1 Opus, the claim check 1 Opus and the
    editor 1-3 Opus: 4-7 calls. A form with no essays still costs one
    Sonnet call."""
    if lean(claude) and essays and drafts:  # a smaller model's request limit: the one-off questions go alone
        written, _ = _answer(claude, posting, essays, [], profile, company, posting_text, redraft, answered, planned,
                             redo, sections)
        return written, _answer(claude, posting, [], drafts, profile, company, posting_text, answered=answered,
                                sections=sections)[1]
    claude = as_applicant(claude, profile)  # every prompt says the profile's name and school
    keys = {f"q{i}": q for i, q in enumerate(essays, 1)}
    shown = form_answers(answered or {}, private.self_id(profile))
    defaults = probe.typical(claude, posting, {key: _ask(q) for key, q in keys.items() if question_type(q) in probe.TYPES},
                             company, posting_text)
    if keys and planned is None:
        planned = plan(claude, posting, essays, profile, company, posting_text, shown,
                       {keys[key]: found for key, found in defaults.items()}, redo)
    plans = {key: planned[q] for key, q in keys.items()} if keys else {}
    waiting = {key: q for key, q in keys.items() if plans[key].asks}  # written once Lisul gives the facts
    keys = {key: q for key, q in keys.items() if key not in waiting}
    types = {key: plans[key].type for key in keys}
    short = {f"d{i}": q for i, q in enumerate(drafts, 1)}
    if not keys and not short:
        return [Essay(q, "", plan=plans[key]) for key, q in waiting.items()], []
    # WorkIt's essays.write kind (D5, KAN-723): its prompt, schema and guides are on the server.
    data = {"sources": sources(profile, company, facts=bool(drafts), types=types.values(), posting=posting),
            "posting": description.block(posting, posting_text),
            "style_card": writing.style_card() if keys else "", "form_answers": dict(shown) if keys else {},
            "questions": {key: _sent(q, types[key]) for key, q in keys.items()},
            "plans": {key: plans[key].shown() for key in keys},
            "short_questions": {key: _sent(q) | {"about": (sections or {}).get(q.name)} for key, q in short.items()},
            "redraft": {key: list(redraft[q]) for key, q in keys.items() if q in (redraft or {})},
            "redo": _redone(redo, {**keys, **short})}
    given = claude.ask_kind("essays.write", data)
    # What the call was given, for the gates and the truth check: a number or a name an answer may take from it.
    prompt = "\n".join(filter(None, [data["sources"], data["posting"], data["style_card"], json.dumps(
        {part: data[part] for part in ("form_answers", "questions", "plans", "short_questions", "redraft", "redo")},
        ensure_ascii=False)]))
    written, drafted = given.get("essays") or {}, given.get("drafts") or {}
    texts = {key: cover_letter.letter(written.get(key) or {}, posting, profile) if cover_letter.is_cover_letter(q)
             else str((written.get(key) or {}).get("answer") or "").strip() for key, q in keys.items()}
    material = "\n".join(filter(None, [sources(profile, company, types=types.values(), employer=posting.company),
                                       description.block(posting, posting_text)]))
    checked = {key: _Checked(keys[key], types[key], f"{prompt}\n{keys[key].label}\n{keys[key].description}",
                             posting.company, company, profile.get("files.resume_pdf")) for key in keys}
    letter_keys = frozenset(key for key, q in keys.items() if cover_letter.is_cover_letter(q))
    questions = {key: _ask(q) for key, q in keys.items()}
    lengths = {key: length for key in keys if (length := _default_length(keys[key], types[key]))}
    if drafted_texts := {key: text for key, text in texts.items() if text}:  # the editor's pass (apply.writing)
        same = _sameness(posting.company, types, {key: found.answer for key, found in defaults.items()}, set(letter_keys))
        texts |= writing.edit(claude, drafted_texts, material, letter_keys & set(drafted_texts),
                              {key: questions[key] for key in drafted_texts},
                              {key: lengths[key] for key in drafted_texts if key in lengths},
                              lambda key, answers: [*_gate(checked, answers).get(key, []), *same(key, answers)])
    failed = _gate(checked, texts)
    if over := _over_cap(checked, texts):  # one shorter rewrite; still over a stated cap, the worker keeps it off the form
        texts |= writing.repair(claude, {key: texts[key] for key in over}, material, over, letter_keys & set(over),
                                {key: questions[key] for key in over}, {key: lengths[key] for key in over if key in lengths})
        failed = _gate(checked, texts)
    own = own_facts(profile, types.values(), posting.company)
    # The posting, the Company material and the question may give a number or a name; a cover letter's
    # template gives its salutation ("Recruiting Team").
    given = (company, description.block(posting, posting_text), cover_letter.TEMPLATE)
    found = {key: truth.unsupported(texts[key], own, (*given, q.label, q.description), plans[key].story if plans[key] else "")
             for key, q in keys.items()}
    result = [Essay(q, texts[key], tuple(c.text for c in found[key] if c.kind == "number"),
                    (written.get(key) or {}).get("needs_lisul") is True, giveaways(texts[key]),
                    _named(written.get(key) or {}, plans[key], texts[key], company), plans[key],
                    tuple(failed[key]) if texts[key] else (),
                    tuple(c.said() for c in found[key] if c.kind != "number"), private.sensitive(texts[key], profile))
              if key in keys else Essay(q, "", plan=plans[key])
              for key, q in {**keys, **waiting}.items()]
    result.sort(key=lambda e: essays.index(e.question))
    if again := {e.question: e.giveaways for e in result if e.giveaways and redraft is None}:
        redone = {e.question: e for e in _answer(claude, posting, list(again), [], profile, company, posting_text, again,
                                                 answered, planned, redo)[0]}
        result = [redone.get(e.question, e) for e in result]
    return result, [_draft(q, drafted.get(key) or {}, prompt, profile, own) for key, q in short.items()]


def _redone(redo: Mapping[Question, tuple[str, str]] | None, keys: Mapping[str, Question]) -> dict[str, dict]:
    """Each question Lisul asked to have written again, by its key, with the earlier answer and the
    context he typed: a kind's `redo`."""
    return {key: {"earlier_answer": redo[q][0], "added_context": redo[q][1]} for key, q in keys.items() if q in (redo or {})}


def _sent(q: Question, kind: str | None = None) -> dict:
    """`q` as a kind's data holds it (backend/app/apply_prompts/essays.py's Question), with its Question
    type when it is an essay."""
    return {"label": q.label, "kind": q.kind, "required": q.required, "options": list(q.options),
            "description": q.description, "max_length": q.max_length, "section": q.section} | (
        {"type": kind} if kind else {})


def _sameness(company: str, types: Mapping[str, str], defaults: Mapping[str, str], letters: set[str]):
    """The editor's sameness checks (apply.sameness) for one form's answers,
    by key: their voice, the typical answer the default probe gave, their past
    answers in the ledger, the form's other answers and the swap test. A
    cover letter is left out: its template opens and closes alike."""
    voice, ledger = writing.samples(), sameness.Ledger()

    def check(key: str, answers: dict[str, str]) -> list[str]:
        if key in letters:
            return []
        others = {k: text for k, text in answers.items() if k != key and k not in letters and text}
        return [flag for flag in sameness.check(answers[key], type=types[key], form_answers=others, samples=voice,
                                                default=defaults.get(key) or None, ledger=ledger, company=company)
                if not flag.startswith(UNWANTED_DRIFT)]
    return check


# A voice-drift flag the writing rules overrule: WRITE asks for 12-25-word
# sentences (writing.LONGEST splits longer ones), while their samples average
# 21-46 words, so "join some short ones" would fight the long-sentence flag.
UNWANTED_DRIFT = ("voice: sentences average",)


def plan(claude: Claude, posting: Posting, essays: list[Question], profile: ApplicantProfile, company: str = "",
         posting_text: str = "", shown: Mapping[str, object] | None = None,
         typical: Mapping[Question, "probe.Typical"] | None = None,
         redo: Mapping[Question, tuple[str, str]] | None = None) -> dict[Question, Plan]:
    """The Plan of every essay in `essays`, from one Claude call over the
    whole form, checked in code (check_plan). `typical` is the default
    probe's answer to each idea-driven essay (apply.probe): the plan's angles
    must steer away from its typical angles. A plan that fails a check is
    asked for again once, with its failures listed; a field that still fails
    is dropped (a story or company fact to "", parts to the question itself,
    a quote no source holds) rather than hold the form. Only a required slot
    that no quote backs then waits: its question for Lisul goes in the Plan's
    asks, and the essay is written once they answer it (remember_fact).
    `redo` is the earlier answer and Lisul's added context of each essay he
    asked to have written again (apply.regenerate)."""
    claude = as_applicant(claude, profile)
    keys = {f"q{i}": q for i, q in enumerate(essays, 1)}
    classified = {key: question_type(q) for key, q in keys.items()}
    bank = story_bank(posting.company)
    mapped = story_map.load() if story_map.MAP.is_file() else []
    angles = {key: list(found.angles) for key, q in keys.items() if (found := (typical or {}).get(q)) and found.angles}
    led = {kind: stories for kind, stories in sameness.Ledger().led(posting.company).items()
           if kind in classified.values()}
    held = "\n".join([sources(profile, company, types=answering.load(), employer=posting.company),
                      description.block(posting, posting_text),
                      json.dumps(shown or {}, ensure_ascii=False)])
    plans = _fact_quoted(_ask_plan(claude, posting, keys, classified, profile, company, posting_text, shown or {},
                                   mapped=mapped, angles=angles, led=led, redo=redo), company, held)
    if failed := check_plan(plans, company, bank, mapped, held):
        plans = _fact_quoted(_ask_plan(claude, posting, keys, classified, profile, company, posting_text, shown or {},
                                       failed, mapped, angles, led, redo), company, held)
        for key, fields in check_plan(plans, company, bank, mapped, held).items():
            plans[key] = replace(plans[key], **{field: _DROPPED[field](keys[key])
                                   for field in [*fields, *(["link_kind"] if "company_fact" in fields else [])]
                                   if field != "slots"})
    return {q: _backed(plans[key], held, profile, posting.company) for key, q in keys.items()}


FACT_SLOT = "company-fact"  # the slot that holds the Company brief fact a plan ties


def _fact_quoted(plans: dict[str, Plan], company: str, held: str) -> dict[str, Plan]:
    """`plans` with each company-fact slot that no quote backs quoted from the brief line its plan's company_fact
    names: the model chose the fact but didn't copy its line (gpt-oss and Gemini, KAN-723, 2026-11-10)."""
    text = _quotable(held)

    def quoted(p: Plan) -> Plan:
        line = named_fact(p.company_fact, company)
        if not line or FACT_SLOT not in {s.name for s in answering.load()[p.type].slots}:
            return p
        given = next((b for b in p.slots if b.slot == FACT_SLOT), None)
        if given and _backers(given, text):
            return p
        backed = _Given(FACT_SLOT, (line,), "")
        return replace(p, slots=(*(b for b in p.slots if b.slot != FACT_SLOT), backed))
    return {key: quoted(p) for key, p in plans.items()}


# What a field of a Plan that fails its check twice becomes.
_DROPPED = {"story": lambda q: "", "company_fact": lambda q: "", "parts": lambda q: (one_line(q.label),),
            "link_kind": lambda q: ""}


def check_plan(plans: Mapping[str, Plan], company: str, bank: str,
               mapped: Sequence[story_map.Entry] = (), held: str | None = None) -> dict[str, dict[str, str]]:
    """What fails a check in `plans`, by key and field: a story not in the
    Story bank text `bank`, a story another answer already leads with
    (anything-else and cover letters may reuse one), a company fact that
    names no Company brief line in `company` or sits on a type that never
    links the company, no parts, and a slot whose quote is not in `held` (the
    sources the plan saw; `bank` when not given) or a required slot no quote
    backs. When the story has an entry in the story map `mapped`, its company
    fact must share a problem kind with it: the plan's link_kind is one of the
    story's problem kinds and one of the fact's brief tags."""
    failed: dict[str, dict[str, str]] = {}
    known, led = _plain(bank), {}
    for key, p in plans.items():
        found = {}
        if story := _plain(p.story):
            if len(story) < 8 or story not in known:
                found["story"] = f"{p.story!r} is not a heading or line of <story_bank>"
            elif p.type not in REUSABLE and story in led:
                found["story"] = f"{p.story!r} already leads the answer to {led[story]}"
            elif p.type not in REUSABLE:
                led[story] = key
        if p.company_fact:
            if not named_fact(p.company_fact, company):
                found["company_fact"] = f"{p.company_fact!r} is not a fact's name in the brief in <company>"
            elif answering.load()[p.type].company_link == "never":
                found["company_fact"] = f"a {p.type} answer never ties a company fact"
            elif (entry := episode(p.story, mapped)) and not (p.link_kind in entry.problem_kinds
                                                               and p.link_kind in fact_tags(p.company_fact, company)):
                found["company_fact"] = (f"{p.company_fact!r} shares no problem kind with the story {entry.id} "
                                         f"(link_kind {p.link_kind!r}): its tags and the story's kinds must both hold it")
        if not p.parts:
            found["parts"] = "no parts"
        if slots := _slot_failures(p, bank if held is None else held):
            found["slots"] = "; ".join(slots)
        if found:
            failed[key] = found
    return failed


def _slot_failures(p: Plan, held: str) -> list[str]:
    """Each quote of `p`'s slots that `held` doesn't hold, and each required
    slot of its type (or asked slot it gives) that no quote backs."""
    text, guide = _quotable(held), {s.name: s for s in answering.load()[p.type].slots}
    given = {b.slot: b for b in p.slots if b.slot in guide}
    wrong = [f"{b.slot}: {q!r} is not word for word in the sources" for b in given.values() for q in b.quotes
             if not _holds(text, q)]
    bare = [f"{name}: no quote backs it" for name, slot in guide.items()
            if (slot.required is True or name in given and slot.required) and not _backers(given.get(name), text)]
    return wrong + bare


def _backed(p: Plan, held: str, profile: ApplicantProfile | None = None, employer: str = "") -> Plan:
    """`p` with only the quotes `held` holds, its unbacked optional slots left
    out, in its guide's order, and the question for Lisul of each required
    slot no quote backs in its asks. A question Apply already holds the
    answer to (apply.asking.known: a link, a fact Lisul gave before) is
    never asked: what it holds backs the slot instead."""
    text, guide = _quotable(held), answering.load()[p.type].slots
    given = {b.slot: b for b in p.slots}
    wanted = lambda s: s.required is True or s.required and s.name in given
    asked = {s.name: ASK + (b.ask if (b := given.get(s.name)) and getattr(b, "ask", "") else f"{s.holds}?")
             for s in guide if wanted(s) and not _backers(given.get(s.name), text)}
    found = {name: facts for name, ask in asked.items() if profile and (facts := asking.known(ask, profile, employer=employer))}
    slots = tuple(Backed(s.name, quotes) for s in guide
                  if (quotes := _backers(given.get(s.name), text) or found.get(s.name, ())))
    return replace(p, slots=slots, asks=tuple(ask for name, ask in asked.items() if name not in found))


def _backers(given: "Backed | None", text: str) -> tuple[str, ...]:
    return tuple(q for q in given.quotes if _holds(text, q)) if given else ()


def _holds(text: str, quote: str) -> bool:
    """Whether the sources' quotable `text` holds `quote` word for word: the same words in the same order, whole."""
    quote = _quotable(quote)
    return len(quote) >= QUOTED and f" {quote} " in f" {text} "


# Small numbers a model may spell out in a quote the sources give as digits ("every five minutes" for "every
# 5 minutes": gpt-oss, KAN-723, 2026-11-10), and the other way round: either form is the same word.
NUMBER_WORDS = {word: str(n) for n, word in enumerate((
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"))} | {
    "thirty": "30", "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
    "hundred": "100"}


def _quotable(text: str) -> str:
    """`text` for matching a quote: its words only, casefolded, in one line, with small numbers as digits.
    Punctuation, markdown and quote marks drop out, so a quote that adds or drops a comma still holds."""
    return " ".join(NUMBER_WORDS.get(word, word) for word in re.findall(r"\w+", _plain(text)))


def episode(story: str, mapped: Sequence[story_map.Entry]) -> "story_map.Entry | None":
    """The story map entry `story` names: by its id, or as its line (the
    story holds the entry's opening words, or is part of them)."""
    plain = _plain(story)
    return next((e for e in mapped if story == e.id or (plain and (_plain(e.anchor) in plain or
                                                                  (len(plain) >= 8 and plain in _plain(e.anchor)))))
                , None)


def fact_tags(name: str, company: str) -> tuple[str, ...]:
    """The problem tags of the Company brief fact `name` in `company`, from
    its line's note ("(2026-06, engineering; tags: a, b)"); () when none."""
    line = named_fact(name, company)
    note = re.match(r"\*\*[^*]+\*\*\s*\(([^()]*)\)", line)
    tags = re.search(r"tags:\s*(.*)$", note[1]) if note else None
    return tuple(t.strip() for t in tags[1].split(",") if t.strip()) if tags else ()


# Hyphens a model may type for "-": gpt-oss writes the non-breaking one (U+2011) inside words it quotes
# word for word ("made‑up"), so a true quote failed the plan's check (KAN-723, 2026-11-10).
HYPHENS = str.maketrans({"\u2010": "-", "\u2011": "-"})


def _plain(text: str) -> str:
    """`text` for matching a story: one line, casefolded, without markdown marks, with plain hyphens."""
    return one_line(text.replace("’", "'").translate(HYPHENS)).strip("#*->: ").casefold()


def _ask_plan(claude: Claude, posting: Posting, keys: Mapping[str, Question], classified: Mapping[str, str],
              profile: ApplicantProfile, company: str, posting_text: str, shown: Mapping[str, object],
              failed: Mapping[str, dict[str, str]] | None = None,
              mapped: Sequence[story_map.Entry] = (), angles: Mapping[str, list[str]] | None = None,
              led: Mapping[str, list[str]] | None = None,
              redo: Mapping[Question, tuple[str, str]] | None = None) -> dict[str, Plan]:
    # WorkIt's essays.plan kind (D5, KAN-723): its prompt, schema and guides are on the server.
    data = {"sources": sources(profile, company, types=classified.values(), employer=posting.company),
            "posting": description.block(posting, posting_text),
            "questions": {key: _sent(q, classified[key]) for key, q in keys.items()}, "form_answers": dict(shown),
            "story_map": story_map.prompt_block(list(mapped)) if mapped else "", "typical": dict(angles or {}),
            "led_before": dict(led or {}), "replan": dict(failed or {}), "redo": _redone(redo, keys)}
    given = claude.ask_kind("essays.plan", data).get("plan") or {}
    plans = {key: _plan(given.get(key), classified[key], keys[key]) for key in keys}
    # An episode id names its line: the writer sees the Story bank, never the map.
    return {key: replace(p, story=entry.anchor) if (entry := next((e for e in mapped if e.id == p.story), None)) else p
            for key, p in plans.items()}


@dataclass(frozen=True)
class _Given(Backed):
    """A slot as the planner gave it, with its question for Lisul."""

    ask: str = ""


def _plan(given: object, classified: str, q: Question) -> Plan:
    """Claude's plan entry as a Plan: an unknown type falls back to the classifier's,
    and a cover letter is always one."""
    given = given if isinstance(given, dict) else {}
    kind = str(given.get("type") or "")
    if cover_letter.is_cover_letter(q) or kind not in answering.load():
        kind = classified
    parts = given.get("parts")
    slots = [s for s in given.get("slots") or [] if isinstance(s, dict)] if isinstance(given.get("slots"), list) else []
    return Plan(kind, tuple(one_line(str(p)) for p in parts if str(p).strip()) if isinstance(parts, list) else (),
                one_line(str(given.get("story") or "")), one_line(str(given.get("company_fact") or "")).strip("*"),
                one_line(str(given.get("angle") or "")), one_line(str(given.get("link_kind") or "")),
                tuple(_Given(one_line(str(s.get("slot") or "")),
                             tuple(str(quote).strip() for quote in s.get("quotes") or [] if str(quote).strip())
                             if isinstance(s.get("quotes"), list) else (),
                             one_line(str(s.get("ask") or ""))) for s in slots))


def _named(written: dict, planned: Plan, text: str, company: str) -> str:
    """An essay's Named fact: the brief line it says it named, else its plan's
    company fact when the text names it; "" for an empty essay."""
    if not text:
        return ""
    if named := named_fact(written.get("named"), company):
        return named
    fact = planned.company_fact
    return named_fact(fact, company) if fact and fact.casefold() in text.casefold() else ""


@dataclass(frozen=True)
class _Checked:
    """What the gates need of one essay question."""

    question: Question
    type: str
    sources: str  # what its facts may come from: the drafting call's prompt and the question
    company: str  # the company's name
    brief: str  # the <company> block, with the Company brief
    resume: Path | None = None  # the profile's resume PDF, for the not-on-resume gate

    def gates(self, text: str) -> list[str]:
        from apply import gates  # gates imports this module
        return gates.answer(text, self.question, self.type, self.sources, self.company, self.brief,
                            letter=self.type == "cover-letter", resume=self.resume)


def _gate(checked: Mapping[str, _Checked], texts: Mapping[str, str]) -> dict[str, list[str]]:
    """The code gates' failures for each of `texts`, an answer per key, read
    as one form's answers (a letter without its salutation and sign-off)."""
    from apply import gates
    body = lambda key, text: "\n".join(text.splitlines()[1:-2]) if checked[key].type == "cover-letter" else text
    across = gates.form({key: body(key, text) for key, text in texts.items() if text})
    return {key: [*checked[key].gates(text), *across.get(key, [])] if text else ["empty"] for key, text in texts.items()}


def _over_cap(checked: Mapping[str, _Checked], texts: Mapping[str, str]) -> dict[str, list[str]]:
    """The essays over a cap their form states (gates.over_cap), or over the most
    their length allows (gates.length: the type's default, when the form states
    none; Bedrock's, live 2026-11-04, went on the form at 132 words of 120), by
    key, each with that failure and what the rewrite must do."""
    from apply import gates
    over = {}
    for key, text in texts.items():
        if not text:
            continue
        q = checked[key].question
        if stated := gates.over_cap(text, q):
            over[key] = [*stated, SHORTER]
        elif long := [f for f in gates.length(text, q, checked[key].type) if f.startswith(gates.TOO_LONG)]:
            over[key] = [*long, CUT]
    return over


# What the one rewrite of an essay over its limit is told (_over_cap); SHORTER when the form states the limit.
CUT = ("rewrite it shorter, under the most the line above gives, counted over the whole text (a letter's "
       "salutation and sign-off too): cut whole sentences, keep the facts it needs.")
SHORTER = f"{CUT} The form refuses a longer answer."


# Heads the Story bank's section of Lisul's answers to the questions essays asked them (ASK).
ANSWERED = "## Answered during applications"


def remember_fact(asked: str, answer: str, company: str, today: date) -> None:
    """Lisul's answer to a question an essay asked them (`asked`, opened by
    ASK), as a Story bank line under ANSWERED, so this essay and every one
    after can quote it. An answer already there is not added again."""
    fact = f"- {one_line(asked.removeprefix(ASK))} {one_line(answer)}"
    bank = data_folder.STORY_BANK.read_text()
    if fact in bank:
        return
    if ANSWERED not in bank:
        bank = f"{bank.rstrip()}\n\n{ANSWERED}\nThe applicant's own answers to what an essay asked during a fill, word for word.\n"
    data_folder.STORY_BANK.write_text(f"{bank.rstrip()}\n{fact} (asked for {company}, {today.isoformat()})\n")


# One line under ANSWERED: the question and answer, then the company it was asked for and the day.
ANSWERED_LINE = re.compile(r"^- (?P<said>.*) \(asked for (?P<company>.+), \d{4}-\d{2}-\d{2}\)$")
# A question whether he applies to other roles there ("...other internships here?"): its answer is that company's
# even when it doesn't name it (apply.other_roles answers it now; this keeps an earlier answer to it).
_ROLES = r"(?:roles?|positions?|jobs?|internships?|openings?|postings?)"
OTHER_ROLES = re.compile(rf"\bappl(?:y|ying|ied)\b[^.?]{{0,80}}?\b(?:other|another|additional|more\s+than\s+one|besides)\b"
                         rf"[^.?]{{0,40}}?\b{_ROLES}\b|\b(?:other|another|additional|more\s+than\s+one)\s+(?:\w+\s+){{0,3}}?"
                         rf"{_ROLES}\b[^.?]{{0,80}}?\bappl(?:y|ying|ied)\b|\bonly\s+(?:\w+\s+){{0,3}}?(?:{_ROLES}|one)\b"
                         rf"[^.?]{{0,60}}?\bapplying\b", re.IGNORECASE)


def story_bank(employer: str = "") -> str:
    """The Story bank as the essays read it. A line under ANSWERED that names
    the company it was asked for is true of that company only ("No, this is
    the only Strava internship I'm applying to"), as is one on other roles
    there that doesn't name it: it is kept for `employer`'s forms and left
    out of every other's (Strava, 2026-11-26)."""
    kept, under = [], False
    for line in data_folder.STORY_BANK.read_text().splitlines(keepends=True):
        if line.startswith("## "):
            under = line.strip() == ANSWERED
        elif under and (m := ANSWERED_LINE.match(line.strip())) and (re.search(
                rf"(?<!\w){re.escape(asked := m["company"].strip())}(?!\w)", m["said"], re.IGNORECASE)
                or OTHER_ROLES.search(m["said"])) and not (
                employer.strip() and (is_company(employer, asked) or is_company(asked, employer))):
            continue
        kept.append(line)
    return "".join(kept)


def form_answers(answered: Mapping[Question, object], self_ids: frozenset[str] = frozenset()) -> dict[str, str | list[str]]:
    """The answers already given on the form that an essay may refer to ("the
    area you picked"), by question label: choices and short text only, never
    a file, an essay, a secret or an answer that is exactly one of the
    student's self-ID answers (`self_ids`: private.self_id, D8). The private
    details in them go as placeholders (apply.private)."""
    return {one_line(q.label): a for q, a in answered.items()
            if q.kind in ("select", "multi_select", "text") and a and isinstance(a, (str, list))
            and not (SECRET.search(q.label) or SECRET.search(q.name) or private.is_self_id(a, self_ids))}


def named_fact(name: object, company: str) -> str:
    """The Company brief line in `company` (the <company> block) for the
    product Claude says an essay named, without its "- "; "" when Claude
    named none, or a name no brief line has."""
    name = one_line(str(name or "")).strip("*").casefold()
    return next((line[2:] for line in company.splitlines()
                 if name and line.startswith("- **") and line[4:].split("**")[0].casefold() == name), "")


def giveaways(text: str) -> tuple[str, ...]:
    """The words in `text` that give away how it was written (GIVEAWAY), as it says them."""
    return tuple(dict.fromkeys(m.group() for m in GIVEAWAY.finditer(text)))


def sources(profile: ApplicantProfile, company: str = "", facts: bool = False, types: Iterable[str] = (),
            posting: Posting | None = None, employer: str = "") -> str:
    """What essays may draw on: the Story bank and Lisul's Stock answers, their
    approved core answer (apply.stock) of each Question type in `types`, the
    Application's Company material when it has some, the town they live
    in (<home>), the profile's graduation date (<graduation>: apply.asking.graduation,
    which holds over another date the Story bank gives), and their links (<links>: apply.asking.links). With
    `facts`, their Applicant profile facts too, for drafted answers to
    one-off questions: with `posting`, as the plan reads them (profile_facts).
    The Story bank is `employer`'s (story_bank: `posting`'s company when no
    `employer` is given)."""
    employer = employer or (posting.company if posting else "")
    own = {key: value for key, value in (profile.get("stock_answers") or {}).items() if value}
    return (
        (profile_block(profile, posting) if facts else "")
        + (f"<home>\n{place}\n</home>\n" if (place := home(profile)) else "")
        + (f"<graduation>\n{graduates}\n</graduation>\n" if (graduates := asking.graduation(profile)) else "")
        + f"<story_bank>\n{story_bank(employer)}</story_bank>\n"
        + (f"<links>\n{chr(10).join(held)}\n</links>\n" if (held := asking.links(profile)) else "")
        + f"<stock_answers>\n{json.dumps(own, indent=1)}\n</stock_answers>"
        + (f"\n{core}" if (core := stock.material(types)) else "")
        + (f"\n{company}" if company else "")
    )


def own_facts(profile: ApplicantProfile, types: Iterable[str] = (), employer: str = "") -> str:
    """What Lisul gave, for the truth check (apply.truth): his Applicant profile
    facts, the Story bank, his Stock answers and core answers of `types`, his
    links and town (`sources` with `facts`), and the Answer bank's answers in
    his own words (`source: lisul`, the rule WorkIt's sync keeps too). A
    draft of Claude's is no fact of his, even once reviewed. The Story bank
    is `employer`'s (story_bank)."""
    bank = profile.folder / answers.FILE
    mine = [entry for entry in answers.AnswerBank(bank).entries() if entry.source == answers.LISUL] if bank.exists() else []
    return "\n".join([sources(profile, facts=True, types=types, employer=employer),
                      *(f"{e.question}: {'; '.join(e.answer) if isinstance(e.answer, list) else e.answer}" for e in mine)])


def profile_block(profile: ApplicantProfile, posting: Posting | None = None) -> str:
    """Their Applicant profile facts as a <profile> block (profile_facts)."""
    return f"<profile>\n{json.dumps(profile_facts(profile, posting), indent=1, default=str)}\n</profile>\n"


def home(profile: ApplicantProfile) -> str:
    """Where they live, without the street: "Springfield, IL 62701, United States". The ZIP code stays: an essay
    box can ask where they would move from (Applied Materials, live)."""
    a = profile.get("identity.home_address") or {}
    state_zip = " ".join(filter(None, [a.get("state"), a.get("zip")]))
    return ", ".join(filter(None, [a.get("city"), state_zip, a.get("country")]))


# Profile sections a model call is never sent: files (paths on Lisul's Mac), Stock answers (given apart, in
# <stock_answers>) and the self-identification (EEO) answers (D8). The private details in the rest go as
# placeholders (apply.private).
NOT_FACTS = {"files", "stock_answers", "voluntary_self_id"}


def profile_facts(profile: ApplicantProfile, posting: Posting | None = None) -> dict:
    """Lisul's Applicant profile as data for Claude: every fact they gave but NOT_FACTS and a secret they
    answered. With `posting`, the Tracker's past applications and interviews join the screeners as the plan
    joins them (fill_engine.with_past_applications)."""
    facts = {key: value for key, value in profile.facts().items() if key not in NOT_FACTS}
    if isinstance(answered := facts.get("answered_questions"), dict):
        facts["answered_questions"] = {q: a for q, a in answered.items() if not SECRET.search(q)}
    return fill_engine.with_past_applications(facts, posting) if posting is not None else facts


NAMED = "Named: "  # starts the line under an essay's heading that gives its Named fact
PLANNED = "Plan: "  # starts the line under an essay's heading that gives its Essay plan
CHECKS = "Checks: "  # starts the line under its Plan line that gives the checks it fails


def as_cell(essays: list[Essay]) -> str:
    """A held Application's essays as one Tracker cell, for Lisul to read and
    edit: each is a "## <question>" line, its Essay plan on a "Plan: <type> |
    <story> | <angle>" line if it has one, the checks it fails on a "Checks: "
    line if any, its Named fact on a "Named: " line if it has one, then its
    text, then a blank line."""
    return "\n\n".join(f"## {one_line(e.question.label)}\n"
                       + (f"{PLANNED}{e.plan.type} | {e.plan.story} | {e.plan.angle}\n" if e.plan else "")
                       + (f"{CHECKS}{'; '.join(e.failed)}\n" if e.failed else "")
                       + (f"{NAMED}{e.named}\n" if e.named else "") + e.text
                       for e in essays)


def from_cell(cell: str, questions: list[Question]) -> list[Essay]:
    """Lisul's (perhaps edited) essays from a held row's Essay cell, the
    format `as_cell` writes, one per question in `questions`. Only a "## "
    line naming one of those questions starts an essay, so their text may hold
    anything else; a question their cell lacks gets an empty essay. A "Plan: "
    and a "Checks: " line under a heading are skipped (a cell may have neither)."""
    labels = {one_line(q.label): q for q in questions}
    texts: dict[str, list[str]] = {}
    current = None
    for line in cell.replace("\r\n", "\n").split("\n"):
        heading = one_line(line[3:]) if line.startswith("## ") else None
        if heading in labels:
            current = texts.setdefault(heading, [])
        elif current is not None:
            current.append(line)
    result = []
    for label, q in labels.items():
        lines = texts.get(label, [])
        if lines and lines[0].startswith(PLANNED):  # shown to Lisul, never sent
            lines.pop(0)
        if lines and lines[0].startswith(CHECKS):  # shown to Lisul, never sent
            lines.pop(0)
        named = lines.pop(0)[len(NAMED):].strip() if lines and lines[0].startswith(NAMED) else ""
        result.append(Essay(q, "\n".join(lines).strip(), named=named))
    return result


def headings(cell: str) -> list[Question]:
    """The questions an Essay cell heads its essays with ("## <question>")."""
    labels = dict.fromkeys(line[3:].strip() for line in cell.splitlines() if line.startswith("## "))
    return [Question(f"essay-{n}", label, "textarea", True) for n, label in enumerate(labels) if label]


def _blocks(cell: str) -> list[tuple[str, list[str], str]]:
    """An Essay cell (as_cell's format) cut into its essays: each one's "## " heading line, the Plan, Checks
    and Named lines under it, and its text."""
    blocks: list[tuple[str, list[str], list[str]]] = []
    for line in cell.replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            blocks.append((line, [], []))
        elif blocks:
            _, kept, text = blocks[-1]
            (kept if not text and line.startswith((PLANNED, CHECKS, NAMED)) else text).append(line)
    return [(heading, kept, "\n".join(text).strip()) for heading, kept, text in blocks]


def cell_texts(cell: str) -> list[tuple[str, str]]:
    """A held cell's essays as the Apply window shows them for Lisul to edit: each (question, text). Only the
    text is his to edit: the heading and the Plan, Checks and Named lines stay as Apply wrote them."""
    return [(one_line(heading[3:]), text) for heading, _, text in _blocks(cell)]


def with_texts(cell: str, texts: Sequence[str]) -> str:
    """The cell with Lisul's text in place of each essay's text, in order (cell_texts), and the headings and
    the Plan, Checks and Named lines as stored, so `from_cell` reads his words for each question. ValueError,
    with words for Lisul, for an empty essay or a count that is not the cell's."""
    blocks = _blocks(cell)
    if len(texts) != len(blocks):
        raise ValueError("The essays changed since the window showed them. Reload the window and edit them again.")
    for (heading, _, _), text in zip(blocks, texts):
        if not text.strip():
            raise ValueError(f'The essay for "{one_line(heading[3:])}" is empty. Write it, or put back Claude\'s.')
    return "\n\n".join("\n".join([heading, *kept, text.strip()]) for (heading, kept, _), text in zip(blocks, texts))


def unsupported_numbers(text: str, *sources: str) -> tuple[str, ...]:
    """The numbers `text` states that none of `sources` does. A fact Claude
    invents most often shows as a number: a count, a percentage, a year."""
    known = {_digits(n) for source in sources for n in NUMBER.findall(source)}
    return tuple(dict.fromkeys(n for n in _numbers(text) if _digits(n) not in known))


def _numbers(text: str) -> list[str]:
    return [m.group() + ("%" if text[m.end():m.end() + 1] == "%" else "") for m in NUMBER.finditer(text)]


def _digits(number: str) -> str:
    return number.replace(",", "").rstrip("%")


def _ask(q: Question) -> str:
    """The question as the essay call reads it: its label first, then what else
    the form says of it in brackets (its description, whether it is required,
    the field's kind, its limit)."""
    label = one_line(q.label)
    asked = f"{label} (write the cover letter)" if cover_letter.is_cover_letter(q) else label
    about = [_described(q), "required" if q.required else "optional", q.kind in FIELDS and f"{FIELDS[q.kind]} field",
             q.max_length and f"at most {q.max_length} characters"]
    return f"{asked} [{'; '.join(filter(None, about))}]"


def _described(q: Question) -> str:
    """The question's description on one line, cut to about DESCRIBED characters."""
    text = one_line(q.description)
    return text if len(text) <= DESCRIBED else text[:DESCRIBED].rsplit(" ", 1)[0] + " …"


def catch_all(q: Question) -> bool:
    """Whether `q` is an optional catch-all box ("Additional information", "Anything else?",
    "Comments"): always left blank on purpose, never drafted nor asked (Lisul, 2026-11-04)."""
    return not q.required and question_type(q) == CATCH_ALL


def question_type(q: Question) -> str:
    """The Question type of `q` (apply.answering), from its label and description."""
    return "cover-letter" if cover_letter.is_cover_letter(q) else answering.classify(f"{q.label} {q.description}")


# A length the form states in a question's label or description.
STATED = re.compile(r"\b\d+\s*(?:(?:-|–|to)\s*\d+\s*)?(?:words?|sentences?|characters?|chars|paragraphs?|lines?)\b"
                    r"|\b(?:a few|a couple of|one|two|three|four|five|a single) (?:short )?(?:sentences?|words?|paragraphs?|lines?)\b"
                    r"|\b(?:word|character) (?:limit|count)\b", re.IGNORECASE)


def _default_length(q: Question, kind: str) -> str:
    """The type's default length, as "70-120 words", when the form states none
    (no limit, no single-line field, no length in its words); else ""."""
    if kind == "cover-letter" or q.max_length or q.kind == "text" or STATED.search(f"{q.label} {q.description}"):
        return ""
    low, high = answering.load()[kind].length
    return f"{low}-{high} words"


def _unread(q: Question) -> bool:
    """A choice whose options weren't read (Claude fill saw a closed dropdown): answered in words."""
    return all(re.match(r"^\W*((select|choose|pick)\b.*)?$", o.strip(), re.IGNORECASE) for o in q.options)


def _draft(q: Question, given: dict, prompt: str, profile: ApplicantProfile, own: str) -> Draft:
    """Claude's draft, or one that needs Lisul: one Claude says it can't
    answer, an empty one, a choice that isn't among the options, or words
    the truth check (apply.truth, KAN-750) finds a claim in: a number or a
    name nothing in the call (`prompt`) holds, or an outcome none of his
    facts (`own`) states about its project. Not a date: the profile keeps
    its dates as values ("2027-05-24"), not as "May 2027"."""
    answer = given.get("answer")
    choices = q.options if q.options and not _unread(q) else None
    if q.kind == "multi_select" and choices:
        picked = [a for a in answer if a in choices] if isinstance(answer, list) else [answer] if answer in choices else []
        usable = bool(picked) and len(picked) == (len(answer) if isinstance(answer, list) else 1)
        answer = picked
    else:
        answer = str(answer or "").strip()
        usable = bool(answer) and (answer in choices if choices else not [
            c for c in truth.unsupported(answer, own, prompt) if c.kind != "date"])
    if given.get("needs_lisul") is True or not usable:
        return Draft(q, "", needs_lisul=True)
    return Draft(q, answer, facts=_facts(given.get("facts"), profile))


def _facts(named: object, profile: ApplicantProfile) -> tuple[str, ...]:
    """The facts Claude named that a source holds: a profile key it was sent,
    or a Story bank line word for word; any other is dropped, unchecked."""
    story = data_folder.STORY_BANK.read_text()
    facts = profile_facts(profile)
    held = lambda f: (f.split(".")[0] in facts and profile.get(f) is not None) or (len(f) > 10 and f in story)
    return tuple(dict.fromkeys(f.strip() for f in named if isinstance(f, str) and held(f.strip()))) \
        if isinstance(named, list) else ()
