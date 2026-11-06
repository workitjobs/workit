"""Discovery measurements cannot count missing evidence or bypass request caps."""

from types import SimpleNamespace

import pytest

import pilot_greenhouse as pilot
from workit_scraper import providers, web
from workit_scraper.board_read import BoardRead, ReadStatus


class Robots:
    def allows(self, url):
        return True

    def pace(self, url):
        pass


def setup(monkeypatch, *, name="Employer", description="An internship."):
    def read(board, robots):
        web.get("https://example.test", timeout=25)
        return BoardRead(
            ReadStatus.OK,
            jobs=[
                providers.Job("greenhouse", board.token, "Employer", "1", "Intern", "https://a/1")
            ],
        )

    monkeypatch.setattr(pilot, "read_board", read)
    monkeypatch.setattr(pilot, "reported_name", lambda *args: name)
    monkeypatch.setattr(web, "get", lambda *args, **kwargs: b"{}")
    monkeypatch.setattr(
        providers,
        "describe",
        lambda job: SimpleNamespace(description=description, apply_url=job.apply_url),
    )
    monkeypatch.setattr(pilot.shortlist, "pick", lambda jobs, **kwargs: jobs)


def test_global_dedup_and_existing_feed_overlap(monkeypatch):
    setup(monkeypatch)
    result = pilot.run(["one", "two"], set(), Robots())
    assert result["new_urls"] == ["https://a/1"]
    assert result["boards"][1]["new_urls"] == []
    result = pilot.run(["one"], {"https://a/1"}, Robots())
    assert result["new_urls"] == []
    assert result["boards"][0]["existing_feed_overlap"] == 1


@pytest.mark.parametrize("name,description", [(None, "Internship"), ("Employer", "")])
def test_missing_name_or_description_never_counts(monkeypatch, name, description):
    setup(monkeypatch, name=name, description=description)
    result = pilot.run(["one"], set(), Robots())
    assert result["qualifying_urls"] == result["new_urls"] == []


def test_request_cap_defers_work_and_restores_get(monkeypatch):
    setup(monkeypatch)
    original = web.get
    monkeypatch.setattr(pilot, "MAX_REQUESTS", 1)
    result = pilot.run(["one", "two"], set(), Robots())
    assert result["requests"] == 1
    assert result["boards"][0]["detail_deferred"] == 1
    assert result["boards"][1]["status"] == "deferred"
    assert web.get is original


@pytest.mark.parametrize("tokens", [[], ["a", "a"], ["../a"], ["a"] * 21])
def test_bad_manifest_rejected(tokens):
    with pytest.raises(ValueError):
        pilot.tokens_from({"provider": "greenhouse", "tokens": tokens})
