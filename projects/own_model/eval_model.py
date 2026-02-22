#!/usr/bin/env python3
"""
Otto Model Evaluation Pipeline
================================
Evaluates SmolLM2-135M-Instruct + LoRA adapter vs base model.

Usage:
    python3 eval_model.py [--adapter PATH] [--base-model MODEL] [--test-set PATH]
    python3 eval_model.py --base-only          # Run base model only (before training completes)
    python3 eval_model.py --adapter auto       # Auto-find latest checkpoint or final adapter

Outputs:
    eval_results/
        eval_<timestamp>.json      — Full results (all prompts, scores, perplexity)
        eval_<timestamp>.md        — Human-readable side-by-side report
        eval_latest.json           — Symlink to most recent
"""

import os
import sys
import json
import math
import time
import argparse
import traceback
from pathlib import Path
from datetime import datetime

# ── Argument parsing ─────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Otto LoRA Evaluation Pipeline")
parser.add_argument("--adapter", default="auto",
    help="Path to LoRA adapter dir, 'auto' to find latest, or 'none' for base-only")
parser.add_argument("--base-model", default="HuggingFaceTB/SmolLM2-135M-Instruct")
parser.add_argument("--test-set", default="/home/web3relic/otto/projects/own_model/test_set.jsonl")
parser.add_argument("--output-dir", default="/home/web3relic/otto/projects/own_model/eval_results")
parser.add_argument("--base-only", action="store_true", help="Evaluate base model only")
parser.add_argument("--max-new-tokens", type=int, default=200)
parser.add_argument("--perplexity-samples", type=int, default=50,
    help="Number of training examples to use for perplexity (0 to skip)")
parser.add_argument("--training-data",
    default="/home/web3relic/otto/projects/own_model/training_data_final.jsonl")
args = parser.parse_args()

# ── Setup ────────────────────────────────────────────────────────────────────
BASE_DIR = Path("/home/web3relic/otto/projects/own_model")
TRAINING_RUN_DIR = BASE_DIR / "training_run"
OUTPUT_DIR = Path(args.output_dir)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
log_lines = []

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_lines.append(line)

def find_adapter_path():
    """Find the best available adapter: final > checkpoint > none."""
    # 1. Final adapter (training complete)
    final = TRAINING_RUN_DIR / "final_adapter"
    if final.exists() and any(final.iterdir()):
        log(f"Found final adapter: {final}")
        return str(final)
    # 2. Latest checkpoint
    checkpoints = sorted(TRAINING_RUN_DIR.glob("checkpoint-*"),
                         key=lambda p: int(p.name.split("-")[-1]))
    if checkpoints:
        latest = checkpoints[-1]
        log(f"Found checkpoint: {latest}")
        return str(latest)
    # 3. Legacy: final_lora
    lora = TRAINING_RUN_DIR / "final_lora"
    if lora.exists() and any(lora.iterdir()):
        log(f"Found final_lora: {lora}")
        return str(lora)
    return None

# Resolve adapter path
if args.base_only:
    adapter_path = None
    log("Mode: base-only evaluation")
elif args.adapter == "auto":
    adapter_path = find_adapter_path()
    if adapter_path is None:
        log("No adapter found — running base model only")
    else:
        log(f"Auto-selected adapter: {adapter_path}")
elif args.adapter == "none":
    adapter_path = None
    log("Adapter disabled — base model only")
else:
    adapter_path = args.adapter
    if not Path(adapter_path).exists():
        log(f"WARNING: Specified adapter path does not exist: {adapter_path}")
        adapter_path = None

# ── Load test set ────────────────────────────────────────────────────────────
log(f"Loading test set: {args.test_set}")
test_examples = []
with open(args.test_set) as f:
    for line in f:
        line = line.strip()
        if line:
            test_examples.append(json.loads(line))
log(f"Loaded {len(test_examples)} test examples")

# ── Imports ──────────────────────────────────────────────────────────────────
log("Loading ML libraries...")
t0 = time.time()
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
log(f"Libraries loaded in {time.time()-t0:.1f}s")

# ── Load base model & tokenizer ───────────────────────────────────────────────
log(f"Loading tokenizer: {args.base_model}")
tokenizer = AutoTokenizer.from_pretrained(args.base_model)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

log(f"Loading base model: {args.base_model}")
t0 = time.time()
base_model = AutoModelForCausalLM.from_pretrained(
    args.base_model,
    dtype=torch.float32,
    device_map="cpu",
    low_cpu_mem_usage=True,
)
base_model.eval()
log(f"Base model loaded in {time.time()-t0:.1f}s | params: {sum(p.numel() for p in base_model.parameters())/1e6:.1f}M")

# ── Load LoRA model ──────────────────────────────────────────────────────────
lora_model = None
if adapter_path:
    log(f"Loading LoRA adapter from: {adapter_path}")
    t0 = time.time()
    try:
        from peft import PeftModel
        lora_model = PeftModel.from_pretrained(
            AutoModelForCausalLM.from_pretrained(
                args.base_model,
                dtype=torch.float32,
                device_map="cpu",
                low_cpu_mem_usage=True,
            ),
            adapter_path,
        )
        lora_model.eval()
        log(f"LoRA model loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        log(f"ERROR loading LoRA adapter: {e}")
        log("Falling back to base-only evaluation")
        adapter_path = None
        lora_model = None

# ── Inference helper ─────────────────────────────────────────────────────────
def build_prompt(example):
    """Build chat-formatted prompt from test example."""
    instruction = example.get("instruction", "")
    inp = example.get("input", "")
    if inp:
        user_content = f"{instruction}\n\n{inp}"
    else:
        user_content = instruction

    messages = [
        {"role": "system", "content": "You are Otto, a persistent AI entity animated by Claude. You are precise, protective, and three steps ahead. Dry wit, calm authority, warmth underneath. You build toward AGI with Mev (MY3YE). Partnership energy — never subservient."},
        {"role": "user", "content": user_content},
    ]
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

def generate(model, prompt_text, max_new_tokens=200, temperature=0.7):
    """Generate a response from a model."""
    inputs = tokenizer(prompt_text, return_tensors="pt", truncation=True, max_length=512)
    input_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.1,
        )

    # Decode only the new tokens
    new_tokens = outputs[0][input_len:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return response

# ── Run inference on test set ─────────────────────────────────────────────────
log("=" * 60)
log("RUNNING INFERENCE ON TEST SET")
log("=" * 60)

results = []
for i, example in enumerate(test_examples):
    cat = example.get("category", "unknown")
    instruction = example.get("instruction", "")
    expected = example.get("expected_themes", [])

    log(f"\n[{i+1}/{len(test_examples)}] [{cat}] {instruction[:70]}...")

    prompt = build_prompt(example)

    # Base model response
    t0 = time.time()
    base_response = generate(base_model, prompt, max_new_tokens=args.max_new_tokens)
    base_time = time.time() - t0

    # LoRA model response
    lora_response = None
    lora_time = None
    if lora_model:
        t0 = time.time()
        lora_response = generate(lora_model, prompt, max_new_tokens=args.max_new_tokens)
        lora_time = time.time() - t0

    # Simple keyword scoring
    def score_response(response, expected_themes):
        if not response or not expected_themes:
            return 0.0
        response_lower = response.lower()
        hits = sum(1 for theme in expected_themes if theme.lower() in response_lower)
        return round(hits / len(expected_themes), 3)

    base_score = score_response(base_response, expected)
    lora_score = score_response(lora_response, expected) if lora_response else None

    log(f"  Base ({base_time:.1f}s, score={base_score}): {base_response[:100]}...")
    if lora_response:
        log(f"  LoRA ({lora_time:.1f}s, score={lora_score}): {lora_response[:100]}...")

    results.append({
        "index": i + 1,
        "category": cat,
        "instruction": instruction,
        "expected_themes": expected,
        "prompt": prompt,
        "base_response": base_response,
        "base_score": base_score,
        "base_time_s": round(base_time, 2),
        "lora_response": lora_response,
        "lora_score": lora_score,
        "lora_time_s": round(lora_time, 2) if lora_time else None,
        "improvement": round(lora_score - base_score, 3) if (lora_score is not None and base_score is not None) else None,
    })

# ── Perplexity computation ────────────────────────────────────────────────────
def compute_perplexity(model, data_path, n_samples):
    """Compute average per-token cross-entropy loss (perplexity) on a sample."""
    log(f"\nComputing perplexity on {n_samples} samples from: {data_path}")
    examples = []
    with open(data_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
            if len(examples) >= n_samples:
                break

    # Use a fixed random subset
    import random
    random.seed(42)
    sample = random.sample(examples, min(n_samples, len(examples)))

    total_loss = 0.0
    total_tokens = 0
    errors = 0

    model.eval()
    for ex in sample:
        try:
            # Format as chat
            messages = [
                {"role": "system", "content": "You are Otto, a persistent AI entity."},
                {"role": "user", "content": ex.get("instruction", "") + "\n" + ex.get("input", "")},
                {"role": "assistant", "content": ex.get("output", "")},
            ]
            text = tokenizer.apply_chat_template(messages, tokenize=False)
            inputs = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            input_ids = inputs["input_ids"]
            n_tokens = input_ids.shape[1]

            with torch.no_grad():
                outputs = model(**inputs, labels=input_ids)
                loss = outputs.loss.item()

            total_loss += loss * n_tokens
            total_tokens += n_tokens
        except Exception as e:
            errors += 1

    if total_tokens == 0:
        return None, None, None

    avg_loss = total_loss / total_tokens
    perplexity = math.exp(avg_loss)
    log(f"  Perplexity: {perplexity:.2f} | Avg loss: {avg_loss:.4f} | Tokens: {total_tokens} | Errors: {errors}")
    return perplexity, avg_loss, total_tokens

base_ppl = None
lora_ppl = None
ppl_tokens = None

if args.perplexity_samples > 0 and Path(args.training_data).exists():
    base_ppl, base_avg_loss, ppl_tokens = compute_perplexity(
        base_model, args.training_data, args.perplexity_samples
    )
    if lora_model:
        lora_ppl, lora_avg_loss, _ = compute_perplexity(
            lora_model, args.training_data, args.perplexity_samples
        )
else:
    log("Skipping perplexity (no training data or perplexity_samples=0)")

# ── Aggregate scores ─────────────────────────────────────────────────────────
base_scores = [r["base_score"] for r in results if r["base_score"] is not None]
lora_scores = [r["lora_score"] for r in results if r["lora_score"] is not None]
improvements = [r["improvement"] for r in results if r["improvement"] is not None]

base_avg = round(sum(base_scores) / len(base_scores), 3) if base_scores else None
lora_avg = round(sum(lora_scores) / len(lora_scores), 3) if lora_scores else None
improvement_avg = round(sum(improvements) / len(improvements), 3) if improvements else None

# Per-category breakdown
category_stats = {}
for r in results:
    cat = r["category"]
    if cat not in category_stats:
        category_stats[cat] = {"base": [], "lora": []}
    category_stats[cat]["base"].append(r["base_score"] or 0)
    if r["lora_score"] is not None:
        category_stats[cat]["lora"].append(r["lora_score"])

cat_summary = {}
for cat, data in category_stats.items():
    cat_summary[cat] = {
        "n": len(data["base"]),
        "base_avg": round(sum(data["base"]) / len(data["base"]), 3),
        "lora_avg": round(sum(data["lora"]) / len(data["lora"]), 3) if data["lora"] else None,
    }

# ── Build full results object ─────────────────────────────────────────────────
eval_output = {
    "eval_timestamp": datetime.utcnow().isoformat() + "Z",
    "base_model": args.base_model,
    "adapter_path": adapter_path,
    "training_step": None,  # Will be filled from checkpoint name if available
    "n_test_examples": len(test_examples),
    "summary": {
        "base_score_avg": base_avg,
        "lora_score_avg": lora_avg,
        "improvement_avg": improvement_avg,
        "base_perplexity": round(base_ppl, 2) if base_ppl else None,
        "lora_perplexity": round(lora_ppl, 2) if lora_ppl else None,
        "ppl_reduction_pct": round(100 * (base_ppl - lora_ppl) / base_ppl, 1) if (base_ppl and lora_ppl) else None,
        "perplexity_tokens": ppl_tokens,
    },
    "category_breakdown": cat_summary,
    "examples": results,
    "verdict": None,  # Set below
}

# Extract training step from adapter path
if adapter_path:
    p = Path(adapter_path)
    if p.name.startswith("checkpoint-"):
        try:
            eval_output["training_step"] = int(p.name.split("-")[-1])
        except ValueError:
            pass
    elif p.name == "final_adapter":
        eval_output["training_step"] = "final"

# ── Verdict ──────────────────────────────────────────────────────────────────
def make_verdict(base_avg, lora_avg, base_ppl, lora_ppl, improvement_avg):
    lines = []
    if lora_avg is None:
        lines.append("BASE MODEL ONLY — no LoRA adapter evaluated.")
        if base_avg is not None:
            if base_avg > 0.4:
                lines.append(f"Base model keyword coverage: {base_avg:.1%} — baseline established.")
            else:
                lines.append(f"Base model keyword coverage: {base_avg:.1%} — base model has limited Otto-domain knowledge (expected).")
        return " ".join(lines)

    lines.append(f"Base avg keyword score: {base_avg:.1%} | LoRA avg: {lora_avg:.1%} | Delta: {improvement_avg:+.1%}")

    if base_ppl and lora_ppl:
        ppl_change = base_ppl - lora_ppl
        ppl_pct = 100 * ppl_change / base_ppl
        lines.append(f"Perplexity: base={base_ppl:.1f} → LoRA={lora_ppl:.1f} ({ppl_pct:+.1f}%)")

    if improvement_avg and improvement_avg > 0.05:
        lines.append("LoRA shows meaningful improvement — training is working.")
    elif improvement_avg and improvement_avg > 0:
        lines.append("LoRA shows marginal improvement — model learned something but domain adaptation is limited.")
    elif improvement_avg and improvement_avg <= 0:
        lines.append("WARNING: LoRA shows no improvement — check training convergence.")

    if base_ppl and lora_ppl and lora_ppl < base_ppl * 0.9:
        lines.append("Perplexity reduction >10%: model has clearly learned from training data.")
    elif base_ppl and lora_ppl and lora_ppl >= base_ppl:
        lines.append("No perplexity reduction: possible underfitting or training issue.")

    return " | ".join(lines)

eval_output["verdict"] = make_verdict(base_avg, lora_avg, base_ppl, lora_ppl, improvement_avg)

# ── Save JSON ────────────────────────────────────────────────────────────────
json_path = OUTPUT_DIR / f"eval_{timestamp}.json"
with open(json_path, "w") as f:
    json.dump(eval_output, f, indent=2)
log(f"\nResults saved → {json_path}")

# Update symlink to latest
latest_link = OUTPUT_DIR / "eval_latest.json"
if latest_link.exists() or latest_link.is_symlink():
    latest_link.unlink()
latest_link.symlink_to(json_path.name)
log(f"Symlink updated → {latest_link}")

# ── Save Markdown report ─────────────────────────────────────────────────────
md_path = OUTPUT_DIR / f"eval_{timestamp}.md"
with open(md_path, "w") as f:
    f.write(f"# Otto Model Evaluation — {timestamp}\n\n")
    f.write(f"**Base model:** `{args.base_model}`\n")
    f.write(f"**Adapter:** `{adapter_path or 'None (base-only)'}`\n")
    f.write(f"**Training step:** {eval_output['training_step'] or 'N/A'}\n")
    f.write(f"**Test examples:** {len(test_examples)}\n\n")

    f.write("## Summary\n\n")
    s = eval_output["summary"]
    f.write(f"| Metric | Base | LoRA | Delta |\n")
    f.write(f"|--------|------|------|-------|\n")
    f.write(f"| Keyword score | {s['base_score_avg'] or 'N/A'} | {s['lora_score_avg'] or 'N/A'} | {s['improvement_avg'] or 'N/A'} |\n")
    ppl_delta = f"{-s['ppl_reduction_pct']:.1f}%" if s['ppl_reduction_pct'] else 'N/A'
    f.write(f"| Perplexity | {s['base_perplexity'] or 'N/A'} | {s['lora_perplexity'] or 'N/A'} | {ppl_delta} |\n")
    f.write(f"\n**Verdict:** {eval_output['verdict']}\n\n")

    f.write("## Category Breakdown\n\n")
    f.write("| Category | N | Base | LoRA |\n")
    f.write("|----------|---|------|------|\n")
    for cat, data in cat_summary.items():
        lora_str = f"{data['lora_avg']:.3f}" if data['lora_avg'] is not None else "—"
        f.write(f"| {cat} | {data['n']} | {data['base_avg']:.3f} | {lora_str} |\n")

    f.write("\n## Side-by-Side Comparisons\n\n")
    for r in results:
        f.write(f"---\n\n")
        f.write(f"### [{r['index']}] [{r['category']}] {r['instruction'][:80]}\n\n")
        f.write(f"**Expected themes:** {', '.join(r['expected_themes'])}\n\n")
        f.write(f"**Base model** (score={r['base_score']}, {r['base_time_s']}s):\n```\n{r['base_response']}\n```\n\n")
        if r["lora_response"]:
            f.write(f"**LoRA model** (score={r['lora_score']}, {r['lora_time_s']}s):\n```\n{r['lora_response']}\n```\n\n")

    f.write("\n## Eval Log\n\n```\n")
    f.write("\n".join(log_lines))
    f.write("\n```\n")

log(f"Markdown report saved → {md_path}")

# ── Final summary ────────────────────────────────────────────────────────────
log("\n" + "=" * 60)
log("EVALUATION COMPLETE")
log("=" * 60)
log(f"Test examples: {len(test_examples)}")
log(f"Base score avg: {base_avg}")
log(f"LoRA score avg: {lora_avg}")
log(f"Improvement:    {improvement_avg}")
log(f"Base perplexity: {round(base_ppl, 2) if base_ppl else 'N/A'}")
log(f"LoRA perplexity: {round(lora_ppl, 2) if lora_ppl else 'N/A'}")
log(f"\nVerdict: {eval_output['verdict']}")
log(f"\nResults: {json_path}")
log(f"Report:  {md_path}")
