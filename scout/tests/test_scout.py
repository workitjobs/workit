"""
Scout without a model: ScriptedLLM stands in for the provider, so these run
with no network, no Ollama and no API key. Run from backend/, whose venv
installs this package: `uv run pytest ../scout/tests`.
"""

import asyncio
import json

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel
from referencing.exceptions import Unresolvable
from workit_scout import llm as llm_module
from workit_scout.agent import MAX_REPLY_CHARS, run
from workit_scout.facts import bank_facts, job_facts
from workit_scout.identity import Identity
from workit_scout.llm import LLM, Spent
from workit_scout.schemas import (
    ChatMessage,
    ErrorEvent,
    ResumeFacts,
    TextEvent,
)
from workit_scout.settings import Endpoint, ScoutSettings
from workit_scout.testing import ScriptedLLM, endpoint

_REQUEST = httpx.Request("POST", "http://primary.test/v1/chat/completions")


def rate_limited() -> RateLimitError:
    return RateLimitError(
        "quota", response=httpx.Response(429, request=_REQUEST), body=None
    )


def server_error() -> InternalServerError:
    return InternalServerError(
        "down", response=httpx.Response(503, request=_REQUEST), body=None
    )


def bad_request() -> BadRequestError:
    return BadRequestError(
        "bad model", response=httpx.Response(400, request=_REQUEST), body=None
    )


def too_large() -> APIStatusError:
    return APIStatusError(
        "Request too large", response=httpx.Response(413, request=_REQUEST), body=None
    )


def context_too_long() -> BadRequestError:
    body = {"code": "context_length_exceeded", "message": "maximum context length"}
    return BadRequestError(
        "maximum context length", response=httpx.Response(400, request=_REQUEST), body=body
    )


def collect(llm: LLM, *texts: str, identity=Identity(), **facts) -> list:
    async def go():
        messages = [ChatMessage(role="user", content=t) for t in texts]
        return [event async for event in run(messages, llm, identity=identity, **facts)]

    return asyncio.run(go())


def reply(events) -> str:
    return "".join(e.delta for e in events if isinstance(e, TextEvent))


# --- the model seam -------------------------------------------------------------


def test_primary_answers():
    assert reply(collect(ScriptedLLM(["Hi", " there"]), "hello")) == "Hi there"


def test_rate_limit_falls_back_once():
    events = collect(ScriptedLLM(rate_limited(), ["from fallback"]), "hello")
    assert reply(events) == "from fallback"


def test_the_chain_moves_down_past_a_429_a_5xx_and_a_dead_endpoint():
    down = APIConnectionError(request=_REQUEST)
    fake = ScriptedLLM(rate_limited(), server_error(), down, ["fourth"])
    assert reply(collect(fake, "hello")) == "fourth"
    # The 5xx endpoint is asked three times, once and after each pause.
    assert len(fake.prompts) == 6


class BusyAtFirst(ScriptedLLM):
    """The chain's first endpoint answers 503 to its first `busy` asks, then
    follows its script, as Gemini's free tier does under high demand."""

    def __init__(self, busy: int, *scripts):
        super().__init__(*scripts)
        self.busy = busy
        self.asked: dict = {}

    async def _complete(self, client, endpoint, messages):
        self.asked[endpoint] = self.asked.get(endpoint, 0) + 1
        if endpoint == self._endpoints[0][0] and self.asked[endpoint] <= self.busy:
            self.prompts.append(list(messages))
            raise server_error()
        async for piece in super()._complete(client, endpoint, messages):
            yield piece


def test_a_busy_endpoint_is_asked_again_before_the_chain_moves_down():
    fake = BusyAtFirst(2, ["from the first"], ["from the second"])
    assert reply(collect(fake, "hello")) == "from the first"
    assert len(fake.prompts) == 3


def test_a_busy_structured_call_is_asked_again():
    fake = BusyAtFirst(1, ['{"title": "T", "bullets": []}'])
    assert ask_json(fake).title == "T"
    assert len(fake.prompts) == 2


def test_a_busy_schema_call_is_asked_again():
    fake = BusyAtFirst(2, ['{"a": 1}'])
    messages = [{"role": "user", "content": "x"}]
    answer, _ = asyncio.run(fake.complete_schema(messages, {"type": "object"}, identity=Identity()))
    assert answer == {"a": 1}


def test_an_endpoint_busy_past_its_pauses_gives_way_to_the_next():
    fake = BusyAtFirst(3, ["never"], ["from the second"])
    assert reply(collect(fake, "hello")) == "from the second"
    assert fake.asked[endpoint(0)] == 3


def test_a_busy_endpoint_waits_each_pause_in_turn(monkeypatch):
    waited = []

    async def sleep(seconds):
        waited.append(seconds)

    monkeypatch.setattr(llm_module.asyncio, "sleep", sleep)
    fake = BusyAtFirst(2, ['{"title": "T", "bullets": []}'])
    fake.BUSY_PAUSES = LLM.BUSY_PAUSES
    assert ask_json(fake).title == "T"
    assert waited == list(LLM.BUSY_PAUSES)


def test_a_429_and_a_dead_endpoint_are_not_asked_again():
    down = APIConnectionError(request=_REQUEST)
    fake = ScriptedLLM(rate_limited(), down, ["third"])
    assert reply(collect(fake, "hello")) == "third"
    assert len(fake.prompts) == 3


def test_a_5xx_mid_reply_is_not_asked_again():
    events = collect(ScriptedLLM(["Half a", server_error()], ["whole"]), "hello")
    assert reply(events) == "Half a"
    assert events[-1] == ErrorEvent(message=llm_module.CUT_OFF)


def test_unreachable_primary_falls_back():
    down = APIConnectionError(request=_REQUEST)
    assert reply(collect(ScriptedLLM(down, ["ok"]), "hello")) == "ok"


def test_no_fallback_reports_quota():
    events = collect(ScriptedLLM(rate_limited()), "hello")
    assert events == [ErrorEvent(message=llm_module.OUT_OF_QUOTA)]


def test_misconfiguration_does_not_fall_back():
    fake = ScriptedLLM(bad_request(), ["should not run"])
    assert collect(fake, "hello") == [ErrorEvent(message=llm_module.OFFLINE)]
    assert len(fake.prompts) == 1


@pytest.mark.parametrize("error", [too_large, context_too_long])
def test_a_request_too_large_moves_down_the_chain(error):
    fake = ScriptedLLM(error(), ["from a bigger model"])
    assert reply(collect(fake, "hello")) == "from a bigger model"


def test_a_request_too_large_for_every_endpoint_says_so():
    with pytest.raises(llm_module.RequestTooLarge, match="too long"):
        ask_json(ScriptedLLM(rate_limited(), too_large()))


def test_failure_mid_reply_is_not_retried():
    # A retry would send the user the start of the reply twice.
    events = collect(ScriptedLLM(["Half a", rate_limited()], ["whole"]), "hello")
    assert reply(events) == "Half a"
    assert events[-1] == ErrorEvent(message=llm_module.CUT_OFF)


def test_the_prompt_sent_holds_no_identity_data():
    fake = ScriptedLLM(["ok"])
    me = Identity(
        name="Sam Seeker",
        email="sam@example.com",
        phone="631-555-0100",
        links=["https://github.com/samseeker"],
    )
    collect(
        fake,
        "I'm Sam Seeker, sam@example.com, (631) 555-0100, github.com/samseeker",
        identity=me,
        resume=ResumeFacts(projects=["Robot arm, by Sam Seeker"]),
    )
    sent = str(fake.prompts)
    for value in ("Sam", "Seeker", "sam@example.com", "555", "samseeker"):
        assert value not in sent
    assert "[name]" in sent and "[email]" in sent and "[phone]" in sent


def test_long_reply_is_cut_at_the_cap():
    events = collect(ScriptedLLM(["x" * 100] * 100), "hello")
    assert len(reply(events)) == MAX_REPLY_CHARS


# --- the structured call -----------------------------------------------------------


class Entry(BaseModel):
    title: str
    bullets: list[str]


def ask_json(llm: LLM, identity=Identity()) -> Entry:
    messages = [{"role": "user", "content": "draft it"}]
    return asyncio.run(llm.complete_json(messages, Entry, identity=identity))


def test_a_structured_call_returns_the_checked_object():
    fake = ScriptedLLM(['{"title": "Intern", ', '"bullets": ["Built a robot"]}'])
    assert ask_json(fake) == Entry(title="Intern", bullets=["Built a robot"])


def test_a_structured_call_says_which_model_replied_and_its_tokens():
    reply = '{"title": "T", "bullets": []}'
    fake = ScriptedLLM(rate_limited(), [reply])
    answered = llm_module.Answered()
    messages = [{"role": "user", "content": "draft it"}]
    asyncio.run(fake.complete_json(messages, Entry, identity=Identity(), answered=answered))
    # The second endpoint replied; ScriptedLLM costs a token a character
    assert answered.model == endpoint(1).model
    assert answered.spent == llm_module.Spent(len("draft it"), len(reply))


def test_a_reply_that_fails_the_check_still_says_who_gave_it():
    answered = llm_module.Answered()
    messages = [{"role": "user", "content": "draft it"}]
    with pytest.raises(llm_module.InvalidReply):
        asyncio.run(ScriptedLLM(["not json"]).complete_json(messages, Entry, identity=Identity(), answered=answered))
    assert (answered.model, answered.spent.output_tokens) == (endpoint(0).model, len("not json"))


def test_a_structured_call_no_endpoint_answers_names_no_model():
    answered = llm_module.Answered()
    messages = [{"role": "user", "content": "draft it"}]
    with pytest.raises(llm_module.ScoutUnavailable):
        asyncio.run(ScriptedLLM(rate_limited()).complete_json(messages, Entry, identity=Identity(), answered=answered))
    assert answered == llm_module.Answered()


def test_a_structured_call_falls_down_the_chain():
    fake = ScriptedLLM(
        rate_limited(), server_error(), ['{"title": "T", "bullets": []}']
    )
    assert ask_json(fake).title == "T"


class StalledFirst(ScriptedLLM):
    """The chain's first endpoint never answers; the rest follow their scripts."""

    async def _complete_schema(self, client, endpoint, messages, *args, **kwargs):
        if endpoint == self._endpoints[0][0]:
            await asyncio.sleep(60)
        return await super()._complete_schema(client, endpoint, messages, *args, **kwargs)


def test_a_structured_call_moves_on_from_an_endpoint_slower_than_its_wait():
    fake = StalledFirst(["never"], ['{"title": "T", "bullets": []}'])
    messages = [{"role": "user", "content": "draft it"}]
    answer = asyncio.run(fake.complete_json(messages, Entry, identity=Identity(), wait=0.05))
    assert answer.title == "T"


def test_a_structured_call_with_every_endpoint_stalled_is_offline():
    fake = StalledFirst(["never"])
    messages = [{"role": "user", "content": "draft it"}]
    with pytest.raises(llm_module.ScoutUnavailable, match="offline"):
        asyncio.run(fake.complete_json(messages, Entry, identity=Identity(), wait=0.05))


@pytest.mark.parametrize("bad", ['{"title": "T"}', "Sure! Here it is: {", ""])
def test_a_reply_that_fails_the_check_is_rejected(bad):
    with pytest.raises(llm_module.InvalidReply):
        ask_json(ScriptedLLM([bad], ['{"title": "T", "bullets": []}']))


def test_a_structured_call_sends_no_identity_data():
    fake = ScriptedLLM(['{"title": "T", "bullets": []}'])
    asyncio.run(
        fake.complete_json(
            [{"role": "user", "content": "Sam Seeker at sam@example.com"}],
            Entry,
            identity=Identity(name="Sam Seeker"),
        )
    )
    assert fake.prompts == [[{"role": "user", "content": "[name] at [email]"}]]


def mocked(sent: list, finish_reason: str = "stop") -> LLM:
    """A real LLM whose one endpoint is a fake HTTP server: it records each
    request body in `sent` and ends each structured reply with
    `finish_reason`."""

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        content = '{"title": "T", "bullets": []}'
        if body.get("stream"):
            chunk = {"choices": [{"index": 0, "delta": {"content": "hi"}}]}
            text = f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n"
            return httpx.Response(
                200, text=text, headers={"content-type": "text/event-stream"}
            )
        message = {"role": "assistant", "content": content}
        choice = {"index": 0, "message": message, "finish_reason": finish_reason}
        # Reasoning counted in the total only, as Gemini's endpoint does.
        usage = {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 12}
        return httpx.Response(
            200,
            json={
                "id": "1",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [choice],
                "usage": usage,
            },
        )

    model = LLM([Endpoint("http://only.test/v1", "m")])
    model._endpoints = [
        (
            endpoint,
            AsyncOpenAI(
                base_url=endpoint.base_url,
                api_key="k",
                http_client=httpx.AsyncClient(transport=httpx.MockTransport(answer)),
            ),
        )
        for endpoint, _ in model._endpoints
    ]
    return model


def test_requests_carry_a_json_schema_and_never_tool_choice():
    sent = []
    model = mocked(sent)
    assert ask_json(model).title == "T"
    assert reply(collect(model, "hello")) == "hi"

    structured, streamed = sent
    assert structured["response_format"]["type"] == "json_schema"
    assert structured["response_format"]["json_schema"]["schema"] == (
        Entry.model_json_schema()
    )
    assert "tool_choice" not in structured and "tool_choice" not in streamed
    # No cap asked for, none sent: not every caller wants one.
    assert "max_tokens" not in structured


def test_a_reply_cap_is_sent_and_a_reply_stopped_at_it_is_cut_off():
    sent = []
    messages = [{"role": "user", "content": "draft it"}]
    with pytest.raises(llm_module.ReplyCutOff):
        asyncio.run(
            mocked(sent, finish_reason="length").complete_json(
                messages, Entry, identity=Identity(), max_tokens=500
            )
        )
    assert sent[0]["max_tokens"] == 500


# --- a schema as data (the Model route, KAN-723) ----------------------------------

CHOICE = {
    "type": "object",
    "properties": {"choice": {"type": ["integer", "null"]}},
    "required": ["choice"],
}


def ask_schema(llm: LLM, content: str = "pick one", schema=CHOICE, identity=Identity()):
    messages = [{"role": "user", "content": content}]
    return asyncio.run(llm.complete_schema(messages, schema, identity=identity))


@pytest.mark.parametrize("bad", ['{"choice": "two"}', "Sure! {"])
def test_an_answer_outside_the_schema_moves_down_the_chain_and_still_costs(bad):
    answer, spent = ask_schema(ScriptedLLM([bad], ['{"choice": 1}']))
    assert answer == {"choice": 1}
    assert spent.output_tokens == len(bad) + len('{"choice": 1}')


def test_an_answer_that_fits_no_endpoint_is_rejected_with_what_it_cost():
    with pytest.raises(llm_module.InvalidReply) as raised:
        ask_schema(ScriptedLLM(["{}"], ["[]"]))
    assert raised.value.spent.output_tokens == 4


def test_a_schema_call_moves_on_at_a_429_or_a_400_and_stops_at_a_wrong_key():
    assert ask_schema(ScriptedLLM(rate_limited(), ['{"choice": null}']))[0] == {"choice": None}
    # A 400 refuses the request (its schema, or Groq's json_validate_failed).
    assert ask_schema(ScriptedLLM(bad_request(), ['{"choice": 1}']))[0] == {"choice": 1}
    with pytest.raises(llm_module.InvalidReply):
        ask_schema(ScriptedLLM(bad_request(), bad_request()))
    wrong_key = AuthenticationError("bad key", response=httpx.Response(401, request=_REQUEST), body=None)
    with pytest.raises(llm_module.ScoutUnavailable) as raised:
        ask_schema(ScriptedLLM(wrong_key, ['{"choice": 1}']))
    assert not isinstance(raised.value, llm_module.InvalidReply)


def test_an_answer_nested_too_deep_to_read_moves_down_the_chain():
    deep = "[" * 20_000 + "]" * 20_000
    assert ask_schema(ScriptedLLM([deep], ['{"choice": 1}']))[0] == {"choice": 1}


def test_a_failure_log_never_holds_the_providers_error_body(caplog):
    body = {"code": "json_validate_failed", "failed_generation": "Dear team, I am Sam Seeker"}
    # The SDK's own text for it: the status and the whole body.
    refused = BadRequestError(f"Error code: 400 - {body}", response=httpx.Response(400, request=_REQUEST), body=body)
    ask_schema(ScriptedLLM(refused, ['{"choice": 1}']))
    assert "HTTP 400 json_validate_failed" in caplog.text
    assert "Sam Seeker" not in caplog.text


def test_a_schema_call_sends_no_identity_data_and_puts_it_back_in_the_answer():
    fake = ScriptedLLM(['{"note": "[name], at [email]"}'])
    note = {"type": "object", "properties": {"note": {"type": "string", "maxLength": 30}}}
    answer, _ = ask_schema(fake, "Sam Seeker at sam@example.com", note, identity=Identity(name="Sam Seeker"))
    assert fake.prompts == [[{"role": "user", "content": "[name] at [email]"}]]
    assert answer == {"note": "Sam Seeker, at sam@example.com"}


def test_a_schema_call_checks_the_answer_with_the_values_back_in():
    # "[email]" fits maxLength 10; the address it stands for does not.
    short = {"type": "object", "properties": {"to": {"type": "string", "maxLength": 10}}}
    with pytest.raises(llm_module.InvalidReply):
        ask_schema(ScriptedLLM(['{"to": "[email]"}']), "mail sam.seeker@example.com", short)


def test_a_schema_call_never_fetches_a_remote_ref(monkeypatch):
    def fetched(*args, **kwargs):
        raise AssertionError("fetched a $ref")

    monkeypatch.setattr("urllib.request.urlopen", fetched)
    remote = {"type": "object", "properties": {"x": {"$ref": "http://169.254.169.254/x"}}}
    with pytest.raises(Unresolvable):
        ask_schema(ScriptedLLM(['{"x": 1}']), schema=remote)


def test_a_schema_call_sends_the_schema_as_given_and_reads_the_tokens():
    sent = []
    schema = {"type": "object", "required": ["title"]}
    answer, spent = ask_schema(mocked(sent), schema=schema)
    assert answer == {"title": "T", "bullets": []}
    assert sent[0]["response_format"]["json_schema"] == {"name": "answer", "schema": schema}
    assert spent == Spent(7, 5)


# --- configuration ----------------------------------------------------------------


def test_one_endpoint_unless_a_chain_is_configured():
    assert len(LLM.from_settings(ScoutSettings(_env_file=None))._endpoints) == 1


def test_the_chain_comes_from_env_in_order(monkeypatch):
    monkeypatch.setenv(
        "SCOUT_ENDPOINTS",
        '[{"base_url": "http://groq/v1", "model": "gpt-oss-120b", "api_key": "k"},'
        ' {"base_url": "http://cf/v1", "model": "gpt-oss-20b",'
        ' "reasoning_effort": "low"}]',
    )
    endpoints = [
        e for e, _ in LLM.from_settings(ScoutSettings(_env_file=None))._endpoints
    ]
    assert [(e.model, e.api_key, e.reasoning_effort) for e in endpoints] == [
        ("gpt-oss-120b", "k", None),
        ("gpt-oss-20b", None, "low"),
    ]


_GROQ_120B = '{"base_url": "http://groq/v1", "model": "gpt-oss-120b", "api_key": "g"}'
_GROQ_20B = '{"base_url": "http://groq/v1", "model": "gpt-oss-20b", "api_key": "g"}'
_GEMINI = '{"base_url": "http://gemini/v1", "model": "flash-lite", "api_key": "k"}'


def _models(size=None) -> list[str]:
    return [e.model for e in ScoutSettings(_env_file=None).chain(size)]


def test_a_size_chain_ends_with_the_default_chain(monkeypatch):
    monkeypatch.setenv("SCOUT_ENDPOINTS", f"[{_GEMINI}]")
    monkeypatch.setenv("SCOUT_ENDPOINTS_LARGE", f"[{_GROQ_120B}]")
    monkeypatch.setenv("SCOUT_ENDPOINTS_SMALL", f"[{_GROQ_20B}]")
    assert _models("large") == ["gpt-oss-120b", "flash-lite"]
    assert _models("small") == ["gpt-oss-20b", "flash-lite"]
    assert _models() == ["flash-lite"]


def test_an_unset_size_is_the_default_chain(monkeypatch):
    for name in ("SCOUT_ENDPOINTS", "SCOUT_ENDPOINTS_LARGE", "SCOUT_ENDPOINTS_SMALL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SCOUT_MODEL", "qwen3.5:9b")
    assert _models("large") == _models("small") == _models() == ["qwen3.5:9b"]


def test_an_endpoint_in_both_chains_is_tried_once(monkeypatch):
    monkeypatch.setenv("SCOUT_ENDPOINTS", f"[{_GEMINI}, {_GROQ_20B}]")
    monkeypatch.setenv("SCOUT_ENDPOINTS_SMALL", f"[{_GROQ_20B}]")
    assert _models("small") == ["gpt-oss-20b", "flash-lite"]


def test_settings_read_the_scout_prefix(monkeypatch):
    monkeypatch.setenv("SCOUT_MODEL", "qwen3.5:9b")
    s = ScoutSettings(_env_file=None)
    assert s.model == "qwen3.5:9b"


# --- what Scout is allowed to know -------------------------------------------------


def _entry(section, title, **fields):
    return {"section": section, "title": title, "bullets": [], **fields}


def test_bank_facts_carry_every_section_and_the_original_bullets():
    bank = {
        "skills": [{"name": "Python", "group": "Languages"}],
        "entries": [
            _entry(
                "education", "Stony Brook University", degree="BS", field_of_study="CS",
                gpa=3.7, start_month="2023-09", end_month="2027-05", end_kind="expected",
                coursework=["Algorithms"], location="Stony Brook, NY",
            ),
            _entry(
                "experience", "Robotics Intern", organization="Acme", start_month="2025-06",
                end_kind="present", location="Austin, TX",
                bullets=[{"id": "b1", "position": 0, "text": "Wrote   ROS nodes\nfor arms."},
                         {"id": "b2", "position": 1, "text": "Cut latency 40%."}],
            ),
            _entry("projects", "WorkIt", link="https://github.com/x/y",
                   bullets=[{"id": "b3", "position": 0, "text": "Job board."}]),
            _entry("leadership", "President", organization="Robotics Club",
                   start_month="2024-09", end_month="2025-05", end_kind="month"),
            _entry("awards", "Dean's List", organization="Stony Brook", award_date="2024-12"),
            _entry("certifications", "AWS Cloud Practitioner", issuer="Amazon", end_month="2025-03"),
        ],
    }
    facts = bank_facts(bank, has_upload=True)
    assert facts.skills == ["Python"]
    assert facts.education == ["BS in CS at Stony Brook University (2023–expected 2027), GPA 3.7"]
    assert facts.experience == [
        "Robotics Intern at Acme (2025–present): Wrote ROS nodes for arms. Cut latency 40%."
    ]
    # A project's link is identity data: it never crosses.
    assert facts.projects == ["WorkIt: Job board."]
    assert facts.leadership == ["President at Robotics Club (2024–2025)"]
    assert facts.awards == ["Dean's List at Stony Brook (2024)"]
    assert facts.certifications == ["AWS Cloud Practitioner from Amazon (2025)"]
    assert "github.com" not in facts.model_dump_json()


def test_bank_facts_ignore_which_resumes_hold_an_entry():
    # GET /bank's KAN-343 fields: resume names are the student's file names,
    # and they never become facts.
    bank = {
        "entries": [_entry("projects", "WorkIt", resume_ids=["r1"])],
        "skills": [{"name": "Python", "resume_ids": ["r1"]}],
        "resumes": [{"id": "r1", "kind": "uploaded", "name": "jane-doe-resume.pdf", "primary": True}],
    }
    facts = bank_facts(bank, has_upload=True)
    assert (facts.projects, facts.skills) == (["WorkIt"], ["Python"])
    assert "jane-doe" not in facts.model_dump_json()


def test_a_long_entry_is_one_short_line():
    bullets = [{"id": str(i), "position": i, "text": "Shipped a feature " * 10} for i in range(5)]
    facts = bank_facts({"entries": [_entry("projects", "Big", bullets=bullets)], "skills": []}, has_upload=False)
    (line,) = facts.projects
    assert len(line) <= 302 and line.endswith("…")


def test_job_facts_use_readable_labels():
    row = {
        "title": "Robot Software Intern",
        "company": "Rhoda AI",
        "apply_url": "https://jobs.example/1",
        "experience_level": "new_grad",
        "work_style": "onsite",
        "location": None,
        "description": "D",
    }
    facts = job_facts(row)
    assert (facts.experience_level, facts.work_style, facts.description) == (
        "New grad",
        "On site",
        "D",
    )


def test_a_student_job_reads_as_an_internship():
    # KAN-233: every internship is a student job; the job's facts carry no job
    # type, so the level says it.
    row = {"title": "SWE Intern", "company": "Acme", "experience_level": "student"}
    assert job_facts(row).experience_level == "Student (internship)"
