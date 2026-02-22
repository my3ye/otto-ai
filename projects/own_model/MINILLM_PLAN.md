# MiniLLM Reverse-KL Distillation Plan for Otto Own-Model Phase 2

**Status:** Research Complete | **Date:** 2026-02-22 | **Priority:** P1  
**Arxiv:** 2306.08543 (v6 Jan 2026) | **Code:** https://github.com/microsoft/LMOps/tree/main/minillm

---

## Executive Summary

This document outlines the implementation plan for MiniLLM-style knowledge distillation to upgrade Otto's Phase 1 QLoRA model (Qwen 2.5 7B) with behaviors distilled from Claude (teacher model). **Key finding: MiniLLM's reverse-KL objective is superior to standard forward-KL distillation for generative LLMs**, producing students that are more precise, better calibrated, and less prone to hallucination.

### Phase 2 at a Glance

| Aspect | Phase 1 (Current) | Phase 2 (This Plan) |
|--------|-------------------|---------------------|
| **Training Type** | QLoRA supervised fine-tuning | Reverse-KL distillation |
| **Teacher Model** | N/A (ground truth responses) | Claude API / Claude 3.5 Sonnet |
| **Student Model** | Qwen 2.5 7B + LoRA adapters | Same base, new distillation adapters |
| **Objective** | Mimic ground truth outputs | Match teacher's high-probability modes |
| **Data Source** | 1,486 Otto interaction examples | Claude-generated responses on prompts |
| **Key Advantage** | Task-specific adaptation | Teacher quality transfer + calibration |

### Recommendation: **Phase 1 First, Phase 2 After Baseline**

1. **Immediate (Now):** Complete Phase 1 QLoRA training to establish baseline
2. **Phase 2 (After baseline proven):** Implement MiniLLM distillation with Claude as teacher
3. **Phase 3 (Future):** Self-distillation from larger Otto models or multi-teacher ensemble

---

## 1. MiniLLM Technical Overview

### 1.1 The Core Problem: Forward KL vs Reverse KL

Standard knowledge distillation minimizes **forward KL divergence**: `KL[p_teacher || p_student]`

**Forward KL behavior (mode-covering):**
- Forces student to cover ALL modes of teacher distribution
- Student assigns probability mass to low-probability regions of teacher
- **Result:** Hallucinations, over-dispersed outputs, calibration errors

**Reverse KL behavior (mode-seeking):**
- Minimizes `KL[p_student || p_teacher]`
- Student focuses on HIGH-probability regions of teacher
- Ignores teacher's low-probability tail regions
- **Result:** Precise, focused outputs that are likely under teacher distribution

### 1.2 Toy Example Illustration

```
Teacher distribution: Bimodal Gaussian (two peaks)
Student capacity: Single Gaussian (can only fit one peak)

Forward KL (standard KD):
  Student places mass BETWEEN the two peaks
  Result: Samples are unlikely under either teacher peak
  
Reverse KL (MiniLLM):
  Student picks the STRONGER peak and fits it precisely
  Result: All samples are likely under the teacher
```

### 1.3 Why This Matters for Otto

| Issue | Forward KL | Reverse KL |
|-------|------------|------------|
| Hallucinations | High (covers low-prob modes) | Low (stays in high-prob regions) |
| Calibration | Poor (overconfident on tails) | Better (matches teacher confidence) |
| Long-form generation | Degrades (exposure bias) | Stable (precise mode-seeking) |
| Response diversity | Artificially high | Natural (from high-prob modes) |

### 1.4 The MiniLLM Objective Function

```python
# Reverse KL objective
L(θ) = KL[q_θ || p] = -E_{x~p_x, y~q_θ}[log(p(y|x) / q_θ(y|x))]

# Policy gradient derivation (since sampling from student)
∇L(θ) = -E[Σ_t (R_t - 1) ∇log q_θ(y_t | y_<t, x)]

where R_t = Σ_{t'=t}^T log(p(y_t'|y_<t',x) / q_θ(y_t'|y_<t',x))
```

**Key insight:** This is RL-style training where:
- Student generates samples (on-policy)
- Teacher provides reward signal `log p(y|x)`
- Reward `R_t` measures how much teacher prefers the student's generation

---

## 2. MiniLLM Algorithm Details

### 2.1 Algorithm 1 from Paper (Simplified)

```
Input: Dataset D (prompts), Teacher p, Pre-trained student q_θ0

1. SFT warmup: Fine-tune q_θ0 on D with ground truth (optional but recommended)
2. For each training step:
   a. Sample batch of prompts from D
   b. Generate responses using TEACHER-MIXED sampling:
      p̃(yt|y<t,x) = α·p(yt|y<t,x) + (1-α)·q_θ(yt|y<t,x)
   c. Compute single-step gradient (∇L)_Single
   d. Compute long-span gradient (∇L)_Long with length normalization
   e. Add language modeling loss on pre-training corpus (preserve general capabilities)
   f. Update θ
```

### 2.2 Key Stabilization Techniques

| Technique | Purpose | Hyperparameter |
|-----------|---------|----------------|
| **Single-step decomposition** | Reduce variance from accumulated rewards | N/A (algorithmic) |
| **Teacher-mixed sampling** | Prevent reward hacking / degenerate outputs | α = 0.2 (teacher mix) |
| **Length normalization** | Prevent short-output bias | Normalize by (T-t-1) |
| **Importance weighting** | Correct for sampling from p̃ not q_θ | w_t approximation |
| **Gradient clipping** | Stability | ε = 0.2 (PPO-style) |

### 2.3 Training Data Requirements

MiniLLM uses:
1. **Task dataset D:** Prompts for the target task (Otto interactions)
2. **Pre-training corpus D_PT:** General text to preserve base capabilities

For Otto Phase 2:
- **D:** ~1,000-5,000 prompts from Otto interaction history
- **D_PT:** Sample from Qwen's pre-training distribution (web text, code)

---

## 3. Data Generation Pipeline

### 3.1 Overview

```
Phase 1 Output (QLoRA model)
    ↓
Generate prompts from Otto interaction history
    ↓
Claude API (teacher) generates high-quality responses
    ↓
Store (prompt, teacher_response) pairs
    ↓
MiniLLM training (student mimics teacher distribution)
    ↓
Phase 2 Output (distilled QLoRA adapters)
```

### 3.2 Teacher Data Generation Script

```python
# generate_distillation_data.py
"""Generate teacher responses using Claude API for MiniLLM training."""

import os
import json
import asyncio
from typing import List, Dict
from anthropic import AsyncAnthropic

# Configuration
CLaude_MODEL = "claude-3-5-sonnet-20241022"  # Teacher model
OUTPUT_FILE = "distillation_data.jsonl"
BATCH_SIZE = 10  # Parallel requests
MAX_TOKENS = 2048
TEMPERATURE = 0.7  # Some diversity in teacher outputs

SYSTEM_PROMPT = """You are an expert AI assistant demonstrating high-quality reasoning, tool use, and autonomous decision-making. Provide thorough, accurate, and well-structured responses."""

async def generate_teacher_response(
    client: AsyncAnthropic,
    prompt: str,
    system: str = SYSTEM_PROMPT
) -> str:
    """Get teacher response from Claude API."""
    response = await client.messages.create(
        model=CLaude_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

async def generate_dataset(
    prompts: List[str],
    output_file: str
) -> None:
    """Generate teacher responses for all prompts."""
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    with open(output_file, 'w') as f:
        for i in range(0, len(prompts), BATCH_SIZE):
            batch = prompts[i:i + BATCH_SIZE]
            
            # Parallel generation
            tasks = [generate_teacher_response(client, p) for p in batch]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for prompt, response in zip(batch, responses):
                if isinstance(response, Exception):
                    print(f"Error for prompt: {prompt[:50]}... - {response}")
                    continue
                    
                record = {
                    "prompt": prompt,
                    "teacher_response": response,
                    "model": CLaude_MODEL,
                }
                f.write(json.dumps(record) + '\n')
                f.flush()
            
            print(f"Processed {i + len(batch)}/{len(prompts)}")

if __name__ == "__main__":
    # Load prompts from Otto interaction history
    prompts = load_otto_prompts()  # From training_data.jsonl
    asyncio.run(generate_dataset(prompts, OUTPUT_FILE))
```

### 3.3 Prompt Sources for Distillation

| Source | Count | Description |
|--------|-------|-------------|
| Otto heartbeat reasoning traces | ~500 | Orchestrator/reflection decisions |
| Tool use examples | ~300 | Web search, file operations, API calls |
| Multi-step task planning | ~200 | Task decomposition and execution |
| Error recovery scenarios | ~200 | Handling failures, retries, adaptation |
| Constitutional decisions | ~300 | Ethical choices, priority trade-offs |
| **Total** | **~1,500** | Scalable to 5,000+ |

### 3.4 Data Format for Training

```json
{
  "conversations": [
    {"from": "system", "value": "You are Otto, an autonomous AI agent..."},
    {"from": "human", "value": "Research the latest knowledge distillation techniques."},
    {"from": "gpt", "value": "<teacher_response_from_claude>"}
  ]
}
```

---

## 4. Estimated API Costs

### 4.1 Claude API Pricing (as of Feb 2026)

| Model | Input Tokens | Output Tokens |
|-------|--------------|---------------|
| Claude 3.5 Sonnet | $3 / 1M tokens | $15 / 1M tokens |
| Claude 3.5 Haiku | $0.80 / 1M tokens | $4 / 1M tokens |

### 4.2 Cost Calculation

**Assumptions:**
- Average prompt length: 200 tokens
- Average teacher response: 500 tokens
- Dataset size: 1,500 examples

```
Input tokens:  1,500 × 200  = 300,000 tokens
Output tokens: 1,500 × 500  = 750,000 tokens

Claude 3.5 Sonnet cost:
  Input:  300,000 × $3 / 1M   = $0.90
  Output: 750,000 × $15 / 1M  = $11.25
  Total:  ~$12.15

Claude 3.5 Haiku cost (faster, cheaper):
  Input:  300,000 × $0.80 / 1M = $0.24
  Output: 750,000 × $4 / 1M    = $3.00
  Total:  ~$3.24
```

### 4.3 Cost Optimization Strategies

| Strategy | Savings | Trade-off |
|----------|---------|-----------|
| Use Haiku for initial experiments | ~73% | Slightly lower teacher quality |
| Generate 500 examples first | ~67% | Less coverage, may need iteration |
| Cache responses for identical prompts | Variable | Requires dedup logic |
| Use existing Otto logs as partial data | ~30% | Less teacher influence |

### 4.4 Recommended Budget

| Phase | Examples | Model | Est. Cost |
|-------|----------|-------|-----------|
| **Pilot** | 500 | Haiku | ~$1.10 |
| **Full** | 1,500 | Sonnet | ~$12.15 |
| **Extended** | 5,000 | Sonnet | ~$40.50 |

**Recommendation:** Start with pilot (500 examples, Haiku) to validate pipeline, then scale to full dataset with Sonnet for best quality.

---

## 5. Tooling Analysis

### 5.1 Available Tools for MiniLLM Implementation

| Tool | Supports Reverse KL | Notes |
|------|---------------------|-------|
| **TRL GKDTrainer** | ✅ Yes (JSD/Generalized JSD) | HF official, well-maintained |
| **MiniLLM official** | ✅ Yes (reference impl) | Microsoft LMOps repo |
| **distilabel** | ⚠️ Partial (black-box only) | Great for data generation |
| **OpenAI API** | ❌ No | Teacher only, no training |
| **Custom implementation** | ✅ Yes | Most flexible, highest effort |

### 5.2 TRL GKDTrainer (Recommended)

TRL (Transformer Reinforcement Learning) includes `GKDTrainer` for Generalized Knowledge Distillation:

```python
from trl import GKDConfig, GKDTrainer

# GKD uses Generalized Jensen-Shannon Divergence
# which interpolates between forward KL and reverse KL
# β=0.5 → symmetric JSD (good balance)
# β→0 → approaches reverse KL (MiniLLM-style)
# β→1 → approaches forward KL (standard KD)

training_args = GKDConfig(
    output_dir="otto-minillm-v1",
    beta=0.1,  # Closer to reverse KL (MiniLLM-style)
    temperature=1.0,
    teacher_model_name_or_path="claude",  # Not directly applicable
)

trainer = GKDTrainer(
    model=student_model,  # Qwen 2.5 7B + adapters
    teacher_model=teacher_model,  # Need to wrap Claude API
    args=training_args,
    train_dataset=distillation_dataset,
)
```

**Limitation:** GKDTrainer expects both models to be loadable HuggingFace models. Claude API requires a custom wrapper.

### 5.3 Custom MiniLLM Implementation (Required)

Since Claude is API-only, we need custom implementation:

```python
# minillm_trainer.py
"""Custom MiniLLM trainer with Claude API as teacher."""

import torch
import torch.nn.functional as F
from transformers import Trainer
from typing import Dict, Optional

class MiniLLMTrainer(Trainer):
    """
    MiniLLM reverse-KL distillation trainer.
    
    Teacher: Claude API (generates responses, provides log-probs via API)
    Student: Qwen 2.5 7B + QLoRA adapters (trainable)
    """
    
    def __init__(
        self,
        teacher_client,  # Anthropic client
        teacher_mix_alpha: float = 0.2,  # Teacher-mixed sampling
        length_normalize: bool = True,
        pretraining_corpus=None,  # D_PT for LM loss
        lm_loss_weight: float = 0.1,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.teacher = teacher_client
        self.alpha = teacher_mix_alpha
        self.length_normalize = length_normalize
        self.pretraining_corpus = pretraining_corpus
        self.lm_loss_weight = lm_loss_weight
        
    def compute_loss(
        self,
        model,
        inputs: Dict[str, torch.Tensor],
        return_outputs: bool = False
    ):
        """Compute reverse-KL distillation loss."""
        # This is a simplified sketch - full implementation needed
        
        # 1. Student forward pass
        student_outputs = model(**inputs)
        student_logits = student_outputs.logits
        
        # 2. Generate samples using teacher-mixed sampling
        # (requires custom sampling loop with teacher log-probs)
        
        # 3. Get teacher log-probabilities for sampled tokens
        # (call Claude API or use cached teacher distribution)
        
        # 4. Compute policy gradient with reverse-KL objective
        # ∇L = -E[(R_t - 1) ∇log q_θ(y_t)]
        
        # 5. Add language modeling loss on pre-training corpus
        
        raise NotImplementedError("Full implementation required")
```

### 5.4 Recommended Tooling Stack

| Component | Tool | Rationale |
|-----------|------|-----------|
| Base training | TRL SFTTrainer | Proven, flexible |
| Distillation loss | Custom implementation | Claude API requires wrapper |
| Teacher generation | Claude API + caching | Best quality teacher |
| Data pipeline | distilabel-style | Parallel generation, retries |
| Model serving | vLLM (for student inference) | Fast, compatible with adapters |

---

## 6. Integration with Existing QLoRA Pipeline

### 6.1 Phase 1 → Phase 2 Transition

```
Phase 1 Output:
  - Qwen 2.5 7B base model
  - LoRA adapters (otto-lora-v1/)
  - Training config and hyperparameters

Phase 2 Preparation:
  1. Generate distillation data using Claude API
  2. Create new output directory: otto-minillm-v1/
  
Phase 2 Training:
  1. Load base model + Phase 1 LoRA adapters
  2. Optionally merge adapters into base (warm start)
  3. Initialize MiniLLM trainer with Claude teacher
  4. Train with reverse-KL objective
  5. Save new LoRA adapters (distinct from Phase 1)

Phase 2 Output:
  - New LoRA adapters with distilled knowledge
  - Can be merged or used separately
```

### 6.2 Training Script Integration

```python
# train_minillm.py
"""Otto Phase 2: MiniLLM distillation training."""

import os
from unsloth import FastLanguageModel
from transformers import TrainingArguments

# ─── Configuration ─────────────────────────────────────────────────────────
CFG = {
    "base_model": "Qwen/Qwen2.5-7B-Instruct",
    "phase1_adapter": "otto-lora-v1/lora_adapter",  # Warm start
    "output_dir": "otto-minillm-v1",
    "distillation_data": "distillation_data.jsonl",
    
    # MiniLLM hyperparameters
    "teacher_mix_alpha": 0.2,  # Teacher-mixed sampling
    "length_normalize": True,
    "lm_loss_weight": 0.1,  # Preserve general capabilities
    
    # Training
    "num_epochs": 3,
    "learning_rate": 1e-4,  # Lower than SFT
    "batch_size": 1,  # On-policy requires sequential generation
    "gradient_accumulation": 8,
}

# ─── Load Model with Phase 1 Adapters ───────────────────────────────────────
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=CFG["base_model"],
    max_seq_length=2048,
    load_in_4bit=True,
)

# Load Phase 1 adapters as warm start
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                   "gate_proj", "up_proj", "down_proj"],
    lora_alpha=32,
)
model.load_adapter(CFG["phase1_adapter"], adapter_name="phase1")

# Option A: Merge Phase 1 into base for warm start
# model = model.merge_and_unload()
# Then re-initialize fresh adapters for Phase 2

# Option B: Continue training Phase 1 adapters (risk: catastrophic forgetting)

# ─── Initialize MiniLLM Trainer ─────────────────────────────────────────────
from anthropic import Anthropic

teacher_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

trainer = MiniLLMTrainer(
    model=model,
    teacher_client=teacher_client,
    teacher_mix_alpha=CFG["teacher_mix_alpha"],
    args=TrainingArguments(
        output_dir=CFG["output_dir"],
        num_train_epochs=CFG["num_epochs"],
        learning_rate=CFG["learning_rate"],
        per_device_train_batch_size=CFG["batch_size"],
        gradient_accumulation_steps=CFG["gradient_accumulation"],
        # ... other args
    ),
    train_dataset=load_distillation_data(CFG["distillation_data"]),
)

# ─── Train ──────────────────────────────────────────────────────────────────
trainer.train()
model.save_pretrained(f"{CFG['output_dir']}/minillm_adapter")
```

### 6.3 Memory Requirements

| Configuration | VRAM | Notes |
|---------------|------|-------|
| Phase 1 QLoRA only | ~6-8 GB | Base case |
| Phase 2 MiniLLM (no teacher cache) | ~8-10 GB | Student generation on-policy |
| Phase 2 MiniLLM (with teacher cache) | ~10-12 GB | Store teacher distributions |

**Feasibility:** ✅ RTX 4090 (24GB) easily handles Phase 2

---

## 7. Timeline and Decision Gates

### 7.1 Recommended Timeline

```
Week 1-2: Phase 1 QLoRA Baseline
  └── Complete supervised fine-tuning
  └── Establish evaluation metrics
  └── Deploy and test baseline model
  └── DECISION GATE 1: Is baseline quality acceptable?
      └── NO → Iterate on Phase 1 (data quality, hyperparams)
      └── YES → Proceed to Phase 2

Week 3: Phase 2 Preparation
  └── Implement teacher data generation pipeline
  └── Generate 500-example pilot dataset (Haiku)
  └── Implement MiniLLM trainer (custom)
  └── DECISION GATE 2: Does pilot show improvement?
      └── NO → Analyze failure mode, adjust approach
      └── YES → Scale to full dataset

Week 4: Phase 2 Training
  └── Generate 1,500-example full dataset (Sonnet)
  └── Run MiniLLM distillation training
  └── Evaluate against Phase 1 baseline
  └── DECISION GATE 3: Is Phase 2 better than Phase 1?
      └── NO → Consider hybrid or stick with Phase 1
      └── YES → Deploy Phase 2 model

Month 2+: Iteration
  └── Collect user feedback
  └── Generate additional distillation data as needed
  └── Fine-tune specific capabilities
```

### 7.2 Success Criteria

| Metric | Phase 1 Target | Phase 2 Improvement |
|--------|---------------|---------------------|
| Response quality (human eval) | Baseline | +10-15% preference for Phase 2 |
| Calibration (confidence vs accuracy) | Baseline | Better calibrated |
| Hallucination rate | Baseline | -20% or more |
| Task completion rate | Baseline | +5-10% |

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Claude API costs exceed budget** | Medium | High | Start with Haiku; cache responses; use 500-example pilot first |
| **MiniLLM trainer implementation bugs** | High | High | Start from TRL GKDTrainer; extensive testing on pilot |
| **Phase 2 worse than Phase 1** | Medium | Medium | A/B evaluation; keep Phase 1 as fallback |
| **Teacher-mixed sampling complexity** | Medium | Medium | Simplify to pure on-policy if needed |
| **Catastrophic forgetting** | Medium | High | Include LM loss on pre-training corpus; use lower LR |
| **API rate limits during generation** | Medium | Medium | Implement retries, backoff; batch requests |
| **Long training time** | Medium | Medium | On-policy generation is slow; budget 2-3x Phase 1 time |

---

## 9. Comparison with Alternatives

### 9.1 MiniLLM vs Standard KD

| Aspect | Standard KD (Forward KL) | MiniLLM (Reverse KL) |
|--------|--------------------------|----------------------|
| Objective | `KL[p\|\|q]` | `KL[q\|\|p]` |
| Behavior | Mode-covering | Mode-seeking |
| Hallucinations | More likely | Less likely |
| Calibration | Worse | Better |
| Diversity | Artificially high | Natural |
| Implementation | Simple (cross-entropy) | Complex (policy gradient) |
| Training speed | Fast | Slower (on-policy) |

### 9.2 MiniLLM vs Direct SFT on Teacher Outputs

| Aspect | SFT on Teacher | MiniLLM |
|--------|---------------|---------|
| Teacher signal | Hard targets (samples) | Soft targets (distribution) |
| Knowledge transfer | Partial (one sample) | Full (whole distribution) |
| Calibration | Poor | Better |
| Training | Simple supervised | Complex policy gradient |
| **Recommendation** | Baseline approach | Advanced approach |

### 9.3 When to Use MiniLLM

✅ **Use MiniLLM when:**
- High-quality teacher available (Claude, GPT-4)
- Student has limited capacity vs teacher (7B vs 70B+)
- Hallucination reduction is priority
- Calibration matters for the application

❌ **Don't use MiniLLM when:**
- Teacher is only marginally better than student
- Training time is critical constraint
- Simple SFT on teacher outputs is sufficient

---

## 10. Files to Create

```
projects/own_model/
├── MINILLM_PLAN.md              # This document
├── generate_distillation_data.py # Teacher data generation
├── train_minillm.py             # Phase 2 training script
├── minillm_trainer.py           # Custom MiniLLM trainer
├── requirements_minillm.txt     # Additional dependencies
└── configs/
    └── minillm_7b.json          # Hyperparameter config
```

---

## 11. References

| Resource | URL |
|----------|-----|
| **MiniLLM Paper** | https://arxiv.org/abs/2306.08543 |
| **MiniLLM Code** | https://github.com/microsoft/LMOps/tree/main/minillm |
| **TRL GKDTrainer** | https://huggingface.co/docs/trl/gkd_trainer |
| **Forward vs Reverse KL** | https://zhuanlan.zhihu.com/p/xxx (Chinese analysis) |
| **Claude API Docs** | https://docs.anthropic.com/claude/reference |

---

## Summary

**Bottom Line:** MiniLLM reverse-KL distillation is a powerful technique for transferring Claude's capabilities to Otto's 7B Qwen model. It addresses key limitations of standard distillation (hallucinations, poor calibration) through mode-seeking behavior.

**Key Constraints:**
1. Requires custom implementation (Claude API can't be loaded as HF model)
2. On-policy training is slower than standard SFT
3. Claude API costs ~$12 for full dataset generation

**Immediate Action:** 
- Complete Phase 1 QLoRA baseline first
- Implement pilot (500 examples) to validate approach
- Scale to full dataset only if pilot shows improvement

**Expected Outcome:** 10-15% improvement in response quality, better calibration, reduced hallucinations compared to Phase 1 baseline.

---

*Document Version: 1.0*  
*Next Review: After Phase 1 baseline training completes*
