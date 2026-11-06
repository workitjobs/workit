"""SuccessFactors pagination failures cannot supply complete or missing evidence."""

import html
import json
import re
from pathlib import Path

import pytest

from workit_scraper import providers
from workit_scraper.board_read import ReadStatus, read_board
from workit_scraper.providers.systems import successfactors as reader

TOKEN = "www.careerprofile.epiroc.com"
SEARCH = (Path(__file__).parent / "fixtures/providers/successfactors-search.html").read_text(
    encoding="utf-8"
)
ROWS = re.findall(r'<tr class="data-row">.*?</tr>', SEARCH, re.S)
CAPTURE = json.loads(
    (Path(__file__).parent / "fixtures/providers/successfactors-epiroc.json").read_text(
        encoding="utf-8"
    )
)


def captured_page(record):
    """Rebuild only the table markup around the captured listing fields."""
    return record["label"] + "".join(
        '<tr class="data-row">'
        f'<a href="{html.escape(path)}" class="jobTitle-link">{html.escape(title)}</a>'
        f'<span class="jobLocation">{html.escape(place)}</span>'
        f'<span class="jobDate">{html.escape(day)}</span></tr>'
        for path, title, place, day in record["rows"]
    )


def test_live_epiroc_capture_replays_all_308_postings(monkeypatch):
    pages = {p["offset"]: p for p in CAPTURE["pages"]}
    asked, paced = [], []

    def response(url):
        offset = int(url.rsplit("startrow=", 1)[1])
        asked.append(offset)
        return captured_page(pages[offset])

    monkeypatch.setattr(providers.fetch, "_get_text", response)
    jobs = reader.successfactors(TOKEN, "Epiroc", pace=paced.append)
    assert len(jobs) == 308
    assert [job.external_id for job in jobs] == [
        row[0] for p in CAPTURE["pages"] for row in p["rows"]
    ]
    assert asked == list(pages)
    assert len(paced) == 12


def test_captured_fallback_total_ten_is_not_a_complete_board(monkeypatch):
    # Substitute the observed out-of-range fallback for the last page: a falling
    # total must not make the already observed larger inventory complete.
    pages = iter([*CAPTURE["pages"][:-1], CAPTURE["tail"]])
    monkeypatch.setattr(providers.fetch, "_get_text", lambda url: captured_page(next(pages)))
    with pytest.raises(providers.Incomplete):
        reader.successfactors(TOKEN, "Epiroc")


class AllowedRobots:
    def allows(self, url):
        return True

    def pace(self, url):
        pass


def page(total, rows):
    """Keep real trimmed rows; vary only count and pagination composition."""
    text = re.sub(r'<tr class="data-row">.*?</tr>', "", SEARCH, flags=re.S)
    return text.replace("of <b>2</b>", f"of <b>{total}</b>").replace(
        "</tbody>", "".join(rows) + "</tbody>"
    )


def board_read():
    return read_board(providers.Board("successfactors", TOKEN, "Epiroc"), AllowedRobots())


def test_later_page_404_is_failed_not_missing(monkeypatch):
    def response(url):
        if url.endswith("startrow=0"):
            return page(3, ROWS)
        raise providers.BoardNotFound(url)

    monkeypatch.setattr(providers.fetch, "_get_text", response)
    result = board_read()
    assert result.status is ReadStatus.FAILED
    assert result.reason == "incomplete"
    assert isinstance(result.error, providers.Incomplete)
    assert result.jobs == []


def test_repeated_nonempty_page_stops_after_two_requests(monkeypatch):
    asked = []

    def response(url):
        asked.append(url)
        if len(asked) > 2:
            pytest.fail("No-progress pagination must stop before requesting the same offset again")
        return page(3, ROWS)

    monkeypatch.setattr(providers.fetch, "_get_text", response)
    with pytest.raises(providers.Incomplete):
        reader.successfactors(TOKEN, "Epiroc")
    assert len(asked) == 2
    assert asked[0].endswith("startrow=0")
    assert asked[1].endswith("startrow=2")


def test_initial_page_404_still_means_missing(monkeypatch):
    def missing(url):
        raise providers.BoardNotFound(url)

    monkeypatch.setattr(providers.fetch, "_get_text", missing)
    result = board_read()
    assert result.status is ReadStatus.MISSING
    assert result.jobs == []


def test_complete_empty_remains_success(monkeypatch):
    monkeypatch.setattr(providers.fetch, "_get_text", lambda url: page(0, []))
    result = board_read()
    assert result.status is ReadStatus.OK
    assert result.jobs == []


@pytest.mark.parametrize("offset", [0, 2])
def test_timeout_is_failed_not_complete_or_missing(monkeypatch, offset):
    def response(url):
        if url.endswith(f"startrow={offset}"):
            raise TimeoutError("page timed out")
        return page(3, ROWS)

    monkeypatch.setattr(providers.fetch, "_get_text", response)
    result = board_read()
    assert result.status is ReadStatus.FAILED
    assert result.reason == "timeout"
    assert result.jobs == []


def test_partial_overlap_then_empty_remains_incomplete(monkeypatch):
    pages = iter([page(3, ROWS[:1]), page(3, ROWS), page(3, [])])
    monkeypatch.setattr(providers.fetch, "_get_text", lambda url: next(pages))
    result = board_read()
    assert result.status is ReadStatus.FAILED
    assert result.reason == "incomplete"
    assert result.jobs == []


def test_overlap_that_reaches_every_counted_posting_remains_complete(monkeypatch):
    pages = iter([page(2, ROWS[:1]), page(2, ROWS)])
    asked, paced = [], []

    def response(url):
        asked.append(url)
        return next(pages)

    monkeypatch.setattr(providers.fetch, "_get_text", response)
    jobs = reader.successfactors(TOKEN, "Epiroc", pace=paced.append)
    assert len(jobs) == 2
    assert len({job.apply_url for job in jobs}) == 2
    assert asked[1].endswith("startrow=1")
    assert paced == asked[1:]
