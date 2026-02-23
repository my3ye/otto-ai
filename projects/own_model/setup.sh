#!/usr/bin/env bash
# Otto RunPod Environment Setup
# ===============================
# Run this ONCE after spinning up a RunPod RTX 4090 pod.
# Template: RunPod PyTorch (pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime)
#
# Usage:
#   bash setup.sh
#
# After setup completes, run:
#   python3 train.py

set -e
echo "======================================================"
echo "  Otto RunPod Setup — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "======================================================"

WORKSPACE="${WORKSPACE:-/workspace}"
cd "$WORKSPACE"

# ── 1. System packages ───────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
apt-get update -q
apt-get install -y -q git curl wget unzip rsync htop

# ── 2. Python upgrades ───────────────────────────────────────────────────────
echo "[2/6] Upgrading pip and base packages..."
pip install --upgrade pip setuptools wheel -q

# ── 3. Unsloth + dependencies ────────────────────────────────────────────────
echo "[3/6] Installing Unsloth (this may take 2-5 minutes)..."

# Check CUDA version to pick right torch build
CUDA_VER=$(python3 -c "import torch; print(torch.version.cuda.replace('.',''))" 2>/dev/null || echo "121")
echo "Detected CUDA version: $CUDA_VER"

# Install unsloth (latest stable)
pip install unsloth -q

# Fallback: If unsloth install fails, use direct repo install
if ! python3 -c "import unsloth" 2>/dev/null; then
    echo "Standard install failed — trying repo install..."
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" -q
fi

# Install supporting packages
pip install --no-deps "xformers<0.0.28" -q || echo "xformers install failed (non-critical)"
pip install "trl>=0.7.4" "peft>=0.6.0" accelerate bitsandbytes datasets transformers -q

echo "Unsloth install check..."
python3 -c "from unsloth import FastLanguageModel; print('  Unsloth OK')"

# ── 4. Hugging Face setup ────────────────────────────────────────────────────
echo "[4/6] Configuring HuggingFace cache..."
mkdir -p "$WORKSPACE/hf_cache"
export HF_HOME="$WORKSPACE/hf_cache"
echo "export HF_HOME=$WORKSPACE/hf_cache" >> ~/.bashrc

# Note: Qwen/Qwen2.5-7B-Instruct is freely accessible — no HF token needed
echo "Model: Qwen/Qwen2.5-7B-Instruct (Apache 2.0, no auth required)"

# ── 5. Upload training data ──────────────────────────────────────────────────
echo "[5/6] Checking for training data..."
if [ ! -f "$WORKSPACE/otto_training_data.jsonl" ]; then
    echo ""
    echo "  ⚠  Training data not found at $WORKSPACE/otto_training_data.jsonl"
    echo "  Upload it with:"
    echo "    scp ~/otto/projects/own_model/training_data.jsonl \\"
    echo "        <runpod-user>@<runpod-host>:$WORKSPACE/otto_training_data.jsonl"
    echo "  Or set OTTO_DATA env var to the correct path."
    echo ""
else
    COUNT=$(wc -l < "$WORKSPACE/otto_training_data.jsonl")
    echo "  Training data: $COUNT examples"
fi

# ── 6. Copy training script ──────────────────────────────────────────────────
echo "[6/6] Confirming train.py is present..."
if [ ! -f "$WORKSPACE/train.py" ]; then
    echo ""
    echo "  ⚠  train.py not found at $WORKSPACE/train.py"
    echo "  Upload it with:"
    echo "    scp ~/otto/projects/own_model/train.py \\"
    echo "        <runpod-user>@<runpod-host>:$WORKSPACE/train.py"
    echo ""
else
    echo "  train.py: present"
fi

echo ""
echo "======================================================"
echo "  Setup complete!"
echo ""
echo "  Training options:"
echo "  (A) QLoRA [default]:"
echo "      python3 $WORKSPACE/train.py"
echo ""
echo "  (B) ReasonCACHE Prefix Tuning [alternative]:"
echo "      python3 $WORKSPACE/train_prefix.py"
echo "      # 46% fewer params, 59% less data, better for limited data"
echo "      # Options:"
echo "      #   --num-virtual-tokens 100  (default, recommended)"
echo "      #   --prefix-projection       (MLP projection, closer to ReasonCACHE)"
echo ""
echo "  Logs: $WORKSPACE/training.log | $WORKSPACE/prefix_training.log"
echo "======================================================"
