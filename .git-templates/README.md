# Otto Git Templates

This directory contains shared git hook templates that are auto-applied to new repos.

## Configuration

Global git config: `init.templateDir = /home/web3relic/otto/.git-templates`

New repos created with `git init` automatically get these hooks.

---

## Hooks

### `pre-push` — Owner-Aware gh Auth Switcher

**Purpose:** Ensures every `git push` uses the correct GitHub account by reading `.repo-owner` and switching `gh auth` before the push proceeds.

**Why this exists:** The MY3YE ecosystem uses 3 GitHub accounts (`ottomev`, `PipiAgent`, `my3ye`). If the wrong account is active during a push, GitHub rejects it ("Repository not found"). Vercel also rejects deploys if the committer doesn't match the repo owner. This hook makes wrong-account pushes impossible.

**How it works:**
1. Reads `.repo-owner` from the repo root (e.g. `ottomev`)
2. Checks current active `gh` account via `gh auth status`
3. If account doesn't match, calls `gh auth switch --user <owner>`
4. Exits 0 — git proceeds with the push using the correct credentials

**Error behavior:**
- `.repo-owner` missing → exit 1, clear error with fix instructions
- `.repo-owner` empty → exit 1
- `gh auth switch` fails → exit 1 (account not logged in)
- All good → exit 0 (push proceeds)

---

## The `.repo-owner` Convention

Every repo must have a `.repo-owner` file in its root containing the GitHub username of the account that owns the repo:

```
ottomev
```

**Account mapping:**
| Account | Email | Repos |
|---------|-------|-------|
| `ottomev` | abraottomev@gmail.com | koink-fun, my3ye-web, otto-ui, otto-web, panik-app-web, tusita, tusita-web, web-assist, web-next, x402t-demos |
| `PipiAgent` | web3otto@gmail.com | 505-systems-web, agency-agents, oneon-web, shakrah-web |
| `my3ye` | my3ye.otto@gmail.com | otto-ai, otto (otto-core) |

**Adding `.repo-owner` to a new repo:**
```bash
echo 'ottomev' > .repo-owner
git add .repo-owner
git commit -m "chore: add .repo-owner for pre-push auth enforcement"
```

---

## Retrofitting Existing Repos

To install the hook on all known repos:
```bash
/home/web3relic/otto/tools/install-hooks.sh
```

To install on a single repo:
```bash
/home/web3relic/otto/tools/install-hooks.sh /path/to/repo
```

The script is idempotent — safe to re-run. It always installs the latest version of the hook.

---

## Adding a New Repo

1. Create `.repo-owner` with the GitHub username
2. Run `install-hooks.sh /path/to/new-repo` (or the hook is auto-applied via templateDir on `git init`)
3. Commit `.repo-owner`

That's it. The enforcement is automatic from the first push.
