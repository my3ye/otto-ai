#!/usr/bin/env bash
# install-commit-enforcer.sh — install the pre-commit identity enforcer hook
#
# Copies the canonical pre-commit hook from the git-templates directory into
# every known git repository. Run this after modifying the hook or adding
# new repos.
#
# Usage:
#   ~/otto/tools/install-commit-enforcer.sh           # install to all repos
#   ~/otto/tools/install-commit-enforcer.sh --dry-run # preview only

set -euo pipefail

HOOK_SOURCE="/home/web3relic/otto/.git-templates/hooks/pre-commit"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  echo "🔍 Dry run — no changes will be made"
fi

if [[ ! -f "$HOOK_SOURCE" ]]; then
  echo "❌ Hook source not found: $HOOK_SOURCE" >&2
  exit 1
fi

# Known repositories (otto + all project repos)
REPOS=(
  "/home/web3relic/otto"
  "/mnt/media/projects/505-systems-web"
  "/mnt/media/projects/agency-agents"
  "/mnt/media/projects/autoresearch"
  "/mnt/media/projects/koink-fun"
  "/mnt/media/projects/my3ye-web"
  "/mnt/media/projects/oneon-web"
  "/mnt/media/projects/otto-ai"
  "/mnt/media/projects/otto-ui"
  "/mnt/media/projects/otto-web"
  "/mnt/media/projects/panik-app-web"
  "/mnt/media/projects/shakrah-web"
  "/mnt/media/projects/tusita"
  "/mnt/media/projects/tusita-web"
  "/mnt/media/projects/web-assist"
  "/mnt/media/projects/x402t-demos"
  "/home/web3relic/interfaces/web-next"
)

INSTALLED=0
SKIPPED=0
FAILED=0

echo ""
echo "📦 Installing pre-commit identity enforcer hook..."
echo "   Source: $HOOK_SOURCE"
echo ""

for REPO in "${REPOS[@]}"; do
  REPO_NAME="$(basename "$REPO")"
  HOOKS_DIR="$REPO/.git/hooks"
  HOOK_DEST="$HOOKS_DIR/pre-commit"

  if [[ ! -d "$REPO/.git" ]]; then
    echo "  ⏭️  $REPO_NAME — not a git repo, skipping"
    ((SKIPPED++)) || true
    continue
  fi

  if [[ ! -d "$HOOKS_DIR" ]]; then
    if [[ $DRY_RUN -eq 0 ]]; then
      mkdir -p "$HOOKS_DIR"
    fi
  fi

  # Check if hook already exists and is identical
  if [[ -f "$HOOK_DEST" ]] && diff -q "$HOOK_SOURCE" "$HOOK_DEST" > /dev/null 2>&1; then
    echo "  ✅ $REPO_NAME — already up to date"
    ((SKIPPED++)) || true
    continue
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    if [[ -f "$HOOK_DEST" ]]; then
      echo "  🔄 $REPO_NAME — would update pre-commit hook"
    else
      echo "  ➕ $REPO_NAME — would install pre-commit hook"
    fi
    ((INSTALLED++)) || true
  else
    if cp "$HOOK_SOURCE" "$HOOK_DEST" && chmod +x "$HOOK_DEST"; then
      if [[ -f "$HOOK_DEST.old" ]]; then
        echo "  🔄 $REPO_NAME — updated pre-commit hook"
      else
        echo "  ➕ $REPO_NAME — installed pre-commit hook"
      fi
      ((INSTALLED++)) || true
    else
      echo "  ❌ $REPO_NAME — FAILED to install hook" >&2
      ((FAILED++)) || true
    fi
  fi
done

echo ""
echo "═══════════════════════════════════════════════"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  Dry run results: $INSTALLED would change, $SKIPPED unchanged"
else
  echo "  Results: $INSTALLED installed/updated, $SKIPPED unchanged, $FAILED failed"
fi
echo "═══════════════════════════════════════════════"
echo ""

[[ $FAILED -eq 0 ]]
