"""Where Apply may give a file (KAN-795): only to the form's own site.

A page can hold a frame from another site with a file input in it (an ad, a widget, or a hostile page's own trap).
A file that Apply, Claude fill or Ask gives there goes to that other site: the applicant's resume or cover letter.
So a file goes only to a file input in:

- the top frame;
- a frame of the top frame's own origin (an about:blank or srcdoc frame takes its parent's);
- a frame on a job system's own host (JOB_SYSTEM_HOSTS): the form a company page embeds, such as Greenhouse's
  job-boards.greenhouse.io/embed/job_app or an iCIMS careers frame.

and every frame between it and the top is the top frame's own origin: a job system's form inside another site's frame
is that site's to embed (a free tenant's form), and a frame under one is that site's to read (PR 556's review). A pop-up
is a top frame, so one a frame of another site opens could take a file: `give` refuses a pop-up with a page of another
origin up its chain of openers, and the guard lets a frame that may not take a file open no pop-up at all (nor a
picker, nor any press: see submit_guard's Uploads section). On a plain Worker, Claude's upload goes only to the drive's
own tab, or a tab of its origin.

Any other frame gets no file, and Apply hands the field to the applicant (`Elsewhere`). Each place a file is set
checks in the same step as the set, so a frame that navigates to another site between the choice and the set
gets nothing:

- a CDP Worker: `give` holds the input's ElementHandle, which belongs to one document. It reads that document's
  frame and its parents, then sets the files on that handle. A navigation in between ends the handle, so the set
  fails. A chooser's input is the one whose picker opened, so a script that puts a new input in its place gets
  nothing.
- a plain Worker: page/dom.js's `files` and ops/tile.js's `giveFiles` read the frame's origin and its ancestors'
  in the frame itself, in the same task as the set, against the hosts Apply sends with each call (none sent: the
  top site only).
- Claude's own upload (Playwright MCP's on a CDP Worker, apply.plain.tools on a plain one): while a guard is on,
  a frame that may not take a file is closed to every press (submit_guard's Uploads section), so Claude has no
  chooser there and the frame opens no pop-up. The guard notes BLOCKED, and Claude fill hands the form over.

What stays open: a job system's host is any of its tenants. A hostile top page could embed its own Greenhouse board's
form, and a file given there goes to that board. The page's own site could take the file anyway, so this is no
worse than the page itself. Claude can press nothing in another site's frame while a guard is on (a
Google sign-in button's frame too): the form is handed over instead.
"""

from urllib.parse import urlsplit

from apply.model import Handoff

# The job systems whose forms a company's page embeds in a frame, by host (each subdomain too). Each is the job
# system's own host, which serves only its tenants' forms: no host here serves files that anyone can put there.
JOB_SYSTEM_HOSTS = (
    "greenhouse.io",  # job-boards.greenhouse.io/embed/job_app, boards.greenhouse.io's older embed
    "lever.co",
    "ashbyhq.com",  # jobs.ashbyhq.com/<org>/embed
    "icims.com",  # careers-<company>.icims.com/jobs/...?in_iframe=1
    "jobvite.com",
    "smartrecruiters.com",
    "workable.com",
    "bamboohr.com",
    "paylocity.com",
    "rippling.com",
    "eightfold.ai",
    "myworkdayjobs.com",
    "recruitee.com",
    "breezy.hr",
    "applytojob.com",  # JazzHR
)

# What a guard notes when it keeps a file input's picker shut in a frame that may not take a file.
BLOCKED = "a file upload into another site's frame"

# The rule in a page (the guard's, and the worker extension's copies in page/dom.js and ops/tile.js): may a file
# go into this document? `own` and `ancestors` are read from the document's own `location`, which no page can
# replace. An about: document (about:blank, about:srcdoc) has the origin "null" there: its caller gives its
# parent's instead. Any other opaque origin (data:, a sandbox's) stays "null", and takes no file.
RULE_JS = r"""(own, ancestors, hosts) => {
  if (!ancestors.length) return true;  // the top frame: the form's own site, whatever its URL
  const top = ancestors[ancestors.length - 1];
  if (!own || own === 'null' || !top || top === 'null') return false;
  // Every frame between this one and the top is the top's own site: a job system's form inside another site's
  // frame is that site's to embed, and a frame under one is that site's to read (PR 556's review).
  for (let i = 0; i < ancestors.length - 1; i++) if (ancestors[i] !== top) return false;
  if (own === top) return true;
  const host = own.replace(/^[a-z][a-z0-9+.-]*:\/\//i, '').replace(/:\d+$/, '').replace(/^\[|\]$/g, '').toLowerCase();
  for (let i = 0; i < hosts.length; i++) {
    const h = String(hosts[i]).toLowerCase();
    if (host === h || (host.length > h.length && host.slice(-h.length - 1) === '.' + h)) return true;
  }
  return false;
}"""


class Elsewhere(Handoff):
    """The file input is in a frame of another site: Apply gives it no file, and the applicant attaches it."""

    def __init__(self, host: str = ""):
        where = f"a frame from {host}" if host else "a frame from another site"
        super().__init__(f"The form asks for a file in {where}, not on the form's own site. Apply never gives a "
                         "file there, since that site would get your resume. Check the page, and attach the file "
                         "yourself if the field is the form's own.")
        self.host = host


def origin(url: str) -> str:
    """The URL's origin (scheme://host[:port]), or "null" for one with none (about:, data:, blob:)."""
    try:
        parts = urlsplit(url or "")
    except ValueError:
        return "null"
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return "null"
    return f"{parts.scheme}://{parts.netloc.rsplit('@', 1)[-1].lower()}"


def may_upload(own: str, ancestors: list[str] | tuple[str, ...] = (), hosts: tuple[str, ...] | None = None) -> bool:
    """Whether a file may go into a document at origin (or URL) `own`, whose ancestors' origins (or URLs) are
    `ancestors`, the parent's first and the top frame's last. The same rule as RULE_JS."""
    if not ancestors:
        return True  # the top frame: the form's own site, whatever its URL
    ancestors = [origin(a) for a in ancestors]
    own = ancestors[0] if own.startswith("about:") else origin(own)
    top = ancestors[-1]
    if not own or own == "null" or top == "null" or any(a != top for a in ancestors[:-1]):
        return False
    if own == top:
        return True
    host = (urlsplit(own).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in (JOB_SYSTEM_HOSTS if hosts is None else hosts))


def chain(frame) -> tuple[str, list[str]]:
    """A frame's URL and its ancestors' URLs (parent first), from a Playwright Frame or a plain PortFrame."""
    own, ancestors = frame.url, []
    parent = frame.parent_frame
    while parent is not None:
        ancestors.append(parent.url)
        parent = parent.parent_frame
    return own, ancestors


def frame_may_upload(frame) -> bool:
    """Whether a file may go into `frame` (a Playwright Frame or a plain PortFrame): the rule, on a page that is no
    pop-up of another site (page_may_upload)."""
    own, ancestors = chain(frame)
    return may_upload(own, ancestors) and page_may_upload(frame.page)


def page_may_upload(page) -> bool:
    """A pop-up takes a file only when every page up its chain of openers is of its own origin (PR 556's reviews): a
    frame of another site on the form's page could open one, or one that opens another, and a pop-up is a top frame,
    which the rule lets take a file. Playwright knows the opener even where the page has none (COOP, noopener)."""
    own, seen = origin(page.url), 0
    while seen < 20:
        opener = getattr(page, "opener", None)
        try:
            page = opener() if callable(opener) else None
        except Exception:
            return False
        if page is None:
            return True
        if origin(page.url) != own:
            return False
        seen += 1
    return False


def host_of(frame) -> str:
    own, ancestors = chain(frame)
    url = ancestors[0] if own.startswith("about:") and ancestors else own
    return urlsplit(url).hostname or ""


def hosts() -> list[str]:
    """The hosts the worker extension's checks take with each set (a plain Worker)."""
    return list(JOB_SYSTEM_HOSTS)


def give(target, files) -> None:
    """Set `files` on `target`, a Locator or a FileChooser, only where a file may go; else raise Elsewhere.

    A plain Worker's (apply.plain) checks in the frame itself as it sets. A CDP Worker's: the input's ElementHandle
    is taken first, so the frame read is the handle's own document's; a navigation after that ends the handle, and
    the set fails with nothing given."""
    if getattr(target, "plain", False) or type(target).__module__.startswith("apply.plain"):
        target.set_input_files(files) if hasattr(target, "set_input_files") else target.set_files(files)
        return
    handle = target.element if hasattr(target, "set_files") else target.element_handle(timeout=5_000)
    frame = handle.owner_frame()
    if frame is None or not frame_may_upload(frame):
        raise Elsewhere(host_of(frame) if frame is not None else "")
    handle.set_input_files(files)
