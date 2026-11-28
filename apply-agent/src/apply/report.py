"""Send report (D26, KAN-837): the support form in the window. The student opens it from Settings ("Report a
problem") or from an Application's tile ("Report this Application", which picks that Application), says what it is
about (CATEGORIES), writes what happened, says whether WorkIt may email them, and, with an Application picked,
whether to include its record and log. The window (W5's) calls `build` with those answers, shows `parts` of what
it built, and on Send calls `send` with that same report, so what goes is exactly what was shown. Nothing is ever
sent without the press. WorkIt keeps a report until the team fixes the problem it shows, then deletes it (backend
routers/apply_reports.py), as the privacy policy says.

What goes, and nothing else from the data folder:
- the category, the student's own words and whether WorkIt may email them (to the account's address);
- with an Application included: the Application as its Tracker row names it; the Record's own files, as the
  window shows them (its answers, essays, verification, the questions Lisul asked Claude and the page's HTML,
  each with its secrets already cut out, apply.records, and the form's screenshots); and the Trace, with Lisul's
  private values masked here first (masked.Known: the Applicant profile's and Answer bank's own values, and every
  email, phone and id in a link), cut to its start and its last TRACE_MAX characters, where a failure shows.

The caps are the server's (backend schemas/apply_reports.py): a part past one is cut or left out here, so a report
is never refused for its size.
"""

import base64
from pathlib import Path

from apply import masked, trace
from apply.tracker import Row

# What a report is about, by the server's key (backend schemas/apply_reports.py, Category), in the form's words.
CATEGORIES = {
    "form": "A form was filled wrong",
    "answer": "An essay or an answer",
    "sign_in": "Signing in, or a job-site account",
    "app": "The app itself",
    "other": "Something else",
}
TEXT_FILES = ("answers.json", "essays.md", "verification.json", "asks.json", "page.html")
SCREENSHOTS = ("form.png", "after-submit.png")
NOTE_MAX = 2_000  # characters of the student's words
TEXT_MAX = 1_000_000  # characters of one text file
TRACE_MAX = 4_000_000  # characters of the Trace
PNG_MAX = 4_000_000  # bytes of one screenshot: a larger one is left out


def build(category: str, note: str, profile: Path, row: Row | None = None, include: bool = True,
          contact_ok: bool = False, traces: Path | None = None) -> dict:
    """The report the form's answers make. `row` is the Application it is about (None for a general question), and
    `include` whether its record and log go with it. `profile` is the Applicant profile's file (home.HOME /
    "applicant-profile.yaml", never its folder) the Trace's values are masked from, and `traces` the Traces' folder
    (trace.TRACES by default). Raises ValueError for a category the server doesn't take, no words, or, when a Trace
    goes, a `profile` that is not a file."""
    if category not in CATEGORIES or not note.strip():
        raise ValueError("a report needs one of CATEGORIES and the student's words")
    report = {"category": category, "note": note.strip()[:NOTE_MAX], "contact_ok": contact_ok}
    if row is None:
        return report
    report |= {"application_id": row.application_id, "company": row.company[:300], "role": row.role[:300],
               "posting_url": row.posting_url if row.posting_url.startswith(("https://", "http://")) else "",
               "outcome": str(row.status.value)[:40]}
    if not include:
        return report
    # A Record in a folder (the Student build's); a pushed one's link is a web page, which gives no files.
    record = Path(row.record) if row.record and not row.record.startswith(("http://", "https://")) else None
    files = {name: path.read_text(errors="replace", encoding="utf-8")[:TEXT_MAX] for name in TEXT_FILES if (path := _file(record, name))}
    screenshots = {name: base64.b64encode(png).decode() for name in SCREENSHOTS
                   if (path := _file(record, name)) and 0 < len(png := path.read_bytes()) <= PNG_MAX}
    return report | {"files": files, "screenshots": screenshots,
                     "trace": _masked_trace(row.application_id, profile, traces)}


def parts(report: dict) -> list[str]:
    """What `report` holds, a line each, for the form to show before Send: "Your words", each file and screenshot
    with its size, and the log."""
    shown = ["Your words" + (", and WorkIt may email you about them" if report.get("contact_ok") else "")]
    if report.get("application_id"):
        shown.append(f"Which application: {report.get('company') or report['application_id']}"
                     + (f", {report['role']}" if report.get("role") else ""))
    shown += [f"{name} ({_size(len(text.encode()))})" for name, text in (report.get("files") or {}).items()]
    shown += [f"{name} ({_size(len(base64.b64decode(png)))})" for name, png in (report.get("screenshots") or {}).items()]
    if report.get("trace"):
        shown.append(f"The step-by-step log ({_size(len(report['trace'].encode()))}), your personal details hidden")
    return shown


def send(report: dict, client=None) -> str:
    """Send a report `build` made to WorkIt; its id there. Raises apply.workit's errors (signed out, WorkIt down,
    CapReached past 10 a day)."""
    from apply.workit import WorkIt

    return (client or WorkIt()).send_report(report)


def _size(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB" if n >= 1_000_000 else f"{max(1, round(n / 1_000))} KB"


def _file(record: Path | None, name: str) -> Path | None:
    path = record / name if record else None
    return path if path and path.is_file() else None


def _masked_trace(application_id: str, profile: Path, traces: Path | None) -> str:
    path = trace.latest(application_id, traces)
    if path is None:
        return ""
    # Known.learn reads a file it can't as no values, which would send the name and street in the log unmasked:
    # a folder (the profile's `folder`) passed in place of the file did.
    if not profile.is_file():
        raise ValueError(f"no Applicant profile to mask the log with: {profile.name} is not a file")
    known = masked.Known()
    known.learn(profile)
    lines = [known.scrub(line) for line in path.read_text(errors="replace", encoding="utf-8").splitlines()]
    text = "".join(f"{line}\n" for line in lines)
    if len(text) <= TRACE_MAX:
        return text
    start = f"{lines[0]}\n" if lines else ""  # the Posting and the Application, which the rest needs
    return start + text[-(TRACE_MAX - len(start)):]
