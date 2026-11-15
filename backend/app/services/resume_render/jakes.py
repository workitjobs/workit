'''
Jake's Resume body from a built resume view: the LaTeX after
\\begin{document}, written with the template's own commands. Every string
from the view or the identity goes through escape(), and a link target
through escape_url().

With `marks` (the default) each bullet, entry field and skill is wrapped in
position markers (`MARKS` in __init__), which give the editor its click
targets and leave the page itself unchanged. With `printed`, each marked
line's plain text goes in it under the marker's name ("<id>.<kind>"), so a
box carries the words it covers (`Box.text`).
'''

from collections.abc import Sequence

from app.services.resume_render import (
    DEFAULT_PAGE,
    HEADER,
    MARKS,
    HeaderIdentity,
    PageSettings,
    escape,
    escape_url,
    mark,
    printed_order,
    type_size,
)
from app.services.resume_render.fields import (
    SECTION_LABELS,
    SKILLS_LABEL,
    TWO_ROW,
    US_CITIZEN,
    degree_leads,
    details,
    heading,
    heading_fields,
    link_text,
    one_row,
    phone_text,
    skill_lines,
)
from app.services.resume_view import ResumeView, ViewEntry, ViewSection, runs

Printed = dict[str, str] | None


def _rich(text: str) -> str:
    '''A marked wording's LaTeX, each run escaped and set in its weight.'''
    pieces = []
    for words, bold, italic in runs(text):
        latex = escape(words)
        if italic:
            latex = rf"\textit{{{latex}}}"
        pieces.append(rf"\textbf{{{latex}}}" if bold else latex)
    return "".join(pieces)


def _marked(item_id, kind: str, latex: str, text: str, marks: bool, printed: Printed) -> str:
    '''`latex` between markers, and `text`, the same words unescaped, noted
    for its box.'''
    if printed is not None and text:
        printed[f"{item_id}.{kind}"] = text
    return mark(item_id, kind, latex) if marks else latex


def _header(identity: HeaderIdentity, marks: bool, printed: Printed, page: PageSettings) -> list[str]:
    # The identity comes from the profile; its markers use HEADER as the id,
    # and each field's profile column as the kind
    def slot(kind: str, latex: str, text: str) -> str:
        return _marked(HEADER, kind, latex, text, marks, printed)

    # "U.S. Citizen" leads the line. No box: the editor types only the
    # fields it can save, and this one is Application Questions' answer
    contact = [US_CITIZEN] if identity.us_citizen else []
    if identity.phone:
        phone = phone_text(identity.phone)
        contact.append(slot("phone_number", escape(phone), phone))
    if identity.email:
        email = escape(identity.email)
        contact.append(slot(
            "email", rf"\href{{mailto:{escape_url(identity.email)}}}{{\underline{{{email}}}}}", identity.email
        ))
    if identity.location:
        contact.append(slot("location", escape(identity.location), identity.location))
    contact += [
        slot(field, rf"\href{{{escape_url(u)}}}{{\underline{{{escape(link_text(u))}}}}}", link_text(u))
        for field, u in identity.links
    ]
    # The page's settings, each only when it differs, so Jake's own page
    # writes his own header
    size = type_size(page.name_size) if page.name_size else r"\Huge"
    shape = rf"\textbf{{{size} \scshape {escape(identity.name)}}}"
    if page.accent != DEFAULT_PAGE.accent:
        shape = rf"\textcolor{{wiaccent}}{{{shape}}}"
    name = slot("full_name", shape, identity.name)
    box = {"left": "flushleft", "center": "center", "right": "flushright"}[page.header_alignment]
    lines = [rf"\begin{{{box}}}", rf"{name} \\ \vspace{{1pt}}"]
    if contact:
        lines.append(r"\small " + " $|$ ".join(contact))
    # The Additional line, under the contact line in its type: the
    # student's own words, never cut by Fit to One Page
    if identity.extra:
        extra = slot("resume_header_extra", escape(identity.extra), identity.extra)
        if contact:
            lines[-1] += r" \\"
        lines.append(r"\small " + extra)
    lines.append(rf"\end{{{box}}}")
    return lines


# A heading's left side wraps only when it is wider than its row leaves
# (KAN-807). Jake's \resumeSubheading and \resumeProjectHeading set it in an
# `l` column, which never breaks, so a long title or organization ran under
# the dates and off the page. \wifit{right}{right two}{left}{left two} sets
# \wiw to the room the wider right side leaves and \ifwiwrap to whether a
# left side is wider than that. A heading that fits keeps Jake's own table,
# so no page that fits moves (a wrapping column for every heading set
# headings with nothing between them up to 13 pt closer); one that does not
# puts each left side in a \parbox of \wiw, which wraps under itself.
_FIT_LINES = (
    # Dimens, never \newlength's glue: a glue assignment looks ahead for
    # "plus", which ran the next \ifdim before the value was set
    r"\newdimen\wiw\newdimen\wiwr\newsavebox\wiboxa\newsavebox\wiboxb\newif\ifwiwrap",
    (
        r"\newcommand\wifit[4]{\settowidth\wiw{#1}\settowidth\wiwr{#2}\ifdim\wiw<\wiwr\wiw=\wiwr\fi"
        r"\wiw=\dimexpr0.97\textwidth-\wiw-4\tabcolsep\relax"
        r"\sbox\wiboxa{#3}\sbox\wiboxb{#4}\wiwrapfalse\ifdim\wd\wiboxa>\wiw\wiwraptrue\fi"
        r"\ifdim\wd\wiboxb>\wiw\wiwraptrue\fi"
        # A wrapped left side keeps 1em from the right one (Jake's
        # \tabcolsep is 0), and at least 0.4 of the line
        r"\advance\wiw-1em\relax\ifdim\wiw<0.4\textwidth\wiw=0.4\textwidth\fi}"
    ),
)
FIT = "\n".join(_FIT_LINES)


def _fitted(measure: tuple[str, str, str, str], item: str, rows: Sequence[tuple[str, str]], jakes: str) -> str:
    """Jake's heading (`jakes`) when its left sides fit beside its right
    ones, else the same table with each left side wrapped in \\wiw (`FIT`).
    `rows` are (left, right) cells; `measure` is \\wifit's four arguments, the
    cells as each is set."""
    wrapped = (
        item,
        r"\begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}",
        *(rf"\parbox[t]{{\wiw}}{{\raggedright {left}}} & {right} \\" for left, right in rows),
        r"\end{tabular*}\vspace{-7pt}",
    )
    # The % ends the line with no space: the line's end, read as a space,
    # set the next of two one-row headings 13.5 pt lower
    return "\n".join((r"\wifit" + "".join(f"{{{m}}}" for m in measure) + "%", r"\ifwiwrap", *wrapped,
                      r"\else", jakes, r"\fi"))


def _entry(entry: ViewEntry, marks: bool, printed: Printed, page: PageSettings) -> list[str]:
    h = heading(entry, page.date_format, page.education_first)
    kinds = heading_fields(entry.section, degree_leads(entry, page.education_first))

    def slot(name: str) -> str:
        text = getattr(h, name)
        latex = escape(text)
        # A project's link is clickable, as the header's are
        if name == "tag" and entry.link and entry.section not in TWO_ROW and entry.section != "certifications":
            shown = link_text(entry.link)
            org = escape(entry.organization) + r" $|$ " if entry.organization else ""
            latex = org + rf"\href{{{escape_url(entry.link)}}}{{\underline{{{escape(shown)}}}}}"
        return _marked(entry.id, kinds[name], latex, text, marks, printed)

    if entry.section in TWO_ROW and (rights := one_row(h, kinds)) is not None:
        # One row (KAN-503): \resumeSubheading's first row and nothing under
        # it. Each value keeps its own look from the two rows (the second
        # row's italic \small), so the editor's field over it still matches.
        # Written out here, since jakes.tex stays byte for byte.
        styled = {
            "right": lambda: slot("right"),
            "subright": lambda: rf"\textit{{\small {slot('subright')}}}",
        }
        right = " $|$ ".join(styled[name]() for name in rights)
        title = rf"\textbf{{{slot('title')}}}"
        line = _fitted((right, "", title, ""), r"\vspace{-2pt}\item", [(title, right)], "\n".join((
            r"\vspace{-2pt}\item",
            r"\begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}",
            rf"{title} & {right} \\",
            r"\end{tabular*}\vspace{-7pt}",
        )))
    elif entry.section in TWO_ROW:
        title, right, subtitle, subright = (slot(name) for name in ("title", "right", "subtitle", "subright"))
        rows = [(rf"\textbf{{{title}}}", right), (rf"\textit{{\small {subtitle}}}", rf"\textit{{\small {subright}}}")]
        line = _fitted(
            (right, rows[1][1], rows[0][0], rows[1][0]), r"\vspace{-2pt}\item", rows,
            rf"\resumeSubheading{{{title}}}{{{right}}}{{{subtitle}}}{{{subright}}}",
        )
    else:
        left = rf"\textbf{{{slot('title')}}}" + (rf" $|$ \emph{{{slot('tag')}}}" if h.tag else "")
        if h.subtitle:
            # A project's tools on a line of their own (KAN-738): Jake's
            # \resumeProjectHeading with a second row in the italic of
            # \resumeSubheading's. Written out here, since jakes.tex stays
            # byte for byte and has no two-row project heading.
            right, subtitle = slot("right"), rf"\textit{{\small {slot('subtitle')}}}"
            line = _fitted((right, "", rf"\small {left}", subtitle), r"\item", [(rf"\small {left}", right), (subtitle, "")],
                           "\n".join((
                               r"\item",
                               r"\begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}",
                               rf"\small{left} & {right} \\",
                               rf"{subtitle} & \\",
                               r"\end{tabular*}\vspace{-7pt}",
                           )))
        else:
            right = slot("right")
            line = _fitted((right, "", rf"\small {left}", ""), r"\item", [(rf"\small {left}", right)],
                           rf"\resumeProjectHeading{{{left}}}{{{right}}}")
    items = [(entry.id, kind, escape(text), text) for kind, text in details(entry)]
    # A marked bullet's box carries its markers: the editor opens the line on
    # them, and saves it only when they change
    items += [(b.id, "bullet", _rich(b.marked) if b.marked else escape(b.text), b.marked or b.text)
              for b in entry.bullets]
    if not items:
        # An empty itemize is a LaTeX error, so a list opens only around items
        return [line]
    rows = []
    for item_id, kind, latex, text in items:
        body = _marked(item_id, kind, latex, text, marks, printed)
        # \ignorespaces swallows the space Jake's \resumeItem puts after its
        # argument ("{#1 \vspace{-2pt}}"): when a bullet's last line is
        # full, TeX broke at that space and printed an empty line after it
        rows.append(rf"\resumeItem{{{body}\ignorespaces}}")
    return [line, r"\resumeItemListStart", *rows, r"\resumeItemListEnd"]


def _lines(section: ViewSection, marks: bool, printed: Printed) -> list[str]:
    '''A Lines section (KAN-498): its entries' bullets as plain lines, with
    no heading and no dot, in the list the skills sit in. Each line is a
    bullet to the editor (its box), so it types, moves and hides as one.
    Empty when it has no line: an empty itemize is a LaTeX error.'''
    rows = []
    for entry in section.entries:
        for b in entry.bullets:
            latex = _rich(b.marked) if b.marked else escape(b.text)
            body = _marked(b.id, "bullet", latex, b.marked or b.text, marks, printed)
            # \ignorespaces as in _entry: Jake's \resumeItem leaves a space
            rows.append(rf"\resumeItem{{{body}\ignorespaces}}")
    if not rows:
        return []
    return [r"\begin{itemize}[leftmargin=0.15in, label={}]", *rows, r"\end{itemize}"]


def _skills(view: ResumeView, marks: bool, printed: Printed) -> str:
    rows = []
    # Each line's start, before its label: Fit to One Page reads the left
    # edge from it to tell how many skills a wrapped line must lose
    start = r"\wipoint{skillrow}" if marks else ""
    for label, skills in skill_lines(view.skills):
        # Each skill's comma stays inside its markers: a marker between two
        # characters drops the kerning between them ("NumPy," moved 0.08 pt)
        names = " ".join(
            _marked(s.id, "skill", escape(s.name) + comma, s.name + comma, marks, printed)
            for i, s in enumerate(skills)
            for comma in ["," if i < len(skills) - 1 else ""]
        )
        rows.append(start + (rf"\textbf{{{escape(label)}}}{{: {names}}}" if label else names))
    return r" \\ ".join(rows)


def body(
    view: ResumeView, identity: HeaderIdentity, *, marks: bool = True, printed: Printed = None,
    page: PageSettings = DEFAULT_PAGE,
) -> str:
    lines = [MARKS, FIT] if marks else [FIT]
    lines += _header(identity, marks, printed, page)
    blocks: dict[str, list[str]] = {}
    for section in view.sections:
        # A custom section (KAN-498) prints its own name
        title = rf"\section{{{escape(section.label or SECTION_LABELS[section.section])}}}"
        if section.layout == "lines":
            if rows := _lines(section, marks, printed):
                blocks[section.section] = [title, *rows]
            continue
        block = [title, r"\resumeSubHeadingListStart"]
        for entry in section.entries:
            block += _entry(entry, marks, printed, page)
        blocks[section.section] = [*block, r"\resumeSubHeadingListEnd"]
    if view.skills:
        blocks["skills"] = [
            rf"\section{{{SKILLS_LABEL}}}",
            r"\begin{itemize}[leftmargin=0.15in, label={}]",
            rf"\small{{\item{{{_skills(view, marks, printed)}}}}}",
            r"\end{itemize}",
        ]
    for name in printed_order(page.section_order, view.sections):
        lines += blocks.get(name, [])
    return "\n".join(lines)
