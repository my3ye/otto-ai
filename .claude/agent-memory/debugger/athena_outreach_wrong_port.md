---
name: athena_outreach_wrong_port
description: Athena outreach messages marked sent in OMS but not delivered — wrong WhatsApp port in send scripts
type: project
---

Root cause: `send_approved_outreach.py` and `outreach_sender.sh` both hardcoded `WHATSAPP_URL=localhost:3001` (Otto's Ottolabs line) instead of `localhost:3002` (Athena's WebAssist line). Messages were delivered from the wrong WhatsApp account. OMS showed "sent" because curl to 3001 returned HTTP 200 (Baileys accepted the message), so `mark_sent()` was called — even though the message went from the wrong number.

**Why:** When Athena was added (2026-03-21), the send scripts were not updated to point to the new port.

**How to apply:** Any outreach or message send tool that serves WebAssist/Athena leads must use port 3002, not 3001. Port 3001 = Otto (Ottolabs/admin comms), port 3002 = Athena (WebAssist customer line). The `whatsapp_send.sh` tool always uses 3001 — never use it for prospect outreach.

Fixed in commit 1d37b1d (2026-03-26). New API endpoints: `POST /outreach/queue/{id}/send` and `POST /outreach/queue/send-approved` both explicitly route through Athena (3002).
