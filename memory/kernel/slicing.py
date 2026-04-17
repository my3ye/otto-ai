"""Semantic Slicing — CID-based memory segmentation.

Reference: arXiv 2602.20934v1 §4.2 (Semantic Slicing)

Uses Contextual Information Density (CID) to detect semantic boundaries
in sequential memories. Groups memories between boundaries into slices.

CID metric: D(t) = 1 - cosine_similarity(embedding[t], rolling_mean[t-w:t])
Sharp gradient (D(t) - D(t-1) > threshold) = semantic boundary

Each slice gets:
- A centroid embedding (mean of member embeddings)
- A label (dominant category + key terms)
- Token count estimate
- Entry in semantic_page_table for L1/L2/L3 tracking
"""

import logging
import math
import numpy as np
from uuid import UUID

from ..db import get_pool
from ..embeddings import get_embedding

log = logging.getLogger("otto.kernel.slicing")

# CID parameters
CID_WINDOW = 10        # rolling mean window
CID_THRESHOLD = 0.15   # gradient threshold for boundary detection
MIN_SLICE_SIZE = 3     # minimum memories per slice
MAX_SLICE_SIZE = 30    # maximum memories per slice


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm < 1e-10:
        return 0.0
    return float(dot / norm)


def _compute_cid(embeddings: list[list[float]], window: int = CID_WINDOW) -> list[float]:
    """Compute CID metric for a sequence of embeddings.

    D(t) = 1 - cosine_sim(embedding[t], rolling_mean[t-w:t])
    """
    n = len(embeddings)
    if n < 2:
        return [0.0] * n

    cid_values = [0.0]  # first element has no prior context
    dim = len(embeddings[0])

    for t in range(1, n):
        # Rolling mean of previous w embeddings
        start = max(0, t - window)
        window_embeds = embeddings[start:t]
        mean = np.mean(window_embeds, axis=0)
        sim = _cosine_sim(embeddings[t], mean.tolist())
        cid_values.append(1.0 - sim)

    return cid_values


def _detect_boundaries(cid_values: list[float], threshold: float = CID_THRESHOLD) -> list[int]:
    """Detect semantic boundaries where CID gradient exceeds threshold.

    Returns list of indices where boundaries occur.
    """
    boundaries = []
    for t in range(1, len(cid_values)):
        gradient = cid_values[t] - cid_values[t - 1]
        if gradient > threshold:
            boundaries.append(t)
    return boundaries


def _segment_by_boundaries(
    n: int,
    boundaries: list[int],
    min_size: int = MIN_SLICE_SIZE,
    max_size: int = MAX_SLICE_SIZE,
) -> list[tuple[int, int]]:
    """Split index range [0, n) at boundary points into segments.

    Returns list of (start, end) tuples.
    Merges small segments and splits large ones.
    """
    if not boundaries:
        # No boundaries: one big segment (may get split by max_size)
        segments = [(0, n)]
    else:
        segments = []
        prev = 0
        for b in boundaries:
            if b > prev:
                segments.append((prev, b))
            prev = b
        if prev < n:
            segments.append((prev, n))

    # Merge segments that are too small
    merged = []
    for seg in segments:
        if merged and (seg[1] - seg[0]) < min_size:
            # Merge with previous
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(seg)

    # Split segments that are too large
    final = []
    for start, end in merged:
        size = end - start
        if size <= max_size:
            final.append((start, end))
        else:
            # Split into chunks of max_size
            for i in range(start, end, max_size):
                final.append((i, min(i + max_size, end)))

    return final


def _label_slice(memories: list[dict]) -> str:
    """Generate a label for a slice based on dominant category + key terms."""
    if not memories:
        return "empty"

    # Dominant category
    cats = {}
    for m in memories:
        c = m.get("category", "general")
        cats[c] = cats.get(c, 0) + 1
    dom_cat = max(cats, key=cats.get)

    # Key terms: first few significant words from content
    words = []
    for m in memories[:3]:
        content = m.get("content", "")[:100]
        words.extend(w for w in content.split()[:5] if len(w) > 3)

    key_terms = " ".join(words[:4]) if words else ""
    label = f"{dom_cat}: {key_terms}" if key_terms else dom_cat

    return label[:200]


def _estimate_tokens(memories: list[dict]) -> int:
    """Estimate total tokens for a set of memories."""
    total_chars = sum(len(m.get("content", "")) for m in memories)
    return total_chars // 4


async def rebuild_all_slices() -> dict:
    """Rebuild all semantic slices from current semantic_memories.

    Steps:
    1. Load all active memories with embeddings
    2. Compute CID metric over the sequence
    3. Detect semantic boundaries
    4. Segment memories into slices
    5. Compute centroids
    6. Store slices + page table entries

    Returns stats about the rebuild.
    """
    pool = await get_pool()

    log.info("Rebuilding semantic slices...")

    # 1. Load all active memories ordered by creation date
    rows = await pool.fetch(
        """SELECT id, content, category, confidence, importance_score,
                  embedding::text as embedding_text
           FROM semantic_memories
           WHERE archived IS NOT TRUE AND deleted_at IS NULL
             AND embedding IS NOT NULL
           ORDER BY created_at ASC"""
    )

    if not rows:
        return {"slices_created": 0, "memories_processed": 0, "error": "no memories found"}

    log.info(f"Processing {len(rows)} memories for slicing")

    # Parse embeddings
    memories = []
    embeddings = []
    for r in rows:
        emb_text = r["embedding_text"]
        if emb_text:
            try:
                # Parse PostgreSQL vector format: [0.1,0.2,...]
                emb = [float(x) for x in emb_text.strip("[]").split(",")]
                memories.append(dict(r))
                embeddings.append(emb)
            except Exception:
                continue

    if len(memories) < MIN_SLICE_SIZE:
        return {"slices_created": 0, "memories_processed": len(memories), "error": "too few memories"}

    # 2. Compute CID
    cid_values = _compute_cid(embeddings)

    # 3. Detect boundaries
    boundaries = _detect_boundaries(cid_values)
    log.info(f"Found {len(boundaries)} semantic boundaries")

    # 4. Segment
    segments = _segment_by_boundaries(len(memories), boundaries)
    log.info(f"Created {len(segments)} segments")

    # 5. Clear existing slices and rebuild
    await pool.execute("DELETE FROM semantic_page_table")
    await pool.execute("DELETE FROM semantic_slices")

    slices_created = 0
    for start, end in segments:
        segment_memories = memories[start:end]
        segment_embeddings = embeddings[start:end]

        if not segment_memories:
            continue

        # Compute centroid
        centroid = np.mean(segment_embeddings, axis=0).tolist()
        centroid_str = "[" + ",".join(str(x) for x in centroid) + "]"

        # Generate label
        label = _label_slice(segment_memories)

        # Memory IDs
        memory_ids = [m["id"] for m in segment_memories]

        # Token count
        tokens = _estimate_tokens(segment_memories)

        # Dominant category
        cats = {}
        for m in segment_memories:
            c = m.get("category", "general")
            cats[c] = cats.get(c, 0) + 1
        dom_cat = max(cats, key=cats.get)

        # CID boundary score (max CID value in this segment)
        seg_cid = cid_values[start:end]
        boundary_score = max(seg_cid) if seg_cid else 0.0

        # Generate summary handle for pyramid retrieval (IMPL-04)
        # First sentence of highest-confidence memory, capped at 200 chars
        summary = label  # default to label
        if segment_memories:
            best = max(segment_memories, key=lambda m: float(m.get("confidence", 0) or 0))
            first_sent = (best.get("content") or "")[:200]
            dot_idx = first_sent.find(". ")
            if dot_idx > 20:
                first_sent = first_sent[:dot_idx + 1]
            summary = first_sent.strip() or label

        # Insert slice
        row = await pool.fetchrow(
            """INSERT INTO semantic_slices
               (label, memory_ids, centroid, cid_boundary_score, token_count, category, summary)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               RETURNING id""",
            label,
            memory_ids,
            centroid_str,
            boundary_score,
            tokens,
            dom_cat,
            summary[:200],
        )

        slice_id = row["id"]

        # Compute importance (avg of member importance scores)
        importance_scores = [
            float(m.get("importance_score", 0.5) or 0.5) for m in segment_memories
        ]
        avg_importance = sum(importance_scores) / len(importance_scores)

        # Insert page table entry
        await pool.execute(
            """INSERT INTO semantic_page_table
               (slice_id, level, importance_score)
               VALUES ($1, $2, $3)""",
            slice_id,
            "L2",  # Start in L2, S-MMU pages into L1 on demand
            avg_importance,
        )

        slices_created += 1

    result = {
        "slices_created": slices_created,
        "memories_processed": len(memories),
        "boundaries_found": len(boundaries),
    }
    log.info(f"Slice rebuild complete: {result}")
    return result
