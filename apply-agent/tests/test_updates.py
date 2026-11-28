"""The built app's install (apply.updates): it ejects the disk image it was installed from, and only that one. Needs
no Mac and no disk image: hdiutil's answer is faked. In CI."""

import plistlib
from pathlib import Path
from types import SimpleNamespace

from apply import updates

OURS = "ai.workitjobs.autoapply"
BUILT = "202611271200"


def app_in(folder: Path, bundle_id: str, build: str = BUILT) -> Path:
    app = folder / "WorkIt Auto Apply.app"
    (app / "Contents").mkdir(parents=True)
    plist = {"CFBundleIdentifier": bundle_id, "CFBundleVersion": build}
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(plist))
    return app


def test_the_app_ejects_its_installer_and_never_a_disk_it_runs_from_another_apps_or_a_newer_download(tmp_path,
                                                                                                    monkeypatch):
    # The faults: a disk ejected from under the running app, which runs from it or from macOS's moved-aside copy of
    # it (App Translocation); another app's installer ejected because it holds an app too; and a newer download the
    # student hasn't dragged in yet ejected because it holds this app.
    installer, other, newer, running = (tmp_path / name for name in ("installer", "other", "newer", "running"))
    installed = app_in(tmp_path / "Applications", OURS)
    app_in(installer, OURS)
    app_in(other, "com.example.other")
    app_in(newer, OURS, "202612011200")
    from_disk = app_in(running, OURS)
    moved_aside = app_in(tmp_path / "AppTranslocation" / "A1B2", OURS)
    info = {"images": [{"system-entities": [{"dev-entry": "/dev/disk9"}, {"mount-point": str(mount)}]}
                       for mount in (installer, other, newer, running)]}
    detached = []

    def hdiutil(command, **kwargs):
        if command[1] != "info":
            detached.append(command[2])
        return SimpleNamespace(stdout=plistlib.dumps(info) if command[1] == "info" else b"")

    monkeypatch.setattr(updates.subprocess, "run", hdiutil)
    updates._eject(installed)
    assert sorted(detached) == sorted([str(installer), str(running)])
    detached.clear()
    updates._eject(from_disk)
    assert str(running) not in detached
    detached.clear()
    updates._eject(moved_aside)
    assert detached == []
