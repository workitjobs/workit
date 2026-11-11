"""A company careers page that embeds a Greenhouse, Lever or Ashby form, as
that form's own link, so the job system's Filler fills it instead of Claude
fill. Plain code, zero tokens.

A page that frames another known job system's form (ADP, UKG, Dayforce,
Taleo, SuccessFactors, Phenom, iCIMS, Workday, Jobvite, SmartRecruiters,
Avature, BrassRing...) gets that frame's own URL as the Posting's link
(KAN-797): the Worker opens it as its own top page, and Claude fill fills it
there. In the frame, PR 556's rule closed it to every press (a frame of
another site may take no file), so the form was handed over. Only a frame
whose URL, as the browser loaded it, is https on a known job system's host
(KNOWN_HOSTS), under frames of the page's own origin alone, that shows a
field or an Apply button is opened. A sign-in frame is never opened: the
form stays the applicant's (`_signs_in`). Any other frame of another site
leaves the Posting as it is, and the fill hands it over as before.

greenhouse.board_behind finds a Greenhouse job from the link alone (its
?gh_jid=, or the job id in its path), with no page. Where it can't, the page
is opened in the Worker's browser and its frames are read: the form's frame
names its job system's link. A page that shows the form only once its Apply
button is clicked (Roblox's "Apply Now", live) gets that one click, on a
button or link outside any form, so it never sends anything. A page that
links its Apply straight to the job system's own page is read the same way.
"""

import re
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page

from apply import description, upload_origin
from apply.adapters import JobSite
from apply.fill_engine import posting_ai_trap
from apply.model import Posting

SETTLES_MS = 5_000  # how long the page may load before its frames are read
SHOWS_MS = 6_000  # how long the form's frame may take to show once Apply is clicked
POLL_MS = 250
APPLY = re.compile(r"^\s*apply(\s+(now|here|online|for this (job|role|position)))?\s*$", re.IGNORECASE)
GREENHOUSE_EMBED = re.compile(r"^https://(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/embed/job_app\?", re.IGNORECASE)
GREENHOUSE_JOB = re.compile(r"^https://(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/([\w-]+)/jobs/(\d+)", re.IGNORECASE)
LEVER = re.compile(r"^https://jobs(?:\.eu)?\.lever\.co/[\w.-]+/[0-9a-f-]{36}", re.IGNORECASE)
ASHBY = re.compile(r"^https://jobs\.ashbyhq\.com/[^/?#]+/[0-9a-f-]{36}", re.IGNORECASE)
JOB_ID = re.compile(r"[?&]gh_jid=(\d+)|/(\d{6,})/?(?:[?#]|$)")
# Job systems whose forms a careers page frames, by host (each subdomain too), besides upload_origin.JOB_SYSTEM_HOSTS
# (KAN-797). Each is the job system's own host, which serves only its tenants' pages. Not the Fill engine's jobOf: it
# names a link Workday's for `?ats=workday` on any host, so a hostile page's frame could name itself a job system.
FRAMED_HOSTS = (
    "workforcenow.adp.com", "recruiting.adp.com", "myjobs.adp.com",  # ADP
    "ultipro.com", "rec.pro.ukg.net",  # UKG Pro Recruiting (UltiPro)
    "dayforcehcm.com",  # Dayforce
    "taleo.net",  # Oracle Taleo
    "successfactors.com", "successfactors.eu", "sapsf.com", "sapsf.eu", "jobs2web.com",  # SAP SuccessFactors
    "phenompeople.com",  # Phenom
    "myworkdaysite.com",  # Workday (myworkdayjobs.com is in JOB_SYSTEM_HOSTS)
    "avature.net",  # Avature
    "brassring.com",  # IBM Kenexa BrassRing
    "paycomonline.net",  # Paycom
    "recruitingbypaycor.com",  # Paycor
)
KNOWN_HOSTS = upload_origin.JOB_SYSTEM_HOSTS + FRAMED_HOSTS
# A sign-in page's link: a path or query part that names a sign-in.
SIGN_IN = re.compile(r"(?:^|[/_.=&?-])(?:log-?in|log-?on|sign-?in|sign-?on|sso|saml|oauth2?|auth|authorize|password)"
                     r"(?:$|[/_.=&?-])", re.IGNORECASE)
FIELD = "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=image]), select, textarea"
# The page's frames' sources (a lazy one not yet loaded too), and every <a> whose words say apply:
# not another link, which may be another job's.
SOURCES = """() => [...document.querySelectorAll('iframe[src]')].map(f => f.src).concat([...document.querySelectorAll('a[href]')]
  .filter(a => /\\bapply\\b/i.test(a.innerText || a.getAttribute('aria-label') || '')).map(a => a.href))"""


def form_behind(posting: Posting, site: JobSite, text: str | None = None) -> Posting:
    """`posting` with its link turned into the link of the Greenhouse, Lever or
    Ashby form its page embeds, or of another known job system's form its
    page frames (its id, company and role kept); as it is when the page
    embeds none, or when it can't be opened. Only a Posting of no known job system is opened, and
    never one whose page, read with a plain fetch (`text`, when the caller
    read it already), speaks to AI agents: the Worker hands it off unopened."""
    if posting.job_system != "other":
        return posting
    if posting_ai_trap(description.from_link(posting, site) if text is None else text):
        return posting
    try:
        with site.open(posting.url) as page:
            found = embedded_form(page, posting.url)
    except Exception:
        return posting
    return replace(posting, url=found) if found else posting


def embedded_form(page: Page, url: str) -> str:
    """The link of the form the open page embeds, or ""."""
    try:
        page.wait_for_load_state("networkidle", timeout=SETTLES_MS)
    except Exception:
        pass  # some pages never go quiet
    if found := _found(page, url):
        return found
    if not _click_apply(page):
        return ""
    waited = 0
    while waited < SHOWS_MS:
        page.wait_for_timeout(POLL_MS)
        waited += POLL_MS
        if found := _found(page, url):
            return found
    return ""


def form_link(link: str, posting_url: str = "") -> str:
    """A frame's or link's URL as its job system's own Posting link, or "" if
    it is none: Greenhouse's embedded form with its board and job (the job
    from the posting's link where the frame names none), Lever's or Ashby's
    job page without its /apply or /application tail."""
    if GREENHOUSE_EMBED.search(link):
        query = parse_qs(urlsplit(link).query)
        board = (query.get("for") or [""])[0]
        job = (query.get("token") or [""])[0] or _job_id(posting_url)
        if re.fullmatch(r"[\w-]+", board) and job.isdigit():
            return f"https://job-boards.greenhouse.io/embed/job_app?for={board}&token={job}"
        return ""
    if hosted := GREENHOUSE_JOB.search(link):
        return f"https://job-boards.greenhouse.io/embed/job_app?for={hosted[1]}&token={hosted[2]}"
    for system in (LEVER, ASHBY):
        if found := system.search(link):
            return found[0]
    return ""


def _job_id(url: str) -> str:
    found = JOB_ID.search(url)
    return (found[1] or found[2]) if found else ""


def _found(page: Page, url: str) -> str:
    """A form's link among the page's frames and Apply links: a Greenhouse, Lever or Ashby form's first, else the URL
    of a frame that holds another known job system's form."""
    links = [frame.url for frame in page.frames]
    try:
        links += page.evaluate(SOURCES)
    except Exception:
        pass
    return next((found for link in links if (found := form_link(link, url))), "") or framed(page)


def known_host(url: str) -> bool:
    """Whether `url` is an https page on a known job system's own host (KNOWN_HOSTS), with no user part."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or "@" in parts.netloc or port not in (None, 443) or not host:
        return False
    return any(host == h or host.endswith("." + h) for h in KNOWN_HOSTS)


def framed(page: Page) -> str:
    """The URL of the first frame on the open page that holds a known job system's form, or "": a frame of another
    origin than the top page, at https on a known job system's host as the browser loaded it (never an attribute the
    page wrote), with every frame above it of the top page's own origin, that shows a field or an Apply button and
    is no sign-in page."""
    top = upload_origin.origin(page.url)
    for frame in page.frames:
        own, ancestors = upload_origin.chain(frame)
        if not ancestors or not known_host(own) or upload_origin.origin(own) == top:
            continue
        if any(upload_origin.origin(a) != top for a in ancestors):
            continue  # under another site's frame: that site's to embed (a free tenant's form)
        try:
            if _signs_in(frame) or not _shows_form(frame):
                continue
        except Exception:
            continue  # gone, or unreadable: not opened
        return own
    return ""


def _signs_in(frame) -> bool:
    """A sign-in page, by its link or a password box: the applicant's to sign in to, so never opened."""
    parts = urlsplit(frame.url)
    return bool(SIGN_IN.search(parts.path) or SIGN_IN.search(parts.query)) or frame.locator("input[type=password]").count() > 0


def _shows_form(frame) -> bool:
    if frame.locator(FIELD).count() > 0:
        return True
    return any(frame.get_by_role(role, name=APPLY).count() > 0 for role in ("button", "link"))


def _click_apply(page: Page) -> bool:
    """Click the page's own Apply button or link, outside any form, once.
    Whether there was one."""
    for role in ("button", "link"):
        for control in page.get_by_role(role, name=APPLY).all():
            try:
                if not control.is_visible() or control.evaluate("el => !!el.closest('form')"):
                    continue
                control.click(timeout=5_000)
                return True
            except Exception:
                continue
    return False
