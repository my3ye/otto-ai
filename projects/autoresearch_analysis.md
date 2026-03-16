# AutoResearch Analysis + Otto System Improvements
*Analyzed: 2026-03-16 | Source: github.com/karpathy/autoresearch*

---

## What autoresearch is

A minimal agentic self-improvement loop for ML research:
- **One file to modify** (`train.py`) — limits scope, keeps diffs reviewable
- **Fixed time budget** (5 min/experiment) — makes results comparable
- **Metric-driven decisions** (`val_bpb`, lower=better) — no subjectivity in keep/discard
- **Git as checkpoint** — reset on failure, advance on success
- **Infinite autonomous loop** — never ask human to continue
- **`program.md` = research org code** — human-editable config governing agent behavior
- **Results TSV** — structured log of every experiment with outcome

## Key patterns extracted

| autoresearch concept | Otto equivalent | Implementation |
|---|---|---|
| `program.md` = research org code | `heartbeat.md` + `reflection.md` | Now explicitly iterated via AutoEvolve |
| `train.py` = single mutable file | One system file per experiment | Enforced: one experiment at a time |
| `val_bpb` metric | RL2F accuracy (7d) | `accuracy_7d` now in `/rl2f/stats` |
| results.tsv | `autoevolve_experiments` table | NEW: implemented |
| keep/discard loop | git checkpoint + metric delta | Encoded in reflection.md §7c |
| Fixed time budget | N=10 evaluation cycles | ~5 hours per experiment |
| Generation counter | `autoevolve_generation` table | NEW: implemented |

## Core insight

The outer loop discipline:
> Don't just fix bugs. Run structured experiments. Every change is a hypothesis. Every hypothesis is tested against a metric. Every metric drives a keep/discard decision. Log everything.

Otto already had RL2F, MARS, procedures. What was missing: the metric-driven outer experiment loop.

## What was implemented

1. **Migration 046_autoevolve.sql** — `autoevolve_experiments` + `autoevolve_generation` tables
2. **`/autoevolve/*` API** — insights, experiment CRUD, tick, generation counter
3. **`reflection.md` §7c** — AutoEvolve loop: check active → tick → evaluate → new hypothesis
4. **`/rl2f/stats` enhancement** — added `accuracy_7d` field

## Additional learnings

### Simplicity criterion (from autoresearch)
"A 0.001 improvement with 20 lines of hacky code? Not worth it." Otto's self-patch had no simplicity criterion. AutoEvolve's keep/discard rules now include: equal metric + simpler code = KEEP.

### Single file at a time
autoresearch never modifies multiple files simultaneously. This is the right discipline — impossible to isolate causation otherwise. AutoEvolve enforces this.

### The generation counter matters
Knowing you're on "Generation 47" creates compounding progress momentum. `/autoevolve/generation` provides this for Otto.

## Files changed

- `memory/migrations/046_autoevolve.sql` — NEW
- `memory/routes/autoevolve.py` — NEW
- `memory/api.py` — registered autoevolve route
- `memory/routes/rl2f.py` — added accuracy_7d to stats
- `.claude/agents/reflection.md` — added Section 7c AutoEvolve loop
