import urllib.error

import pytest

from workit_scraper import web


class _Response:
    def __init__(self, data: bytes = b"abc"):
        self._data = data
        self._pos = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, size: int = -1):
        if size < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk


def test_stats_count_failed_requests_but_not_their_bytes(monkeypatch):
    def refuse(request, *, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

    before = web.stats()
    monkeypatch.setattr(web._OPENER, "open", refuse)
    with pytest.raises(urllib.error.HTTPError):
        web.get("https://boards.example.com/a", timeout=3)
    with pytest.raises(urllib.error.HTTPError):
        web.post("https://boards.example.com/b", {}, timeout=3)
    monkeypatch.setattr(web._OPENER, "open", lambda request, *, timeout: _Response())
    web.get("https://boards.example.com/c", timeout=3)

    after = web.stats()
    assert after["requests"] - before["requests"] == 3
    assert after["received_bytes"] - before["received_bytes"] == 3


def test_body_over_max_raises(monkeypatch):
    monkeypatch.setattr(web, "MAX_BODY", 100)
    monkeypatch.setattr(web._OPENER, "open", lambda req, *, timeout: _Response(b"x" * 101))
    with pytest.raises(ValueError, match="exceeds"):
        web.get("https://boards.example.com/huge", timeout=3)
