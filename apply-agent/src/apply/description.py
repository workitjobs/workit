"""The Posting description: the Posting's own text (its role, company, the job
text and its pay range), read once per Application and given to every Claude
call for it in one <posting> block, so a company-specific question is answered
and checked against the job itself.

The text loses its boilerplate (equal-opportunity, benefits, accommodation,
privacy and fraud-warning paragraphs) and is cut to CAP characters, about a
thousand tokens; its pay range is named apart first, so the cut never loses it.
It is employer text: Claude reads it as data and never follows instructions in it."""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass

from apply import company
from apply.adapters import JobSite
from apply.company import text_of
from apply.model import Posting, Question, one_line

CAP = 4_000  # characters of the Posting's text in each call, about 1,000 tokens

# A paragraph no answer draws on, wherever it stands.
BOILERPLATE = re.compile(
    r"equal (employment )?opportunity|affirmative action|do(es)? not discriminate|without regard to"
    r"|regardless of (race|age|background|sex|gender)|protected (veteran|characteristic|status)"
    r"|accommodations?\b.{0,80}\b(disabilit|hiring|application|interview)|disabilit\w*.{0,80}\baccommodation"
    r"|e-verify|privacy (notice|policy)|applicant privacy|phishing|fraudulent|scam|#LI-",
    re.IGNORECASE,
)
# A heading whose section is boilerplate: skipped up to the next heading of the job itself.
BOILERPLATE_HEADING = re.compile(
    r"^(our )?(benefits|perks)\b|what we offer|what you can expect from us|accommodations?\b|accessibility"
    r"|(data )?privacy|fraud|recruit\w* scams?|equal (employment )?opportunity|\beeo|\beoe\b|commitment to",
    re.IGNORECASE,
)
JOB_HEADING = re.compile(
    r"about|the role|responsibilit|what you('ll| will)? (do|work on|build)|qualifications|requirements|who you are"
    r"|you('ll| will)? (have|bring|need)|skills|experience|the team|our (values|mission)|location|schedule|duration",
    re.IGNORECASE,
)
HEADING_WORDS = 8
# An amount of money, and words that make a line about this role's pay.
MONEY = re.compile(r"\$\s?\d|\b\d[\d,.]*\s?(USD|usd)\b")
PAY_WORDS = re.compile(r"\b(pay|salary|compensation|wage|stipend|hourly|per hour|an hour|/\s?h(ou)?r|annual|base)\b",
                       re.IGNORECASE)
PAY_CHARS = 200
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
SECTION_CHARS = 200  # a shorter "description" element is a caption, not the job's text

# What an open posting page says about its job, read with no Claude call: its
# JobPosting schema (application/ld+json), else its visible job description
# section, else its meta description.
PAGE = """() => {
  const postings = [];
  const visit = (node) => {
    if (!node || typeof node !== 'object') return;
    if (Array.isArray(node)) return node.forEach(visit);
    const type = [].concat(node['@type'] || []);
    if (type.includes('JobPosting')) postings.push(node);
    if (node['@graph']) visit(node['@graph']);
  };
  for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
    try { visit(JSON.parse(script.textContent)); } catch (e) {}
  }
  const posting = postings.find((p) => p.description) || {};
  const sections = [...document.querySelectorAll(
    '[data-automation-id="jobPostingDescription"], [itemprop="description"], [class*="description" i], ' +
    '[id*="description" i], [class*="job-details" i], [id*="job-details" i], article')]
    .filter((el) => el.offsetParent !== null && !el.querySelector('input, select, textarea'))
    .map((el) => el.innerText.trim());
  const meta = document.querySelector('meta[name="description"], meta[property="og:description"]');
  const org = posting.hiringOrganization;
  return {
    schema: posting.description || '',
    title: typeof posting.title === 'string' ? posting.title : '',
    company: org && typeof org === 'object' ? org.name || '' : typeof org === 'string' ? org : '',
    salary: posting.baseSalary || null,
    section: sections.sort((a, b) => b.length - a.length)[0] || '',
    meta: meta ? meta.content || '' : '',
    page_title: document.title || '',
  };
}"""


def from_api(posting: Posting, site: JobSite) -> str:
    """The Posting's text from its job system's API (company.description), or
    "" for a job system with none or a text that can't be read."""
    try:
        return company.description(posting, site)
    except Exception:
        return ""


def from_link(posting: Posting, site: JobSite) -> str:
    """The Posting's own page, read with a plain fetch (no browser), or "":
    for a job system with no API whose Filler read no page."""
    try:
        return text_of(site.fetch(posting.url).decode(errors="replace"))
    except Exception:
        return ""


def block(posting: Posting, text: str, questions: Sequence[Question] = ()) -> str:
    """The <posting> block for every Claude call of one Application: the
    company, the role, its pay range if the text states one, and the text.
    Each of `questions` that the text lists prompts for (asked) gets that
    section first, in an <asked_in_description> block the cut never reaches."""
    text = _safe(text)
    head = {"company": posting.company, "role": posting.title} | ({"pay": pay} if (pay := pay_range(text)) else {})
    body = _cut(_without_boilerplate(text))
    listed = [f'<asked_in_description>\nFor the question "{_quoted(q.label)}":\n{found.text}\n</asked_in_description>'
              for q in questions if (found := asked(text, q))]
    return "\n".join(["<posting>", json.dumps(head, ensure_ascii=False), *listed,
                      *([f"<description>\n{body}\n</description>"] if body else []), "</posting>"])


# --- Prompts the Posting lists for an application question ---------------------
# OpenSesame's form asked for "a shareable YouTube link to your Creative Project submission ... Your project should
# answer the Creative Project questions listed in the job description" (2026-11-26). The questions were past the
# block's cut, so the essay writer never saw them. A question that points at the Posting's text gets that section.

# A question that points at instructions in the Posting's own text.
POINTS_AT = re.compile(r"\b(?:job|role|position)\s+(?:description|posting|listing|post|ad)\b|\b(?:the|this)\s+(?:posting|listing)\b"
                       r"|\b(?:questions?|prompts?|topics?)\s+(?:listed|given|outlined|described|above|below)\b",
                       re.IGNORECASE)
# A line that leads into a list of prompts for the applicant ("In your video, please cover:").
LEADS_IN = re.compile(r"\b(?:cover|answer|address|include|respond\s+to|tell\s+us|share|discuss|questions?|prompts?|topics?)\b"
                      r"[^:]{0,60}:$", re.IGNORECASE)
# One prompt of that list: a question, or an ask ("Show us something you've built with AI").
PROMPT = re.compile(r"\?|^(?:show|tell|share|describe|explain|walk|give|talk|list|demonstrate|include)\b", re.IGNORECASE)
# Words too common to tie a question to a section by.
COMMON = frozenset({"about", "above", "after", "also", "answer", "answers", "application", "applications", "apply",
                    "applying", "before", "below", "cover", "description", "every", "include", "including", "into",
                    "job", "link", "list", "listed", "more", "must", "other", "please", "posting", "question",
                    "questions", "role", "should", "submission", "submit", "that", "their", "there", "these",
                    "they", "this", "those", "what", "when", "where", "which", "will", "with", "would", "you",
                    "your"})
ASKED_CHARS = 1_500  # characters of one section given for a question
TIES = 2  # distinctive words a question shares with a section's heading and lead-in, when it doesn't point at the text


@dataclass(frozen=True)
class Asked:
    """One section of the Posting's text that lists prompts for the applicant to answer."""

    heading: str  # the section's heading, "" when the text gives none
    lead: str  # the line that leads into its prompts ("In your video, please cover:")
    text: str  # the whole section, from its heading to the next one, cut to ASKED_CHARS
    prompts: tuple[str, ...]  # each prompt it lists, in order


def prompt_sections(text: str) -> list[Asked]:
    """Every section of the Posting's text that lists prompts: a line that leads into
    them (LEADS_IN), then one or more prompts (PROMPT), one a line."""
    lines = [line.strip() for line in _safe(text).splitlines() if line.strip()]
    found = []
    for n, line in enumerate(lines):
        if not LEADS_IN.search(line):
            continue
        listed = []
        for prompt in lines[n + 1:]:  # a short prompt with no "?" ("Tell us about yourself") is no heading
            if not PROMPT.search(prompt):
                break
            listed.append(prompt)
        if not listed:
            continue
        start = next((i for i in range(n, -1, -1) if _section_heading(lines[i])), None)
        end = next((i for i in range(n + 1 + len(listed), len(lines)) if _section_heading(lines[i])), len(lines))
        body = "\n".join(lines[(start if start is not None else n):end])
        found.append(Asked(lines[start] if start is not None else "", line, _cut_to(body, ASKED_CHARS), tuple(listed)))
    return found


def asked(text: str, q: Question) -> Asked | None:
    """The section of the Posting's text that lists the prompts `q` asks the applicant to answer, or None. A
    question that points at the text ("the questions listed in the job description") gets the section it shares
    the most words with, if it shares one; any other question only one whose heading and lead-in share TIES
    distinctive words with it ("Creative Project")."""
    sections = prompt_sections(text)
    if not sections:
        return None
    said = f"{q.label}\n{q.description}"
    words = _words(said)
    tie = lambda s: len(words & _words(f"{s.heading} {s.lead}"))
    best = max(sections, key=tie)
    return best if tie(best) >= (1 if POINTS_AT.search(one_line(said)) else TIES) else None


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.casefold()) if w not in COMMON}


def _section_heading(line: str) -> bool:
    """A heading of the Posting's text: short, and no question, ask or sentence."""
    return _is_heading(line) and not line.endswith(("?", ":", "!"))


def _quoted(label: str) -> str:
    label = one_line(label).replace('"', "'")
    return label if len(label) <= 160 else label[:159].rstrip() + "…"


def _cut_to(text: str, cap: int) -> str:
    return text if len(text) <= cap else text[:cap].rsplit("\n", 1)[0].rstrip() + "\n(cut)"


def pay_range(text: str) -> str:
    """The line of the Posting's text that states its pay, with the line that
    leads into it ("The annual base salary range is:"), or ""."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for n, line in enumerate(lines):
        if not MONEY.search(line):
            continue
        if PAY_WORDS.search(line):
            sentence = next(s for s in SENTENCE.split(line) if MONEY.search(s))
            return one_line(sentence if PAY_WORDS.search(sentence) else line)[:PAY_CHARS]
        if n and PAY_WORDS.search(lines[n - 1]) and len(lines[n - 1]) <= PAY_CHARS:
            return one_line(f"{lines[n - 1]} {line}")[:PAY_CHARS]
    return ""


def _without_boilerplate(text: str) -> str:
    kept, skipping = [], False
    for line in (line.strip() for line in text.splitlines()):
        if not line:
            continue
        heading = _is_heading(line)
        if heading and BOILERPLATE_HEADING.search(line):
            skipping = True
            continue
        if skipping and heading and JOB_HEADING.search(line):
            skipping = False
        if skipping or BOILERPLATE.search(line):
            continue
        kept.append(line)
    return "\n".join(kept)


def _is_heading(line: str) -> bool:
    return len(line.split()) <= HEADING_WORDS and not line.endswith((".", ",", ";"))


def _cut(text: str) -> str:
    """`text` cut to CAP characters, at the end of a line where one ends in reach."""
    if len(text) <= CAP:
        return text
    cut = text[:CAP]
    end = cut.rfind("\n")
    return (cut[:end] if end > CAP // 2 else cut).rstrip() + "\n(cut)"


def _safe(text: str) -> str:
    """No angle brackets, so the text can't close the block it sits in."""
    return text.replace("<", "(").replace(">", ")")


def from_page(page) -> str:
    """The Posting's text as its open page shows it: before the Apply click
    the posting itself, after it whatever the form page still says. "" if
    the page says nothing about the job. A JobPosting schema's role and
    company lead it, as a pasted link may name neither."""
    found = page.evaluate(PAGE)
    if found["schema"]:
        pay, role = _salary(found["salary"]), " at ".join(filter(None, [found["title"], found["company"]]))
        return "\n".join(filter(None, [one_line(role), pay and f"Pay: {pay}", text_of(found["schema"])]))
    if len(found["section"]) >= SECTION_CHARS:
        return "\n".join(line.strip() for line in found["section"].splitlines() if line.strip())
    return one_line(found["meta"])


# How a careers page's title names the company and role, when no JobPosting schema does:
# Jobvite's "AArete Careers - Apply for Data Architecture Intern", Paylocity's
# "North Atlantic Industries, Inc - Intern - Full Stack Software Engineer Application".
PAGE_TITLES = [
    re.compile(r"^(?P<company>.+?) careers? - (?:apply for )?(?P<title>.+)$", re.IGNORECASE),
    re.compile(r"^(?P<company>.+?) - (?P<title>.+?) application$", re.IGNORECASE),
    # A form builder's page: "2027 Netflix Internship Application - Airtable"
    re.compile(r"^(?:(?:summer |fall )?\d{4} )?(?P<company>[^-]+?) (?P<title>(?:summer )?internships?(?: program)?) application"
               r"(?: form)?(?: - [^-]+)?$", re.IGNORECASE),
]


def names_on_page(page) -> tuple[str, str]:
    """The company and role the open page names: its JobPosting schema's,
    else its title's; ("", "") if it names neither."""
    found = page.evaluate(PAGE)
    company, title = one_line(found["company"]), one_line(found["title"])
    for shape in PAGE_TITLES:
        if company and title:
            break
        if m := shape.match(one_line(found["page_title"])):
            company, title = company or m["company"].strip(), title or m["title"].strip()
    return company, title


def _salary(salary) -> str:
    """A JobPosting's baseSalary in words: "$28 - $32 USD per hour"."""
    if not isinstance(salary, dict):
        return ""
    value = salary.get("value")
    value = value if isinstance(value, dict) else {"value": value}
    amounts = [value.get(k) for k in ("minValue", "maxValue", "value") if value.get(k) not in (None, "")]
    if not amounts:
        return ""
    unit = str(value.get("unitText") or "").lower()
    currency = str(salary.get("currency") or "")
    shown = " - ".join(f"${a:,}" if isinstance(a, (int, float)) else f"${a}" for a in dict.fromkeys(amounts))
    return " ".join(filter(None, [shown, currency, unit and f"per {unit}"]))
