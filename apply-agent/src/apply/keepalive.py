"""A held form's job-site session (KAN-776, KAN-779): kept alive while the form waits for the applicant, on every
job system, and told when it ends.

Live, 2026-11-10: JPMorgan's Oracle Recruiting form was held on its last step for review. When Lisul came to
submit, Oracle said "For security reasons your session was ended due to inactivity" and went back to the job list,
and the filled form was lost. A held page is the applicant's, so Apply never drives it; but many job systems sign a
person out when nothing happens on the page for a while (docs/research/session-timeouts.md: Oracle Recruiting and
SuccessFactors after 30 minutes, Taleo after 30 to 60, BrassRing as each employer sets it). So on every site, while
`_Kept.hold` holds a page, a Keeper looks at it every LOOK_S seconds and does only these things, never anything
that saves, posts the application or touches a field:

- `ping`: every PING_S, one same-origin GET of the page's own URL, with the page's cookies (a CDP page: the
  browser context's request API, so no page code runs; a plain page: the extension's isolated world), so a
  session the server keeps is used again; and, when the site's entry names one (`own`), one GET of the site's
  own keep-alive address, same origin only.
- `activity`: with the ping, one `mousemove` event dispatched on the document, which is what a page's own idle
  timer listens for (Oracle's: mousemove, scroll and keydown on window). It goes to no field and moves no pointer.
- `stay`: a dialog (a dialog role, `<dialog>` or aria-modal) whose words say the session is about to end
  (WARNS: "your session is about to expire", "are you still there?", "you will be signed out in 2 minutes") gets
  ONLY its stay-signed-in button pressed, by one of the entry's names (STAY_NAMES on any site), matched whole, as
  listed or in Sentence, Title or lower case. Plain code checks the real element first (STAY), the four checks: its name sends nothing
  (account_pages.SENDS) and leaves nothing (LEAVES: sign out, cancel...); it is in that dialog; it is in no form
  and holds nothing; and the dialog has no field and no form. Words alone, with no dialog role, are never enough.
  The press is made with the rehearsal's guard put back on (`driving`, as Ask Claude's drive). After it, the page
  is the applicant's again but their Submit is held (`holding()`, STAY_HELD), so the in-page guard stays whole,
  until they press the note's Dismiss: a page whose button sends the form later, at any delay, sends nothing while
  the form is held. A fixed wait after the press was not enough: a Continue that sent 3.5 s later went through
  (the adversarial review of #541). From the press on, the Keeper sends no more mouse moves on that page (a page
  could arm on the press and send on the next one); the GET, which the page's code never sees, goes on. The same
  holds on every site, by the generic rules too. It is a click path of the submit guard's hostile pages
  (tests/test_submit_guard_hostile.py): a change here gets an adversarial review first (KAN-666).

The Keeper acts only while the page is on the host it was held on (not on a sign-in page's). It reads for the
session's end on every site: ENDED's words showing anew (an expiry toast or page), the address turning to a
timeout page (ENDED_PATH: Eightfold's /session_timeout), or, on a site whose entry knows its form's address
(`form`), the page leaving it. Then `lost(why)` runs once, with ENDED_WHY: the rehearsal says so on the tile and by
phone push, and the form is held no more (Ask Claude stops; Fill again still works). Once Submit is pressed,
nothing here runs.

SITES holds what is known per job system: its idle limit (`minutes`, shown on the tile), its form's address, its
own keep-alive address. A site with no entry gets the generic rules (ANY), which do the same three things. No
site's dialog wording is verified live yet (docs/research/session-timeouts.md).
"""

import re
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from apply.account_pages import SENDS

LOOK_S = 5.0  # how often a held page is read for a session dialog or its end
PING_S = 240.0  # how often a listed site is pinged: well inside any idle limit seen (15 min and up)
SETTLE_MS = 3000  # the press waits this long, guard on, before the page is theirs again (their Submit still held)
STAY_HELD = ("Apply pressed this site's {} to keep you signed in. Check the form; press Dismiss when you are "
             "ready to submit.")

ENDED_WHY = "{}'s session ended; press Fill again after signing in"
PUSH_TITLE = "Apply: a held form's session ended"
ENDED_STATUS = "session ended"  # the open-forms list's status for it (apply.batch): `apply reopen` fills it anew

# A session that has ended, in the past tense: never a warning that it will ("your session will expire in 2
# minutes", "you will be signed out due to inactivity"), which a stay press answers.
ENDED = re.compile(
    r"\b(?:session|you)\s+(?:has|have|was|were)\s+(?:been\s+)?(?:ended|expired|timed\s*out|signed\s+out|logged\s+out)"
    r"|\bsession\s+(?:ended|expired|timed\s*out)\b"
    r"|\b(?:been|we|has|have)\s+(?:signed|logged)\s+(?:you\s+)?out\s+(?:due\s+to|because\s+of|after)\s+(?:\w+\s+){0,3}inactiv",
    re.IGNORECASE)

# An address a site sends an ended session to (Eightfold's /session_timeout?login_url=...).
ENDED_PATH = re.compile(r"session[_-]?(?:time[_-]?out|timed[_-]?out|expired?|ended)|timed[_-]?out", re.IGNORECASE)

# The warning a stay press answers, on a dialog: "Your session is about to expire", "will expire in 2 minutes",
# "Are you still there?", "You will be signed out in 2 minutes", "Session timeout warning".
WARNS = (r"session\W+(?:\w+\W+){0,4}(?:about\s+to|will|going\s+to|soon|is)\s+(?:expir|end\b|ending|time\s*out)"
         r"|(?:expire|end|time\s*out)s?\s+in\s+\d|are\s+you\s+still\s+(?:there|here|working)|still\s+there\?"
         r"|(?:will|[’']ll|about\s+to)\s+be\s+(?:automatically\s+)?(?:signed|logged)\s+(?:you\s+)?out"
         r"|(?:signed|logged)\s+out\s+in\s+\d|session\s+(?:time\s*out|expiry|expiration)\s+warning"
         r"|(?:extend|continue)\s+your\s+session|remaining\s+(?:time\s+)?before\s+(?:the|your)\s+session")

# A name a stay press never presses, whatever a site's entry lists: it ends the session or leaves the form.
LEAVES = re.compile(r"\b(?:sign|log)\s*-?\s*(?:out|off)\b|logout|\bcancel|\bclose\b|\bquit\b|\bexit\b|\bleave\b"
                    r"|\bdiscard|\bdelete|\bwithdraw|\bend\b|^\s*(?:no|yes|ok|okay)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Site:
    """One job system's keep-alive: what is known of it. ANY is a site with no entry."""

    name: str
    hosts: re.Pattern  # the hosts it covers
    stay: tuple[str, ...]  # the stay-signed-in button's names, whole (_cases)
    warns: str = WARNS  # the dialog's words (a JavaScript RegExp, case-insensitive)
    form: re.Pattern | None = None  # the form's own pages, by path: leaving them while held means the session ended
    minutes: float | None = None  # how long the site allows a page to sit idle, when known
    own: str | None = None  # the site's own keep-alive address (a same-origin path), when known
    ping: bool = True
    activity: bool = True


STAY_NAMES = ("Continue", "Continue session", "Continue my session", "Continue working", "Stay signed in",
              "Stay logged in", "Keep me signed in", "Keep me logged in", "Keep working", "Extend session",
              "Extend my session", "Extend", "Renew session", "I'm still here", "I am still here", "Still here",
              "I'm here", "Yes, keep me signed in", "Yes, continue", "Remain signed in", "Remain logged in")

# Every site with no entry: the generic rules. It covers every host (site_of: http and https pages only).
ANY = Site("", re.compile(r"."), STAY_NAMES)

# What is known per job system (docs/research/session-timeouts.md). An entry adds to the generic rules; it never
# lets a press do more than STAY allows.
SITES = (
    # JPMorgan's form, 2026-11-10. Its page's own code: a 30-minute idle timer reset by mousemove, scroll and
    # keydown, its warning 3 minutes before (SESSION_EXPIRE_TIME_OUT 18e5, ..._DIALOG_THREASHOLD_TIME 18e4), and
    # the server's 4 hours. The form's pages are .../job/<id>/apply/section/<n> (apply.oracle.FORM_SECTION).
    Site("Oracle Recruiting", re.compile(r"(?:^|\.)oraclecloud\.com$"), STAY_NAMES,
         form=re.compile(r"/apply/section/\d+"), minutes=30),
    # Workday's "Your session is about to expire" dialog. Its idle limit for applicants isn't published.
    Site("Workday", re.compile(r"(?:^|\.)(?:myworkdayjobs|myworkday|myworkdaysite)\.com$"), STAY_NAMES,
         form=re.compile(r"/apply(?:/|$)")),
    Site("Amazon", re.compile(r"(?:^|\.)amazon\.jobs$"), STAY_NAMES),
    # Eightfold, Microsoft Careers' too (apply.careers.microsoft.com): its server ends the session, and the page
    # goes to /session_timeout (ENDED_PATH).
    Site("Eightfold", re.compile(r"(?:^|\.)eightfold\.ai$|^apply\.careers\.microsoft\.com$"), STAY_NAMES),
    # Taleo career sections: 30 or 60 minutes by default, a reminder before; its page pings a beacon every 5
    # minutes, at an address its docs don't give.
    Site("Taleo", re.compile(r"(?:^|\.)taleo\.net$"), STAY_NAMES, minutes=30),
    # SuccessFactors' career site: 30 minutes by default, a warning 10 minutes before.
    Site("SuccessFactors", re.compile(r"(?:^|\.)(?:successfactors\.(?:com|eu)|sapsf\.(?:com|eu|cn))$"), STAY_NAMES,
         minutes=30),
    # BrassRing's Talent Gateway: each employer sets it, 15 minutes to 24 hours.
    Site("BrassRing", re.compile(r"(?:^|\.)brassring\.com$"), STAY_NAMES),
)


def site_of(url: str, sites: tuple[Site, ...] = SITES) -> Site | None:
    """The table's entry for the page at `url`, else ANY (the generic rules); None for a page that is no http(s)
    page (about:blank, a file)."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or not host:
        return None
    return next((site for site in sites if site.hosts.search(host)), ANY)


# --- page functions: fixed functions on a plain Worker (apply.plain.fixed), in the extension's isolated world

# What a held page shows now: a dialog that warns its session is about to end, and the words of an ended one.
LOOK = r"""({warns, ended}) => {
  const shown = (n) => !n.checkVisibility || n.checkVisibility();
  const warning = new RegExp(warns, 'i'), over = new RegExp(ended, 'i');
  const dialogs = [...document.querySelectorAll('[role=dialog], [role=alertdialog], dialog, [aria-modal=true]')].filter(shown);
  const text = (document.body && document.body.innerText) || '';
  return {warned: dialogs.some((d) => warning.test(d.innerText || '')), ended: over.test(text)};
}"""

# Whether a button may be pressed as a session dialog's stay-signed-in (the four checks): no words of it send or
# leave (its text, value, label and title, as well as the name Python matched); it is in a dialog that warns; it is
# no form's (nor names one), no link away and no input, and nothing is inside it; and the dialog holds no form and
# no field.
STAY = r"""(el, {warns, sends, leaves}) => {
  const said = [el.innerText, el.value, el.getAttribute('aria-label'), el.getAttribute('title')].filter(Boolean);
  if (said.some((w) => new RegExp(sends, 'i').test(w) || new RegExp(leaves, 'i').test(w))) return false;
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

# A plain page's ping: one GET of its own URL (or of `url`, the site's own keep-alive address, same origin only)
# with its cookies, from the extension's world (no page code runs).
PING = r"""async (url) => {
  try {
    const to = new URL(url || location.href, location.href);
    if (to.origin !== location.origin) return 0;
    const answer = await fetch(to.href, {method: 'GET', credentials: 'include', cache: 'no-store', redirect: 'manual'});
    return answer.status;
  } catch (e) {
    return 0;
  }
}"""


def _plain(page) -> bool:
    return getattr(page, "plain", False) is True


def _cases(name: str) -> tuple[str, ...]:
    """A button's name as listed, in Sentence case, Title Case and lower case: a stay name matches whole in each.
    Exact strings, never a case-insensitive pattern: with one, the press's click timed out on a fake whose dialog
    shows again (2026-11-10)."""
    return tuple(dict.fromkeys((name, name[:1].upper() + name[1:].lower(), name.title(), name.lower())))


def press(page, site: Site, driving: Callable[[], AbstractContextManager] = nullcontext) -> str:
    """Press the stay-signed-in button of a session dialog on `page`, if one shows: the name pressed, or "". Only a
    name of `site.stay` that neither sends (SENDS) nor leaves (LEAVES), and only a button STAY passes. The press,
    and SETTLE_MS after it, run inside `driving()`: the held page's guard back on. A name is returned once the press
    was tried, even when it raised: the Keeper then holds the Submit (Keeper.holding) until the Dismiss."""
    for name in site.stay:
        if SENDS.search(name) or LEAVES.search(name):
            continue
        found = []
        for said in _cases(name):
            try:
                found += [b for b in page.get_by_role("button", name=said, exact=True).all() if b.is_visible()]
            except Exception:
                continue
        for button in found:
            try:
                if button.evaluate(STAY, {"warns": site.warns, "sends": SENDS.pattern, "leaves": LEAVES.pattern}) is not True:
                    continue
            except Exception:
                continue
            with driving():
                try:
                    button.click(timeout=3000)
                except Exception:
                    pass  # refused or missed, maybe after the press went down: held all the same
                try:
                    page.wait_for_timeout(SETTLE_MS)
                except Exception:
                    pass  # the page went on to another document
            return name
    return ""


def _same_origin(url: str, path: str) -> str:
    """`path` on `url`'s origin, or "" when it would leave it."""
    to = urljoin(url, path)
    return to if urlsplit(to)[:2] == urlsplit(url)[:2] else ""


def ping(page, site: Site, activity: bool = True) -> None:
    """What `site` allows: a mouse move on the page's document, one GET of its own URL with its cookies, and one of
    the site's own keep-alive address when its entry names one. Errors are ignored: the next look tries again."""
    try:
        if site.activity and activity:
            page.evaluate(ACTIVITY)
    except Exception:
        pass
    if not site.ping:
        return
    url = page.url
    for to in (url, _same_origin(url, site.own) if site.own else ""):
        if not to:
            continue
        try:
            if _plain(page):
                page.evaluate(PING, to)
            else:
                page.context.request.get(to, max_redirects=0, timeout=10_000).dispose()
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
        self._host = ""
        self._held_on_form = False
        self._showed_ended: bool | None = None
        self._at_ended_path = False
        self._look_at = self._ping_at = 0.0
        self._since = ""
        self._pressed = ""
        self._hold = ""  # why the Submit is held: a stay press, until the Dismiss
        self._quiet = False  # no mouse move after a stay press

    def line(self) -> str:
        """The tile's session line: since when the form is held, what Apply does for it and what the site allows."""
        words = [f"Held since {self._since}"]
        if self.site:
            whose = f"{self.site.name}'s" if self.site.name else "the site's"
            words.append(f"Apply keeps {whose} session alive")
            words.append(f"it signs you out after about {self.site.minutes:g} min idle" if self.site.minutes
                         else "its idle limit isn't known")
        else:
            words.append("Apply can't keep this page's session alive, and only watches for its end")
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
            self._host = (urlsplit(url).hostname or "").lower()
            self._held_on_form = bool(self.site and self.site.form and self.site.form.search(urlsplit(url).path))
            self._at_ended_path = bool(ENDED_PATH.search(urlsplit(url).path))
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
        at_ended_path = bool(ENDED_PATH.search(urlsplit(url).path))
        if ended and not self._showed_ended or at_ended_path and not self._at_ended_path or self._left_form(url):
            self.over = True
            self._lost(ENDED_WHY.format(self._company))
            return
        self._showed_ended, self._at_ended_path = ended, at_ended_path
        if not self.site or (urlsplit(url).hostname or "").lower() != self._host:
            return  # no web page, or the page on another host (a sign-in's): nothing is done there
        if looked.get("warned"):
            before, self._hold = self._hold, STAY_HELD.format("stay-signed-in button")  # held as the guard lifts
            if name := press(page, self.site, driving):
                self._hold, self._quiet = STAY_HELD.format(repr(name)), True
                self._pressed = f"pressed the site's {name} at {self._now().strftime('%H:%M')}"
                self._say(self.line())
            else:
                self._hold = before
        if now >= self._ping_at:
            self._ping_at = now + PING_S
            ping(page, self.site, activity=not self._quiet)

    def holding(self) -> str:
        """Why the applicant's Submit is held: a stay press, until they dismiss it. "" when it is theirs."""
        return self._hold

    def dismiss(self) -> None:
        """The note's Dismiss was pressed: Submit is theirs again (the mouse moves stay off on this page)."""
        self._hold = ""

    def _left_form(self, url: str) -> bool:
        return self._held_on_form and not self.site.form.search(urlsplit(url).path)
