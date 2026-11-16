"""Sign in with Google, by plain code: Apply presses the site's Google button and, in Google's account chooser,
the account of the applicant's own email. That pick is the only click Apply makes on Google's pages. It never types
into them and never sees a Google password: a page that asks for a password, a code or a passkey, or Google's refusal
of the browser, is a Needs sign-in Handoff. The Worker's Chrome profile holds the applicant's Google sign-in, made by
hand (docs/sign-in.md). Workday's Filler (workday_sign_in: google) and the provider sign-in in the way of a Claude
fill form (apply.provider_sign_in) share it."""

from urllib.parse import urlsplit

from playwright.sync_api import Page

from apply.accounts import NEEDS_SIGN_IN

REJECTED = (
    f"{NEEDS_SIGN_IN}Google refused Sign in with Google in the Worker's Chrome (\"This browser or app may not be "
    "secure\"). Sign in with Google in your own Chrome and apply yourself."
)


def on_google(page: Page) -> bool:
    return page.url.startswith("https://accounts.google.com/")


def asks(page: Page) -> bool:
    """Whether Google's page asks for something typed (a password, a code, a phone number), or is one of
    its challenges, such as a passkey, which has no box to type in (KLA, 2026-11-03)."""
    return challenge(page) or \
        page.locator("input[type=password]:visible, input[type=tel]:visible, input[type=text]:visible").count() > 0


def challenge(page: Page) -> bool:
    url = urlsplit(page.url)
    return url.hostname == "accounts.google.com" and "/signin/challenge/" in url.path


def rejected(page: Page) -> bool:
    """Whether Google refused to sign in this browser ("This browser or app may not be secure")."""
    return urlsplit(page.url).hostname == "accounts.google.com" and "/signin/rejected" in urlsplit(page.url).path


def wants(page: Page) -> str:
    """The Handoff for a Google page that asks for more than the account pick."""
    asked = "a password" if page.locator("input[type=password]").count() else "a passkey" if (
        "/signin/challenge/pk" in urlsplit(page.url).path) else (
        page.locator("h1").first.inner_text().strip() if page.locator("h1").count() else page.url)
    return (
        f"Google asked for more than an account pick ({asked}). Agents never type Google credentials: "
        "sign the Worker profiles in to Google again by hand (see the setup checklist), then apply yourself."
    )


def account(page: Page, login: str):
    """The applicant's own account in Google's chooser."""
    return page.locator(f'[data-identifier="{login}"], [data-email="{login}"]')
