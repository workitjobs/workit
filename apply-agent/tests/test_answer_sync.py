"""The Answer bank's sync to WorkIt (KAN-746), against a fake WorkIt
(fake_workit.py): off by default, each change sent once it is on, Claude's
drafts sent as Claude's, WorkIt down keeps the change, and `apply
sync-answers` pushes the whole bank. Every value here is made up."""

import dataclasses
from datetime import date, datetime

import pytest
from fake_workit import FakeWorkIt, Reply
from test_tracker_record import logged_in

from apply import answer_sync, cli
from apply.answer_bank import AnswerBank
from apply.answer_sync import AnswerSync
from apply.model import Question
from apply.workit import WorkIt

DAY = date(2026, 11, 10)
HEARD = Question("q1", "How did you hear about Initech?", "text", required=True)
SHIFTS = Question("q2", "Which shifts can you work?", "select", required=True, options=("Mornings", "Nights"))
ON = {"workit_sync": {"answers": True}}
PATH = "/applicants/00000000-0000-4000-8000-000000000001/fill-answers"


@pytest.fixture
def fake():
    """The fake WorkIt, keeping each fill-answers call in `fake.synced`; it has a newer
    answer of its own to each question in `fake.newer`, as WorkIt's merge would."""
    with FakeWorkIt() as fake:
        fake.synced, fake.newer = [], set()

        def merge(seen, fake):
            if not fake.signed_in(seen):
                return Reply(401, {"detail": "Not authenticated"})
            fake.synced.append(seen.body)
            kept = [a["question"] for a in seen.body["answers"] + seen.body["deleted"] if a["question"] in fake.newer]
            return Reply(200, {"saved": len(seen.body["answers"]) - len(kept), "deleted": len(seen.body["deleted"]),
                               "kept": kept})

        fake.route("PATCH", PATH, merge)
        yield fake


def synced(fake) -> list[dict]:
    return [a for body in fake.synced for a in body["answers"]]


def test_off_by_default_the_bank_stamps_nothing_and_sends_nothing(fake, tmp_path):
    path = tmp_path / "answer-bank.yaml"
    sync = AnswerSync(logged_in(fake, tmp_path), tmp_path / "queue.json")

    bank = answer_sync.bank(path, {}, sync)
    bank.add(HEARD, "From a friend.", "Initech", DAY)
    bank.answer(HEARD.label, "From a friend on the team.", DAY)

    assert fake.synced == []
    assert "edited_at" not in path.read_text()
    assert not answer_sync.enabled({"workit_sync": {"answers": "yes"}})  # only true turns it on


def test_each_change_goes_to_workit_and_a_claude_draft_goes_as_claude_s(fake, tmp_path):
    bank = answer_sync.bank(tmp_path / "answer-bank.yaml", ON, AnswerSync(logged_in(fake, tmp_path), tmp_path / "q.json"))

    bank.add(HEARD, "From the careers page.", "Initech", DAY)
    bank.answer(HEARD.label, "From a friend on the team.", DAY)

    draft, own = synced(fake)
    assert (draft["source"], draft["reviewed"], draft["company"]) == ("claude", False, "Initech")
    assert (own["question"], own["answer"], own["source"], own["reviewed"]) == (
        HEARD.label, "From a friend on the team.", "lisul", True)
    assert datetime.fromisoformat(own["edited_at"]).tzinfo is not None
    assert AnswerBank(tmp_path / "answer-bank.yaml").raw()[HEARD.label.casefold()]["edited_at"]


def test_a_delete_goes_and_a_counted_use_sends_nothing(fake, tmp_path):
    bank = answer_sync.bank(tmp_path / "answer-bank.yaml", ON, AnswerSync(logged_in(fake, tmp_path), tmp_path / "q.json"))
    bank.add(SHIFTS, ["Mornings"], "Initech", DAY)

    bank.use([SHIFTS.label], DAY)
    assert len(fake.synced) == 1
    bank.delete(SHIFTS.label)

    assert [d["question"] for d in fake.synced[-1]["deleted"]] == [SHIFTS.label.casefold()]


def test_with_workit_down_the_change_waits_and_goes_with_the_next(fake, tmp_path):
    queue = tmp_path / "q.json"
    client = logged_in(fake, tmp_path)
    bank = answer_sync.bank(tmp_path / "answer-bank.yaml", ON, AnswerSync(client, queue))
    with FakeWorkIt() as down:
        down.stop()  # the same login, but WorkIt's API does not answer
        unreachable = WorkIt(dataclasses.replace(fake.site, api=down.url), client.login)
        offline = answer_sync.bank(tmp_path / "answer-bank.yaml", ON, AnswerSync(unreachable, queue))
        offline.add(HEARD, "From the careers page.", "Initech", DAY)
        offline.answer(HEARD.label, "From a friend.", DAY)

    assert AnswerBank(tmp_path / "answer-bank.yaml").get(HEARD.label).answer == "From a friend."  # saved anyway
    assert AnswerSync(client, queue).waiting() == 1  # the newest per question
    assert fake.synced == []

    bank.add(SHIFTS, ["Nights"], "Initech", DAY)

    assert {a["question"]: a["answer"] for a in synced(fake)} == {HEARD.label: "From a friend.", SHIFTS.label: ["Nights"]}
    assert not queue.exists()


def test_with_no_login_a_change_waits_and_the_bank_still_saves(tmp_path):
    queue = tmp_path / "q.json"
    with FakeWorkIt() as fake:
        bank = answer_sync.bank(tmp_path / "answer-bank.yaml", ON,
                                AnswerSync(WorkIt(fake.site, tmp_path / "no-login.json"), queue))
        bank.answer(HEARD.label, "From a friend.", DAY)

        assert fake.requests == []
    assert AnswerBank(tmp_path / "answer-bank.yaml").get(HEARD.label).source == "lisul"
    assert AnswerSync(path=queue).waiting() == 1


def test_a_refused_batch_is_dropped_and_said(fake, tmp_path):
    fake.route("PATCH", PATH, lambda seen, fake: Reply(422, {"detail": "At most 2000 saved answers."}))
    sync = AnswerSync(logged_in(fake, tmp_path), tmp_path / "q.json")

    sent = sync.changed({"q": {"question": "Q?", "answer": "A.", "source": "lisul", "reviewed": True}}, [])

    assert sent.problems and "refused" in sent.problems[0]
    assert sync.waiting() == 0


BANK = """\
'how did you hear about initech?':
  question: How did you hear about Initech?
  answer: From a friend on the team.
  source: lisul
  reviewed: true
  first_seen: {date: 2026-10-16, company: Initech}
'what drew you to logistics?':
  question: What drew you to logistics?
  answer: Watching a warehouse route its trucks.
  source: claude
  reviewed: false
'which shifts can you work?':
  question: Which shifts can you work?
  answer: []
  none: true
  options: [Mornings, Nights]
  source: lisul
  reviewed: true
  edited_at: '2026-11-09T12:00:00+00:00'
"""


def test_sync_answers_pushes_the_whole_bank_and_names_what_workit_kept(fake, tmp_path, capsys):
    path = tmp_path / "answer-bank.yaml"
    path.write_text(BANK)
    fake.newer.add("What drew you to logistics?")

    code = cli._sync_answers(path, logged_in(fake, tmp_path), tmp_path / "q.json")

    sent = {a["question"]: a for a in synced(fake)}
    assert set(sent) == {"How did you hear about Initech?", "What drew you to logistics?", "Which shifts can you work?"}
    assert sent["How did you hear about Initech?"]["edited_at"] is None  # changed before the sync was on
    assert (sent["What drew you to logistics?"]["source"], sent["What drew you to logistics?"]["reviewed"]) == (
        "claude", False)
    assert sent["Which shifts can you work?"] == {
        "question": "Which shifts can you work?", "answer": [], "options": ["Mornings", "Nights"], "source": "lisul",
        "reviewed": True, "company": None, "edited_at": "2026-11-09T12:00:00+00:00"}  # none of its options: WorkIt deletes its copy
    out = capsys.readouterr().out
    assert code == 0
    assert "Kept WorkIt's newer answer to 1: What drew you to logistics?" in out
    assert "warehouse" not in out and "friend" not in out  # never an answer
    assert path.read_text() == BANK  # the push changes nothing in the bank


def test_sync_answers_needs_a_login(tmp_path, capsys):
    path = tmp_path / "answer-bank.yaml"
    path.write_text(BANK)
    with FakeWorkIt() as fake:
        assert cli._sync_answers(path, WorkIt(fake.site, tmp_path / "no-login.json"), tmp_path / "q.json") == 1
    assert "apply login" in capsys.readouterr().err
