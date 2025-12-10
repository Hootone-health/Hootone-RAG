"""
Quick example of calling the self-hosted ai/embeddinggemma model via the
OpenAI Python client. This assumes you are running the Docker Model Runner
locally and exposing an OpenAI-compatible endpoint (default: http://localhost:8000/v1).
"""

from __future__ import annotations

import os
from typing import Iterable, List

from openai import OpenAI


# Point to your local Model Runner endpoint; override with MODEL_RUNNER_BASE_URL.
MODEL_RUNNER_BASE_URL = os.getenv("MODEL_RUNNER_BASE_URL", "http://localhost:12434/engines/v1")

# Dummy API key is acceptable for the local runner; override via OPENAI_API_KEY if needed.
API_KEY = os.getenv("OPENAI_API_KEY", "docker")

# Model name exposed by the Docker Model Runner for embeddings.
EMBED_MODEL_NAME = "ai/embeddinggemma"


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    """
    Create embeddings for a collection of texts using ai/embeddinggemma.

    Returns a list of embedding vectors (one per input string).
    """
    client = OpenAI(base_url=MODEL_RUNNER_BASE_URL, api_key=API_KEY)
    response = client.embeddings.create(model=EMBED_MODEL_NAME, input=list(texts))
    return [item.embedding for item in response.data]


if __name__ == "__main__":
    sample_inputs = [
        "A quick fox jumps over a lazy dog.",
        "Self-hosted embeddings are handy for offline scenarios.",
    ]

    embeddings = embed_texts(sample_inputs)

    # Print a short preview of each embedding vector for sanity checking.
    for text, vector in zip(sample_inputs, embeddings):
        preview = ", ".join(f"{v:.4f}" for v in vector[:5])
        print(f"text: {text!r}")
        print(f"dim: {len(vector)}, head: [{preview}, ...]")
        print("-" * 40)

