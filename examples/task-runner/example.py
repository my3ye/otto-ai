"""
Task Runner — Otto AI Example

Demonstrates the Task Queue: create a task, launch it, poll for completion.

Tasks run as detached subprocesses — your agent doesn't block while waiting.
This is how Otto coordinates long-running work across multiple agents.

Usage:
    pip install requests
    python example.py

Prerequisites:
    - Otto AI stack running: docker compose up -d
    - claude CLI installed (optional — task will show "not found" without it)
"""

import requests
import time
import json

API_URL = "http://localhost:8100"


def create_task(title: str, prompt: str, priority: int = 5, budget: float = 0.5) -> dict:
    resp = requests.post(f"{API_URL}/tasks", json={
        "title": title,
        "prompt": prompt,
        "priority": priority,
        "budget_usd": budget,
        "timeout_seconds": 60,
        "agent_type": "general-purpose",
        "model": "sonnet",
        "created_by": "example-script",
    })
    resp.raise_for_status()
    return resp.json()


def launch_task(task_id: str) -> dict:
    resp = requests.post(f"{API_URL}/tasks/{task_id}/run")
    resp.raise_for_status()
    return resp.json()


def poll_task(task_id: str, timeout: int = 30) -> dict:
    """Poll until task completes or timeout (seconds)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API_URL}/tasks/{task_id}")
        resp.raise_for_status()
        task = resp.json()
        status = task["status"]

        if status in ("completed", "failed"):
            return task

        print(f"  Status: {status}... waiting")
        time.sleep(3)

    return {"status": "timeout", "id": task_id}


def queue_status() -> dict:
    resp = requests.get(f"{API_URL}/tasks/queue/status")
    resp.raise_for_status()
    return resp.json()


def main():
    print("=== Otto AI — Task Runner Example ===\n")

    # Queue status before
    status = queue_status()
    print(f"Queue: {status['pending']} pending, {status['running']} running, "
          f"{status['completed_24h']} completed today\n")

    # Create a task
    print("Creating task...")
    task = create_task(
        title="Summarize Otto AI architecture",
        prompt=(
            "In 2-3 sentences, explain what Otto AI is and what problem it solves. "
            "Be concise and developer-facing."
        ),
        priority=5,
        budget=0.25,
    )
    task_id = task["id"]
    print(f"  Created: {task_id}")
    print(f"  Title: {task['title']}")
    print(f"  Status: {task['status']}\n")

    # Launch it
    print("Launching task...")
    result = launch_task(task_id)
    print(f"  {result['status']}: {result.get('title', '')}\n")

    # Poll for completion
    print("Polling for completion (30s timeout)...")
    final = poll_task(task_id, timeout=30)

    print(f"\nFinal status: {final['status']}")
    if final.get("output"):
        print(f"Output:\n{final['output'][:500]}")
    elif final["status"] == "timeout":
        print("Task is still running. Check it later:")
        print(f"  curl {API_URL}/tasks/{task_id}")

    # Queue status after
    status = queue_status()
    print(f"\nQueue now: {status['pending']} pending, {status['running']} running")


if __name__ == "__main__":
    main()
