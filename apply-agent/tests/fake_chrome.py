"""A plain Worker's Chrome, played by Python, for tests of how a native messaging host finds its Chrome
(host.browser_of): `command(profile, *rest)` is a process with `--user-data-dir=<profile>` that runs `rest`
through a process between them, as Chrome on Windows starts a .bat host through cmd.exe. Both pass on their
stdin and stdout, and end when `rest` ends."""

import sys

SHELL = "import subprocess, sys; sys.exit(subprocess.call(sys.argv[1:]))"  # cmd.exe: no --user-data-dir
CHROME = f"import subprocess, sys; sys.exit(subprocess.call([sys.executable, '-c', {SHELL!r}, *sys.argv[2:]]))"


def command(profile, *rest: str) -> list[str]:
    return [sys.executable, "-c", CHROME, f"--user-data-dir={profile}", *rest]
