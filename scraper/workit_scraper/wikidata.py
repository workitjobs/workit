"""A company's website by its name, from Wikidata, for `checked_websites.csv`.

Many company job boards name no website (Workday, Oracle, iCIMS), so their cards
show initials (docs/logos.md, "Wikidata proposals"). Wikidata keeps a company's
official website (property P856) under its name, and its data is CC0, so an answer
may be stored and reused. A name is not a key ("CMS" is a law firm too), so an
answer counts only under the rules in `pick`, and even then it is only proposed:
`domain_pr.py` puts it in a pull request that a person reviews.

Not through `polite.Robots`: Wikidata's robots.txt disallows `/w/` to crawlers,
since its dynamic pages are costly to index, while Wikimedia's API etiquette
welcomes scripts that name themselves, ask one thing at a time and back off
(`maxlag`, `Retry-After`). This module asks only the API, never a page, and never
runs in the scrape.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

from workit_scraper import logos, web

API = "https://www.wikidata.org/w/api.php"
#: Seconds between requests: one at a time, as the API etiquette asks.
PACE_S = 1.0
#: Waits on a 429 or a `maxlag` answer before giving up on a name.
TRIES = 4
#: The longest a `Retry-After` may hold us, so one answer cannot stall a run.
LONGEST_WAIT_S = 60.0
#: Search results read per name. A company is almost always in the first few.
RESULTS = 10
TIMEOUT_S = 30.0

#: Words that only say what kind of legal body a company is: "CMS Energy
#: Corporation" is "CMS Energy". Dropped from the end of a name, repeatedly.
LEGAL = frozenset(
    {
        "inc",
        "incorporated",
        "llc",
        "llp",
        "lp",
        "corp",
        "corporation",
        "co",
        "company",
        "ltd",
        "limited",
        "plc",
        "sa",
        "ag",
        "nv",
        "gmbh",
    }
)
#: Properties read off each search result: its official website, the date it
#: was dissolved (a dissolved company is not the employer hiring now) and what
#: kind of thing it is.
WEBSITE, DISSOLVED, INSTANCE_OF = "P856", "P576", "P31"
#: Kinds of thing that are never an employer, though they share a company's
#: name and have a website. The 200-board trial of 2026-11-10 matched a
#: racehorse (Secretariat), a band (Black Box), a French commune (Arc) and a TV
#: channel (Freeform). Matched on the item's own "instance of", not its parents.
NOT_EMPLOYERS = frozenset(
    {
        "Q5",  # human
        "Q15632617",  # fictional human
        "Q95074",  # character
        "Q726",  # horse
        "Q10855242",  # racehorse
        "Q26401003",  # individual animal
        "Q215380",  # musical group
        "Q5741069",  # rock band
        "Q484170",  # commune of France
        "Q515",  # city
        "Q3957",  # town
        "Q532",  # village
        "Q486972",  # human settlement
        "Q1616075",  # television station
        "Q2001305",  # television channel
        "Q561068",  # specialty channel
        "Q15416",  # television program
        "Q5398426",  # television series
        "Q11424",  # film
        "Q482994",  # album
        "Q7366",  # song
        "Q7889",  # video game
        "Q571",  # book
        "Q13442814",  # scholarly article
        "Q101352",  # family name
        "Q202444",  # given name
        "Q4167410",  # Wikimedia disambiguation page
    }
)
#: Words a one-word company's domain may add to its name: `safran-group.com`
#: for Safran, `thecloroxcompany.com` for Clorox, `envistaco.com` for Envista.
DOMAIN_WORDS = ("group", "company", "co", "corp", "inc", "global", "holdings")


@dataclass(frozen=True)
class Answer:
    """What Wikidata gave for one company: its domain, and the item that names it
    with that item's description, which the review row shows. All None when no
    item passed the rules."""

    domain: str | None
    item: str | None = None
    description: str | None = None


NONE = Answer(None)


def key(name: str) -> str:
    """A name as compared: lower case, no parenthesis ("(SPA)"), "&" as "and", no
    trailing legal words, and no spaces or punctuation, so "U-Haul" is "Uhaul"."""
    name = re.sub(r"\([^)]*\)", " ", name.lower()).replace("&", " and ")
    words = re.findall(r"[a-z0-9]+", name)
    while len(words) > 1 and words[-1] in LEGAL:
        words.pop()
    if len(words) > 1 and words[0] == "the":
        words.pop(0)
    return "".join(words)


def query(name: str) -> str:
    """What is searched: the name without its parenthesis, which Wikidata's
    labels rarely carry."""
    return " ".join(re.sub(r"\([^)]*\)", " ", name).split())


def one_word(name: str) -> bool:
    return len(re.findall(r"[a-z0-9]+", query(name).lower())) == 1


def _site(claim: dict) -> str | None:
    value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
    return value if isinstance(value, str) else None


def website(item: dict) -> str | None:
    """The item's official website as one registered domain, or None: no website,
    a dissolved company, or websites on two different domains. Preferred-rank
    values win over normal ones; deprecated ones never count."""
    claims = item.get("claims", {})
    if claims.get(DISSOLVED):
        return None
    sites = [c for c in claims.get(WEBSITE, []) if c.get("rank") != "deprecated"]
    preferred = [c for c in sites if c.get("rank") == "preferred"]
    hosts = {urlsplit(s).hostname for s in map(_site, preferred or sites) if s}
    domains = {logos.registered_domain(host) for host in hosts if host}
    if len(domains) != 1:
        return None
    (domain,) = domains
    if domain in logos.VENDOR_DOMAINS or not logos.DOMAIN.fullmatch(domain):
        return None
    return domain


def kinds(item: dict) -> set[str]:
    """The item's "instance of" classes, as ids."""
    claims = item.get("claims", {}).get(INSTANCE_OF, [])
    values = (c.get("mainsnak", {}).get("datavalue", {}).get("value") for c in claims)
    return {v["id"] for v in values if isinstance(v, dict) and "id" in v}


def own_domain(company: str, domain: str) -> bool:
    """Whether a one-word company's domain is its own name: the domain's name,
    without punctuation and a leading "the", is the company's name, or that name
    and one of `DOMAIN_WORDS`. `krollshop.de` is not Kroll's, `chubbfs.com` not
    Chubb's and `teledyne-e2v.com` not Teledyne's: in the trial each was another
    company of the same name, or one of its parts."""
    label = re.sub(r"[^a-z0-9]", "", domain.split(".")[0])
    label = label.removeprefix("the") if label != "the" else label
    name = key(company)
    return label == name or any(label == name + word for word in DOMAIN_WORDS)


def _names(item: dict) -> set[str]:
    label = item.get("labels", {}).get("en", {}).get("value")
    aliases = [a.get("value") for a in item.get("aliases", {}).get("en", [])]
    return {key(n) for n in [label, *aliases] if n}


def pick(company: str, items: list[dict]) -> Answer:
    """The one website the items give for `company`, under these rules:

    - An item counts only when its English label or an alias is the company's
      name (`key`): "CMS" (a law firm) is not "CMS Energy".
    - It must name an official website, on one domain, and not be dissolved.
    - It must not be a kind of thing that never hires (`NOT_EMPLOYERS`): a
      racehorse, a band, a town, a TV channel.
    - Every counted item must agree on one domain, or the name is ambiguous and
      gives nothing. "Workshop" matched no company at all.
    - A one-word name is in too many names (Kroll, Chubb, Mercury), so its
      domain must also be its own name (`own_domain`: paccar.com for Paccar).
    """
    wanted = key(company)
    if not wanted:
        return NONE
    found: dict[str, Answer] = {}
    for item in items:
        if wanted not in _names(item) or kinds(item) & NOT_EMPLOYERS:
            continue
        domain = website(item)
        if domain is None or (one_word(company) and not own_domain(company, domain)):
            continue
        description = item.get("descriptions", {}).get("en", {}).get("value")
        found.setdefault(domain, Answer(domain, item.get("id"), description))
    if len(found) != 1:
        return NONE
    return next(iter(found.values()))


class Busy(Exception):
    """Wikidata asked us to wait longer than a run should: stop for today."""


def _ask(params: dict[str, str], sleep=time.sleep) -> dict:
    """One API call, paced, with `maxlag` so a busy server can turn us away, and
    its `Retry-After` honoured (capped) up to `TRIES` times."""
    url = f"{API}?{urlencode({**params, 'format': 'json', 'maxlag': '5'})}"
    for _ in range(TRIES):
        sleep(PACE_S)
        try:
            body = json.loads(web.get(url, timeout=TIMEOUT_S))
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503):
                raise
            wait = error.headers.get("Retry-After") if error.headers else None
            sleep(min(float(wait) if wait and wait.isdigit() else 5.0, LONGEST_WAIT_S))
            continue
        if body.get("error", {}).get("code") == "maxlag":
            sleep(5.0)
            continue
        return body
    raise Busy(f"Wikidata stayed busy for {params.get('action')}")


def look_up(company: str, sleep=time.sleep) -> Answer:
    """Search Wikidata for `company` and `pick` from what comes back: two calls,
    a search and one read of every result's labels, aliases and claims."""
    found = _ask(
        {
            "action": "wbsearchentities",
            "search": query(company),
            "language": "en",
            "type": "item",
            "limit": str(RESULTS),
        },
        sleep,
    )
    ids = [result["id"] for result in found.get("search", [])]
    if not ids:
        return NONE
    items = _ask(
        {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": "labels|aliases|descriptions|claims",
            "languages": "en",
        },
        sleep,
    )
    entities = items.get("entities", {})
    return pick(company, [entities[i] for i in ids if i in entities])
