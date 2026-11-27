"""WorkIt Auto Apply's updates (W8 step 3, KAN-941): Sparkle, in the built app only.

scripts/build_app.py puts Sparkle.framework in the app and its settings in Info.plist: the feed's address
(SUFeedURL), the update key's public half (SUPublicEDKey), and checks with no question asked
(SUEnableAutomaticChecks) that download a newer build in the background and install it when the student quits
(SUAutomaticallyUpdate). `start` starts Sparkle's own updater with them, which then checks at launch and each day.
A checkout, or an app built before there was a key, has neither, and nothing starts.
"""

from pathlib import Path

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
