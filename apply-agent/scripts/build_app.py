"""Build WorkIt Auto Apply, the Student build of Apply, as a Mac app (KAN-833, W8 of
../docs/desktop_application_auto_apply.md).

    python3 scripts/build_app.py            (from apply-agent/, on an Apple Silicon Mac)

It needs Xcode's Command Line Tools (xcode-select --install), uv, and the network. Any python3 runs it, macOS's
own 3.9 too: it uses the standard library only, and builds with a Python of its own. It writes
build/out/WorkIt Auto Apply.app. In order:

1. A venv of its own, build/venv, from uv.lock: uv's own Python 3.12 (one Python for every team Mac),
   Apply installed as a copy, not editable, with the `build` group (Nuitka) and without the dev group.
2. STUDENT = True in that copy's apply/build.py, and no JavaScript comments in its page code
   (scripts/strip_js_comments.py), so the comments stay in the checkout for development. It checks that the
   Worker extension's store copy is the same after.
3. The third-party notices (scripts/third_party_notices.py) and the other inputs the app reads beside its
   program (home.CODE): the EULA, the default policies and the Worker extension.
4. Nuitka compiles scripts/app_entry.py and what it imports, with no module of build.DEVELOPER and no
   docstrings. Every docstring would be a plain sentence in the program about how Apply works.
   swiftc builds the plain Workers' window capture helper into the app beside the program.
5. Checks: no DEVELOPER module, no source or bytecode, no docstring, no page code comment and no home folder
   path left in the app, and a capture helper that runs.
6. build/out/WorkIt Auto Apply.dmg, the download: the app, a link to Applications, and the license and notices
   beside them. It checks that the DMG mounts and the app in it passes codesign's check.

`--release` is a build for students. It builds from the current commit's own files (`git archive` into
build/source), never the working tree: Apply installs from its folder with every untracked file in it, Nuitka ships
every data file of the package, and the inputs are copied as folders, so a stray file (a debug dump with real
answers) went into the app. Uncommitted changes are left out, and the build says so. The notices must be complete,
and Nuitka compiles with no ccache, a program it would download from nuitka.net with no check and run on every C
file. Every build writes its commit into Info.plist (COMMIT_KEY), with "+changes" for a test build of a working tree
that has some, so a report names the code it came from.

W8 step 1 only: the app has only the compiler's ad-hoc signature, no notarization and no Sparkle, so it
opens only on the Mac that built it. Signing and notarizing are step 2, Sparkle step 3.
"""

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # apply-agent/
BUILD = ROOT / "build"
VENV = BUILD / "venv"
PYTHON = VENV / "bin" / "python"
DATA = BUILD / "data"  # the inputs the app reads beside its program, staged for Nuitka
OUT = BUILD / "out"
REPORT = OUT / "report.xml"
SOURCE = BUILD / "source"  # a release's own copy of the commit's files
# Each build step reads these from its source folder: the checkout for a test build, SOURCE for a release.
ENTRY = Path("scripts", "app_entry.py")
# The app's icon: WorkIt's logo at 1024 px, laid out on Apple's macOS icon grid (an 824 px shape, a transparent margin),
# so it shows the size of other apps' icons. The build makes the .icns from it (`make_icon`).
ICON = Path("assets", "app-icon.png")
# The plain Workers' live tiles film a Worker's window with this Swift program (apply.plain.window_capture). A
# checkout builds it with swiftc on first use; a student's Mac has no swiftc, so the app ships it, built here.
CAPTURE_SOURCE = Path("src", "apply", "plain", "window_capture.swift")
COMMIT_KEY = "WorkItCommit"  # Info.plist: the commit the app was built from
# Where uv puts the build's Python. The app carries this path (Python's build settings, sysconfig, and libpython's
# own name), so it names no one: in uv's default place, ~/.local/share/uv, every copy of the app held the user
# name of whoever built it. It is also the same path on every Mac that builds.
PYTHON_HOME = Path("/Users/Shared/workit-auto-apply-build/python")

# Sparkle, the app's updater (W8 step 3, KAN-941): one release, checked against its sha256 before any use.
# legal/licenses/Sparkle-LICENSE.txt is this release's.
SPARKLE_VERSION = "2.10.1"
SPARKLE_SHA256 = "1a856d2a9edb8e628de88121d7be04cf0e2167f8641650b78fca00b14244cf27"
SPARKLE = BUILD / f"sparkle-{SPARKLE_VERSION}"  # the release, unpacked once: its framework, and its tools in bin/
# Where every app looks for updates. Each app keeps it in its Info.plist for good: never change it. R2 serves it (D17).
FEED = "https://downloads.workitjobs.ai/appcast.xml"
# The update key's public half (Sparkle's generate_keys; the private half signs each update, in the publisher's
# Keychain with a backup in Infisical). Empty while there is no key: Sparkle won't start without one, so the app then
# ships no updater.
SPARKLE_PUBLIC_KEY = ""
# Sparkle's parts the app never runs: the XPC services are for sandboxed apps, and the headers and module maps are
# for compiling against it.
SPARKLE_LEAVE_OUT = ("XPCServices", "Headers", "PrivateHeaders", "Modules")

NAME = "WorkIt Auto Apply"  # D19
BUNDLE_ID = "ai.workitjobs.autoapply"
MIN_MACOS = "13.0"  # D18
APP = OUT / f"{NAME}.app"
DMG = OUT / f"{NAME}.dmg"
STUDENT_LINE = ("STUDENT = False\n", "STUDENT = True\n")

# The checkout's inputs home.CODE names, staged as the app reads them. The Worker extension's vendor/ is what
# `prepare` writes on one Mac (its .gitignore), never part of the app. The Test Person sample (sample/) is not one:
# a student's app has no Test Person (2026-11-24); its data comes from WorkIt (W11).
INPUTS = ("legal/EULA.txt", "policies.default.yaml", "worker-extension")
SKIP = shutil.ignore_patterns("vendor", ".gitignore", ".DS_Store")
NOTICES = "dist/THIRD-PARTY-NOTICES.txt"  # first_run.NOTICES

# Flags from the shell (Homebrew's LLVM sets these) would compile and link against its headers and libraries,
# which a student's Mac lacks: the first build linked Homebrew's libunwind. The app builds with Apple's clang and
# the macOS SDK only.
COMPILER_ENV = ("CC", "CXX", "CFLAGS", "CPPFLAGS", "CXXFLAGS", "LDFLAGS", "LIBRARY_PATH", "CPATH")
# Apple's own tools only: with Anaconda first on the PATH, Nuitka ran its install_name_tool, which failed.
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
# Package files the app doesn't ship: the Swift source (the app ships the program built from it), the tools Claude
# drives a page with (apply.plain.mcp, which only `claude -p` starts: a developer part, W3), and Playwright's web UIs
# (its trace viewer, HTML report, recorder and dashboard, 3.6 MB), which Apply never opens: its driver starts Chrome
# and drives pages without them (checked 2026-11-21).
LEAVE_OUT = ("apply/plain/window_capture.swift", "apply/plain/mcp_tools.json", "playwright/driver/package/lib/vite",
             "apply/Apply.icns")  # the developer's Dock icon (dock_app): the app's own is ICON
# Why the app sends Apple events, as macOS asks it: FocusKeeper (apply.focus) has System Events bring the student's
# app back in front of a Worker's window. With no reason in Info.plist, macOS refuses the event and never asks.
APPLE_EVENTS_REASON = ("WorkIt Auto Apply brings the app you were using back to the front when a Worker's Chrome "
                       "window opens on top of it.")
# Text the checks look for in the program, read from the build's copy before the compile (`probes`), so a reworded
# docstring or comment can't make a check pass by finding nothing: a string constant that must be there
# (student.NO_MODEL), a docstring's first line that must be gone (student.NoClaude's) and a page code comment that must
# be gone (the first in dashboard_page.PAGE). Run on the build's Python: Apply's source is Python 3.12's.
PROBES = r"""
import ast, json, re, sys
package = sys.argv[1]
def body(module):
    return ast.parse(open(f"{package}/{module}.py").read()).body
def value(module, name):
    return next(ast.literal_eval(n.value) for n in body(module) if isinstance(n, ast.Assign)
                and getattr(n.targets[0], "id", None) == name)
doc = next(ast.get_docstring(n) for n in body("student") if isinstance(n, ast.ClassDef) and n.name == "NoClaude")
comment = re.search(r"^[ \t]*//[ \t]*(\S[^\n]{19,})$", value("dashboard_page", "PAGE"), re.MULTILINE).group(1)
print(json.dumps({"constant": value("student", "NO_MODEL"), "docstring": doc.splitlines()[0], "comment": comment}))
"""


def run(command: list[str], **kwargs) -> None:
    print("+", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, check=True, **kwargs)


def venv_python(code: str, *args: object) -> str:
    """What `code` prints, run on the build's own Python with `args`."""
    return subprocess.run([PYTHON, "-I", "-c", code, *map(str, args)], check=True, capture_output=True,
                          text=True).stdout.strip()


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout.strip()


def committed(commit: str) -> Path:
    """The commit's own files of this folder, in SOURCE: nothing from the working tree, tracked or not, gets in."""
    shutil.rmtree(SOURCE, ignore_errors=True)
    SOURCE.mkdir(parents=True)
    prefix = git("rev-parse", "--show-prefix")  # "apply-agent/" in the WorkIt repo; "" once Apply has its own (W0)
    # From the repo's top folder: run in a subfolder, git archive keeps only paths under it, inside the subtree too,
    # which left nothing.
    top = git("rev-parse", "--show-toplevel")
    archive = subprocess.run(["git", "-C", top, "archive", "--format=tar", f"{commit}:{prefix}"], check=True,
                             capture_output=True).stdout
    subprocess.run(["/usr/bin/tar", "-x", "-C", str(SOURCE)], input=archive, check=True)
    return SOURCE


def preflight() -> None:
    if sys.platform != "darwin" or os.uname().machine != "arm64":
        sys.exit("Build WorkIt Auto Apply on an Apple Silicon Mac (D18).")
    if subprocess.run(["/usr/bin/xcode-select", "-p"], capture_output=True, check=False).returncode != 0:
        sys.exit("Install Xcode's Command Line Tools first: xcode-select --install")
    if not shutil.which("uv"):
        sys.exit("Install uv first: https://docs.astral.sh/uv/")


def make_venv(source: Path) -> Path:
    """build/venv from `source`'s uv.lock, with Apply installed from `source`; returns the copy's apply/ folder."""
    run(["uv", "sync", "--frozen", "--no-dev", "--group", "build", "--no-editable", "--reinstall-package", "apply",
         "--managed-python", "--python", "3.12"], cwd=source,
        env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(VENV), "UV_PYTHON_INSTALL_DIR": str(PYTHON_HOME)})
    return Path(venv_python("import apply, pathlib; print(pathlib.Path(apply.__file__).parent)"))


def set_student(package: Path) -> None:
    flag = package / "build.py"
    text = flag.read_text()
    if text.count(STUDENT_LINE[0]) != 1:
        sys.exit(f"{flag} has no single line {STUDENT_LINE[0].strip()!r}: apply.build changed, so fix this script.")
    flag.write_text(text.replace(*STUDENT_LINE))


def store_files(package: Path, source: Path) -> str:
    """The set id of the Worker extension's built-in files (the guards, fixed.js, injected.js) as `package` makes
    them. Apply finds the extension beside its checkout (home.CODE), so it runs here from a tree shaped like one."""
    tree = BUILD / "store-check"
    shutil.rmtree(tree, ignore_errors=True)
    shutil.copytree(package, tree / "src" / "apply")
    (tree / "worker-extension").symlink_to(source / "worker-extension")
    stamp = subprocess.run([PYTHON, "-c", "from apply.plain import extension; print(extension.store_stamp()['files'])"],
                           cwd=tree, env={**os.environ, "PYTHONPATH": str(tree / "src")}, check=True,
                           capture_output=True, text=True).stdout.strip()
    shutil.rmtree(tree)
    return stamp


def strip_comments(package: Path, source: Path) -> None:
    """No JavaScript comments in the copy's page code, with the Worker extension's store copy unchanged: a plain
    Worker refuses guards or fixed functions whose sha256 isn't the store copy's."""
    before = store_files(package, source)
    node = package.parent / "playwright" / "driver" / "node"
    run([PYTHON, "-I", source / "scripts" / "strip_js_comments.py", package, node])
    if store_files(package, source) != before:
        sys.exit("Stripping comments changed the Worker extension's store files: a module that plain/fixed.py, "
                 "plain/guards.py or plain/extension.py takes page code from is missing from STORE_CODE in "
                 "scripts/strip_js_comments.py.")


def stage_inputs(source: Path, strict: bool) -> None:
    shutil.rmtree(DATA, ignore_errors=True)
    for name in INPUTS:
        dest = DATA / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if (source / name).is_dir():
            shutil.copytree(source / name, dest, ignore=SKIP)
        else:
            shutil.copy2(source / name, dest)
    # On the build's own Python, which the notices name: their venv took the first Python 3.12 uv found (Anaconda's
    # 3.12.2 on one Mac, while the app ships 3.12.14). UV_PYTHON reaches the script's own uv calls only: set on a
    # `uv run`, it would also change the Python of the checkout's .venv.
    run([PYTHON, "-I", source / "scripts" / "third_party_notices.py", "--out", DATA / NOTICES,
         *(["--strict"] if strict else [])], cwd=source, env={**os.environ, "UV_PYTHON": str(PYTHON)})


def fetch_sparkle() -> Path:
    """Sparkle's release, unpacked in SPARKLE: downloaded once, and used only when it matches SPARKLE_SHA256."""
    if (SPARKLE / "Sparkle.framework").is_dir():
        return SPARKLE
    archive = BUILD / f"Sparkle-{SPARKLE_VERSION}.tar.xz"
    run(["/usr/bin/curl", "-fsSL", "-o", archive,
         f"https://github.com/sparkle-project/Sparkle/releases/download/{SPARKLE_VERSION}/{archive.name}"])
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SPARKLE_SHA256:
        archive.unlink()
        sys.exit(f"Sparkle {SPARKLE_VERSION}'s download doesn't match its sha256, so it isn't used.")
    unpacking = BUILD / f"sparkle-{SPARKLE_VERSION}.partial"
    shutil.rmtree(unpacking, ignore_errors=True)
    unpacking.mkdir(parents=True)
    run(["/usr/bin/tar", "-xJf", archive, "-C", unpacking])
    unpacking.rename(SPARKLE)
    archive.unlink()
    return SPARKLE


def make_icon(source: Path) -> Path:
    """ICON as an .icns file, at every size macOS asks for, made with macOS's own sips and iconutil."""
    iconset = BUILD / "AppIcon.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir(parents=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            pixels = str(size * scale)
            subprocess.run(["/usr/bin/sips", "-z", pixels, pixels, source / ICON, "--out",
                            iconset / f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"], check=True,
                           capture_output=True)
    icns = BUILD / "AppIcon.icns"
    run(["/usr/bin/iconutil", "-c", "icns", iconset, "-o", icns])
    return icns


def compile_app(source: Path, developer: list[str], version: str, scheme: str, capture: str, release: bool,
                commit: str) -> None:
    def xcrun(*args: str) -> str:
        return subprocess.run(["/usr/bin/xcrun", *args], check=True, capture_output=True, text=True).stdout.strip()

    # No PYTHON* variable either: PYTHONPATH comes before the venv, so a teammate's could make Nuitka compile the
    # checkout's Apply (STUDENT False, comments in) or another copy of a library.
    env = {key: value for key, value in os.environ.items() if key not in COMPILER_ENV and not key.startswith("PYTHON")}
    # The clang xcrun names finds the SDK's headers only through SDKROOT ('stdlib.h' file not found without it).
    env |= {"CC": xcrun("--find", "clang"), "SDKROOT": xcrun("--show-sdk-path"), "MACOSX_DEPLOYMENT_TARGET": MIN_MACOS,
            "PATH": SYSTEM_PATH}
    shutil.rmtree(APP, ignore_errors=True)
    DMG.unlink(missing_ok=True)  # a failed build leaves no DMG of an earlier one beside its app
    shutil.rmtree(OUT / f"{ENTRY.stem}.app", ignore_errors=True)
    data = [f"--include-data-dir={DATA / name}={name}" if (DATA / name).is_dir()
            else f"--include-data-files={DATA / name}={name}" for name in (*INPUTS, NOTICES)]
    run([PYTHON, "-m", "nuitka", "--mode=app", f"--output-dir={OUT}", f"--output-filename={NAME}",
         f"--macos-app-name={NAME}", f"--macos-signed-app-name={BUNDLE_ID}", f"--macos-app-version={version}",
         f"--macos-app-icon={make_icon(source)}", "--macos-target-arch=arm64",
         # The engine download names the app's version from Apply's metadata (W7): without it no build fits.
         "--include-distribution-metadata=apply", "--include-package-data=apply",
         *(f"--noinclude-data-files={path}" for path in LEAVE_OUT),
         "--playwright-include-browser=none",  # Workers run the student's Chrome
         # No docstrings: each one explains Apply in plain words. No asserts stays off: launcher's NEVER check
         # is an assert. Isolated: no PYTHON* variable or user site folder changes what the app runs.
         "--python-flag=no_docstrings", "--python-flag=isolated", "--python-flag=safe_path",
         "--assume-yes-for-downloads", *(["--disable-cache=ccache"] if release else []), f"--report={REPORT}",
         *(f"--nofollow-import-to={module}" for module in developer), *data, source / ENTRY], cwd=source, env=env)
    # Nuitka names the bundle after the entry file and builds its program for macOS 11 (the Python's own target).
    (OUT / f"{ENTRY.stem}.app").rename(APP)
    info = APP / "Contents" / "Info.plist"
    plist = plistlib.loads(info.read_bytes())
    plist["LSMinimumSystemVersion"] = MIN_MACOS  # Finder refuses to open it on an older macOS
    # The build number, which only grows: Sparkle offers an update only when the feed's is higher than the app's, and
    # pyproject's version (CFBundleShortVersionString, the one the student sees) stays the same over many builds. The
    # build time, not a commit count: a count drops when W0 moves Apply to its own repo, and differs between branches.
    plist["CFBundleVersion"] = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")  # noqa: UP017 (UTC is 3.11's: macOS has 3.9)
    # WorkIt's sign-in page sends the student back with a workit-auto-apply:// link: macOS opens this app for it
    # and hands it the link (apply.sign_in_link.listen).
    plist["CFBundleURLTypes"] = [{"CFBundleURLName": f"{BUNDLE_ID}.sign-in", "CFBundleURLSchemes": [scheme]}]
    plist["NSAppleEventsUsageDescription"] = APPLE_EVENTS_REASON
    plist[COMMIT_KEY] = commit
    if SPARKLE_PUBLIC_KEY:
        # The updater (apply.updates): it checks the feed at launch and each day, downloads a newer build in the
        # background and installs it when the student quits, asking nothing; it checks an update's EdDSA signature
        # before it unpacks it.
        plist |= {"SUFeedURL": FEED, "SUPublicEDKey": SPARKLE_PUBLIC_KEY, "SUEnableAutomaticChecks": True,
                  "SUAutomaticallyUpdate": True, "SUVerifyUpdateBeforeExtraction": True}
    info.write_bytes(plistlib.dumps(plist))
    run(["/usr/bin/xcrun", "swiftc", "-O", "-target", f"arm64-apple-macos{MIN_MACOS}",
         "-o", APP / "Contents" / "MacOS" / capture, source / CAPTURE_SOURCE], env=env)
    if SPARKLE_PUBLIC_KEY:
        framework = APP / "Contents" / "Frameworks" / "Sparkle.framework"
        run(["/usr/bin/ditto", fetch_sparkle() / "Sparkle.framework", framework])
        for part in SPARKLE_LEAVE_OUT:
            shutil.rmtree(framework / "Versions" / "Current" / part, ignore_errors=True)
            (framework / part).unlink(missing_ok=True)  # the framework's top-level link to it
    # The edits broke Nuitka's ad-hoc signature, and Apple Silicon runs no unsigned code: sign it ad hoc again.
    # Step 2 replaces this with the Developer ID signature, file by file.
    run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", APP])


def check(developer: list[str], capture: str, probes: dict[str, str]) -> None:
    """Refuse an app that carries a developer part, Python source or bytecode, a docstring, a page code comment or
    the builder's home folder, or whose capture helper doesn't run."""
    compiled = {module.get("name") for module in ET.parse(REPORT).getroot().iter("module")}
    if found := sorted(compiled & set(developer)):
        sys.exit(f"The app compiled in developer modules: {', '.join(found)}. Import them only where "
                 "build.STUDENT never runs (apply-agent/CLAUDE.md).")
    if found := sorted(str(p.relative_to(APP)) for p in APP.rglob("*") if p.suffix in (".py", ".pyc")):
        sys.exit(f"The app holds Python source or bytecode, which reads back as code: {', '.join(found[:10])}")
    if found := [path for path in LEAVE_OUT if (APP / "Contents" / "MacOS" / path).exists()]:
        sys.exit(f"The app holds files it must leave out: {', '.join(found)}")
    # --check answers 0 with Screen Recording permission and 3 without; anything else, it can't run here.
    helper = APP / "Contents" / "MacOS" / capture
    if subprocess.run([helper, "--check"], capture_output=True, check=False).returncode not in (0, 3):
        sys.exit(f"The app's window capture helper ({capture}) doesn't run.")
    folder = APP / "Contents" / "MacOS"
    program = (folder / NAME).read_bytes()
    if probes["constant"].encode() not in program:
        sys.exit("The docstring check can't read the program's constants: it found no known string in it.")
    if probes["docstring"].encode() in program:
        sys.exit("The app still holds docstrings: Nuitka's no_docstrings flag didn't take.")
    if probes["comment"].encode() in program:
        sys.exit("The app still holds its page code's comments: scripts/strip_js_comments.py didn't take.")
    # Only the files this build makes: third-party ones carry their own builders' paths (/Users/admin in Node,
    # /Users/runner in cffi), which a teammate's home folder can match.
    home = (str(Path.home()) + "/").encode()
    ours = [folder / NAME, folder / capture, *folder.glob("libpython*.dylib")]
    if found := [p.name for p in ours if home in p.read_bytes()]:
        sys.exit(f"The app names this Mac's home folder ({home.decode()}), and with it who built it: "
                 f"{', '.join(found)}")
    print(f"Checked: no developer module, no Python source or bytecode, no docstrings, no page code comments, "
          f"no home folder ({len(compiled)} modules).")


def make_dmg() -> None:
    """The download: the app, a link to Applications to drag it onto, and the license and notices beside them (W10)."""
    stage = OUT / "dmg"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir()
    run(["/usr/bin/ditto", APP, stage / APP.name])  # ditto keeps the app's signatures, links and attributes
    (stage / "Applications").symlink_to("/Applications")
    shutil.copy2(DATA / "legal" / "EULA.txt", stage / "License.txt")
    shutil.copy2(DATA / NOTICES, stage / "Third-Party Notices.txt")
    try:
        run(["/usr/bin/hdiutil", "create", "-volname", NAME, "-srcfolder", stage, "-fs", "HFS+", "-format", "UDZO",
             "-ov", DMG])
        shutil.rmtree(stage)
        mount = OUT / "dmg-check"  # mounted read-only, as a student's Mac opens it, and its app checked as it is there
        run(["/usr/bin/hdiutil", "attach", DMG, "-readonly", "-nobrowse", "-mountpoint", mount])
        try:
            signed = subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", mount / APP.name],
                                    capture_output=True, check=False).returncode == 0
            linked = (mount / "Applications").is_symlink()
        finally:
            run(["/usr/bin/hdiutil", "detach", mount])
        if not (signed and linked):
            sys.exit(f"The DMG's app fails codesign's check or it has no Applications link: {DMG}")
    except BaseException:  # a failed or refused DMG is no download: none stays in build/out
        DMG.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--release", action="store_true",
                        help="a build for students: complete notices (third_party_notices --strict), no ccache")
    args = parser.parse_args()
    preflight()
    fetch_sparkle()  # once, even with no key yet: its bin/generate_keys makes the key
    commit = git("rev-parse", "HEAD")
    changed = bool(git("status", "--porcelain", "--untracked-files=all", "--", "."))
    if args.release:
        # Only the inputs come from the commit: this script runs from the working tree. An uncommitted change to it
        # would decide what the release holds while WorkItCommit names a commit that can't build that app again.
        if git("status", "--porcelain", "--", "scripts/build_app.py"):
            sys.exit("Commit scripts/build_app.py first: a release runs the committed build, and its commit is "
                     "written into the app.")
        source = committed(commit)
        if changed:
            print(f"Building the release from commit {commit[:12]}: this folder's uncommitted changes are not in it.")
    else:
        source, commit = ROOT, commit + ("+changes" if changed else "")
    package = make_venv(source)
    set_student(package)
    probes = json.loads(venv_python(PROBES, package))
    strip_comments(package, source)
    developer = sorted(venv_python("import apply.build as b; print(*b.DEVELOPER)").split())
    version = venv_python("import importlib.metadata as m; print(m.version('apply'))")
    scheme = venv_python("from apply.sign_in_link import SCHEME; print(SCHEME)")
    capture = venv_python("from apply.plain.window_capture import BUNDLED_NAME; print(BUNDLED_NAME)")
    stage_inputs(source, strict=args.release)
    compile_app(source, developer, version, scheme, capture, release=args.release, commit=commit)
    check(developer, capture, probes)
    make_dmg()
    size = sum(p.stat().st_size for p in APP.rglob("*") if p.is_file()) / 1e6
    print(f"Built {APP} ({size:.0f} MB) and {DMG.name} ({DMG.stat().st_size / 1e6:.0f} MB). Open it with: open '{APP}'")


if __name__ == "__main__":
    main()
