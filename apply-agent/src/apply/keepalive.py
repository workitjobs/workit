"""A held form's job-site session (KAN-776): kept alive while the form waits on Lisul, and told when it ends.

Live, 2026-11-10: JPMorgan's Oracle Recruiting form was held on its last step for Lisul's review. When he came
to submit, Oracle said "For security reasons your session was ended due to inactivity" and went back to the
job list, and the filled form was lost. A held page is his, so Apply never drives it; but a site signs a
person out when nothing happens on the page for a while.

While `_Kept.hold` holds a page, a Keeper looks at it every LOOK_S seconds and does only what the site's entry
in SITES (the allowlist) names, never anything that saves, posts the application or touches a field:

- `ping`: every PING_S, one same-origin GET of the page's own URL, with the page's cookies (a CDP page: the
  browser context's request API, so no page code runs; a plain page: the extension's isolated world), so a
  session the server keeps is used again.
- `activity`: with the ping, one `mousemove` event dispatched on the document, which is what a page's own
  idle timer listens for. It goes to no field and moves no pointer.
- `stay`: the site's own "your session is about to expire" dialog (its words: `warns`) gets ONLY its
  stay-signed-in button pressed, by one of the names the entry lists, matched exactly. Plain code checks the
  real element first (STAY): it is in that dialog, in no form, holds nothing, and the dialog has no field and
  no form. A name that sends (submit, apply, confirm...) is never pressed. The press is made with the
  rehearsal's guard put back on (`driving`, as Ask Claude's drive), and the guard stays on SETTLE_MS after it,
  so a page whose button sends the form anyway sends nothing. It is a click path of the submit guard's hostile
  pages (tests/test_submit_guard_hostile.py): a change here gets an adversarial review first (KAN-666).

On every site, listed or not, the Keeper only reads for the session's end: ENDED's words showing anew (an
expiry toast or page), or, on a site whose entry knows its form's address (`form`), the page leaving it. Then
`lost(why)` runs once, with ENDED_WHY: the rehearsal tells Lisul on the tile and by phone push, and the form is
held no more (Ask Claude stops; Fill again still works). Once Lisul presses Submit, nothing here runs.

The names and words in SITES come from what the sites are reported to show; none is verified live yet.
`minutes` is how long a site allows a page to sit idle, when that is known (the tile shows it); none is.
"""

import re
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from apply.account_pages import SENDS

LOOK_S = 5.0  # how often a held page is read for a session dialog or its end
PING_S = 240.0  # how often a listed site is pinged: well inside any idle limit seen (15 min and up)
SETTLE_MS = 3000  # the guard stays on this long after a stay press: a page that sends after it sends nothing

ENDED_WHY = "{}'s session ended; press Fill again after signing in"
PUSH_TITLE = "Apply: a held form's session ended"
ENDED_STATUS = "session ended"  # the open-forms list's status for it (apply.batch): `apply reopen` fills it anew

# A session that has ended, in the past tense: never a warning that it will ("your session will expire in 2
# minutes"), which a stay press answers.
ENDED = re.compile(
    r"\b(?:session|you)\s+(?:has|have|was|were)\s+(?:been\s+)?(?:ended|expired|timed\s*out|signed\s+out|logged\s+out)"
    r"|\bsession\s+(?:ended|expired|timed\s*out)\b"
    r"|\b(?:signed|logged)\s+(?:you\s+)?out\s+(?:due\s+to|because\s+of|after)\s+(?:\w+\s+){0,3}inactiv",
    re.IGNORECASE)

# The warning a stay press answers, on a dialog: "Your session is about to expire", "will expire in 2 minutes",
# "Are you still there?".
WARNS = (r"session\W+(?:\w+\W+){0,4}(?:about\s+to|will|going\s+to|soon)\s+(?:expire|end|time\s*out)"
         r"|(?:expire|end|time\s*out)s?\s+in\s+\d|are\s+you\s+still\s+(?:there|here|working)|still\s+there\?")


@dataclass(frozen=True)
class Site:
    """One job system's keep-alive actions: the allowlist's entry."""

    name: str
    hosts: re.Pattern  # the hosts it covers
    stay: tuple[str, ...]  # the stay-signed-in button's names, exact (case and all)
    warns: str = WARNS  # the dialog's words (a JavaScript RegExp, case-insensitive)
    form: re.Pattern | None = None  # the form's own pages, by path: leaving them while held means the session ended
    minutes: float | None = None  # how long the site allows a page to sit idle, when known
    ping: bool = True
    activity: bool = True


STAY_NAMES = ("Continue", "Continue session", "Continue Session", "Stay signed in", "Stay Signed In",
              "Stay logged in", "Keep me signed in", "Extend session", "Extend Session", "Keep working")

SITES = (
    # JPMorgan's form, 2026-11-10. The form's pages are .../job/<id>/apply/section/<n> (apply.oracle.FORM_SECTION).
    Site("Oracle Recruiting", re.compile(r"(?:^|\.)oraclecloud\.com$"), STAY_NAMES,
         form=re.compile(r"/apply/section/\d+")),
    # Workday's "Your session is about to expire" dialog.
    Site("Workday", re.compile(r"(?:^|\.)(?:myworkdayjobs|myworkday|myworkdaysite)\.com$"), STAY_NAMES,
         form=re.compile(r"/apply(?:/|$)")),
    Site("Amazon", re.compile(r"(?:^|\.)amazon\.jobs$"), STAY_NAMES),
    # Eightfold, Microsoft Careers' too (apply.careers.microsoft.com).
    Site("Eightfold", re.compile(r"(?:^|\.)eightfold\.ai$|^apply\.careers\.microsoft\.com$"), STAY_NAMES),
)


def site_of(url: str, sites: tuple[Site, ...] = SITES) -> Site | None:
    """The allowlist's entry for the page at `url`, or None: a site with no entry gets no keep-alive action."""
    host = (urlsplit(url).hostname or "").lower()
    return next((site for site in sites if host and site.hosts.search(host)), None)


# --- page functions: fixed functions on a plain Worker (apply.plain.fixed), in the extension's isolated world

# What a held page shows now: a dialog that warns its session is about to end, and the words of an ended one.
LOOK = r"""({warns, ended}) => {
  const shown = (n) => !n.checkVisibility || n.checkVisibility();
  const warning = new RegExp(warns, 'i'), over = new RegExp(ended, 'i');
  const dialogs = [...document.querySelectorAll('[role=dialog], [role=alertdialog], dialog, [aria-modal=true]')].filter(shown);
  const text = (document.body && document.body.innerText) || '';
  return {warned: dialogs.some((d) => warning.test(d.innerText || '')), ended: over.test(text)};
}"""

# Whether a button may be pressed as a session dialog's stay-signed-in: it is in a dialog that warns, it is no
# form's (nor names one), it is no link away and no input, nothing is inside it, and the dialog holds no form and
# no field. Python checks its name first.
STAY = r"""(el, warns) => {
  const dialog = el.closest('[role=dialog], [role=alertdialog], dialog, [aria-modal=true]');
  if (!dialog || !new RegExp(warns, 'i').test(dialog.innerText || '')) return false;
  if (el.tagName === 'INPUT' || el.form || el.closest('form') || dialog.closest('form')) return false;
  if (el.hasAttribute('form') || el.hasAttribute('formaction')) return false;
  if (el.tagName === 'A' && /^(?!#|javascript:)./i.test(el.getAttribute('href') || '')) return false;
  if (el.querySelector('input, select, textarea, label, button, a, iframe, frame, object, embed')) return false;
  return !dialog.querySelector('form, input:not([type=hidden]), select, textarea, [contenteditable]:not([contenteditable=false]), iframe, frame');
}"""

# The page's own idle timer hears a mouse move. Dispatched on the document: no field, no pointer.
ACTIVITY = r"""() => {
  document.documentElement.dispatchEvent(new MouseEvent('mousemove', {bubbles: true, cancelable: true}));
  return true;
}"""

# A plain page's ping: one GET of its own URL with its cookies, from the extension's world (no page code runs).
PING = r"""async () => {
  try {
    const answer = await fetch(location.href, {method: 'GET', credentials: 'include', cache: 'no-store', redirect: 'manual'});
    return answer.status;
  } catch (e) {
    return 0;
  }
}"""


def _plain(page) -> bool:
    return getattr(page, "plain", False) is True


def press(page, site: Site, driving: Callable[[], AbstractContextManager] = nullcontext) -> str:
    """Press the stay-signed-in button of the site's session dialog on `page`, if one shows: the name pressed,
    or "". Only a name of `site.stay` that sends nothing, and only a button STAY passes. The press, and SETTLE_MS
    after it, run inside `driving()`: the held page's guard back on."""
    for name in site.stay:
        if SENDS.search(name):
            continue
        try:
            found = [b for b in page.get_by_role("button", name=name, exact=True).all() if b.is_visible()]
        except Exception:
            continue
        for button in found:
            try:
                if button.evaluate(STAY, site.warns) is not True:
                    continue
            except Exception:
                continue
            with driving():
                try:
                    button.click(timeout=3000)
                except Exception:
                    return ""  # refused or missed: nothing more on this look
                try:
                    page.wait_for_timeout(SETTLE_MS)
                except Exception:
                    pass  # the page went on to another document
            return name
    return ""


def ping(page, site: Site) -> None:
    """What `site` allows: a mouse move on the page's document, and one GET of its own URL with its cookies.
    Errors are ignored: the next look tries again."""
    try:
        if site.activity:
            page.evaluate(ACTIVITY)
    except Exception:
        pass
    try:
        if not site.ping:
            return
        if _plain(page):
            page.evaluate(PING)
        else:
            page.context.request.get(page.url, max_redirects=0, timeout=10_000).dispose()
    except Exception:
        pass


class Keeper:
    """One held page's session: kept alive while held, and told once when it ends. `say(line)` hears the tile's
    session line; `lost(why)` hears the end, once."""

    def __init__(self, company: str, lost: Callable[[str], None], say: Callable[[str], None] = lambda line: None,
                 sites: tuple[Site, ...] = SITES, clock: Callable[[], float] = time.monotonic,
                 now: Callable[[], datetime] = datetime.now):
        self._company = company or "The job site"
        self._lost, self._say, self._sites, self._clock, self._now = lost, say, sites, clock, now
        self.site: Site | None = None
        self.over = False
        self._started = False
        self._held_on_form = False
        self._showed_ended: bool | None = None
        self._look_at = self._ping_at = 0.0
        self._since = ""
        self._pressed = ""

    def line(self) -> str:
        """The tile's session line: since when the form is held, what Apply does for it and what the site allows."""
        words = [f"Held since {self._since}"]
        if self.site:
            words.append(f"Apply keeps {self.site.name}'s session alive")
            words.append(f"it signs you out after about {self.site.minutes:g} min idle" if self.site.minutes
                         else "its idle limit isn't known")
        else:
            words.append("this site may sign you out when idle, and Apply only watches for it")
        if self._pressed:
            words.append(self._pressed)
        return "; ".join(words)

    def tick(self, page, driving: Callable[[], AbstractContextManager] = nullcontext) -> None:
        """One turn of the hold loop: look at the page when LOOK_S has passed."""
        now = self._clock()
        if self.over or now < self._look_at:
            return
        self._look_at = now + LOOK_S
        try:
            url = page.url
        except Exception:
            return
        if not self._started:
            self._started = True
            self.site = site_of(url, self._sites)
            self._held_on_form = bool(self.site and self.site.form and self.site.form.search(urlsplit(url).path))
            self._since = self._now().strftime("%H:%M")
            self._ping_at = now + PING_S
            self._say(self.line())
        try:
            looked = page.evaluate(LOOK, {"warns": self.site.warns if self.site else WARNS, "ended": ENDED.pattern})
        except Exception:
            return  # the page navigating: look again next time
        ended = bool(looked and looked.get("ended"))
        if self._showed_ended is None:  # the first look: words there from the start (a sign-in page's) are no new end
            self._showed_ended = ended
        if ended and not self._showed_ended or self._left_form(url):
            self.over = True
            self._lost(ENDED_WHY.format(self._company))
            return
        self._showed_ended = ended
        if not self.site or site_of(url, self._sites) is not self.site:
            return  # an unlisted site, or the page on another host (a sign-in's): nothing is done there
        if looked.get("warned") and (name := press(page, self.site, driving)):
            self._pressed = f"pressed the site's {name} at {self._now().strftime('%H:%M')}"
            self._say(self.line())
        if now >= self._ping_at:
            self._ping_at = now + PING_S
            ping(page, self.site)

    def _left_form(self, url: str) -> bool:
        return self._held_on_form and not self.site.form.search(urlsplit(url).path)
