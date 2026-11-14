"""
Embeddings: experience banks and job postings as vectors, so they can be
compared by meaning in any field. What a bank is embedded from is
`bank_input.bank_text`.
"""

import logging
import math
from collections.abc import Sequence

import httpx  # general Python library for sending HTTP requests

from app.config import get_settings
from app.models.dto import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

# Every writer that shares a database must use one provider and model:
# vectors from different models can't be compared, even at equal
# dimensions. Production's is Ollama's Qwen3 embedding model on the team
# computer (KAN-726, ollama_embedding_model); model_key() names the space a
# vector came from. Changing the model or DIMENSIONS means clearing and
# re-embedding every job and bank. Gemini's model stays callable by name.
MODEL = "gemini-embedding-001"

DIMENSIONS = EMBEDDING_DIMENSIONS

BATCH_SIZE = 100
_MAX_CHARS = 6000   # NOTE: MAX CHARACTER ON EMBED. Need to consider increasing as EXP BANK GROWS
_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchEmbedContents"


# The headings the scraper stores a description under (KAN-229,
# scraper/workit_scraper/sections.py `KEPT`), each alone on its line. Part of
# the feed's contract: renamed on one side only, every posting embeds its
# whole description again. Matching reads the role and what it asks for; the
# pay and the details are left out, and so is the intro unless the posting has
# no Overview: then the intro is where it states the role (19 of the scraper's
# 50 gold postings keep role or requirement lines there). The extras the
# scraper keeps after them (Benefits, How to Apply, About the Company,
# `sections.EXTRA`) are for the job posting's page: matching, the keywords and
# Tailor never read them (`job_part`).
_MATCHED_HEADINGS = frozenset(
    {"Overview", "Responsibilities", "Requirements", "Preferred Qualifications"}
)
_OTHER_HEADINGS = frozenset({"Pay", "Details", "Benefits", "How to Apply", "About the Company"})


def _matched_part(description: str, *, keep_headings: bool = False) -> str | None:
    '''the text under the matched headings, after the intro when there is no
    Overview, or None when no line is a matched heading. A description stored
    before KAN-229 that uses one of those words as a heading of its own is read
    from there; the scraper's own whole-text fallback never has one'''
    intro: list[str] = []
    lines: list[str] = []
    seen = reading = False
    has_content = False
    for line in description.split("\n"):
        if line in _MATCHED_HEADINGS or line in _OTHER_HEADINGS:
            seen, reading = True, line in _MATCHED_HEADINGS
            if reading and keep_headings:
                lines.append(line)
        elif not seen:
            intro.append(line)
        elif reading:
            lines.append(line)
            has_content |= bool(line.strip())
    if not has_content:
        # Only the intro under none of them, then Pay or an extra: the intro is
        # the job, and the perks after it must not stand in for it.
        return ("\n".join(intro).strip() or None) if seen else None
    if "Overview" not in description.split("\n"):
        lines = intro + lines
    return "\n".join(lines).strip()


def job_part(description: str | None, *, keep_headings: bool = False) -> str:
    """What a posting says about the job itself (`_matched_part`), or its whole
    description when it was stored with none of the fixed headings. What the
    embedding, the keywords and Tailor read, so a perks list or the company's
    pitch never steers them. Model prompts keep headings to distinguish required
    from preferred qualifications; embeddings can omit them."""
    if not description:
        return ""
    return _matched_part(description, keep_headings=keep_headings) or description


def job_text(title: str, description: str | None) -> str:
    '''what a posting is embedded from: its title, then its role (its intro
    when it has no Overview), responsibilities, requirements and preferred
    qualifications, or its whole description when it has none of them'''
    return f"{title}\n\n{job_part(description)}".strip()


def model_key() -> str:
    """Identity stored with vectors; equal dimensions alone do not imply compatibility."""
    settings = get_settings()
    model = MODEL if settings.embedding_provider == "gemini" else settings.ollama_embedding_model
    return f"{settings.embedding_provider}:{model}:{DIMENSIONS}"


async def embed(
    texts: Sequence[str], *, timeout: float | None = None, query: bool = False
) -> list[list[float]] | None:
    """One vector per text, or None on provider failure; never fall back to another model.

    Empty input returns []; oversized batches are caller errors. Both providers
    must return finite, 768-dimensional vectors before anything can be stored.
    `timeout` overrides `embedding_timeout_seconds` (120s, sized for the
    import's batches): a call inside a user's request passes a short one, so
    a provider that is down or absent costs seconds, not the whole request.
    `query` marks the texts as banks, the asking side: Ollama gets
    `ollama_embedding_query_prefix` before each. Postings are never queries.
    An Ollama vector longer than DIMENSIONS keeps its first DIMENSIONS values,
    scaled back to length 1 (`_shortened`).
    """
    if len(texts) > BATCH_SIZE:
        raise ValueError(f"embed() takes at most {BATCH_SIZE} texts at a time")
    if not texts:
        return []
    settings = get_settings()
    provider = settings.embedding_provider
    if provider == "none":
        return None
    headers = {}
    if provider == "gemini":
        if not settings.gemini_api_key:
            return None
        url = _URL
        headers = {"x-goog-api-key": settings.gemini_api_key}
        body = {
            "requests": [
                {
                    "model": f"models/{MODEL}",
                    "content": {"parts": [{"text": text[:_MAX_CHARS]}]},
                    "taskType": "SEMANTIC_SIMILARITY",
                    "outputDimensionality": DIMENSIONS,
                }
                for text in texts
            ]
        }
    else:
        url = settings.ollama_embedding_url.rstrip("/") + "/api/embed"
        body = {
            "model": settings.ollama_embedding_model,
            "input": [_as_query(text, settings.ollama_embedding_query_prefix, query) for text in texts],
            "truncate": True,
        }
    try:
        async with httpx.AsyncClient(
            timeout=timeout if timeout is not None else settings.embedding_timeout_seconds
        ) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("%s embedding failed: HTTP %s", provider, exc.response.status_code)
        return None
    except httpx.HTTPError as exc:
        logger.warning("%s embedding failed: %s", provider, exc)
        return None
    try:
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("response must be an object")
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise ValueError("expected one embedding per input text")
        vectors = []
        for embedding in embeddings:
            if provider == "gemini":
                values = embedding.get("values") if isinstance(embedding, dict) else None
            else:
                values = embedding
            # Gemini is asked for DIMENSIONS exactly; an Ollama model answers
            # its own size, which may be longer (Qwen3's 4B: 2560).
            too_short = len(values) < DIMENSIONS if isinstance(values, list) else True
            if too_short or (provider == "gemini" and len(values) != DIMENSIONS):
                raise ValueError(f"expected {DIMENSIONS} values per embedding")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in values
            ):
                raise ValueError("embedding values must be finite numbers")
            vector = [float(value) for value in values]
            vectors.append(_shortened(vector) if len(vector) > DIMENSIONS else vector)
        return vectors
    except (TypeError, ValueError, OverflowError) as exc:
        logger.warning("%s embedding returned an invalid response: %s", provider, exc)
        return None


def _as_query(text: str, prefix: str, query: bool) -> str:
    """A bank's text with the model's task line before it; a posting's as it is.
    The cut leaves room for the prefix, so the bank's own text loses no more."""
    text = text[:_MAX_CHARS]
    return f"{prefix}{text}" if query and prefix else text


def _shortened(vector: list[float]) -> list[float]:
    """The first DIMENSIONS values, scaled to length 1. Qwen3's embedding
    models are trained so a vector's first part stands on its own (Matryoshka
    training), so the cut keeps the columns at vector(768) with no migration.
    The scale changes no cosine distance; it keeps the stored vectors alike."""
    head = vector[:DIMENSIONS]
    norm = math.sqrt(sum(value * value for value in head))
    if norm == 0:
        raise ValueError("embedding is all zeros")
    return [value / norm for value in head]
