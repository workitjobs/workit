"""Build WorkIt Auto Apply, the Student build of Apply, as a Mac app (KAN-833, W8 of
../docs/desktop_application_auto_apply.md).

    python3 scripts/build_app.py            (from apply-agent/, on an Apple Silicon Mac)

It writes build/out/WorkIt Auto Apply.app. In order:

1. A venv of its own, build/venv, from uv.lock: uv's own Python 3.12 (one Python for every team Mac),
   Apply installed as a copy, not editable, with the `build` group (Nuitka) and without the dev group.
2. STUDENT = True in that copy's apply/build.py. The checkout's own build.py stays False.
3. The third-party notices (scripts/third_party_notices.py) and the other inputs the app reads beside its
   program (home.CODE): the EULA, the default policies, the Test Person sample and the Worker extension.
4. Nuitka compiles scripts/app_entry.py and what it imports, with no module of build.DEVELOPER and no
   docstrings. Every docstring would be a plain sentence in the program about how Apply works.
5. Checks: no DEVELOPER module, no Python source or bytecode, no docstring left in the app.

W8 step 1 only: the app has only the compiler's ad-hoc signature, no notarization and no Sparkle, so it
opens only on the Mac that built it. Signing and notarizing are step 2, Sparkle step 3.
"""

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # apply-agent/
BUILD = ROOT / "build"
VENV = BUILD / "venv"
PYTHON = VENV / "bin" / "python"
DATA = BUILD / "data"  # the inputs the app reads beside its program, staged for Nuitka
OUT = BUILD / "out"
REPORT = OUT / "report.xml"
ENTRY = ROOT / "scripts" / "app_entry.py"
# Where uv puts the build's Python. The app carries this path (Python's build settings, sysconfig, and libpython's
# own name), so it names no one: in uv's default place, ~/.local/share/uv, every copy of the app held the user
# name of whoever built it. It is also the same path on every Mac that builds.
PYTHON_HOME = Path("/Users/Shared/workit-auto-apply-build/python")

NAME = "WorkIt Auto Apply"  # D19
BUNDLE_ID = "ai.workitjobs.autoapply"
MIN_MACOS = "13.0"  # D18
APP = OUT / f"{NAME}.app"
STUDENT_LINE = ("STUDENT = False\n", "STUDENT = True\n")

# The checkout's inputs home.CODE names, staged as the app reads them. The Worker extension's vendor/ is what
# `prepare` writes on one Mac (its .gitignore), never part of the app.
INPUTS = ("legal/EULA.txt", "policies.default.yaml", "sample", "worker-extension")
SKIP = shutil.ignore_patterns("vendor", ".gitignore", ".DS_Store")
NOTICES = "dist/THIRD-PARTY-NOTICES.txt"  # first_run.NOTICES

# Flags from the shell (Homebrew's LLVM sets these) would compile and link against its headers and libraries,
# which a student's Mac lacks: the first build linked Homebrew's libunwind. The app builds with Apple's clang and
# the macOS SDK only.
COMPILER_ENV = ("CC", "CXX", "CFLAGS", "CPPFLAGS", "CXXFLAGS", "LDFLAGS", "LIBRARY_PATH", "CPATH")
# Apple's own tools only: with Anaconda first on the PATH, Nuitka ran its install_name_tool, which failed.
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def run(command: list[str], **kwargs) -> None:
    print("+", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, check=True, **kwargs)


def version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def make_venv() -> Path:
    """build/venv from uv.lock, with Apply's source as it is now; returns the copy's apply/ folder."""
    run(["uv", "sync", "--frozen", "--no-dev", "--group", "build", "--no-editable", "--reinstall-package", "apply",
         "--managed-python", "--python", "3.12"], cwd=ROOT,
        env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(VENV), "UV_PYTHON_INSTALL_DIR": str(PYTHON_HOME)})
    found = subprocess.run([PYTHON, "-I", "-c", "import apply, pathlib; print(pathlib.Path(apply.__file__).parent)"],
                           check=True, capture_output=True, text=True).stdout.strip()
    return Path(found)


def set_student(package: Path) -> None:
    flag = package / "build.py"
    text = flag.read_text()
    if text.count(STUDENT_LINE[0]) != 1:
        sys.exit(f"{flag} has no single line {STUDENT_LINE[0].strip()!r}: apply.build changed, so fix this script.")
    flag.write_text(text.replace(*STUDENT_LINE))


def stage_inputs(strict: bool) -> None:
    shutil.rmtree(DATA, ignore_errors=True)
    for name in INPUTS:
        source, dest = ROOT / name, DATA / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, dest, ignore=SKIP)
        else:
            shutil.copy2(source, dest)
    run(["uv", "run", "--frozen", "python", "scripts/third_party_notices.py",
         "--out", DATA / NOTICES, *(["--strict"] if strict else [])], cwd=ROOT)


def compile_app(developer: list[str]) -> None:
    def xcrun(*args: str) -> str:
        return subprocess.run(["/usr/bin/xcrun", *args], check=True, capture_output=True, text=True).stdout.strip()

    env = {key: value for key, value in os.environ.items() if key not in COMPILER_ENV}
    # The clang xcrun names finds the SDK's headers only through SDKROOT ('stdlib.h' file not found without it).
    env |= {"CC": xcrun("--find", "clang"), "SDKROOT": xcrun("--show-sdk-path"), "MACOSX_DEPLOYMENT_TARGET": MIN_MACOS,
            "PATH": SYSTEM_PATH}
    shutil.rmtree(APP, ignore_errors=True)
    shutil.rmtree(OUT / f"{ENTRY.stem}.app", ignore_errors=True)
    data = [f"--include-data-dir={DATA / name}={name}" if (DATA / name).is_dir()
            else f"--include-data-files={DATA / name}={name}" for name in (*INPUTS, NOTICES)]
    run([PYTHON, "-m", "nuitka", "--mode=app", f"--output-dir={OUT}", f"--output-filename={NAME}",
         f"--macos-app-name={NAME}", f"--macos-signed-app-name={BUNDLE_ID}", f"--macos-app-version={version()}",
         f"--macos-app-icon={ROOT / 'src' / 'apply' / 'Apply.icns'}", "--macos-target-arch=arm64",
         # The engine download names the app's version from Apply's metadata (W7): without it no build fits.
         "--include-distribution-metadata=apply", "--include-package-data=apply",
         "--playwright-include-browser=none",  # Workers run the student's Chrome
         # No docstrings: each one explains Apply in plain words. No asserts stays off: launcher's NEVER check
         # is an assert. Isolated: no PYTHON* variable or user site folder changes what the app runs.
         "--python-flag=no_docstrings", "--python-flag=isolated", "--python-flag=safe_path",
         "--assume-yes-for-downloads", f"--report={REPORT}",
         *(f"--nofollow-import-to={module}" for module in developer), *data, ENTRY], cwd=ROOT, env=env)
    # Nuitka names the bundle after the entry file and builds its program for macOS 11 (the Python's own target).
    (OUT / f"{ENTRY.stem}.app").rename(APP)
    info = APP / "Contents" / "Info.plist"
    plist = plistlib.loads(info.read_bytes())
    plist["LSMinimumSystemVersion"] = MIN_MACOS  # Finder refuses to open it on an older macOS
    info.write_bytes(plistlib.dumps(plist))
    # The edit broke Nuitka's ad-hoc signature, and Apple Silicon runs no unsigned code: sign it ad hoc again.
    # Step 2 replaces this with the Developer ID signature, file by file.
    run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", APP])


def check(developer: list[str]) -> None:
    """Refuse an app that carries a developer part, Python source or bytecode, or a docstring."""
    compiled = {module.get("name") for module in ET.parse(REPORT).getroot().iter("module")}
    if found := sorted(compiled & set(developer)):
        sys.exit(f"The app compiled in developer modules: {', '.join(found)}. Import them only where "
                 "build.STUDENT never runs (apply-agent/CLAUDE.md).")
    if found := sorted(str(p.relative_to(APP)) for p in APP.rglob("*") if p.suffix in (".py", ".pyc")):
        sys.exit(f"The app holds Python source or bytecode, which reads back as code: {', '.join(found[:10])}")
    program = (APP / "Contents" / "MacOS" / NAME).read_bytes()
    control = b"WorkIt Auto Apply doesn't {what}"  # a string constant (student.NO_MODEL), which must be there
    if control not in program:
        sys.exit("The docstring check can't read the program's constants: it found no known string in it.")
    docstring = b"The Student build's stand-in for `claude -p`"  # student.NoClaude's, which must be gone
    if docstring in program:
        sys.exit("The app still holds docstrings: Nuitka's no_docstrings flag didn't take.")
    home = str(Path.home()).encode()
    if found := sorted(str(p.relative_to(APP)) for p in APP.rglob("*") if p.is_file() and home in p.read_bytes()):
        sys.exit(f"The app names this Mac's home folder ({home.decode()}), and with it who built it: "
                 f"{', '.join(found[:10])}")
    print(f"Checked: no developer module, no Python source or bytecode, no docstrings, no home folder "
          f"({len(compiled)} modules).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--release", action="store_true",
                        help="a build for students: the notices must be complete (third_party_notices --strict)")
    args = parser.parse_args()
    if sys.platform != "darwin" or os.uname().machine != "arm64":
        sys.exit("Build WorkIt Auto Apply on an Apple Silicon Mac (D18).")
    package = make_venv()
    set_student(package)
    developer = sorted(subprocess.run([PYTHON, "-I", "-c", "import apply.build as b; print(*b.DEVELOPER)"],
                                      check=True, capture_output=True, text=True).stdout.split())
    stage_inputs(strict=args.release)
    compile_app(developer)
    check(developer)
    size = sum(p.stat().st_size for p in APP.rglob("*") if p.is_file()) / 1e6
    print(f"Built {APP} ({size:.0f} MB). Open it with: open '{APP}'")


if __name__ == "__main__":
    main()
