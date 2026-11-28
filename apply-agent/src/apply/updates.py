"""WorkIt Auto Apply's updates and install (W8 steps 3 and 4, KAN-941, KAN-950), in the built app only.

scripts/build_app.py puts Sparkle.framework in the app and its settings in Info.plist: the feed's address
(SUFeedURL), the update key's public half (SUPublicEDKey), and checks with no question asked
(SUEnableAutomaticChecks) that download a newer build in the background and install it when the student quits
(SUAutomaticallyUpdate). `start` starts Sparkle's own updater with them, which then checks at launch and each day.
A checkout, or an app built before there was a key, has neither, and nothing starts.

`eject_installer` ejects the disk image the student installed the app from, once they have dragged the app to
Applications and opened it there: the disk otherwise stays in Finder's sidebar. The .dmg file stays where it was
downloaded: deleting it there needs the student's leave for the Downloads folder (the user's call, 2026-11-27).
"""

import plistlib
import subprocess
import sys
import threading
from pathlib import Path

import psutil

BUNDLED = "__compiled__" in globals()  # the built app
_updater = None  # Sparkle's controller, kept: it stops checking once nothing holds it


def start() -> None:
    """Start Sparkle's updater in the built app once its run loop runs: Sparkle asks for the main thread."""
    if not BUNDLED:
        return
    from PyObjCTools import AppHelper

    AppHelper.callAfter(_start)


def _start() -> None:
    global _updater
    if _updater is not None:
        return
    import Foundation
    import objc

    bundle = Foundation.NSBundle.mainBundle()
    framework = Path(str(bundle.privateFrameworksPath())) / "Sparkle.framework"
    if not framework.is_dir() or not bundle.objectForInfoDictionaryKey_("SUPublicEDKey"):
        return  # built with no key: Sparkle would refuse to start, so the app runs with no updater
    sparkle: dict = {}
    objc.loadBundle("Sparkle", sparkle, bundle_path=str(framework))
    controller = sparkle["SPUStandardUpdaterController"].alloc()
    _updater = controller.initWithStartingUpdater_updaterDelegate_userDriverDelegate_(True, None, None)


def eject_installer() -> None:
    """In the built app on a Mac, eject its installer's disk image in a thread of its own: `hdiutil` takes a moment."""
    if not BUNDLED or sys.platform != "darwin":
        return
    app = Path(psutil.Process().exe()).parents[2]  # .app/Contents/MacOS/<program>; never sys.executable in Nuitka
    threading.Thread(target=_eject, args=(app,), daemon=True, name="eject-installer").start()


def _eject(app: Path) -> None:
    info = subprocess.run(["/usr/bin/hdiutil", "info", "-plist"], capture_output=True, check=False).stdout
    for mount in installer_disks(plistlib.loads(info) if info else {}, app):
        # Never --force: a disk the student has a file open on stays, and is no harm.
        subprocess.run(["/usr/bin/hdiutil", "detach", mount], capture_output=True, check=False)


def installer_disks(info: dict, app: Path) -> list[str]:
    """The mounted disks (`hdiutil info -plist`) that hold this very build of `app` (its bundle ID and build number),
    while `app` runs from elsewhere. A newer download the student hasn't installed yet stays: they may open the old
    app before they drag the new one in. None while `app` runs from a disk image: from the disk itself, or from the
    copy macOS runs a downloaded app from where it lies (App Translocation). Ejecting would pull the app from under
    itself."""
    ours = _build(app)
    if ours is None or "/AppTranslocation/" in str(app):
        return []
    mounts = [entity["mount-point"] for image in info.get("images", []) for entity in image.get("system-entities", [])
              if "mount-point" in entity]
    return [mount for mount in mounts if not app.is_relative_to(mount)
            and any(_build(copy) == ours for copy in Path(mount).glob("*.app"))]


def _build(app: Path) -> tuple[str, str] | None:
    """An app's bundle ID and build number (CFBundleVersion), or None when it has no Info.plist to read."""
    try:
        plist = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    except (OSError, plistlib.InvalidFileException):
        return None
    return plist.get("CFBundleIdentifier"), plist.get("CFBundleVersion")
