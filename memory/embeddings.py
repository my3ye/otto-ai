import contextvars
import logging
import time
from pathlib import Path

import numpy as np
from openai import AsyncOpenAI

from .config import settings

_client: AsyncOpenAI | None = None
logger = logging.getLogger(__name__)

# ── Provider tracking (async-safe via contextvars) ─────────────────────────
# After calling get_embedding(), callers can check which provider was used
# to decide which DB column to store in / search against.

_current_provider: contextvars.ContextVar[str] = contextvars.ContextVar(
    "embedding_provider", default="openai"
)


def get_embedding_provider() -> str:
    """Return the provider used by the last get_embedding() call in this async context."""
    return _current_provider.get()


def get_embedding_dim() -> int:
    """Return embedding dimension for current provider."""
    return 1536 if _current_provider.get() == "openai" else 384


def emb_col() -> str:
    """Return the DB column name for the current embedding provider.

    'embedding_hv' for OpenAI (halfvec 1536-dim),
    'embedding_local' for local model (halfvec 384-dim).
    """
    return "embedding_hv" if _current_provider.get() == "openai" else "embedding_local"


def emb_cast(param: str = "$1") -> str:
    """Return SQL cast expression for the current embedding provider.

    e.g. '$1::halfvec(1536)' for OpenAI, '$1::halfvec(384)' for local.
    """
    if _current_provider.get() == "openai":
        return f"{param}::halfvec(1536)"
    return f"{param}::halfvec(384)"


def emb_summary_col() -> str:
    """Return the summary embedding column for current provider."""
    return "summary_embedding_hv" if _current_provider.get() == "openai" else "summary_embedding_local"


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


# ── Local Model (lazy singleton) ──────────────────────────────────────────
_local_model = None
_local_model_lock = None  # initialized lazily


def _get_local_model():
    """Load sentence-transformer model on first use (lazy, ~80MB for MiniLM)."""
    global _local_model
    if _local_model is not None:
        return _local_model

    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local embedding model: {settings.local_embedding_model}")
        _local_model = SentenceTransformer(settings.local_embedding_model)
        logger.info(f"Local embedding model loaded: {settings.local_embedding_model} "
                     f"(dim={_local_model.get_embedding_dimension()})")
        return _local_model
    except Exception as e:
        logger.error(f"Failed to load local embedding model: {e}")
        raise


def _local_embed(text: str) -> list[float]:
    """Generate embedding using local sentence-transformer model.

    Returns 384-dim vector (for all-MiniLM-L6-v2).
    No SVC calibration — SVC is fitted to OpenAI's embedding space.
    """
    model = _get_local_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


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
# NOTE: SVC is only applied to OpenAI embeddings (fitted to that space).

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


_embedding_tracer = None
try:
    from opentelemetry import trace as _otel_trace
    _embedding_tracer = _otel_trace.get_tracer("otto.embeddings")
except ImportError:
    pass


async def _openai_embed(text: str) -> list[float]:
    """Generate embedding via OpenAI API. Raises on failure."""
    client = _get_client()

    if _embedding_tracer:
        with _embedding_tracer.start_as_current_span(
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

    return resp.data[0].embedding


async def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for text.

    Tries OpenAI first (1536-dim). On failure, falls back to local model (384-dim)
    if LOCAL_EMBEDDING_ENABLED is set. After calling this, use get_embedding_provider()
    to check which provider was used, and emb_col()/emb_cast() for SQL generation.

    SVC calibration is only applied to OpenAI embeddings.
    """
    # Try OpenAI first
    try:
        raw = await _openai_embed(text)
        _current_provider.set("openai")
        logger.debug("Embedding generated via OpenAI (1536-dim)")
        return apply_svc(raw)
    except Exception as openai_err:
        logger.warning(f"OpenAI embedding failed: {openai_err}")

    # Fallback to local model
    if settings.local_embedding_enabled:
        try:
            result = _local_embed(text)
            _current_provider.set("local")
            logger.info(f"Embedding generated via local model (384-dim, fallback)")
            return result
        except Exception as local_err:
            logger.error(f"Local embedding also failed: {local_err}")
            raise RuntimeError(
                f"All embedding providers failed. OpenAI: {openai_err}, Local: {local_err}"
            ) from local_err

    # Local not enabled and OpenAI failed
    raise RuntimeError(f"OpenAI embedding failed and local fallback is disabled: {openai_err}")
