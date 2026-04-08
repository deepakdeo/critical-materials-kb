"""Embedding generation via OpenAI text-embedding-3-small with batching and retry."""

import logging
import time

from openai import OpenAI, RateLimitError

from src.config import settings
from src.ingest.chunker import Chunk

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 100
MAX_RETRIES = 5
BASE_DELAY = 1.0


def _get_client() -> OpenAI:
    """Create an OpenAI client using the configured API key."""
    return OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str], client: OpenAI | None = None) -> list[list[float]]:
    """Generate embeddings for a list of texts with batching and exponential backoff.

    Args:
        texts: List of text strings to embed.
        client: Optional OpenAI client instance (created if not provided).

    Returns:
        List of embedding vectors, one per input text.

    Raises:
        RuntimeError: If all retries are exhausted due to rate limits.
    """
    if not texts:
        return []

    if client is None:
        client = _get_client()

    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), MAX_BATCH_SIZE):
        batch = texts[batch_start : batch_start + MAX_BATCH_SIZE]

        for attempt in range(MAX_RETRIES):
            try:
                response = client.embeddings.create(
                    input=batch,
                    model=settings.embedding_model,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                logger.debug(
                    "Embedded batch %d-%d (%d texts)",
                    batch_start,
                    batch_start + len(batch),
                    len(batch),
                )
                break
            except RateLimitError as e:
                delay = BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limit hit (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                    e,
                )
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"Embedding failed after {MAX_RETRIES} retries due to rate limits"
                    ) from e
                time.sleep(delay)

    return all_embeddings


def embed_chunks(chunks: list[Chunk], client: OpenAI | None = None) -> list[Chunk]:
    """Generate embeddings for a list of Chunk models.

    Embeds the text of each chunk and attaches the embedding vector to the chunk.

    Args:
        chunks: List of Chunk models to embed.
        client: Optional OpenAI client instance.

    Returns:
        The same list of Chunk models, now with embeddings attached.
    """
    if not chunks:
        return chunks

    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts, client=client)

    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding

    logger.info("Embedded %d chunks (dim=%d)", len(chunks), len(embeddings[0]) if embeddings else 0)
    return chunks
