"""Скачивает и кэширует модели для эмбеддингов при сборке Docker."""

import os

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "deepvk/USER-bge-m3"


def main() -> None:
    """Скачивает модель эмбеддингов в локальный кэш HuggingFace."""
    hf_token = os.getenv("HF_TOKEN")
    print(f"Downloading embedding model: {EMBEDDING_MODEL}")
    print(f"Using HuggingFace token: {'yes' if hf_token else 'no (anonymous)'}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"Model downloaded: {EMBEDDING_MODEL}")
    print(f"Embedding dimension: {model.get_sentence_embedding_dimension()}")


if __name__ == "__main__":
    main()
