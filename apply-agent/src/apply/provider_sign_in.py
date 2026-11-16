"""A sign-in with a provider (Google, Microsoft, LinkedIn, Facebook) in the way of a form that Claude fill reads
(KAN-763). Microsoft Careers (apply.careers.microsoft.com, an Eightfold site) opens one on Apply now: a window
that offers "Sign in using Google" and the others, and the form opens only to a signed-in applicant.

Where it offers Google and the policy says so (`provider_sign_in: google`, KAN-878), plain code signs in with
Google (`with_google`): it presses the site's Google button and, in Google's account chooser, the applicant's own
account, as Workday's Google sign-in does (apply.google_sign_in). It never types into a sign-in and never handles a
password. Any other provider, a Google page that asks for more than the pick, and a sign-in that doesn't come back
within GOOGLE_WAIT_S are the applicant's: `shows` makes Claude fill's stop there a Needs sign-in pause, and
`signed_in` lets that pause go on by itself once the provider sign-in is gone and the site's account menu shows
(rehearsal's KAN-670 check), as Oracle's and Workday's sign-in pauses do.
"""

import re
import time
from urllib.parse import unquote

from playwright.sync_api import Locator, Page

from apply import google_sign_in
from apply.accounts import NEEDS_SIGN_IN
from apply.model import Handoff

# One read of the page's visible buttons and links: the providers a sign-in offers, and whether an account menu shows.
# A provider button is named "Sign in using Google" (Microsoft's) or the like, or has Eightfold's own class for it
# (candidateAuthGoogleLoginButton). The account menu is Eightfold's "Account manager for <name>" button, or a
# "Sign out". Microsoft's header shows a "Sign in" button there while signed out (its trace, 2026-11-05).
READ = r"""() => {
  const providers = /^(?:sign in|sign up|log in|continue)\s+(?:using|with)\s+(google|microsoft|linkedin|facebook|apple)$/i;
  const account = /^(?:account manager\b|sign out$|log out$)/i;
  const seen = el => {
    const box = el.getBoundingClientRect(), style = getComputedStyle(el);
    return box.width > 0 && box.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const name = el => (el.getAttribute('aria-label') || el.innerText || '').replace(/\s+/g, ' ').trim();
  const found = [], menu = [];
  for (const el of document.querySelectorAll('button, a, [role=button], [class*=candidateAuth][class*=LoginButton]')) {
    if (!seen(el)) continue;
    const named = name(el).match(providers) || String(el.className).match(/candidateAuth(\w+?)LoginButton/);
    if (named) found.push(named[1][0].toUpperCase() + named[1].slice(1).toLowerCase());
    if (account.test(name(el))) menu.push(true);
  }
  return {providers: [...new Set(found)], account: menu.length > 0};
}"""
NAMES = {"Linkedin": "LinkedIn"}
HANDOFF = (NEEDS_SIGN_IN + "{site} asks you to sign in ({providers}) before its form opens. Sign in on the page "
           "yourself: Apply goes on by itself once you have, and never presses a sign-in button for you.")


def _read(page: Page) -> dict:
    return page.evaluate(READ)


def shows(page: Page) -> list[str]:
    """The providers a sign-in on the page offers ([] when none shows)."""
    try:
        return [NAMES.get(p, p) for p in _read(page)["providers"]]
    except Exception:
        return []  # the page navigating: no sign-in seen


def handoff(providers: list[str], site: str) -> str:
    """A Needs sign-in Handoff's reason, naming the site and what its sign-in offers."""
    return HANDOFF.format(site=site, providers=", ".join(providers))


def signed_in(page: Page) -> bool:
    """Whether the page is past the provider sign-in: none shows, and the site's account menu does."""
    read = _read(page)
    return not read["providers"] and bool(read["account"])


GOOGLE_WAIT_S = 60.0  # for the site to come back signed in from Google, as Workday's GOOGLE_WAIT
# Its whole name says it signs in with Google ("Sign in using Google"), or it has Eightfold's own class for it.
GOOGLE_NAME = re.compile(r"^\s*(?:sign in|sign up|log in|continue)\s+(?:using|with)\s+google\s*$", re.IGNORECASE)
GOOGLE_CLASS = "[class*=candidateAuthGoogleLoginButton]"
# Google's consent for this site ("Sign in to <site>" with Continue), shown once per site: its Continue only.
CONSENT = re.compile(r"^\s*continue\s*$", re.IGNORECASE)
NOT_BACK = (NEEDS_SIGN_IN + "{site} didn't come back signed in from Sign in with Google within {seconds:.0f} s. Sign in on "
            "the page yourself: Apply goes on by itself once you have.")
NO_BUTTON = (NEEDS_SIGN_IN + "{site} offers Sign in with Google, but Apply found {found} button for it. Sign in on the "
             "page yourself: Apply goes on by itself once you have.")
IN_A_FORM = (NEEDS_SIGN_IN + "{site}'s Sign in with Google would submit a form, so Apply didn't press it. Sign in on "
             "the page yourself: Apply goes on by itself once you have.")
# Whether a press of it would submit a form: a submit button of one (a <button> of no type, an <input type=submit>).
# A real Sign in with Google is a link or a button of type=button; one that submits could send the application.
# It is, sits in or holds a form's submit button, or is a label for one (a click on a label clicks its control).
SUBMITS = """el => {
  const sub = (b) => !!b && !!b.form && (b.tagName === 'BUTTON'
    ? (b.getAttribute('type') || 'submit').toLowerCase() === 'submit' : /^(submit|image)$/i.test(b.type || ''));
  const lab = (l) => !!l && sub(l.control);
  return sub(el.closest('button, input')) || lab(el.closest('label'))
    || [...el.querySelectorAll('button, input')].some(sub) || [...el.querySelectorAll('label')].some(lab);
}"""
# What a sign-in with Google may share: the applicant's name and email, nothing more (KAN-878's review: a page's
# Google button can open any app's OAuth request, such as one for Drive).
BASIC_SCOPES = frozenset({"openid", "email", "profile", "https://www.googleapis.com/auth/userinfo.email",
                          "https://www.googleapis.com/auth/userinfo.profile"})
SCOPE = re.compile(r"[?&#]scope=([^&#]+)")
MORE_THAN_SIGN_IN = (NEEDS_SIGN_IN + "{site}'s Sign in with Google asks Google for more than your name and email ({scopes}), "
                     "so Apply didn't go on. Sign in on the page yourself if you mean to.")
UNKNOWN_SCOPE = (NEEDS_SIGN_IN + "{site}'s Sign in with Google didn't say what it asks Google for, so Apply didn't pick "
                 "your account. Sign in on the page yourself: Apply goes on by itself once you have.")
A_FRAME = (NEEDS_SIGN_IN + "{site}'s Sign in with Google holds a frame, where Apply's press could land on another "
           "form. Sign in on the page yourself: Apply goes on by itself once you have.")


def google_button(page: Page) -> list[Locator]:
    """The visible Sign in with Google buttons and links on the page."""
    found = [el for role in ("button", "link") for el in page.get_by_role(role, name=GOOGLE_NAME).all() if el.is_visible()]
    found += [el for el in page.locator(GOOGLE_CLASS).all() if el.is_visible()]
    return found


def scopes(url: str) -> set[str] | None:
    """The OAuth scopes a Google URL asks for, in itself or in the URLs nested in it (`continue`), or None when it
    names none."""
    found: set[str] = set()
    seen = url
    for _ in range(4):  # each level of nesting is one more quoting
        for match in SCOPE.finditer(seen):
            found |= {s for s in re.split(r"[\s+]+", unquote(match[1])) if s}
        seen = unquote(seen)
    return found or None


def with_google(page: Page, login: str, site: str, guard=None, wait: float = GOOGLE_WAIT_S) -> None:
    """Sign in with Google (KAN-878): press the site's one Google button, through the guards as plain code's
    account click, then pick `login` in Google's account chooser, in the page or the window the button opened, and
    press Continue on Google's consent for the site, the first time. Returns once the page is past the provider
    sign-in (`signed_in`). Raises a Needs sign-in Handoff where Google asks for a password, a code or a passkey,
    refuses the browser, or the site doesn't come back in `wait` seconds: the applicant signs in."""
    buttons = google_button(page)
    if len({" ".join(b.aria_snapshot().split()) for b in buttons}) != 1:
        raise Handoff(NO_BUTTON.format(site=site, found="no" if not buttons else "more than one"))
    try:
        submits = buttons[0].evaluate(SUBMITS) is not False
    except Exception:
        submits = True  # one Apply can't read is never pressed
    if submits:
        raise Handoff(IN_A_FORM.format(site=site))
    if guard is not None and not guard.let_account_click(buttons[0]):  # a frame inside it (KAN-710)
        guard.arm()
        raise Handoff(A_FRAME.format(site=site))
    context = getattr(page, "context", None)
    before = list(context.pages) if context is not None else []
    try:
        buttons[0].click()
    finally:
        if guard is not None:
            guard.arm()  # the account click's flag off again
            guard.rest()
    picked, agreed = set(), set()
    asked: set[str] = set()  # the scopes Google's pages have shown, across the windows
    end = time.monotonic() + wait
    while time.monotonic() < end:
        try:
            if signed_in(page):
                return
        except Exception:
            pass  # the page navigating back from Google
        windows = [page] + ([p for p in context.pages if p not in before and p is not page] if context is not None else [])
        for window in windows:
            try:
                if not google_sign_in.on_google(window):
                    continue
                if google_sign_in.rejected(window):
                    raise Handoff(google_sign_in.REJECTED)
                if google_sign_in.asks(window):
                    raise Handoff(NEEDS_SIGN_IN + google_sign_in.wants(window))
                asked |= scopes(window.url) or set()
                if more := asked - BASIC_SCOPES:
                    raise Handoff(MORE_THAN_SIGN_IN.format(site=site, scopes=", ".join(sorted(more))))
                account = google_sign_in.account(window, login).first
                if id(window) not in picked and account.is_visible():
                    if not asked:  # never pick the account for a request that says nothing of what it wants
                        raise Handoff(UNKNOWN_SCOPE.format(site=site))
                    picked.add(id(window))
                    account.click()
                    continue
                consent = window.get_by_role("button", name=CONSENT)
                if id(window) not in agreed and "/signin/oauth" in window.url and consent.count() == 1 and consent.is_visible():
                    agreed.add(id(window))
                    consent.click()
            except Handoff:
                raise
            except Exception:
                continue  # a window closing or navigating as Google hands back
        page.wait_for_timeout(250)
    raise Handoff(NOT_BACK.format(site=site, seconds=wait))
