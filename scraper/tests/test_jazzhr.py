"""JazzHR reader and page reader: real response shapes, empty boards, JSON-LD
detail parsing and the apply_link pattern.

Each fixture in ``fixtures/providers/`` is a trimmed JazzHR response.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from workit_scraper import providers
from workit_scraper.providers.model import BoardNotFound

FIXTURES = Path(__file__).parent / "fixtures" / "providers"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestJazzHR:
    def test_the_list_reads_postings_with_all_fields(self, monkeypatch) -> None:
        asked: list[str] = []
        html = fixture_text("jazzhr-list.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: asked.append(url) or html)
        jobs = providers.jazzhr("examplecorp", "Example Corp")
        assert len(asked) == 1
        assert "applytojob.com/apply" in asked[0]
        assert len(jobs) == 3

        first = jobs[0]
        assert first.title == "Software Engineering Intern - Summer 2027"
        assert first.external_id == "WpIfUaLo9Q"
        assert (
            first.apply_url
            == "https://examplecorp.applytojob.com/apply/WpIfUaLo9Q/Software-Engineering-Intern"
        )
        assert first.location == "New York, NY"
        assert first.page is None

    def test_remote_location(self, monkeypatch) -> None:
        html = fixture_text("jazzhr-list.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: html)
        jobs = providers.jazzhr("examplecorp", "Example Corp")
        second = jobs[1]
        assert second.location == "Remote"

    def test_empty_board_returns_no_jobs(self, monkeypatch) -> None:
        monkeypatch.setattr(
            providers.fetch,
            "_get_text",
            lambda url: "<html><body>This account is no longer active.</body></html>",
        )
        jobs = providers.jazzhr("inactive", "Inactive Corp")
        assert jobs == []

    def test_missing_board_raises_board_not_found(self, monkeypatch) -> None:
        def raise_404(url):
            raise BoardNotFound(url)

        monkeypatch.setattr(providers.fetch, "_get_text", raise_404)
        with pytest.raises(BoardNotFound):
            providers.jazzhr("nosuch", "No Such Corp")

    def test_deduplicates_by_id(self, monkeypatch) -> None:
        """A job ID appearing twice in the HTML is kept once."""
        html = fixture_text("jazzhr-list.html")
        doubled = html + html
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: doubled)
        jobs = providers.jazzhr("examplecorp", "Example Corp")
        assert len(jobs) == 3


class TestDescribeJazzHR:
    def test_description_and_facts_from_detail(self, monkeypatch, swap_provider) -> None:
        html = fixture_text("jazzhr-detail.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: html)
        job = providers.Job(
            ats="jazzhr",
            token="examplecorp",
            company="Example Corp",
            external_id="WpIfUaLo9Q",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://examplecorp.applytojob.com/apply/WpIfUaLo9Q/Software-Engineering-Intern",
            location="New York, NY",
        )
        result = providers.describe_jazzhr(job)
        assert result.page is not None
        assert "12-week paid summer internship" in (result.description or "")
        assert "Currently pursuing" in (result.description or "")
        assert result.posted_at is not None and result.posted_at.startswith("2026-10-08")
        # Pay from baseSalary.
        assert result.facts.pay is not None
        assert result.facts.pay.currency == "USD"
        assert result.facts.pay.low == 30.0
        assert result.facts.pay.high == 45.0
        assert result.facts.pay.period == "hour"

    def test_no_json_ld_gives_empty_page(self, monkeypatch, swap_provider) -> None:
        monkeypatch.setattr(
            providers.fetch, "_get_text", lambda url: "<html><body>No schema</body></html>"
        )
        job = providers.Job(
            ats="jazzhr",
            token="examplecorp",
            company="Example Corp",
            external_id="WpIfUaLo9Q",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://examplecorp.applytojob.com/apply/WpIfUaLo9Q/Software-Engineering-Intern",
        )
        result = providers.describe_jazzhr(job)
        assert result.page is not None
        assert result.description is None

    def test_place_from_json_ld(self, monkeypatch, swap_provider) -> None:
        html = fixture_text("jazzhr-detail.html")
        monkeypatch.setattr(providers.fetch, "_get_text", lambda url: html)
        job = providers.Job(
            ats="jazzhr",
            token="examplecorp",
            company="Example Corp",
            external_id="WpIfUaLo9Q",
            title="Software Engineering Intern - Summer 2027",
            apply_url="https://examplecorp.applytojob.com/apply/WpIfUaLo9Q/Software-Engineering-Intern",
        )
        result = providers.describe_jazzhr(job)
        assert result.page is not None
        assert result.page.offices == ("New York, NY",)


class TestProviderRecord:
    def test_apply_link_matches(self) -> None:
        pattern = providers.PROVIDERS["jazzhr"].apply_link
        m = pattern.search("https://brennancenter.applytojob.com/apply/WpIfUaLo9Q/Associate-Editor")
        assert m and m.group(1) == "brennancenter"

    def test_subdomains_is_set(self) -> None:
        assert providers.PROVIDERS["jazzhr"].subdomains == "applytojob.com"

    def test_not_paged(self) -> None:
        assert providers.PROVIDERS["jazzhr"].paged is False

    def test_has_describe(self) -> None:
        assert providers.PROVIDERS["jazzhr"].describe is not None
