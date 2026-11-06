"""Jibe pagination failures must not turn an existing board into absence evidence."""

import json
from pathlib import Path

import pytest

from workit_scraper import providers
from workit_scraper.board_read import ReadStatus, read_board
from workit_scraper.providers.systems import jibe as reader


class AllowedRobots:
    def allows(self, url):
        return True

    def pace(self, url):
        pass


def first_page():
    payload = json.loads(
        (Path(__file__).parent / "fixtures/providers/icims-jibe-list.json").read_text()
    )
    payload["totalCount"] = 3
    return payload


def test_captured_ies_board_is_complete_and_paces_every_later_page(monkeypatch):
    capture = json.loads(
        (Path(__file__).parent / "fixtures/providers/jibe-ies-complete.json").read_text()
    )
    asked, paced = [], []

    def response(url):
        asked.append(url)
        number = int(url.split("page=", 1)[1].split("&", 1)[0])
        return capture["pages"][number - 1]

    monkeypatch.setattr(providers.fetch, "_get_json", response)
    jobs = reader.jibe(capture["token"], "IES", pace=paced.append)
    ids = [row["data"]["slug"] for page in capture["pages"] for row in page["jobs"]]
    assert len(jobs) == len(set(ids)) == 753
    assert [job.external_id for job in jobs] == ids
    assert len(asked) == 8
    assert paced == asked[1:]


def test_later_page_404_is_failed_not_missing(monkeypatch):
    monkeypatch.setattr(reader, "JIBE_PAGE", 2)

    def response(url):
        if "page=1&" in url:
            return first_page()
        raise providers.BoardNotFound(url)

    monkeypatch.setattr(providers.fetch, "_get_json", response)
    result = read_board(providers.Board("jibe", "joinus.ies-co.com", "IES"), AllowedRobots())
    assert result.status is ReadStatus.FAILED
    assert result.reason == "incomplete"
    assert isinstance(result.error, providers.Incomplete)
    assert result.jobs == []


def test_initial_page_404_still_means_missing(monkeypatch):
    def missing(url):
        raise providers.BoardNotFound(url)

    monkeypatch.setattr(providers.fetch, "_get_json", missing)
    result = read_board(providers.Board("jibe", "joinus.ies-co.com", "IES"), AllowedRobots())
    assert result.status is ReadStatus.MISSING
    assert result.jobs == []


def test_complete_empty_is_success(monkeypatch):
    monkeypatch.setattr(providers.fetch, "_get_json", lambda url: {"totalCount": 0, "jobs": []})
    result = read_board(providers.Board("jibe", "joinus.ies-co.com", "IES"), AllowedRobots())
    assert result.status is ReadStatus.OK
    assert result.jobs == []


@pytest.mark.parametrize("failure", ["short", "timeout"])
def test_partial_and_failed_reads_return_no_closure_evidence(monkeypatch, failure):
    monkeypatch.setattr(reader, "JIBE_PAGE", 2)

    def response(url):
        if "page=1&" in url:
            return first_page()
        if failure == "timeout":
            raise TimeoutError("page timed out")
        return {"totalCount": 3, "jobs": []}

    monkeypatch.setattr(providers.fetch, "_get_json", response)
    result = read_board(providers.Board("jibe", "joinus.ies-co.com", "IES"), AllowedRobots())
    assert result.status is ReadStatus.FAILED
    assert result.reason == ("timeout" if failure == "timeout" else "incomplete")
    assert result.jobs == []
