"""Embedding generation using sentence-transformers."""

import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from qa.kb.config import get_kb_config

logger = logging.getLogger(__name__)

_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or create the embedding model.

    Returns:
        SentenceTransformer model
    """
    global _model
    if _model is None:
        config = get_kb_config()
        logger.info(f"Loading embedding model: {config.embedding_model}")
        _model = SentenceTransformer(config.embedding_model)
        logger.info("Embedding model loaded")
    return _model


def get_embedding(text: str) -> list[float]:
    """Generate embedding for a text.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return embeddings.tolist()


def get_embedding_dimension() -> int:
    """Get the dimension of the embedding vector.

    Returns:
        Embedding dimension
    """
    model = get_embedding_model()
    return model.get_sentence_embedding_dimension()
