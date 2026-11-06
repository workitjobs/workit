"""Replay KAN-722's real incomplete reads; do not turn count gaps into closures."""

import json
from pathlib import Path

import pytest

from workit_scraper import providers
from workit_scraper.providers.systems import oracle as reader

CAPTURE = json.loads(
    (Path(__file__).parent / "fixtures/providers/oracle-incomplete.json").read_text()
)


@pytest.mark.parametrize(
    "run", CAPTURE["runs"], ids=lambda run: f"{run['token']}-{run['page_size']}"
)
def test_captured_count_gaps_remain_incomplete(monkeypatch, run):
    """Both live page sizes produced the same gap, with real IDs and totals."""
    pages = {page["offset"]: page for page in run["pages"]}
    asked = []
    paced = []

    def replay(url):
        offset = int(url.rsplit("offset=", 1)[1])
        asked.append(offset)
        page = pages[offset]
        return {
            "items": [
                {
                    "TotalJobsCount": page["total"],
                    "requisitionList": [{"Id": job_id} for job_id in page["ids"]],
                }
            ]
        }

    monkeypatch.setattr(reader, "ORACLE_PAGE", run["page_size"])
    monkeypatch.setattr(providers.fetch, "_get_json", replay)
    with pytest.raises(providers.Incomplete) as error:
        reader.oracle(run["token"], "Captured employer", pace=paced.append)
    assert str(error.value) == run["error"]
    assert asked == list(pages)
    assert len(paced) == len(pages) - 1


@pytest.mark.parametrize("empty", [{"items": []}, {"items": [{"TotalJobsCount": 0}]}])
def test_existing_complete_empty_contract(monkeypatch, empty):
    monkeypatch.setattr(providers.fetch, "_get_json", lambda url: empty)
    assert reader.oracle("example/CX", "Example") == []


@pytest.mark.parametrize("offset", [0, 2])
def test_timeout_never_returns_a_complete_or_empty_board(monkeypatch, offset):
    monkeypatch.setattr(reader, "ORACLE_PAGE", 2)

    def response(url):
        if url.endswith(f"offset={offset}"):
            raise TimeoutError("captured transport failure shape")
        return {"items": [{"TotalJobsCount": 3, "requisitionList": [{"Id": "1"}, {"Id": "2"}]}]}

    monkeypatch.setattr(providers.fetch, "_get_json", response)
    with pytest.raises(TimeoutError):
        reader.oracle("example/CX", "Example")


def test_initial_missing_board_remains_distinct_from_later_missing_page(monkeypatch):
    def missing(url):
        raise providers.BoardNotFound(url)

    monkeypatch.setattr(providers.fetch, "_get_json", missing)
    with pytest.raises(providers.BoardNotFound):
        reader.oracle("example/CX", "Example")
