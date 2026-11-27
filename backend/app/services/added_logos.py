"""
The logo of a job WorkIt doesn't list (an added job: KAN-515, Apply's
`track_only` writes, KAN-542): the two sources every card draws a logo from,
`company_domain` (Brandfetch's icon) and `company_logo_url` (the job board's
upload, or a favicon), as the scraper finds them for a listed job
(`../../../scraper/docs/logos.md`). An added job kept only its link, company
and title, so its card showed initials.

Two places, best first:

1. **A posting of the same company in the catalog** (`catalog_logo`): the
   scraper's own checked domain and logo, copied. The company is matched by
   its whole name, case aside, never a guess at a website.
2. **The employer's own site** (`own_site`): a link on a host no hiring
   system or job board shares (a careers page that shows a Greenhouse
   posting, `?gh_jid=`), whose registered domain is the employer's, as the
   scraper reads a board's redirect, with that site's favicon.

A link on a hiring system's or a job board's host gives no domain: its host
is the vendor's (`micron.eightfold.ai` gave Eightfold's logo).
"""

import re
from urllib.parse import quote, urlsplit

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_apply.hosts import AUTO_APPLY_HOSTS, JOB_BOARDS
from app.models.jobs import Job_Post

# Hosts many employers share, beside the hiring systems Apply fills and the
# job boards: other hiring systems, form tools and site hosts. A domain read
# from one of them is the vendor's (`acme.github.io` gave GitHub's icon).
OTHER_VENDORS = (
    # hiring systems
    "adp.com", "angel.co", "applicantpro.com", "applytojob.com", "avature.net", "bamboohr.com",
    "breezy.hr", "brassring.com", "careerplug.com", "csod.com", "dayforcehcm.com", "dover.com",
    "gem.com", "isolvedhire.com", "jazzhr.com", "jobvite.com", "paycomonline.net",
    "paylocity.com", "personio.com", "personio.de", "phenompeople.com", "pinpointhq.com",
    "recruitee.com", "recruitingbypaycor.com", "taleo.net", "teamtailor.com", "trinethire.com",
    "ukg.com", "ultipro.com", "workatastartup.com", "ycombinator.com",
    # forms and documents
    "airtable.com", "forms.gle", "forms.office.com", "google.com", "jotform.com", "notion.site",
    "tally.so", "typeform.com",
    # site hosts
    "github.io", "herokuapp.com", "netlify.app", "pages.dev", "squarespace.com", "vercel.app",
    "webflow.io", "wixsite.com",
)
VENDOR_HOSTS = (*AUTO_APPLY_HOSTS, *JOB_BOARDS, *OTHER_VENDORS)

# Google's favicon service, as the scraper reads a site's icon (a 404, so
# the card's initials, for a site with none); next.config.ts allows it.
FAVICON = "https://www.google.com/s2/favicons?"


def registered_domain(host: str) -> str:
    """The name a company registered (`careers.airbnb.com` -> `airbnb.com`,
    `intel.co.uk` kept whole): the scraper's rule (workit_scraper.logos),
    copied, since importing that module reads a CSV the installed copy lacks."""
    labels = host.lower().strip(".").split(".")
    second = ("ac", "co", "com", "edu", "gov", "net", "org")
    n = 3 if len(labels) > 2 and len(labels[-1]) == 2 and labels[-2] in second else 2
    return ".".join(labels[-n:])


# job_postings_company_domain's CHECK (app/models/jobs.py): a bare lower-case host.
_DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


def own_site(url: str) -> tuple[str, str] | None:
    """The employer's registered domain and its favicon, when `url` is on the
    employer's own site; None on a vendor's host or a link with no host."""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return None
    if not host or any(host == v or host.endswith(f".{v}") for v in VENDOR_HOSTS):
        return None
    domain = registered_domain(host)
    if not _DOMAIN.match(domain) or not domain.rsplit(".", 1)[-1].isalpha():  # an IP address has no domain
        return None
    return domain, f"{FAVICON}domain={quote(domain)}&sz=128"


def has_logo() -> ColumnElement[bool]:
    """A posting with either logo source."""
    return or_(Job_Post.company_domain.is_not(None), Job_Post.company_logo_url.is_not(None))


def same_company(pattern: str) -> ColumnElement[bool]:
    """A scraped posting (never another added job, whose logo is only a
    guess from its link) of the company `pattern` (an ILIKE pattern) names:
    whole name, case aside."""
    return (
        Job_Post.company_id.is_(None)
        & Job_Post.added_by_student.is_(False)
        & Job_Post.company_name.ilike(pattern)
    )


async def catalog_logo(db: AsyncSession, company: str) -> tuple[str | None, str | None]:
    """The domain and logo of a posting of `company` in the catalog that has
    one, the domain first; (None, None) when none has."""
    name = company.strip()
    if not name:
        return None, None
    escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    row = (await db.execute(
        select(Job_Post.company_domain, Job_Post.company_logo_url)
        .where(same_company(escaped), has_logo())
        .order_by(Job_Post.company_domain.is_(None), Job_Post.company_logo_url.is_(None), Job_Post.id)
        .limit(1)
    )).first()
    return (row.company_domain, row.company_logo_url) if row else (None, None)


async def added_logo(db: AsyncSession, url: str, company: str) -> tuple[str | None, str | None]:
    """The (company_domain, company_logo_url) to keep on a job added at `url`
    for `company`: the catalog's, else the employer's own site's, else none."""
    domain, logo = await catalog_logo(db, company)
    if domain or logo:
        return domain, logo
    return own_site(url) or (None, None)
