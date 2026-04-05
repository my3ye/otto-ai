import logging
import time
from pathlib import Path

import numpy as np
from openai import AsyncOpenAI

from .config import settings

_client: AsyncOpenAI | None = None
logger = logging.getLogger(__name__)


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


# ── SVC: Singular Value Calibration ──────────────────────────────────────────
# Implements anisotropy reduction for embedding vectors.
# Reference: "All-but-the-Top" (Mu & Viswanath, 2018) + SVC from sweep #13.
#
# Algorithm:
#   1. Compute mean vector + top-k PCA directions from stored embeddings corpus
#   2. At query time: remove mean bias + project out top-k principal components
#   3. Re-normalize the result
#
# Components are fitted offline via POST /memory/svc/fit and saved to .npz file.
# Reloaded at most every hour from disk.

_SVC_CACHE: dict = {"mean": None, "components": None, "ts": 0.0}
_SVC_CACHE_TTL_S = 3600.0  # reload from disk at most hourly


def _load_svc_components() -> tuple[np.ndarray, np.ndarray] | None:
    """Load SVC components from disk into in-memory cache.

    Returns (mean_vector, principal_components) or None if unavailable.
    mean_vector shape: (1536,)
    principal_components shape: (top_k, 1536) — each row is a unit principal direction
    """
    global _SVC_CACHE
    now = time.monotonic()

    # Serve from in-memory cache if fresh
    if (
        _SVC_CACHE["mean"] is not None
        and _SVC_CACHE["components"] is not None
        and (now - _SVC_CACHE["ts"]) < _SVC_CACHE_TTL_S
    ):
        return _SVC_CACHE["mean"], _SVC_CACHE["components"]

    path = Path(settings.svc_components_path)
    if not path.exists():
        return None

    try:
        data = np.load(str(path))
        mean = data["mean"].astype(np.float32)
        components = data["components"].astype(np.float32)
        _SVC_CACHE = {"mean": mean, "components": components, "ts": now}
        logger.info(f"SVC: loaded components from {path} (top_k={len(components)}, dim={mean.shape[0]})")
        return mean, components
    except Exception as e:
        logger.warning(f"SVC: failed to load components from {path}: {e}")
        return None


def invalidate_svc_cache() -> None:
    """Force reload of SVC components on next call (used after /svc/fit)."""
    global _SVC_CACHE
    _SVC_CACHE = {"mean": None, "components": None, "ts": 0.0}


def apply_svc(embedding: list[float]) -> list[float]:
    """Apply Singular Value Calibration to a raw embedding vector.

    Removes the mean bias direction and top-k principal components to reduce
    anisotropy (the cone problem where embeddings cluster in a narrow region).

    Steps:
      1. v = embedding - mean_vector         (remove corpus mean)
      2. v = v - sum_k (v · pc_k) * pc_k    (remove top-k principal directions)
      3. v = v / ||v||                        (re-normalize to unit sphere)

    If components are not available (not fitted yet), returns original embedding.
    If settings.svc_enabled is False, returns original embedding unchanged.
    """
    if not settings.svc_enabled:
        return embedding

    components_data = _load_svc_components()
    if components_data is None:
        return embedding

    mean_vec, principal_components = components_data
    top_k = min(settings.svc_top_k, len(principal_components))

    # Convert to float32 numpy array
    v = np.array(embedding, dtype=np.float32)

    # Step 1: Remove corpus mean (shifts embedding space to zero-mean)
    v = v - mean_vec

    # Step 2: Remove projection onto top-k principal directions
    # These directions capture systematic frequency/style biases, not semantic content
    for i in range(top_k):
        pc = principal_components[i]
        v = v - np.dot(v, pc) * pc

    # Step 3: Re-normalize to unit sphere
    norm = np.linalg.norm(v)
    if norm < 1e-8:
        logger.warning("SVC: degenerate vector after calibration, returning original")
        return embedding

    return (v / norm).tolist()


async def get_embedding(text: str) -> list[float]:
    # Optional OTel span around the OpenAI API call
    _tracer = None
    try:
        from opentelemetry import trace
        _tracer = trace.get_tracer("otto.embeddings")
    except ImportError:
        pass

    client = _get_client()

    if _tracer:
        with _tracer.start_as_current_span(
            "embeddings.openai",
            attributes={
                "embedding.model": "text-embedding-3-small",
                "embedding.input_length": len(text),
            },
        ):
            resp = await client.embeddings.create(
                input=text,
                model="text-embedding-3-small",
            )
    else:
        resp = await client.embeddings.create(
            input=text,
            model="text-embedding-3-small",
        )

    embedding = resp.data[0].embedding
    return apply_svc(embedding)
