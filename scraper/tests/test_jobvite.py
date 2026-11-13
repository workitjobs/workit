"""Jobvite reader and page reader: real response shapes, empty boards, JSON-LD
detail parsing and the apply_link pattern.

Each fixture in ``fixtures/providers/`` is a trimmed Jobvite response.
"""

from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

from workit_scraper import providers
from workit_scraper.providers.model import BoardNotFound

FIXTURES = Path(__file__).parent / "fixtures" / "providers"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestJobvite:
    def test_the_list_reads_postings_with_all_fields(self, monkeypatch) -> None:
        asked: list[str] = []
        html = fixture_text("jobvite-list.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: asked.append(url) or html)
        jobs = providers.jobvite("examplecorp", "Example Corp")
        assert len(asked) == 1
        assert "jobs.jobvite.com/examplecorp" in asked[0]
        assert len(jobs) == 3

        first = jobs[0]
        assert first.title == "Software Engineering Intern (Summer 2027)"
        assert first.external_id == "oABC1234"
        assert first.apply_url == "https://jobs.jobvite.com/examplecorp/job/oABC1234"
        assert first.location == "Chicago, Illinois"
        assert first.page is None

    def test_multi_location_is_none(self, monkeypatch) -> None:
        html = fixture_text("jobvite-list.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: html)
        jobs = providers.jobvite("examplecorp", "Example Corp")
        second = jobs[1]
        assert second.location is None

    def test_remote_location(self, monkeypatch) -> None:
        html = fixture_text("jobvite-list.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: html)
        jobs = providers.jobvite("examplecorp", "Example Corp")
        third = jobs[2]
        assert third.location == "Remote"

    def test_empty_board_returns_no_jobs(self, monkeypatch) -> None:
        monkeypatch.setattr(
            providers.fetch,
            "_get_text",
            lambda url: "<html><body><table class='jv-job-list'></table></body></html>",
        )
        jobs = providers.jobvite("empty", "Empty Corp")
        assert jobs == []

    def test_missing_board_raises_board_not_found(self, monkeypatch) -> None:
        def raise_redirect(url):
            raise urllib.error.HTTPError(
                "https://search.jobvite.com?invalid=1",
                302,
                "refused cross-origin redirect",
                {},
                None,
            )

        monkeypatch.setattr(providers.fetch, "_get_text", raise_redirect)
        with pytest.raises(BoardNotFound):
            providers.jobvite("nosuch", "No Such Corp")

    def test_deduplicates_by_id(self, monkeypatch) -> None:
        """A job ID appearing twice in the HTML is kept once."""
        html = fixture_text("jobvite-list.html")
        doubled = html + html
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: doubled)
        jobs = providers.jobvite("examplecorp", "Example Corp")
        assert len(jobs) == 3


class TestDescribeJobvite:
    def test_description_and_facts_from_detail(self, monkeypatch, swap_provider) -> None:
        html = fixture_text("jobvite-detail.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: html)
        job = providers.Job(
            ats="jobvite",
            token="examplecorp",
            company="Example Corp",
            external_id="oABC1234",
            title="Software Engineering Intern (Summer 2027)",
            apply_url="https://jobs.jobvite.com/examplecorp/job/oABC1234",
            location="Chicago, Illinois",
        )
        result = providers.describe_jobvite(job)
        assert result.page is not None
        assert "12-week paid summer internship" in (result.description or "")
        assert "Currently pursuing" in (result.description or "")
        assert result.posted_at is not None and result.posted_at.startswith("2026-10-15")
        # Pay from baseSalary.
        assert result.facts.pay is not None
        assert result.facts.pay.currency == "USD"
        assert result.facts.pay.low == 25.0
        assert result.facts.pay.high == 40.0
        assert result.facts.pay.period == "hour"

    def test_no_json_ld_gives_empty_page(self, monkeypatch, swap_provider) -> None:
        monkeypatch.setattr(
            providers.fetch, "_get_text", lambda url: "<html><body>No schema</body></html>"
        )
        job = providers.Job(
            ats="jobvite",
            token="examplecorp",
            company="Example Corp",
            external_id="oABC1234",
            title="Software Engineering Intern (Summer 2027)",
            apply_url="https://jobs.jobvite.com/examplecorp/job/oABC1234",
        )
        result = providers.describe_jobvite(job)
        assert result.page is not None
        assert result.description is None

    def test_place_from_json_ld(self, monkeypatch, swap_provider) -> None:
        html = fixture_text("jobvite-detail.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: html)
        job = providers.Job(
            ats="jobvite",
            token="examplecorp",
            company="Example Corp",
            external_id="oABC1234",
            title="Software Engineering Intern (Summer 2027)",
            apply_url="https://jobs.jobvite.com/examplecorp/job/oABC1234",
        )
        result = providers.describe_jobvite(job)
        assert result.page is not None
        assert result.page.offices == ("Chicago, Illinois",)


class TestProviderRecord:
    def test_apply_link_matches(self) -> None:
        pattern = providers.PROVIDERS["jobvite"].apply_link
        m = pattern.search("https://jobs.jobvite.com/tylertech/job/oAVOAfwD?nl=1&fr=false")
        assert m and m.group(1) == "tylertech"

    def test_apply_link_rejects_non_job_path(self) -> None:
        pattern = providers.PROVIDERS["jobvite"].apply_link
        assert pattern.search("https://jobs.jobvite.com/tylertech") is None

    def test_not_paged(self) -> None:
        assert providers.PROVIDERS["jobvite"].paged is False

    def test_has_describe(self) -> None:
        assert providers.PROVIDERS["jobvite"].describe is not None
