"""A Worker never runs older worker extension code without Apply saying so (KAN-764). On 2026-11-10 a seed copied
from another profiles folder registered that folder's copy, 5 days old, and every new Worker loaded it at the same
feature level as current code. With fakes: a fake `ps`, Chrome preference files and a fake hello. No browser."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from test_plain_bridge import (  # noqa: F401 (a fixture)
    ENGINE,
    bridge,
    fake_worker,
    read,
)

from apply.plain import extension
from apply.plain.bridge import FEATURES, OUT_OF_DATE
from apply.plain.extension import CODE_FILES, EXTENSION_DIR, EXTENSION_ID, STAMP
from apply.plain.launcher import PlainWorkers

FILES = {"engine.js": b"engine", "guards/lifted.js": b"x"}


def registered(profile: Path, folder: Path) -> Path:
    """A Chrome profile whose Load unpacked registered the worker extension from `folder`."""
    (profile / "Default").mkdir(parents=True, exist_ok=True)
    (profile / "Default" / "Preferences").write_text(json.dumps(
        {"extensions": {"settings": {EXTENSION_ID: {"path": str(folder)}}}}))
    return profile


def old_copy(folder: Path) -> Path:
    """A copy `install` made of older extension code (KAN-645's tile.js), stamped with that code's hash."""
    folder.mkdir(parents=True, exist_ok=True)
    for part in CODE_FILES:
        (shutil.copytree if (EXTENSION_DIR / part).is_dir() else shutil.copy2)(EXTENSION_DIR / part, folder / part)
    (folder / "ops" / "tile.js").write_text("// KAN-645's tile.js: no title in tile.shown\n")
    (folder / STAMP).write_text(extension.code_hash(folder) + "\n")
    return folder


@pytest.fixture
def ps(monkeypatch):
    """`ps -axo pid=,command=`, faked: `ps.lines` are the processes it lists."""
    real = subprocess.run

    def run(command, *args, **kwargs):
        if command[:2] == ["ps", "-axo"]:
            return subprocess.CompletedProcess(command, 0, stdout="\n".join(run.lines) + "\n", stderr="")
        return real(command, *args, **kwargs)
    run.lines = []
    monkeypatch.setattr(extension.subprocess, "run", run)
    return run


def chrome(pid: int, profile: Path, *more: str) -> str:
    return f"{pid:>6} /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --user-data-dir={profile} " \
           "--no-first-run " + " ".join(more)


def test_loaders_are_the_running_chromes_that_load_the_folder(tmp_path, ps):
    shared = old_copy(tmp_path / "default" / "worker-extension")
    other = tmp_path / "testing-copy"
    jpm = registered(tmp_path / "profiles-jpm" / "plain-1", shared)
    msft = registered(tmp_path / "profiles-msft" / "plain-1", tmp_path / "profiles-msft" / "worker-extension")
    ps.lines = [chrome(12302, jpm), chrome(12310, jpm, "--type=renderer"), chrome(13000, msft),
                f"  14000 /x/Google Chrome for Testing --user-data-dir={tmp_path / 't'} --load-extension={other}",
                "  15000 /bin/zsh -l"]

    assert extension.loaders(shared) == [12302]  # its browser process only, not its renderer
    assert extension.loaders(other) == [14000]
    assert extension.loaders(tmp_path / "nowhere") == []


def test_a_stale_copy_no_chrome_loads_is_brought_up_to_date(tmp_path, ps):
    shared = old_copy(tmp_path / "worker-extension")

    assert extension.refresh(shared, FILES)
    assert extension.code_hash(shared) == extension.code_hash(EXTENSION_DIR)
    assert not extension.refresh(shared, FILES)  # current already


def test_a_stale_copy_a_running_chrome_loads_is_never_changed_under_it(tmp_path, ps):
    shared = old_copy(tmp_path / "worker-extension")
    before = extension.code_hash(shared)
    ps.lines = [chrome(12302, registered(tmp_path / "plain-1", shared))]

    assert not extension.refresh(shared, FILES)
    assert extension.code_hash(shared) == before


def test_a_checkout_is_never_replaced(tmp_path, ps):
    checkout = old_copy(tmp_path / "wt" / "worker-extension")
    (checkout / STAMP).unlink()  # Load unpacked of a checkout: not a copy Apply made
    before = extension.code_hash(checkout)

    assert not extension.refresh(checkout, FILES)
    assert extension.code_hash(checkout) == before


@pytest.fixture
def workers(tmp_path, monkeypatch, ps):
    """A profiles folder (profiles-jpm) whose seed registered another folder's copy (the default one's), of old code."""
    monkeypatch.setattr(extension, "engine_identity", lambda engine=None: ENGINE)
    monkeypatch.setattr(extension, "generated", lambda identity=None: FILES)
    shared = old_copy(tmp_path / "default" / "worker-extension")
    profiles = tmp_path / "profiles-jpm"
    registered(profiles / "plain-seed", shared)
    return PlainWorkers(profiles, kind="chrome"), shared


def test_a_worker_about_to_start_gets_its_seeds_folder_brought_up_to_date(workers, capsys):
    plain, shared = workers

    plain.prepare(0)

    assert extension.code_hash(shared) == extension.code_hash(EXTENSION_DIR)
    assert f"Updated the worker extension in {shared.resolve()}" in capsys.readouterr().err


def test_the_seeds_folder_stays_while_another_folders_worker_loads_it(workers, tmp_path, ps):
    plain, shared = workers
    before = extension.code_hash(shared)
    ps.lines = [chrome(13000, registered(tmp_path / "profiles-msft" / "plain-1", shared))]  # a running Worker

    plain.prepare(0)

    assert extension.code_hash(shared) == before
    assert plain.bridge.other_code(0) == shared  # welcomed as out of date, with where


def test_a_worker_whose_folder_holds_other_code_is_welcomed_as_out_of_date_with_one_line(bridge, tmp_path, capsys):
    shared = old_copy(tmp_path / "worker-extension")
    bridge.code, bridge.loaded = extension.code_hash(EXTENSION_DIR), lambda worker: shared
    sock = fake_worker(bridge, worker=0, features=FEATURES)  # its feature level is current: only the code differs
    assert read(sock)["type"] == "welcome"  # never refused: the run goes on

    connection = bridge.wait_for(0, timeout=5)
    said = capsys.readouterr().err

    assert connection.stale
    assert said.count(OUT_OF_DATE) == 1 and str(shared) in said and "start Apply again" in said


def test_a_worker_whose_folder_holds_this_applys_code_is_not_out_of_date(bridge, capsys):
    bridge.code, bridge.loaded = extension.code_hash(EXTENSION_DIR), lambda worker: EXTENSION_DIR
    sock = fake_worker(bridge, worker=0, features=FEATURES)
    assert read(sock)["type"] == "welcome"

    assert not bridge.wait_for(0, timeout=5).stale and OUT_OF_DATE not in capsys.readouterr().err
