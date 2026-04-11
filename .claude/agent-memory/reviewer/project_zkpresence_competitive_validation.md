---
name: zkPresence competitive landscape validation
description: WF Step 2 validation of zkPresence competitive landscape synthesis (2026-04-11). MINOR_CHANGES 7.5/10. Critical: todo!() vs // TODO: conflation + missing security escalation warning.
type: project
---

zkPresence competitive landscape synthesis (2026-04-11, WF Step 2). MINOR_CHANGES 7.5/10.

**Why:** Step 2 validation of research pipeline producing competitive positioning for zkPresence ZK attendance protocol.
**How to apply:** Use as prior context when reviewing future zkPresence work; "todo!() vs // TODO:" distinction is a recurring Rust issue to watch.

## Critical Issues

1. **todo!() vs // TODO: conflation**: Synthesis says "Circuit panics at runtime" for all 4 locations. Only true for line 20's `todo!()` MACRO. Lines 61/88/104 are `// TODO:` COMMENTS — silent ECDSA omission. The silence is MORE dangerous: fixing line 20 first creates a circuit that runs but accepts forged attestations without error. Recommendations must say: fix ECDSA stubs simultaneously, not after.

2. **Source count methodology for Insight #1**: "Sources: 4 (codebase grep, 4 confirmed locations)" — "4 confirmed locations" is data, not 4 independent sources. It is 1 grep source that found 4 locations.

## Warnings

3. **SP1 version precision**: Cargo.toml specifies `"6.1"` (semver range, resolves to latest 6.1.x). Synthesis claims "v6.1.0" — slight precision overclaim. ARCHITECTURE.md also says `"6.1"`.

4. **ZkPresence.sol line count**: 147 lines (synthesis says 148). Off-by-one. Trivial.

5. **Geohash analysis CORRECT but ARCHITECTURE.md itself contradicts**: Type definition comment in ARCHITECTURE.md says "6-char precision (~1.2km)" but pseudocode implementation says "5-char match ~5km." Synthesis correctly identifies effective precision as 5-char. The original retrieval's "6-char/1.2km" claim came from ARCHITECTURE.md's misleading type comment — this ambiguity should be noted for documentation cleanup.

## What's Good

- All HIGH confidence claims verified against live codebase
- Zero tests confirmed (comprehensive grep + find, no false negatives)
- Competitive matrix reasoning sound (Zupass/Semaphore/POAP differentiation)
- Recommended actions specific and implementable (SP1 precompile API reference, grant targets)
- Geohash precision discrepancy correctly caught and explained
- Confidence levels (HIGH/MEDIUM) appropriate to evidence quality
- "No SP1-native open-source attendance protocol" as MEDIUM (appropriate for negative match)
