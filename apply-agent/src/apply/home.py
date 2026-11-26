"""Where Apply keeps data: the applicant's own files in one data folder, its code's inputs in the checkout.

HOME is $APPLY_HOME, else APP_FOLDER in the Student build, else ~/.config/apply. It holds everything personal (the
Applicant profile, Answer bank, Story bank, voice, policies override, company
briefs) and everything Apply writes (Traces, rehearsals, Repairs, Worker
profiles). Every data path derives from it, read once at import.

CODE is Apply's folder in the checkout (apply-agent/): only generic inputs live there (the
answering guides, the default policies, the profile template, and SAMPLE, the
Test Person data a first run starts from). In the compiled app it is the folder that
holds the program, where the build (scripts/build_app.py) puts the same inputs.

APP_FOLDER is WorkIt Auto Apply's data folder (D25), in each OS's standard place
as platformdirs gives it: ~/Library/Application Support/WorkIt Auto Apply on
macOS, %LOCALAPPDATA%/WorkIt Auto Apply on Windows (local, not roaming: a Worker
profile is a Chrome profile, which Chrome keeps there too), and $XDG_DATA_HOME or
~/.local/share, then WorkIt Auto Apply, on Linux. It is the Student build's HOME
(KAN-858); a Developer checkout keeps ~/.config/apply. HOME reads build.STUDENT
once, at import, as every path here is made: the build script writes STUDENT
before it compiles, so the compiled app's import already sees it.
"""

import os
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

import platformdirs

from apply import build

APP_FOLDER = platformdirs.user_data_path("WorkIt Auto Apply", appauthor=False, roaming=False)
HOME = Path(os.environ.get("APPLY_HOME") or (APP_FOLDER if build.STUDENT else "~/.config/apply")).expanduser()
# The compiled app (Nuitka, W8) has no checkout: the build puts these inputs beside the program, and each compiled
# module's __file__ names its place there (Contents/MacOS/apply/home.py), one folder less deep than src/apply/.
CODE = Path(__file__).resolve().parents[1 if "__compiled__" in globals() else 2]
# The Story bank, read by essays, gates, stock answers and the story map: one path, so a test moves all of them.
# Read it through story_bank(), which is WorkIt's in WorkIt Auto Apply.
STORY_BANK = HOME / "story-bank.md"
# The Test Person sample data: copied into a data folder that has no Applicant profile yet, never written to.
SAMPLE = CODE / "sample"
# Where a reboot wipes what lives there: held forms, notes and signed-in Worker profiles went this way on 2026-11-05.
TEMP_FOLDERS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
# A test run's own switch: its data folder is a temp one on purpose.
TEMP_OK = "APPLY_TEST_TEMP_OK"


def in_temp(path: Path) -> bool:
    """Whether a folder is under a temp path, by its name and by where its links lead (/tmp is /private/tmp)."""
    path = Path(path).expanduser()
    return any(p == t or p.startswith(t + "/") for p in (str(path), str(path.resolve())) for t in (*TEMP_FOLDERS, tempfile.gettempdir()))


def temp_state(profiles: Path) -> str | None:
    """Why this data folder or profiles folder can't hold live state, in one line; None when it can."""
    if os.environ.get(TEMP_OK):
        return None
    named = next(((name, f) for name, f in (("APPLY_HOME", HOME), ("the profiles folder (APPLY_PROFILES)", profiles)) if in_temp(f)), None)
    if not named:
        return None
    return (f"{named[0]} is {named[1]}, a temp folder, and a reboot wipes it: held forms, sign-ins and Records would be lost. "
            "Set APPLY_HOME and APPLY_PROFILES to a lasting folder, such as ~/.config/apply, or unset them.")


def fill_from_sample() -> bool:
    """On the first run (no Applicant profile in HOME), copy the sample into HOME, beside anything
    already there, and say so; True when it did."""
    if (HOME / "applicant-profile.yaml").exists():
        return False
    shutil.copytree(SAMPLE, HOME, dirs_exist_ok=True,
                    ignore=lambda folder, names: [n for n in names if (HOME / Path(folder).relative_to(SAMPLE) / n).is_file()])
    return True


@dataclass
class FromWorkIt:
    """WorkIt Auto Apply's Story bank and voice (W11): WorkIt's, read at each Start (student.profile_from_workit)
    and kept in memory, never in a file. A line a fill adds stays in memory until the next Start."""

    story_bank: str = ""
    voice: str = ""


WORKIT: FromWorkIt | None = None  # None in a Developer command: the data folder's files
_ADDING = threading.Lock()  # two Workers' lines at once: each read-and-add sees the other's


def story_bank() -> str:
    """The Story bank as essays read it: WorkIt's in WorkIt Auto Apply, else the data folder's story-bank.md, ""
    when there is none."""
    if WORKIT is not None:
        return WORKIT.story_bank
    return STORY_BANK.read_text() if STORY_BANK.is_file() else ""


def add_story_line(section: str, line: str, seen: str) -> bool:
    """`line` at the Story bank's end, under `section` (its heading line, then what it holds) unless the bank has
    that heading already, and not when `seen` is in the bank. In WorkIt Auto Apply only in memory, for the checks
    of the answer it was added for: WorkIt never keeps it. False when it was there."""
    with _ADDING:
        bank = story_bank()
        if seen in bank:
            return False
        if section.split("\n", 1)[0] not in bank:
            bank = f"{bank.rstrip()}\n\n{section}\n"
        bank = f"{bank.rstrip()}\n{line}\n"
        if WORKIT is None:
            STORY_BANK.write_text(bank)
            return True
        WORKIT.story_bank = bank
    return True
