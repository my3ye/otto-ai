#!/usr/bin/env python3
"""
launch_and_train.py — Provision RunPod pod, upload files, start training in background.
Does NOT wait for training to complete. Does NOT terminate the pod.
Training continues on RunPod after this script exits.

Usage:
    python3 launch_and_train.py
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("launch-train")

# ── Config ───────────────────────────────────────────────────────────────────
RUNPOD_API_URL  = "https://api.runpod.io/graphql"
OWN_MODEL_DIR   = Path(__file__).parent
ENV_PATH        = Path.home() / "memory" / ".env"
SSH_KEY         = Path.home() / ".ssh" / "runpod_id_rsa"
SSH_PUB_KEY     = Path.home() / ".ssh" / "runpod_id_rsa.pub"
TRAINING_SCRIPT = OWN_MODEL_DIR / "train_gpu.py"
TRAINING_DATA   = OWN_MODEL_DIR / "training_data_v3.jsonl"

# Training parameters (matching task spec)
LORA_RANK    = 16
LORA_ALPHA   = 32
EPOCHS       = 3
LR           = "1e-4"
BATCH        = 1
GRAD_ACCUM   = 4

GPU_PREFERENCES = [
    "NVIDIA GeForce RTX 4090",   # 24GB, ~$0.34/hr community
    "NVIDIA GeForce RTX 3090",   # 24GB, cheaper
    "NVIDIA L40",                # 48GB
    "NVIDIA A100 80GB PCIe",     # 80GB, expensive but powerful
]
IMAGE_NAME      = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
CONTAINER_DISK  = 50
VOLUME_DISK     = 10
POD_NAME        = "otto-qwen-qlora"
WORKSPACE       = "/workspace"

POLL_INTERVAL   = 20
MAX_WAIT_READY  = 480   # 8 minutes to wait for pod


def load_api_key() -> str:
    key = os.environ.get("RUNPOD_API_KEY")
    if key:
        return key
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("RUNPOD_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"\'')
                if key:
                    return key
    raise RuntimeError("RUNPOD_API_KEY not found")


def runpod_query(api_key: str, gql: str, variables: dict = None) -> dict:
    import urllib.request
    import urllib.error
    payload = {"query": gql}
    if variables:
        payload["variables"] = variables
    data = json.dumps(payload).encode()
    url = f"{RUNPOD_API_URL}?api_key={api_key}"
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}")
    if "errors" in result:
        raise RuntimeError(f"GraphQL error: {result['errors']}")
    return result.get("data", {})


def create_pod(api_key: str, gpu_type_id: str, public_key: str) -> dict:
    """Create RunPod pod with SSH public key injected as env var."""
    gql = """
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
    """
    variables = {
        "name": POD_NAME,
        "gpuTypeId": gpu_type_id,
        "imageName": IMAGE_NAME,
        "containerDiskInGb": CONTAINER_DISK,
        "volumeInGb": VOLUME_DISK,
        "ports": "22/tcp",
        "env": [{"key": "PUBLIC_KEY", "value": public_key}],
    }
    data = runpod_query(api_key, gql, variables)
    return data.get("podFindAndDeployOnDemand", {})


def get_pod(api_key: str, pod_id: str) -> dict:
    gql = """
    query getPod($podId: String!) {
      pod(input: { podId: $podId }) {
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
    """
    data = runpod_query(api_key, gql, {"podId": pod_id})
    return data.get("pod", {})


def terminate_pod(api_key: str, pod_id: str):
    gql = """
    mutation terminatePod($podId: String!) {
      podTerminate(input: { podId: $podId })
    }
    """
    runpod_query(api_key, gql, {"podId": pod_id})
    log.info(f"Pod {pod_id} terminated.")


def get_ssh_info(pod: dict) -> tuple:
    ports = pod.get("runtime", {}).get("ports", []) or []
    for p in ports:
        if p.get("privatePort") == 22 and p.get("type") == "tcp":
            ip = p.get("ip")
            port = p.get("publicPort")
            if ip and port:
                return ip, int(port)
    return None, None


def ssh_exec(host: str, port: int, cmd: str, timeout: int = 120) -> tuple:
    ssh_cmd = [
        "ssh",
        "-i", str(SSH_KEY),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=20",
        "-p", str(port),
        f"root@{host}",
        cmd,
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def scp_upload(host: str, port: int, local_path: str, remote_path: str, timeout: int = 120) -> bool:
    scp_cmd = [
        "scp",
        "-i", str(SSH_KEY),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-P", str(port),
        str(local_path),
        f"root@{host}:{remote_path}",
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        log.error(f"SCP upload failed: {result.stderr}")
        return False
    return True


def wait_for_pod_ready(api_key: str, pod_id: str, timeout: int = MAX_WAIT_READY) -> dict:
    log.info(f"Waiting for pod {pod_id} to be ready (max {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        pod = get_pod(api_key, pod_id)
        status = pod.get("desiredStatus", "UNKNOWN")
        ssh_ip, ssh_port = get_ssh_info(pod)
        log.info(f"  Status: {status} | SSH: {ssh_ip}:{ssh_port}")

        if ssh_ip and ssh_port:
            log.info("Pod has SSH port. Testing SSH connection...")
            # Test if SSH actually accepts connections
            for attempt in range(5):
                try:
                    rc, out, err = ssh_exec(ssh_ip, ssh_port, "echo ALIVE", timeout=30)
                    if rc == 0 and "ALIVE" in out:
                        log.info("SSH connection successful!")
                        return pod
                except subprocess.TimeoutExpired:
                    pass
                log.info(f"  SSH attempt {attempt+1}/5 failed, retrying in 15s...")
                time.sleep(15)

        if status in ("EXITED", "TERMINATED", "FAILED"):
            raise RuntimeError(f"Pod entered terminal state: {status}")

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Pod not ready after {timeout}s")


def install_deps(host: str, port: int) -> bool:
    log.info("Installing GPU training dependencies...")
    install_cmd = """
pip install -q \
    transformers==4.48.3 \
    peft==0.14.0 \
    bitsandbytes==0.45.3 \
    trl==0.14.0 \
    accelerate==1.3.0 \
    datasets==3.3.2 \
    sentencepiece \
    protobuf \
    && echo DEPS_OK
""".strip()
    rc, out, err = ssh_exec(host, port, install_cmd, timeout=600)
    if "DEPS_OK" not in out:
        log.error(f"Dep install failed (rc={rc}):\nSTDOUT: {out[-1000:]}\nSTDERR: {err[-500:]}")
        return False
    log.info("Dependencies installed successfully.")
    return True


def launch_training_background(host: str, port: int) -> bool:
    """Launch training in background — nohup so it persists after SSH exit."""
    log.info("Launching Qwen 2.5 7B QLoRA training in background...")

    launch_cmd = (
        f"cd {WORKSPACE} && "
        f"nohup python3 train_gpu.py "
        f"--data /workspace/training_data_v3.jsonl "
        f"--output /workspace/otto-qlora-qwen7b "
        f"> /workspace/training_gpu.log 2>&1 & "
        f"echo $! > /workspace/train.pid && "
        f"echo LAUNCHED:$!"
    )

    rc, out, err = ssh_exec(host, port, launch_cmd, timeout=60)
    if "LAUNCHED:" not in out:
        log.error(f"Failed to launch training: rc={rc}\nout: {out}\nerr: {err}")
        return False

    pid = out.strip().split("LAUNCHED:")[-1].strip()
    log.info(f"Training launched as background process. PID: {pid}")
    return True


def verify_training_started(host: str, port: int, wait_seconds: int = 90) -> dict:
    """Wait for training to start and verify first steps are running."""
    log.info(f"Waiting {wait_seconds}s for training to initialize...")
    time.sleep(wait_seconds)

    # Check if process is still running
    rc, out, err = ssh_exec(host, port, "cat /workspace/train.pid | xargs ps -p 2>/dev/null | grep python || echo NOTRUNNING", timeout=30)
    is_running = "python" in out

    # Get log output
    rc2, log_out, _ = ssh_exec(host, port, "tail -30 /workspace/training_gpu.log 2>/dev/null || echo NOLOG", timeout=30)

    # Check for step progress
    rc3, step_out, _ = ssh_exec(host, port, "grep -c 'step' /workspace/training_gpu.log 2>/dev/null || echo 0", timeout=30)
    steps_logged = step_out.strip()

    log.info(f"Process running: {is_running}")
    log.info(f"Steps logged: {steps_logged}")
    log.info(f"Recent log:\n{log_out[-500:]}")

    # Check if failed immediately
    if not is_running:
        rc4, full_log, _ = ssh_exec(host, port, "cat /workspace/training_gpu.log 2>/dev/null", timeout=30)
        log.error(f"Process died. Full log:\n{full_log[-2000:]}")

    return {
        "is_running": is_running,
        "steps_logged": steps_logged,
        "recent_log": log_out[-500:],
    }


def main():
    log.info("=" * 65)
    log.info("Otto — Qwen 2.5 7B QLoRA RunPod Launcher")
    log.info(f"Started: {datetime.utcnow().isoformat()}Z")
    log.info("=" * 65)

    # Load API key and SSH public key
    api_key = load_api_key()
    log.info(f"API key: {api_key[:12]}...{api_key[-4:]}")

    public_key = SSH_PUB_KEY.read_text().strip()
    log.info(f"SSH public key loaded: {public_key[:40]}...")

    if not TRAINING_SCRIPT.exists():
        log.error(f"Training script not found: {TRAINING_SCRIPT}")
        sys.exit(1)

    if not TRAINING_DATA.exists():
        log.error(f"Training data not found: {TRAINING_DATA}")
        sys.exit(1)

    data_size_kb = TRAINING_DATA.stat().st_size / 1024
    log.info(f"Training data: {TRAINING_DATA} ({data_size_kb:.1f} KB)")

    # Try GPUs in preference order
    pod = None
    gpu_used = None
    for gpu in GPU_PREFERENCES:
        log.info(f"\nAttempting pod creation with GPU: {gpu}")
        try:
            pod = create_pod(api_key, gpu, public_key)
            if pod and pod.get("id"):
                gpu_used = gpu
                log.info(f"Pod created! ID: {pod['id']}")
                break
        except Exception as e:
            log.warning(f"Failed with {gpu}: {e}")
            continue

    if not pod or not pod.get("id"):
        log.error("All GPU types failed. Cannot provision pod.")
        sys.exit(1)

    pod_id = pod["id"]
    log.info(f"Pod ID: {pod_id}")
    log.info(f"GPU: {gpu_used}")
    log.info(f"Monitor: https://www.runpod.io/console/pods/{pod_id}")

    # Wait for pod to be ready
    try:
        pod = wait_for_pod_ready(api_key, pod_id)
    except Exception as e:
        log.error(f"Pod not ready: {e}")
        log.info("Terminating pod to avoid billing...")
        try:
            terminate_pod(api_key, pod_id)
        except:
            pass
        sys.exit(1)

    ssh_ip, ssh_port = get_ssh_info(pod)
    log.info(f"SSH: root@{ssh_ip} -p {ssh_port}")
    log.info(f"  ssh -i ~/.ssh/runpod_id_rsa -p {ssh_port} root@{ssh_ip}")

    # Give SSH a moment to fully settle
    time.sleep(10)

    # Upload training files
    log.info("\nUploading training files...")
    ok1 = scp_upload(ssh_ip, ssh_port, str(TRAINING_SCRIPT), f"{WORKSPACE}/train_gpu.py")
    if not ok1:
        log.error("Failed to upload train_gpu.py. Terminating pod.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)
    log.info("  train_gpu.py uploaded")

    ok2 = scp_upload(ssh_ip, ssh_port, str(TRAINING_DATA), f"{WORKSPACE}/training_data_v3.jsonl", timeout=180)
    if not ok2:
        log.error("Failed to upload training_data_v3.jsonl. Terminating pod.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)
    log.info("  training_data_v3.jsonl uploaded")

    # Install dependencies
    if not install_deps(ssh_ip, ssh_port):
        log.error("Dependency installation failed. Terminating pod.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)

    # Launch training in background
    if not launch_training_background(ssh_ip, ssh_port):
        log.error("Failed to start training. Terminating pod.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)

    # Verify training started
    log.info("\nVerifying training initialization...")
    status = verify_training_started(ssh_ip, ssh_port, wait_seconds=90)

    # Save pod info for future reference
    pod_info = {
        "pod_id": pod_id,
        "gpu": gpu_used,
        "ssh_host": ssh_ip,
        "ssh_port": ssh_port,
        "ssh_key": str(SSH_KEY),
        "launched_at": datetime.utcnow().isoformat() + "Z",
        "training_running": status["is_running"],
        "steps_logged": status["steps_logged"],
        "model": "Qwen/Qwen2.5-7B",
        "lora_rank": LORA_RANK,
        "epochs": EPOCHS,
        "training_data": "training_data_v3.jsonl",
        "output_dir": "/workspace/otto-qlora-qwen7b",
        "log_file": "/workspace/training_gpu.log",
        "monitor_url": f"https://www.runpod.io/console/pods/{pod_id}",
        "ssh_command": f"ssh -i ~/.ssh/runpod_id_rsa -p {ssh_port} root@{ssh_ip}",
        "tail_command": f"ssh -i ~/.ssh/runpod_id_rsa -p {ssh_port} root@{ssh_ip} 'tail -f /workspace/training_gpu.log'",
    }

    info_path = OWN_MODEL_DIR / "runpod_pod_info.json"
    with open(info_path, "w") as f:
        json.dump(pod_info, f, indent=2)
    log.info(f"\nPod info saved to: {info_path}")

    log.info("\n" + "=" * 65)
    if status["is_running"]:
        log.info("SUCCESS — Training is running on RunPod!")
    else:
        log.warning("WARNING — Training may not have started properly")
        log.warning("Check the log file via SSH for errors")
    log.info(f"Pod ID    : {pod_id}")
    log.info(f"GPU       : {gpu_used}")
    log.info(f"SSH cmd   : ssh -i ~/.ssh/runpod_id_rsa -p {ssh_port} root@{ssh_ip}")
    log.info(f"Watch log : ssh -i ~/.ssh/runpod_id_rsa -p {ssh_port} root@{ssh_ip} 'tail -f /workspace/training_gpu.log'")
    log.info(f"Est cost  : ~$0.50-1.00 total (RTX 4090 @ $0.34/hr)")
    log.info(f"Est time  : ~2-3 hours for 3 epochs on 1856 examples")
    log.info("\nIMPORTANT: Pod is NOT terminated. Training continues on RunPod.")
    log.info("           Download results when done:")
    log.info(f"           scp -i ~/.ssh/runpod_id_rsa -r -P {ssh_port} root@{ssh_ip}:/workspace/otto-qlora-qwen7b {OWN_MODEL_DIR}/models/")
    log.info("=" * 65)

    return pod_info


if __name__ == "__main__":
    main()
