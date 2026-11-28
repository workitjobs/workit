"""
WorkIt Auto Apply's Story bank (W11), built from what WorkIt holds, in the
layout Apply's essays read (apply-agent/sample/story-bank.md):

1. the student's own writing, word for word: their writing samples, under
   "## <first name>'s own essays" (Apply's writing.samples and the import's
   own_pieces read that heading);
2. one section for each school, job, project or other entry of their
   experience bank, one story for each bullet, newest first; a copy of an
   entry on another resume (its `copy_group`) once;
3. Skills.

Nothing a fill adds: every essay's prompt carries the whole Story bank, so it
holds only what the student keeps on the website. An answer to what an essay
asked is a Needs you answer (fill_profile's answered_questions).

Pure: it takes the student as engine_student assembles them.
"""

import datetime

ORDER = ("experience", "projects", "leadership", "custom", "awards", "certifications")


def story_bank(student: dict, samples: tuple[str, ...]) -> str:
    entries = _once((student.get("bank") or {}).get("entries") or [])
    name = (student.get("full_name") or "").strip()
    first = student.get("first_name") or (name.split(" ")[0] if name else "") or "The applicant"
    parts = [f"# Story bank: {name or first}\n"]
    if samples:
        parts.append(f"## {first}'s own essays\n" + "\n\n".join(s.strip() for s in samples) + "\n")
    if schools := [e for e in entries if e.get("section") == "education"]:
        parts.append("## Education\n" + "".join(f"- {_school(e)}\n" for e in _newest(schools)))
    for section in ORDER:
        for e in _newest([e for e in entries if e.get("section") == section]):
            parts.append(f"## {_heading(e)}\n" + "".join(f"- {b['text'].strip()}\n" for b in _bullets(e)))
    if skills := (student.get("bank") or {}).get("skills") or []:
        groups: dict[str, list[str]] = {}
        for s in skills:
            groups.setdefault(s.get("group") or "", []).append(s["name"])
        parts.append("## Skills\n" + "".join(f"- {g + ': ' if g else ''}{', '.join(n)}.\n" for g, n in groups.items()))
    return "\n".join(parts)


def _once(entries: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for e in entries:
        group = e.get("copy_group") or str(e.get("id") or id(e))
        if group not in seen:
            seen.add(group)
            out.append(e)
    return out


def _newest(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda e: (e.get("end_kind") == "present", e.get("end_month") or "",
                                          e.get("start_month") or ""), reverse=True)


def _bullets(e: dict) -> list[dict]:
    return sorted((b for b in e.get("bullets") or [] if (b.get("text") or "").strip()), key=lambda b: b["position"])


def _month(month: str | None) -> str:
    if not month:
        return ""
    year, number = month.split("-")[:2]
    return f"{datetime.date(int(year), int(number), 1):%b} {year}"


def _dates(e: dict) -> str:
    start = _month(e.get("start_month"))
    end = "present" if e.get("end_kind") == "present" else _month(e.get("end_month") or e.get("award_date"))
    return f"{start}-{end}" if start and end else start or end


def _heading(e: dict) -> str:
    title = e.get("title") or ""
    head = f"{e['organization']}: {title}" if e.get("organization") else title
    about = "; ".join(filter(None, [", ".join(filter(None, [_dates(e), e.get("location"), e.get("issuer")])),
                                    ", ".join(e.get("tools") or [])]))
    return f"{head} ({about})" if about else head


def _school(e: dict) -> str:
    degree = " ".join(filter(None, [e.get("degree"), e.get("field_of_study")]))
    end = _month(e.get("end_month"))
    when = "present" if e.get("end_kind") == "present" else f"expected {end}" if e.get("end_kind") == "expected" else end
    gpa = f" GPA {e['gpa']}" + (f"/{e['gpa_scale']}" if e.get("gpa_scale") else "") + "." if e.get("gpa") else ""
    said = ", ".join(filter(None, [e.get("title"), degree, when])) + "." + gpa
    if e.get("coursework"):
        said += f" Coursework: {', '.join(e['coursework'])}."
    return said + (f" {e['honors'].strip()}" if e.get("honors") else "")
