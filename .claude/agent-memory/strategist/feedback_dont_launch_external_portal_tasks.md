---
name: Don't Launch External Portal Submission Tasks
description: Tasks requiring form submission on external websites (Gitcoin, ENS, Solana portals) cannot be run by agents — they need Mev credentials and browser access
type: feedback
---

Never launch tasks whose prompts require submitting forms on external portals (Gitcoin, ENS builder grants, Solana Foundation, any external site with auth). These tasks will fail or stall because:
1. Agents cannot log into Mev's accounts on external services
2. Form submission via web tools is unreliable and often blocked

**Why:** The 3 grant tasks (ENS/Solana/Gitcoin) have been sitting in the queue since 2026-03-27 because they require Mev to go to the portals and click submit. Launching them wastes budget and clutters the queue.

**How to apply:** When a pending task has a prompt that says "submit at [external URL]" or "register at [external service]", do NOT launch it. Instead, flag it to Mev in the WhatsApp brief with clear next action. For Otto's portion (prep application text, research requirements), create a SEPARATE preparation task if the materials don't exist yet.
