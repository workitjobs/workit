"""Send report (D26, KAN-837, apply.report): what one Application's report holds. Only the Record's own files go,
the Trace goes with the student's private values masked, and a long Trace keeps its start and its end."""

import base64
import json
import shutil

from conftest import FIXTURES

from apply import report
from apply.model import Status
from apply.tracker import Row

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


def _row(record: str) -> Row:
    return Row(application_id="harvey-123", company="Harvey", role="Software Engineer Intern",
               posting_url="https://jobs.ashbyhq.com/harvey/123", job_system="ashby", status=Status.HELD, record=record)


def test_a_report_holds_the_records_files_and_the_trace_with_private_values_masked(tmp_path):
    record = tmp_path / "rehearsals" / "2026-11-15" / "harvey-123"
    record.mkdir(parents=True)
    (record / "answers.json").write_text('[{"question": "First Name", "planned": "Test", "on_page": "Test"}]')
    (record / "form.png").write_bytes(PNG)
    (record / "README.md").write_text("# Harvey")  # the answers again, for GitHub: not sent
    traces = tmp_path / "traces" / "2026-11-15"
    traces.mkdir(parents=True)
    (traces / "harvey-123.jsonl").write_text("\n".join(json.dumps(e) for e in (
        {"t": 0, "kind": "start", "posting": "https://jobs.ashbyhq.com/harvey/123"},
        {"t": 4, "kind": "request", "body": "first=Test&last=Person&email=test.person@example.com"},
    )) + "\n")
    profile = tmp_path / "applicant-profile.yaml"
    shutil.copy(FIXTURES / "profile.yaml", profile)

    sent = report.build(_row(str(record)), profile, " The essay box stayed empty. ", traces.parent)

    assert set(sent["files"]) == {"answers.json"} and sent["screenshots"] == {"form.png": base64.b64encode(PNG).decode()}
    assert (sent["outcome"], sent["note"]) == ("held", "The essay box stayed empty.")
    assert "harvey/123" in sent["trace"]  # the start says which posting
    for value in ("Person", "test.person@example.com"):
        assert value not in sent["trace"]


def test_a_long_trace_keeps_its_start_and_its_end(tmp_path, monkeypatch):
    traces = tmp_path / "traces" / "2026-11-15"
    traces.mkdir(parents=True)
    events = [{"t": 0, "kind": "start", "posting": "harvey-123"}, *({"t": n, "kind": "nav"} for n in range(1, 500)),
              {"t": 999, "kind": "error", "error": "the submit never came back"}]
    (traces / "harvey-123.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    monkeypatch.setattr(report, "TRACE_MAX", 2_000)

    sent = report.build(_row(""), tmp_path / "no-profile.yaml", traces=traces.parent)["trace"]

    assert len(sent) <= 2_000 and sent.startswith('{"t": 0, "kind": "start"') and "the submit never came back" in sent
