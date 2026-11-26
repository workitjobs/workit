"""Third-party notices for WorkIt Auto Apply (KAN-723, W10 of docs/desktop_application_auto_apply.md).

    uv run python scripts/third_party_notices.py [--out dist/THIRD-PARTY-NOTICES.txt] [--strict]

Writes one plain-text file with the license of each part of other people's software the app ships:

1. Apply's Python packages without the dev group, read by pip-licenses from a new environment built
   from uv.lock (`uv export --no-dev`). A dev tool never lands in the file, and a package added to
   pyproject.toml lands in it with no edit here.
2. Playwright's driver: Node.js and playwright-core, from the driver's own license and notice files.
3. Python itself (Nuitka compiles its runtime into the app), from the interpreter's LICENSE.txt.
4. BY_HAND: what no Python package gives, each with its license name. A hand entry whose package
   pip-licenses already lists is left out, so pywebview's entry goes by itself once W5 adds it to
   the dependencies. The full text of a hand entry comes from legal/licenses/<file>; until that
   file exists the entry says so, and --strict fails (W8's build runs with --strict).

Run it on the Mac that builds the app: packages resolve for the platform the script runs on. It
needs uv and the network (uvx fetches pip-licenses; the new environment downloads the packages).
"""

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSES = ROOT / "legal" / "licenses"
RULE = "=" * 78
THIN = "-" * 78


@dataclass(frozen=True)
class Part:
    name: str
    license: str
    url: str = ""
    version: str = ""
    text: str = ""
    note: str = ""


@dataclass(frozen=True)
class Hand:
    name: str
    license: str
    url: str
    file: str  # the full text, under legal/licenses/
    note: str
    package: str = ""  # its Python package, once Apply depends on it


BY_HAND = (
    Hand("pywebview", "BSD-3-Clause (Copyright (c) 2014-2017, Roman Sirokov)",
         "https://github.com/r0x0r/pywebview", "pywebview-LICENSE.txt",
         "The app's window (W5). pip-licenses lists it once pyproject.toml names it.", package="pywebview"),
    Hand("Sparkle", "MIT, with notices for the code it includes: bsdiff and bspatch (BSD), sais-lite (MIT), "
         "Ed25519 (zlib) and SUSignatureVerifier (BSD)", "https://github.com/sparkle-project/Sparkle",
         "Sparkle-LICENSE.txt",
         "The app's updater (W8): a macOS framework, not a Python package. Copy LICENSE from the Sparkle "
         "release the build uses."),
    Hand("Nuitka runtime", "AGPL-3.0, with the Nuitka runtime exception: the compiled app is not bound by the "
         "AGPL", "https://nuitka.net/", "Nuitka-LICENSE-RUNTIME.txt",
         "Nuitka compiles the app (W8) and puts its runtime code in it. Copy LICENSE-RUNTIME from the Nuitka "
         "release the build uses."),
    Hand("Latin Modern Roman fonts", "GUST Font License (c) 2003-2009 B. Jackowski and J. M. Nowacki (GUST)",
         "http://www.gust.org.pl/fonts/licenses/GUST-FONT-LICENSE.txt", "GUST-FONT-LICENSE.txt",
         "The cover letters' font (src/apply/fonts/README.md)."),
    # The student page (window/, built into src/apply/student_page/index.html) carries these inside it.
    Hand("Inter", "SIL Open Font License 1.1 (c) 2016 The Inter Project Authors", "https://github.com/rsms/inter",
         "Inter-LICENSE.txt", "The student page's font (its Latin subset). Copy LICENSE from "
         "window/node_modules/@fontsource-variable/inter."),
    Hand("React", "MIT (c) Meta Platforms, Inc. and affiliates", "https://react.dev/", "React-LICENSE.txt",
         "The student page: react, react-dom and scheduler. Copy LICENSE from window/node_modules/react."),
    Hand("Phosphor Icons", "MIT (c) 2020 Phosphor Icons", "https://phosphoricons.com/", "Phosphor-LICENSE.txt",
         "The student page's icons. Copy LICENSE from window/node_modules/@phosphor-icons/react."),
    Hand("Tailwind CSS", "MIT (c) Tailwind Labs, Inc.", "https://tailwindcss.com/", "Tailwind-LICENSE.txt",
         "The student page's base styles. Copy LICENSE from window/node_modules/tailwindcss."),
)


def by_hand(listed: set[str], licenses: Path = LICENSES) -> tuple[list[Part], list[str]]:
    """The hand entries pip-licenses doesn't list, and the license files they still lack."""
    parts, missing = [], []
    for hand in BY_HAND:
        if hand.package and hand.package.lower() in listed:
            continue
        path = licenses / hand.file
        text = path.read_text() if path.is_file() else ""
        if not text:
            missing.append(f"legal/licenses/{hand.file}")
        parts.append(Part(hand.name, hand.license, hand.url, text=text or f"LICENSE TEXT MISSING: add "
                          f"legal/licenses/{hand.file}.", note=hand.note))
    return parts, missing


def packages(rows: list[dict]) -> list[Part]:
    """pip-licenses' JSON rows as parts, without Apply itself."""
    return [Part(row["Name"], row["License"], "" if row.get("URL") == "UNKNOWN" else row.get("URL", ""),
                 row.get("Version", ""),
                 "\n\n".join(t for t in (row.get("LicenseText"), row.get("NoticeText")) if t and t != "UNKNOWN"))
            for row in sorted(rows, key=lambda r: r["Name"].lower()) if row["Name"].lower() != "apply"]


def driver(folder: Path) -> list[Part]:
    """Playwright's driver: Node.js's license, and playwright-core's with the files beside its bundles."""
    core = folder / "package"
    texts = [core / "LICENSE", core / "NOTICE", core / "ThirdPartyNotices.txt", *sorted((core / "lib").rglob("*.LICENSE"))]
    return [
        Part("Node.js (in Playwright's driver)", "MIT, with the licenses of the code Node.js includes",
             "https://nodejs.org/", text=(folder / "LICENSE").read_text()),
        Part("playwright-core (in Playwright's driver)", "Apache-2.0, with the licenses of the code its bundles include",
             "https://github.com/microsoft/playwright",
             text="\n\n".join(f"{THIN}\n{p.relative_to(folder)}\n{THIN}\n{p.read_text()}" for p in texts if p.is_file())),
    ]


def render(parts: list[Part], made: date) -> str:
    head = [
        "WorkIt Auto Apply: third-party notices",
        "",
        "WorkIt Auto Apply includes the software below. Each part keeps its own license, and its license text",
        "follows. The rest of the app is under the app's own license (EULA.txt). Where a license asks us to say",
        "where its source code is (certifi's MPL-2.0, for one), the link with each part names it.",
        "",
        f"Made {made.isoformat()} by apply-agent/scripts/third_party_notices.py from apply-agent/uv.lock.",
        "",
        "Contents",
        *(f"  {p.name}{' ' + p.version if p.version else ''}: {p.license}" for p in parts),
    ]
    body = []
    for p in parts:
        body += ["", RULE, f"{p.name}{' ' + p.version if p.version else ''}", f"License: {p.license}"]
        body += [f"Source: {p.url}"] if p.url else []
        body += [p.note] if p.note else []
        body += [THIN, p.text.strip() or "(This package ships no license file: see its link above.)"]
    return "\n".join(head + body) + "\n"


# Run in the new environment: where its Playwright driver and its Python's license are, and its Python's version.
WHERE = """import json, pathlib, platform, sysconfig, playwright
print(json.dumps([str(pathlib.Path(playwright.__file__).parent / "driver"),
                  str(pathlib.Path(sysconfig.get_paths()["stdlib"]) / "LICENSE.txt"), platform.python_version()]))"""


def _run(*command: str, cwd: Path = ROOT) -> str:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout


def build() -> tuple[str, list[str]]:
    with tempfile.TemporaryDirectory() as tmp:
        env, requirements = Path(tmp) / "env", Path(tmp) / "requirements.txt"
        _run("uv", "export", "--frozen", "--no-dev", "--no-hashes", "--no-emit-project", "--quiet",
             "--output-file", str(requirements))
        _run("uv", "venv", "--quiet", str(env))
        python = next(p for p in (env / "bin" / "python", env / "Scripts" / "python.exe") if p.exists())
        _run("uv", "pip", "install", "--quiet", "--python", str(python), "-r", str(requirements))
        rows = json.loads(_run("uvx", "pip-licenses", "--python", str(python), "--from=mixed", "--with-urls",
                               "--with-license-file", "--no-license-path", "--with-notice-file", "--format=json"))
        driver_folder, python_license, python_version = json.loads(_run(str(python), "-c", WHERE))
        driver_folder, python_license = Path(driver_folder), Path(python_license)
        listed = {row["Name"].lower() for row in rows}
        hand, missing = by_hand(listed)
        parts = [*packages(rows), *driver(driver_folder),
                 Part("Python", "PSF-2.0, with the licenses of the code Python includes", "https://www.python.org/",
                      python_version, python_license.read_text() if python_license.is_file() else ""),
                 *hand]
        return render(parts, datetime.now(UTC).date()), missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "THIRD-PARTY-NOTICES.txt")
    parser.add_argument("--strict", action="store_true", help="fail while a hand entry has no license file")
    args = parser.parse_args(argv)
    text, missing = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"wrote {args.out}")
    for path in missing:
        print(f"missing license text: {path}", file=sys.stderr)
    return 1 if args.strict and missing else 0


if __name__ == "__main__":
    sys.exit(main())
