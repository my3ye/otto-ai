/**
 * @zkpresence/server — Server-side utilities for zkPresence.
 *
 * Phase 0: Placeholder. Phase 1 will add:
 * - Proof queue manager (Redis-backed)
 * - Webhook handlers for proof completion
 * - Event indexer for on-chain event sync
 * - Health check utilities
 *
 * @packageDocumentation
 */

// Re-export SDK types for convenience
export type {
  PublicValues,
  Proof,
  ProofStatus,
} from '@zkpresence/sdk';
