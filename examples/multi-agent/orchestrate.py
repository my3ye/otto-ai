"""
Multi-Agent Coordination — Otto AI Example

Two agents coordinate through shared memory:
  - Agent A (Researcher): analyzes a topic, stores findings as memories
  - Agent B (Synthesizer): searches those memories, produces a summary

This demonstrates how agents can work together without direct communication —
through the shared memory layer.

Usage:
    pip install requests
    python orchestrate.py

Prerequisites:
    - Otto AI stack running: docker compose up -d
    - OpenAI API key set in .env (for embeddings)
"""

import requests
import json
import time
from datetime import datetime, timezone

API_URL = "http://localhost:8100"


# ── Shared utilities ──────────────────────────────────────────────────────────

def start_session(agent_id: str) -> str:
    resp = requests.post(f"{API_URL}/sessions/start", json={"agent_id": agent_id})
    resp.raise_for_status()
    return resp.json()["id"]


def end_session(session_id: str, summary: str):
    requests.post(f"{API_URL}/sessions/{session_id}/end", json={"summary": summary})


def log_event(session_id: str, content: str, event_type: str = "action", importance: float = 0.7):
    requests.post(f"{API_URL}/episodic/events", json={
        "session_id": session_id,
        "content": content,
        "event_type": event_type,
        "importance": importance,
    })


def remember(content: str, category: str, confidence: float = 0.85, source: str = "agent") -> str:
    resp = requests.post(f"{API_URL}/semantic/remember", json={
        "content": content,
        "category": category,
        "confidence": confidence,
        "source": source,
        "metadata": {"stored_at": datetime.now(timezone.utc).isoformat()},
    })
    resp.raise_for_status()
    return resp.json()["id"]


def search(query: str, limit: int = 5) -> list[dict]:
    resp = requests.post(f"{API_URL}/semantic/search", json={
        "query": query,
        "limit": limit,
    })
    resp.raise_for_status()
    return resp.json()


# ── Agent A: Researcher ───────────────────────────────────────────────────────

def agent_researcher(topic: str):
    """Researcher agent: generates findings about a topic, stores them in memory."""
    print(f"\n[Agent A: Researcher] Analyzing topic: '{topic}'")
    session_id = start_session("researcher")

    # Simulate research findings (in production, this would call an LLM)
    findings = [
        {
            "content": f"Otto AI uses vector embeddings (OpenAI text-embedding-3-small) for semantic search, enabling agents to find relevant memories by meaning, not keyword.",
            "category": "technical",
            "confidence": 0.95,
        },
        {
            "content": f"The task queue enables detached execution — agents create work items that run asynchronously, allowing parallel coordination without blocking.",
            "category": "architecture",
            "confidence": 0.90,
        },
        {
            "content": f"Episodic memory provides a timestamped event log — agents can reconstruct their history and understand what happened in a previous session.",
            "category": "architecture",
            "confidence": 0.88,
        },
        {
            "content": f"Procedural memory stores named sequences of steps with trust scores. High-trust procedures are surfaced first when planning similar work.",
            "category": "capability",
            "confidence": 0.85,
        },
        {
            "content": f"All memory is persistent by default — nothing expires. Agents accumulate knowledge across runs, sessions, and time.",
            "category": "design",
            "confidence": 0.95,
        },
    ]

    log_event(session_id, f"Starting research on: {topic}", "action", 0.8)

    stored_ids = []
    for finding in findings:
        mem_id = remember(
            finding["content"],
            finding["category"],
            finding["confidence"],
            source="researcher",
        )
        stored_ids.append(mem_id)
        print(f"  ✓ Stored [{finding['category']}]: {finding['content'][:70]}...")

    log_event(session_id, f"Stored {len(stored_ids)} findings about {topic}", "observation", 0.9)
    end_session(session_id, f"Researched '{topic}', stored {len(stored_ids)} findings")

    print(f"[Agent A] Done. Stored {len(stored_ids)} memories.\n")
    return stored_ids


# ── Agent B: Synthesizer ──────────────────────────────────────────────────────

def agent_synthesizer(question: str):
    """Synthesizer agent: searches existing memories to answer a question."""
    print(f"[Agent B: Synthesizer] Answering: '{question}'")
    session_id = start_session("synthesizer")

    log_event(session_id, f"Searching memory for: {question}", "action", 0.8)

    results = search(question, limit=4)

    print(f"\n  Found {len(results)} relevant memories:\n")
    synthesis_parts = []
    for r in results:
        score = r.get("relevance", 0)
        print(f"  [{score:.2f}] {r['content'][:90]}...")
        synthesis_parts.append(r["content"])

    # Compose a synthesis
    synthesis = f"Based on {len(results)} relevant memories:\n\n"
    for i, part in enumerate(synthesis_parts[:3], 1):
        synthesis += f"{i}. {part[:120]}\n\n"

    log_event(session_id, f"Synthesized answer from {len(results)} memories", "observation", 0.85)
    end_session(session_id, f"Answered '{question}' using {len(results)} memories")

    print(f"\n[Agent B] Synthesis:\n{synthesis}")
    return synthesis


# ── Orchestrator ──────────────────────────────────────────────────────────────

def main():
    print("=== Otto AI — Multi-Agent Coordination ===")
    print("Two agents communicate through shared memory.\n")

    topic = "Otto AI memory architecture"

    # Agent A researches and stores findings
    agent_researcher(topic)

    # Brief pause to ensure writes are committed
    time.sleep(1)

    # Agent B searches and synthesizes (no direct communication with Agent A)
    questions = [
        "How does Otto AI handle long-term memory persistence?",
        "What makes the task queue useful for agent coordination?",
    ]

    for question in questions:
        agent_synthesizer(question)
        print("-" * 60)

    print("\nDone. The memories Agent A stored are now available to any agent.")
    print(f"Try searching them: curl -X POST {API_URL}/semantic/search -H 'Content-Type: application/json' -d '{{\"query\": \"agent memory\"}}'")


if __name__ == "__main__":
    main()
