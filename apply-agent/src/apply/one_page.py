"""The job site as one Application sees it (apply.claude_fill used to hold it): here so the Student build, which
has no Claude fill, keeps it for the Fillers whose form stays open throughout (apply.build)."""

from contextlib import ExitStack, contextmanager
from typing import Self

from playwright.sync_api import Page

from apply.adapters import JobSite


class OnePage:
    """The job site as one Application sees it: the form opens once, and every open() gives that same page,
    closed when the Application ends (Claude fill, and a Filler whose form stays open throughout)."""

    def __init__(self, site: JobSite):
        self._site = site
        self._stack = ExitStack()
        self._page: Page | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self._stack.close()

    def fetch(self, url: str, body: bytes | None = None) -> bytes:
        return self._site.fetch(url, body)

    @contextmanager
    def open(self, url: str):
        if self._page is None:
            self._page = self._stack.enter_context(self._site.open(url))
        yield self._page
