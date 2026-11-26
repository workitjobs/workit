"""The Apply accounts host (KAN-592): the native messaging host that gives the
WorkIt extension, in Lisul's own Chrome, one Employer account's login from
Keychain, so the extension fills Workday's Sign In and Chrome offers to save it.
With a fake Keychain and an in-memory Tracker."""

import io
import json
import struct
import subprocess
import sys
from datetime import date
from pathlib import Path

import fake_chrome
import pytest

from apply import cli, native_host
from apply.keychain import InMemoryKeychain
from apply.model import Status
from apply.tracker import EmployerAccount, InMemoryTracker, Row

CACI = "caci.wd1.myworkdayjobs.com"
XCEL = "xcel.wd1.myworkdayjobs.com"
EMAIL = "test.person@example.com"
PASSWORD = "Generated-Test-Pw-1!x"
EXTENSION = native_host.EXTENSION_ORIGIN  # the ID manifest.json's key gives: the test below checks it


def listed(*sites: str) -> InMemoryTracker:
    tracker = InMemoryTracker()
    for site in sites:
        tracker.add_employer_account(EmployerAccount(site.split(".")[0].upper(), site, EMAIL, date(2026, 11, 3)))
    return tracker


def ask(request: dict, origin: str = EXTENSION, tracker=None, keychain=None) -> dict:
    return native_host.answer(origin, request, tracker if tracker is not None else listed(CACI),
                              keychain or InMemoryKeychain({CACI: PASSWORD}))


def test_the_extension_gets_a_listed_tenants_login_from_keychain():
    assert ask({"tenant": CACI, "want": "login"}) == {"company": "CACI", "login": EMAIL, "password": PASSWORD}


def test_asking_whether_apply_knows_a_tenant_never_gives_its_password():
    assert ask({"tenant": CACI, "want": "known"}) == {"company": "CACI", "login": EMAIL}


def test_a_caller_that_is_not_the_workit_extension_gets_nothing():
    answer = ask({"tenant": CACI, "want": "login"}, origin="chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/")

    assert "password" not in answer and "none" in answer


def test_a_tenant_not_in_the_employer_accounts_list_gets_nothing_even_with_a_keychain_password():
    answer = ask({"tenant": XCEL, "want": "login"}, keychain=InMemoryKeychain({CACI: PASSWORD, XCEL: PASSWORD}))

    assert "password" not in answer and "none" in answer


def test_a_tenant_whose_password_sign_in_failed_gets_nothing():
    tracker = listed(CACI)
    tracker.add(Row("a1", "CACI", "Intern", f"https://{CACI}/job/1", "workday", Status.HANDOFF,
                    reason=f"Sign-in failed at {CACI}: Workday refused the password."))

    answer = ask({"tenant": CACI, "want": "login"}, tracker=tracker)

    assert "password" not in answer and "none" in answer


def test_a_listed_tenant_with_no_keychain_password_gets_nothing():
    answer = ask({"tenant": CACI, "want": "known"}, keychain=InMemoryKeychain())

    assert answer.keys() == {"none"}


def framed(message: dict) -> bytes:
    body = json.dumps(message).encode()
    return struct.pack("=I", len(body)) + body


def test_one_framed_message_gets_one_framed_answer_and_the_log_names_the_tenant_but_never_the_password(tmp_path):
    out, log = io.BytesIO(), tmp_path / "apply-accounts-host.log"

    native_host.serve([EXTENSION], io.BytesIO(framed({"tenant": CACI, "want": "login"})), out,
                      listed(CACI), InMemoryKeychain({CACI: PASSWORD}), log)

    (size,) = struct.unpack("=I", out.getvalue()[:4])
    assert json.loads(out.getvalue()[4:4 + size])["password"] == PASSWORD
    assert CACI in log.read_text() and PASSWORD not in log.read_text()


def test_the_host_answers_the_id_that_the_extensions_manifest_key_gives():
    import base64
    import hashlib
    from pathlib import Path

    key = json.loads((Path(__file__).parents[2] / "autofiller_extension" / "manifest.json").read_text())["key"]
    digest = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    assert native_host.EXTENSION_ID == "".join(chr(ord("a") + int(c, 16)) for c in digest)


def test_install_writes_a_host_manifest_that_names_only_the_workit_extension_and_a_wrapper_that_runs_the_host(tmp_path):
    """Faults: the manifest lets another extension call the host, or the wrapper can't run, runs another Python, or
    doesn't set APPLY_HOME (the host then answers from another data folder). Windows: test_each_os.py."""
    hosts, home = tmp_path / "NativeMessagingHosts", tmp_path / "apply"

    manifest = native_host.install(hosts, "/venv/bin/python", home, "darwin", fake_chrome.NoRegistry())

    written = json.loads(manifest.read_text())
    assert manifest == hosts / "com.workit.apply_accounts.json"
    assert written["name"] == "com.workit.apply_accounts" and written["type"] == "stdio"
    assert written["allowed_origins"] == [EXTENSION]
    wrapper = written["path"]
    assert wrapper.startswith(str(home)) and oct(Path(wrapper).stat().st_mode & 0o777) == "0o700"
    assert Path(wrapper).read_text() == f'#!/bin/sh\nAPPLY_HOME={home} exec /venv/bin/python -m apply.native_host "$@"\n'


def test_adopting_lists_each_keychain_tenant_the_tracker_lacks_once_with_its_company_from_a_row(tmp_path):
    tracker = listed(CACI)
    tracker.add(Row("a1", "Xcel Energy", "Intern", f"https://{XCEL}/en-US/careers/job/1", "workday", Status.HANDOFF))
    in_keychain = [CACI, XCEL, "zillow.wd5.myworkdayjobs.com"]

    added = native_host.adopt(in_keychain, tracker, EMAIL, date(2026, 11, 3))
    native_host.adopt(in_keychain, tracker, EMAIL, date(2026, 11, 3))

    assert added == [XCEL, "zillow.wd5.myworkdayjobs.com"]
    assert [(a.company, a.site) for a in tracker.employer_accounts()] == [
        ("CACI", CACI), ("Xcel Energy", XCEL), ("Zillow", "zillow.wd5.myworkdayjobs.com")]


# `security dump-keychain` without -d: attributes only. One apply-ats item, one of another service, one with no account.
DUMP = f"""keychain: "/Users/test/Library/Keychains/login.keychain-db"
class: "genp"
attributes:
    "acct"<blob>="{CACI}"
    "svce"<blob>="apply-ats"
keychain: "/Users/test/Library/Keychains/login.keychain-db"
class: "genp"
attributes:
    "acct"<blob>="{EMAIL}"
    "svce"<blob>="apply-gmail"
keychain: "/Users/test/Library/Keychains/login.keychain-db"
class: "genp"
attributes:
    "svce"<blob>="apply-ats"
keychain: "/Users/test/Library/Keychains/login.keychain-db"
class: "genp"
attributes:
    "svce"<blob>="apply-ats"
    "acct"<blob>="{XCEL}"
"""


def test_the_backfill_reads_the_mac_keychains_apply_ats_sites_from_attributes_only(monkeypatch):
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, DUMP, "")

    monkeypatch.setattr(sys, "platform", "darwin")
    assert cli._mac_keychain_sites(run) == [CACI, XCEL]
    assert calls == [["security", "dump-keychain"]]  # no -d: never a password


def test_the_backfill_reads_nothing_on_another_system(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert cli._mac_keychain_sites(lambda *a, **kw: pytest.fail("ran security off a Mac")) == []
