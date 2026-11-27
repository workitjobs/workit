"""The Pre-submit check. Every answer read back from the page must be what was
meant (the Fill engine's read-back comparison, fill_engine.readback_problems);
then Claude reviews each question next to the answer on the page, for
answers that are valid but wrong."""


from apply import description, fill_engine, private
from apply.adapters import Claude
from apply.model import Answers, Posting, QuestionSet, Readback, one_line
from apply.records import SECRET

MAX_OPTIONS_SHOWN = 30  # a long list (every school) only costs tokens
class Found(list):
    """The review's problems, one line each, and `fixes`: for a problem the sources answer, the answer
    to enter in its place, by the question as the review named it (its label on one line)."""

    def __init__(self, problems=(), fixes: dict[str, str] | None = None):
        super().__init__(problems)
        self.fixes = dict(fixes or {})


def review(claude: Claude, posting: Posting, questions: QuestionSet, readback: Readback, sources: str = "",
           posting_text: str = "", own: set[str] | frozenset[str] = frozenset(),
           self_ids: frozenset[str] = frozenset()) -> Found:
    """Claude's review of the filled form: the problems it found, with the fixes it
    gives for those the sources answer (Found.fixes). `sources` is
    what essays may draw on (essays.sources, with the Company material), given
    when the form has essays; `posting_text` is the Posting's own text
    (apply.description), always given; `own` names the questions answered in
    Lisul's own words (his Answer bank answers). Secrets never leave Apply, nor does an answer that is exactly
    one of his self-ID answers (`self_ids`: private.self_id, D8), and his private details go as placeholders
    (apply.private). The read-back check, which is code, still checks every field the engine typed."""
    rows = _rows(questions, readback, own, self_ids)
    if not rows:
        return Found()
    # WorkIt's presubmit.review kind (D5, KAN-723): its prompt is on the server.
    given = claude.ask_kind("presubmit.review", {"sources": sources, "posting": description.block(posting, posting_text),
                                                 "rows": rows})
    problems = [str(problem).strip() for problem in given.get("problems") or [] if str(problem).strip()]
    asked = {row["question"] for row in rows}
    fixes = {}
    for fix in given.get("fixes") or [] if problems else []:  # a fix is for a problem: none without one
        question = str((fix or {}).get("question") or "").strip().strip("'\"“”") if isinstance(fix, dict) else ""
        answer = str((fix or {}).get("answer") or "").strip() if isinstance(fix, dict) else ""
        if question in asked and answer:
            fixes[question] = answer
    return Found(problems, fixes)


def _rows(questions: QuestionSet, readback: Readback, own: set[str] | frozenset[str],
          self_ids: frozenset[str]) -> list[dict]:
    """Each answered field as the review reads it: never a secret's answer, nor one that is a self-ID answer."""
    return [
        # Labelled, so a multi-select's ticked boxes never read as its options (Palantir, live).
        {"question": one_line(q.label),
         # Only typed answers can hold a secret; an option picked ("I agree... trade secrets") is shown.
         "ticked" if q.kind == "multi_select" else "answer":
             "(secret)" if q.kind in ("text", "textarea") and (SECRET.search(q.label) or SECRET.search(q.name))
             else readback[q.name],
         **({"options": list(q.options)} if q.options and len(q.options) <= MAX_OPTIONS_SHOWN else {}),
         **({"his_own_answer": True} if q.name in own else {})}
        for q in questions if readback.get(q.name) not in (None, "", []) and not private.is_self_id(readback[q.name], self_ids)
    ]


def replan(claude: Claude, questions: QuestionSet, answers: Answers, readback: Readback,
           accepted: dict[str, tuple[str, ...]] | None = None, posting: Posting | None = None,
           posting_text: str = "") -> Answers:
    """`answers`, with each one the page showed otherwise planned again.
    Files and secrets are left as they are, and so is any new answer that
    isn't one of its question's options. `posting` and its own text
    (apply.description) are given to the call as context."""
    flagged = {
        f"q{n}": q for n, q in enumerate(questions, 1)
        if q.name in answers and q.kind != "file" and not (SECRET.search(q.label) or SECRET.search(q.name))
        and not fill_engine.shows(readback.get(q.name, ""), answers[q.name], (accepted or {}).get(q.name, ()))
    }
    if not flagged:
        return answers
    # WorkIt's presubmit.replan kind (D5, KAN-723): its prompt and schema are on the server.
    fields = {key: {"question": one_line(q.label), "options": list(q.options), "meant": answers[q.name],
                    "shown": readback.get(q.name, ""), "multi_select": q.kind == "multi_select"}
              for key, q in flagged.items()}
    data = {"posting": description.block(posting, posting_text) if posting else "", "fields": fields}
    replanned = claude.ask_kind("presubmit.replan", data).get("replanned") or {}
    new = dict(answers)
    for key, q in flagged.items():
        answer = (replanned.get(key) or {}).get("answer")
        chosen = answer if isinstance(answer, list) else [answer]
        if answer and all(isinstance(a, str) and a.strip() for a in chosen) and (
                not q.options or all(a in q.options for a in chosen)):
            new[q.name] = answer if isinstance(answer, list) else answer.strip()
    return new
