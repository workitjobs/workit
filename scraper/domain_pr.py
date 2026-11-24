"""Propose company websites from Wikidata in one reviewed PR; never push to main.

Reads the boards whose jobs have no `company_domain` from the latest scheduled
scrape's `metrics.json` (`boards_without_domain`), looks each company up on
Wikidata (`workit_scraper.wikidata`), and adds a row to `checked_websites.csv`
for each one that passes the rules. A person reviews the rows in the PR and
removes any that are wrong; nothing reaches a card until the PR merges
(docs/logos.md, "Wikidata proposals").

Every board looked up goes into `company-domains.json`, answer or not, so a
board is asked once: a removed row is never proposed again, and a board with no
answer is asked again only after `RETRY_DAYS`. Without --publish, nothing leaves
this machine.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from workit_scraper import wikidata

PREFIX = "codex/company-domains-"
CHECKED = "scraper/checked_websites.csv"
LEDGER = "scraper/company-domains.json"
FILES = (CHECKED, LEDGER)
#: Boards looked up a run, most jobs first: two paced calls each, so about five
#: minutes. The 755 boards of 2026-11-09 take about five daily runs.
LIMIT = 150
#: Days before a board Wikidata had no answer for is asked again: a company's
#: item, or its website, can be added later.
RETRY_DAYS = 60
BOT = (
    "-c",
    "user.name=github-actions[bot]",
    "-c",
    "user.email=41898282+github-actions[bot]@users.noreply.github.com",
)


def command(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, encoding="utf-8").strip()


def git(root: Path, *args: str) -> str:
    return command(["git", *args], root)


def read_ledger(path: Path) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def checked_boards(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        return {row["board"] for row in rows}


def due(
    boards: list[dict], checked: set[str], ledger: dict[str, dict], today: date, limit: int
) -> list[dict]:
    """The boards to look up this run, in the metrics' order (most jobs first):
    not in the checked list, never looked up, or looked up with no answer more
    than `RETRY_DAYS` ago. A board with an answer is never asked again, so a row
    a reviewer removed stays removed."""
    picked = []
    for board in boards:
        key = board["board"]
        seen = ledger.get(key)
        if key in checked or (seen and seen.get("domain")):
            continue
        if seen and date.fromisoformat(seen["looked_up"]) > today - timedelta(days=RETRY_DAYS):
            continue
        picked.append(board)
    return picked[:limit]


def note(answer: wikidata.Answer, today: date) -> str:
    """The review row's note: the item, so a reviewer can open it, and its
    description, which usually says at a glance whether it is the employer."""
    about = f" ({answer.description})" if answer.description else ""
    return f"Wikidata {answer.item}{about} names it the official website; proposed {today}"


def add_rows(path: Path, rows: list[list[str]]) -> None:
    text = path.read_text(encoding="utf-8")
    with path.open("a", newline="", encoding="utf-8") as handle:
        if text and not text.endswith("\n"):
            handle.write("\n")
        csv.writer(handle, lineterminator="\n").writerows(rows)


def look_up_all(worktree: Path, boards: list[dict], today: date, look_up=wikidata.look_up) -> int:
    """Look up each board, record it in the ledger and add a row for each answer.
    Returns the rows added. Wikidata staying busy ends the run early, keeping
    what was found."""
    ledger = read_ledger(worktree / LEDGER)
    rows = []
    for board in boards:
        try:
            answer = look_up(board["company"])
        except wikidata.Busy as busy:
            print(f"Stopping early: {busy}")
            break
        ledger[board["board"]] = {
            "company": board["company"],
            "domain": answer.domain,
            "item": answer.item,
            "looked_up": today.isoformat(),
        }
        if answer.domain:
            rows.append([board["board"], answer.domain, board["company"], note(answer, today)])
            print(f"  {board['company']}: {answer.domain} ({answer.item})")
    add_rows(worktree / CHECKED, rows)
    (worktree / LEDGER).write_text(
        json.dumps(ledger, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return len(rows)


def latest_metrics(root: Path, repository: str, folder: Path) -> Path:
    """The newest scheduled scrape's metrics.json, from its artifact
    (`scrape-<run id>`, kept a week by scrape.yml)."""
    run_id = command(
        [
            "gh", "run", "list", "--repo", repository, "--workflow", "scrape.yml",
            "--event", "schedule", "--status", "success", "--limit", "1",
            "--json", "databaseId", "--jq", ".[0].databaseId",
        ],
        root,
    )  # fmt: skip
    if not run_id.isdigit():
        raise ValueError("No successful scheduled scrape to read metrics.json from")
    command(
        [
            "gh", "run", "download", run_id, "--repo", repository,
            "--name", f"scrape-{run_id}", "--dir", str(folder),
        ],
        root,
    )  # fmt: skip
    return folder / "metrics.json"


def pull_requests(root: Path, repository: str) -> list[dict]:
    pages = json.loads(
        command(
            [
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{repository}/pulls?state=all&base=main&per_page=100",
            ],
            root,
        )
    )
    return [
        pr
        for page in pages
        for pr in page
        if pr["head"]["ref"].startswith(PREFIX)
        and (pr["head"].get("repo") or {}).get("full_name") == repository
    ]


def current_pr(prs: list[dict]) -> dict | None:
    """The open proposal PR, or None to start a new one. A PR closed without
    merging pauses the runs: its ledger never reached main, so every board in
    it would be proposed again."""
    opened = [pr for pr in prs if pr["state"] == "open"]
    if len(opened) > 1:
        raise ValueError("Several company-domain PRs are open; close all but one")
    if opened:
        return opened[0]
    latest = max(prs, key=lambda pr: pr["number"], default=None)
    if latest and not latest.get("merged_at"):
        raise ValueError(
            "The last company-domain PR was closed without merging; reopen it, "
            "remove the rows you reject and merge it, ledger included"
        )
    return None


def next_branch(prs: list[dict]) -> str:
    return PREFIX + "after-" + str(max((pr["number"] for pr in prs), default=0))


BODY = """\
Company websites that Wikidata names for boards whose jobs show initials. Each \
row passed these rules: Wikidata's name for the item is the company's name, the \
item names one official website and is not dissolved, and only one website \
matched, and it is not a kind of thing that never hires (a person, a horse, \
a band, a town). A one-word company's domain must be its own name.

**Before merging, check each row's note**: the Wikidata item and its \
description. Remove a row from `scraper/checked_websites.csv` when it names \
another company (the same name, another business). A removed row is never \
proposed again. Keep `scraper/company-domains.json` in the merge: it records \
every board looked up, so none is asked twice.

A merged row reaches the cards at the next scrape. Daily runs add rows here \
until it merges. Closing it without merging pauses the runs.
"""


def publish(root: Path, worktree: Path, repository: str, branch: str, pr: dict | None) -> None:
    git(worktree, "add", "--", *FILES)
    staged = set(git(worktree, "diff", "--cached", "--name-only").splitlines())
    if staged - set(FILES):
        raise ValueError("Refusing to publish changes outside the company-domain files")
    if staged:
        git(worktree, *BOT, "commit", "-m", "chore(scraper): propose company websites")
    # A normal push: if a reviewer pushed meanwhile, it fails rather than
    # overwrite their edits, and the next run starts from them.
    git(worktree, "push", "origin", f"HEAD:refs/heads/{branch}")
    if pr:
        print(f"Updated {pr['html_url']}")
        return
    body = Path(worktree) / "company-domains-pr.txt"
    body.write_text(BODY, encoding="utf-8")
    print(
        command(
            [
                "gh", "pr", "create", "--repo", repository, "--base", "main",
                "--head", branch, "--title", "Review company websites from Wikidata",
                "--body-file", str(body),
            ],
            root,
        )
    )  # fmt: skip


def run(
    root: Path,
    repository: str,
    *,
    publishing: bool = False,
    metrics: Path | None = None,
    limit: int = LIMIT,
    look_up=wikidata.look_up,
) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("The repository must be an owner/name")
    prs = pull_requests(root, repository)
    pr = current_pr(prs)
    git(root, "fetch", "origin", "main")
    branch = pr["head"]["ref"] if pr else next_branch(prs)
    if not re.fullmatch(re.escape(PREFIX) + r"[A-Za-z0-9_-]+", branch):
        raise ValueError("Invalid company-domain branch name")
    start = "origin/main"
    if git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}"):
        git(root, "fetch", "origin", branch)
        start = "FETCH_HEAD"
    today = datetime.now(UTC).date()
    with tempfile.TemporaryDirectory(prefix="workit-domains-") as folder:
        worktree = Path(folder) / "review"
        git(root, "worktree", "add", "--detach", str(worktree), start)
        try:
            changed = set(git(worktree, "diff", "--name-only", "origin/main...HEAD").splitlines())
            if changed - set(FILES):
                raise ValueError("The proposal branch changes other files; fix it by hand")
            git(worktree, *BOT, "merge", "--no-edit", "origin/main")
            source = metrics or latest_metrics(root, repository, Path(folder) / "metrics")
            boards = json.loads(source.read_text(encoding="utf-8")).get("boards_without_domain", [])
            todo = due(
                boards,
                checked_boards(worktree / CHECKED),
                read_ledger(worktree / LEDGER),
                today,
                limit,
            )
            print(f"{len(boards)} boards without a domain; looking up {len(todo)}")
            if not todo:
                return 0
            added = look_up_all(worktree, todo, today, look_up)
            print(f"{added} rows proposed")
            if not publishing:
                print("Preview: nothing published")
                return 0
            if added or pr:
                publish(root, worktree, repository, branch, pr)
            else:
                # Only misses: nothing to review, but the ledger must be kept, or
                # the next run asks the same boards again. It waits on the
                # branch, and the first run with a row opens the PR there.
                git(worktree, "add", "--", LEDGER)
                git(worktree, *BOT, "commit", "-m", "chore(scraper): record company lookups")
                git(worktree, "push", "origin", f"HEAD:refs/heads/{branch}")
                print(f"Saved the lookups on {branch}; nothing to review yet")
            return 0
        finally:
            git(root, "worktree", "remove", "--force", str(worktree))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="push the branch and open the PR")
    parser.add_argument(
        "--metrics", type=Path, help="a metrics.json to read instead of the latest scrape's"
    )
    parser.add_argument("--limit", type=int, default=LIMIT, help="boards to look up this run")
    parser.add_argument("--repo", help="GitHub owner/name; defaults to this checkout's remote")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    repository = (
        args.repo
        or os.environ.get("GITHUB_REPOSITORY")
        or command(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], root
        )
    )
    return run(root, repository, publishing=args.publish, metrics=args.metrics, limit=args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
