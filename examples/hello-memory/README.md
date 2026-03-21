# Hello Memory

The simplest Otto AI example. Store a few memories, search them by meaning.

## Run

```bash
# From the otto-ai root directory:
docker compose up -d

cd examples/hello-memory
pip install requests
python agent.py
```

## What it demonstrates

- `POST /semantic/remember` — store a memory with embedding
- `POST /semantic/search` — retrieve by semantic similarity (not keyword)

## Why this matters

Keyword search finds documents containing the word. Semantic search finds documents with the *meaning*.

Query: `"what blockchain is the user working with?"`
Finds: `"The user is building a DeFi protocol on Base"` — even though the query doesn't contain "Base", "DeFi", or "protocol".

This is how agents build real understanding over time.
