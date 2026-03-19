---
name: secrets_vault_review
description: OMS API Key Manager & Secrets Vault code review (2026-03-19) — NEEDS_CHANGES. Two security issues around unauthenticated secret reads and dev-mode auth bypass.
type: project
---

OMS Secrets Vault review completed 2026-03-19. NEEDS_CHANGES.

**Why:** Auth on `/secrets/get/{key_name}` relies solely on service scoping — no bearer token required. Default `allowed_services: ["*"]` means any unauthenticated process can read all secrets from port 8100.

**How to apply:** In next implementation pass, require bearer token for the value-read endpoint (or at minimum block when no service header AND no bearer). Also guard against empty `web_auth_token` default allowing open write access.

Critical issues found:
1. `/secrets/get/{key_name}` is readable without auth for `["*"]`-scoped secrets (unauthenticated `service="unknown"` passes `["*"]` scope check)
2. `_check_auth()` silently passes when `web_auth_token=""` (default config) — all write endpoints open in dev/misconfigured deploy

Warnings found:
3. `set_secret` action detection checks audit_log for prior "created" entries — fragile in revoke→re-create cycles
4. Architecture specified PBKDF2HMAC key derivation; implementation uses raw `Fernet(key.encode())` — master key must be a valid Fernet key, not a human password

Patterns noted for future reviews:
- FastAPI internal APIs on :8100 consistently use bearer token auth — verify this on every new route file
- Default empty config values (`str = ""`) create implicit dev-mode bypasses; flag these on security-sensitive routes
