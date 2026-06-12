"""
RAG (Retrieval-Augmented Generation) for per-tenant knowledge bases.

Ingest time: chunk text → embed with OpenAI → store in kb_chunks (pgvector)
Query time : embed caller utterance → cosine search → return top-k chunks
"""
from __future__ import annotations

import openai

from src.config import settings
from src.db import db
from src.utils.logger import logger
from src.utils.text import split_text  # noqa: F401  re-exported for convenience

_openai: openai.AsyncOpenAI | None = None


def _client() -> openai.AsyncOpenAI:
    global _openai
    if _openai is None:
        _openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai


async def embed(text: str) -> list[float]:
    """Embed text with OpenAI text-embedding-3-small (1536 dims)."""
    response = await _client().embeddings.create(
        input=text[:8000],
        model="text-embedding-3-small",
    )
    return response.data[0].embedding


async def search_kb(tenant_id: str, query: str, k: int = 5) -> list[str]:
    """
    Find the k most relevant KB chunks for this tenant.
    Returns empty list if no OpenAI key is configured or KB is empty.
    """
    if not settings.openai_api_key:
        return []

    try:
        embedding = await embed(query)
        result = await db.rpc("match_kb_chunks", {
            "query_embedding": embedding,
            "tenant": tenant_id,
            "match_count": k,
        }).execute()
        return [row["content"] for row in (result.data or [])]
    except Exception as e:
        logger.error("RAG search failed", error=str(e))
        return []


async def ingest_chunk(tenant_id: str, content: str, metadata: dict | None = None) -> str:
    """Embed and store one text chunk. Returns the new chunk ID."""
    embedding = await embed(content)
    result = await db.table("kb_chunks").insert({
        "tenant_id": tenant_id,
        "content": content,
        "embedding": embedding,
        "metadata": metadata or {},
    }).execute()
    return result.data[0]["id"]
