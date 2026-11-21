"""The Answer bank: one answer per one-off question, kept on WorkIt and read once into memory (W11)."""

import threading
import time

import pytest
from fake_bank import Server, Source

from apply import answer_bank, masked
from apply.answer_bank import AnswerBank, NotSaved, key
from apply.model import Question
from apply.workit import Unreachable, WorkItError

HEARD = Question("q1", "Tell us how you heard about Zipline", "text", required=True)
SAMPLES = Question("q2", "Will you be including a link on your resume to samples of projects you've worked on?",
                   "select", required=True, options=("Yes", "No"))
SKILLS = Question("q3", "Skill Areas (Select all that apply)", "multi_select", True, ("Finance", "Software", "Robotics"))


def test_a_draft_is_found_again_under_its_question_in_any_case_or_spacing():
    bank = AnswerBank()
    assert bank.add(HEARD, "From the Simplify list.", "Zipline")

    assert bank.get("  tell us how you heard about zipline * ").answer == "From the Simplify list."
    assert bank.get(HEARD.label).own is False  # the model's, until the student reviews it


def test_an_answer_in_the_bank_is_never_replaced_by_a_new_draft():
    bank = AnswerBank()
    bank.answer(SAMPLES.label, "No")
    bank.add(HEARD, "From the Simplify list.", "Zipline")

    assert not bank.add(SAMPLES, "Yes", "Roblox")
    assert not bank.add(HEARD, "From LinkedIn.", "Roblox")
    assert (bank.get(SAMPLES.label).answer, bank.get(HEARD.label).answer) == ("No", "From the Simplify list.")


def test_workers_drafting_at_once_lose_no_answer():
    bank = AnswerBank()
    questions = [Question(f"q{n}", f"Question {n}?", "text", True) for n in range(40)]
    threads = [threading.Thread(target=bank.add, args=(q, f"Draft {q.name}", "Acme")) for q in questions]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(e.answer for e in bank.entries()) == sorted(f"Draft {q.name}" for q in questions)


def test_the_students_answer_replaces_a_draft_and_review_makes_a_draft_theirs():
    bank = AnswerBank()
    bank.add(HEARD, "From the Simplify list.", "Zipline")
    bank.add(SAMPLES, "Yes", "Zipline")

    bank.answer(HEARD.label, "A friend on the avionics team.")
    assert bank.review(SAMPLES.label)
    bank.answer("Do you have a driver's license?", "Yes")  # one they add themselves

    assert [(e.answer, e.own) for e in bank.entries()] == [
        ("A friend on the avionics team.", True), ("Yes", True), ("Yes", True)]
    assert bank.own_lines()[0] == "Tell us how you heard about Zipline: A friend on the avionics team."
    assert not bank.review("Never asked?")


def test_a_redraft_replaces_the_models_draft_but_never_the_students_answer():
    bank = AnswerBank()
    bank.add(HEARD, "From the Simplify list.", "Zipline")
    bank.answer(SAMPLES.label, "No")

    assert bank.redraft(HEARD, "From a friend.")
    assert not bank.redraft(SAMPLES, "Yes")
    assert (bank.get(HEARD.label).answer, bank.get(SAMPLES.label).answer) == ("From a friend.", "No")


def test_a_deleted_answer_leaves_the_bank_so_the_model_drafts_it_again():
    bank = AnswerBank()
    bank.add(HEARD, "From the Simplify list.", "Zipline")

    assert bank.delete(HEARD.label.upper())
    assert bank.get(HEARD.label) is None and not bank.delete(HEARD.label)
    assert bank.add(HEARD, "From LinkedIn.", "Roblox")


def test_none_of_a_multi_selects_options_is_an_answer():
    bank = AnswerBank()
    bank.answer(SKILLS.label, [])

    entry = bank.get(SKILLS.label)
    assert (entry.answer, entry.none) == ([], True)


def test_a_bare_date_is_filed_under_its_section_never_its_label_alone():
    # Arrowstreet (live, 2026-11-04): "from (mm/dd/yyyy)" held the internship's start, for every From on every form.
    bank = AnswerBank()
    start = Question("q", "From (MM/DD/YYYY)", "text", True)

    assert bank.add(start, "06/01/2026", "Acme", wording="work experience / From (MM/DD/YYYY)")

    assert bank.get("From (MM/DD/YYYY)") is None
    assert bank.get("work experience / From (MM/DD/YYYY)").answer == "06/01/2026"


def test_test_persons_bank_keeps_no_drafts():
    bank = AnswerBank(drafts=False)

    assert not bank.add(HEARD, "From the Simplify list.", "Zipline")
    assert not bank.redraft(HEARD, "From a friend.")
    assert bank.entries() == []


def test_the_bank_reads_workits_entries_and_masks_their_answers():
    bank = AnswerBank(Source({
        "tell us how you heard about zipline": {"question": HEARD.label, "answer": "A friend at Zipline HQ.", "own": True},
        "skill areas (select all that apply)": {"question": SKILLS.label, "answer": [], "own": False, "none": True},
    }))
    assert not bank.ready

    bank.load()

    assert bank.ready
    assert [(e.question, e.own, e.none) for e in bank.entries()] == [(HEARD.label, True, False), (SKILLS.label, False, True)]
    assert "A friend at Zipline HQ." not in masked.KNOWN.scrub("They heard: A friend at Zipline HQ.")


def test_a_bank_that_cant_read_tries_again_in_the_background_and_at_once_on_wake(monkeypatch):
    monkeypatch.setattr("apply.answer_bank.RETRIES", (30.0,))
    source = Source({"q": {"question": "Q?", "answer": "Yes", "own": True}}, fails=2)
    bank = AnswerBank(source)
    with pytest.raises(Unreachable):
        bank.load()

    bank.load_in_background()

    assert bank.wake(5.0)  # the first try in the thread fails; the wake skips its 30 s wait
    assert bank.get("Q?").answer == "Yes" and bank.problem == ""
    assert source.reads == 3


def loaded(server: Server) -> AnswerBank:
    bank = AnswerBank(server)
    bank.load()
    return bank


def test_a_draft_goes_to_workit_flagged_with_its_job_and_enters_memory_only_from_the_reply():
    """Fault: memory took a draft WorkIt's rule kept out, so a later form filled it; or a draft named no form."""
    server = Server(keeps_out=(SAMPLES.label,))
    bank = loaded(server)

    assert bank.add(HEARD, "From the Simplify list.", "Zipline", job_id="j1")
    assert bank.add(SAMPLES, "Yes", "Zipline")
    assert not bank.add(HEARD, "From LinkedIn.", "Roblox")  # one on its way already
    bank.close()

    assert server.sent == [
        ([{"question": HEARD.label, "answer": "From the Simplify list.", "review": True, "choice": False, "job_id": "j1"}], []),
        ([{"question": SAMPLES.label, "answer": "Yes", "review": True, "choice": True, "company": "Zipline"}], []),
    ]
    assert bank.get(HEARD.label).answer == "From the Simplify list." and not bank.get(HEARD.label).own
    assert bank.get(SAMPLES.label) is None
    assert server.reads == 1  # each reply was the bank's own version plus one: nothing to read again


def test_the_students_edit_waits_for_workit_and_says_why_its_rule_kept_it_out():
    server = Server({key(HEARD.label): {"question": HEARD.label, "answer": "From the Simplify list.", "own": False}},
                    keeps_out=("Why Zipline?",))
    bank = loaded(server)

    assert bank.review(HEARD.label)  # back from WorkIt before it returns
    assert bank.get(HEARD.label).own
    with pytest.raises(NotSaved, match="It names Zipline") as kept_out:
        bank.answer("Why Zipline?", "The drones.")

    assert kept_out.value.status == 400 and bank.get("Why Zipline?") is None
    # Reviewed sends a pick: the answer WorkIt's rule let in, read by its question alone again (a pick "Google"
    # read as text names a company the student applied to, and could never be reviewed).
    assert server.sent[0] == ([{"question": HEARD.label, "answer": "From the Simplify list.", "review": False,
                                "choice": True}], [])


def test_another_writers_save_meanwhile_reads_the_bank_again():
    """Fault: a choice the student gave in the extension never reached the app's memory."""
    server = Server(others=1)
    bank = loaded(server)
    server.answers[key(SKILLS.label)] = {"question": SKILLS.label, "answer": ["Software"], "own": True}

    bank.add(HEARD, "From the Simplify list.", "Zipline")
    bank.close()

    assert server.reads == 2 and bank.get(SKILLS.label).answer == ["Software"]
    assert bank.get(HEARD.label).answer == "From the Simplify list."


def test_a_draft_workit_doesnt_answer_is_sent_again_then_dropped_and_a_refusal_at_once(monkeypatch, capsys):
    monkeypatch.setattr(answer_bank, "SEND_RETRIES", (0.01, 0.01))
    server = Server(unanswered=2)
    bank = loaded(server)
    bank.add(HEARD, "From the Simplify list.", "Zipline")
    bank.close()
    assert len(server.sent) == 3 and bank.get(HEARD.label).answer == "From the Simplify list."

    server.unanswered = 3
    bank.add(SAMPLES, "Yes", "Zipline")
    bank.close()
    assert len(server.sent) == 6 and bank.get(SAMPLES.label) is None  # drafted again the next time a form asks

    server.refusal = WorkItError("PATCH: 422", 422)
    bank.add(SKILLS, ["Software"], "Zipline")
    bank.close()
    assert len(server.sent) == 7 and bank.get(SKILLS.label) is None
    said = capsys.readouterr().err
    assert "Unreachable 502" in said and "WorkItError 422" in said and SAMPLES.label in said
    assert "Software" not in said  # the log names the question only


def test_an_edit_workit_doesnt_answer_says_not_saved_and_is_never_sent_after(monkeypatch):
    monkeypatch.setattr(answer_bank, "EDIT_WAIT", 0.2)
    monkeypatch.setattr(answer_bank, "SEND_RETRIES", (0.5,))
    server = Server(unanswered=5)
    bank = loaded(server)

    with pytest.raises(NotSaved, match="WorkIt didn't answer") as unsaved:
        bank.answer(HEARD.label, "A friend.")

    bank.close()
    assert unsaved.value.status == 503 and len(server.sent) == 1 and bank.get(HEARD.label) is None
    server.unanswered, server.refusal = 0, WorkItError("PATCH: 413", 413)
    with pytest.raises(NotSaved, match="refused it") as refused:
        bank.answer(HEARD.label, "A friend.")
    assert refused.value.status == 400


def test_the_students_edit_goes_ahead_of_the_drafts_and_in_place_of_one_to_its_question():
    """Fault: the Answers view waited behind every draft, or a draft sent after the student's edit replaced it."""
    gate = threading.Event()
    server = Server(gate=gate)
    bank = loaded(server)
    third = Question("q4", "Are you 18 or older?", "select", True, ("Yes", "No"))
    bank.add(HEARD, "From the Simplify list.", "Zipline")  # in flight, held at the gate
    bank.add(SAMPLES, "Yes", "Zipline")
    bank.add(third, "Yes", "Zipline")
    threading.Timer(0.3, gate.set).start()

    bank.answer(third.label, "No")
    bank.close()

    assert [(e[0]["question"], e[0]["answer"]) for e, _ in server.sent] == [
        (HEARD.label, "From the Simplify list."), (third.label, "No"), (SAMPLES.label, "Yes")]
    assert bank.get(third.label).own


def test_a_draft_the_pre_submit_review_found_wrong_leaves_the_bank_but_the_students_answer_stays():
    server = Server({key(HEARD.label): {"question": HEARD.label, "answer": "From LinkedIn.", "own": False},
                     key(SAMPLES.label): {"question": SAMPLES.label, "answer": "No", "own": True}})
    bank = loaded(server)

    bank.drop_draft(SAMPLES.label)
    bank.drop_draft(HEARD.label)
    bank.close()

    assert server.sent == [([], [HEARD.label])]
    assert bank.get(HEARD.label) is None and bank.get(SAMPLES.label).answer == "No"


def test_a_draft_the_review_found_wrong_while_it_was_on_its_way_never_stays_in_the_bank(monkeypatch):
    """Fault: the review looked in memory alone, so a draft waiting to be sent again (or being sent) landed later,
    an answer known wrong for every later form."""
    monkeypatch.setattr(answer_bank, "SEND_RETRIES", (0.3,))
    server = Server(unanswered=1)
    bank = loaded(server)
    bank.add(HEARD, "From LinkedIn.", "Zipline")  # WorkIt didn't answer: waiting to be sent again
    for _ in range(100):
        if server.sent:
            break
        threading.Event().wait(0.01)

    bank.drop_draft(HEARD.label)
    bank.close()
    assert len(server.sent) == 1 and bank.get(HEARD.label) is None

    gate = threading.Event()
    server.gate = gate
    bank.add(SAMPLES, "Yes", "Zipline")  # being sent, held at the gate
    for _ in range(100):
        if len(server.sent) == 2:
            break
        threading.Event().wait(0.01)
    bank.drop_draft(SAMPLES.label)
    gate.set()
    bank.close()
    assert server.sent[2] == ([], [SAMPLES.label]) and key(SAMPLES.label) not in server.answers
    assert bank.get(SAMPLES.label) is None


def test_a_change_waiting_behind_one_to_the_same_question_waits_without_spinning(monkeypatch):
    """Fault: the sender's wait took the due time of the change behind, already past, and looped at full speed till
    the one ahead was due."""
    monkeypatch.setattr(answer_bank, "SEND_RETRIES", (0.6,))
    server = Server(unanswered=1)
    bank = loaded(server)
    bank.add(HEARD, "From LinkedIn.", "Zipline")  # not answered: sent again in 0.6 s
    for _ in range(100):
        if server.sent:
            break
        threading.Event().wait(0.01)
    bank.redraft(HEARD, "From a friend.")  # due now, but behind the first

    used = time.process_time()
    threading.Event().wait(0.4)
    assert time.process_time() - used < 0.2
    bank.close()
    assert [e[0]["answer"] for e, _ in server.sent] == ["From LinkedIn.", "From LinkedIn.", "From a friend."]


def test_before_an_application_the_bank_is_read_again_only_when_workits_version_moved():
    """Fault: a choice the student gave in the extension never reached the app's next Application (W11)."""
    server = Server()
    bank = loaded(server)
    bank.follow(7)
    assert server.reads == 1  # the version memory holds: nothing to read

    server.answers[key(SKILLS.label)] = {"question": SKILLS.label, "answer": ["Software"], "own": True}
    server.version = 8  # the extension saved it
    bank.follow(8)
    assert server.reads == 2 and bank.get(SKILLS.label).answer == ["Software"]

    bank.follow()  # a reading without the version (a Developer checkout off the Model route): the bank asks
    assert (server.asked, server.reads) == (1, 2)

    server.version, server.fails = 9, 3  # WorkIt down: memory stays, and the next check reads
    bank.follow(9)
    assert server.reads == 3 and bank.get(SKILLS.label).answer == ["Software"]
    bank.follow(9)
    assert server.reads == 4


OLD_FILE = """\
'are you open to working in person?':
  question: Are you open to working in person?
  answer: Yes
  options: [Yes, No]
  source: lisul
  reviewed: true
  first_seen: {date: 2026-10-01, company: Example Robotics}
'how did you hear about us?':
  question: How did you hear about us?
  answer: The Simplify list.
  source: lisul
  reviewed: false
'tell us how you heard about zipline':
  question: Tell us how you heard about Zipline
  answer: From LinkedIn.
  source: claude
'fax number':
  question: Fax number
  answer: ''
"""


def test_a_developers_old_answer_bank_file_goes_to_workit_once_then_is_renamed(tmp_path):
    """W11: no student has the file; a Developer checkout's goes once, with no word, only what WorkIt lacks."""
    (tmp_path / "answer-bank.yaml").write_text(OLD_FILE)
    server = Server({key(HEARD.label): {"question": HEARD.label, "answer": "A friend.", "own": True}})
    bank = loaded(server)

    bank.upload(tmp_path)

    assert server.sent == [([  # a bare Yes stays the word, as Apply wrote it; an empty answer stays out
        {"question": "Are you open to working in person?", "answer": "Yes", "review": False, "choice": True,
         "company": "Example Robotics"},
        {"question": "How did you hear about us?", "answer": "The Simplify list.", "review": True, "choice": False},
    ], [])]
    assert not (tmp_path / "answer-bank.yaml").exists() and (tmp_path / "answer-bank.before-workit.yaml").is_file()
    assert bank.get("How did you hear about us?").own is False and bank.get(HEARD.label).answer == "A friend."
    bank.upload(tmp_path)
    assert len(server.sent) == 1  # once


def test_the_upload_goes_in_patches_of_100_and_one_that_fails_keeps_the_file_for_the_next_start(tmp_path):
    (tmp_path / "answer-bank.yaml").write_text(
        "".join(f"q{n}:\n  question: Question {n}?\n  answer: Answer {n}\n  source: lisul\n" for n in range(150)))
    AnswerBank(drafts=False).upload(tmp_path)  # Test Person's bank sends nothing anywhere
    server = Server(unanswered=1)
    bank = loaded(server)

    with pytest.raises(Unreachable):
        bank.upload(tmp_path)
    assert (tmp_path / "answer-bank.yaml").is_file()
    bank.upload(tmp_path)

    assert [len(entries) for entries, _ in server.sent] == [100, 100, 50]
    assert len(bank.entries()) == 150


def test_the_upload_sends_the_students_own_answer_where_workit_holds_only_a_models_draft(tmp_path):
    """Fault: any answer WorkIt held kept the file's out, so a draft from the extension's Claude beat the student's
    own reviewed answer (W11: a model's draft never replaces the student's own)."""
    (tmp_path / "answer-bank.yaml").write_text(OLD_FILE)
    server = Server({  # both the model's: the file has the student's own to the first, a draft to the second
        key("Are you open to working in person?"): {"question": "Are you open to working in person?", "answer": "No",
                                                    "own": False},
        key("How did you hear about us?"): {"question": "How did you hear about us?", "answer": "LinkedIn.",
                                            "own": False},
    })
    bank = loaded(server)

    bank.upload(tmp_path)

    assert [e["question"] for e in server.sent[0][0]] == ["Are you open to working in person?",
                                                          "Tell us how you heard about Zipline"]
    entry = bank.get("Are you open to working in person?")
    assert (entry.answer, entry.own) == ("Yes", True) and bank.get("How did you hear about us?").answer == "LinkedIn."


def test_an_upload_whose_read_back_fails_keeps_the_file_and_the_next_start_only_renames_it(tmp_path):
    """Fault: renamed before the read, the command said the file hadn't reached WorkIt, which it had."""
    (tmp_path / "answer-bank.yaml").write_text(OLD_FILE)
    server = Server()
    bank = loaded(server)
    server.fails = 2  # the next read gets no answer

    with pytest.raises(Unreachable):
        bank.upload(tmp_path)
    assert (tmp_path / "answer-bank.yaml").is_file() and len(server.sent) == 1

    loaded(server).upload(tmp_path)  # the next command: WorkIt holds them now
    assert len(server.sent) == 1 and (tmp_path / "answer-bank.before-workit.yaml").is_file()


def test_a_read_that_comes_back_after_a_newer_save_keeps_the_save():
    """Fault: a Worker's read, answered before the student's Save reached WorkIt but landing after its reply, put
    the old bank back: the tab said Saved and showed the old answer."""
    server = Server()
    bank = loaded(server)
    bank.answer(HEARD.label, "A friend.")  # version 8, in memory from its reply
    server.answers, server.version = {}, 7  # the read that left before it

    bank.load()

    assert bank.get(HEARD.label).answer == "A friend."
