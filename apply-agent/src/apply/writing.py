"""How Claude writes for Lisul: one shared prompt for every answer it writes
(essays, cover letters), and one editor's pass over them all, built on
research/writing-prompt.md.

The drafting call (apply.essays) gets WRITE beside its rules on facts and the
guidance for each Question type on the form (apply.answering), and Lisul's style card (voice.md) beside their own writing in the Story
bank. Then a check lists any claim the sources don't support, and a
stronger model edits every answer of the Application at once (WorkIt's
writing.check and writing.edit kinds, whose prompts are on its server:
backend/app/apply_prompts/writing.py, D5):
it cuts any sentence the sources don't support, fixes the writing, and keeps
their voice. Banned words live here in code (TELLS), not in the drafting prompt,
since naming a word to a model primes it: an answer still holding one, or a
run of their own words copied from their samples, is edited once more.
"""

import re
from collections.abc import Callable

from apply import home

VOICE = home.HOME / "voice.md"
COPIED = 5  # words in a row from the applicant's samples that count as copying them
LONGEST = 30  # words in a sentence the editor must split
NUMBERS = 2  # numbers an answer may state, years aside (WRITE)
# The Story bank's sections of the applicant's own writing ("## Lisul's own essays"), whatever their name.
OWN = r"^## [^\n]*'s own (?:essays|answers)[^\n]*\n"

WRITE = """How to write every answer, so it reads as @NAME@ typed it themselves. Recruiters read hundreds of applications and readers who know them will see these, so an answer that sounds machine-written loses its value.
<style_card> describes how they write, and their own essays and answers in <story_bank> show it. Copy how @NAME@ writes, not what @NAME@ wrote: @NAME@'s sentence lengths and how much they vary, @NAME@'s plain verbs, how @NAME@ opens, how @NAME@ explains a technical thing (the problem, then what @NAME@ did, with a plain gloss in parentheses), how @NAME@ lays out steps ("then ... and then ..."), and the words they move between ideas with. Where the style card and the samples disagree, follow the samples. Never reuse a run of five or more words from them, and use a habit no more often than @NAME@ does.
Write for a reader outside their team: plain words, "I" plus what they did, at most one technical name per sentence, and nothing below what a recruiter would follow (versions, byte-level details, library and model names, frame rates); their resume has those. One idea per sentence, mostly 12-25 words with a short one now and then, in correct grammar.
Every sentence says something concrete about @NAME@ or this company: a thing @NAME@ built, a problem @NAME@ solved, a specific product of theirs. Describe the work and what came of it and leave the praise to the reader; say plainly what draws them, once, without flattering the company. The reader works there: name their product with a few words on what it does, never a sentence explaining it back to them. A sentence that only asserts ("I care about that problem") or aims at nothing in particular ("own a project end to end", "learn from the team") says nothing; say what they did, or what they want to build there, instead. Claim no lesson, cause or superlative the sources don't state: not "that course is why I could", not "that taught me" unless they say so; only the question's own ranking ("the hardest", "the one I'm proudest of") may be named. Never count commits or pull requests, and state at most two numbers in an answer.
A reader decides in seconds, so the first sentence carries the answer and their strongest fact, in their own words, never the posting's, and never opens on a date or a setting. The reader knows nothing of their projects: the first time one comes up, say in a few plain words what it is and who it was for ("a scheduling tool that a campus food bank used to plan its volunteer shifts"); never name a project, tool or product of theirs the reader hasn't been told about. Say each technical step by what it does, in plain words ("so two shifts that overlapped were never booked to one person"), not by its technical name ("interval overlap check"): a recruiter who isn't an engineer must follow every sentence, and an engineer must still see what they did. Tell finished work in the past tense, as the sources date it. Then show how they think: for the main story, the one decision they made and why, as the sources give it, and end the story on what came of it. When the sources give a result, use it: a placing, a measured speedup, a bug caught, a feature used or demoed. Keep the facts that show scale and judgment too: how many people they led, a check they chose and the reason for it, the tests behind a claim. Say plainly which parts @NAME@ did themselves ("I trained", "I wrote"), and never blur them into what the team or the system did. Keep the details that show how hard it was, their judgment, their scale or a result, and drop tool lists and steps that show none of those. End on a concrete point, never on a wish that would fit any company (to own a project, to ship something people rely on, to learn from a mentor) or a line that sums up.
When the question names a quality or an ask (grit, initiative, ownership, excellence, how they debugged it, why they are proud, what motivates them), the first two sentences answer it in those terms, and the story shows it. Give a technical term a plain gloss of a few words the first time ("the IMU (the sensor that tracks turning)") or say it plainly instead, and never name a teammate or an internal system the reader can't know (a coworker's name, an in-house product or protocol); say what it is. Where the sources give a number for a result, use it rather than a vague word ("much lighter", "fairly consistently"), and never say something was measured or tracked without giving what it showed; when they give none, end on the strongest result they do give. When the story turns on a decision, give their reason and, when the sources say it, what it cost them. End a story on its payoff (the result, or what it let them or the team do), not on a last tuning step. An idea of @NAME@'s for the company's work must be one <company> doesn't say they already ship, and a link to their work only one where the problem is plainly the same kind.
Use a signpost word ("Particularly", "Lastly", "In fact") at most once in an answer, and only where the sentence follows from the one before; never "Hence", which readers flag.
Plain paragraphs: no headings, lists, bold, dashes as punctuation or exclamation marks."""



# Words and shapes that mark text as machine-written (Wikipedia: Signs of AI
# writing; Kobak et al. 2025; Reinhart et al. 2025), and cover letter clichés.
TELLS = re.compile(r"""\b(?:
    delv\w* | tapestr\w* | testament | pivotal | crucial | underscor\w* | showcas\w* | foster\w* | intricat\w*
  | meticulous\w* | robust | vibrant | seamless\w* | leverag\w* | passionate | thrilled | honou?red | groundbreaking
  | cutting[- ]edge | invaluable | embark\w* | journey | realm | landscape | synerg\w* | resonat\w* | dream
  | serves\ as | stands\ as | not\ just | not\ only | align(?:s|ed)?\ with | commitment\ to | perfect\ fit
  | I\ am\ writing\ to | excited\ to\ apply | eager\ to
)\b|—|!""", re.IGNORECASE | re.VERBOSE)

# Time counted from today ("this summer"): the answer is read weeks later (WRITE, EDIT).
RELATIVE_TIME = re.compile(r"\b(?:(?:this|last|next|past)\s+(?:summer|fall|autumn|spring|winter|year|semester)|recently|currently\s+interning)\b", re.IGNORECASE)
# Their signpost words: one an answer reads as theirs; more, or "Particularly," opening
# a sentence where they mean "Specifically", read as a tic to a recruiter.
SIGNPOSTS = re.compile(r"(?:^|(?<=[.!?]\s))(?:Hence|Particularly|Lastly|In fact|Indeed|Essentially|As such|In terms of)\b")
PLACEHOLDER = re.compile(r"\[(?:add|insert|link|url|your|todo|tbd)[^\]]*\]|\b(?:TBD|TODO|XXX)\b", re.IGNORECASE)  # left for them to fill: they add it themselves
HENCE = re.compile(r"\b[Hh]ence\b")  # readers flag it in most answers that use it (research/essay-prompt.md)
# Detail below what a recruiter follows (WRITE: "their resume has those"), and
# talk of the posting itself, which the employer wrote and needn't be told.
LOW_LEVEL = re.compile(r"\b(?:serializ\w*|byte[- ]alignment|bytes?|binary|protobuf|udp|tcp|version\ (?:two|three|\d)|v\d)\b",
                       re.IGNORECASE)
# A course credited with what they did ("that course is why I knew where to look"):
# the Story bank says which courses the applicant liked and why, never what they made possible.
COURSE_CREDIT = re.compile(r"\b(?:course|class|CSE\ ?\d{3}|Fundamentals)\b[^.]*\b(?:helped|taught|why|without|reason|knew|let\ me|prepared)\b"
                           r"|\b(?:helped|taught|without|knew|prepared)\b[^.]*\b(?:course|class|CSE\ ?\d{3}|Fundamentals)\b", re.IGNORECASE)
POSTING_TALK = re.compile(r"\b(?:(?:the|your|this)\ (?:job\ )?(?:posting|listing|job\ description|role|job)|\w+\ also)\ (?:also\ )?"
                          r"(?:asks?\ for|stresses|calls\ for|wants|emphasi[sz]es|requires|mentions|lists)\b", re.IGNORECASE | re.VERBOSE)


def style_card() -> str:
    return VOICE.read_text() if VOICE.is_file() else ""


def samples() -> str:
    """The applicant's own essays and answers, word for word, from the Story bank."""
    own = re.findall(rf"{OWN}(.*?)(?=^## )", home.STORY_BANK.read_text(),
                     re.MULTILINE | re.DOTALL)
    return "\n".join(own).strip()


def tells(text: str) -> tuple[str, ...]:
    """The machine-made words and marks in `text` (TELLS), as it says them."""
    return tuple(dict.fromkeys(m.group() for m in TELLS.finditer(text)))


def copied(text: str, n: int = COPIED) -> tuple[str, ...]:
    """Runs of `n` words in a row that `text` takes from their samples."""
    def runs(words: list[str]) -> set[str]:
        return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}
    words = lambda t: re.findall(r"[a-z0-9']+", t.lower())
    taken = runs(words(text)) & runs(words(samples()))
    return tuple(sorted(taken))


def flags(text: str) -> list[str]:
    """What a check finds in `text` for the editor to fix: tells, runs copied
    from their samples, sentences over LONGEST words, detail below a recruiter,
    talk of the posting, more than NUMBERS numbers, and a course credited
    with something they did."""
    long = [f"a sentence over {LONGEST} words: \"{' '.join(s.split()[:8])} ...\"" for s in _sentences(text)
            if len(s.split()) > LONGEST]
    numbers = [n for n in dict.fromkeys(_numbers(text)) if not re.fullmatch(r"(?:19|20)\d\d", n)]
    many = [f"{len(numbers)} numbers ({', '.join(numbers)}): keep the {NUMBERS} that matter most"] if len(numbers) > NUMBERS else []
    credit = [f"a course credited with what they did: \"{m.group()}\"" for m in COURSE_CREDIT.finditer(text)]
    when = [f"time counted from today: \"{m.group()}\" (say it as the sources date it)" for m in RELATIVE_TIME.finditer(text)]
    signposts = [m.group() for m in SIGNPOSTS.finditer(text)]
    tics = ([f"{len(signposts)} signpost words ({', '.join(signposts)}): keep at most one"] if len(signposts) > 1 else []) \
        + (["\"Particularly,\" opening a sentence: say it plainly"] if "Particularly" in signposts else []) \
        + (["\"Hence\": say it plainly (\"so\") or drop it"] if HENCE.search(text) else []) \
        + [f"a placeholder: \"{m.group()}\" (leave out what only they can give)" for m in PLACEHOLDER.finditer(text)]
    return [*tells(text), *copied(text), *long, *tics, *dict.fromkeys(m.group() for m in LOW_LEVEL.finditer(text)),
            *dict.fromkeys(m.group() for m in POSTING_TALK.finditer(text)), *many, *credit, *when]


def edit(claude, drafts: dict[str, str], sources: str, letters: frozenset[str] = frozenset(),
         questions: dict[str, str] | None = None, lengths: dict[str, str] | None = None,
         checks: Callable[[str, dict[str, str]], list[str]] | None = None) -> dict[str, str]:
    """`drafts` (answer by key) after the claim check and the editor's pass,
    given the drafting call's `sources` (Story bank, Stock answers, Posting,
    Company material). The claim check (CHECK) lists what the sources don't
    support and the editor cuts it (research/essay-prompt.md). There is no
    1-10 reader's review: it raised unsupported claims from 8 to 13, and a
    model revising its own answer with no outside signal gets worse
    (research/sources/answer-types/g-quality.md); every pass here is
    triggered by a check. An answer a scripted check still flags
    (flags) is edited again, at most twice. An edit that isn't usable (empty,
    holding a number the draft didn't, or for a key in `letters` not
    the same letter) is dropped, and the answer stays as the last usable pass
    left it. `lengths` gives, by key, the length an answer keeps to when its
    question states none (its Question type's default, "70-120 words").
    `checks(key, answers)`, when given, adds its own flags for the answer
    under `key`, given every answer as the last pass left them (apply.sameness)."""
    asked = questions or {}
    base = dict(drafts)
    edited = dict(base)

    def take(given: dict[str, str]) -> None:  # each pass's edit, where usable; else the last usable one stays
        edited.update({key: text for key, text in given.items() if _usable(base[key], text, key in letters)})
    take(_pass(claude, base, sources, _check(claude, base, sources), asked, lengths))
    for _ in range(2):
        flagged = {key: found for key, text in edited.items()
                   if (found := [*flags(text), *(checks(key, dict(edited)) if checks else [])])}
        if not flagged:
            break
        take(_pass(claude, {key: edited[key] for key in flagged}, sources, flagged, asked, lengths))
    return edited


def repair(claude, drafts: dict[str, str], sources: str, flagged: dict[str, list[str]],
           letters: frozenset[str] = frozenset(), questions: dict[str, str] | None = None,
           lengths: dict[str, str] | None = None) -> dict[str, str]:
    """One editor's pass over `drafts` to fix what `flagged` lists for each
    (a gate or a checklist item it fails, apply.essays); an edit that isn't
    usable leaves its draft as it was."""
    given = _pass(claude, drafts, sources, flagged, questions, lengths)
    return {key: text if _usable(drafts[key], text, key in letters) else drafts[key] for key, text in given.items()}


def _pass(claude, drafts: dict[str, str], sources: str, flagged: dict[str, list[str]],
          questions: dict[str, str] | None = None, lengths: dict[str, str] | None = None) -> dict[str, str]:
    """One editor's pass: WorkIt's writing.edit kind (D5, KAN-723; its prompt is
    backend/app/apply_prompts/writing.py's EDIT)."""
    data = {"drafts": drafts, "sources": sources, "style_card": style_card(), "flagged": flagged,
            "questions": {key: questions[key] for key in drafts if questions and key in questions},
            "lengths": {key: lengths[key] for key in drafts if lengths and key in lengths}}
    given = claude.ask_kind("writing.edit", data).get("edited") or {}
    return {key: str(given.get(key) or "").strip() for key in drafts}


def _check(claude, drafts: dict[str, str], sources: str) -> dict[str, list[str]]:
    """Claims in each of `drafts` its sources don't support, for the editor to cut: WorkIt's
    writing.check kind (its prompt is backend/app/apply_prompts/writing.py's CHECK)."""
    if not drafts:
        return {}
    given = claude.ask_kind("writing.check", {"drafts": drafts, "sources": sources}).get("unsupported") or {}
    return {key: [f"a claim the sources don't support: {claim}" for claim in found]
            for key in drafts if (found := [str(c) for c in given.get(key) or [] if str(c).strip()])}


def _usable(draft: str, edited: str, letter: bool) -> bool:
    if not edited or not set(_numbers(edited)) <= set(_numbers(draft)):
        return False
    lines = draft.splitlines()
    return not letter or (edited.startswith(lines[0]) and edited.endswith("\n".join(lines[-2:])))


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]


def _numbers(text: str) -> list[str]:
    return re.findall(r"\d+(?:[.,]\d+)*", text)
