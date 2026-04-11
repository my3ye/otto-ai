/**
 * @zkpresence/sdk — TypeScript SDK for the zkPresence protocol.
 *
 * @packageDocumentation
 */

export { ZkPresenceClient } from './client';
export type { ZkPresenceClientConfig } from './client';

export {
  AttestationMode,
  ProofStatus,
} from './types';

export type {
  Hex,
  PublicValues,
  Proof,
  ProofMetadata,
  CreateEventParams,
  ChainAdapter,
} from './types';
