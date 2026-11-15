"""Send report (D26, KAN-837): one Application's Record and its masked Trace, sent to WorkIt only when the student
presses "Send report" in the window, which calls `send` (the button is W5's). WorkIt keeps the report until the
team fixes the problem it shows, then deletes it (backend routers/apply_reports.py), as the privacy policy says.

What goes, and nothing else from the data folder:
- the Application as its Tracker row names it, and the student's note;
- the Record's own files, as the window shows them: its answers, essays, verification, the questions Lisul asked
  Claude, the page's HTML (each with its secrets already cut out, apply.records) and the form's screenshots;
- the Trace, with Lisul's private values masked here first (masked.Known: the Applicant profile's and Answer
  bank's own values, and every email, phone and id in a link), cut to its start and its last TRACE_MAX
  characters, where a failure shows.

The caps are the server's (backend schemas/apply_reports.py): a part past one is cut or left out here, so a report
is never refused for its size.
"""

import base64
from pathlib import Path

from apply import masked, trace
from apply.tracker import Row

TEXT_FILES = ("answers.json", "essays.md", "verification.json", "asks.json", "page.html")
SCREENSHOTS = ("form.png", "after-submit.png")
TEXT_MAX = 1_000_000  # characters of one text file
TRACE_MAX = 4_000_000  # characters of the Trace
PNG_MAX = 4_000_000  # bytes of one screenshot: a larger one is left out


def build(row: Row, profile: Path, note: str = "", traces: Path | None = None) -> dict:
    """The report for `row`'s Application: `profile` is the Applicant profile the Trace's values are masked from,
    and `traces` the Traces' folder (trace.TRACES by default)."""
    # A Record in a folder (the Student build's); a pushed one's link is a web page, which gives no files.
    record = Path(row.record) if row.record and not row.record.startswith(("http://", "https://")) else None
    files = {name: path.read_text(errors="replace")[:TEXT_MAX] for name in TEXT_FILES if (path := _file(record, name))}
    screenshots = {name: base64.b64encode(png).decode() for name in SCREENSHOTS
                   if (path := _file(record, name)) and 0 < len(png := path.read_bytes()) <= PNG_MAX}
    return {"application_id": row.application_id, "company": row.company[:300], "role": row.role[:300],
            "posting_url": row.posting_url if row.posting_url.startswith(("https://", "http://")) else "",
            "outcome": str(row.status.value)[:40], "note": note.strip()[:2000], "files": files,
            "screenshots": screenshots, "trace": _masked_trace(row.application_id, profile, traces)}


def _file(record: Path | None, name: str) -> Path | None:
    path = record / name if record else None
    return path if path and path.is_file() else None


def _masked_trace(application_id: str, profile: Path, traces: Path | None) -> str:
    path = trace.latest(application_id, traces)
    if path is None:
        return ""
    known = masked.Known()
    known.learn(profile)
    lines = [known.scrub(line) for line in path.read_text(errors="replace").splitlines()]
    text = "".join(f"{line}\n" for line in lines)
    if len(text) <= TRACE_MAX:
        return text
    start = f"{lines[0]}\n" if lines else ""  # the Posting and the Application, which the rest needs
    return start + text[-(TRACE_MAX - len(start)):]


def send(row: Row, profile: Path, note: str = "", client=None) -> str:
    """Send `row`'s report to WorkIt; its id there. Raises apply.workit's errors (signed out, WorkIt down)."""
    from apply.workit import WorkIt

    return (client or WorkIt()).send_report(build(row, profile, note))
