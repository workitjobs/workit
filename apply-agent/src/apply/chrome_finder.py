"""The Chrome finder (W4, KAN-850): where Google Chrome and Playwright's Chrome for Testing are on macOS, Windows
and Linux, which version Chrome is, and the user agent a Worker gives.

Every caller finds Chrome here: the Workers' Chromes (apply.browsers, apply.plain.launcher), the student's everyday
Chrome (captcha.to_everyday_chrome) and `apply doctor`. No general library finds an installed Chrome (Playwright's
channel "chrome" finds it only as it launches one), so each OS has its own entry, picked by `system`
(sys.platform's "darwin" or "win32", else Linux). A test passes each OS's name and gets that OS's paths.
"""

import os
import plistlib
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

import platformdirs

MAC, WINDOWS = "darwin", "win32"  # sys.platform's names; any other system is Linux here
VERSION = re.compile(r"\d+(?:\.\d+){3}")  # Chrome's version: 142.0.7444.60
NO_CHROME = "Google Chrome isn't installed: install it from https://www.google.com/chrome/"

# Chrome's own user agent names one fixed platform for each OS (Chrome's user-agent reduction), whatever the OS's
# own version is. A Worker says the same, so its user agent agrees with its navigator.platform.
UA_PLATFORMS = {MAC: "Macintosh; Intel Mac OS X 10_15_7", WINDOWS: "Windows NT 10.0; Win64; x64"}
LINUX_UA = "X11; Linux x86_64"
UA_MAJOR = "141"  # when Chrome's version can't be read

# Chrome for Testing's binary inside one of Playwright's chromium-<revision> folders, on each OS.
FOR_TESTING = {MAC: "chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
               WINDOWS: "chrome-win*/chrome.exe"}
FOR_TESTING_LINUX = "chrome-linux*/chrome"


def places(system: str = sys.platform, env: Mapping[str, str] = os.environ, home: Path | None = None,
           which: Callable[[str], str | None] = shutil.which) -> list[Path]:
    """Where Google Chrome's binary can be on `system`, the first choice first.

    - macOS: the app in /Applications, then in the student's own ~/Applications (a Mac with no admin rights).
    - Windows: Program Files (a machine-wide install), the 32-bit Program Files, then the student's own
      %LOCALAPPDATA% (a per-user install).
    - Linux: `google-chrome`, then `google-chrome-stable`, on the PATH (Google's .deb and .rpm put both there)."""
    if system == MAC:
        return [Path(root) / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome"
                for root in ("/Applications", (home or Path.home()) / "Applications")]
    if system == WINDOWS:
        return [Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe"
                for root in (env.get("PROGRAMFILES"), env.get("PROGRAMFILES(X86)"), env.get("LOCALAPPDATA")) if root]
    return [Path(found) for name in ("google-chrome", "google-chrome-stable") if (found := which(name))]


def find(system: str = sys.platform, env: Mapping[str, str] = os.environ, home: Path | None = None,
         which: Callable[[str], str | None] = shutil.which) -> Path | None:
    """The installed Google Chrome's binary, or None when there is none."""
    return next((path for path in places(system, env, home, which) if path.is_file()), None)


def version(binary: Path | None, system: str = sys.platform,
            run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> str | None:
    """`binary`'s Chrome version, or None when it can't be read.

    - macOS: the app's Info.plist (…/Google Chrome.app/Contents/Info.plist), which starts nothing.
    - Windows: chrome.exe sits beside a folder named for its version (Application/142.0.7444.60/); the newest wins.
    - Linux: `google-chrome --version` ("Google Chrome 142.0.7444.59")."""
    if binary is None:
        return None
    if system == MAC:
        try:
            return str(plistlib.loads((binary.parents[1] / "Info.plist").read_bytes())["CFBundleShortVersionString"])
        except (OSError, KeyError, IndexError, plistlib.InvalidFileException):
            return None
    if system == WINDOWS:
        try:
            named = [p.name for p in binary.parent.iterdir() if p.is_dir() and VERSION.fullmatch(p.name)]
        except OSError:
            return None
        return max(named, key=lambda name: tuple(map(int, name.split("."))), default=None)
    try:
        said = run([str(binary), "--version"], capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    found = VERSION.search(said or "")
    return found.group() if found else None


def user_agent(binary: Path | None = None, system: str = sys.platform) -> str:
    """The user agent installed Chrome gives in a window on `system`. Headless Chrome says "HeadlessChrome", which
    job sites' bot checks look for, so a headless Worker says this instead."""
    major = (version(binary or find(system), system) or UA_MAJOR).split(".")[0]
    platform = UA_PLATFORMS.get(system, LINUX_UA)
    return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"


def playwright_browsers(env: Mapping[str, str] = os.environ) -> Path:
    """Where Playwright keeps the browsers it installs: $PLAYWRIGHT_BROWSERS_PATH, else ms-playwright in the OS's
    cache folder. platformdirs gives that folder as Playwright picks it: ~/Library/Caches on macOS, %LOCALAPPDATA%
    on Windows, $XDG_CACHE_HOME or ~/.cache on Linux."""
    return Path(env.get("PLAYWRIGHT_BROWSERS_PATH") or platformdirs.user_cache_path() / "ms-playwright")


def chrome_for_testing(root: Path | None = None, system: str = sys.platform) -> Path:
    """The newest Chrome for Testing that Playwright installed under `root` (default: playwright_browsers())."""
    root = root or playwright_browsers()
    found = sorted(root.glob(f"chromium-*/{FOR_TESTING.get(system, FOR_TESTING_LINUX)}"),
                   key=lambda p: int(p.parts[len(root.parts)].split("-")[1]))
    if not found:
        raise FileNotFoundError(f"no Chrome for Testing under {root}: run `uv run playwright install chromium`")
    return found[-1]
