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
from pathlib import Path

import platformdirs

from apply import build

APP_FOLDER = platformdirs.user_data_path("WorkIt Auto Apply", appauthor=False, roaming=False)
HOME = Path(os.environ.get("APPLY_HOME") or (APP_FOLDER if build.STUDENT else "~/.config/apply")).expanduser()
# The compiled app (Nuitka, W8) has no checkout: the build puts these inputs beside the program, and each compiled
# module's __file__ names its place there (Contents/MacOS/apply/home.py), one folder less deep than src/apply/.
CODE = Path(__file__).resolve().parents[1 if "__compiled__" in globals() else 2]
# The Story bank, read by essays, gates, stock answers and the story map: one path, so a test moves all of them.
STORY_BANK = HOME / "story-bank.md"
# The Test Person sample data: copied into a data folder that has no Applicant profile yet, never written to.
SAMPLE = CODE / "sample"
# Where a reboot wipes what lives there: held forms, notes and signed-in Worker profiles went this way on 2026-11-05.
TEMP_FOLDERS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
# A test run's own switch: its data folder is a temp one on purpose.
TEMP_OK = "APPLY_TEST_TEMP_OK"


def in_temp(path: Path) -> bool:
    """Whether a folder is under a temp path, by its name and by where its links lead (/tmp is /private/tmp). By
    path parts, not text: Windows' paths use backslashes, and its temp folder (tempfile.gettempdir) may come in its
    short 8.3 form, which resolve() writes long."""
    path = Path(path).expanduser()
    temps = [*map(Path, TEMP_FOLDERS), Path(tempfile.gettempdir()), Path(tempfile.gettempdir()).resolve()]
    return any(p.is_relative_to(t) for p in (path, path.resolve()) for t in temps)


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
