# Training Data Quality Report

**Generated:** 2026-02-22
**File:** `training_data.jsonl` → `training_data_clean.jsonl`

---

## Summary

| Metric | Value |
|--------|-------|
| Total lines (raw) | 1486 |
| Valid JSON | 1486 (100%) |
| Malformed JSON | 0 |
| Wrong schema | 0 |
| Exact duplicates removed | 167 |
| **Final clean count** | **1319** |
| Avg tokens per example | ~196 |
| Examples > 2048 tokens | 0 |
| Empty outputs | 0 |

---

## Format

All 1486 examples use the `instruction/input/output` format:
```json
{"instruction": "...", "input": "...", "output": "..."}
```

> **Note for training:** This is Alpaca/LoRA format, NOT ChatML `{"messages": [...]}`. The `train.py` script must use Alpaca prompt template, not ChatML. Verify before QLoRA run.

---

## Deduplication

- **Method:** Exact match on `(instruction + first 200 chars of input)` → MD5 hash
- **167 duplicates removed** — all from repeated heartbeat runs extracting the same memory entries
- Clean file written to `training_data_clean.jsonl`

---

## Token Distribution

| Range | Count |
|-------|-------|
| < 50 tokens | 22 |
| 50–99 tokens | 344 |
| 100–199 tokens | 580 |
| 200–499 tokens | 267 |
| 500–999 tokens | 97 |
| 1000–2047 tokens | 9 |
| ≥ 2048 tokens | **0** |

No examples exceed the 2048-token limit. Max context is safe for standard LoRA training.

---

## Instruction Template Diversity

| Instruction Template | Count |
|----------------------|-------|
| "Otto, given this context, what is your analysis?" | 471 (36%) |
| "How should Otto apply this research finding?" | 94 (7%) |
| "You are Otto's reflection heartbeat..." | 18 |
| "You are Otto. Mev sent you a message via WhatsApp..." | 17 |
| "What does Otto know about infrastructure?" | 8 |
| Other unique templates | 711 |

**Unique instruction templates:** 684
**Single-use templates:** 663 (97%)

> **Concern:** 36% of data shares one instruction template ("given this context, what is your analysis?"). This creates template bias — the model may learn to respond to this specific prompt well but generalize poorly. Recommend diversifying instruction templates in next data generation pass.

---

## Data Categories

| Category | Count |
|----------|-------|
| Context analysis (episodic/memory facts) | ~471 |
| Research application | ~94 |
| Reflection heartbeat decisions | ~34 |
| Task execution | ~203 |
| Memory/semantic | ~35 |
| Session summaries | ~14 |
| Reasoning chains | ~11 |
| Principles/rules | ~11 |
| Other | ~446 |

---

## Quality Issues Found

1. **Template concentration:** 36% of examples use a single instruction template. Low diversity may cause overfitting to this prompt pattern.
2. **Short examples:** 22 examples < 50 tokens — may be too short to provide useful signal. Consider filtering at < 30 tokens.
3. **Format mismatch risk:** All examples are Alpaca format. Confirm `train.py` uses matching template.

---

## Recommendations

1. **Use `training_data_clean.jsonl`** (1319 examples) for training — duplicates removed.
2. **Next data expansion:** Generate more diverse instruction templates. Vary the phrasing beyond "given this context" + "how should Otto apply".
3. **Optional:** Filter the 22 ultra-short examples (< 50 tokens) for a stricter 1297-example set.
4. **Before training:** Verify `train.py` Alpaca template matches `{"instruction": ..., "input": ..., "output": ...}` format.

---

## Files

| File | Count | Description |
|------|-------|-------------|
| `training_data.jsonl` | 1486 | Original (with duplicates) |
| `training_data_clean.jsonl` | 1319 | Clean, deduplicated |
