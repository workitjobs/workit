"""The worker extension (apply-agent/worker-extension/): its ID, the files `prepare` writes, and the
Chrome Web Store package (`package`).

The extension is separate from the WorkIt extension. A Developer checkout loads it unpacked, with
its ID fixed by manifest.json's `key`; WorkIt Auto Apply's students add the store copy
(`package`, KAN-839), whose ID the store gives (STORE_ID). `prepare` writes its generated files
into vendor/:

- engine.json: the Fill engine's version and sha256 (fill_engine.source), which the extension
  reports in its hello. The engine itself is never a file here: Apply hands it to the extension's
  memory over native messaging (`cdp.keep`, apply.plain.script.keep_engine), so no plain engine
  sits on disk, and a store copy needs none in its package;
- injected.js: Playwright's own injected script (playwright-core's injectedScriptSource,
  Apache-2.0), from the installed Python package's driver, wrapped to set
  `globalThis.__applyPW` in the extension's isolated world;
- guards/*.js: the submit and drive guards' scripts (apply.plain.guards), which the extension
  registers as content scripts and refuses when their sha256 isn't Apply's;
- fixed.js: Apply's fixed page functions (apply.plain.fixed: Needs you's field, Resume's field
  error, the emailed code's boxes), which `fixed.call` runs with no eval (KAN-611).

The same files also go, write-once, into a set of their own: vendor/sets/<id>/, <id> a hash of
their bytes (`vendor_set`, KAN-645). The launcher writes the set into the folder the Worker
really loads the extension from (`loaded_folder`: the seed's Load unpacked folder, which may be
another checkout's), and names it in the welcome; the extension then reads every generated file
from there (ops/shared.js: vendor). A set is never changed or replaced, so an Apply process on
another engine, with Workers of its own on the same folder, keeps its own set, and no Worker is
refused for an engine another checkout prepared.

Workers load no checkout at all: each profiles folder has its own copy of the extension,
APPLY_PROFILES/worker-extension/ (`install`), which the seed's Load unpacked registers and Chrome
for Testing's --load-extension names. Apply replaces that copy only while none of that folder's
Workers runs (one Apply process drives a profiles folder, KAN-634), so a `git pull` in any checkout,
or an Apply on newer code, never changes the code of a Worker that is running: Chrome restarts an
MV3 service worker from disk, so a shared folder would (KAN-645).

A seed copied from another profiles folder registers that folder's copy, which nothing kept current: on
2026-11-10 every new Worker loaded 5-day-old guard, tile and typing code that said the same feature level as
current code (KAN-764). So before a Worker starts, Apply brings the folder it will load up to this Apply's code
(`refresh`) when that folder is a copy (it has STAMP) and no running Chrome loads it (`loaders`). A folder it
can't update is welcomed as out of date (bridge.Bridge.code) and fails doctor's "Plain seed".
"""

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from functools import cache
from pathlib import Path

import psutil
from playwright._impl._driver import compute_driver_executable

from apply import fill_engine
from apply.home import CODE
from apply.plain import fixed

EXTENSION_DIR = CODE / "worker-extension"
VENDOR = EXTENSION_DIR / "vendor"
HOST_NAME = "com.workit.apply_worker"
COPY = "worker-extension"  # APPLY_PROFILES/worker-extension/: the profiles folder's own copy (install)
SET_FILE = "set.json"  # vendor/set.json in a package: the id of the generated files built into it (`package`)
STORE = EXTENSION_DIR / "store.json"  # the store package's name, description and version
LICENSES = ("LICENSE", "NOTICE")  # the extension's own license, and the third-party code it ships
STAMP = ".apply-code"  # in a copy: the code_hash of the code it holds
SETS = "sets"  # vendor/sets/<id>/: one write-once set of the generated files per Apply build
SET_DAYS = 7  # a set unused this long is removed when a new one is written
# The extension's own code: what `code_hash` reads to tell an extension running old code.
CODE_FILES = ("manifest.json", "background.js", "ops", "page")

# The injected script's options, as Playwright gives them for its utility world on Chromium.
INJECTED_OPTIONS = {"isUnderTest": False, "sdkLanguage": "python", "frameSeq": 0, "testIdAttributeName": "data-testid",
                    "stableRafCount": 1, "browserName": "chromium", "shouldPrependErrorPrefix": False,
                    "isUtilityWorld": True, "customEngines": []}
# Reads injectedScriptSource out of the driver's bundle: the string literal after its module marker.
EXTRACT = r"""const fs = require("fs");
const bundle = fs.readFileSync(process.argv[1], "utf8");
const at = bundle.indexOf('injectedScriptSource.ts"() {');
if (at < 0) throw new Error("no injectedScriptSource in " + process.argv[1]);
const start = bundle.indexOf("= '", at), end = bundle.indexOf("';\n", start);
process.stdout.write((0, eval)(bundle.slice(start + 2, end + 1)));"""
# The engine bundle's own version (FillEngine.version), read in Node.
# Reads the bundle's text on stdin (it may be WorkIt's download, never a file) and prints FillEngine.version.
VERSION = r"""const vm = require("vm"), fs = require("fs");
const context = vm.createContext({URL});
vm.runInContext(fs.readFileSync(0, "utf8"), context);
process.stdout.write(String(vm.runInContext("FillEngine.version", context)));"""


def extension_id(manifest: Path = EXTENSION_DIR / "manifest.json") -> str:
    """The ID Chrome gives the extension: the first 128 bits of the sha256 of its public key, as a-p."""
    key = base64.b64decode(json.loads(manifest.read_text())["key"])
    return "".join(chr(ord("a") + int(c, 16)) for c in hashlib.sha256(key).hexdigest()[:32])


EXTENSION_ID = extension_id()
EXTENSION_ORIGIN = f"chrome-extension://{EXTENSION_ID}/"
# The Chrome Web Store copy's ID, which the store gives at the first upload: empty until then. A Worker
# may connect from either ID (the native host's allowed_origins, the bridge's check).
STORE_ID = ""
EXTENSION_ORIGINS = (EXTENSION_ORIGIN, *([f"chrome-extension://{STORE_ID}/"] if STORE_ID else []))


def engine_identity(source: str | None = None) -> dict:
    """The engine bundle's version and sha256, as the hello carries them: of `source`, else of fill_engine.source()."""
    source = fill_engine.source() if source is None else source
    sha = hashlib.sha256(source.encode()).hexdigest()
    return {"version": _engine_version(source), "sha256": sha}


@cache
def _engine_version(source: str) -> str:
    return subprocess.run([_node(), "-e", VERSION], input=source, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def _node() -> str:
    return compute_driver_executable()[0]


def _driver_bundle() -> Path:
    return Path(compute_driver_executable()[1]).parent / "lib" / "coreBundle.js"


def _injected() -> str:
    """vendor/injected.js: Playwright's injected script, from the installed package's driver."""
    source = subprocess.run([_node(), "-e", EXTRACT, str(_driver_bundle())], capture_output=True, text=True, check=True).stdout
    return ("// Playwright's injected script (Apache-2.0), from the installed playwright package.\n"
            "(() => {\nif (globalThis.__applyPW) return;\nconst module = {};\n" + source +
            f"\nglobalThis.__applyPW = new (module.exports.InjectedScript())(globalThis, {json.dumps(INJECTED_OPTIONS)});\n}})();\n")


def _built_in(guard_files: dict[str, str]) -> dict[str, bytes]:
    from apply.plain import guards

    files = {"injected.js": _injected().encode(), "fixed.js": fixed.script().encode()}
    return files | {f"{guards.FOLDER}/{name}": text.encode() for name, text in guard_files.items()}


def generated(identity: dict | None = None) -> dict[str, bytes]:
    """Each generated file's path under vendor/ and its bytes."""
    from apply.plain import guards

    identity = identity or engine_identity()  # through fill_engine.source(), which checks the checkout's file
    return {"engine.json": (json.dumps(identity, indent=1) + "\n").encode(), **_built_in(guards.FILES)}


def store_stamp() -> dict[str, str]:
    """What a store version of the extension holds, the same in every Apply process: the hash of its own code, and the
    set id of its built-in files with each of the guards' per-run tokens (submit_guard.TOKENS, TOUCHES, MARKS, TELL,
    wherever their values went) written as a fixed value. store.json records it for its version; a change means a new
    store release (apply-agent/CLAUDE.md)."""
    from apply import submit_guard
    from apply.plain import guards

    secrets = [*submit_guard.TOKENS.values(), *submit_guard.TOUCHES.values(), *submit_guard.MARKS.values(), submit_guard.TELL]
    neutral = {}
    for name, text in guards.FILES.items():
        for secret in secrets:
            text = text.replace(secret, "0" * len(secret))
        neutral[name] = text
    return {"code": code_hash(), "files": set_id(_built_in(neutral))}


def packaged_files(files: dict[str, bytes] | None = None) -> dict[str, bytes]:
    """The generated files a store package holds: all but the engine's identity, which changes with each engine
    and is no part of the package. Their set_id is what a package's hello names (`packaged`)."""
    return {name: data for name, data in (files if files is not None else generated()).items() if name != "engine.json"}


def prepare(vendor: Path = VENDOR) -> dict:
    """Write vendor/engine.json, injected.js, fixed.js and guards/, each only when it changed, and remove an
    engine bundle an older Apply wrote there. Returns the engine's identity."""
    identity = engine_identity()
    vendor.mkdir(parents=True, exist_ok=True)
    (vendor / "engine.js").unlink(missing_ok=True)
    for name, data in generated(identity).items():
        path = vendor / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    return identity


def set_id(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode() + b"\0" + hashlib.sha256(files[name]).digest())
    return digest.hexdigest()[:16]


def vendor_set(folder: Path, files: dict[str, bytes]) -> str:
    """`files` as the set vendor/sets/<id>/ of the extension folder `folder`, written once: a set that is
    there already is left as it is, and none is ever changed. Returns the set's root as the extension
    names it ("vendor/sets/<id>"). Sets unused for SET_DAYS go."""
    sets = folder / "vendor" / SETS
    sets.mkdir(parents=True, exist_ok=True)
    ident = set_id(files)
    done = sets / ident
    if not done.is_dir():
        building = Path(tempfile.mkdtemp(prefix=f".{ident}-", dir=sets))
        for name, data in files.items():
            (building / name).parent.mkdir(parents=True, exist_ok=True)
            (building / name).write_bytes(data)
        try:
            building.rename(done)  # whole or not at all: a Worker never reads half a set
        except OSError:  # another Apply wrote the same set first
            shutil.rmtree(building, ignore_errors=True)
    os.utime(done)  # in use: not old
    old = time.time() - SET_DAYS * 86400
    for other in sets.iterdir():
        try:
            if other != done and other.stat().st_mtime < old:
                shutil.rmtree(other, ignore_errors=True)
        except OSError:
            pass
    return f"vendor/{SETS}/{ident}"


def registration(profile: Path) -> dict | None:
    """The worker extension's entry in Chrome profile `profile`'s preference files, read only. None when
    neither file has one. Its `path` may name a folder that is gone."""
    for prefs in ("Secure Preferences", "Preferences"):
        try:
            settings = json.loads((profile / "Default" / prefs).read_text())["extensions"]["settings"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(settings, dict) and isinstance(entry := settings.get(EXTENSION_ID), dict):
            return entry
    return None


def loaded_folder(profile: Path) -> Path | None:
    """The folder the worker extension is loaded from in Chrome profile `profile`: the path Load unpacked
    (or --load-extension) registered in its preferences. None when the profile has no such record."""
    for prefs in ("Secure Preferences", "Preferences"):
        try:
            settings = json.loads((profile / "Default" / prefs).read_text())["extensions"]["settings"]
            path = Path(settings[EXTENSION_ID]["path"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if path.is_absolute() and (path / "manifest.json").is_file():
            return path
    return None


def code_hash(folder: Path = EXTENSION_DIR) -> str:
    """A hash of the extension's own code in `folder` (not vendor/): it changes when the code on disk does."""
    digest = hashlib.sha256()
    for part in CODE_FILES:
        root = folder / part
        for path in sorted([root] if root.is_file() else root.rglob("*.js") if root.is_dir() else []):
            digest.update(str(path.relative_to(folder)).encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()[:16]


def install(dest: Path, files: dict[str, bytes], replace: bool, source: Path = EXTENSION_DIR) -> bool:
    """Make `dest` a copy of the extension in `source` (its code, the generated files and their vendor
    set), unless it holds that code already. A copy that holds other code is replaced only when
    `replace` (no Worker loads it now): whole, by a rename, its vendor sets kept. True when `dest`
    holds `source`'s code after."""
    code = code_hash(source)
    stamp = dest / STAMP
    held = stamp.read_text().strip() if stamp.is_file() else ""
    if held != code and (replace or not dest.exists()):
        dest.parent.mkdir(parents=True, exist_ok=True)
        building = Path(tempfile.mkdtemp(prefix=f".{dest.name}-", dir=dest.parent))
        for part in CODE_FILES:
            if (source / part).is_dir():
                shutil.copytree(source / part, building / part)
            elif (source / part).is_file():
                shutil.copy2(source / part, building / part)
        for name, data in files.items():  # the plain vendor/ files, for code that reads no set
            (building / "vendor" / name).parent.mkdir(parents=True, exist_ok=True)
            (building / "vendor" / name).write_bytes(data)
        if (dest / "vendor" / SETS).is_dir():
            shutil.copytree(dest / "vendor" / SETS, building / "vendor" / SETS)
            for old_engine in (building / "vendor" / SETS).glob("*/engine.js"):  # an older Apply's: no engine on disk
                old_engine.unlink()
        (building / STAMP).write_text(code + "\n")
        old = dest.with_name(f".{dest.name}-old-{os.getpid()}")
        if dest.exists():
            dest.rename(old)
        building.rename(dest)
        shutil.rmtree(old, ignore_errors=True)
        held = code
    if dest.exists():
        vendor_set(dest, files)
    return held == code


def guards_match(folder: Path) -> bool:
    """Whether `folder`'s plain vendor/guards/ files are this Apply's: code that reads no vendor set guards
    pages with those, and refuses any that differ."""
    from apply.plain import guards

    try:
        return all((folder / "vendor" / guards.FOLDER / name).read_text() == text for name, text in guards.FILES.items())
    except OSError:
        return False


def loaders(folder: Path) -> list[int]:
    """The PIDs of the running Chromes that load the worker extension from `folder`: by --load-extension, or by a
    profile (--user-data-dir) whose registration names it. Changing `folder` under one of them would change the code
    of a Worker that runs: never done. psutil reads each process's arguments, on every OS (W4)."""
    try:
        processes = [p.info for p in psutil.process_iter(["pid", "cmdline"])]
    except (psutil.Error, OSError):
        return [0]  # can't tell: as if one did
    target, pids = folder.resolve(), []
    for process in processes:
        arguments = process.get("cmdline") or []  # None: another user's process, or one gone
        if any(a.startswith("--type=") for a in arguments):  # a Chrome's helpers name its profile too: the browser is enough
            continue
        named = [Path(path) for a in arguments if a.startswith("--load-extension=")
                 for path in a.partition("=")[2].split(",") if path]
        for a in arguments:
            if a.startswith("--user-data-dir=") and (registered := loaded_folder(Path(a.partition("=")[2]))):
                named.append(registered)
        if any(path.resolve() == target for path in named):
            pids.append(process["pid"])
    return pids


def refresh(folder: Path, files: dict[str, bytes], source: Path = EXTENSION_DIR) -> bool:
    """Bring `folder` up to `source`'s code when it is a copy (`install` made it: it has STAMP) that holds other
    code and no running Chrome loads it. A checkout or a folder in use is left as it is. True when it was updated."""
    if not (folder / STAMP).is_file() or code_hash(folder) == code_hash(source) or loaders(folder):
        return False
    return install(folder, files, replace=True, source=source)


def package(out: Path, store: bool = True) -> Path:
    """The Chrome Web Store package of the extension, as a zip in `out`: its own code, the generated files that
    packaged_files gives (never the engine) with their id in vendor/set.json, LICENSE, NOTICE and Playwright's
    license, and a manifest with store.json's name, description and version. `store` drops the manifest's `key`,
    which the store refuses (it gives its own ID); a test's package keeps it, so Chrome for Testing gives it
    EXTENSION_ID and the native host lets it connect. Returns the zip; its unpacked folder is beside it."""
    files = packaged_files()
    meta = json.loads(STORE.read_text())
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
    manifest |= {"name": meta["name"], "description": meta["description"], "version": meta["version"]}
    if store:
        manifest.pop("key", None)
    folder = out / f"worker-extension-{meta['version']}"
    if folder.exists():
        shutil.rmtree(folder)
    for part in CODE_FILES:
        if (EXTENSION_DIR / part).is_dir():
            shutil.copytree(EXTENSION_DIR / part, folder / part)
        elif (EXTENSION_DIR / part).is_file():
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(EXTENSION_DIR / part, folder / part)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name, data in files.items():
        (folder / "vendor" / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / "vendor" / name).write_bytes(data)
    (folder / "vendor" / SET_FILE).write_text(json.dumps({"id": set_id(files)}) + "\n")
    for name in LICENSES:
        shutil.copy2(EXTENSION_DIR / name, folder / name)
    shutil.copy2(_driver_bundle().parents[1] / "LICENSE", folder / "LICENSE-playwright")  # Apache-2.0, for injected.js
    archive = shutil.make_archive(str(out / folder.name), "zip", root_dir=folder)
    return Path(archive)
