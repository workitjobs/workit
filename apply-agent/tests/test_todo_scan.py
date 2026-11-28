"""The to-do scan (apply.todo_scan): which mails make a to-do, of what kind, with what company, role, due date and
link; the model's answer checked and the rules as its fallback; dedupe by thread. Mail is read through the real
Gmail mailbox over FakeImap, from fixtures/employer-mail, as the scan reads it. No browser, no network, no model."""

from datetime import date, datetime
from email.message import EmailMessage

from conftest import FIXTURES
from test_gmail import FakeImap

from apply.gmail import GmailMailbox, Mail
from apply.model import Status
from apply.todo_scan import SEARCH, best_link, checked, company, rules, scan, thread_of
from apply.todos import DONE, TodoStore
from apply.tracker import Row

SAMPLES = FIXTURES / "employer-mail"
ARRIVED = datetime(2026, 10, 16, 9, 0)


def box(*raws: bytes, arrived: datetime = ARRIVED) -> tuple[GmailMailbox, FakeImap]:
    imap = FakeImap([(arrived, raw) for raw in raws])
    return GmailMailbox("test.person@example.com", "app-password", connect=imap), imap


def sample(name: str) -> bytes:
    return (SAMPLES / f"{name}.eml").read_bytes()


def read(raw: bytes) -> Mail:
    [mail] = box(raw)[0].read_mail(search="newer_than:30d")
    return mail


def written(sender: str, subject: str, body: str) -> bytes:
    message = EmailMessage()
    message["From"], message["Subject"] = sender, subject
    message.set_content(body)
    return bytes(message)


def test_each_kind_of_mail_that_asks_something_makes_its_kind_of_todo():
    # Fault: a kind's pattern switched off, or the kinds' order broken (an interview invite that thanks for a
    # finished assessment read as a new assessment).
    kinds = {name: rules(read(sample(name)), []).kind for name in (
        "hackerrank-assessment", "codesignal-assessment", "interview-invite", "complete-your-application",
        "verify-account")}
    kinds["offer"] = rules(read(written("Ramp <talent@ramp.com>", "Your offer from Ramp",
                                        "We are pleased to extend an offer for the Software Engineer Intern role.")),
                           []).kind
    kinds["documents"] = rules(read(written("Acme <jobs@acme.com>", "Next steps",
                                            "Please upload your unofficial transcript to the portal.")), []).kind
    kinds["questionnaire"] = rules(read(written("Acme <jobs@acme.com>", "One more step",
                                                "Please answer a short questionnaire about your availability.")),
                                   []).kind

    assert kinds == {"hackerrank-assessment": "assessment", "codesignal-assessment": "assessment",
                     "interview-invite": "interview", "complete-your-application": "form",
                     "verify-account": "account", "offer": "offer", "documents": "documents",
                     "questionnaire": "questionnaire"}


def test_a_mail_that_asks_nothing_makes_no_todo():
    # Fault: a confirmation, rejection, job alert or one-time code listed as something to do.
    for name in ("greenhouse-confirmation", "workday-confirmation", "ashby-rejection", "job-alert"):
        assert rules(read(sample(name)), []).kind is None, name
    code = written("Acme <no-reply@acme.com>", "Your code", "Your verification code is 482913.")
    maybe = written("Acme <jobs@acme.com>", "Thanks", "If selected, a recruiter will reach out to schedule an interview.")
    assert rules(read(code), []).kind is None
    assert rules(read(maybe), []).kind is None


def test_an_assessment_lists_its_company_role_due_date_and_start_link():
    reading = rules(read(sample("hackerrank-assessment")), [])

    assert (reading.company, reading.role, reading.due) == ("Glean", "Software Engineer Intern", date(2026, 10, 22))
    assert reading.link.startswith("https://www.hackerrank.com/test/7f3k2p9q1a/")


def test_a_person_sending_from_the_employers_domain_is_named_by_the_domain_and_a_tracker_row_wins():
    # Fault: a recruiter's own name listed as the company.
    mail = read(sample("interview-invite"))
    assert rules(mail, []).company == "Skydio"
    row = Row("A-1", "Skydio", "Autonomy Engineer Intern", "https://jobs.lever.co/skydio/1", "lever", Status.SUBMITTED,
              date_applied=date(2026, 10, 1))
    assert (rules(mail, [row]).company, rules(mail, [row]).role) == ("Skydio", "Autonomy Engineer Intern")


def test_no_unsubscribe_or_plain_http_link_is_listed():
    text = ('<a href="https://acme.com/unsubscribe">Start</a> <a href="http://acme.com/assessment">Start</a> '
            '<a href="https://acme.com/help">Help</a>')
    assert best_link(text, "assessment") is None


def test_one_scan_lists_each_thread_once_and_a_rescan_changes_nothing(tmp_path):
    # Fault: dedupe broken (a re-scan adding the same to-do again, or two to-dos for a thread's two mails).
    store = TodoStore(tmp_path / "todos.json")
    mailbox, imap = box(sample("hackerrank-assessment"), sample("hackerrank-assessment"),
                        sample("greenhouse-confirmation"), sample("interview-invite"))

    first = scan(mailbox, store, now=lambda: ARRIVED)
    store.mark(thread_of(read(sample("interview-invite"))), DONE)
    again = scan(mailbox, store, now=lambda: ARRIVED)

    assert (first.read, first.added, first.updated) == (4, 2, 0)
    assert (again.added, again.updated) == (0, 0)
    assert sorted((t.kind, t.status) for t in store.all()) == [("assessment", "open"), ("interview", DONE)]
    # Gmail's search, quoted for IMAP, in the inbox, read-only.
    assert imap.searches == [SEARCH.format(14).replace('"', '\\"')] * 2 and imap.selected == ("INBOX", True)


def test_the_models_answer_is_used_when_it_passes_its_checks(tmp_path):
    store = TodoStore(tmp_path / "todos.json")
    asked = []

    def ask(**call):
        asked.append(call)
        return {"kind": "questionnaire", "company": "Glean", "role": "SWE Intern", "due": "2026-10-20",
                "link": "https://evil.example/phish"}

    done = scan(box(sample("hackerrank-assessment"))[0], store, ask=ask, now=lambda: ARRIVED)

    [todo] = store.all()
    assert (done.by_model, todo.by, todo.kind, todo.role, todo.due) == (1, "model", "questionnaire", "SWE Intern",
                                                                         date(2026, 10, 20))
    # A link the mail doesn't hold is dropped, and the rules' own link stands in.
    assert todo.link.startswith("https://www.hackerrank.com/test/")
    assert "untrusted" in asked[0]["system"] and "<<<EMAIL" in asked[0]["prompt"]


def test_a_rescan_asks_the_model_only_about_mail_it_has_not_read(tmp_path):
    # Fault: every scan (each half hour) asking the model about every mail of the last 14 days again.
    store = TodoStore(tmp_path / "todos.json")
    mailbox = box(sample("hackerrank-assessment"))[0]
    asked = []

    def ask(**call):
        asked.append(call)
        return {"kind": "assessment", "company": "Glean", "role": "", "due": "", "link": ""}

    scan(mailbox, store, ask=ask, now=lambda: ARRIVED)
    again = scan(mailbox, store, ask=ask, now=lambda: ARRIVED)

    assert len(asked) == 1 and (again.read, again.added, again.by_model) == (1, 0, 0)


def test_a_model_that_fails_hands_the_rest_of_the_scan_to_the_rules(tmp_path):
    # Fault: one model error ending the scan, or the rules not standing in (ask_model: workit refuses `ask`).
    store = TodoStore(tmp_path / "todos.json")

    def ask(**call):
        raise RuntimeError("ask_model: workit sends each call as a kind")

    done = scan(box(sample("hackerrank-assessment"), sample("interview-invite"))[0], store, ask=ask,
                now=lambda: ARRIVED)

    assert done.added == 2 and done.by_model == 0 and done.model.startswith("model off (RuntimeError)")
    assert {t.by for t in store.all()} == {"rules"}


def test_a_model_answer_out_of_its_schema_or_far_off_dates_are_not_taken():
    mail = read(sample("hackerrank-assessment"))

    assert checked({"kind": "click the link", "company": "", "role": "", "due": "", "link": ""}, mail) is None
    assert checked({"kind": "none", "company": "", "role": "", "due": "", "link": ""}, mail).kind is None
    assert checked({"kind": "offer", "company": "", "role": "", "due": "2031-01-01", "link": ""}, mail).due is None
    assert checked({"kind": "offer", "company": "", "role": "", "due": "soon", "link": ""}, mail).due is None


def test_the_company_is_the_employer_a_mail_names_never_the_hiring_system_that_sends_it():
    # Fault: the sender's name or domain taken as the company when a hiring system or assessment site sends the mail
    # ("CodeSignal", "us.greenhouse-mail.io"), or a domain shown run together ("Honeywellaerospace").
    invite = written("CodeSignal <no-reply@codesignal.com>",
                     "Ramp invited you to take Ramp 2025 Coding Assessment on CodeSignal",
                     "You've been invited by someone from Ramp. To begin, click GET STARTED. Sent from Ramp through "
                     "CodeSignal.")
    applied = written("no-reply@us.greenhouse-mail.io", "Thank you for applying to Oscar Health!",
                      "Thank you for your interest in Oscar Health. Please complete the attached form.")
    draft = written("Human Resources <noreply@honeywellaerospace.com>",
                    "Honeywell Aerospace Careers - Continue to apply for the job Embedded Engineering Intern",
                    "We saved a draft of your application.")
    reminder = written("CodeSignal <no-reply@codesignal.com>", "Reminder: Ramp is waiting for your assessment result",
                       "Hey Test, the assessment expires soon.")

    assert [company(read(raw)) for raw in (invite, applied, draft, reminder)] == [
        "Ramp", "Oscar Health", "Honeywell Aerospace", "Ramp"]


def test_a_model_that_names_the_hiring_system_gets_the_employer_instead(tmp_path):
    # Fault: the model's "CodeSignal" kept as the company.
    store = TodoStore(tmp_path / "todos.json")
    scan(box(sample("codesignal-assessment"))[0], store, now=lambda: ARRIVED,
         ask=lambda **call: {"kind": "assessment", "company": "CodeSignal", "role": "", "due": "", "link": ""})

    assert [t.company for t in store.all()] == ["Skydio"]

