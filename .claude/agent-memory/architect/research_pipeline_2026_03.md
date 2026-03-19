---
name: research_pipeline_design_2026_03
description: Architecture decision for the multi-agent research pipeline: 5-step workflow with research-synthesizer as the key new agent
type: project
---

## Research Pipeline Architecture (2026-03-19)

Designed a 5-step multi-agent research pipeline to replace ad-hoc single researcher tasks.

**Pipeline:** researcher (retrieval) → research-synthesizer (synthesis) → reviewer (validation) → researcher (storage) → notify

**Template ID:** c4abc114-dffe-446d-ae3f-42ea40820ad4 (name: research-pipeline)

**New agent created:** `research-synthesizer.md` — synthesis-only, strict 2000-token output format, confidence scoring (HIGH/MEDIUM/LOW based on source count)

**Key design decisions:**
- Reuse `reviewer` for validation (adversarial analysis is exactly what validation needs)
- Reuse `researcher` for storage step (already has memory API access)
- Only one new agent justified (research-synthesizer) — synthesis genuinely differs from retrieval
- Output compression enforced at each boundary (≤3000 tokens retrieval, ≤2000 synthesis)
- Total cost: ~$6 standard / ~$10 deep

**Architecture doc:** ~/otto/docs/research-pipeline-architecture-2026-03-19.md

**Why:** The existing `researcher` agent ran retrieval, synthesis, validation, and storage in one shot — losing-in-middle problem, no adversarial validation, no systematic memory persistence.

**How to apply:** When Mev or orchestrator wants a research task on any topic, use `research-pipeline` workflow instead of single researcher task for anything that needs validated, persistent findings.
