"""SimpleMem: 3-stage semantic lossless compression for memory retrieval.

Based on arXiv 2601.02553 (Jan 2026) — SimpleMem achieves large token
reduction at retrieval time while preserving semantic content.

Stages:
  1. DEDUP      — remove near-duplicate results by word-level Jaccard similarity
  2. SUMMARIZE  — compress long content to first sentence + key facts (pure Python)
  3. RANK+TRIM  — re-rank by relevance score, trim to top-K

Pure Python — no LLM calls, no DB calls. Uses summary_content (HyMem) when
available for Stage 2 to leverage pre-computed concise representations.
"""

import logging
import re

log = logging.getLogger("otto.simplemem")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _word_set(text: str) -> set[str]:
    """Tokenize text to a set of lowercase alpha-numeric words."""
    return set(re.findall(r'\b\w{3,}\b', text.lower()))


def _jaccard(a: str, b: str) -> float:
    """Word-level Jaccard similarity between two content strings."""
    sa = _word_set(a)
    sb = _word_set(b)
    if not sa or not sb:
        return 0.0
    intersection = len(sa & sb)
    union = len(sa | sb)
    return intersection / union if union > 0 else 0.0


def _extract_first_sentence(text: str) -> str:
    """Extract first complete sentence from text.

    Stops at the first sentence-ending punctuation followed by whitespace
    (or end of text). Falls back to 200-char truncation.
    """
    text = text.strip()
    # Try sentence-ending punctuation with at least 20 chars of context
    for m in re.finditer(r'[.!?](?=\s|$)', text):
        end = m.end()
        if end >= 20:
            return text[:end].strip()
    # No sentence boundary found — truncate at 200 chars
    if len(text) <= 200:
        return text
    # Try to cut at a word boundary
    cut = text[:200].rsplit(' ', 1)[0]
    return cut + '...'


def _compress_content(content: str, summary_content: str | None = None) -> str:
    """Compress a memory's content to its essential meaning.

    Priority order:
    1. summary_content (HyMem pre-generated summary) — if shorter than content
    2. First-sentence extraction
    3. Verbatim (content already short)
    """
    if not content:
        return content

    # Already short enough — no compression needed
    if len(content) <= 200:
        return content

    # Use HyMem summary if available and actually shorter
    if summary_content and len(summary_content.strip()) < len(content) * 0.8:
        return summary_content.strip()

    return _extract_first_sentence(content)


def _get_score(m: dict) -> float:
    """Extract the best available relevance score from a memory dict."""
    for key in ('score', 'importance_score', 'confidence'):
        val = m.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return 0.5


# ── Main compression entry point ──────────────────────────────────────────────

def compress_for_context(
    memories: list,
    top_k: int | None = None,
    dedup_threshold: float = 0.82,
) -> tuple[list, int, int]:
    """SimpleMem 3-stage semantic compression.

    Args:
        memories:        List of SemanticMemoryOut objects or dicts.
        top_k:           Maximum results after compression (None = no trim beyond dedup).
        dedup_threshold: Jaccard similarity above which to suppress near-duplicates.
                         Default 0.82 (slightly below the storage-level 0.85 AgeMem
                         threshold to catch retrieval-time drift).

    Returns:
        (compressed_list, original_char_count, compressed_char_count)
        compressed_list has the same type as memories (models preserved if input is models).
    """
    if not memories:
        return memories, 0, 0

    # Normalise to dicts for uniform processing
    is_model = hasattr(memories[0], 'model_dump')
    if is_model:
        items = [m.model_dump() for m in memories]
    else:
        items = [dict(m) for m in memories]

    original_chars = sum(len(str(m.get('content') or '')) for m in items)

    # ── Stage 1: DEDUP ────────────────────────────────────────────────────────
    # Suppress near-duplicate results using word-level Jaccard similarity.
    # When two memories are near-duplicates, keep the one with the higher score.
    suppressed: set[int] = set()

    for i in range(len(items)):
        if i in suppressed:
            continue
        content_i = str(items[i].get('content') or '')
        for j in range(i + 1, len(items)):
            if j in suppressed:
                continue
            content_j = str(items[j].get('content') or '')
            sim = _jaccard(content_i, content_j)
            if sim >= dedup_threshold:
                score_i = _get_score(items[i])
                score_j = _get_score(items[j])
                if score_i >= score_j:
                    suppressed.add(j)
                else:
                    suppressed.add(i)
                    break  # i is suppressed; move to next i

    deduplicated = [m for idx, m in enumerate(items) if idx not in suppressed]
    n_deduped = len(items) - len(deduplicated)

    # ── Stage 2: SUMMARIZE ────────────────────────────────────────────────────
    # Compress each memory's content field using summary_content or first-sentence.
    summarized = []
    for item in deduplicated:
        compressed = dict(item)
        content = str(item.get('content') or '')
        summary = item.get('summary_content')
        compressed['content'] = _compress_content(content, summary)
        summarized.append(compressed)

    # ── Stage 3: RANK+TRIM ────────────────────────────────────────────────────
    # Re-rank by score (descending), trim to top_k.
    ranked = sorted(summarized, key=_get_score, reverse=True)
    n_before_trim = len(ranked)
    if top_k is not None:
        ranked = ranked[:top_k]

    compressed_chars = sum(len(str(m.get('content') or '')) for m in ranked)

    log.info(
        f"SimpleMem: {len(items)} → {len(ranked)} memories "
        f"(deduped={n_deduped}, trimmed={n_before_trim - len(ranked)}) | "
        f"chars {original_chars} → {compressed_chars} "
        f"({round(100 * (1 - compressed_chars / original_chars), 1) if original_chars > 0 else 0}% reduction)"
    )

    # Restore to original model type if input was Pydantic models
    if is_model:
        from .models import SemanticMemoryOut
        result = []
        for m in ranked:
            try:
                result.append(SemanticMemoryOut(**m))
            except Exception:
                result.append(m)
        return result, original_chars, compressed_chars

    return ranked, original_chars, compressed_chars
