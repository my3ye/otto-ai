# Otto Model Merging Plan — DELLA Specialist Architecture

**Status:** Tooling Ready | **Phase:** Pre-Phase 1 (baseline training pending)
**Date:** 2026-02-22 | **Priority:** P1
**Papers:** arXiv 2601.21115 (Data Mix vs Merge), arXiv 2406.11617 (DELLA), arXiv 2511.21437 (Systematic Study)
**Tool:** `merge_models.py` (this directory) | **Backend:** mergekit (arcee-ai/mergekit)

---

## Core Insight

From arXiv 2601.21115 (IBM Research + Cisco + RPI, Jan 2026):

> **For 7B+ models: merging specialist fine-tunes outperforms jointly training on mixed data.**

| Approach | Strategy | HumanEval Pass@1 |
|----------|----------|-----------------|
| Data mixing (joint training) | Mix all tasks → single model | 90.9% |
| **DELLA merging (specialists)** | Train specialists → merge weights | **92.7%** |
| Task-specific fine-tune | One model per task, no merge | Varies per task |

At Qwen2.5-7B scale, Otto should train **separate LoRA adapters for different capability domains**, then merge them into a unified model using DELLA. This is superior to dumping all training data into a single fine-tune.

---

## Why DELLA Over TIES/DARE?

| Method | Pruning Strategy | 7B Performance | Use Case |
|--------|-----------------|----------------|----------|
| **DELLA** | Magnitude-based sampling | **Best** (Jan 2026 eval) | Otto's primary |
| TIES | Sign election + trimming | Strong | Overlapping tasks |
| DARE + TIES | Random drop + sign | Moderate | Quick experiments |
| Linear avg | Simple weighted average | Baseline | Same-domain tasks |
| SLERP | Geodesic interpolation | Good (2 models only) | Fine-grained blend |

DELLA's magnitude-based approach preserves the most important parameters across all specialist adapters, reducing interference better than random dropping (DARE) or pure sign-based selection (TIES).

---

## Otto Specialist Architecture

Otto's capabilities naturally decompose into 4 specialist domains. Each gets its own LoRA fine-tune, then all are merged:

```
Base Model: Qwen/Qwen2.5-7B-Instruct
         │
         ├── QLoRA Fine-Tune #1: Reasoning Specialist
         │     Training data: planning, analysis, task_decomposition, research
         │     Output: otto-lora-reasoning/
         │
         ├── QLoRA Fine-Tune #2: Personality Specialist
         │     Training data: persona, whatsapp messages, heartbeat orchestration
         │     Output: otto-lora-personality/
         │
         ├── QLoRA Fine-Tune #3: Memory Specialist
         │     Training data: episodic retrieval, semantic ops, context management
         │     Output: otto-lora-memory/
         │
         └── QLoRA Fine-Tune #4: Crypto Specialist (optional, Phase 2+)
               Training data: alpha signals, wallet analysis, trading decisions
               Output: otto-lora-crypto/
                    │
                    ▼
            DELLA Merge (merge_models.py)
                    │
                    ▼
            otto-merged-v1/  (unified model)
                    │
                    ▼
            Export GGUF → Deploy via Ollama
```

### Specialist Definitions

| Specialist | Training Tags | Expected Examples | Priority |
|------------|---------------|-------------------|----------|
| **Reasoning** | planning, analysis, task_decomposition, research, heartbeat | ~400 | 1 |
| **Personality** | persona, whatsapp, tone, mev_relationship, reflection | ~400 | 2 |
| **Memory** | episodic, semantic, retrieval, memory_ops, context | ~300 | 3 |
| **Crypto** | alpha, trading, signals, wallet, backtest | ~200 | 4 |

Current training data (1,486 examples) has enough to cover specialists 1-3 after filtering by tag. Specialist 4 may need additional alpha-specific data collection.

---

## Step-by-Step Execution (Post Phase 1 Baseline)

### Phase 1: Baseline (Current Blocker: RunPod API Key)

```bash
# Train unified baseline first (all 1,486 examples, single LoRA)
python3 train.py --method qlora
# → otto-qlora-v1/lora_adapter/
```

This establishes the quality floor. If baseline quality is acceptable, proceed to specialist merging.

### Phase 2: Specialist Fine-Tunes

Filter training data by domain, then run 4 separate QLoRA runs:

```bash
# On RunPod — run these 4 sequentially or in parallel pods

# Specialist 1: Reasoning
OTTO_DATA=otto_training_reasoning.jsonl \
OTTO_OUTPUT=otto-lora-reasoning \
python3 train.py --method qlora

# Specialist 2: Personality
OTTO_DATA=otto_training_personality.jsonl \
OTTO_OUTPUT=otto-lora-personality \
python3 train.py --method qlora

# Specialist 3: Memory
OTTO_DATA=otto_training_memory.jsonl \
OTTO_OUTPUT=otto-lora-memory \
python3 train.py --method qlora
```

**Cost estimate for 3 specialists:**
- ~300-400 examples each × 3 epochs ≈ 45-60 min per specialist on RTX 4090
- 3 specialists × $0.34/hr × 1 hr = ~$1.02 total
- Well within $15 RunPod budget (after ~$1 for Phase 1 baseline)

### Phase 3: Pre-Merge Diagnostic

Before merging, diagnose compatibility (checks L2 distance + Pearson correlation):

```bash
# Download adapters from RunPod to otto-machine
scp -r runpod:/workspace/otto-lora-reasoning ~/otto/projects/own_model/models/
scp -r runpod:/workspace/otto-lora-personality ~/otto/projects/own_model/models/
scp -r runpod:/workspace/otto-lora-memory ~/otto/projects/own_model/models/

# Diagnose pairwise compatibility (predict merging success)
python3 merge_models.py diagnose \
    --adapter1 models/otto-lora-reasoning/lora_adapter \
    --adapter2 models/otto-lora-personality/lora_adapter \
    --output diagnostics/reasoning_vs_personality.json

python3 merge_models.py diagnose \
    --adapter1 models/otto-lora-reasoning/lora_adapter \
    --adapter2 models/otto-lora-memory/lora_adapter \
    --output diagnostics/reasoning_vs_memory.json
```

**Interpret results:**
- Avg Pearson > 0.7 → MERGE_SAFE (density=0.7)
- Avg Pearson 0.3-0.7 → MERGE_LIKELY (density=0.5)
- Avg Pearson 0.0-0.3 → MERGE_CAUTIOUS (density=0.3)
- Avg Pearson < 0.0 → DO_NOT_MERGE (deploy separately)

### Phase 4: Generate Merge Config

```bash
# Generate DELLA merge config for 3 specialists
python3 merge_models.py config \
    --base Qwen/Qwen2.5-7B-Instruct \
    --adapters \
        models/otto-lora-reasoning/lora_adapter \
        models/otto-lora-personality/lora_adapter \
        models/otto-lora-memory/lora_adapter \
    --method della \
    --density 0.5 \
    --output merge_output/merge_config.yaml
```

Or run the full pipeline (diagnose + config + optional merge in one step):

```bash
python3 merge_models.py pipeline \
    --base Qwen/Qwen2.5-7B-Instruct \
    --adapters \
        models/otto-lora-reasoning/lora_adapter \
        models/otto-lora-personality/lora_adapter \
        models/otto-lora-memory/lora_adapter \
    --output merge_output/ \
    --method della
    # Add --run to execute merge immediately
```

### Phase 5: Execute Merge (on RunPod or otto-machine)

mergekit runs on CPU (slow but works on otto-machine) or GPU (fast, RunPod preferred):

```bash
# Install mergekit (once)
pip install mergekit

# Execute merge — this is the DELLA merge itself
mergekit-yaml merge_output/merge_config.yaml merge_output/merged \
    --copy-tokenizer \
    --lazy-unpickle \
    --cuda   # omit if CPU-only

# Or via script:
python3 merge_models.py run \
    --config merge_output/merge_config.yaml \
    --output merge_output/merged
```

**Cost:** Merging does not train — it's a weight-space operation. On RTX 4090: ~5-15 minutes. On otto-machine CPU: ~30-60 minutes. No GPU cost if done locally.

### Phase 6: Export and Deploy

```bash
# Convert merged model to GGUF for Ollama inference
# (mergekit output is in HuggingFace format)
pip install llama-cpp-python

# Option A: Use Unsloth on RunPod for GGUF export
# Option B: Use llama.cpp conversion script
git clone https://github.com/ggerganov/llama.cpp /tmp/llama_cpp
python3 /tmp/llama_cpp/convert_hf_to_gguf.py merge_output/merged \
    --outfile merge_output/otto-merged-v1-q4km.gguf \
    --outtype q4_k_m

# Deploy via Ollama on otto-machine
curl -fsSL https://ollama.com/install.sh | sh
ollama create otto:v2 -f otto-core/Modelfile
ollama run otto:v2
```

---

## Density Parameter Guide

The DELLA `density` controls what fraction of parameters are retained during merging:

| Density | Effect | When to Use |
|---------|--------|-------------|
| `0.9` | Minimal pruning — almost all params kept | Specialists trained on very similar data |
| `0.7` | Light pruning | High diagnostic correlation (Pearson > 0.7) |
| `0.5` | **Default** — balanced | Standard multi-domain merge |
| `0.3` | Aggressive pruning | Low correlation, high interference risk |
| `0.1` | Extreme pruning | Only highest-magnitude params survive |

Start with `density=0.5`. If the merged model performs worse than baseline, try `0.7`. If there's interference (model outputs blend weirdly), try `0.3`.

---

## Weight Coefficients

By default, specialists are merged with equal weights (each gets `1/N` weight). Override when one specialist is more important:

```yaml
# Example: Personality weighted more heavily (2x reasoning, 2x memory)
models:
  - model: otto-lora-reasoning
    parameters:
      weight: 0.25
      density: 0.5
  - model: otto-lora-personality
    parameters:
      weight: 0.50    # 2x weight
      density: 0.5
  - model: otto-lora-memory
    parameters:
      weight: 0.25
      density: 0.5
```

For Otto: personality should likely get the highest weight (it defines who Otto IS), followed by reasoning (how Otto thinks), then memory ops (how Otto retrieves).

**Recommended starting weights:**
- Personality: 0.4
- Reasoning: 0.35
- Memory: 0.25

---

## Expected Benefits

1. **Multi-domain capability without data mixing interference**: Each specialist trains cleanly on its domain without gradients from other domains polluting its representations.

2. **Modular updates**: When Otto's reasoning capability needs improvement, retrain just `otto-lora-reasoning` and re-merge. No need to retrain all specialists.

3. **Quality floor**: The merged model should perform at least as well as the best individual specialist on each domain, and often better than any single specialist (task transfer via weight interpolation).

4. **Research backing**: DELLA outperforms data mixing at 7B scale (92.7% vs 90.9% Pass@1). The scale-dependent finding means this strategy is specifically right for Qwen2.5-7B.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Merge interference (quality drops vs baseline) | Medium | High | Run diagnostic first; lower density; try TIES as alternative |
| Specialist data insufficient (< 200 examples) | High for crypto | Medium | Merge 2-3 specialists first; add crypto when data is larger |
| mergekit OOM on otto-machine (16GB RAM) | Medium | Medium | Use `--lazy-unpickle` flag; or merge on RunPod GPU pod |
| Merged model worse than unified baseline | Low | High | Fall back to unified baseline for deployment; use specialists for evaluation only |
| GGUF conversion fails after merge | Low | Low | HF format still usable via transformers; convert separately |

---

## Fallback Strategy

If specialist merging produces a model worse than the unified baseline:

1. **Deploy the unified baseline** (`otto-qlora-v1`) — it still captures all capabilities in one adapter
2. **Use multi-LoRA composition** instead of merging — load specialists as separate PEFT adapters and blend at inference time
3. **Investigate diagnostic output** — if Pearson correlation was negative for some pair, those two specialists should NOT be merged together (deploy them separately or use different merge method)

---

## Integration with Continuous Learning

Once the specialist merge pipeline is established, each heartbeat cycle can feed new training signals into the appropriate specialist:

```
Heartbeat generates training signal
        │
        ├── Reasoning/planning signal → queue for otto-lora-reasoning update
        ├── Persona/tone signal → queue for otto-lora-personality update
        └── Memory ops signal → queue for otto-lora-memory update
                │
    (Weekly or monthly) Batch re-train specialists with accumulated signals
                │
    Re-merge with DELLA → otto-merged-v2, v3, ...
```

This creates a genuine continuous learning loop where Otto's own model improves incrementally without catastrophic forgetting (each specialist stays in its domain).

---

## Quickstart Checklist

- [ ] Phase 1: Complete baseline QLoRA training on RunPod (blocked: API key needed)
- [ ] Evaluate baseline quality vs current Claude-animated Otto
- [ ] Tag existing training data (1,486 examples) by domain for specialist splits
- [ ] Phase 2: Train 3 specialist adapters (reasoning, personality, memory)
- [ ] Phase 3: Run diagnostics with `merge_models.py diagnose`
- [ ] Phase 4: Generate merge config with `merge_models.py config`
- [ ] Phase 5: Execute DELLA merge with `merge_models.py run`
- [ ] Phase 6: Export GGUF and deploy via Ollama
- [ ] Evaluate merged model quality vs baseline and individual specialists
- [ ] Integrate merged model into Otto heartbeat loop

---

*Document Version: 1.0*
*Tool: merge_models.py (same directory)*
*Next review: After Phase 1 baseline training completes*
