# Security Audit: Gating System
**Date:** 2026-03-24
**Auditor:** Otto (security-audit task 236a3891)
**Scope:** `memory/routes/workflows.py`, `memory/gate_notifier.py`, `memory/migrations/074_workflow_gates.sql`

---

## Executive Summary

The gating system is well-structured and the core logic is sound. Three issues require immediate attention: a path traversal in the artifact resolver that can leak local files, a TOCTOU race in gate resolution that can cause double-advance, and no authentication on gate resolve endpoints. The remaining findings are medium/low severity and can be addressed before external exposure.

---

## Finding 1 — CRITICAL: Path Traversal in `_resolve_artifact`
**File:** `workflows.py:169-183`

```python
def _resolve_artifact(s: str, limit: int) -> str:
    m = re.search(r'\[ARTIFACT: ([^\]]+)\]', s)
    if m:
        artifact_path = m.group(1).strip()
        if os.path.exists(artifact_path):
            with open(artifact_path, "r") as f:
                return f.read(limit)
```

**Vulnerability:** This function is called on `step_outputs` values during `_interpolate` and `get_pending_gate`. If any step output (agent-supplied) contains `[ARTIFACT: /home/web3relic/memory/.env]`, the API will read that file and:
- Include its content in the `context_snapshot` of the gate (returned by `GET /instances/{id}/gate`)
- Transmit it in the `context_snapshot` field of webhook payloads

The uvicorn process runs as `web3relic` and can read `/home/web3relic/memory/.env` (DB creds, OpenAI key, CDP keys), `~/.ssh/`, and all project files.

**Trigger path:** A malicious or compromised agent task writes `[ARTIFACT: /home/web3relic/memory/.env]` to its step output → stored in `step_outputs` JSONB → `_interpolate` calls `_resolve_artifact` → file contents appear in webhook payload.

**Fix:** Whitelist artifact paths to `~/otto/logs/tasks/` only:
```python
ARTIFACT_BASE = "/home/web3relic/otto/logs/tasks/"
artifact_path = os.path.realpath(m.group(1).strip())
if not artifact_path.startswith(ARTIFACT_BASE):
    return s  # reject
```

---

## Finding 2 — HIGH: TOCTOU Race in `_resolve_gate` (Non-Atomic State Transition)
**File:** `workflows.py:1765-1781`

```python
gate = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
if gate["status"] != "pending":
    raise ValueError(f"Gate {gate_id} is already {gate['status']}")
# ... (multiple async steps) ...
await pool.execute("UPDATE workflow_gates SET status = $2 ... WHERE id = $1", gate_id, gate_status)
```

**Vulnerability:** The SELECT and UPDATE are separate queries with no transaction or row-level lock. Two concurrent calls to `_resolve_gate` (e.g., OMS double-click, DAO quorum auto-resolve racing against manual approve) can both read `status = 'pending'`, both pass the check, and both execute the UPDATE + `_advance_workflow`. This double-advances `current_step` and runs the next step twice.

**Fix:** Use `SELECT ... FOR UPDATE` to acquire a row lock:
```python
gate = await pool.fetchrow(
    "SELECT * FROM workflow_gates WHERE id = $1 FOR UPDATE", gate_id
)
```
This requires the call to be inside a transaction (`async with pool.transaction()`). Alternatively, use an atomic compare-and-swap UPDATE:
```python
updated = await pool.fetchrow("""
    UPDATE workflow_gates
    SET status = $2, resolved_by = $3, resolved_at = now(), resolution_reason = $4
    WHERE id = $1 AND status = 'pending'
    RETURNING *
""", gate_id, gate_status, resolved_by, reason)
if not updated:
    raise ValueError(f"Gate {gate_id} already resolved (concurrent update)")
```
The second approach is simpler and doesn't require transaction wrapping.

---

## Finding 3 — HIGH: No Authentication on Gate Resolve/Approve Endpoints
**File:** `workflows.py:810-818, 629-695`

```python
@router.post("/gates/{gate_id}/resolve")
async def resolve_gate(gate_id: UUID, req: GateResolveRequest):
    """Admin resolve a gate (approve/reject/skip)."""
    # No auth check — any caller can approve/reject
```

**Current exposure:** The API is bound to `127.0.0.1:8100` (confirmed). Any process on the VM can approve/reject/skip any gate. If the OMS, WhatsApp interface, or any other service running on otto-machine is compromised, an attacker gains full workflow control.

**Finding 3a — resolved_by is caller-controlled.** The `GateResolveRequest.resolved_by` field defaults to `"mev"` but can be set to any value by the caller. Audit trail integrity is compromised — an internal service can impersonate Mev in gate records.

**Fix:** Add a simple shared-secret check consistent with existing patterns:
```python
from fastapi import Header
async def resolve_gate(gate_id: UUID, req: GateResolveRequest, x_api_key: str = Header(None)):
    if x_api_key != settings.internal_api_key:
        raise HTTPException(403, "Forbidden")
```
Alternatively, enforce that `resolved_by` is set from the auth context, not the request body.

---

## Finding 4 — MEDIUM: Unconstrained Vote Weight Allows DAO Manipulation
**File:** `workflows.py:55-60`, `gate_notifier/vote endpoint:836-843`

```python
class GateVoteRequest(BaseModel):
    voter_address: str   # free text, no validation
    vote: str
    weight: float = 1.0  # caller-controlled — no cap, no on-chain verification
    signature: Optional[str] = None  # stored but never verified
```

**Vulnerability:** Any caller who can reach the API can cast a vote with `weight: 999999.0` and instantly reach quorum. The `signature` field is stored but never cryptographically verified in Phase 1. This creates a false sense of security — votes appear signed but are never validated.

**Fix (Phase 1):** Cap `weight` at 1.0: `weight: float = Field(default=1.0, ge=0.0, le=1.0)`. Alternatively, ignore the caller-supplied `weight` entirely and set it to `1.0` server-side. Add a warning comment that signatures are not yet verified.

---

## Finding 5 — MEDIUM: Unlimited Escalation Loop
**File:** `workflows.py:1902-1922`

```python
if action == "escalate":
    await pool.execute("""
        UPDATE workflow_gates
        SET expires_at = now() + interval '1 hour', ...
        WHERE id = $1
    """, gate_id)
    # sends WhatsApp notification
```

**Vulnerability:** An unattended gate with `timeout_action = "escalate"` will re-escalate every hour indefinitely, flooding WhatsApp with notifications. The `metadata` records `escalated_at` but there is no `escalation_count` limit and no maximum total timeout.

**Fix:** Add an escalation count to metadata and cap at N escalations (e.g., 3), then fall back to `reject` or `fail_workflow`:
```python
meta = _jsonb(gate.get("metadata") or {})
count = int(meta.get("escalation_count", 0)) + 1
if count > 3:
    await _resolve_gate(pool, gate_id, "reject", "system:max-escalations", ...)
else:
    # extend + update escalation_count in metadata
```

---

## Finding 6 — LOW: Webhook Payload Includes Unfiltered context_snapshot
**File:** `gate_notifier.py:159`

```python
"context_snapshot": gate.get("context_snapshot") or {},
```

**Issue:** `context_snapshot` is passed verbatim to external webhook recipients. It may contain agent step output (AI-generated content, file paths, partial credentials if an agent accidentally logs them). Webhook recipients receive this data with no scrubbing.

**Fix:** Strip or redact large/sensitive fields before transmitting, or send only a summary. At minimum, document that webhook recipients may receive step output.

---

## Finding 7 — LOW: No Resume Token Mechanism (N/A — Design Gap)
**Audit item 1 asked about resume token generation.** There is no resume token in the current implementation. Gate resumption uses the raw gate UUID directly in the URL (`POST /gates/{gate_id}/resolve`). UUIDs are not guessable, but:
- They are logged in WhatsApp messages and webhook payloads
- Anyone with the UUID can resolve the gate (no additional proof required)

This is acceptable for the current internal-only deployment but should be noted for future external-facing use. A HMAC-signed token (`gate_id + expires_at + secret`) would provide forgery/replay protection.

---

## Finding 8 — LOW: `check-timeouts` Endpoint Unauthenticated
**File:** `workflows.py:745-750`

```python
@router.post("/gates/check-timeouts")
async def run_check_timeouts():
    """Trigger gate timeout processing. Called by reflection heartbeat every 30 min."""
```

Any caller can trigger bulk timeout processing at will. This is low risk since the timeout logic is deterministic, but an attacker could force early resolution of escalate-configured gates by rapid polling.

---

## Crash Safety Assessment

Gate creation is reasonably crash-safe: `_create_gate` inserts the gate row and updates `workflow_instances.pending_gate_id` in two separate statements (not a transaction). If the service crashes between these two statements, the gate row exists but `pending_gate_id` is NULL, causing `approve_step` to fall through to the legacy path. The gate orphan is not automatically recovered.

**Fix:** Wrap `_create_gate` in a transaction, or query by `instance_id` + `status = pending` (which `approve_step` already does for the pending gate lookup — this is the correct path and works correctly even if `pending_gate_id` is NULL).

---

## Summary Table

| # | Severity | Title | File:Line | Fix Complexity |
|---|----------|-------|-----------|----------------|
| 1 | CRITICAL | Path traversal in `_resolve_artifact` | workflows.py:169 | Small (path whitelist) |
| 2 | HIGH | TOCTOU race in `_resolve_gate` | workflows.py:1765 | Small (CAS UPDATE) |
| 3 | HIGH | No auth on resolve/approve endpoints | workflows.py:810,629 | Small (Header check) |
| 4 | MEDIUM | Unconstrained DAO vote weight | workflows.py:55 | Trivial (Field cap) |
| 5 | MEDIUM | Unlimited escalation loop | workflows.py:1902 | Small (counter cap) |
| 6 | LOW | Webhook sends unfiltered context_snapshot | gate_notifier.py:159 | Small |
| 7 | LOW | No resume token (plain UUID) | workflows.py:810 | Medium (HMAC token) |
| 8 | LOW | check-timeouts unauthenticated | workflows.py:745 | Trivial |

---

## Recommended Fix Priority

1. **Finding 1 (CRITICAL)** — Fix `_resolve_artifact` path whitelist before any external webhook exposure
2. **Finding 2 (HIGH)** — CAS UPDATE in `_resolve_gate` before production load
3. **Finding 3 (HIGH)** — Auth header on resolve endpoints before any external exposure
4. **Finding 4 (MEDIUM)** — Cap vote weight before DAO goes live
5. **Finding 5 (MEDIUM)** — Escalation cap before long-running workflows
6. Findings 6-8 can be deferred to a cleanup sprint
