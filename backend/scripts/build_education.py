"""
Build the lists the Education form suggests from (app/services/education_lists.py):

    data/schools.tsv           schools, from two sources:
        HD<year>.zip           IPEDS's institution directory (US Department of
                               Education, public domain): every US school that
                               grants degrees and is open, with its aliases
        world_universities_and_domains.json
                               Hipo's university-domains-list (MIT license):
                               universities outside the US
    data/fields_of_study.tsv   fields of study, from CIPCode2020.csv: the
                               Classification of Instructional Programs, the
                               US Department of Education's list of majors

    uv run python scripts/build_education.py               download, then build
    uv run python scripts/build_education.py --src DIR     build from files in DIR

Re-run it once a year to refresh the data (IPEDS publishes a new directory
each year; raise IPEDS_YEAR when it does); the output is committed, so the API
never downloads anything. Stdlib only.

College Scorecard, the API the plan named first, is built from this same
IPEDS directory and needs an api.data.gov key; the directory's file needs
none.
"""

import argparse
import csv
import datetime
import io
import json
import re
import tempfile
import urllib.request
import zipfile
from pathlib import Path

IPEDS_YEAR = 2023
SOURCES = {
    f"HD{IPEDS_YEAR}.zip": f"https://nces.ed.gov/ipeds/datacenter/data/HD{IPEDS_YEAR}.zip",
    "world_universities_and_domains.json": (
        "https://raw.githubusercontent.com/Hipo/university-domains-list/master/"
        "world_universities_and_domains.json"
    ),
    "CIPCode2020.csv": "https://nces.ed.gov/ipeds/cipcode/Files/CIPCode2020.csv",
}
DATA = Path(__file__).resolve().parents[1] / "data"
SCHOOLS_OUT = DATA / "schools.tsv"
FIELDS_OUT = DATA / "fields_of_study.tsv"

# CIP families that are not majors a student studies toward a degree in:
# basic skills, citizenship, health and leisure courses (32 to 37), high
# school diplomas (53), and medical residencies (60, 61).
SKIP_FAMILIES = {"32", "33", "34", "35", "36", "37", "53", "60", "61"}


def _download(dest: Path) -> None:
    for name, url in SOURCES.items():
        request = urllib.request.Request(url, headers={"User-Agent": "workit-build-education"})
        with urllib.request.urlopen(request, timeout=60) as resp:
            (dest / name).write_bytes(resp.read())


def _clean(field: str) -> str:
    # Tabs and pipes are this file's separators; a stray one would shift every
    # column after it.
    return re.sub(r"\s+", " ", field.replace("\t", " ").replace("|", " ")).strip()


def _aliases(raw: str, name: str) -> list[str]:
    # IPEDS's IALIAS is free text: "SBU | Stony Brook | SUNY at Stony Brook",
    # or commas. Each alias is kept once, never the name again.
    seen = {name.casefold()}
    out = []
    for part in re.split(r"[|,;]", raw):
        alias = _clean(part)
        if len(alias) >= 2 and alias.casefold() not in seen:
            seen.add(alias.casefold())
            out.append(alias)
    return out


def build_schools(src: Path) -> list[str]:
    rows: dict[str, tuple[int, str]] = {}

    with zipfile.ZipFile(src / f"HD{IPEDS_YEAR}.zip") as zf:
        member = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        # IPEDS writes Windows-1252.
        text = io.TextIOWrapper(zf.open(member), encoding="cp1252", newline="")
        for row in csv.DictReader(text):
            row = {k.strip().upper(): (v or "").strip() for k, v in row.items() if k}
            # Degree-granting and open this year: a beauty school or a closed
            # campus is no student's "where do you go to school?".
            if row.get("DEGGRANT") != "1" or row.get("CYACTIVE") != "1":
                continue
            name = _clean(row["INSTNM"])
            # Four-year schools first among equal matches, then two-year.
            level = {"1": 0, "2": 1}.get(row.get("ICLEVEL", ""), 2)
            place = ", ".join(p for p in (_clean(row.get("CITY", "")), row.get("STABBR", "")) if p)
            aliases = "|".join(_aliases(row.get("IALIAS", ""), name))
            key = name.casefold()
            line = "\t".join(["us", str(level), name, place, aliases])
            if key not in rows or level < rows[key][0]:
                rows[key] = (level, line)

    world = json.loads((src / "world_universities_and_domains.json").read_text(encoding="utf-8"))
    for school in world:
        # IPEDS has every US school and their real names; Hipo's US rows are
        # fewer and sometimes older names.
        if school.get("alpha_two_code") == "US":
            continue
        name = _clean(school.get("name") or "")
        key = name.casefold()
        if not name or key in rows:
            continue
        region = _clean(school.get("state-province") or "")
        place = ", ".join(p for p in (region, _clean(school.get("country") or "")) if p)
        rows[key] = (3, f"world\t3\t{name}\t{place}\t")

    return [line for _, line in sorted(rows.values(), key=lambda r: r[1].split("\t")[2].casefold())]


def build_fields(src: Path) -> list[str]:
    titles: dict[str, str] = {}
    # The CIP file starts with a byte order mark and quotes every cell
    # ('="11.0701"' in some years): both are stripped.
    text = (src / "CIPCode2020.csv").read_text(encoding="utf-8-sig")
    for row in csv.DictReader(io.StringIO(text)):
        code = re.sub(r'[="\s]', "", row.get("CIPCode", ""))
        # Six-digit programs only ("11.0701"): the two- and four-digit rows
        # are families and series, not majors.
        if not re.fullmatch(r"\d{2}\.\d{4}", code) or code[:2] in SKIP_FAMILIES:
            continue
        if "deleted" in (row.get("Action") or "").lower():
            continue
        title = _clean(row.get("CIPTitle", "")).rstrip(".")
        # "Economics, General" is how a student says "Economics"; "Computer
        # Science, Other" is no major anyone names.
        if title.endswith((", Other", " Other")):
            continue
        title = re.sub(r",\s*General$", "", title)
        if title and title.casefold() not in titles:
            titles[title.casefold()] = f"{code}\t{title}"
    return sorted(titles.values(), key=lambda line: line.split("\t")[1].casefold())


def build(src: Path) -> None:
    built = datetime.datetime.now(datetime.UTC).date().isoformat()
    schools = build_schools(src)
    SCHOOLS_OUT.write_text(
        "\n".join(
            [
                f"# US schools from IPEDS's HD{IPEDS_YEAR} directory (US Department of Education, public domain);",
                "# schools elsewhere from Hipo's university-domains-list (MIT license, github.com/Hipo/university-domains-list).",
                f"# Built by scripts/build_education.py on {built}. Never edit by hand.",
                "# source<TAB>rank (0 four-year, 1 two-year, 2 other US, 3 outside the US)<TAB>name<TAB>place<TAB>aliases, |-separated",
                *schools,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fields = build_fields(src)
    FIELDS_OUT.write_text(
        "\n".join(
            [
                "# Fields of study from CIP 2020, the Classification of Instructional Programs",
                "# (US Department of Education, public domain); ', General' dropped, ', Other' rows left out.",
                f"# Built by scripts/build_education.py on {built}. Never edit by hand.",
                "# CIP code<TAB>title",
                *fields,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(schools)} schools -> {SCHOOLS_OUT}")
    print(f"{len(fields)} fields of study -> {FIELDS_OUT}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--src", type=Path, help="build from these files instead of downloading")
    args = parser.parse_args()
    if args.src:
        build(args.src)
        return
    with tempfile.TemporaryDirectory() as tmp:
        _download(Path(tmp))
        build(Path(tmp))


if __name__ == "__main__":
    main()
