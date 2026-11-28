"""Essays an Application wrote but never sent, because it failed after
writing them (a Worker gone mid-fill, a page that broke, a usage limit):
kept by the Posting's link, so its next attempt takes them instead of
writing them again. Each one is a plan, a draft, a claim check and two
edits, about 200k tokens a form (WorkerGone retries, 2026-11-25).

Kept as an Essay cell (essays.as_cell), for KEEP. Only a clean essay is
kept (_clean): the cell keeps no flags, so one that failed a gate or would
be held is written again, and held again. An attempt that fails keeps
what it has (taken essays too); one that ends any other way forgets them.
A Plan isn't kept: a taken essay has none."""

import hashlib
from datetime import date, timedelta
from pathlib import Path

from apply import essays
from apply.feed import normalize_url
from apply.home import HOME
from apply.model import Posting, Question

UNSENT = HOME / "unsent-essays"
KEEP = timedelta(days=14)  # past it the brief, the bank or the Story bank may have moved on
KEPT = "Kept "


def keep(posting: Posting, written: list["essays.Essay"], today: date) -> None:
    """Keep `posting`'s clean written essays; none: forget any kept."""
    if not (passed := [e for e in written if _clean(e)]):
        forget(posting)
        return
    UNSENT.mkdir(exist_ok=True)
    _path(posting).write_text(f"{KEPT}{today.isoformat()}\n\n{essays.as_cell(passed)}", encoding="utf-8")


def take(posting: Posting, questions: list[Question], today: date) -> list["essays.Essay"]:
    """The kept essays of `posting` that answer one of `questions`, if kept less than KEEP."""
    path = _path(posting)
    if not questions or not path.exists():
        return []
    stamp, _, cell = path.read_text(encoding="utf-8").partition("\n\n")
    try:
        kept = date.fromisoformat(stamp.removeprefix(KEPT))
    except ValueError:
        return []
    if today - kept > KEEP:
        return []
    return [e for e in essays.from_cell(cell, questions) if e.text]


def _clean(essay: "essays.Essay") -> bool:
    return bool(essay.text) and not (essay.failed or essay.unsupported or essay.claims or essay.needs_applicant
                                     or essay.giveaways or essay.sensitive)


def forget(posting: Posting) -> None:
    _path(posting).unlink(missing_ok=True)


def _path(posting: Posting) -> Path:
    return UNSENT / f"{hashlib.sha1(normalize_url(posting.url).encode()).hexdigest()[:12]}.md"
