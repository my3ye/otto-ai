#!/usr/bin/env python3
"""
self_patch.py — Gödel Agent self-modification tool for Otto.

Safety-first: patches are NEVER auto-applied. All proposals are staged in
projects/self_patches/ for review by the next heartbeat cycle.

Usage:
    python3 tools/self_patch.py \
        --target .claude/agents/reflection.md \
        --old-string "old text to replace" \
        --new-string "new replacement text" \
        --reason "why this patch improves Otto"

    # Or pass diff via JSON file:
    python3 tools/self_patch.py --spec /path/to/patch_spec.json
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

OTTO_ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = OTTO_ROOT / "projects" / "self_patches"
MEMORY_API = "http://localhost:8100"

# Targets that may be patched (relative to OTTO_ROOT)
ALLOWED_TARGETS = {
    ".claude/agents/heartbeat.md",
    ".claude/agents/reflection.md",
    ".claude/agents/alpha_heartbeat.md",
    "tools/lead_scraper.py",
    "tools/stage_outreach_queue.py",
    "tools/outreach_sender.py",
    "tools/self_patch.py",
    "heartbeat.sh",
    "reflection.sh",
    "task_runner.sh",
}

# Strings that indicate destructive / dangerous operations
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"os\.remove",
    r"shutil\.rmtree",
    r"DROP\s+TABLE",
    r"DELETE\s+FROM",
    r"TRUNCATE",
    r"subprocess\.call",
    r"subprocess\.run",
    r"os\.system",
    r"eval\(",
    r"exec\(",
    r"__import__",
    r"importlib\.import",
    r"open\(.+,\s*['\"]w",   # file open for writing inside new_string
    r"sudo\s",
    r"chmod\s+[0-7]*7",      # world-writable
    r"curl.*\|\s*bash",
    r"wget.*\|\s*bash",
]

MAX_LINES_CHANGED = 50


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def validate_patch(target_rel: str, old_string: str, new_string: str) -> None:
    """Raise ValueError with a reason if the patch is unsafe or invalid."""

    # 1. Target must be in the allowed set
    if target_rel not in ALLOWED_TARGETS:
        raise ValueError(
            f"Target '{target_rel}' not in allowed patch targets. "
            f"Allowed: {sorted(ALLOWED_TARGETS)}"
        )

    # 2. Target file must actually exist
    target_path = OTTO_ROOT / target_rel
    if not target_path.exists():
        raise ValueError(f"Target file does not exist: {target_path}")

    # 3. old_string must appear exactly once in the file
    content = target_path.read_text(encoding="utf-8")
    occurrences = content.count(old_string)
    if occurrences == 0:
        raise ValueError("old_string not found in target file — patch would be a no-op")
    if occurrences > 1:
        raise ValueError(
            f"old_string appears {occurrences} times in target file — "
            "patch is ambiguous; provide more context to make it unique"
        )

    # 4. Patch must not be a no-op
    if old_string == new_string:
        raise ValueError("old_string and new_string are identical — no change")

    # 5. Line-change limit
    old_lines = old_string.count("\n") + 1
    new_lines = new_string.count("\n") + 1
    changed = max(old_lines, new_lines)
    if changed > MAX_LINES_CHANGED:
        raise ValueError(
            f"Patch spans {changed} lines (max {MAX_LINES_CHANGED}). "
            "Break into smaller patches."
        )

    # 6. Dangerous pattern scan on new_string
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, new_string, re.IGNORECASE):
            raise ValueError(
                f"new_string matches dangerous pattern '{pat}'. "
                "Patch rejected for safety."
            )


def stage_patch(
    target_rel: str,
    old_string: str,
    new_string: str,
    reason: str,
    proposed_by: str = "reflection",
) -> Path:
    """Write patch proposal to staging dir. Returns path of staged file."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Stable short ID based on content
    patch_id = hashlib.sha256(
        f"{target_rel}:{old_string}:{new_string}".encode()
    ).hexdigest()[:8]
    filename = f"{ts}_{patch_id}.json"
    patch_path = STAGING_DIR / filename

    patch = {
        "patch_id": patch_id,
        "proposed_at": datetime.now(timezone.utc).isoformat(),
        "proposed_by": proposed_by,
        "status": "pending",  # pending | approved | rejected | applied
        "target": target_rel,
        "old_string": old_string,
        "new_string": new_string,
        "reason": reason,
        "review_notes": None,
    }
    patch_path.write_text(json.dumps(patch, indent=2), encoding="utf-8")
    return patch_path


def log_to_memory(patch: dict, patch_path: Path) -> bool:
    """Store patch proposal in semantic memory. Returns True on success."""
    fact = (
        f"Self-patch proposal [{patch['patch_id']}] staged at {patch['proposed_at']}. "
        f"Target: {patch['target']}. "
        f"Reason: {patch['reason']}. "
        f"Status: pending review. File: {patch_path}"
    )
    try:
        r = requests.post(
            f"{MEMORY_API}/semantic/remember",
            json={
                "content": fact,
                "category": "self_modification",
                "importance": 7,
                "source": "self_patch",
            },
            timeout=10,
        )
        return r.ok
    except Exception as e:
        print(f"WARNING: Could not log to memory API: {e}", file=sys.stderr)
        return False


def apply_patch(patch_path: Path, eval_gate: bool = False) -> None:
    """
    Apply an approved patch from a staged JSON file. Used by heartbeat reviewer.

    If eval_gate=True: runs eval before and after the patch. Reverts the patch
    if aggregate_score drops (regression guard). Results stored in memory API.
    """
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    if patch["status"] != "approved":
        die(f"Patch {patch['patch_id']} is not approved (status={patch['status']})")

    target_path = OTTO_ROOT / patch["target"]
    content = target_path.read_text(encoding="utf-8")

    if content.count(patch["old_string"]) != 1:
        die(
            f"old_string no longer appears exactly once in {patch['target']} — "
            "file may have changed since proposal. Patch NOT applied."
        )

    # ── Eval gate: baseline before applying ────────────────────────────────
    baseline_score: float | None = None
    if eval_gate:
        try:
            from tools.eval_harness import run_eval
        except ImportError:
            sys.path.insert(0, str(OTTO_ROOT))
            from tools.eval_harness import run_eval

        print(f"[eval-gate] Running baseline eval before patch {patch['patch_id']}...")
        baseline = run_eval(
            context=f"BEFORE patch {patch['patch_id']} on {patch['target']}",
            store=True,
        )
        baseline_score = baseline["aggregate_score"]
        print(f"[eval-gate] Baseline score: {baseline_score:.4f}")

    # ── Apply patch ─────────────────────────────────────────────────────────
    new_content = content.replace(patch["old_string"], patch["new_string"], 1)
    target_path.write_text(new_content, encoding="utf-8")

    # ── Eval gate: post-patch check ─────────────────────────────────────────
    if eval_gate and baseline_score is not None:
        print(f"[eval-gate] Running post-patch eval...")
        post = run_eval(
            context=f"AFTER patch {patch['patch_id']} on {patch['target']}",
            store=True,
        )
        post_score = post["aggregate_score"]
        delta = round(post_score - baseline_score, 4)
        print(f"[eval-gate] Post-patch score: {post_score:.4f} (delta: {delta:+.4f})")

        if post_score < baseline_score:
            # Regression — revert the patch
            target_path.write_text(content, encoding="utf-8")
            patch["status"] = "reverted"
            patch["revert_reason"] = (
                f"Eval regression: {baseline_score:.4f} → {post_score:.4f} (delta {delta:+.4f})"
            )
            patch["reverted_at"] = datetime.now(timezone.utc).isoformat()
            patch_path.write_text(json.dumps(patch, indent=2), encoding="utf-8")
            print(
                f"[eval-gate] REVERTED patch {patch['patch_id']} — "
                f"performance regressed {delta:+.4f}. Original file restored."
            )
            return

        patch["eval_baseline"] = baseline_score
        patch["eval_post"] = post_score
        patch["eval_delta"] = delta

    # ── Finalize ────────────────────────────────────────────────────────────
    patch["status"] = "applied"
    patch["applied_at"] = datetime.now(timezone.utc).isoformat()
    patch_path.write_text(json.dumps(patch, indent=2), encoding="utf-8")

    print(f"Applied patch {patch['patch_id']} to {patch['target']}")
    if eval_gate and baseline_score is not None:
        print(f"  Eval gate passed: {baseline_score:.4f} → {patch.get('eval_post', '?'):.4f}")


def list_pending() -> None:
    """Print all pending patch proposals."""
    if not STAGING_DIR.exists():
        print("No staging directory — no patches yet.")
        return
    patches = sorted(STAGING_DIR.glob("*.json"))
    pending = []
    for p in patches:
        try:
            d = json.loads(p.read_text())
            if d.get("status") == "pending":
                pending.append((p, d))
        except Exception:
            pass
    if not pending:
        print("No pending patches.")
        return
    for path, d in pending:
        print(f"\n{'='*60}")
        print(f"Patch ID : {d['patch_id']}")
        print(f"File     : {path.name}")
        print(f"Proposed : {d['proposed_at']} by {d['proposed_by']}")
        print(f"Target   : {d['target']}")
        print(f"Reason   : {d['reason']}")
        print(f"Old      : {repr(d['old_string'][:120])}")
        print(f"New      : {repr(d['new_string'][:120])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Propose or apply self-improvement patches to Otto's core files."
    )
    sub = parser.add_subparsers(dest="command")

    # propose
    propose_p = sub.add_parser("propose", help="Stage a new patch proposal")
    propose_p.add_argument("--target", required=True, help="Relative path to target file")
    propose_p.add_argument("--old-string", required=True, help="Text to replace")
    propose_p.add_argument("--new-string", required=True, help="Replacement text")
    propose_p.add_argument("--reason", required=True, help="Why this patch improves Otto")
    propose_p.add_argument("--proposed-by", default="reflection")
    propose_p.add_argument("--spec", help="JSON file with patch spec (alternative to flags)")

    # apply
    apply_p = sub.add_parser("apply", help="Apply an approved patch (heartbeat only)")
    apply_p.add_argument("patch_file", help="Path to staged patch JSON")
    apply_p.add_argument(
        "--eval-gate",
        action="store_true",
        default=False,
        help="Run capability eval before/after; revert patch if score drops",
    )

    # list
    sub.add_parser("list", help="List all pending patch proposals")

    args = parser.parse_args()

    if args.command == "list":
        list_pending()
        return

    if args.command == "apply":
        apply_patch(Path(args.patch_file), eval_gate=getattr(args, "eval_gate", False))
        return

    if args.command == "propose" or args.command is None:
        # Support --spec as JSON file input
        if hasattr(args, "spec") and args.spec:
            spec = json.loads(Path(args.spec).read_text())
            target = spec["target"]
            old_string = spec["old_string"]
            new_string = spec["new_string"]
            reason = spec["reason"]
            proposed_by = spec.get("proposed_by", "reflection")
        else:
            if not all([args.target, args.old_string, args.new_string, args.reason]):
                parser.print_help()
                sys.exit(1)
            target = args.target
            old_string = args.old_string
            new_string = args.new_string
            reason = args.reason
            proposed_by = args.proposed_by

        # Validate
        try:
            validate_patch(target, old_string, new_string)
        except ValueError as e:
            die(f"Patch validation failed: {e}")

        # Stage
        patch_path = stage_patch(target, old_string, new_string, reason, proposed_by)
        patch_data = json.loads(patch_path.read_text())

        # Log to memory
        logged = log_to_memory(patch_data, patch_path)

        print(json.dumps({
            "status": "staged",
            "patch_id": patch_data["patch_id"],
            "target": target,
            "staged_at": str(patch_path),
            "memory_logged": logged,
        }, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
