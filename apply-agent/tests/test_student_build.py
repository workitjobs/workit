"""The Student build (KAN-723, W3; D14): WorkIt Auto Apply holds no developer part, and nothing in it turns one on.
No browser: in CI.

- Its path (apply.student) loads no module in apply.build.DEVELOPER, so the compile can leave them all out.
- It reads no policies.yaml: `ask_model: claude` or `live_runs: true` in the data folder changes nothing.
- Where a Developer checkout would start `claude -p` (Claude fill, Rescue, Ask Claude, research), read Gmail or keep
  a Repair request, the Student build does none of it."""

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from apply import brief, build, orchestrator, profile, rehearsal, student
from apply.adapters import ClaudeError
from apply.ask_model import live_claude
from apply.fillers import FILLERS
from apply.model import Posting, Status
from apply.profile import (
    load_policies as real_policies,  # before conftest's fixture strips the switches
)
from apply.worker import Result

# In a new process, so nothing a test imported counts. It runs what the app runs first: its adapters, and a plain
# Worker's first page call (which loaded Ask Claude and Gmail, KAN-723). As conftest does, it blocks the network and
# gives keyring its null backend; APPLY_HOME is conftest's. Its hosted models get stand-in keys (KEYS): an environment
# variable comes before the Keychain and the checkout's .env, so no real key is read, and CI, which has none, passes.
LOADED = """import json, sys
from pathlib import Path
from apply import build
build.STUDENT = True
sys.path.insert(0, sys.argv[2])
import keyring, network_block
from keyring.backends import null
network_block.install()
network_block.begin()
keyring.set_keyring(null.Keyring())
from apply import student
from apply.plain import fixed
from apply.profile import ApplicantProfile
student.adapters(ApplicantProfile.load(Path(sys.argv[1])))
fixed.functions()
print(json.dumps({"loaded": sorted(m for m in sys.modules if m in build.DEVELOPER), "reached": network_block.end()}))"""
KEYS = {"GROQ_API_KEY": "not-a-key", "GEMINI_API_KEY": "not-a-key"}


@pytest.fixture
def student_build(monkeypatch):
    monkeypatch.setattr(build, "STUDENT", True)


def test_the_student_path_loads_no_developer_module(tmp_path):
    """Nuitka compiles what apply.student imports and leaves out each DEVELOPER module: one that the Student path
    imports, or loads as it runs, would fail in the app."""
    (tmp_path / "applicant-profile.yaml").write_text("identity: {}\n")
    run = subprocess.run([sys.executable, "-c", LOADED, str(tmp_path / "applicant-profile.yaml"), str(Path(__file__).parent)],
                         capture_output=True, text=True, env=os.environ | KEYS)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == {"loaded": [], "reached": []}, (
        "the Student build's path loads a developer module (apply.build.DEVELOPER), or reached the network: import it "
        "inside the function the Student build never reaches")


def test_every_developer_module_is_a_module():
    for name in build.DEVELOPER:  # a misspelt name would leave the real module in the compile
        assert importlib.util.find_spec(name) is not None, name


def test_policies_in_the_data_folder_change_nothing(tmp_path, monkeypatch, student_build):
    monkeypatch.setattr(profile, "load_policies", real_policies)
    mine, applicant = tmp_path / "policies.yaml", tmp_path / "applicant-profile.yaml"
    monkeypatch.setattr(profile, "OVERRIDE", mine)  # the data folder's, and the one beside the profile
    applicant.write_text("identity: {}\n")
    policies = lambda: (profile.load_policies(), profile.ApplicantProfile.load(applicant).policies())
    before = policies()
    mine.write_text("ask_model: claude\nlive_runs: true\nrepair: {max_per_day: 5}\nphone_push: true\n")
    assert policies() == before
    assert before[0]["ask_model"] == build.STUDENT_POLICIES["ask_model"]
    monkeypatch.setattr(build, "STUDENT", False)  # the same file does reach a Developer checkout
    assert profile.load_policies()["ask_model"] == "claude"
    assert profile.ApplicantProfile.load(applicant).policies()["live_runs"] is True


def test_even_ask_model_claude_builds_no_claude_cli():
    assert isinstance(live_claude({"ask_model": "claude"}, student.NoClaude()), student.NoClaude)


@pytest.mark.parametrize("call", ["ask", "drive", "research"])
def test_no_claude_refuses_every_call_to_claude(call):
    with pytest.raises(ClaudeError, match="WorkIt Auto Apply doesn't"):
        getattr(student.NoClaude(), call)(model="haiku")


class Filler:
    def __init__(self, accounts, rescue, **options):
        self.rescue = rescue


def posting(url: str) -> Posting:
    return Posting(id="p1", company="Acme", title="Intern", url=url)


def by_filler(url: str):
    """The Filler by_filler hands the form to, or the Result it gives without one."""
    given = []
    profile_ = SimpleNamespace(policy=lambda name: None, get=lambda key: None)
    result = orchestrator.by_filler(posting(url), SimpleNamespace(), profile_, student.NoClaude(),
                                    lambda: SimpleNamespace(), lambda filler, site: given.append(filler) or Result(Status.HELD))
    return given[0] if given else result


def test_a_job_system_with_no_filler_is_a_handoff_not_claude_fill(student_build):
    result = by_filler("https://careers.example.com/jobs/1")
    assert result.status == Status.HANDOFF and "WorkIt Auto Apply can't fill" in result.reason


def test_a_filler_gets_no_rescue(student_build, monkeypatch):
    monkeypatch.setitem(FILLERS, "workday", Filler)
    assert by_filler("https://acme.wd1.myworkdayjobs.com/careers/job/1").rescue is None
    monkeypatch.setattr(build, "STUDENT", False)  # a Developer checkout's Filler has one
    assert by_filler("https://acme.wd1.myworkdayjobs.com/careers/job/1").rescue is not None


def test_no_emailed_code_no_ask_claude_no_repair_request(student_build):
    assert rehearsal._email_code(SimpleNamespace(), "greenhouse", lambda status, why: None) is None
    board = SimpleNamespace(updates=[], update=lambda n, **fields: board.updates.append(fields),
                            asks=lambda n: [{"id": "1", "message": "fix the email field"}])
    asker = rehearsal._Ask(lambda: None, SimpleNamespace(board=board), None, 0, print)
    asker.open(SimpleNamespace())
    assert board.updates == [] and asker.asked() == []  # its tile takes no message, and none reaches Claude
    never = SimpleNamespace(add=lambda request: pytest.fail("the Student build kept a Repair request"))
    orchestrator.keep_repair_requests(SimpleNamespace(repairs=never), posting("https://x.example/1"), Result(Status.FAILED))


def test_a_brief_is_never_researched(student_build, tmp_path, monkeypatch):
    monkeypatch.setattr(brief, "BRIEFS", tmp_path)
    monkeypatch.setattr(brief, "research", lambda *a, **k: pytest.fail("the Student build researched a company"))
    claude = SimpleNamespace(ask_kind=lambda kind, data: {"team": ""})  # brief.team, a WorkIt kind (D5)
    assert brief.brief(posting("https://x.example/1"), SimpleNamespace(), claude, date(2026, 11, 14)) == ""
