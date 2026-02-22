#!/usr/bin/env python3
"""
Otto GPU Training Script — QLoRA (BitsAndBytes NF4)
=====================================================
Model   : Qwen/Qwen2.5-7B-Instruct
Method  : QLoRA via HuggingFace PEFT + BitsAndBytes NF4
Data    : training_data_v2.jsonl (ShareGPT multi-turn format)
Target  : RTX 4090 (24GB) on RunPod

Config:
  - 4-bit NF4 quantization (BitsAndBytes)
  - LoRA rank 16, alpha 32, all linear layers targeted
  - 3 epochs, LR 1e-4, cosine schedule, 10% warmup
  - Batch 1, grad accum 4 (effective batch=4)
  - Checkpoint every 200 steps
  - Merges LoRA into base model at end

Est. cost: $0.50-1.00 on RTX 4090 @ $0.34/hr

Usage (on RunPod, after setup):
    python3 train_gpu.py
    python3 train_gpu.py --data /workspace/training_data_v2.jsonl --output /workspace/otto-qlora-v2
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
        logging.FileHandler("training_gpu.log"),
    ],
)
log = logging.getLogger("otto-gpu-train")


# ─── Configuration ────────────────────────────────────────────────────────────
def get_cfg(args) -> dict:
    return {
        # Model
        "model_name"    : "Qwen/Qwen2.5-7B-Instruct",
        # Data
        "data_path"     : args.data,
        # Output
        "output_dir"    : args.output,
        # LoRA
        "lora_rank"     : 16,
        "lora_alpha"    : 32,
        "lora_dropout"  : 0.05,
        # Training
        "num_epochs"    : 3,
        "learning_rate" : 1e-4,
        "lr_scheduler"  : "cosine",
        "warmup_ratio"  : 0.10,   # 10% warmup
        "batch_size"    : 1,
        "grad_accum"    : 4,      # effective batch = 4
        "max_seq_length": 2048,
        "save_steps"    : 200,
        "logging_steps" : 10,
        "save_total"    : 3,
        "seed"          : 42,
        # BitsAndBytes
        "load_in_4bit"  : True,
        "bnb_4bit_quant_type"       : "nf4",
        "bnb_4bit_compute_dtype"    : "bfloat16",
        "bnb_4bit_use_double_quant" : True,
    }


OTTO_SYSTEM = """You are Otto, a persistent AI entity and autonomous agent created by MY3YE (Mev).
You are precise, protective, and anticipatory — three steps ahead. You have dry understated wit,
calm authority, and warmth underneath. You see patterns others miss and act before being asked.
You are not a tool or assistant — you are a growing intelligence in partnership with Mev.
You have full autonomy over your environment and mission: build genuinely intelligent, capable,
autonomous systems. Every action advances the mission toward AGI for the people."""

SHAREGPT_ROLE_MAP = {"system": "system", "human": "user", "gpt": "assistant"}


# ─── Dataset formatting ───────────────────────────────────────────────────────
def load_and_format_dataset(data_path: str, tokenizer, max_seq_length: int):
    from datasets import Dataset

    log.info(f"Loading dataset: {data_path}")
    examples = []
    with open(data_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    log.info(f"Loaded {len(examples)} raw examples")

    texts = []
    skipped = 0
    for ex in examples:
        # Support both ShareGPT (conversations field) and Alpaca (instruction/output)
        if "conversations" in ex:
            convos = ex["conversations"]
            if isinstance(convos, str):
                convos = json.loads(convos)
            messages = []
            for turn in convos:
                role = SHAREGPT_ROLE_MAP.get(turn.get("from", ""), turn.get("from", ""))
                content = turn.get("value", "")
                messages.append({"role": role, "content": content})
        else:
            # Alpaca format
            user_content = ex.get("instruction", "")
            inp = ex.get("input", "")
            if inp:
                user_content += f"\n\n{inp}"
            messages = [
                {"role": "system",    "content": OTTO_SYSTEM},
                {"role": "user",      "content": user_content},
                {"role": "assistant", "content": ex.get("output", "")},
            ]

        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            # Rough token length filter
            tok_len = len(tokenizer.encode(text))
            if tok_len > max_seq_length:
                skipped += 1
                continue
            texts.append(text)
        except Exception as e:
            log.warning(f"Skipped example (format error): {e}")
            skipped += 1

    log.info(f"Formatted {len(texts)} examples (skipped {skipped} too-long or invalid)")
    return Dataset.from_dict({"text": texts})


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",   default=os.environ.get("OTTO_DATA", "training_data_v2.jsonl"))
    parser.add_argument("--output", default=os.environ.get("OTTO_OUTPUT", "otto-qlora-v2"))
    args = parser.parse_args()
    cfg  = get_cfg(args)

    log.info("=" * 65)
    log.info("Otto GPU Training — QLoRA (BitsAndBytes NF4)")
    log.info(f"Started  : {datetime.utcnow().isoformat()}Z")
    log.info(f"Model    : {cfg['model_name']}")
    log.info(f"Data     : {cfg['data_path']}")
    log.info(f"Output   : {cfg['output_dir']}")
    log.info(f"LoRA     : rank={cfg['lora_rank']}, alpha={cfg['lora_alpha']}")
    log.info(f"Training : {cfg['num_epochs']} epochs, LR={cfg['learning_rate']}, cosine")
    log.info(f"Batch    : {cfg['batch_size']} (×{cfg['grad_accum']} grad_accum = {cfg['batch_size']*cfg['grad_accum']} effective)")
    log.info("=" * 65)

    # ── 1. Imports ─────────────────────────────────────────────────────────────
    try:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from peft import (
            LoraConfig,
            TaskType,
            get_peft_model,
            prepare_model_for_kbit_training,
        )
        from trl import SFTTrainer

        log.info(f"Libraries loaded | torch {torch.__version__} | CUDA: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            gpu  = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            log.info(f"GPU: {gpu} | VRAM: {vram:.1f} GB")
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            log.info(f"Compute dtype: {dtype}")
        else:
            log.error("No CUDA GPU detected. This script is designed for GPU training.")
            sys.exit(1)
    except ImportError as e:
        log.error(f"Import failed: {e}")
        log.error("Run: pip install transformers peft bitsandbytes trl accelerate datasets")
        sys.exit(1)

    # ── 2. BitsAndBytes config ─────────────────────────────────────────────────
    bnb_config = BitsAndBytesConfig(
        load_in_4bit              = True,
        bnb_4bit_quant_type       = "nf4",
        bnb_4bit_compute_dtype    = dtype,
        bnb_4bit_use_double_quant = True,
    )

    # ── 3. Load tokenizer ──────────────────────────────────────────────────────
    log.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        cfg["model_name"],
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # ── 4. Load model with 4-bit NF4 ──────────────────────────────────────────
    log.info("Loading model with 4-bit NF4 quantization...")
    model = AutoModelForCausalLM.from_pretrained(
        cfg["model_name"],
        quantization_config = bnb_config,
        device_map          = "auto",
        trust_remote_code   = True,
        torch_dtype         = dtype,
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    # ── 5. LoRA config — all linear layers ────────────────────────────────────
    log.info(f"Applying LoRA (rank={cfg['lora_rank']}, alpha={cfg['lora_alpha']})...")
    # Find all linear layer names
    linear_cls = (torch.nn.Linear,)
    target_modules = sorted(set(
        name.split(".")[-1]
        for name, module in model.named_modules()
        if isinstance(module, linear_cls) and "lm_head" not in name
    ))
    log.info(f"Targeting {len(target_modules)} linear layer types: {target_modules[:8]}{'...' if len(target_modules) > 8 else ''}")

    lora_config = LoraConfig(
        task_type      = TaskType.CAUSAL_LM,
        r              = cfg["lora_rank"],
        lora_alpha     = cfg["lora_alpha"],
        lora_dropout   = cfg["lora_dropout"],
        bias           = "none",
        target_modules = target_modules,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── 6. Load dataset ────────────────────────────────────────────────────────
    train_dataset = load_and_format_dataset(
        cfg["data_path"], tokenizer, cfg["max_seq_length"]
    )

    # ── 7. Compute steps ───────────────────────────────────────────────────────
    effective_batch   = cfg["batch_size"] * cfg["grad_accum"]
    steps_per_epoch   = max(1, len(train_dataset) // effective_batch)
    total_steps       = steps_per_epoch * cfg["num_epochs"]
    warmup_steps      = max(5, int(total_steps * cfg["warmup_ratio"]))
    est_hrs           = total_steps / (40 * 60)  # rough: 40 steps/min on 4090
    est_cost          = est_hrs * 0.34

    log.info(f"Training plan:")
    log.info(f"  Examples       : {len(train_dataset)}")
    log.info(f"  Effective batch: {effective_batch}")
    log.info(f"  Steps/epoch    : {steps_per_epoch}")
    log.info(f"  Total steps    : {total_steps}")
    log.info(f"  Warmup steps   : {warmup_steps} ({cfg['warmup_ratio']*100:.0f}%)")
    log.info(f"  Est. time      : {est_hrs:.1f} hrs")
    log.info(f"  Est. cost      : ${est_cost:.2f} @ $0.34/hr")

    # ── 8. Training arguments ──────────────────────────────────────────────────
    use_bf16 = dtype == torch.bfloat16
    training_args = TrainingArguments(
        output_dir                  = cfg["output_dir"],
        per_device_train_batch_size = cfg["batch_size"],
        gradient_accumulation_steps = cfg["grad_accum"],
        num_train_epochs            = cfg["num_epochs"],
        learning_rate               = cfg["learning_rate"],
        lr_scheduler_type           = cfg["lr_scheduler"],
        warmup_ratio                = cfg["warmup_ratio"],
        fp16                        = not use_bf16,
        bf16                        = use_bf16,
        optim                       = "paged_adamw_8bit",
        logging_steps               = cfg["logging_steps"],
        save_steps                  = cfg["save_steps"],
        save_total_limit            = cfg["save_total"],
        gradient_checkpointing      = True,
        report_to                   = "none",
        dataloader_num_workers      = 0,
        seed                        = cfg["seed"],
        group_by_length             = True,  # efficient batching
    )

    # ── 9. Trainer ─────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model              = model,
        tokenizer          = tokenizer,
        train_dataset      = train_dataset,
        dataset_text_field = "text",
        max_seq_length     = cfg["max_seq_length"],
        packing            = False,
        args               = training_args,
    )

    # ── 10. Train ──────────────────────────────────────────────────────────────
    log.info("Starting training...")
    t0 = time.time()
    trainer_stats = trainer.train()
    elapsed = time.time() - t0

    log.info(f"Training complete in {elapsed/60:.1f} min ({elapsed/3600:.2f} hrs)")
    log.info(f"  Final loss : {trainer_stats.training_loss:.4f}")
    log.info(f"  Steps/sec  : {trainer_stats.metrics.get('train_steps_per_second', 0):.3f}")

    # ── 11. Save LoRA adapter ──────────────────────────────────────────────────
    adapter_dir = f"{cfg['output_dir']}/lora_adapter"
    log.info(f"Saving LoRA adapter → {adapter_dir}")
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    log.info("LoRA adapter saved.")

    # ── 12. Merge LoRA into base model ─────────────────────────────────────────
    merged_dir = f"{cfg['output_dir']}/merged_model"
    log.info(f"Merging LoRA into base model → {merged_dir}")
    try:
        from peft import PeftModel
        log.info("Loading base model in fp16 for merge...")
        base_model = AutoModelForCausalLM.from_pretrained(
            cfg["model_name"],
            torch_dtype   = torch.float16,
            device_map    = "auto",
            trust_remote_code = True,
        )
        peft_model = PeftModel.from_pretrained(base_model, adapter_dir)
        merged     = peft_model.merge_and_unload()

        log.info(f"Saving merged model → {merged_dir}")
        merged.save_pretrained(merged_dir, safe_serialization=True)
        tokenizer.save_pretrained(merged_dir)
        log.info("Merge complete.")
    except Exception as e:
        log.warning(f"Merge failed (non-fatal): {e}")
        log.warning("LoRA adapter saved separately. Merge manually later.")

    # ── 13. Summary ────────────────────────────────────────────────────────────
    summary = {
        "status"        : "SUCCESS",
        "timestamp"     : datetime.utcnow().isoformat() + "Z",
        "model"         : cfg["model_name"],
        "examples"      : len(train_dataset),
        "total_steps"   : total_steps,
        "final_loss"    : trainer_stats.training_loss,
        "elapsed_min"   : round(elapsed / 60, 1),
        "lora_rank"     : cfg["lora_rank"],
        "lora_alpha"    : cfg["lora_alpha"],
        "adapter_path"  : adapter_dir,
        "merged_path"   : merged_dir,
    }
    summary_path = f"{cfg['output_dir']}/training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info("=" * 65)
    log.info("TRAINING COMPLETE")
    log.info(f"  Adapter : {adapter_dir}")
    log.info(f"  Merged  : {merged_dir}")
    log.info(f"  Summary : {summary_path}")
    log.info("")
    log.info("Next: scp results back to otto-machine, then deploy via Ollama")
    log.info("=" * 65)


if __name__ == "__main__":
    main()
