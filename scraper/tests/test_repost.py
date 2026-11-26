"""Repost detection: `_is_repost` flags jobs whose `posted_at` is more than
`_REPOST_DAYS` after `first_seen_at`."""

from workit_scraper.shortlist import _REPOST_DAYS, _is_repost


class _FakeJob:
    def __init__(self, posted_at, first_seen_at):
        self.posted_at = posted_at
        self.first_seen_at = first_seen_at


def test_repost_30_day_gap():
    job = _FakeJob("2026-11-14", "2026-10-15")
    assert _is_repost(job) is True


def test_genuinely_new():
    job = _FakeJob("2026-11-14", "2026-11-14")
    assert _is_repost(job) is False


def test_no_posted_at():
    job = _FakeJob(None, "2026-11-14")
    assert _is_repost(job) is False


def test_no_first_seen_at():
    job = _FakeJob("2026-11-14", None)
    assert _is_repost(job) is False


def test_exactly_seven_days_is_not_repost():
    """The gap must be *greater than* _REPOST_DAYS, not equal."""
    job = _FakeJob("2026-11-21", "2026-11-14")
    assert _REPOST_DAYS == (21 - 14)  # sanity
    assert _is_repost(job) is False
