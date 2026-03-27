---
name: A2A Protocol Architecture
description: Agent-to-agent messaging protocol — PostgreSQL mailbox with HTTP polling, channel-scoped via plan_id/workflow_instance_id. 4 endpoints, migration 077, ~$5 total.
type: project
---

A2A Protocol designed (2026-03-28). Lightweight agent-to-agent messaging for Otto.

**Why:** Agents in plan DAGs and workflows can't communicate mid-execution. Only sequential output piping exists. A2A adds a side-channel for questions, artifacts, and coordination signals.

**How to apply:** When designing multi-agent features, A2A channels are available for any plan or workflow. Channel ID = plan_id or workflow_instance_id (implicit, no setup needed). Message types: message, request, response, artifact, signal.

Key decisions:
- PostgreSQL polling over pub-sub (no new infra, agents are bash/curl processes)
- Channel-scoped messages, not global broadcast
- Separate from IVT (peer-level, not kernel-level)
- No formal handshake (channel existence = open)
- 7-day TTL + maintenance cleanup

Integration: task_runner.sh injects A2A block into prompts, tasks.py posts completion signals, plan/workflow IDs serve as implicit channels.

Migration 077: a2a_messages table. 4 endpoints: /a2a/send, /a2a/poll, /a2a/channel/{id}, /a2a/peers.

Phase 1 (~$3): table + routes. Phase 2 (~$2): task_runner + completion hooks.

Full spec at ~/otto/docs/arch-a2a-protocol.md.
