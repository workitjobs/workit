"""What Apply checks and says before it asks Lisul a question.

`known` finds what Apply already holds for a question (the Applicant
profile, the Answer bank, the Story bank, the resume's links), so a question
he has answered somewhere is answered from it and never reaches him. `where`
and `for_essay` give the one context line each question card shows: which
step of the form it is on, the question it follows and its pair, or the essay
it is for."""

import re
from collections.abc import Sequence
from datetime import date
from functools import lru_cache
from pathlib import Path

from apply import home as data_folder
from apply.answer_bank import AnswerBank, key
from apply.model import Question, one_line
from apply.profile import ANSWERED, ApplicantProfile

IN = "In: "  # opens a Missing fact's context line in its Tracker reason ("Missing fact: <q>; In: <context>")
SHORT = 60  # characters of a question quoted in a context line
BARE = 3  # words (a format in brackets aside) a label has at most to say little alone, so the question before it is named

# --- What Apply already knows --------------------------------------------------

# A question that asks for links, and the kinds of link it names.
LINK_ASK = re.compile(r"\b(?:urls?|links?|github|linked\s?in|portfolio|website|repo\w*|source code)\b", re.IGNORECASE)
KINDS = {"github": re.compile(r"github", re.IGNORECASE), "linkedin": re.compile(r"linked\s?in", re.IGNORECASE),
         "site": re.compile(r"portfolio|website|personal site", re.IGNORECASE),
         "repo": re.compile(r"\brepo\w*|source code|project|firmware|demo", re.IGNORECASE)}
# Which known link holds each kind: "github" is a profile, not a repo.
HOLDS = {"github": re.compile(r"github\.com/[^/\s]+/?(?:\s|$)", re.IGNORECASE), "linkedin": re.compile(r"linkedin\.com/", re.IGNORECASE),
         "site": re.compile(r"^(?:Portfolio|Website):", re.IGNORECASE),
         "repo": re.compile(r"(?:github|gitlab|bitbucket)\.(?:com|org)/[^/\s]+/[^/\s)]+", re.IGNORECASE)}
URL = re.compile(r"https?://[^\s)<>\]]+")
# A question for the applicant's graduation date ("which graduation date should the cover letter give?").
# Never "what will you do after you graduate this year?": the date's word comes before "graduate", or right after it.
GRADUATION_ASK = re.compile(r"\bgraduation\s+(?:date|month|year|term|semester)\b"
                            r"|\b(?:when|date|month|year|term|semester)\b[^?]{0,40}\bgraduat", re.IGNORECASE)
# The profile's link fields by their name in a line ("GitHub: https://...").
LINK_NAMES = {"github_url": "GitHub", "linkedin_url": "LinkedIn", "portfolio_url": "Portfolio",
              "google_scholar_url": "Google Scholar", "x_twitter_url": "X", "showcase_project_url": "Project"}
# A question that sends the applicant to take something at a link (a quiz, a test, an assessment, a challenge) and
# give what it returns: only its result answers it, and only the applicant has that. Ramp's "Take this builder's
# quiz: https://awu-ramp.github.io/..." was answered with his GitHub profile, for the "github" in its link (2026-11-26).
TAKE = re.compile(r"\b(?:take|complete|finish|attempt|try)\b.{0,60}?\b(?:quiz(?:zes)?|tests?|assessments?|challenges?"
                  r"|puzzles?|exercises?|surveys?|questionnaires?)\b", re.IGNORECASE)


# A question for a link to something the applicant must make or host first: a video, a recording, a submission, a
# portfolio or a demo. Only a link of theirs answers it, never written text: OpenSesame's "Please include a shareable
# YouTube link to your Creative Project submission" got a written essay in its link box (2026-11-26).
LINK_WORD = re.compile(r"\b(?:urls?|links?|shareable)\b", re.IGNORECASE)
MADE = {"video": re.compile(r"\b(?:youtube|loom|vimeo|videos?|recordings?|screencasts?|screen\s+recordings?)\b", re.IGNORECASE),
        "submission": re.compile(r"\bsubmissions?\b", re.IGNORECASE),
        "portfolio": re.compile(r"\bportfolios?\b", re.IGNORECASE),
        "demo": re.compile(r"\bdemos?\b", re.IGNORECASE)}
# A link to one video (never a channel): YouTube's watch, short and youtu.be links, Loom's share links, Vimeo's.
VIDEO_LINK = re.compile(r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/|loom\.com/(?:share|embed)/|vimeo\.com/\d)",
                        re.IGNORECASE)
HOSTS = {"youtube": "YouTube", "loom": "Loom", "vimeo": "Vimeo"}
# Words too common to tie a link line to the thing a question asks for.
PLAIN = frozenset({"please", "include", "shareable", "link", "links", "your", "video", "videos", "submission", "required",
                   "accessible", "anyone", "with", "should", "will", "that", "this", "from", "into", "applications",
                   "application", "reviewed", "youtube", "loom", "vimeo", "recording", "unlisted", "share", "url"})


def to_make(q: Question | str) -> str:
    """What a link question asks the applicant to make or host first ("video", "submission", "portfolio", "demo"),
    or "" for any other question. Only a text field asks it; a file upload is no link."""
    if not isinstance(q, str) and q.kind not in ("text", "textarea"):
        return ""
    text = one_line(q if isinstance(q, str) else q.label)
    if not LINK_WORD.search(text):
        return ""
    # "Portfolio, Video, or Website Link" takes any of them: a video is one choice, so it is a portfolio's ask.
    others = any(KINDS[kind].search(text) for kind in ("github", "linkedin", "site"))
    return next((kind for kind, named in MADE.items() if named.search(text) and not (kind == "video" and others)), "")


def fits_made(q: Question | str, answer: object) -> bool:
    """Whether `answer` can stand in the link field `q` (to_make): links alone, each one to a single video when
    it asks for a video."""
    if not isinstance(answer, str) or not answer.strip():
        return False
    words = answer.split()
    return all(URL.fullmatch(w) for w in words) and (to_make(q) != "video" or all(VIDEO_LINK.search(w) for w in words))


def _made_links(asked: str, held: Sequence[str]) -> tuple[str, ...]:
    """The links Apply holds that answer a video ask: a link to one video, on a line that names what the
    question asks for ("Creative Project video: https://youtu.be/..."). () for a submission: only Lisul has it."""
    if to_make(asked) != "video":
        return ()
    named = {w for w in re.findall(r"[a-z]{4,}", asked.casefold()) if w not in PLAIN}
    return tuple(line for line in held if VIDEO_LINK.search(line)
                 and named & set(re.findall(r"[a-z]{4,}", URL.sub("", line).casefold())))


def takes_elsewhere(q: Question | str) -> str:
    """The link a question asks the applicant to take a quiz, test, assessment or challenge at, to give its result;
    "" for any other question. The link is in its label or its help text."""
    text = q if isinstance(q, str) else f"{q.label}\n{q.description}"
    return URL.search(text)[0].rstrip(".,;:") if TAKE.search(one_line(text)) and URL.search(text) else ""


def links(profile: ApplicantProfile) -> tuple[str, ...]:
    """Every link of the applicant's Apply holds, one "what: url" line each:
    the profile's `links`, each Story bank line with a URL in it, and each
    link on the resume PDF with the words it is on. A URL two of them give
    is listed once, from the Story bank or the resume, whose words say what it is."""
    own = [f"{LINK_NAMES.get(name, name.removesuffix('_url').replace('_', ' ').title())}: {url}"
           for name, url in (profile.get("links") or {}).items() if isinstance(url, str) and url.strip()]
    bank = data_folder.STORY_BANK.read_text() if data_folder.STORY_BANK.is_file() else ""
    stories = [one_line(line).lstrip("-* ") for line in bank.splitlines() if URL.search(line)]
    pdf = profile.get("files.resume_pdf")
    on_resume = [f"{words} (on the resume): {url}" for words, url in
                 (resume_links(pdf, pdf.stat().st_mtime) if isinstance(pdf, Path) and pdf.is_file() else ())]
    seen, kept = set(), []
    for line in stories + on_resume + own:  # one line a URL: the one that says what it is, when two give it
        urls = {re.sub(r"^https?://(?:www\.)?", "", url).rstrip("/").casefold() for url in URL.findall(line)}
        if urls - seen:
            kept.append(line)
        seen |= urls
    return tuple(kept)


@lru_cache(maxsize=4)
def resume_links(pdf: Path, mtime: float) -> tuple[tuple[str, str], ...]:
    """(the words a link is on, its URL) of each web link in the PDF; () when it can't be read."""
    from pypdf import PdfReader
    found = []
    try:
        for page in PdfReader(pdf).pages:
            runs = []
            page.extract_text(visitor_text=lambda text, cm, tm, *_: text.strip() and runs.append(
                (tm[4] * cm[0] + cm[4], tm[5] * cm[3] + cm[5], text)))
            for annot in page.get("/Annots") or []:
                annot = annot.get_object()
                url = str((annot.get("/A") or {}).get("/URI") or "")
                if not url.startswith(("http://", "https://")):
                    continue
                x0, y0, x1, y1 = (float(v) for v in annot["/Rect"])
                words = one_line("".join(t for x, y, t in runs if x0 - 2 <= x <= x1 and y0 - 2 <= y <= y1 + 2))
                found.append((words or url, url))
    except Exception:
        return ()
    return tuple(dict.fromkeys(found))


def graduation(profile: ApplicantProfile) -> str:
    """The profile's expected graduation as one line ("Expected graduation: May 2028"); "" when it gives none.
    The profile's date is the one to state: the form's graduation answer comes from it, and a Story bank line
    can be older (Anduril's cover letter, 2026-11-25, waited on a Story bank date the profile had moved)."""
    given = str(profile.get("education.expected_graduation") or "").strip()
    if (m := re.fullmatch(r"(\d{4})-(\d{1,2})(?:-\d{1,2})?", given)) and 1 <= int(m[2]) <= 12:
        return f"Expected graduation: {date(int(m[1]), int(m[2]), 1):%B %Y}"
    return f"Expected graduation: {given}" if given else ""


def known(asked: str, profile: ApplicantProfile, bank: AnswerBank | None = None, employer: str = "") -> tuple[str, ...]:
    """What Apply already holds that answers `asked`, a line a fact; () when
    it holds nothing, and Lisul must be asked. An answer Lisul gave before
    (the profile's answered questions, the Answer bank, a Story bank line
    from an earlier Essay fact) answers the same question. A question for
    the graduation date is answered by the profile's (graduation). A question for
    links is answered by the links Apply holds when each kind it names
    (GitHub, LinkedIn, a site, a repo) is among them: those of its kinds.
    A Story bank line true of one company only is `employer`'s (essays.story_bank)."""
    from apply import essays  # imported here: essays imports this module
    asked = one_line(asked.removeprefix(essays.ASK))
    if not asked:
        return ()
    answered = {key(q): a for q, a in (profile.get(ANSWERED) or {}).items() if a not in (None, "", [])}
    if key(asked) in answered:
        return (_shown(answered[key(asked)]),)
    if bank and (entry := bank.get(asked)) and entry.answer:
        return (_shown(entry.answer),)
    stories = essays.story_bank(employer) if data_folder.STORY_BANK.is_file() else ""
    if line := next((one_line(line)[2:] for line in stories.splitlines()
                     if one_line(line).casefold().startswith(f"- {asked}".casefold())), ""):
        return (line,)
    if GRADUATION_ASK.search(asked) and (graduates := graduation(profile)):
        return (graduates,)
    if not LINK_ASK.search(asked) or takes_elsewhere(asked):  # a quiz's result is no link Apply holds
        return ()
    held = links(profile)
    if to_make(asked) in ("video", "submission"):  # only a link to that very thing, never a profile or a repo
        return _made_links(asked, held)
    kinds = [kind for kind, named in KINDS.items() if named.search(asked)] or ["repo"]
    fit = {kind: [line for line in held if HOLDS[kind].search(line)] for kind in kinds}
    return tuple(dict.fromkeys(line for kind in kinds for line in fit[kind])) if all(fit.values()) else ()


def value(facts: Sequence[str]) -> str:
    """Known facts as a form field's answer: their URLs alone when they are links."""
    urls = [url for line in facts for url in URL.findall(line)]
    return " ".join(dict.fromkeys(urls)) if urls and len(urls) >= len(facts) else "\n".join(facts)


def _shown(answer: object) -> str:
    return ", ".join(map(str, answer)) if isinstance(answer, list) else str(answer)


# --- The context line ------------------------------------------------------------

# Fields that come in pairs, each first word with its partner's ("From" and "To").
PAIRS = {"from": "to", "to": "from", "start": "end", "end": "start", "min": "max", "max": "min",
         "minimum": "maximum", "maximum": "minimum", "first": "last", "last": "first"}


def where(q: Question, questions: Sequence[Question]) -> str:
    """One short line on where `q` sits on its form, from what the Filler
    read: its step (a Workday name is "<step> / <label>"), the question just
    before it on that step when its own label is a bare word or two, and the
    field it pairs with ("From" with "To"). A quiz, test or challenge to take
    at a link (`takes_elsewhere`) leads with that link, and a link to something
    to make first (`to_make`) with what to make.
    "" when there is nothing to say."""
    take = f"Take it yourself at {link}, then paste its result" if (link := takes_elsewhere(q)) else made(q)
    return " · ".join(filter(None, [take, _place(q, questions)]))


def first_line(where: str) -> str:
    """A context line alone, without the lines a Recording brief adds under it (apply.recording): for a one-line
    place such as a Tracker reason."""
    return where.split("\n", 1)[0]


def made(q: Question) -> str:
    """What the applicant does for a link question of `to_make`, as its context line leads with it; "" for any other."""
    kind = to_make(q)
    if kind == "video":
        host = next((name for word, name in HOSTS.items() if word in q.label.casefold()), "")
        return f"Record the video yourself, then paste its {host or 'video'} link"
    return f"Make the {kind} yourself, then paste its link" if kind else ""


def _place(q: Question, questions: Sequence[Question]) -> str:
    step = _step(q)
    same = [other for other in questions if _step(other) == step]
    at = next((i for i, other in enumerate(same) if other.name == q.name), None)
    if at is None:
        return step
    pair = _pair(q, same[at - 1] if at else None) or _pair(q, same[at + 1] if at + 1 < len(same) else None)
    bare = len(re.sub(r"\([^)]*\)", "", q.label).split()) <= BARE  # "From (MM/DD/YYYY)" says little alone
    before = next((other for other in reversed(same[:at]) if other is not pair), None) if bare else None
    return " · ".join(filter(None, [step, before and f"after '{_cut(before.label)}'",
                                    pair and f"paired with {one_line(pair.label)}"]))


def for_essay(essay: Question) -> str:
    """The context line of an Essay fact: the essay it is for, and what Apply does with the answer."""
    return f"For the essay '{_cut(essay.label)}': Claude writes it from your answer, which joins your Story bank"


def _step(q: Question) -> str:
    """The form step a Question is on, when its name says (Workday's "<step> / <label>"); else ""."""
    name, label = re.sub(r" \(\d+\)$", "", q.name), q.label.strip()
    return name[:-len(label)].rstrip(" /") if label and name.endswith(label) and len(name) > len(label) else ""


def _pair(q: Question, other: Question | None) -> Question | None:
    first = lambda text: (re.findall(r"[a-z]+", text.casefold()) or [""])[0]
    return other if other and (partner := PAIRS.get(first(q.label))) and first(other.label) == partner else None


def _cut(text: str) -> str:
    text = one_line(text)
    return text if len(text) <= SHORT else text[:SHORT - 1].rstrip() + "…"
