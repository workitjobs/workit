"""Where each OS's Chrome finds a native messaging host, and the files that start it (KAN-929, P5 of
docs/windows_desktop.md). Chrome reads a host's manifest, a JSON file that names the program to start and the
extensions that may call it (https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging):

- macOS and Linux: from the NativeMessagingHosts folder in its user data folder, so each plain Worker's profile
  has its own. The program is a `#!/bin/sh` wrapper.
- Windows: only from the registry (Chromium's launch_context_win.cc): the default value of
  HKEY_CURRENT_USER\\Software\\Google\\Chrome\\NativeMessagingHosts\\<name> is the manifest's path. Every Chrome
  build reads that key, Chrome for Testing too, and it is one for all of this Windows user's Chromes: so one
  folder (WINDOWS_FOLDER) holds the manifest, never a profile, which a test deletes when it ends. The program
  is a .bat wrapper, which Chrome starts through `cmd.exe /d /s /c`. It is UTF-8, and its `chcp 65001` makes
  cmd.exe read it so: in the console's own code page (437 on US Windows) a path such as C:\\Users\\Łukasz can't
  be written, and every Worker's start failed.

A file is written only when its text changes, in one step (a new file, then os.replace): Chrome and cmd.exe
read them while other Workers start, and on Windows a file that is open can't be replaced.
"""

import json
import os
import secrets
import shlex
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from apply.home import APP_FOLDER

KEY = r"Software\Google\Chrome\NativeMessagingHosts"  # under HKEY_CURRENT_USER
WINDOWS_FOLDER = APP_FOLDER / "native-hosts"


def folder(user_data: Path, system: str = sys.platform) -> Path:
    """Where the host files go for a Chrome on the user data folder `user_data`."""
    return WINDOWS_FOLDER if system == "win32" else user_data / "NativeMessagingHosts"


def install(name: str, description: str, origins: Iterable[str], command: Sequence[str], manifests: Path,
            wrapper: Path, system: str = sys.platform, registry=None) -> Path:
    """Write host `name`: its wrapper at `wrapper` (with .bat on Windows), which runs `command` with Chrome's
    arguments, and its manifest in `manifests`, which names the wrapper and lets only `origins` call it. On Windows
    also the registry key that names the manifest (`registry`: winreg, or a test's stand-in). Returns the
    manifest's path."""
    if system == "win32":
        wrapper = wrapper.with_name(wrapper.name + ".bat")
        line = " ".join('"' + part.replace("%", "%%") + '"' for part in command)  # %: a variable in a .bat
        # No echo, and chcp's own line to nul: either would go into Chrome's pipe.
        _write(wrapper, f"@echo off\r\nchcp 65001 >nul\r\n{line} %*\r\n".encode())
    else:
        _write(wrapper, f"#!/bin/sh\nexec {shlex.join(command)} \"$@\"\n".encode(), mode=0o700)
    manifest = manifests / f"{name}.json"
    _write(manifest, (json.dumps({"name": name, "description": description, "path": str(wrapper), "type": "stdio",
                                  "allowed_origins": list(origins)}, indent=1) + "\n").encode())
    if system == "win32":
        if registry is None:
            import winreg as registry  # Windows only
        with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, rf"{KEY}\{name}", 0, registry.KEY_SET_VALUE) as key:
            registry.SetValueEx(key, "", 0, registry.REG_SZ, str(manifest))
    return manifest


def _write(path: Path, data: bytes, mode: int | None = None) -> None:
    try:
        if path.read_bytes() == data:
            return
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(f"{path.name}.{secrets.token_hex(4)}.part")  # one per writer: Workers start at once
    part.write_bytes(data)
    if mode is not None:
        part.chmod(mode)
    os.replace(part, path)
