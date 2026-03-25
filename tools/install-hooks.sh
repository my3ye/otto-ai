#!/usr/bin/env bash
# install-hooks.sh — retrofit pre-push hook to all existing repos
#
# Usage:
#   ./install-hooks.sh                 # Install hooks in all known repos
#   ./install-hooks.sh /path/to/repo   # Install hook in a specific repo
#
# What it does:
#   1. Copies .git-templates/hooks/pre-push to .git/hooks/pre-push in each repo
#   2. Makes it executable
#   3. Reports status per repo
#
# Safe to re-run — overwrites existing hook with latest version.

set -euo pipefail

TEMPLATE_HOOK="/home/web3relic/otto/.git-templates/hooks/pre-push"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$TEMPLATE_HOOK" ]]; then
  echo "❌ Template hook not found at: $TEMPLATE_HOOK" >&2
  exit 1
fi

# All known repos
ALL_REPOS=(
  "/mnt/media/projects/505-systems-web"
  "/mnt/media/projects/agency-agents"
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
  "/home/web3relic/otto"
)

# If a specific repo is given, only install there
if [[ $# -gt 0 ]]; then
  ALL_REPOS=("$@")
fi

INSTALLED=0
SKIPPED=0
FAILED=0

echo "🔧 Installing pre-push hooks..."
echo ""

for repo in "${ALL_REPOS[@]}"; do
  if [[ ! -d "$repo/.git" ]]; then
    echo "  ⚠️  SKIP  $repo  (not a git repo)"
    ((SKIPPED++)) || true
    continue
  fi

  hooks_dir="$repo/.git/hooks"
  dest="$hooks_dir/pre-push"

  # Ensure hooks dir exists
  mkdir -p "$hooks_dir"

  # Copy hook
  if cp "$TEMPLATE_HOOK" "$dest" && chmod +x "$dest"; then
    echo "  ✅  OK    $repo"
    ((INSTALLED++)) || true
  else
    echo "  ❌  FAIL  $repo"
    ((FAILED++)) || true
  fi
done

echo ""
echo "─────────────────────────────────────"
echo "  Installed: $INSTALLED  |  Skipped: $SKIPPED  |  Failed: $FAILED"
echo "─────────────────────────────────────"

if [[ $FAILED -gt 0 ]]; then
  exit 1
fi
exit 0
