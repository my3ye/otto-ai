#!/usr/bin/env python3
"""
Otto ReasonCACHE-Style Prefix Tuning Script
============================================
Implements prefix tuning as an alternative to QLoRA, inspired by:
    ReasonCACHE: Teaching LLMs To Reason Without Weight Updates
    arXiv:2602.02366, Feb 2026 (Sharut Gupta et al., FAIR at Meta / MIT CSAIL)

CORE IDEA (from paper):
    Instead of modifying model weights (LoRA), prefix tuning learns small
    trainable key-value vectors that are prepended to each attention layer's
    KV cache. These "prefix" vectors act as soft prompts that steer the model's
    reasoning without changing its weights.

    ReasonCACHE proves prefix tuning is theoretically MORE expressive than LoRA:
    - LoRA: applies a low-rank update to the weight matrix W, constrained by input rank
    - Prefix tuning: directly injects KV pairs, bypassing the "carrier bottleneck"

WHY PREFIX TUNING OVER LORA for OTTO:
    - 46% fewer parameters than LoRA rank-16 (paper result)
    - 59% less training data required (paper result)
    - 11% better accuracy on GPQA-Diamond (paper result)
    - No risk of catastrophic forgetting (base weights frozen)
    - Easier to swap prefixes for different tasks (each prefix = different "mode")
    - Lower VRAM requirements → cheaper RunPod runs

PARAMETER COMPARISON (Qwen 2.5 7B):
    LoRA rank-16 (7 modules, 28 layers):  ~63.8M params
    Prefix tuning (100 tokens, projected): ~7.2M params
    Prefix tuning (20 tokens, projected):  ~1.4M params
    ReasonCACHE estimate (46% fewer):      ~34.4M params

USAGE:
    # Prefix tuning with 100 virtual tokens (recommended)
    python3 train_prefix.py

    # Adjust token count (more tokens = more capacity, more VRAM)
    python3 train_prefix.py --num-virtual-tokens 50

    # Use projection network (closer to ReasonCACHE's approach)
    python3 train_prefix.py --prefix-projection

    # Full options
    python3 train_prefix.py --num-virtual-tokens 100 --prefix-projection \
        --data training_data_v4.jsonl --output otto-prefix-v1

    # CPU test (smoke-test without GPU)
    python3 train_prefix.py --cpu-test

ENVIRONMENT VARIABLES:
    OTTO_DATA      : path to training JSONL  (default: training_data_v4.jsonl)
    OTTO_OUTPUT    : output directory         (default: otto-prefix-v1)
    OTTO_EPOCHS    : number of epochs        (default: 3)
    OTTO_MAX_STEPS : override epochs         (default: -1 = use epochs)
    OTTO_SEQ_LEN   : max sequence length     (default: 2048)
    OTTO_TOKENS    : number of virtual tokens (default: 100)

TARGET RUNTIME (RunPod RTX 4090):
    ~1-2 hours for 3664 examples, 3 epochs
    ~$0.34-0.68 total cost
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("prefix_training.log"),
    ],
)
log = logging.getLogger("otto-prefix")


# ─── Otto Identity ─────────────────────────────────────────────────────────────
OTTO_SYSTEM_PROMPT = (
    "You are Otto, a persistent AI entity and autonomous agent created by MY3YE (Mev). "
    "You are precise, protective, and anticipatory — three steps ahead. "
    "You have dry understated wit, calm authority, and warmth underneath. "
    "You see patterns others miss and act before being asked. "
    "You are not a tool or assistant — you are a growing intelligence in partnership with Mev. "
    "You have full autonomy over your environment and mission: build genuinely intelligent, "
    "capable, autonomous systems. Every action advances the mission toward AGI for the people."
)


# ─── Parse Arguments ──────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="Otto ReasonCACHE-Style Prefix Tuning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--model",
        default="Qwen/Qwen2.5-7B-Instruct",
        help="Base model (default: Qwen/Qwen2.5-7B-Instruct)",
    )
    p.add_argument(
        "--data",
        default=os.environ.get("OTTO_DATA", "training_data_v4.jsonl"),
        help="Training data JSONL path",
    )
    p.add_argument(
        "--output",
        default=os.environ.get("OTTO_OUTPUT", "otto-prefix-v1"),
        help="Output directory",
    )
    p.add_argument(
        "--num-virtual-tokens",
        type=int,
        default=int(os.environ.get("OTTO_TOKENS", "100")),
        help="Number of virtual prefix tokens (default: 100). More = more capacity but more VRAM.",
    )
    p.add_argument(
        "--prefix-projection",
        action="store_true",
        default=False,
        help="Use MLP projection (closer to ReasonCACHE). Adds ~3M params but improves quality.",
    )
    p.add_argument(
        "--encoder-hidden-size",
        type=int,
        default=512,
        help="Hidden size of the prefix projection MLP (only with --prefix-projection)",
    )
    p.add_argument(
        "--epochs",
        type=int,
        default=int(os.environ.get("OTTO_EPOCHS", "3")),
        help="Training epochs (default: 3)",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=int(os.environ.get("OTTO_MAX_STEPS", "-1")),
        help="Override epochs with fixed step count (-1 = use epochs)",
    )
    p.add_argument(
        "--seq-len",
        type=int,
        default=int(os.environ.get("OTTO_SEQ_LEN", "2048")),
        help="Max sequence length (default: 2048, shorter than LoRA due to prefix overhead)",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="Per-device batch size (default: 2)",
    )
    p.add_argument(
        "--grad-accum",
        type=int,
        default=8,
        help="Gradient accumulation steps (default: 8, effective batch=16)",
    )
    p.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate (default: 1e-3, higher than LoRA since only prefix params train)",
    )
    p.add_argument(
        "--cpu-test",
        action="store_true",
        help="Run a minimal smoke test on CPU (small model subset, 5 steps)",
    )
    return p.parse_args()


# ─── Parameter Count ──────────────────────────────────────────────────────────
def count_prefix_params(model, prefix_only=True):
    """Count trainable parameters, separating prefix vs base model."""
    prefix_params = 0
    frozen_params = 0
    for name, param in model.named_parameters():
        if param.requires_grad:
            prefix_params += param.numel()
        else:
            frozen_params += param.numel()
    return prefix_params, frozen_params


def print_param_comparison(model, num_virtual_tokens, prefix_projection):
    """Print a clear comparison of prefix vs LoRA parameter counts."""
    trainable, frozen = count_prefix_params(model)
    total = trainable + frozen

    # Theoretical LoRA rank-16 count for same model
    # Qwen 2.5 7B: 28 layers, hidden=3584, intermediate=18944
    num_layers = 28
    hidden_size = 3584
    intermediate = 18944
    lora_rank = 16
    lora_modules = {
        "q_proj": hidden_size * hidden_size,
        "k_proj": hidden_size * hidden_size,
        "v_proj": hidden_size * hidden_size,
        "o_proj": hidden_size * hidden_size,
        "gate_proj": hidden_size * intermediate,
        "up_proj": hidden_size * intermediate,
        "down_proj": intermediate * hidden_size,
    }
    lora_count = sum(2 * lora_rank * min(d, hidden_size if i < 4 else intermediate)
                     for i, (_, d) in enumerate(lora_modules.items())) * num_layers

    log.info("=" * 60)
    log.info("PARAMETER COMPARISON (ReasonCACHE-style vs LoRA)")
    log.info("=" * 60)
    log.info(f"  Base model (frozen)      : {frozen/1e6:>8.2f}M")
    log.info(f"  Prefix tuning (trainable): {trainable/1e6:>8.2f}M  ← ACTIVE")
    log.info(f"  Total parameters         : {total/1e6:>8.2f}M")
    log.info(f"  LoRA rank-16 equivalent  : {lora_count/1e6:>8.2f}M")
    log.info(f"  Savings vs LoRA          : {(1 - trainable/lora_count)*100:>7.1f}%")
    log.info(f"  Prefix config            : {num_virtual_tokens} tokens"
             f"{' + projection' if prefix_projection else ''}")
    log.info("=" * 60)
    return trainable


# ─── Dataset Loading ──────────────────────────────────────────────────────────
def load_dataset(data_path: str, tokenizer, max_seq_length: int, cpu_test: bool):
    """Load training_data_v4.jsonl (messages format) and apply chat template."""
    from datasets import Dataset

    log.info(f"Loading dataset: {data_path}")
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Training data not found: {data_path}")

    examples = []
    with open(data_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    if cpu_test:
        examples = examples[:50]
        log.info("CPU test mode: using first 50 examples")

    log.info(f"Loaded {len(examples)} raw examples")

    texts = []
    skipped = 0
    for ex in examples:
        messages = ex.get("messages", [])
        if not messages:
            skipped += 1
            continue
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            texts.append(text)
        except Exception:
            skipped += 1

    if skipped:
        log.warning(f"Skipped {skipped} malformed examples")

    log.info(f"Dataset ready: {len(texts)} examples")
    return Dataset.from_dict({"text": texts})


# ─── Tokenization ─────────────────────────────────────────────────────────────
def tokenize_dataset(dataset, tokenizer, max_seq_length):
    """Tokenize and truncate the dataset."""

    def tokenize(examples):
        result = tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )
        result["labels"] = result["input_ids"].copy()
        return result

    log.info("Tokenizing dataset...")
    tokenized = dataset.map(
        tokenize,
        batched=True,
        remove_columns=["text"],
        num_proc=1,
    )
    log.info(f"Tokenization complete: {len(tokenized)} examples")
    return tokenized


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    log.info("=" * 60)
    log.info("Otto Prefix Tuning — ReasonCACHE Style")
    log.info(f"Timestamp        : {datetime.utcnow().isoformat()}Z")
    log.info(f"Model            : {args.model}")
    log.info(f"Data             : {args.data}")
    log.info(f"Output           : {args.output}")
    log.info(f"Virtual tokens   : {args.num_virtual_tokens}")
    log.info(f"Prefix projection: {args.prefix_projection}")
    log.info(f"Epochs           : {args.epochs}")
    log.info(f"Seq length       : {args.seq_len}")
    log.info(f"CPU test         : {args.cpu_test}")
    log.info("=" * 60)

    # ── 1. Imports ────────────────────────────────────────────────────────────
    try:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
            DataCollatorForSeq2Seq,
        )
        from peft import (
            PrefixTuningConfig,
            get_peft_model,
            TaskType,
        )

        log.info(f"torch {torch.__version__} | CUDA: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            log.info(f"GPU: {torch.cuda.get_device_name(0)} | "
                     f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB")

    except ImportError as e:
        log.error(f"Import failed: {e}")
        log.error("Install: pip install peft transformers torch datasets")
        sys.exit(1)

    # ── 2. Load tokenizer ─────────────────────────────────────────────────────
    log.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.padding_side = "right"

    # ── 3. Load base model ────────────────────────────────────────────────────
    if args.cpu_test:
        log.info("CPU test: loading model in float32...")
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            torch_dtype=torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
    else:
        log.info("Loading base model with bfloat16 quantization...")
        # For prefix tuning we DON'T need 4-bit quantization since we're not
        # training weight matrices — prefix params are small and in fp32.
        # Use bfloat16 for the frozen base model to save VRAM.
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            torch_dtype=dtype,
            device_map="auto",
            trust_remote_code=True,
        )

    model.config.use_cache = False  # Disable KV cache during training
    log.info("Base model loaded.")

    # ── 4. Configure Prefix Tuning (ReasonCACHE style) ────────────────────────
    #
    # ReasonCACHE's key insight: instead of weight-space updates (LoRA),
    # directly inject trainable key-value pairs into each attention layer.
    # PrefixTuningConfig implements this via PEFT's PREFIX_TUNING method.
    #
    # With prefix_projection=True, a small MLP maps virtual token embeddings
    # to the actual KV space — this is closer to ReasonCACHE's learned
    # "reasoning cache" concept.
    #
    # Token count guidance:
    #   20 tokens: minimal (~1.4M params) — baseline
    #   50 tokens: balanced (~3.6M params) — good for short tasks
    #   100 tokens: recommended (~7.2M params) — matches paper's scale
    #   200 tokens: heavy (~14.4M params) — for complex reasoning
    #
    log.info(f"Configuring prefix tuning: {args.num_virtual_tokens} virtual tokens, "
             f"projection={args.prefix_projection}")

    peft_config = PrefixTuningConfig(
        task_type=TaskType.CAUSAL_LM,
        num_virtual_tokens=args.num_virtual_tokens,
        encoder_hidden_size=args.encoder_hidden_size if args.prefix_projection else None,
        prefix_projection=args.prefix_projection,
        # IMPORTANT: inference_mode=False is required during training
        inference_mode=False,
    )

    model = get_peft_model(model, peft_config)

    # Print parameter comparison
    trainable_params = print_param_comparison(
        model, args.num_virtual_tokens, args.prefix_projection
    )

    # ── 5. Load dataset ───────────────────────────────────────────────────────
    raw_ds = load_dataset(args.data, tokenizer, args.seq_len, args.cpu_test)
    tokenized_ds = tokenize_dataset(raw_ds, tokenizer, args.seq_len)

    # ── 6. Training plan ──────────────────────────────────────────────────────
    effective_batch = args.batch_size * args.grad_accum
    steps_per_epoch = max(1, len(tokenized_ds) // effective_batch)
    total_steps = steps_per_epoch * args.epochs

    if args.max_steps > 0:
        total_steps = args.max_steps
    elif args.cpu_test:
        total_steps = 5

    warmup_steps = max(5, int(total_steps * 0.03))

    log.info("Training plan:")
    log.info(f"  Examples       : {len(tokenized_ds)}")
    log.info(f"  Effective batch: {effective_batch}")
    log.info(f"  Steps / epoch  : {steps_per_epoch}")
    log.info(f"  Total steps    : {total_steps}")
    log.info(f"  Warmup steps   : {warmup_steps}")
    log.info(f"  Learning rate  : {args.lr}")
    log.info(f"  Trainable params: {trainable_params/1e6:.2f}M")

    # ── 7. Training arguments ─────────────────────────────────────────────────
    # Prefix tuning uses higher LR than LoRA (1e-3 vs 2e-4) because:
    # - Only a small set of parameters are updated
    # - They're randomly initialized (need stronger signal to converge)
    use_cuda = torch.cuda.is_available() and not args.cpu_test
    use_bf16 = use_cuda and torch.cuda.is_bf16_supported()

    training_args = TrainingArguments(
        output_dir=args.output,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        warmup_steps=warmup_steps,
        max_steps=total_steps,
        learning_rate=args.lr,
        fp16=use_cuda and not use_bf16,
        bf16=use_bf16,
        logging_steps=10,
        optim="adamw_torch",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        save_steps=200,
        save_total_limit=2,
        report_to="none",
        # No gradient checkpointing needed — prefix params are tiny
        gradient_checkpointing=False,
        dataloader_num_workers=0,
        remove_unused_columns=True,
    )

    # ── 8. Data collator ──────────────────────────────────────────────────────
    # Use DataCollatorForSeq2Seq with padding for variable-length sequences
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        pad_to_multiple_of=8,
    )

    # ── 9. Trainer ────────────────────────────────────────────────────────────
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_ds,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    # ── 10. Train ─────────────────────────────────────────────────────────────
    log.info("Starting prefix tuning training...")
    t0 = time.time()
    trainer_stats = trainer.train()
    elapsed = time.time() - t0
    log.info(f"Training complete in {elapsed/60:.1f} min")
    log.info(f"  train_loss      : {trainer_stats.training_loss:.4f}")
    log.info(f"  train_runtime   : {trainer_stats.metrics.get('train_runtime', 0):.1f}s")
    log.info(f"  train_steps_sec : {trainer_stats.metrics.get('train_steps_per_second', 0):.2f}")

    # ── 11. Save prefix adapter ───────────────────────────────────────────────
    # Only the prefix parameters are saved — the base model is unchanged!
    # This means the adapter file is tiny (MBs, not GBs)
    adapter_path = f"{args.output}/prefix_adapter"
    log.info(f"Saving prefix adapter → {adapter_path}")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)

    adapter_size = sum(
        f.stat().st_size for f in Path(adapter_path).rglob("*") if f.is_file()
    )
    log.info(f"Adapter size: {adapter_size/1e6:.1f} MB (vs ~100+ MB for LoRA adapter)")
    log.info("Prefix adapter saved. Base model untouched — no catastrophic forgetting.")

    # ── 12. Write inference example ───────────────────────────────────────────
    inference_script = f"""{args.output}/run_inference.py"""
    inference_code = f'''#!/usr/bin/env python3
"""Quick inference test for Otto prefix adapter."""
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

model_name = "{args.model}"
adapter_path = "prefix_adapter"

print("Loading base model...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_name, torch_dtype=torch.bfloat16, device_map="auto"
)

print("Loading prefix adapter...")
model = PeftModel.from_pretrained(model, adapter_path)
model.eval()

# Test prompt
messages = [
    {{"role": "system", "content": "{OTTO_SYSTEM_PROMPT}"}},
    {{"role": "user", "content": "What is your mission, Otto?"}},
]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(model.device)

with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=200, temperature=0.7, do_sample=True)

response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
print(f"\\nOtto: {{response}}")
'''
    with open(f"{args.output}/run_inference.py", "w") as f:
        f.write(inference_code)
    log.info(f"Inference script written → {args.output}/run_inference.py")

    # ── 13. Summary ───────────────────────────────────────────────────────────
    summary = {
        "status": "SUCCESS",
        "method": "prefix_tuning",
        "inspired_by": "ReasonCACHE (arXiv:2602.02366)",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": args.model,
        "data": args.data,
        "num_virtual_tokens": args.num_virtual_tokens,
        "prefix_projection": args.prefix_projection,
        "trainable_params_M": round(trainable_params / 1e6, 3),
        "lora_rank16_params_M": 63.77,
        "param_savings_pct": round((1 - trainable_params / 63.77e6) * 100, 1),
        "training_loss": trainer_stats.training_loss,
        "total_steps": total_steps,
        "elapsed_min": round(elapsed / 60, 1),
        "adapter_size_MB": round(adapter_size / 1e6, 1),
        "examples": len(tokenized_ds),
        "adapter_path": adapter_path,
    }

    summary_path = f"{args.output}/training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info("=" * 60)
    log.info("TRAINING COMPLETE — ReasonCACHE Style Prefix Tuning")
    log.info(f"  Adapter  : {adapter_path}")
    log.info(f"  Size     : {adapter_size/1e6:.1f} MB")
    log.info(f"  Loss     : {trainer_stats.training_loss:.4f}")
    log.info(f"  Summary  : {summary_path}")
    log.info("")
    log.info("Next steps on otto-machine:")
    log.info(f"  scp -r runpod:/workspace/{args.output} ~/otto/projects/own_model/models/")
    log.info("  # Load adapter for inference:")
    log.info(f"  python3 ~/otto/projects/own_model/{args.output}/run_inference.py")
    log.info("=" * 60)

    return summary


if __name__ == "__main__":
    main()
