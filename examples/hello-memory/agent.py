"""
Hello Memory — Otto AI Example

An agent that stores and retrieves semantic memories.
Demonstrates the most fundamental capability: persistent memory across runs.

Usage:
    pip install requests
    python agent.py

Prerequisites:
    - Otto AI stack running: docker compose up -d
    - OpenAI API key set in .env
"""

import requests
import json

API_URL = "http://localhost:8100"


def remember(content: str, category: str = "general", confidence: float = 0.8) -> dict:
    """Store a memory."""
    resp = requests.post(f"{API_URL}/semantic/remember", json={
        "content": content,
        "category": category,
        "confidence": confidence,
    })
    resp.raise_for_status()
    return resp.json()


def search(query: str, limit: int = 3) -> list[dict]:
    """Search memories by meaning."""
    resp = requests.post(f"{API_URL}/semantic/search", json={
        "query": query,
        "limit": limit,
    })
    resp.raise_for_status()
    return resp.json()


def main():
    print("=== Otto AI — Hello Memory ===\n")

    # Store some memories
    print("Storing memories...")
    memories = [
        ("The user is building a DeFi protocol on Base", "context", 0.9),
        ("The user prefers TypeScript over JavaScript", "preference", 0.85),
        ("The project uses Hardhat for contract development", "technical", 0.9),
        ("The user's team has 3 engineers and ships weekly", "context", 0.8),
        ("The user wants gas optimization before launch", "requirement", 0.95),
    ]

    for content, category, confidence in memories:
        mem = remember(content, category, confidence)
        print(f"  ✓ [{category}] {content[:60]}")

    print()

    # Search by meaning — not keyword
    queries = [
        "what blockchain is the user working with?",
        "what are the team's technical preferences?",
        "what needs to be done before launch?",
    ]

    for query in queries:
        print(f"Query: '{query}'")
        results = search(query, limit=2)
        for r in results:
            score = r.get("relevance", 0)
            print(f"  [{score:.2f}] {r['content'][:80]}")
        print()

    print("Memory persists. Run this again — the memories will still be there.")
    print("Check health: curl http://localhost:8100/health")


if __name__ == "__main__":
    main()
