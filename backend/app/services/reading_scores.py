"""
The resume reading score's record (KAN-953): `data/reading_scores.json`, one
entry per run of `app.scripts.reading_score` (KAN-900) that the team chose to
keep, oldest first. The admins' Resume Reading page shows the newest.

A committed file, not a table: a score belongs to the code it scored, so it
travels with that code, and a new one reaches the page when its change
deploys. It holds totals only (the share of the answer keys' fields each
reading got right, in percent), so a run on real resumes is safe to commit:
no resume text and no name.

A run is `ran` (the day, YYYY-MM-DD), `set` ("made_up" for the committed
scoring set, "real" for the private one), `resumes` (how many every reader
read), `model` (the model that read them) and the three scores: `parser`
(the rule-based parser alone), `ai` (the model's reading alone) and
`combined` (the reading an upload saves).
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCORES = Path(__file__).resolve().parents[2] / "data" / "reading_scores.json"


def last_run(path: Path = SCORES) -> dict | None:
    """The newest recorded run, or None when the file is missing, holds no run
    or cannot be read: the page then says no run is recorded, and still loads."""
    try:
        runs = json.loads(path.read_text())["runs"]
        return dict(runs[-1]) if runs else None
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        logger.warning("The reading scores at %s could not be read", path, exc_info=True)
        return None
