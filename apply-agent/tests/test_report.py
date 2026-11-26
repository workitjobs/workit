"""Send report (D26, KAN-837, apply.report): what the window's support form sends. An Application's report holds only
its Record's own files and its Trace with the student's private values masked, a long Trace keeps its start and its
end, a log is never sent without the profile to mask it with, and a general question, or one that leaves the
record out, holds only the student's words."""

import base64
import json
import shutil

import pytest
from conftest import FIXTURES

from apply import report
from apply.model import Status
from apply.tracker import Row

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


def _row(record: str) -> Row:
    return Row(application_id="harvey-123", company="Harvey", role="Software Engineer Intern",
               posting_url="https://jobs.ashbyhq.com/harvey/123", job_system="ashby", status=Status.HELD, record=record)


def test_an_applications_report_holds_its_records_files_and_its_trace_with_private_values_masked(tmp_path):
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
    profile = _profile(tmp_path)

    sent = report.build("answer", " The essay box stayed empty. ", profile, _row(str(record)), contact_ok=True,
                        traces=traces.parent)

    assert (sent["category"], sent["note"], sent["contact_ok"], sent["outcome"]) == (
        "answer", "The essay box stayed empty.", True, "held")
    assert set(sent["files"]) == {"answers.json"} and sent["screenshots"] == {"form.png": base64.b64encode(PNG).decode()}
    assert "harvey/123" in sent["trace"]  # the start says which posting
    for value in ("Person", "test.person@example.com"):
        assert value not in sent["trace"]
    assert [line.split(" (")[0] for line in report.parts(sent)] == [
        "Your words, and WorkIt may email you about them", "Which application: Harvey, Software Engineer Intern",
        "answers.json", "form.png", "The step-by-step log"]


def _profile(tmp_path):
    profile = tmp_path / "applicant-profile.yaml"
    shutil.copy(FIXTURES / "profile.yaml", profile)
    return profile


def test_a_long_trace_keeps_its_start_and_its_end(tmp_path, monkeypatch):
    traces = tmp_path / "traces" / "2026-11-15"
    traces.mkdir(parents=True)
    events = [{"t": 0, "kind": "start", "posting": "harvey-123"}, *({"t": n, "kind": "nav"} for n in range(1, 500)),
              {"t": 999, "kind": "error", "error": "the submit never came back"}]
    (traces / "harvey-123.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    monkeypatch.setattr(report, "TRACE_MAX", 2_000)

    sent = report.build("form", "It hung.", _profile(tmp_path), _row(""), traces=traces.parent)["trace"]

    assert len(sent) <= 2_000 and sent.startswith('{"t": 0, "kind": "start"') and "the submit never came back" in sent


def test_a_log_never_goes_without_the_profile_to_mask_it(tmp_path):
    # The fault: Known.learn reads a folder as no values, so `profile.folder` in place of the file sent the
    # student's name in the log.
    traces = tmp_path / "traces" / "2026-11-15"
    traces.mkdir(parents=True)
    (traces / "harvey-123.jsonl").write_text('{"t": 1, "kind": "console", "text": "saved Test Person"}\n')
    profile = _profile(tmp_path)

    with pytest.raises(ValueError, match="not a file"):
        report.build("form", "It hung.", profile.parent, _row(""), traces=traces.parent)
    assert "Person" not in report.build("form", "It hung.", profile, _row(""), traces=traces.parent)["trace"]


def test_a_general_question_and_a_report_without_the_record_hold_only_the_students_words(tmp_path):
    asked = report.build("app", "How do I change my Worker count?", tmp_path / "no-profile.yaml")
    assert asked == {"category": "app", "note": "How do I change my Worker count?", "contact_ok": False}
    left_out = report.build("form", "It hung.", tmp_path / "no-profile.yaml", _row(str(tmp_path)), include=False)
    assert left_out["application_id"] == "harvey-123" and not {"files", "screenshots", "trace"} & set(left_out)
