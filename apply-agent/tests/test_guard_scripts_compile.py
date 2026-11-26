"""Every guard script Apply builds compiles (KAN-868), with no browser: CI's fast list.

A guard script is one function, built from shared parts. A name declared twice in it (a second `const dispatchOf`,
a second `signInStep`) is an early SyntaxError, so the whole script never runs, and the page is unguarded with no
error Apply sees: twice while KAN-868 was built, every hostile page sent. Fault: any part that declares a name
another part declares."""

import subprocess

import pytest
from playwright._impl._driver import compute_driver_executable

from apply import submit_guard

SCRIPTS = {
    "rehearsal": lambda: submit_guard.rehearsal_script(),
    "rehearsal, plain": lambda: submit_guard.rehearsal_script(port=True),
    "drive": lambda: submit_guard.drive_script(),
    "drive, plain": lambda: submit_guard.drive_script(port=True),
    "drive, late": lambda: submit_guard.drive_script(late=True),
    "drive, at open": lambda: submit_guard.drive_script(at_open=True),
}


@pytest.mark.parametrize("name", list(SCRIPTS))
def test_each_guard_script_compiles(name, tmp_path):
    script = tmp_path / "guard.js"
    script.write_text(SCRIPTS[name]())
    checked = subprocess.run([compute_driver_executable()[0], "--check", str(script)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr[-2000:]
