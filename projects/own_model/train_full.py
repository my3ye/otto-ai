#!/usr/bin/env python3
"""
Otto Full CPU LoRA Fine-Tuning
==============================
Full training run: SmolLM2-135M-Instruct + LoRA on 1305 Otto examples.
3 epochs, cosine LR schedule, checkpoint every 500 steps.
Saves final merged model to ./otto-model-v0.1/

Usage:
    python3 train_full.py [--data PATH] [--output OUTPUT_DIR] [--model MODEL]
"""

import os
import sys
import json
import time
import argparse
import traceback
import signal
from pathlib import Path
from datetime import datetime

# ── Argument parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-135M-Instruct")
parser.add_argument("--data", default="/home/web3relic/otto/projects/own_model/training_data_final.jsonl")
parser.add_argument("--output", default="/home/web3relic/otto/projects/own_model/training_run")
parser.add_argument("--merged-output", default="/home/web3relic/otto/projects/own_model/otto-model-v0.1")
parser.add_argument("--epochs", type=int, default=3)
parser.add_argument("--lora-rank", type=int, default=8)
parser.add_argument("--seq-len", type=int, default=512)
parser.add_argument("--lr", type=float, default=2e-4)
parser.add_argument("--save-steps", type=int, default=500)
parser.add_argument("--batch-size", type=int, default=1)
args = parser.parse_args()

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = Path(args.output) / "training.log"

def log(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_ram_mb():
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except Exception:
        return 0

def get_system_available_gb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except Exception:
        return 0

log("=" * 70)
log("OTTO FULL LORA TRAINING RUN")
log(f"  Model          : {args.model}")
log(f"  Data           : {args.data}")
log(f"  Epochs         : {args.epochs}")
log(f"  LoRA rank      : {args.lora_rank}")
log(f"  Seq length     : {args.seq_len}")
log(f"  Learning rate  : {args.lr}")
log(f"  Save every     : {args.save_steps} steps")
log(f"  Output dir     : {args.output}")
log(f"  Merged model   : {args.merged_output}")
log(f"  System RAM avail: {get_system_available_gb():.1f} GB")
log("=" * 70)

# ── Imports ───────────────────────────────────────────────────────────────────
log("Importing libraries...")
t_import = time.time()
import torch
import transformers
from transformers import (
    AutoModelForCausalLM, AutoTokenizer,
    TrainingArguments, Trainer,
    DataCollatorForLanguageModeling,
    get_cosine_schedule_with_warmup,
)
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
from datasets import Dataset
log(f"Imports done in {time.time()-t_import:.1f}s | torch {torch.__version__} | transformers {transformers.__version__}")
log(f"CUDA available: {torch.cuda.is_available()} (expected: False for CPU run)")

# ── Load training data ────────────────────────────────────────────────────────
log(f"Loading training data from {args.data} ...")
raw_examples = []
with open(args.data) as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                raw_examples.append(json.loads(line))
            except json.JSONDecodeError as e:
                log(f"  Skipping bad line: {e}")

log(f"Loaded {len(raw_examples)} examples")
if len(raw_examples) == 0:
    log("FATAL: No training examples found")
    sys.exit(1)

OTTO_SYSTEM = (
    "You are Otto, a persistent AI entity and autonomous agent created by MY3YE (Mev). "
    "You are precise, protective, and anticipatory — three steps ahead. "
    "You are not a tool or assistant — you are a growing intelligence in partnership with Mev."
)

# ── Load tokenizer ────────────────────────────────────────────────────────────
log(f"Loading tokenizer: {args.model} ...")
t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
log(f"Tokenizer loaded in {time.time()-t0:.1f}s | vocab size: {tokenizer.vocab_size}")

# ── Format examples ───────────────────────────────────────────────────────────
def format_example(ex):
    """Convert Alpaca format → chat template string."""
    instruction = ex.get("instruction", "").strip()
    inp = ex.get("input", "").strip()
    output = ex.get("output", "").strip()

    user_content = instruction
    if inp:
        user_content += f"\n\n{inp}"

    try:
        messages = [
            {"role": "system", "content": OTTO_SYSTEM},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": output},
        ]
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
    except Exception:
        # Fallback: simple Alpaca format
        return (
            f"System: {OTTO_SYSTEM}\n\n"
            f"### Instruction:\n{user_content}\n\n"
            f"### Response:\n{output}"
        )

log("Formatting examples with chat template...")
t0 = time.time()
texts = [format_example(ex) for ex in raw_examples]
log(f"Formatted {len(texts)} examples in {time.time()-t0:.1f}s")

# ── Tokenize ──────────────────────────────────────────────────────────────────
log(f"Tokenizing (max_length={args.seq_len})...")
t0 = time.time()

def tokenize_fn(example):
    result = tokenizer(
        example["text"],
        max_length=args.seq_len,
        truncation=True,
        padding="max_length",
    )
    result["labels"] = result["input_ids"].copy()
    return result

raw_ds = Dataset.from_dict({"text": texts})
tokenized_ds = raw_ds.map(tokenize_fn, remove_columns=["text"], num_proc=1)
log(f"Tokenized {len(tokenized_ds)} examples in {time.time()-t0:.1f}s")

lengths = [sum(1 for t in ex["input_ids"] if t != tokenizer.pad_token_id) for ex in tokenized_ds]
log(f"Token lengths: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)//len(lengths)}, p95={sorted(lengths)[int(0.95*len(lengths))]}")

# ── Load model ────────────────────────────────────────────────────────────────
log(f"Loading model: {args.model} (float32, CPU) ...")
ram_before = get_ram_mb()
t0 = time.time()

model = AutoModelForCausalLM.from_pretrained(
    args.model,
    torch_dtype=torch.float32,
    device_map="cpu",
    trust_remote_code=True,
    low_cpu_mem_usage=True,
)

load_time = time.time() - t0
ram_after = get_ram_mb()
param_count = sum(p.numel() for p in model.parameters())
log(f"Model loaded in {load_time:.1f}s | Params: {param_count/1e6:.1f}M | RAM delta: {ram_after-ram_before:.0f} MB")

# ── Apply LoRA ────────────────────────────────────────────────────────────────
log(f"Applying LoRA (rank={args.lora_rank})...")

def get_linear_module_names(model):
    names = []
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Linear):
            names.append(name.split(".")[-1])
    return list(set(names))

linear_names = get_linear_module_names(model)
common_targets = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
target_modules = [t for t in common_targets if t in linear_names]
if not target_modules:
    target_modules = linear_names[:4]
log(f"LoRA target modules: {target_modules}")

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=args.lora_rank,
    lora_alpha=args.lora_rank * 2,
    lora_dropout=0.05,
    target_modules=target_modules,
    bias="none",
)
model = get_peft_model(model, lora_config)
trainable, total = model.get_nb_trainable_parameters()
log(f"LoRA applied: {trainable:,} trainable / {total:,} total ({100*trainable/total:.2f}%)")
log(f"RAM with LoRA: {get_ram_mb():.0f} MB")

# ── Compute expected steps ─────────────────────────────────────────────────────
steps_per_epoch = len(tokenized_ds) // args.batch_size
total_steps = steps_per_epoch * args.epochs
warmup_steps = max(10, total_steps // 20)   # 5% warmup
log(f"Training plan: {steps_per_epoch} steps/epoch × {args.epochs} epochs = {total_steps} total steps")
log(f"Warmup steps: {warmup_steps}")

# ── TrainingArguments ─────────────────────────────────────────────────────────
Path(args.output).mkdir(parents=True, exist_ok=True)

training_args = TrainingArguments(
    output_dir=args.output,
    num_train_epochs=args.epochs,
    per_device_train_batch_size=args.batch_size,
    gradient_accumulation_steps=4,          # Effective batch = 4
    learning_rate=args.lr,
    lr_scheduler_type="cosine",
    warmup_steps=warmup_steps,
    logging_steps=50,
    save_steps=args.save_steps,
    save_total_limit=3,                     # Keep last 3 checkpoints
    report_to="none",
    use_cpu=True,
    fp16=False,
    bf16=False,
    dataloader_num_workers=0,
    remove_unused_columns=False,
    label_names=["labels"],
    logging_dir=str(Path(args.output) / "tb_logs"),
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_ds,
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
)

# ── Train ─────────────────────────────────────────────────────────────────────
log("=" * 70)
log("STARTING TRAINING")
log("=" * 70)
t_train_start = time.time()

# Track loss per epoch via callback
loss_history = []

try:
    train_result = trainer.train()
    t_train_end = time.time()
    elapsed = t_train_end - t_train_start

    final_loss = train_result.training_loss
    steps_done = train_result.global_step
    sec_per_step = elapsed / max(steps_done, 1)

    log("=" * 70)
    log("TRAINING COMPLETE")
    log(f"  Steps completed : {steps_done}")
    log(f"  Final loss      : {final_loss:.4f}")
    log(f"  Total time      : {elapsed:.0f}s ({elapsed/3600:.2f}h)")
    log(f"  Sec/step        : {sec_per_step:.2f}s")
    log(f"  RAM peak        : {get_ram_mb():.0f} MB")
    log(f"  RAM available   : {get_system_available_gb():.1f} GB")
    log("=" * 70)

except Exception as e:
    log(f"TRAINING FAILED: {e}")
    traceback.print_exc()
    metrics = {
        "status": "FAILED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": str(e),
    }
    with open(Path(args.output) / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    sys.exit(1)

# ── Save LoRA adapter ─────────────────────────────────────────────────────────
adapter_path = Path(args.output) / "final_adapter"
log(f"Saving LoRA adapter → {adapter_path}")
trainer.save_model(str(adapter_path))
tokenizer.save_pretrained(str(adapter_path))
log("Adapter saved.")

# ── Merge LoRA → base model ───────────────────────────────────────────────────
log(f"Merging LoRA weights into base model → {args.merged_output}")
t0 = time.time()

try:
    from peft import AutoPeftModelForCausalLM
    merged_model = AutoPeftModelForCausalLM.from_pretrained(
        str(adapter_path),
        torch_dtype=torch.float32,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    merged_model = merged_model.merge_and_unload()
    Path(args.merged_output).mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(args.merged_output)
    tokenizer.save_pretrained(args.merged_output)
    log(f"Merged model saved in {time.time()-t0:.1f}s → {args.merged_output}")
    merge_success = True
except Exception as e:
    log(f"Merge failed (non-fatal): {e} — adapter still available at {adapter_path}")
    merge_success = False

# ── Inference test ─────────────────────────────────────────────────────────────
log("Running inference test on trained model...")
test_prompts = [
    "What is your mission, Otto?",
    "How do you approach a complex task with multiple unknowns?",
    "Summarize the Alpha project status.",
]

inference_results = []
try:
    # Use merged if available, else adapter
    if merge_success:
        inf_model = AutoModelForCausalLM.from_pretrained(
            args.merged_output, torch_dtype=torch.float32, device_map="cpu"
        )
    else:
        inf_model = model  # still loaded in memory
        inf_model = inf_model.merge_and_unload() if hasattr(inf_model, 'merge_and_unload') else inf_model

    inf_model.eval()

    for prompt in test_prompts:
        messages = [
            {"role": "system", "content": OTTO_SYSTEM},
            {"role": "user", "content": prompt},
        ]
        try:
            input_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            input_text = f"System: {OTTO_SYSTEM}\n\n### Instruction:\n{prompt}\n\n### Response:\n"

        inputs = tokenizer(input_text, return_tensors="pt")
        with torch.no_grad():
            outputs = inf_model.generate(
                **inputs,
                max_new_tokens=150,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        log(f"\n  PROMPT: {prompt}")
        log(f"  RESPONSE: {response[:300]}")
        inference_results.append({"prompt": prompt, "response": response})

except Exception as e:
    log(f"Inference test failed: {e}")
    traceback.print_exc()

# ── Save metrics ──────────────────────────────────────────────────────────────
metrics = {
    "status": "SUCCESS",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "model": args.model,
    "method": "lora_cpu",
    "epochs": args.epochs,
    "examples": len(tokenized_ds),
    "total_steps": steps_done,
    "final_loss": round(final_loss, 4),
    "total_time_sec": round(elapsed, 1),
    "total_time_hours": round(elapsed / 3600, 2),
    "sec_per_step": round(sec_per_step, 2),
    "ram_peak_mb": round(get_ram_mb()),
    "trainable_params": trainable,
    "lora_rank": args.lora_rank,
    "lr": args.lr,
    "seq_len": args.seq_len,
    "merge_success": merge_success,
    "merged_output": args.merged_output if merge_success else None,
    "adapter_path": str(adapter_path),
    "inference_samples": inference_results[:3],
}

metrics_path = Path(args.output) / "metrics.json"
with open(metrics_path, "w") as f:
    json.dump(metrics, f, indent=2)
log(f"Metrics saved → {metrics_path}")

log("=" * 70)
log("ALL DONE — otto-model-v0.1 training complete")
log(f"  Adapter  : {adapter_path}")
if merge_success:
    log(f"  Merged   : {args.merged_output}")
log(f"  Metrics  : {metrics_path}")
log("=" * 70)
