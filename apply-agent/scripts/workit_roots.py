"""Write src/apply/workit_roots.py: the only certificate authorities Apply trusts for api.workitjobs.ai (D28, W7).

    uv run python scripts/workit_roots.py            write it
    uv run python scripts/workit_roots.py --check    connect to each pinned host with only these roots

Cloudflare issues api.workitjobs.ai's certificate, and Supabase's (behind Cloudflare too), from Let's Encrypt,
Google Trust Services or SSL.com, and its backup certificates from Sectigo (https://developers.cloudflare.com/ssl/reference/certificate-authorities/,
read 2026-11-15). This takes those CAs' roots from certifi's copy of Mozilla's list, by subject, so the file holds
Mozilla's bytes and nothing typed by hand. Run it again when Cloudflare's list changes, and ship the app: a
pinned set the live chain is not in stops every student's app. `--check` tells you (the tests never reach the
network, tests/network_block.py).
"""

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import certifi

OUT = Path(__file__).resolve().parents[1] / "src" / "apply" / "workit_roots.py"
ROOTS = (
    "ISRG Root X1", "ISRG Root X2",  # Let's Encrypt
    "GTS Root R1", "GTS Root R2", "GTS Root R3", "GTS Root R4",  # Google Trust Services
    "SSL.com TLS RSA Root CA 2022", "SSL.com TLS ECC Root CA 2022",  # SSL.com
    "SSL.com Root Certification Authority RSA", "SSL.com Root Certification Authority ECC",
    "USERTrust RSA Certification Authority", "USERTrust ECC Certification Authority",  # Sectigo: backups
    "Sectigo Public Server Authentication Root R46", "Sectigo Public Server Authentication Root E46",
)


def check() -> None:
    sys.path.insert(0, str(OUT.parents[1]))
    from apply import workit

    for url in (workit.LIVE.api + "/health", workit.LIVE.auth + "/auth/v1/health"):
        request = urllib.request.Request(url, headers={"User-Agent": workit.USER_AGENT, "apikey": workit.LIVE.anon_key})
        try:
            urllib.request.urlopen(request, timeout=20, context=workit._pinned(url)).close()
        except urllib.error.HTTPError as answer:  # any HTTP answer: the TLS handshake, the part that's pinned, passed
            print(f"{url}: {answer.code}, its chain is in the pinned set")
        else:
            print(f"{url}: its chain is in the pinned set")


def main() -> None:
    if "--check" in sys.argv:
        check()
        return
    text = Path(certifi.where()).read_text()
    found = {}
    for block in re.findall(r"(# Issuer: .*?-----END CERTIFICATE-----\n)", text, re.DOTALL):
        subject = re.search(r"^# Subject: CN=(.*?)(?: O=| OU=|$)", block, re.MULTILINE)  # some roots have no CN
        if subject and (name := subject.group(1)) in ROOTS:
            found[name] = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----\n", block, re.DOTALL).group(0)
    pem = "".join(f"# {name}\n{found[name]}" for name in ROOTS if name in found)
    OUT.write_text(
        '"""The certificate authorities Apply trusts for api.workitjobs.ai, and no others (D28, W7): Cloudflare\'s\n'
        f"CAs. Written by scripts/workit_roots.py from certifi {certifi.__version__}; never edit by hand.\n"
        f'Not in it: {", ".join(n for n in ROOTS if n not in found) or "none"}."""\n\n'
        f'ROOTS = """{pem}"""\n'
    )
    print(f"{len(found)} roots to {OUT}")


if __name__ == "__main__":
    main()
