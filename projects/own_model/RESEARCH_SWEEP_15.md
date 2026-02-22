# Research Sweep #15: Continual Learning + Test-Time Training

**Date:** 2026-02-22  
**Papers Found:** 12 new papers (not in previous 81)  
**Focus Areas:** Continual/lifelong learning, Test-time training (TTT), Self-improvement, Memory-augmented networks, Efficient inference

---

## Summary

This sweep identified **12 new papers** from Jan-Feb 2026 relevant to Otto's continuously learning model architecture (Qwen2.5-7B + QLoRA). Key trends:

1. **Training-free continual learning** is emerging as a practical path - JitRL shows 30x cost reduction vs traditional RL
2. **Test-time training** is maturing with curriculum synthesis (TTCS) and end-to-end formulations (TTT-E2E)
3. **Memory systems** are focusing on query-aware indexing (SwiftMem) and recurrent state updates (LLM-as-RNN)
4. **Inference efficiency** remains critical - Extra-CoT achieves 73% token reduction in CoT reasoning

---

## Paper Analysis

### 1. JitRL: Just-In-Time Reinforcement Learning
- **arXiv ID:** 2601.18510
- **Date:** Jan 26, 2026
- **Key Insight:** Training-free framework enabling test-time policy optimization without gradient updates. Maintains dynamic non-parametric memory of <state, action, reward> triplets and retrieves relevant trajectories to estimate action advantages on-the-fly. Additive logit update is the closed-form solution to KL-constrained policy optimization.
- **Relevance to Otto:** 5/5 - Directly enables continual learning without expensive fine-tuning, perfect for Otto's 7B model
- **Implementation Complexity:** Medium - Requires memory bank infrastructure and advantage estimation logic
- **Why it matters:** Outperforms WebRL while reducing costs by 30x; achieves 60% success rate on WebArena-Lite vs 46% for WebRL

### 2. TTT-Discover: Learning to Discover at Test Time
- **arXiv ID:** 2601.16175
- **Date:** Jan 22, 2026
- **Key Insight:** Performs reinforcement learning at test time with experience specific to the test problem. Co-evolving synthesizer and solver policies - synthesizer generates progressively challenging question variants creating a curriculum, while solver updates using self-consistency rewards.
- **Relevance to Otto:** 4/5 - Excellent for discovery and research tasks; sets SOTA on math, GPU kernel engineering, and biology problems
- **Implementation Complexity:** High - Requires dual-policy architecture and curriculum generation
- **Why it matters:** Achieved 2x faster GPU kernels than prior art; uses open models (gpt-oss-120b) vs closed frontier models

### 3. TTCS: Test-Time Curriculum Synthesis
- **arXiv ID:** 2601.22628
- **Date:** Jan 30, 2026
- **Key Insight:** Addresses difficult reasoning problems where raw test questions yield low-quality pseudo-labels. Initializes question synthesizer and reasoning solver from same pretrained model; policies co-evolve through iterative optimization. Solver feedback guides synthesizer to generate questions aligned with current capability.
- **Relevance to Otto:** 5/5 - Self-evolving curriculum generation without human labels - exactly what Otto needs for autonomous improvement
- **Implementation Complexity:** Medium-High - Requires two-policy setup and self-consistency reward mechanism
- **Why it matters:** Consistently strengthens reasoning on math benchmarks and transfers to general-domain tasks

### 4. TTT-E2E: End-to-End Test-Time Training for Long Context
- **arXiv ID:** 2512.23675
- **Date:** Dec 29, 2025 (published Jan 2026)
- **Key Insight:** Reframes long-context language modeling as continual learning. Uses sliding-window attention as "working memory" and designated MLP layers as mutable "long-term memory". Meta-learning at training time optimizes the model's initialization for learning at test time.
- **Relevance to Otto:** 4/5 - Enables compressed memory of context into weights; 2.7x faster than full attention at 128K context
- **Implementation Complexity:** High - Requires architectural modifications and meta-learning training
- **Why it matters:** Scales with context length like full attention but with RNN-like constant inference latency

### 5. LLM-as-RNN: Recurrent Language Model for Memory Updates
- **arXiv ID:** 2601.13352
- **Date:** Jan 19, 2026
- **Key Insight:** Turns frozen LLM into recurrent predictor by representing hidden state as natural-language memory. Structured system-prompt summary updated at each timestep via feedback-driven text rewrites. Enables online learning without parameter updates under fixed token budget.
- **Relevance to Otto:** 4/5 - Inference-only adaptation through textual state; 6.5% avg improvement across healthcare, weather, finance
- **Implementation Complexity:** Low-Medium - Pure prompt-based approach requiring feedback mechanism
- **Why it matters:** Corrects errors and retains task-relevant patterns without gradient updates; produces interpretable learning traces

### 6. SwiftMem: Fast Agentic Memory via Query-aware Indexing
- **arXiv ID:** 2601.08160
- **Date:** Jan 13, 2026
- **Key Insight:** Query-aware memory system achieving sub-linear retrieval through temporal and semantic indexing. Temporal index enables O(log N) range queries; semantic DAG-Tag index maps queries via hierarchical tag structures. Embedding-tag co-consolidation improves cache locality.
- **Relevance to Otto:** 5/5 - Critical infrastructure for Otto's memory system; 47x faster search than SOTA baselines
- **Implementation Complexity:** Medium - Requires index infrastructure and tag generation
- **Why it matters:** Maintains sub-15ms search latency across varying conversation lengths; enables practical deployment of memory-augmented agents

### 7. Extra-CoT: Extreme-Ratio Chain-of-Thought Compression
- **arXiv ID:** 2602.08324
- **Date:** Feb 9, 2026
- **Key Insight:** Aggressively reduces token budget while preserving answer accuracy through semantically-preserved compression. Trains dedicated compressor on mathematical CoT data with fine-grained annotations, then fine-tunes LLM via mixed-ratio SFT for variable compression budgets.
- **Relevance to Otto:** 3/5 - Reduces inference costs; 73% token reduction on MATH-500 with Qwen3-1.7B
- **Implementation Complexity:** Medium - Requires compressor training and multi-ratio SFT
- **Why it matters:** Enables fast reasoning at extreme compression ratios without accuracy loss

### 8. ORBIT: Scaling In-Context Online Learning
- **arXiv ID:** 2602.04089
- **Date:** Feb 3, 2026
- **Key Insight:** Multi-task, multi-episode meta-RL framework training LLMs to learn from interaction in context. Meta-trained model (Qwen3-14B) demonstrates improved in-context online learning on unseen environments, matching GPT-5.2 performance.
- **Relevance to Otto:** 4/5 - Learn-at-inference-time capability for decision-making agents
- **Implementation Complexity:** High - Requires meta-RL training infrastructure
- **Why it matters:** Addresses online decision-making where feedback is delayed and information must be acquired through interaction

### 9. GLP: Generative Latent Prior for LLM Activations
- **arXiv ID:** 2602.06964
- **Date:** Feb 6, 2026
- **Key Insight:** Trains diffusion models on residual stream activations creating "meta-models" that learn distribution of network's internal states. Provides learned prior for steering interventions, improving fluency while maintaining concept strength.
- **Relevance to Otto:** 3/5 - Advanced interpretability and activation steering; scales predictably with compute
- **Implementation Complexity:** High - Requires training diffusion models on activations
- **Why it matters:** Offers scalable path toward interpretability without restrictive structural assumptions

### 10. Test-Time Training for Long-Context LLMs
- **arXiv ID:** 2512.13898
- **Date:** Dec 15, 2025
- **Key Insight:** Shows inference-time strategies have rapidly diminishing returns for long context. Attributes failures to "score dilution" inherent to static self-attention. Proposes targeted gradient updates on context to overcome limitations.
- **Relevance to Otto:** 4/5 - 12.6 and 14.1 percentage point improvements for Qwen3-4B on LongBench-v2 and ZeroScrolls
- **Implementation Complexity:** Medium - Requires gradient computation at test time
- **Why it matters:** Small amount of context-specific training better use of inference compute than generating more thinking tokens

### 11. Continuous Low-Rank Decomposed Scaling (LoRA-CL)
- **arXiv ID:** 2601.22716
- **Date:** Jan 2026
- **Key Insight:** Unified parameter-efficient continual learning framework combining low-rank decomposition with continuous scaling. Addresses catastrophic forgetting through gradient projection and importance-weighted parameter updates.
- **Relevance to Otto:** 4/5 - Directly applicable to Otto's QLoRA-based architecture
- **Implementation Complexity:** Medium - Extends existing LoRA infrastructure
- **Why it matters:** Provides principled approach to continual fine-tuning without full model retraining

### 12. In-Place Test-Time Training (In-Place TTT)
- **arXiv ID:** ICLR 2026 submission
- **Date:** Jan 2026
- **Key Insight:** Treats final projection matrix of MLP blocks as adaptable fast weights for "drop-in" TTT enhancement. Replaces generic reconstruction objective with theoretically-grounded objective aligned with next-token prediction. Efficient chunk-wise update mechanism compatible with context parallelism.
- **Relevance to Otto:** 5/5 - Enables 4B model to handle 128K contexts; no costly retraining from scratch
- **Implementation Complexity:** Medium - Requires architectural modifications to existing transformers
- **Why it matters:** First practical TTT framework for existing LLMs without architectural redesign

---

## Top 3 Papers for Immediate Implementation

### #1: JitRL (2601.18510) - Priority: HIGHEST
**Why first:** Training-free continual learning with proven 30x cost reduction. Otto can implement this immediately without modifying the base model.

**Implementation path:**
1. Build memory bank storing <state, action, reward> triplets
2. Implement state abstraction function (compress HTML/text to structured state)
3. Add advantage estimation via retrieval from memory neighbors
4. Apply additive logit update: z' = z + β·A
5. Use self-reflective LLM evaluator for step-wise credit assignment

**Expected impact:** Enable continuous adaptation to new tasks without fine-tuning costs; 46%→51% success rate improvement demonstrated

### #2: SwiftMem (2601.08160) - Priority: HIGH
**Why second:** Memory infrastructure is foundational. SwiftMem's query-aware indexing solves the scaling bottleneck Otto's memory system will face.

**Implementation path:**
1. Build temporal index with binary-searchable user timelines
2. Implement DAG-Tag index with hierarchical semantic relationships
3. Add LLM-based tag generation for episodes
4. Implement query-tag router with embedding-based alignment
5. Add embedding-tag co-consolidation for cache locality

**Expected impact:** 47x faster memory retrieval; sub-15ms latency regardless of memory size; enables real-time agent interactions

### #3: TTCS (2601.22628) - Priority: HIGH
**Why third:** Self-evolving curriculum synthesis enables Otto to generate its own training data without human intervention - the holy grail of autonomous improvement.

**Implementation path:**
1. Initialize synthesizer and solver policies from same base model
2. Implement question variant generation conditioned on solver capability
3. Add self-consistency reward computation from multiple sampled responses
4. Build iterative optimization loop between synthesizer and solver
5. Integrate with existing QLoRA training pipeline

**Expected impact:** Continuous self-improvement on reasoning tasks without external data; transferable to general-domain tasks

---

## Implementation Roadmap

### Phase 1 (Immediate - 1-2 weeks)
- Implement JitRL's memory bank and advantage estimation
- Deploy SwiftMem's query-aware indexing for existing memory
- A/B test against current static retrieval

### Phase 2 (Short-term - 1 month)
- Integrate TTCS curriculum generation with training pipeline
- Add LLM-as-RNN style recurrent state updates for error correction
- Evaluate TTT-E2E style weight updates for long-context handling

### Phase 3 (Medium-term - 2-3 months)
- Full integration of top 3 methods into unified training loop
- Meta-learning outer loop optimization (ORBIT-style)
- Compress reasoning chains with Extra-CoT for efficiency

---

## Rejected Papers (Already Covered or Lower Priority)

**Already in covered list:** None of the 12 papers overlap with existing 81 papers (TAME, PreFlect, G2CP, AgeMem, A-RAG, BMAM, Focus, MARS, SuRe, SVC, FIT, DELLA, TIES, DARE, MiniLLM, GaLore, VLoRP, DoRA, video-SALMONN, A-Mem, Agent-R, SOFAI-LM, GoalAct, E-mem, OpenSage, DART, Team of Thought, ACuRL, ToolMaker, MAGMA, xMemory, ReMe, APC, MAR, CoM, WAC, FoT, LoRAM, PiSSA, MiLoRA)

**Lower priority for Otto:**
- GLP (2602.06964): Interesting for interpretability but not core to Otto's current goals
- Extra-CoT (2602.08324): Useful for efficiency but less critical than learning capabilities

---

## Key Insights for Otto's Architecture

1. **Training-free continual learning is viable:** JitRL proves we don't need expensive RL fine-tuning for continuous adaptation

2. **Memory indexing matters more than scale:** SwiftMem shows intelligent indexing beats brute-force retrieval by 47x

3. **Self-generated curricula work:** TTCS demonstrates agents can generate their own training data effectively

4. **Test-time compute should go to training, not just generation:** TTT-E2E and Test-Time Training papers show small gradient updates outperform more thinking tokens

5. **Dual-memory architecture is emerging pattern:** Fast context (attention) + compressed weights (MLP updates) appears in multiple papers

---

*Research Sweep #15 complete. 12 new papers identified, 3 prioritized for implementation.*
