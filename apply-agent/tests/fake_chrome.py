"""Chrome's side of a native messaging host, played for tests that need no browser.

- `command(profile, *rest)`: a plain Worker's Chrome, for tests of how a host finds its Chrome (host.browser_of).
  A process with `--user-data-dir=<profile>` that runs `rest` through a process between them, as Chrome on Windows
  starts a .bat host through cmd.exe. Both pass on their stdin and stdout, and end when `rest` ends.
- FakeRegistry: the Windows registry, where Chrome there finds a host (chrome_host), as winreg. NoRegistry fails
  a test that touches a registry off Windows."""

import contextlib
import sys

import pytest

SHELL = "import subprocess, sys; sys.exit(subprocess.call(sys.argv[1:]))"  # cmd.exe: no --user-data-dir
CHROME = f"import subprocess, sys; sys.exit(subprocess.call([sys.executable, '-c', {SHELL!r}, *sys.argv[2:]]))"


def command(profile, *rest: str) -> list[str]:
    return [sys.executable, "-c", CHROME, f"--user-data-dir={profile}", *rest]


class FakeRegistry:
    """winreg, as chrome_host uses it: the default values set, by key."""
    HKEY_CURRENT_USER, KEY_SET_VALUE, REG_SZ = "HKEY_CURRENT_USER", 2, 1

    def __init__(self):
        self.values = {}

    def CreateKeyEx(self, root, path, reserved, access):
        return contextlib.nullcontext((root, path))

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[(*key, name)] = (kind, value)

    def QueryValue(self, root, path):
        if (root, path, "") not in self.values:
            raise FileNotFoundError(path)
        return self.values[(root, path, "")][1]


class NoRegistry:
    def __getattr__(self, name):
        pytest.fail("a registry call off Windows")
