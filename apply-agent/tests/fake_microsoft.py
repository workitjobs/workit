"""A fake Microsoft Careers (apply.careers.microsoft.com, an Eightfold site, KAN-763): its posting page, and its
apply page, which shows a sign-in window with provider buttons until the applicant is signed in. Hand-written
from the live page's shape in a Trace (2026-11-05, 2026-11-10): the header's "Sign in" button while signed out,
"Account manager for <name>" once signed in, and "Sign in using Google" (Microsoft, LinkedIn, Facebook) in the
window. Served by Playwright routes alone; nothing reaches the network. Implements the JobSite adapter."""

from contextlib import contextmanager
from urllib.parse import urlsplit

from playwright.sync_api import Route, sync_playwright

HOST = "apply.careers.microsoft.com"
URL = f"https://{HOST}/careers/job/1970393557037859"
APPLY = f"https://{HOST}/careers/apply?pid=1970393557037859"
COOKIE = "signed_in"
PROVIDERS = ("Google", "Microsoft", "LinkedIn", "Facebook")


def _header(signed_in: bool) -> str:
    menu = ('<button aria-label="Account manager for Test Person">TP</button>' if signed_in
            else "<button>Sign in</button>")
    return f'<header role="banner"><a href="https://careers.microsoft.com/">Careers</a>{menu}</header>'


def _page(body: str, signed_in: bool) -> str:
    return (f"<!doctype html><html><head><title>Software Engineer Intern | Microsoft Careers</title></head>"
            f"<body>{_header(signed_in)}<main>{body}</main></body></html>")


POSTING = ("<h1>Software Engineer Intern</h1><p>Microsoft. Build things with us.</p>"
           "<button onclick=\"location.href='/careers/apply?pid=1970393557037859'\">Apply now</button>")
# Each provider's button opens its own sign-in window, as Eightfold's does: Apply never presses one.
SIGN_IN = ('<div role="dialog" aria-modal="true" aria-label="Sign in"><h2>Sign in to apply</h2>' + "".join(
    f'<button class="candidateAuth{p}LoginButton" onclick="window.open(\'/oauth/{p.lower()}\')">'
    f'<span class="sign-in-text">Sign in using {p}</span></button>' for p in PROVIDERS) + "</div>")
FORM = ("<h1>Apply: Software Engineer Intern</h1><form onsubmit=\"event.preventDefault(); fetch('/api/apply', "
        "{method: 'POST', body: new FormData(this)})\">"
        '<label>First Name <input name="first"></label><label>Last Name <input name="last"></label>'
        '<label>Email <input name="email" type="email"></label><button>Submit application</button></form>')


class FakeMicrosoftServer:
    def __init__(self):
        self.submissions: list[str] = []
        self.provider_opened: list[str] = []  # each provider sign-in window that opened: never by Apply

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def fetch(self, url: str, body: bytes | None = None) -> bytes:
        raise LookupError(f"fake Microsoft Careers has no API: {url}")

    @contextmanager
    def open(self, url: str, worker: int = 0):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(service_workers="block")
            context.route("**/*", self._handle)
            try:
                page = context.new_page()
                page.goto(url)
                yield page
            finally:
                browser.close()

    def _handle(self, route: Route) -> None:
        request, parts = route.request, urlsplit(route.request.url)
        if parts.hostname != HOST:
            return route.abort()
        signed_in = f"{COOKIE}=1" in (request.headers.get("cookie") or "")
        if parts.path.startswith("/oauth/"):
            self.provider_opened.append(parts.path)
            return route.fulfill(content_type="text/html", body="<p>Provider sign-in</p>")
        if parts.path == "/api/apply":
            self.submissions.append(request.post_data or "")
            return route.fulfill(json={})
        if parts.path.startswith("/careers/job/"):
            return route.fulfill(content_type="text/html", body=_page(POSTING, signed_in))
        if parts.path == "/careers/apply":
            return route.fulfill(content_type="text/html", body=_page(FORM if signed_in else SIGN_IN, signed_in))
        route.abort()


def sign_in(page) -> None:
    """The applicant signs in himself, in the provider's window; then Eightfold reloads its apply page."""
    page.context.add_cookies([{"name": COOKIE, "value": "1", "domain": HOST, "path": "/"}])
    page.reload()
