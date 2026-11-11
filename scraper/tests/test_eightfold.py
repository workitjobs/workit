"""Eightfold AI reader and page reader: real response shapes, pagination, empty
boards, missing first page and the apply_link pattern.

Each fixture in ``fixtures/providers/`` is a trimmed Eightfold API response.
Where a test pages, the page size is shrunk, never the data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workit_scraper import providers
from workit_scraper.providers.model import BoardNotFound, Incomplete
from workit_scraper.providers.systems.eightfold import EIGHTFOLD_PAGE

FIXTURES = Path(__file__).parent / "fixtures" / "providers"


def fixture(name: str) -> object:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return json.loads(text)


class TestEightfold:
    def test_the_list_reads_postings_with_all_fields(self, monkeypatch) -> None:
        asked: list[str] = []
        payload = fixture("eightfold-search.json")
        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: asked.append(url) or payload
        )
        jobs = providers.eightfold("testco/example.com", "Test Co")
        assert len(asked) == 1
        assert "start=0" in asked[0]
        assert len(jobs) == 3

        first = jobs[0]
        assert first.title == "Software Engineering Intern - Summer 2027"
        assert first.external_id == "10001"
        assert "testco.eightfold.ai" in first.apply_url
        assert "domain=example.com" in first.apply_url
        assert first.location == "Boise, ID, US"
        assert first.department == "Engineering"
        assert first.posted_at is not None
        assert first.work_style == "Hybrid"
        assert first.page is None

    def test_location_falls_back_to_standardized(self, monkeypatch) -> None:
        """Empty locations list -> first standardizedLocations entry."""
        payload = fixture("eightfold-search.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.eightfold("testco/example.com", "Test Co")
        second = jobs[1]
        assert second.location == "San Jose, California, United States"

    def test_multiple_locations_joined(self, monkeypatch) -> None:
        payload = fixture("eightfold-search.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.eightfold("testco/example.com", "Test Co")
        third = jobs[2]
        assert third.location == "Austin, TX, US; San Jose, CA, US"

    def test_work_styles_mapped(self, monkeypatch) -> None:
        payload = fixture("eightfold-search.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: payload)
        jobs = providers.eightfold("testco/example.com", "Test Co")
        assert jobs[0].work_style == "Hybrid"
        assert jobs[1].work_style == "Remote"
        assert jobs[2].work_style == "On site"

    def test_pagination_across_two_pages(self, monkeypatch) -> None:
        full = fixture("eightfold-search.json")
        page1 = {
            "status": "OK",
            "data": {"count": 3, "positions": full["data"]["positions"][:2]},
        }
        page2 = {
            "status": "OK",
            "data": {"count": 3, "positions": full["data"]["positions"][2:]},
        }
        pages = iter([page1, page2])
        asked: list[str] = []
        paced: list[str] = []

        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: asked.append(url) or next(pages)
        )
        monkeypatch.setattr(
            "workit_scraper.providers.systems.eightfold.EIGHTFOLD_PAGE", 2
        )
        jobs = providers.eightfold(
            "testco/example.com", "Test Co", pace=paced.append
        )
        assert len(jobs) == 3
        assert len(asked) == 2
        assert "start=0" in asked[0]
        assert "start=2" in asked[1]
        # Pace called before the second page, not the first.
        assert len(paced) == 1

    def test_empty_board_returns_no_jobs(self, monkeypatch) -> None:
        monkeypatch.setattr(
            providers.fetch,
            "_get_json",
            lambda url: {"status": "OK", "data": {"count": 0, "positions": []}},
        )
        jobs = providers.eightfold("testco/example.com", "Test Co")
        assert jobs == []

    def test_missing_data_raises_board_not_found(self, monkeypatch) -> None:
        monkeypatch.setattr(
            providers.fetch, "_get_json", lambda url: {"status": "ERROR"}
        )
        with pytest.raises(BoardNotFound):
            providers.eightfold("testco/example.com", "Test Co")

    def test_missing_count_raises_board_not_found(self, monkeypatch) -> None:
        monkeypatch.setattr(
            providers.fetch,
            "_get_json",
            lambda url: {"status": "OK", "data": {"positions": []}},
        )
        with pytest.raises(BoardNotFound):
            providers.eightfold("testco/example.com", "Test Co")


class TestDescribeEightfold:
    def test_description_and_facts_from_detail(self, monkeypatch, swap_provider) -> None:
        detail = fixture("eightfold-detail.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: detail)
        job = providers.Job(
            ats="eightfold",
            token="testco/example.com",
            company="Test Co",
            external_id="10001",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://testco.eightfold.ai/careers/job?domain=example.com&pid=10001",
            location="Boise, ID, US",
            work_style="Hybrid",
        )
        result = providers.describe_eightfold(job)
        assert result.page is not None
        assert "12-week summer internship" in (result.description or "")
        assert "Currently pursuing" in (result.description or "")

    def test_work_style_carried_from_list(self, monkeypatch, swap_provider) -> None:
        detail = fixture("eightfold-detail.json")
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: detail)
        job = providers.Job(
            ats="eightfold",
            token="testco/example.com",
            company="Test Co",
            external_id="10001",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://testco.eightfold.ai/careers/job?domain=example.com&pid=10001",
            location="Boise, ID, US",
            work_style="Hybrid",
        )
        result = providers.describe_eightfold(job)
        assert result.facts.work_style == "Hybrid"

    def test_no_description_gives_none(self, monkeypatch, swap_provider) -> None:
        detail = {"status": "OK", "data": {}}
        monkeypatch.setattr(providers.fetch, "_get_json", lambda url: detail)
        job = providers.Job(
            ats="eightfold",
            token="testco/example.com",
            company="Test Co",
            external_id="10001",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://testco.eightfold.ai/careers/job?domain=example.com&pid=10001",
        )
        result = providers.describe_eightfold(job)
        assert result.page is not None
        assert result.description is None


class TestProviderRecord:
    def test_apply_link_matches_url_with_domain(self) -> None:
        pattern = providers.PROVIDERS["eightfold"].apply_link
        url = "//micron.eightfold.ai/careers/job?domain=micron.com&pid=123"
        m = pattern.search(url)
        assert m
        assert m.group(1) == "micron"
        assert m.group(2) == "micron.com"

    def test_apply_link_rejects_url_without_domain(self) -> None:
        pattern = providers.PROVIDERS["eightfold"].apply_link
        url = "//micron.eightfold.ai/careers/job?pid=123"
        assert pattern.search(url) is None

    def test_paged_is_set(self) -> None:
        assert providers.PROVIDERS["eightfold"].paged is True

    def test_subdomains_is_set(self) -> None:
        assert providers.PROVIDERS["eightfold"].subdomains == "eightfold.ai"

    def test_skip_robots_is_not_set(self) -> None:
        assert providers.PROVIDERS["eightfold"].skip_robots is False
