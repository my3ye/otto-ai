#!/usr/bin/env python3
"""
pod_launcher.py — Thin RunPod pod launcher using subprocess curl.
Uses curl (not urllib/requests) to avoid Cloudflare bot blocks.

v4: Uses training_data_v4.jsonl (3664 examples), 10-min provisioning timeout,
    spot pricing priority.
"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pod-launcher")

ENV_PATH    = Path.home() / "memory" / ".env"
SSH_KEY     = Path.home() / ".ssh" / "runpod_id_rsa"
SSH_PUB_KEY = Path.home() / ".ssh" / "runpod_id_rsa.pub"
OWN_MODEL   = Path(__file__).parent
WORKSPACE   = "/workspace"

POLL_INTERVAL           = 20
MAX_PROVISIONING_WAIT   = 600   # 10 min — if runtime still null, give up on this GPU
MAX_SSH_WAIT            = 300   # 5 min — once runtime appears, wait for SSH to respond


def load_api_key():
    key = os.environ.get("RUNPOD_API_KEY")
    if key:
        return key
    for line in open(ENV_PATH):
        line = line.strip()
        if line.startswith("RUNPOD_API_KEY="):
            k = line.split("=", 1)[1].strip().strip("\"'")
            if k:
                return k
    raise RuntimeError("RUNPOD_API_KEY not found")


def runpod_gql(api_key, query, variables=None):
    """Execute RunPod GraphQL query via subprocess curl."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    payload_json = json.dumps(payload)

    cmd = [
        "curl", "-s", "--max-time", "30",
        "-X", "POST",
        f"https://api.runpod.io/graphql?api_key={api_key}",
        "-H", "Content-Type: application/json",
        "-d", payload_json,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON response: {result.stdout[:500]}")

    if "errors" in data:
        msg = data["errors"][0].get("message", str(data["errors"]))
        raise RuntimeError(f"GraphQL error: {msg}")

    return data.get("data", {})


def create_pod(api_key, gpu_type_id, public_key, name="otto-qwen-qlora",
               container_disk=60, volume_disk=20, cloud_type="COMMUNITY"):
    """Create pod with cloud type fallback. Tries COMMUNITY first, falls back to SECURE."""
    safe_key = public_key.replace("\\", "\\\\").replace('"', '\\"')
    safe_gpu = gpu_type_id.replace('"', '\\"')
    safe_name = name.replace('"', '\\"')

    for ct in ([cloud_type, "SECURE"] if cloud_type == "COMMUNITY" else [cloud_type]):
        log.info(f"Trying cloudType={ct} for {gpu_type_id}")
        query = f"""
        mutation {{
          podFindAndDeployOnDemand(input: {{
            name: "{safe_name}"
            gpuTypeId: "{safe_gpu}"
            imageName: "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
            containerDiskInGb: {container_disk}
            volumeInGb: {volume_disk}
            cloudType: {ct}
            gpuCount: 1
            ports: "22/tcp"
            env: [{{key: "PUBLIC_KEY", value: "{safe_key}"}}]
          }}) {{
            id
            imageName
            desiredStatus
            runtime {{
              ports {{
                ip
                isIpPublic
                privatePort
                publicPort
                type
              }}
            }}
          }}
        }}
        """
        try:
            data = runpod_gql(api_key, query)
            result = data.get("podFindAndDeployOnDemand", {})
            if result:
                log.info(f"Pod created on {ct}: {result.get('id')}")
                return result
        except RuntimeError as e:
            log.warning(f"cloudType={ct} failed: {e}")
            if ct == "SECURE":
                raise
            continue
    raise RuntimeError("Pod creation failed on all cloud types")


def get_pod(api_key, pod_id):
    query = """
    query GetPod($podId: String!) {
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
    data = runpod_gql(api_key, query, {"podId": pod_id})
    return data.get("pod", {})


def terminate_pod(api_key, pod_id):
    query = """
    mutation TerminatePod($podId: String!) {
      podTerminate(input: { podId: $podId })
    }
    """
    runpod_gql(api_key, query, {"podId": pod_id})
    log.info(f"Pod {pod_id} terminated")


def get_ssh_info(pod):
    ports = (pod.get("runtime") or {}).get("ports", []) or []
    for p in ports:
        if p.get("privatePort") == 22 and p.get("type") == "tcp":
            ip = p.get("ip")
            port = p.get("publicPort")
            if ip and port:
                return ip, int(port)
    return None, None


def ssh(host, port, cmd, timeout=120):
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


def scp(host, port, local, remote, timeout=300):
    scp_cmd = [
        "scp",
        "-i", str(SSH_KEY),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-P", str(port),
        str(local),
        f"root@{host}:{remote}",
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        log.error(f"SCP failed: {result.stderr}")
    return result.returncode == 0


def wait_for_pod(api_key, pod_id,
                 provisioning_timeout=MAX_PROVISIONING_WAIT,
                 ssh_timeout=MAX_SSH_WAIT):
    """
    Two-phase wait:
      Phase 1: Wait up to provisioning_timeout for runtime to appear (SSH info populated).
               If runtime is still null after this, the GPU is stuck — terminate immediately.
      Phase 2: Once runtime appears, wait up to ssh_timeout for SSH to respond.
    """
    log.info(f"Waiting for pod {pod_id} to provision (max {provisioning_timeout}s)...")
    prov_deadline = time.time() + provisioning_timeout
    runtime_appeared = False

    while time.time() < prov_deadline:
        pod = get_pod(api_key, pod_id)
        status = pod.get("desiredStatus", "?")
        ip, port = get_ssh_info(pod)
        runtime = pod.get("runtime")
        log.info(f"  Status={status} runtime={'yes' if runtime else 'null'} SSH={ip}:{port}")

        if status in ("EXITED", "TERMINATED", "FAILED"):
            raise RuntimeError(f"Pod in terminal state: {status}")

        if ip and port:
            runtime_appeared = True
            log.info(f"Runtime appeared! SSH endpoint: {ip}:{port}")
            break

        elapsed = time.time() - (prov_deadline - provisioning_timeout)
        log.info(f"  Still provisioning... ({elapsed:.0f}s elapsed, max {provisioning_timeout}s)")
        time.sleep(POLL_INTERVAL)

    if not runtime_appeared:
        raise TimeoutError(
            f"Pod {pod_id} stuck provisioning — runtime never appeared after {provisioning_timeout}s. "
            "GPU likely unavailable. Terminating."
        )

    # Phase 2: SSH readiness
    log.info(f"Runtime appeared. Waiting up to {ssh_timeout}s for SSH to respond...")
    ssh_deadline = time.time() + ssh_timeout
    while time.time() < ssh_deadline:
        pod = get_pod(api_key, pod_id)
        ip, port = get_ssh_info(pod)
        if ip and port:
            for attempt in range(3):
                try:
                    rc, out, err = ssh(ip, port, "echo ALIVE", timeout=25)
                    if rc == 0 and "ALIVE" in out:
                        log.info("SSH is live!")
                        return pod
                    log.info(f"  SSH attempt {attempt+1}/3 failed (rc={rc}): {err[:100]}")
                except Exception as e:
                    log.info(f"  SSH attempt {attempt+1}/3 exception: {e}")
                time.sleep(10)

        status = pod.get("desiredStatus", "?")
        if status in ("EXITED", "TERMINATED", "FAILED"):
            raise RuntimeError(f"Pod in terminal state: {status}")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"SSH never responded after runtime appeared (waited {ssh_timeout}s)")


def install_deps(host, port):
    log.info("Installing Python dependencies on pod...")
    cmd = (
        "pip install -q "
        "transformers==4.48.3 "
        "peft==0.14.0 "
        "bitsandbytes==0.45.3 "
        "trl==0.14.0 "
        "accelerate==1.3.0 "
        "datasets==3.3.2 "
        "sentencepiece "
        "protobuf "
        "&& echo DEPS_OK"
    )
    rc, out, err = ssh(host, port, cmd, timeout=600)
    if "DEPS_OK" not in out:
        log.error(f"Dep install failed:\nSTDOUT: {out[-800:]}\nSTDERR: {err[-400:]}")
        return False
    log.info("Dependencies installed OK")
    return True


def start_training_bg(host, port):
    log.info("Starting Qwen 2.5 7B-Instruct QLoRA training in background...")
    cmd = (
        "cd /workspace && "
        "nohup python3 train_gpu.py "
        "--data /workspace/training_data_v4.jsonl "
        "--output /workspace/otto-qlora-qwen7b "
        "> /workspace/training_gpu.log 2>&1 & "
        "echo $! > /workspace/train.pid && "
        "echo LAUNCHED:$!"
    )
    rc, out, err = ssh(host, port, cmd, timeout=60)
    if "LAUNCHED:" not in out:
        log.error(f"Launch failed rc={rc}: {out} {err}")
        return None
    pid = out.strip().split("LAUNCHED:")[-1].strip()
    log.info(f"Training started, PID={pid}")
    return pid


def check_training(host, port, wait_secs=120):
    log.info(f"Waiting {wait_secs}s for training to initialize...")
    time.sleep(wait_secs)

    # Check process
    rc, out, _ = ssh(host, port,
        "PID=$(cat /workspace/train.pid 2>/dev/null); "
        "if [ -n \"$PID\" ] && kill -0 $PID 2>/dev/null; then echo RUNNING; else echo DEAD; fi",
        timeout=30)
    is_running = "RUNNING" in out

    # Get log
    rc2, log_out, _ = ssh(host, port, "tail -30 /workspace/training_gpu.log 2>/dev/null", timeout=30)

    # Count step lines
    rc3, step_cnt, _ = ssh(host, port,
        "grep -c 'step\\|Step\\|loss\\|Loss\\|epoch\\|Epoch' /workspace/training_gpu.log 2>/dev/null || echo 0",
        timeout=30)

    log.info(f"Training process: {'RUNNING' if is_running else 'DEAD'}")
    log.info(f"Log lines with step/loss/epoch: {step_cnt.strip()}")
    log.info(f"Recent log:\n{log_out[-800:]}")

    if not is_running:
        rc4, full, _ = ssh(host, port, "cat /workspace/training_gpu.log 2>/dev/null || echo NOLOG", timeout=30)
        log.error(f"Process died. Full log:\n{full[-3000:]}")

    return is_running, log_out


def main():
    log.info("=" * 65)
    log.info("Otto — Qwen 2.5 7B QLoRA RunPod Launcher v4")
    log.info(f"Time: {datetime.utcnow().isoformat()}Z")
    log.info("=" * 65)

    api_key = load_api_key()
    public_key = SSH_PUB_KEY.read_text().strip()
    train_script = OWN_MODEL / "train_gpu.py"
    train_data   = OWN_MODEL / "training_data_v4.jsonl"

    for f in [train_script, train_data, SSH_KEY]:
        if not Path(f).exists():
            log.error(f"Required file missing: {f}")
            sys.exit(1)

    log.info(f"Training data: {train_data.stat().st_size/1024:.0f} KB ({train_data.name})")

    # GPU preference order — cheapest community spot first, then escalate
    # Prices (spot/od): RTX 4090=$0.20/$0.34, RTX A5000=$0.11/$0.16, RTX 3090=$0.11/$0.22
    gpu_order = [
        "NVIDIA GeForce RTX 4090",   # 24GB, $0.20/hr spot — best value
        "NVIDIA RTX A5000",          # 24GB, $0.11/hr spot — cheapest
        "NVIDIA GeForce RTX 3090",   # 24GB, $0.11/hr spot — cheapest alt
        "NVIDIA GeForce RTX 3090 Ti",# 24GB, $0.14/hr spot
        "NVIDIA L40S",               # 48GB, $0.40/hr spot — more VRAM
        "NVIDIA A100 80GB PCIe",     # 80GB, $0.60/hr spot — last resort
    ]

    pod = None
    gpu_used = None
    pod_id = None

    for gpu in gpu_order:
        log.info(f"Trying GPU: {gpu}")
        try:
            pod = create_pod(api_key, gpu, public_key)
            if pod and pod.get("id"):
                pod_id = pod["id"]
                gpu_used = gpu
                log.info(f"Pod created: {pod_id} ({gpu_used})")
                log.info(f"Monitor: https://www.runpod.io/console/pods/{pod_id}")

                # Wait for pod — with 10-min provisioning timeout
                try:
                    pod = wait_for_pod(api_key, pod_id,
                                       provisioning_timeout=MAX_PROVISIONING_WAIT,
                                       ssh_timeout=MAX_SSH_WAIT)
                    break  # Success — pod is ready
                except TimeoutError as te:
                    log.warning(f"Provisioning timeout for {gpu}: {te}")
                    log.info("Terminating stuck pod and trying next GPU...")
                    try:
                        terminate_pod(api_key, pod_id)
                    except Exception as ex:
                        log.warning(f"Terminate failed: {ex}")
                    pod = None
                    pod_id = None
                    gpu_used = None
                    continue
                except RuntimeError as re:
                    log.warning(f"Pod failed for {gpu}: {re}")
                    try:
                        terminate_pod(api_key, pod_id)
                    except Exception:
                        pass
                    pod = None
                    pod_id = None
                    gpu_used = None
                    continue
        except RuntimeError as e:
            log.warning(f"  Pod creation failed for {gpu}: {e}")

    if not pod or not pod_id:
        log.error("All GPUs exhausted — no pod provisioned successfully.")
        sys.exit(1)

    ip, port = get_ssh_info(pod)
    log.info(f"SSH ready: root@{ip} -p {port}")

    # Small delay for SSH to fully stabilize
    time.sleep(10)

    # Upload files
    log.info("Uploading train_gpu.py...")
    if not scp(ip, port, str(train_script), f"{WORKSPACE}/train_gpu.py"):
        log.error("Upload failed. Terminating.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)

    # Also upload prefix tuning script (ReasonCACHE alternative)
    prefix_script = OWN_MODEL / "train_prefix.py"
    if prefix_script.exists():
        log.info("Uploading train_prefix.py (ReasonCACHE prefix tuning)...")
        scp(ip, port, str(prefix_script), f"{WORKSPACE}/train_prefix.py")

    log.info(f"Uploading {train_data.name} ({train_data.stat().st_size/1024/1024:.1f} MB)...")
    if not scp(ip, port, str(train_data), f"{WORKSPACE}/training_data_v4.jsonl"):
        log.error("Upload failed. Terminating.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)

    # Install deps
    if not install_deps(ip, port):
        log.error("Deps failed. Terminating.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)

    # Start training in background
    pid = start_training_bg(ip, port)
    if not pid:
        log.error("Training launch failed. Terminating.")
        terminate_pod(api_key, pod_id)
        sys.exit(1)

    # Verify training is running (wait 2 min for init)
    is_running, recent_log = check_training(ip, port, wait_secs=120)

    # Save pod info regardless
    info = {
        "pod_id": pod_id,
        "gpu": gpu_used,
        "ssh_host": ip,
        "ssh_port": port,
        "training_pid": pid,
        "launched_at": datetime.utcnow().isoformat() + "Z",
        "training_running": is_running,
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "lora_rank": 16,
        "lora_alpha": 32,
        "epochs": 3,
        "lr": "1e-4",
        "batch": 1,
        "grad_accum": 4,
        "quantization": "NF4 4-bit",
        "training_data": "training_data_v4.jsonl",
        "num_examples": 3664,
        "output_dir": "/workspace/otto-qlora-qwen7b",
        "log_file": "/workspace/training_gpu.log",
        "monitor_url": f"https://www.runpod.io/console/pods/{pod_id}",
        "ssh_cmd": f"ssh -i ~/.ssh/runpod_id_rsa -p {port} root@{ip}",
        "tail_cmd": f"ssh -i ~/.ssh/runpod_id_rsa -p {port} root@{ip} 'tail -f /workspace/training_gpu.log'",
        "download_cmd": f"scp -i ~/.ssh/runpod_id_rsa -r -P {port} root@{ip}:/workspace/otto-qlora-qwen7b {OWN_MODEL}/models/",
        "terminate_note": "Training continues on RunPod. Do NOT terminate until training completes.",
        "recent_log_tail": recent_log[-500:] if recent_log else "",
    }

    info_path = OWN_MODEL / "runpod_pod_info.json"
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)
    log.info(f"Pod info saved: {info_path}")

    log.info("\n" + "=" * 65)
    if is_running:
        log.info("SUCCESS — Qwen 2.5 7B QLoRA TRAINING IS RUNNING on RunPod!")
    else:
        log.warning("POSSIBLE ISSUE — Training may not have started. Check logs via SSH.")
    log.info(f"Pod ID   : {pod_id}")
    log.info(f"GPU      : {gpu_used}")
    log.info(f"SSH      : ssh -i ~/.ssh/runpod_id_rsa -p {port} root@{ip}")
    log.info(f"Tail log : ssh -i ~/.ssh/runpod_id_rsa -p {port} root@{ip} 'tail -f /workspace/training_gpu.log'")
    log.info(f"Data     : training_data_v4.jsonl ({3664} examples)")
    log.info(f"Est time : ~2-3 hours for 3 epochs, 3664 examples")
    log.info("\nPod will NOT be terminated. Training continues.")
    log.info("=" * 65)

    return info


if __name__ == "__main__":
    main()
