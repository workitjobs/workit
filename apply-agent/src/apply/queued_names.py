"""What names a link that waits to start in a run (dashboard.QUEUED_JOB) when no queue named it: a link the student
sent in (`apply app <link>`) or pasted. Its row in the window then shows the company, the role and the logo as soon as
it waits, not its host till its form starts filling.

Each link is named in the background (Dashboard.names_by), with plain reads only and never a browser:

1. WorkIt's own job, when WorkIt lists the link (POST /jobs/listed-by-link, then GET /jobs/{id}): its company, title
   and logo sources, as the queue gives them.
2. Else its job system, as a fill names it (request.resolve: Greenhouse's, Lever's and Ashby's APIs, Workday's Feed,
   with zero tokens), and a company careers page that names its Greenhouse job (`?gh_jid=`, or the job id in its path)
   by Greenhouse's job API (greenhouse.board_behind). Such a page is the employer's own site, so its registered domain
   is the logo's (`company_domain`): a host, never a guess from a company's name (window/src/logo.ts).

A link nothing names gets {}: its row keeps the host and a letter tile."""

import urllib.request
from collections.abc import Callable
from dataclasses import replace
from urllib.parse import urlsplit

from apply import greenhouse, request, workit
from apply.browsers import USER_AGENT
from apply.dashboard import QUEUED_JOB
from apply.model import Posting

TIMEOUT = 15  # seconds for each read: a slow job board leaves the row on its host a while, and the run never waits


class Fetches:
    """A JobSite that only reads (a GET, or a JSON POST that only reads): naming a link opens no browser."""

    def fetch(self, url: str, body: bytes | None = None) -> bytes:
        headers = {"User-Agent": USER_AGENT} | ({"Content-Type": "application/json"} if body else {})
        with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=TIMEOUT) as answer:
            return answer.read()

    def open(self, url: str, worker: int = 0):
        raise RuntimeError("Naming a queued link opens no browser.")


def namer(client: workit.WorkIt, site=None) -> Callable[[str], dict]:
    """names() for each link, with the student's WorkIt and a fetch-only site."""
    site = site or Fetches()
    return lambda link: names(link, client, site)


def names(link: str, client: workit.WorkIt, site) -> dict:
    """The QUEUED_JOB of `link` (only what was found), WorkIt's first; {} when nothing names it."""
    return from_workit(link, client) or from_job_system(link, site)


def from_workit(link: str, client: workit.WorkIt) -> dict:
    """WorkIt's job at `link`, when WorkIt lists it: its company, title and logo sources. {} when signed out, unlisted
    or unreachable."""
    try:
        listed = client.listed_by_link(link)
        job = client.call("GET", f"/jobs/{listed[0]}") if listed else {}
    except Exception:
        return {}
    return {key: job[key] for key in QUEUED_JOB if isinstance(job, dict) and job.get(key)}


def from_job_system(link: str, site) -> dict:
    """The company and role `link`'s job system names, and a careers page's own domain when Greenhouse's job is
    behind it; {} when none names them."""
    try:
        posting, ended = request.resolve(link, site)
        named = _behind(posting, site) if ended is None and not (posting.company and posting.title) else posting
    except Exception:
        return {}
    found = {"company": named.company, "title": named.title}
    if posting.job_system == "other" and named.url != posting.url and found["company"]:
        # Greenhouse has the job of the careers page at `link`: the employer's own site
        found["company_domain"] = registered_domain(urlsplit(posting.url).hostname or "")
    return {key: value for key, value in found.items() if value}


def _behind(posting: Posting, site) -> Posting:
    """`posting` named by the Greenhouse job its careers page names, with that job's link; as it is otherwise."""
    behind = greenhouse.board_behind(posting, site)
    if behind == posting:
        return posting
    form = request.resolve(behind.url, site)[0]
    return replace(behind, company=form.company or posting.company, title=form.title or posting.title)


def registered_domain(host: str) -> str:
    """The name a company registered (`careers.airbnb.com` -> `airbnb.com`, `intel.co.uk` kept whole), as Brandfetch
    knows it: the scraper's own rule (scraper/workit_scraper/logos.py), not the public suffix list."""
    labels = host.lower().strip(".").split(".")
    second = ("ac", "co", "com", "edu", "gov", "net", "org")
    n = 3 if len(labels) > 2 and len(labels[-1]) == 2 and labels[-2] in second else 2
    return ".".join(labels[-n:])
