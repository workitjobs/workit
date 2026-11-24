"""A fake Microsoft Careers (apply.careers.microsoft.com, an Eightfold site, KAN-763): its posting page, and its
apply page, which shows a sign-in window with provider buttons until the applicant is signed in. Hand-written
from the live page's shape in a Trace (2026-11-05, 2026-11-10): the header's "Sign in" button while signed out,
"Account manager for <name>" once signed in, and "Sign in using Google" (Microsoft, LinkedIn, Facebook) in the
window. Served by Playwright routes alone; nothing reaches the network. Implements the JobSite adapter.

With `google` (KAN-878), its Google button's window goes to a fake Google: its account chooser, or with
"consent" Google's Continue after the pick, or a password, passkey or refusal page. Done, the window closes and the
apply page reloads signed in, as Eightfold's does."""

import html
import json
from contextlib import contextmanager
from urllib.parse import parse_qs, quote, urlsplit

from playwright.sync_api import Route, sync_playwright

HOST = "apply.careers.microsoft.com"
URL = f"https://{HOST}/careers/job/1970393557037859"
APPLY = f"https://{HOST}/careers/apply?pid=1970393557037859"
COOKIE = "signed_in"
PROVIDERS = ("Google", "Microsoft", "LinkedIn", "Facebook")
GOOGLE = "https://accounts.google.com"
DONE = f"https://{HOST}/oauth/done"
CHOOSER_SCRIPT = """for (const account of document.querySelectorAll('[data-identifier]'))
  account.onclick = () => { location.href = account.dataset.next; };"""


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
    def __init__(self, google: str | None = None, account: str = "test.person@example.com", scope: str = "openid email profile"):
        """`google`: None (the Google button's window is a bare page), "chooser" (Google's account chooser, then
        back signed in), "consent" (the chooser, then Google's Continue for the site), "password", "passkey" or
        "rejected" (Google asks for more than the pick, or refuses the browser)."""
        self.submissions: list[str] = []
        self.provider_opened: list[str] = []  # each provider sign-in window that opened
        self.google, self.account = google, account
        self.scope = scope  # what the site's OAuth request asks Google for
        self.picked: list[str] = []  # each account picked in Google's chooser
        self.typed: list[str] = []  # anything typed into a Google page: never

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
        if parts.hostname == "accounts.google.com" and self.google:
            return self._google_page(route, parts)
        if parts.hostname != HOST:
            return route.abort()
        if parts.path == "/oauth/done":  # back from Google: the site signs in, closes the window, reloads its page
            return route.fulfill(content_type="text/html", headers={"set-cookie": f"{COOKIE}=1; Path=/"},
                                 body="<script>opener && opener.location.reload(); window.close();</script>")
        signed_in = f"{COOKIE}=1" in (request.headers.get("cookie") or "")
        if parts.path.startswith("/oauth/"):
            self.provider_opened.append(parts.path)
            if parts.path == "/oauth/google" and self.google:
                chooser = f"{GOOGLE}/v3/signin/accountchooser?continue={quote(DONE)}&scope={quote(self.scope)}"
                if self.google == "granted":  # the app's earlier grants come with it, unseen
                    chooser += "&include_granted_scopes=true"
                if self.google == "straight":  # a login_hint: Google goes straight to its consent, scopes hidden
                    chooser = f"{GOOGLE}/signin/oauth/v2/consentsummary?part=opaque&continue={quote(DONE)}"
                return route.fulfill(content_type="text/html", body=f"<script>location.replace({json.dumps(chooser)})</script>")
            return route.fulfill(content_type="text/html", body="<p>Provider sign-in</p>")
        if parts.path == "/api/apply":
            self.submissions.append(request.post_data or "")
            return route.fulfill(json={})
        if parts.path.startswith("/careers/job/"):
            return route.fulfill(content_type="text/html", body=_page(POSTING, signed_in))
        if parts.path == "/careers/apply":
            return route.fulfill(content_type="text/html", body=_page(FORM if signed_in else SIGN_IN, signed_in))
        route.abort()

    def _google_page(self, route: Route, parts) -> None:
        page = lambda body: route.fulfill(content_type="text/html",
                                          body=f"<!doctype html><meta charset='utf-8'><body>{body}</body>")
        if route.request.method == "POST":
            self.typed.append(route.request.post_data or "")
            return route.abort()
        if parts.path == "/v3/signin/accountchooser":
            after = {"password": f"{GOOGLE}/v3/signin/challenge/pwd", "passkey": f"{GOOGLE}/v3/signin/challenge/pk",
                     "rejected": f"{GOOGLE}/v3/signin/rejected",
                     "consent": f"{GOOGLE}/signin/oauth/id?continue={quote(DONE)}"}.get(self.google, DONE)
            account = html.escape(self.account)
            return page(f'<h1>Choose an account</h1><ul><li><div role="link" tabindex="0" data-identifier="{account}" '
                        f'data-next="{html.escape(after)}" onmousedown="window.picked = 1">'
                        f"<div>Test Person</div><div>{account}</div></div></li>"
                        '<li><div role="link">Use another account</div></li></ul>'
                        f"<script>{CHOOSER_SCRIPT}; for (const a of document.querySelectorAll('[data-identifier]')) "
                        "a.addEventListener('click', () => fetch('/picked?' + a.dataset.identifier));</script>")
        if parts.path == "/picked":
            self.picked.append(parts.query)
            return route.fulfill(body="")
        if parts.path in ("/signin/oauth/id", "/signin/oauth/v2/consentsummary"):
            done = parse_qs(parts.query)["continue"][0]
            return page(f"<h1>Sign in to Microsoft Careers</h1><p>Google will share your name and email.</p>"
                        f"<button onclick='location.href={json.dumps(done)}'>Continue</button><button>Cancel</button>")
        if parts.path == "/v3/signin/challenge/pwd":
            return page('<h1>Welcome</h1><form method=post><input type="password" name="Passwd" aria-label="Enter your password"></form>')
        if parts.path == "/v3/signin/challenge/pk":
            return page("<h1>Welcome</h1><p>Complete sign-in using your passkey</p><button>Try another way</button>")
        if parts.path == "/v3/signin/rejected":
            return page("<h1>Couldn't sign you in</h1><p>This browser or app may not be secure.</p><button>Try again</button>")
        route.abort()


def sign_in(page) -> None:
    """The applicant signs in himself, in the provider's window; then Eightfold reloads its apply page."""
    page.context.add_cookies([{"name": COOKIE, "value": "1", "domain": HOST, "path": "/"}])
    page.reload()

