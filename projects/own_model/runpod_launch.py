#!/usr/bin/env python3
"""
RunPod Launch Script — Otto GPU Training Orchestrator
======================================================
Provisions a RunPod RTX 4090 pod, uploads training assets,
runs train_gpu.py, downloads results, and terminates the pod.

Usage:
    # Dry run — shows what it would do (no pod created)
    python3 runpod_launch.py --dry-run

    # Full automated run (launches pod, trains, downloads, terminates)
    python3 runpod_launch.py

    # Custom training data / output
    python3 runpod_launch.py --data /path/to/data.jsonl --output otto-qlora-v3

    # Just provision pod, SSH in manually
    python3 runpod_launch.py --provision-only

    # Download results from existing pod (already trained)
    python3 runpod_launch.py --pod-id <POD_ID> --download-only

Requirements:
    pip install requests python-dotenv paramiko scp
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("runpod-launch")

# ─── Constants ────────────────────────────────────────────────────────────────
RUNPOD_API_URL   = "https://api.runpod.io/graphql"
OWN_MODEL_DIR    = Path(__file__).parent
ENV_PATH         = Path.home() / "memory" / ".env"
TRAINING_SCRIPT  = OWN_MODEL_DIR / "train_gpu.py"
TRAINING_DATA    = OWN_MODEL_DIR / "training_data_v2.jsonl"
REQUIREMENTS_GPU = OWN_MODEL_DIR / "requirements-gpu.txt"
MODELS_DIR       = OWN_MODEL_DIR / "models"

# RunPod config
GPU_TYPE         = "NVIDIA GeForce RTX 4090"
IMAGE_NAME       = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
CONTAINER_DISK   = 60    # GB — enough for Qwen 7B + outputs
VOLUME_DISK      = 20    # GB — persistent (results survive pod restart)
POD_NAME         = "otto-qlora-training"
WORKSPACE        = "/workspace"

# Cost guardrails
MAX_BUDGET_USD   = 5.00  # Stop if estimated cost exceeds this
POLL_INTERVAL    = 30    # seconds between status checks
MAX_WAIT_READY   = 600   # seconds to wait for pod to become ready
MAX_TRAIN_TIME   = 7200  # seconds (2hrs) before giving up


# ─── Env loading ──────────────────────────────────────────────────────────────
def load_api_key() -> str:
    """Load RUNPOD_API_KEY from ~/memory/.env."""
    api_key = os.environ.get("RUNPOD_API_KEY")
    if api_key:
        return api_key

    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith("RUNPOD_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if api_key:
                        return api_key

    raise RuntimeError(
        f"RUNPOD_API_KEY not found. Set it in {ENV_PATH} or as an env var."
    )


# ─── RunPod GraphQL client ────────────────────────────────────────────────────
class RunPodClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"{RUNPOD_API_URL}?api_key={api_key}"

    def query(self, gql: str, variables: dict = None) -> dict:
        import requests
        payload = {"query": gql}
        if variables:
            payload["variables"] = variables

        resp = requests.post(
            self.base_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")
        return data.get("data", {})

    def get_account(self) -> dict:
        return self.query("{ myself { id email currentSpendPerHr spendLimit } }")

    def get_gpu_types(self) -> list:
        data = self.query("""
        {
          gpuTypes {
            id
            displayName
            memoryInGb
            communityCloud
            secureCloud
          }
        }
        """)
        return data.get("gpuTypes", [])

    def get_pods(self) -> list:
        data = self.query("""
        {
          myself {
            pods {
              id
              name
              desiredStatus
              runtime {
                uptimeInSeconds
                ports {
                  ip
                  isIpPublic
                  privatePort
                  publicPort
                  type
                }
              }
            }
          }
        }
        """)
        return data.get("myself", {}).get("pods", [])

    def get_pod(self, pod_id: str) -> dict:
        data = self.query("""
        query getPod($podId: String!) {
          pod(input: { podId: $podId }) {
            id
            name
            desiredStatus
            lastStatusChange
            runtime {
              uptimeInSeconds
              ports {
                ip
                isIpPublic
                privatePort
                publicPort
                type
              }
            }
          }
        }
        """, {"podId": pod_id})
        return data.get("pod", {})

    def create_pod(
        self,
        name: str,
        gpu_type_id: str,
        image_name: str,
        container_disk_in_gb: int,
        volume_in_gb: int,
        ports: str = "22/tcp",
        env: dict = None,
    ) -> dict:
        """Deploy a pod on RunPod community cloud."""
        env_list = []
        if env:
            env_list = [{"key": k, "value": v} for k, v in env.items()]

        data = self.query("""
        mutation createPod(
          $name: String!
          $gpuTypeId: String!
          $imageName: String!
          $containerDiskInGb: Int!
          $volumeInGb: Int!
          $ports: String
          $env: [PodEnvInput]
        ) {
          podFindAndDeployOnDemand(input: {
            name: $name
            gpuTypeId: $gpuTypeId
            imageName: $imageName
            containerDiskInGb: $containerDiskInGb
            volumeInGb: $volumeInGb
            cloudType: COMMUNITY
            gpuCount: 1
            ports: $ports
            env: $env
          }) {
            id
            imageName
            desiredStatus
            runtime {
              ports {
                ip
                isIpPublic
                privatePort
                publicPort
                type
              }
            }
          }
        }
        """, {
            "name"                : name,
            "gpuTypeId"           : gpu_type_id,
            "imageName"           : image_name,
            "containerDiskInGb"   : container_disk_in_gb,
            "volumeInGb"          : volume_in_gb,
            "ports"               : ports,
            "env"                 : env_list if env_list else None,
        })
        return data.get("podFindAndDeployOnDemand", {})

    def terminate_pod(self, pod_id: str) -> bool:
        data = self.query("""
        mutation terminatePod($podId: String!) {
          podTerminate(input: { podId: $podId })
        }
        """, {"podId": pod_id})
        return True  # If no exception, it worked


# ─── SSH helpers ──────────────────────────────────────────────────────────────
def get_ssh_info(pod: dict) -> tuple[str, int]:
    """Extract SSH IP and port from pod runtime."""
    ports = pod.get("runtime", {}).get("ports", []) or []
    for p in ports:
        if p.get("privatePort") == 22 and p.get("type") == "tcp":
            ip   = p.get("ip")
            port = p.get("publicPort")
            if ip and port:
                return ip, int(port)
    return None, None


def ssh_exec(host: str, port: int, cmd: str, timeout: int = 300) -> tuple[int, str, str]:
    """Execute a command on remote host via ssh CLI."""
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=30",
        "-p", str(port),
        f"root@{host}",
        cmd,
    ]
    result = subprocess.run(
        ssh_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def scp_upload(host: str, port: int, local_path: str, remote_path: str) -> bool:
    """Upload a file to remote host."""
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-P", str(port),
        str(local_path),
        f"root@{host}:{remote_path}",
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        log.error(f"SCP upload failed: {result.stderr}")
        return False
    return True


def scp_download(host: str, port: int, remote_path: str, local_path: str) -> bool:
    """Download file/dir from remote host."""
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-r",
        "-P", str(port),
        f"root@{host}:{remote_path}",
        str(local_path),
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        log.error(f"SCP download failed: {result.stderr}")
        return False
    return True


# ─── Main orchestration ────────────────────────────────────────────────────────
def wait_for_pod_ready(client: RunPodClient, pod_id: str, timeout: int = MAX_WAIT_READY) -> dict:
    """Poll until pod has SSH port available."""
    log.info(f"Waiting for pod {pod_id} to be ready (max {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        pod = client.get_pod(pod_id)
        status = pod.get("desiredStatus", "UNKNOWN")
        ports  = pod.get("runtime", {}).get("ports", []) or []
        ssh_ip, ssh_port = get_ssh_info(pod)

        log.info(f"  Status: {status} | SSH: {ssh_ip}:{ssh_port}")

        if ssh_ip and ssh_port:
            log.info("Pod is ready!")
            return pod

        if status in ("EXITED", "TERMINATED", "FAILED"):
            raise RuntimeError(f"Pod entered terminal state: {status}")

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Pod not ready after {timeout}s")


def install_deps(host: str, port: int) -> bool:
    """Install Python dependencies on the pod."""
    log.info("Installing GPU training dependencies...")

    install_cmd = """pip install -q \
        transformers==4.48.3 \
        peft==0.14.0 \
        bitsandbytes==0.45.3 \
        trl==0.14.0 \
        accelerate==1.3.0 \
        datasets==3.3.2 \
        sentencepiece \
        protobuf \
        && echo DEPS_OK"""

    code, stdout, stderr = ssh_exec(host, port, install_cmd, timeout=600)
    if "DEPS_OK" not in stdout:
        log.error(f"Dep install failed:\n{stderr[-2000:]}")
        return False
    log.info("Dependencies installed.")
    return True


def run_training(host: str, port: int, data_remote: str, output_remote: str) -> bool:
    """Launch training in background, poll for completion."""
    log.info("Launching training job (background nohup)...")

    launch_cmd = (
        f"cd {WORKSPACE} && "
        f"nohup python3 train_gpu.py "
        f"--data {data_remote} "
        f"--output {output_remote} "
        f"> training_gpu.log 2>&1 & "
        f"echo $! > train.pid && echo LAUNCHED"
    )
    code, stdout, stderr = ssh_exec(host, port, launch_cmd, timeout=60)
    if "LAUNCHED" not in stdout:
        log.error(f"Failed to launch training: {stderr}")
        return False

    log.info("Training launched. Polling for completion...")

    deadline = time.time() + MAX_TRAIN_TIME
    last_loss = None
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)

        # Check if process is still running
        code, stdout, _ = ssh_exec(
            host, port,
            "cat train.pid | xargs ps -p 2>/dev/null | grep python || echo DONE",
            timeout=30,
        )
        proc_running = "python" in stdout

        # Get last log line
        code2, log_tail, _ = ssh_exec(
            host, port, f"tail -5 {WORKSPACE}/training_gpu.log 2>/dev/null", timeout=30
        )
        log.info(f"  Process: {'RUNNING' if proc_running else 'DONE'} | Log: {log_tail.strip()[-200:]}")

        if not proc_running:
            # Check if summary exists
            code3, summary_out, _ = ssh_exec(
                host, port,
                f"cat {output_remote}/training_summary.json 2>/dev/null || echo NOSUMMARY",
                timeout=30,
            )
            if "NOSUMMARY" not in summary_out and summary_out.strip():
                summary = json.loads(summary_out)
                log.info(f"Training complete! Status: {summary.get('status')} | Loss: {summary.get('final_loss')}")
                return True
            else:
                log.error("Process ended but no summary found — training may have failed")
                # Show full log for debugging
                ssh_exec(host, port, f"tail -50 {WORKSPACE}/training_gpu.log", timeout=30)
                return False

    log.error(f"Training timed out after {MAX_TRAIN_TIME/3600:.1f} hours")
    return False


def download_results(host: str, port: int, output_remote: str, local_output: str) -> bool:
    """Download training results from pod."""
    log.info(f"Downloading results from pod: {output_remote} → {local_output}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Download adapter (small, always download)
    adapter_remote = f"{output_remote}/lora_adapter"
    adapter_local  = Path(local_output) / "lora_adapter"
    ok1 = scp_download(host, port, adapter_remote, str(adapter_local))

    # Download summary
    summary_remote = f"{output_remote}/training_summary.json"
    summary_local  = Path(local_output) / "training_summary.json"
    ok2 = scp_download(host, port, summary_remote, str(summary_local))

    # Download training log
    log_remote = f"{WORKSPACE}/training_gpu.log"
    log_local  = Path(local_output) / "training_gpu.log"
    scp_download(host, port, log_remote, str(log_local))

    # Note: skip merged_model download by default (it's ~14GB)
    # User can manually scp if needed
    log.info("NOTE: merged_model not auto-downloaded (too large). Download manually if needed:")
    log.info(f"  scp -P {port} -r root@{host}:{output_remote}/merged_model {local_output}/merged_model")

    return ok1 and ok2


def main():
    parser = argparse.ArgumentParser(description="RunPod launch orchestrator for Otto GPU training")
    parser.add_argument("--dry-run",       action="store_true", help="Show plan without launching")
    parser.add_argument("--provision-only",action="store_true", help="Provision pod but don't run training")
    parser.add_argument("--download-only", action="store_true", help="Download results from existing pod")
    parser.add_argument("--pod-id",        type=str,            help="Existing pod ID (for download-only)")
    parser.add_argument("--data",          type=str, default=str(TRAINING_DATA), help="Training data path")
    parser.add_argument("--output",        type=str, default="otto-qlora-v2",    help="Output directory name")
    args = parser.parse_args()

    log.info("=" * 65)
    log.info("RunPod Launch — Otto GPU Training Orchestrator")
    log.info(f"Started  : {datetime.utcnow().isoformat()}Z")
    log.info(f"Dry run  : {args.dry_run}")
    log.info("=" * 65)

    # ── Load API key ───────────────────────────────────────────────────────────
    try:
        api_key = load_api_key()
        log.info(f"API key  : {api_key[:12]}...{api_key[-4:]}")
    except RuntimeError as e:
        log.error(str(e))
        sys.exit(1)

    client = RunPodClient(api_key)

    # ── Verify account ─────────────────────────────────────────────────────────
    account = client.get_account()["myself"]
    log.info(f"Account  : {account['email']}")
    log.info(f"Spend/hr : ${account['currentSpendPerHr']:.4f}")
    log.info(f"Limit    : ${account['spendLimit']:.0f}")

    # ── Files to upload ────────────────────────────────────────────────────────
    data_file = Path(args.data)
    if not data_file.exists():
        # Fallback to training_data_final.jsonl
        data_file = OWN_MODEL_DIR / "training_data_final.jsonl"
        log.warning(f"Primary data not found, using: {data_file}")

    output_remote = f"{WORKSPACE}/{args.output}"
    data_remote   = f"{WORKSPACE}/training_data_v2.jsonl"

    log.info(f"Training data : {data_file} ({data_file.stat().st_size / 1024:.1f} KB)")
    log.info(f"Remote output : {output_remote}")
    log.info(f"GPU type      : {GPU_TYPE}")
    log.info(f"Image         : {IMAGE_NAME}")
    log.info(f"Est. cost     : $0.50-1.00 @ $0.34/hr")

    if args.dry_run:
        log.info("\n[DRY RUN] Would execute:")
        log.info(f"  1. Create pod: {POD_NAME} ({GPU_TYPE}, {CONTAINER_DISK}GB disk)")
        log.info(f"  2. Upload: train_gpu.py, {data_file.name}")
        log.info(f"  3. Install deps: transformers, peft, bitsandbytes, trl, accelerate")
        log.info(f"  4. Run: python3 train_gpu.py --data {data_remote} --output {output_remote}")
        log.info(f"  5. Download: {output_remote}/lora_adapter → {MODELS_DIR}/{args.output}/lora_adapter")
        log.info(f"  6. Terminate pod")
        log.info("\n[DRY RUN] No pod created. Pass --no-dry-run or remove --dry-run to launch.")
        return

    # ── Download only mode ─────────────────────────────────────────────────────
    if args.download_only:
        if not args.pod_id:
            log.error("--download-only requires --pod-id")
            sys.exit(1)
        pod = client.get_pod(args.pod_id)
        ssh_ip, ssh_port = get_ssh_info(pod)
        if not ssh_ip:
            log.error("Pod has no SSH port available")
            sys.exit(1)
        local_output = str(MODELS_DIR / args.output)
        download_results(ssh_ip, ssh_port, output_remote, local_output)
        log.info("Download complete.")
        return

    # ── Create pod ─────────────────────────────────────────────────────────────
    log.info(f"\nCreating RunPod pod: {POD_NAME}...")
    try:
        pod = client.create_pod(
            name                  = POD_NAME,
            gpu_type_id           = GPU_TYPE,
            image_name            = IMAGE_NAME,
            container_disk_in_gb  = CONTAINER_DISK,
            volume_in_gb          = VOLUME_DISK,
            ports                 = "22/tcp",
        )
    except Exception as e:
        log.error(f"Failed to create pod: {e}")
        log.error("If community cloud unavailable, try: reduce container disk, or retry later")
        sys.exit(1)

    pod_id = pod.get("id")
    if not pod_id:
        log.error(f"Pod creation failed: {pod}")
        sys.exit(1)

    log.info(f"Pod created! ID: {pod_id}")
    log.info(f"Monitor at: https://www.runpod.io/console/pods/{pod_id}")

    # ── Wait for ready ─────────────────────────────────────────────────────────
    try:
        pod = wait_for_pod_ready(client, pod_id)
    except Exception as e:
        log.error(f"Pod not ready: {e}")
        log.info(f"Terminating pod {pod_id}...")
        client.terminate_pod(pod_id)
        sys.exit(1)

    ssh_ip, ssh_port = get_ssh_info(pod)
    log.info(f"SSH: {ssh_ip}:{ssh_port}")
    log.info(f"  ssh -p {ssh_port} root@{ssh_ip}")

    if args.provision_only:
        log.info("\n[PROVISION ONLY] Pod is ready. SSH in manually to continue.")
        log.info(f"  ssh -p {ssh_port} root@{ssh_ip}")
        log.info(f"  scp -P {ssh_port} {TRAINING_SCRIPT} root@{ssh_ip}:{WORKSPACE}/")
        log.info(f"  scp -P {ssh_port} {data_file} root@{ssh_ip}:{data_remote}")
        log.info(f"  python3 train_gpu.py --data {data_remote} --output {output_remote}")
        log.info(f"\nTerminate when done:")
        log.info(f"  python3 runpod_launch.py --pod-id {pod_id} --download-only --output {args.output}")
        return

    # Give SSH service a moment to fully start
    time.sleep(15)

    # ── Upload files ───────────────────────────────────────────────────────────
    log.info("Uploading training files...")
    ok1 = scp_upload(ssh_ip, ssh_port, str(TRAINING_SCRIPT), f"{WORKSPACE}/train_gpu.py")
    ok2 = scp_upload(ssh_ip, ssh_port, str(data_file), data_remote)

    if not (ok1 and ok2):
        log.error("File upload failed. Terminating pod.")
        client.terminate_pod(pod_id)
        sys.exit(1)
    log.info("Files uploaded.")

    # ── Install dependencies ───────────────────────────────────────────────────
    if not install_deps(ssh_ip, ssh_port):
        log.error("Dep install failed. Terminating pod.")
        client.terminate_pod(pod_id)
        sys.exit(1)

    # ── Run training ───────────────────────────────────────────────────────────
    training_ok = run_training(ssh_ip, ssh_port, data_remote, output_remote)

    # ── Download results (even if training partially failed) ───────────────────
    local_output = str(MODELS_DIR / args.output)
    download_results(ssh_ip, ssh_port, output_remote, local_output)

    # ── Terminate pod ──────────────────────────────────────────────────────────
    log.info(f"Terminating pod {pod_id}...")
    try:
        client.terminate_pod(pod_id)
        log.info("Pod terminated. Billing stopped.")
    except Exception as e:
        log.warning(f"Terminate call failed (check manually): {e}")
        log.warning(f"IMPORTANT: Manually terminate pod {pod_id} at runpod.io to stop billing!")

    # ── Final summary ──────────────────────────────────────────────────────────
    log.info("=" * 65)
    if training_ok:
        log.info("TRAINING COMPLETE — SUCCESS")
        log.info(f"  Results   : {local_output}")
        log.info(f"  Adapter   : {local_output}/lora_adapter")
        log.info(f"  Summary   : {local_output}/training_summary.json")
        log.info("")
        log.info("Next steps on otto-machine:")
        log.info("  1. Review training_summary.json and training_gpu.log")
        log.info("  2. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        log.info("  3. Merge + deploy: see merge_models.py")
    else:
        log.error("TRAINING FAILED OR TIMED OUT")
        log.info("  Check logs in the downloaded results directory")
        log.info("  Adapter may still be partially saved")
    log.info("=" * 65)


if __name__ == "__main__":
    main()
