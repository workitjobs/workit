"""
A stand-in for the model, for Scout's own tests and the API's.

Lives in the package rather than in either test folder so both can use the
same one: the API's route tests need a model as much as Scout's do.
"""

from collections.abc import AsyncIterator, Sequence

from workit_scout.llm import LLM, Message, Spent
from workit_scout.settings import Endpoint

Script = list[str | Exception] | Exception


def endpoint(n: int) -> Endpoint:
    """The nth fake endpoint in a ScriptedLLM's chain, counting from 0."""
    return Endpoint(f"http://endpoint{n}.test/v1", f"model-{n}")


class ScriptedLLM(LLM):
    """
    One script for each endpoint in the chain, in order. Each endpoint yields
    its scripted pieces of reply in order, raising any exception it reaches —
    so a script can fail before a reply or halfway through one. An endpoint
    is asked again after a 5xx as a real one is, with no pause, so its script
    runs again and fails the same way.
    """

    BUSY_PAUSES = (0.0, 0.0)

    def __init__(self, *scripts: Script):
        super().__init__([endpoint(n) for n in range(len(scripts))])
        self._scripts = {endpoint(n): script for n, script in enumerate(scripts)}
        #: Every prompt sent, in order, as the model would have received it.
        self.prompts: list[list[Message]] = []
        #: The reply cap each structured call asked for, in order.
        self.max_tokens: list[int | None] = []

    @property
    def system_prompt(self) -> str:
        return self.prompts[0][0]["content"]

    async def _complete(
        self, client, endpoint: Endpoint, messages: Sequence[Message]
    ) -> AsyncIterator[str]:
        self.prompts.append(list(messages))
        script = self._scripts[endpoint]
        for item in script if isinstance(script, list) else [script]:
            if isinstance(item, Exception):
                raise item
            yield item

    async def _complete_schema(
        self, client, endpoint, messages, name, schema, max_tokens=None
    ) -> tuple[str, Spent]:
        # A structured reply is the script's pieces joined, as one answer. It
        # costs a token a character: the prompt's read, the reply's written.
        self.max_tokens.append(max_tokens)
        text = "".join(
            [piece async for piece in self._complete(client, endpoint, messages)]
        )
        return text, Spent(sum(len(m["content"]) for m in messages), len(text))
