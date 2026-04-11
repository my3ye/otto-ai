/**
 * @zkpresence/react — React hooks for zkPresence.
 *
 * Phase 0: Placeholder. Phase 1 will add:
 * - useZkPresence() — context provider
 * - useProveAttendance() — proof generation hook
 * - useEventDetails() — on-chain event query
 * - useAttendanceStatus() — check attendance status
 *
 * @packageDocumentation
 */

// Re-export SDK types for convenience
export type {
  PublicValues,
  Proof,
  AttestationMode,
  ProofStatus,
} from '@zkpresence/sdk';
