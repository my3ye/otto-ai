#!/usr/bin/env python3
"""
Otto Model Merging Utility — DELLA + mergekit
=============================================
Implements DELLA-style specialist model merging for Otto's own-model pipeline.

Based on:
  - "Multi-task Code LLMs: Data Mix or Model Merge?" (arXiv 2601.21115)
  - "DELLA-Merging" (arXiv 2406.11617)
  - "A Systematic Study of Model Merging Techniques in LLMs" (arXiv 2511.21437)

Key finding: For 7B+ models, merging specialists outperforms joint training.
DELLA achieves 92.7% Pass@1 vs 90.9% for task-specific fine-tuned (HumanEval).

Usage:
    # Generate mergekit YAML for DELLA merge of 2 adapters
    python3 merge_models.py config \\
        --base Qwen/Qwen2.5-7B-Instruct \\
        --adapters otto-lora-reasoning otto-lora-personality \\
        --method della \\
        --output merge_config.yaml

    # Diagnose mergeability before committing
    python3 merge_models.py diagnose \\
        --adapter1 otto-lora-reasoning \\
        --adapter2 otto-lora-personality

    # Run merge (requires mergekit installed)
    python3 merge_models.py run \\
        --config merge_config.yaml \\
        --output merged_otto_v1

    # Full pipeline: diagnose → config → run
    python3 merge_models.py pipeline \\
        --base Qwen/Qwen2.5-7B-Instruct \\
        --adapters otto-lora-reasoning otto-lora-personality otto-lora-memory \\
        --output merged_otto_v1

Requirements (on RunPod or otto-machine):
    pip install mergekit torch transformers peft
    # mergekit: https://github.com/arcee-ai/mergekit
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("otto-merge")

# ─── DELLA / mergekit Method Descriptions ────────────────────────────────────
MERGE_METHODS = {
    "della": {
        "name": "DELLA (Density + Magnitude-based)",
        "description": (
            "Samples parameters for merging based on magnitude. "
            "Better than random dropping (DARE) or sign-only (TIES) for 7B+ models. "
            "Recommended for Otto's specialist merging."
        ),
        "mergekit_method": "della",
        "best_for": "7B+ specialists with different task domains",
        "paper": "arXiv 2406.11617",
    },
    "ties": {
        "name": "TIES (Trim, Elect Sign, Merge)",
        "description": (
            "Trims small-magnitude parameters, resolves sign conflicts by majority vote, "
            "then merges. Good for tasks with some overlap."
        ),
        "mergekit_method": "ties",
        "best_for": "Tasks with overlapping parameter domains",
        "paper": "arXiv 2306.01708",
    },
    "dare_ties": {
        "name": "DARE + TIES (Random Dropping + Sign Elect)",
        "description": (
            "Randomly drops parameters with probability (1-density), "
            "then applies TIES merging. A DELL predecessor."
        ),
        "mergekit_method": "dare_ties",
        "best_for": "Moderate task diversity, quick experiments",
        "paper": "arXiv 2311.03099",
    },
    "slerp": {
        "name": "SLERP (Spherical Linear Interpolation)",
        "description": (
            "Geodesic interpolation between two models on the weight manifold. "
            "Only supports exactly 2 models. Preserves model geometry."
        ),
        "mergekit_method": "slerp",
        "best_for": "Fine-grained blending of 2 closely related models",
        "paper": "Classic technique, no single paper",
    },
    "linear": {
        "name": "Linear (Weighted Average)",
        "description": "Simple weighted average of model weights. Baseline.",
        "mergekit_method": "linear",
        "best_for": "Models trained on very similar tasks/data",
        "paper": "N/A (baseline)",
    },
}

# ─── Otto Specialist Profiles ─────────────────────────────────────────────────
OTTO_SPECIALISTS = {
    "reasoning": {
        "description": "Chain-of-thought reasoning, problem decomposition, planning",
        "training_data_tags": ["reasoning", "planning", "analysis", "task_decomposition"],
        "expected_adapter": "otto-lora-reasoning",
        "priority": 1,
    },
    "personality": {
        "description": "Otto persona, tone, communication style, Mev relationship",
        "training_data_tags": ["persona", "whatsapp", "orchestrator", "reflection"],
        "expected_adapter": "otto-lora-personality",
        "priority": 2,
    },
    "memory": {
        "description": "Memory operations, episodic retrieval, semantic storage",
        "training_data_tags": ["memory", "episodic", "semantic", "retrieval"],
        "expected_adapter": "otto-lora-memory",
        "priority": 3,
    },
    "crypto": {
        "description": "Alpha trading signals, wallet analysis, market interpretation",
        "training_data_tags": ["alpha", "crypto", "trading", "wallet"],
        "expected_adapter": "otto-lora-crypto",
        "priority": 4,
    },
}

# ─── YAML Config Generation ────────────────────────────────────────────────────

def generate_mergekit_yaml(
    base_model: str,
    adapter_paths: list[str],
    method: str = "della",
    density: float = 0.5,
    weights: Optional[list[float]] = None,
    output_path: str = "merge_config.yaml",
    dtype: str = "bfloat16",
) -> str:
    """
    Generate a mergekit YAML configuration for DELLA (or other) merging.

    Args:
        base_model:    HuggingFace model ID or local path (the base to merge into)
        adapter_paths: List of LoRA adapter directories (merged into base weight space first)
        method:        Merge method key from MERGE_METHODS
        density:       Parameter density (0.0-1.0). Lower = more pruning. 0.5 recommended.
        weights:       Per-adapter merge weights. Defaults to equal weights.
        output_path:   Where to write the YAML file
        dtype:         Model dtype for mergekit (bfloat16 recommended)

    Returns:
        YAML string content
    """
    if method not in MERGE_METHODS:
        raise ValueError(f"Unknown method '{method}'. Choose from: {list(MERGE_METHODS)}")

    info = MERGE_METHODS[method]
    mergekit_method = info["mergekit_method"]
    n_adapters = len(adapter_paths)

    if weights is None:
        weights = [1.0 / n_adapters] * n_adapters

    if len(weights) != n_adapters:
        raise ValueError(f"weights length ({len(weights)}) must match adapters ({n_adapters})")

    if method == "slerp" and n_adapters != 2:
        raise ValueError("SLERP only supports exactly 2 models")

    lines = []
    lines.append(f"# Otto Model Merge — {info['name']}")
    lines.append(f"# Method: {mergekit_method} | Density: {density}")
    lines.append(f"# Paper: {info['paper']}")
    lines.append(f"# Generated by merge_models.py")
    lines.append("")
    lines.append(f"merge_method: {mergekit_method}")
    lines.append(f"base_model: {base_model}")
    lines.append(f"dtype: {dtype}")
    lines.append("")
    lines.append("models:")

    for i, (adapter_path, weight) in enumerate(zip(adapter_paths, weights)):
        adapter_name = Path(adapter_path).name
        lines.append(f"  - model: {adapter_path}")
        lines.append(f"    # Specialist: {adapter_name}")

        if method in ("della", "ties", "dare_ties"):
            lines.append(f"    parameters:")
            lines.append(f"      weight: {weight:.4f}")
            lines.append(f"      density: {density:.2f}")
        elif method == "slerp":
            # SLERP uses t parameter (0.0 = model A, 1.0 = model B)
            t_val = i / max(n_adapters - 1, 1)
            lines.append(f"    parameters:")
            lines.append(f"      t: {t_val:.2f}")
        else:  # linear
            lines.append(f"    parameters:")
            lines.append(f"      weight: {weight:.4f}")

    if method in ("della", "ties", "dare_ties"):
        lines.append("")
        lines.append("parameters:")
        lines.append(f"  density: {density:.2f}")
        lines.append(f"  normalize: true")

    yaml_content = "\n".join(lines) + "\n"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(yaml_content)
    log.info(f"mergekit YAML written → {output_path}")

    return yaml_content


# ─── Diagnostic: L2 Distance + Pearson Correlation ───────────────────────────

def diagnose_adapters(adapter1_path: str, adapter2_path: str) -> dict:
    """
    Compute layer-wise L2 distance and Pearson correlation between two LoRA adapters.

    From arXiv 2601.21115: These metrics predict merging success.
    - Low L2 + high correlation → merging will work well (similar task domains)
    - High L2 + low/negative correlation → potential interference, use higher density
    - Very high L2 → consider separate deployment instead of merging

    Args:
        adapter1_path: Path to first LoRA adapter directory
        adapter2_path: Path to second LoRA adapter directory

    Returns:
        Dict with per-layer metrics and overall recommendation
    """
    try:
        import torch
        from safetensors.torch import load_file
    except ImportError:
        log.error("torch and safetensors required: pip install torch safetensors")
        raise

    def load_adapter_weights(adapter_path: str) -> dict:
        """Load LoRA adapter weights from safetensors or bin files."""
        path = Path(adapter_path)
        weights = {}

        # Try safetensors first (preferred)
        st_files = list(path.glob("*.safetensors"))
        if st_files:
            for f in st_files:
                chunk = load_file(str(f))
                weights.update(chunk)
            return weights

        # Fallback to pytorch bin
        bin_files = list(path.glob("*.bin")) + list(path.glob("adapter_model.bin"))
        if bin_files:
            for f in bin_files:
                chunk = torch.load(str(f), map_location="cpu", weights_only=True)
                weights.update(chunk)
            return weights

        raise FileNotFoundError(
            f"No adapter weights found in {adapter_path}. "
            "Expected *.safetensors or adapter_model.bin"
        )

    log.info(f"Loading adapter 1: {adapter1_path}")
    w1 = load_adapter_weights(adapter1_path)
    log.info(f"Loading adapter 2: {adapter2_path}")
    w2 = load_adapter_weights(adapter2_path)

    # Find common parameter keys (LoRA A/B matrices)
    keys1 = set(w1.keys())
    keys2 = set(w2.keys())
    common_keys = keys1 & keys2

    if not common_keys:
        log.warning("No common parameter keys found. Are these the same base model?")
        return {"error": "no_common_keys", "recommendation": "incompatible"}

    lora_keys = [k for k in common_keys if "lora" in k.lower()]
    if not lora_keys:
        lora_keys = list(common_keys)

    log.info(f"Comparing {len(lora_keys)} LoRA parameter tensors")

    layer_stats = []
    total_l2 = 0.0
    total_pearson = 0.0
    valid_count = 0

    for key in sorted(lora_keys):
        t1 = w1[key].float().flatten()
        t2 = w2[key].float().flatten()

        if t1.shape != t2.shape:
            continue

        # L2 distance (normalized by sqrt of tensor size)
        l2_dist = float(torch.norm(t1 - t2) / (t1.numel() ** 0.5))

        # Pearson correlation
        t1_centered = t1 - t1.mean()
        t2_centered = t2 - t2.mean()
        denom = (torch.norm(t1_centered) * torch.norm(t2_centered) + 1e-8)
        pearson = float(torch.dot(t1_centered, t2_centered) / denom)

        layer_stats.append({
            "key": key,
            "l2_distance": round(l2_dist, 6),
            "pearson_correlation": round(pearson, 6),
            "shape": list(t1.shape),
        })

        total_l2 += l2_dist
        total_pearson += pearson
        valid_count += 1

    if valid_count == 0:
        return {"error": "no_valid_tensors", "recommendation": "check_adapter_format"}

    avg_l2 = total_l2 / valid_count
    avg_pearson = total_pearson / valid_count

    # Recommendation logic based on arXiv 2601.21115 findings
    if avg_pearson > 0.7 and avg_l2 < 0.1:
        rec = "MERGE_SAFE: High correlation, low divergence. DELLA density=0.7 recommended."
        rec_density = 0.7
    elif avg_pearson > 0.3 and avg_l2 < 0.3:
        rec = "MERGE_LIKELY: Moderate alignment. DELLA density=0.5 recommended."
        rec_density = 0.5
    elif avg_pearson > 0.0:
        rec = "MERGE_CAUTIOUS: Low alignment. Use DELLA density=0.3, validate after merge."
        rec_density = 0.3
    elif avg_pearson > -0.3:
        rec = "MERGE_RISKY: Near-zero or negative correlation. TIES may be safer. Test carefully."
        rec_density = 0.3
    else:
        rec = "DO_NOT_MERGE: Strong negative correlation. Specialists are incompatible. Deploy separately."
        rec_density = None

    result = {
        "adapter1": adapter1_path,
        "adapter2": adapter2_path,
        "tensors_compared": valid_count,
        "avg_l2_distance": round(avg_l2, 6),
        "avg_pearson_correlation": round(avg_pearson, 6),
        "recommendation": rec,
        "recommended_density": rec_density,
        "layer_stats": layer_stats,
    }

    # Print summary
    log.info("=" * 60)
    log.info("MERGE DIAGNOSTIC RESULTS")
    log.info(f"  Adapter 1       : {adapter1_path}")
    log.info(f"  Adapter 2       : {adapter2_path}")
    log.info(f"  Tensors compared: {valid_count}")
    log.info(f"  Avg L2 distance : {avg_l2:.6f}")
    log.info(f"  Avg Pearson corr: {avg_pearson:.6f}")
    log.info(f"  Recommendation  : {rec}")
    if rec_density:
        log.info(f"  Suggested density: {rec_density}")
    log.info("=" * 60)

    return result


# ─── Run Merge via mergekit ───────────────────────────────────────────────────

def run_mergekit(config_path: str, output_dir: str, cuda: bool = True) -> bool:
    """
    Execute mergekit with the given YAML config.

    Requires mergekit installed: pip install mergekit
    GitHub: https://github.com/arcee-ai/mergekit

    Args:
        config_path: Path to YAML config generated by generate_mergekit_yaml()
        output_dir:  Directory to write merged model
        cuda:        Use CUDA if available (True) or CPU-only (False)

    Returns:
        True if successful, False otherwise
    """
    import subprocess

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Check mergekit available
    check = subprocess.run(
        ["python3", "-c", "import mergekit; print(mergekit.__version__)"],
        capture_output=True, text=True
    )
    if check.returncode != 0:
        log.error("mergekit not found. Install: pip install mergekit")
        log.error("GitHub: https://github.com/arcee-ai/mergekit")
        return False

    mergekit_version = check.stdout.strip()
    log.info(f"mergekit version: {mergekit_version}")

    cmd = [
        "mergekit-yaml",
        str(config_path),
        str(output_dir),
        "--copy-tokenizer",
        "--lazy-unpickle",
    ]

    if cuda:
        cmd.append("--cuda")

    log.info(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode == 0:
        log.info(f"Merge complete → {output_dir}")
        return True
    else:
        log.error(f"Merge failed (exit code {result.returncode})")
        return False


# ─── Full Pipeline ────────────────────────────────────────────────────────────

def full_pipeline(
    base_model: str,
    adapter_paths: list[str],
    output_dir: str,
    method: str = "della",
    density: Optional[float] = None,
    weights: Optional[list[float]] = None,
    run: bool = False,
) -> dict:
    """
    Full merge pipeline: diagnose → recommend density → generate config → optionally run.

    Args:
        base_model:    Base model path or HF ID
        adapter_paths: List of LoRA adapter paths
        output_dir:    Output directory for merged model
        method:        Merge method (default: della)
        density:       Override density (if None, inferred from diagnostics)
        weights:       Per-adapter weights (if None, equal weights)
        run:           If True, execute mergekit after config generation

    Returns:
        Dict with config path, diagnostics, and (if run=True) success status
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    results = {
        "base_model": base_model,
        "adapters": adapter_paths,
        "method": method,
        "diagnostics": [],
    }

    # Step 1: Diagnose pairwise compatibility
    recommended_densities = []
    if len(adapter_paths) >= 2:
        log.info("Step 1: Diagnosing adapter compatibility...")
        for i in range(len(adapter_paths)):
            for j in range(i + 1, len(adapter_paths)):
                a1, a2 = adapter_paths[i], adapter_paths[j]
                diag_file = output / f"diag_{Path(a1).name}_vs_{Path(a2).name}.json"
                try:
                    diag = diagnose_adapters(a1, a2)
                    diag_file.write_text(json.dumps(diag, indent=2))
                    results["diagnostics"].append(diag)
                    if diag.get("recommended_density") is not None:
                        recommended_densities.append(diag["recommended_density"])
                    log.info(f"Diagnostic saved → {diag_file}")
                except Exception as e:
                    log.warning(f"Diagnostic failed for {a1} vs {a2}: {e}")
                    log.warning("Skipping diagnostic — proceeding with default density 0.5")
    else:
        log.info("Step 1: Single adapter pair, skipping pairwise diagnostic")

    # Step 2: Determine density
    if density is None:
        if recommended_densities:
            density = min(recommended_densities)  # conservative: use lowest recommended
            log.info(f"Step 2: Using recommended density {density:.2f} (conservative)")
        else:
            density = 0.5
            log.info("Step 2: Using default density 0.50")
    else:
        log.info(f"Step 2: Using user-specified density {density:.2f}")

    # Step 3: Generate YAML config
    config_path = output / "merge_config.yaml"
    log.info(f"Step 3: Generating mergekit YAML → {config_path}")
    yaml_content = generate_mergekit_yaml(
        base_model=base_model,
        adapter_paths=adapter_paths,
        method=method,
        density=density,
        weights=weights,
        output_path=str(config_path),
    )

    results["config_path"] = str(config_path)
    results["density_used"] = density

    # Save pipeline summary
    summary_path = output / "pipeline_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, default=str))
    log.info(f"Pipeline summary → {summary_path}")

    # Step 4: Print next steps
    log.info("")
    log.info("=" * 60)
    log.info("MERGE PIPELINE READY")
    log.info(f"  Config: {config_path}")
    log.info(f"  Method: {MERGE_METHODS[method]['name']}")
    log.info(f"  Density: {density:.2f}")
    log.info("")
    log.info("To execute the merge:")
    log.info(f"  pip install mergekit  # if not installed")
    log.info(f"  mergekit-yaml {config_path} {output_dir}/merged --copy-tokenizer --cuda")
    log.info("")
    log.info("Or use this script:")
    log.info(f"  python3 merge_models.py run --config {config_path} --output {output_dir}/merged")
    log.info("=" * 60)

    # Step 5: Optionally run
    if run:
        merged_dir = output / "merged"
        log.info(f"Step 5: Running merge → {merged_dir}")
        success = run_mergekit(str(config_path), str(merged_dir))
        results["merge_success"] = success
        results["merged_model_path"] = str(merged_dir) if success else None
    else:
        results["merge_success"] = None
        results["merged_model_path"] = None

    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Otto Model Merging Utility (DELLA / mergekit)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate DELLA merge config
  python3 merge_models.py config \\
      --base Qwen/Qwen2.5-7B-Instruct \\
      --adapters otto-lora-reasoning otto-lora-personality \\
      --output merge_output/

  # Diagnose two adapters before merging
  python3 merge_models.py diagnose \\
      --adapter1 otto-lora-reasoning \\
      --adapter2 otto-lora-personality

  # Full pipeline (diagnose + config, no actual merge)
  python3 merge_models.py pipeline \\
      --base Qwen/Qwen2.5-7B-Instruct \\
      --adapters otto-lora-reasoning otto-lora-personality otto-lora-memory \\
      --output merge_output/

  # Full pipeline WITH merge execution
  python3 merge_models.py pipeline \\
      --base Qwen/Qwen2.5-7B-Instruct \\
      --adapters otto-lora-reasoning otto-lora-personality \\
      --output merge_output/ \\
      --run

  # Run an existing config
  python3 merge_models.py run \\
      --config merge_output/merge_config.yaml \\
      --output merge_output/merged
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")
    subparsers.required = True

    # --- config subcommand ---
    config_parser = subparsers.add_parser("config", help="Generate mergekit YAML config")
    config_parser.add_argument(
        "--base", required=True,
        help="Base model path or HuggingFace ID (e.g., Qwen/Qwen2.5-7B-Instruct)"
    )
    config_parser.add_argument(
        "--adapters", nargs="+", required=True,
        help="LoRA adapter directories to merge"
    )
    config_parser.add_argument(
        "--method", choices=list(MERGE_METHODS), default="della",
        help="Merge method (default: della)"
    )
    config_parser.add_argument(
        "--density", type=float, default=0.5,
        help="Parameter density 0.0-1.0 (default: 0.5). Higher = less pruning."
    )
    config_parser.add_argument(
        "--weights", nargs="+", type=float,
        help="Per-adapter merge weights (default: equal)"
    )
    config_parser.add_argument(
        "--output", default="merge_config.yaml",
        help="Output YAML file path"
    )
    config_parser.add_argument(
        "--dtype", default="bfloat16",
        help="Model dtype (default: bfloat16)"
    )

    # --- diagnose subcommand ---
    diag_parser = subparsers.add_parser("diagnose", help="Diagnose adapter compatibility")
    diag_parser.add_argument("--adapter1", required=True, help="First adapter path")
    diag_parser.add_argument("--adapter2", required=True, help="Second adapter path")
    diag_parser.add_argument("--output", help="Save JSON diagnostic to this file")

    # --- run subcommand ---
    run_parser = subparsers.add_parser("run", help="Execute mergekit merge")
    run_parser.add_argument("--config", required=True, help="YAML config path")
    run_parser.add_argument("--output", required=True, help="Merged model output directory")
    run_parser.add_argument("--no-cuda", action="store_true", help="Disable CUDA (CPU only)")

    # --- pipeline subcommand ---
    pipe_parser = subparsers.add_parser("pipeline", help="Full diagnose + config + optional merge")
    pipe_parser.add_argument(
        "--base", required=True,
        help="Base model path or HuggingFace ID"
    )
    pipe_parser.add_argument(
        "--adapters", nargs="+", required=True,
        help="LoRA adapter directories to merge"
    )
    pipe_parser.add_argument(
        "--method", choices=list(MERGE_METHODS), default="della",
        help="Merge method (default: della)"
    )
    pipe_parser.add_argument(
        "--density", type=float,
        help="Override density (if not set, inferred from diagnostics)"
    )
    pipe_parser.add_argument(
        "--weights", nargs="+", type=float,
        help="Per-adapter merge weights (default: equal)"
    )
    pipe_parser.add_argument(
        "--output", required=True,
        help="Output directory for configs and merged model"
    )
    pipe_parser.add_argument(
        "--run", action="store_true",
        help="Execute the merge (requires mergekit)"
    )

    # --- info subcommand ---
    info_parser = subparsers.add_parser("info", help="Show merge method descriptions")
    info_parser.add_argument("--method", choices=list(MERGE_METHODS), help="Specific method info")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "config":
        yaml_str = generate_mergekit_yaml(
            base_model=args.base,
            adapter_paths=args.adapters,
            method=args.method,
            density=args.density,
            weights=args.weights,
            output_path=args.output,
            dtype=args.dtype,
        )
        print("\n--- Generated YAML ---")
        print(yaml_str)

    elif args.command == "diagnose":
        result = diagnose_adapters(args.adapter1, args.adapter2)
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2))
            log.info(f"Diagnostic saved → {args.output}")
        else:
            print(json.dumps(result, indent=2))

    elif args.command == "run":
        success = run_mergekit(
            config_path=args.config,
            output_dir=args.output,
            cuda=not args.no_cuda,
        )
        sys.exit(0 if success else 1)

    elif args.command == "pipeline":
        result = full_pipeline(
            base_model=args.base,
            adapter_paths=args.adapters,
            output_dir=args.output,
            method=args.method,
            density=args.density,
            weights=args.weights,
            run=args.run,
        )
        success = result.get("merge_success")
        if args.run and success is False:
            sys.exit(1)

    elif args.command == "info":
        if args.method:
            methods_to_show = {args.method: MERGE_METHODS[args.method]}
        else:
            methods_to_show = MERGE_METHODS

        for key, info in methods_to_show.items():
            print(f"\n{'='*50}")
            print(f"Method: {key}")
            print(f"  Name       : {info['name']}")
            print(f"  Paper      : {info['paper']}")
            print(f"  Best for   : {info['best_for']}")
            print(f"  Description: {info['description']}")

        print(f"\n{'='*50}")
        print("\nOtto Specialist Profiles:")
        for name, spec in OTTO_SPECIALISTS.items():
            print(f"\n  [{name}]")
            print(f"    Description: {spec['description']}")
            print(f"    Expected adapter: {spec['expected_adapter']}")
            print(f"    Priority: {spec['priority']}")


if __name__ == "__main__":
    main()
