"""A sign-in with a provider (Google, Microsoft, LinkedIn, Facebook) in the way of a form that Claude fill reads
(KAN-763). Microsoft Careers (apply.careers.microsoft.com, an Eightfold site) opens one on Apply now: a window
that offers "Sign in using Google" and the others, and the form opens only to a signed-in applicant.

Plain code reads the page only. Apply never presses a provider's button, never types into a sign-in and never
handles a password: the applicant signs in on the page. `shows` makes Claude fill's stop there a Needs sign-in
pause, and `signed_in` lets that pause go on by itself once the provider sign-in is gone and the site's account
menu shows (rehearsal's KAN-670 check), as Oracle's and Workday's sign-in pauses do.
"""

from playwright.sync_api import Page

from apply.accounts import NEEDS_SIGN_IN

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
