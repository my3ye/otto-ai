# Remote URL Audit — All Project Repos
**Date:** 2026-03-25
**Scope:** All git repos under ~/otto, ~/interfaces/web-next, /mnt/media/projects/

---

## Summary

| Account | Email | Repos Owned |
|---------|-------|------------|
| my3ye | my3ye.otto@gmail.com | otto-core, otto-ai |
| ottomev | abraottomev@gmail.com | koink-fun, my3ye-web, otto-ui, otto-web, panik-app-web, tusita, tusita-web, web-assist, web-next, x402t-demos |
| PipiAgent | web3otto@gmail.com | 505-systems-web, agency-agents, oneon-web, shakrah-web |

**Changes applied:** 7 repos fixed (1 remote URL corrected, 3 embedded credentials removed, 4 git user.email mismatches fixed, 1 oneon-web remote URL + git user both changed).

**All repos verified accessible** with correct account auth.

---

## Full Repo Audit

### 1. otto (~/)
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/my3ye/otto-core.git` |
| **New remote** | `https://github.com/my3ye/otto-core.git` *(no change)* |
| **git user.email** | my3ye.otto@gmail.com |
| **.repo-owner** | my3ye |
| **ls-remote (my3ye auth)** | ✅ OK |
| **Status** | CORRECT — no change needed |

---

### 2. 505-systems-web
| Field | Value |
|-------|-------|
| **Old remote** | `https://<TOKEN>@github.com/PipiAgent/505-systems-web.git` *(credentials embedded)* |
| **New remote** | `https://github.com/PipiAgent/505-systems-web.git` |
| **git user.email** | web3otto@gmail.com |
| **.repo-owner** | PipiAgent |
| **ls-remote (PipiAgent auth)** | ✅ OK |
| **Status** | FIXED — removed embedded credentials from URL |

---

### 3. agency-agents
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/PipiAgent/agency-agents.git` |
| **New remote** | `https://github.com/PipiAgent/agency-agents.git` *(no change)* |
| **git user.email** | web3otto@gmail.com |
| **.repo-owner** | PipiAgent |
| **ls-remote (PipiAgent auth)** | ✅ OK |
| **Status** | CORRECT — no change needed |

---

### 4. autoresearch
| Field | Value |
|-------|-------|
| **Remote** | `https://github.com/karpathy/autoresearch.git` |
| **git user.email** | my3ye.otto@gmail.com |
| **.repo-owner** | N/A (external 3rd-party fork) |
| **ls-remote** | N/A — external upstream, not a MY3YE project |
| **Status** | SKIP — external fork, no owner fix applicable |

---

### 5. koink-fun
| Field | Value |
|-------|-------|
| **Old remote** | `https://<TOKEN>@github.com/ottomev/koink-fun.git` *(credentials embedded)* |
| **New remote** | `https://github.com/ottomev/koink-fun.git` |
| **git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | FIXED — removed embedded credentials from URL |

---

### 6. my3ye-web
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/my3ye-web.git` |
| **New remote** | `https://github.com/ottomev/my3ye-web.git` *(no change)* |
| **git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | CORRECT — no change needed |

---

### 7. oneon-web ⭐ (key fix per task)
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/oneon-web.git` |
| **New remote** | `https://github.com/PipiAgent/oneon-web.git` |
| **Old git user.email** | abraottomev@gmail.com |
| **New git user.email** | web3otto@gmail.com |
| **.repo-owner** | PipiAgent |
| **ls-remote (PipiAgent auth)** | ✅ OK |
| **Status** | FIXED — remote URL changed ottomev → PipiAgent; git user updated |

---

### 8. otto-ai
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/my3ye/otto-ai` |
| **New remote** | `https://github.com/my3ye/otto-ai` *(no change)* |
| **git user.email** | my3ye.otto@gmail.com |
| **.repo-owner** | my3ye |
| **ls-remote (my3ye auth)** | ✅ OK |
| **Status** | CORRECT — no change needed |

---

### 9. otto-ui
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/otto-ui.git` |
| **New remote** | `https://github.com/ottomev/otto-ui.git` *(no change)* |
| **Old git user.email** | my3ye.otto@gmail.com *(mismatch — repo is ottomev)* |
| **New git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | FIXED — git user.email corrected (was my3ye, now ottomev) |

---

### 10. otto-web
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/otto-web.git` |
| **New remote** | `https://github.com/ottomev/otto-web.git` *(no change)* |
| **git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | CORRECT — no change needed |

---

### 11. panik-app-web
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/panik-app-web.git` |
| **New remote** | `https://github.com/ottomev/panik-app-web.git` *(no change)* |
| **git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | CORRECT — ottomev/panik-app-web is the active repo (last pushed 2026-03-18 vs PipiAgent copy 2026-02-27) |
| **Note** | PipiAgent also has panik-app-web (older fork/mirror) — this is the Vercel-connected version |

---

### 12. shakrah-web
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/PipiAgent/shakrah-web.git` |
| **New remote** | `https://github.com/PipiAgent/shakrah-web.git` *(no change)* |
| **Old git user.email** | my3ye.otto@gmail.com *(mismatch — repo is PipiAgent)* |
| **New git user.email** | web3otto@gmail.com |
| **.repo-owner** | PipiAgent |
| **ls-remote (PipiAgent auth)** | ✅ OK |
| **Status** | FIXED — git user.email corrected (was my3ye, now PipiAgent) |

---

### 13. tusita
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/tusita.git` |
| **New remote** | `https://github.com/ottomev/tusita.git` *(no change)* |
| **Old git user.email** | my3ye.otto@gmail.com *(mismatch — repo is ottomev)* |
| **New git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | FIXED — git user.email corrected (was my3ye, now ottomev) |

---

### 14. tusita-web
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/tusita-web.git` |
| **New remote** | `https://github.com/ottomev/tusita-web.git` *(no change)* |
| **Old git user.email** | my3ye.otto@gmail.com *(mismatch — repo is ottomev)* |
| **New git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | FIXED — git user.email corrected (was my3ye, now ottomev) |

---

### 15. web-assist
| Field | Value |
|-------|-------|
| **Old remote** | `https://<TOKEN>@github.com/ottomev/web-assist.git` *(credentials embedded)* |
| **New remote** | `https://github.com/ottomev/web-assist.git` |
| **git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | FIXED — removed embedded credentials from URL |

---

### 16. web-next (~/interfaces/web-next)
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/web-next.git` |
| **New remote** | `https://github.com/ottomev/web-next.git` *(no change)* |
| **git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | CORRECT — no change needed |

---

### 17. x402t-demos
| Field | Value |
|-------|-------|
| **Old remote** | `https://github.com/ottomev/x402t-demos.git` |
| **New remote** | `https://github.com/ottomev/x402t-demos.git` *(no change)* |
| **git user.email** | abraottomev@gmail.com |
| **.repo-owner** | ottomev |
| **ls-remote (ottomev auth)** | ✅ OK |
| **Status** | CORRECT — no change needed |

---

## Changes Made

| Repo | Change Type | Before | After |
|------|------------|--------|-------|
| `oneon-web` | Remote URL | `github.com/ottomev/oneon-web.git` | `github.com/PipiAgent/oneon-web.git` |
| `oneon-web` | git user.email | abraottomev@gmail.com | web3otto@gmail.com |
| `505-systems-web` | Remote URL | `<TOKEN>@github.com/PipiAgent/505-systems-web.git` | `github.com/PipiAgent/505-systems-web.git` |
| `koink-fun` | Remote URL | `<TOKEN>@github.com/ottomev/koink-fun.git` | `github.com/ottomev/koink-fun.git` |
| `web-assist` | Remote URL | `<TOKEN>@github.com/ottomev/web-assist.git` | `github.com/ottomev/web-assist.git` |
| `otto-ui` | git user.email | my3ye.otto@gmail.com | abraottomev@gmail.com |
| `tusita` | git user.email | my3ye.otto@gmail.com | abraottomev@gmail.com |
| `tusita-web` | git user.email | my3ye.otto@gmail.com | abraottomev@gmail.com |
| `shakrah-web` | git user.email | my3ye.otto@gmail.com | web3otto@gmail.com |

---

## Verification Summary

All 17 repos verified with `git ls-remote --heads origin` using the correct account auth:
- **my3ye auth**: otto (~), otto-ai — ✅ both OK
- **ottomev auth**: koink-fun, my3ye-web, otto-ui, otto-web, panik-app-web, tusita, tusita-web, web-assist, web-next, x402t-demos — ✅ all 10 OK
- **PipiAgent auth**: 505-systems-web, agency-agents, oneon-web, shakrah-web — ✅ all 4 OK
- **External (skip)**: autoresearch (karpathy upstream)

**Root cause of push failures:** Commits were being made with git user.email that didn't match the GitHub account owning the repo (e.g., my3ye.otto@gmail.com committing to ottomev-owned repos). Vercel deploy hooks check commit author — mismatched author triggers deployment failures.
