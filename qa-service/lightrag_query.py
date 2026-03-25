"""Скрипт для запуска LightRAG запроса в отдельном процессе."""

import json
import sys
import asyncio


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python script.py <question> <working_dir>"}))
        sys.exit(1)

    question = sys.argv[1]
    working_dir = sys.argv[2]

    import os

    os.makedirs(working_dir, exist_ok=True)

    from lightrag import LightRAG, QueryParam
    from lightrag.utils import EmbeddingFunc
    import numpy as np

    async def embedding_func(texts):
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("deepvk/USER-bge-m3")
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings

    async def llm_model_func(prompt, system_prompt=None, **kwargs):
        return "LightRAG response"

    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=512,
            func=embedding_func,
        ),
        graph_storage="NetworkXStorage",
    )

    try:
        result = asyncio.run(rag.aquery(question, param=QueryParam(mode="mix")))
        print(json.dumps({"result": result}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    main()
