"""Measure the generic Filler against Claude fill and the job system's own Filler (KAN-861, W2's "Done when").

    uv run python scripts/generic_fill_measure.py [--claude] [saved-form ...]

Each saved form of the Fill engine (default: the six Lever forms, whose questions the engine reads off the served
page with no network) is served on 127.0.0.1 as `apply plain fill` serves it, which refuses every POST, and filled
in a plain Worker as Test Person, once by each Filler in a fresh tab:

- **engine**: the Fill engine's own Filler for the form's job system (what `apply plain fill` runs);
- **generic**: the generic Filler (apply.generic_fill), code only: a Developer checkout has no WorkIt Model route,
  so its picks are none and each field it can't match is the student's;
- **claude** (with --claude): Claude fill (apply.claude_fill), Haiku driving the page through `claude -p`. It
  spends the developer's own Claude usage.

Each Filler reads the form its own way and plans its own answers with the same planner and profile; no essay is
written. Then the engine itself reads the page back for the questions it reads, and the score is how many of its
own plan's answers the page shows: one ruler for all three. Nothing is ever submitted.
"""

import argparse
import sys
import time
from contextlib import contextmanager

from apply import fill_engine
from apply.generic_fill import GenericFiller
from apply.home import SAMPLE
from apply.model import FillError, Handoff, MoreQuestions, Posting
from apply.plain.demo import SAVED_FORMS, replay
from apply.plain.launcher import PlainWorkers
from apply.profile import ApplicantProfile

LEVER = ["lever-belvedere", "lever-hermeus", "lever-immuta", "lever-rhombus", "lever-shieldai", "lever-xcimer"]


class Site:
    def __init__(self, page):
        self.page = page

    @contextmanager
    def open(self, url):
        yield self.page


def _planned(questions, posting, profile) -> dict:
    planned = fill_engine.plan(questions, posting, profile)
    return {name: value for name, value in planned.answers.items() if value not in (None, "", [])}


def _by_filler(filler, page, url, posting, profile) -> str:
    """Fill the page with `filler` (the generic Filler or Claude fill) to its last step; how it ended."""
    questions = filler.question_set(url, Site(page))
    answers = _planned(questions, posting, profile)
    for _ in range(20):
        try:
            filler.fill(page, questions, answers)
            return "filled"
        except MoreQuestions as more:
            questions = [*questions, *more.questions]
            answers |= _planned(more.questions, posting, profile)
        except FillError as error:  # that field is the student's: dropped, as the Worker drops it
            field = str(error).split(":", 1)[0].strip()
            answers = {n: a for n, a in answers.items() if n != field and next(
                (q.label.strip() for q in questions if q.name == n), "") != field}
        except Handoff as handoff:
            return f"handoff: {handoff}"
    return "no end"


def _by_engine(page, site, questions, answers) -> str:
    answers = dict(answers)
    for _ in range(10):
        try:
            fill_engine.fill(page, site, questions, answers)
            return "filled"
        except FillError as error:
            answers.pop(str(error).split(":", 1)[0], None)
    return "no end"


def measure(form: str, who: str, workers: PlainWorkers, profile: ApplicantProfile) -> tuple[int, int, str, float]:
    with replay(SAVED_FORMS / form) as (url, real), workers.open(url) as page:
        page.wait_for_timeout(1500)
        site = fill_engine.job_of(real)["site"]
        posting = Posting(form, "Saved form", "Intern", real)
        truth_questions = fill_engine.parse_questions(site, page.evaluate("() => document.documentElement.outerHTML"))
        planned = fill_engine.plan(truth_questions, posting, profile)
        truth = {n: a for n, a in planned.answers.items() if a not in (None, "", [])}
        started = time.monotonic()
        if who == "engine":
            ended = _by_engine(page, site, truth_questions, truth)
        elif who == "generic":
            ended = _by_filler(GenericFiller(resume=profile.get("files.resume_pdf")), page, url, posting, profile)
        else:
            from apply.claude_cli import ClaudeCLI
            from apply.claude_fill import ClaudeFill

            ended = _by_filler(ClaudeFill(ClaudeCLI(), resume=profile.get("files.resume_pdf")), page, url, posting, profile)
        seconds = time.monotonic() - started
        shown = fill_engine.call(page, "readback", site, fill_engine.questions_arg(truth_questions), list(truth))
        right = sum(1 for n, a in truth.items()
                    if fill_engine.shows(shown.get(n), a.name if hasattr(a, "name") else a, planned.accepted.get(n, ())))
        return right, len(truth), ended, seconds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("forms", nargs="*", default=LEVER)
    parser.add_argument("--claude", action="store_true", help="also run Claude fill (spends your Claude usage)")
    parser.add_argument("--only", choices=["engine", "generic", "claude"], help="run this Filler alone")
    args = parser.parse_args()
    profile = ApplicantProfile.load(SAMPLE / "applicant-profile.yaml")
    whos = ["engine", "generic", *(["claude"] if args.claude else [])] if not args.only else [args.only]
    workers = PlainWorkers()
    totals = {who: [0, 0] for who in whos}
    try:
        for form in args.forms:
            for who in whos:
                right, planned, ended, seconds = measure(form, who, workers, profile)
                totals[who][0] += right
                totals[who][1] += planned
                print(f"{form:20} {who:8} {right:3}/{planned:3} right  {seconds:6.1f}s  {ended[:110]}", flush=True)
    finally:
        workers.stop_all()
    for who, (right, planned) in totals.items():
        print(f"TOTAL {who:8} {right}/{planned} ({100 * right / max(planned, 1):.0f}%)")


if __name__ == "__main__":
    sys.exit(main())
