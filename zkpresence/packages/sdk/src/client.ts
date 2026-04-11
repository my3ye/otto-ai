/**
 * ZkPresenceClient — main entry point for the SDK.
 *
 * Coordinates proof generation (via prover service) and on-chain
 * submission (via chain adapter).
 */

import type { ChainAdapter, Proof, ProofStatus } from './types';

export interface ZkPresenceClientConfig {
  /** URL of the zkPresence prover service. */
  proverUrl: string;
  /** Chain adapter for on-chain interactions. */
  adapter: ChainAdapter;
}

/**
 * High-level client for interacting with the zkPresence protocol.
 *
 * Phase 0: Stub implementation. Will be fleshed out in Phase 1
 * when the prover service API is defined.
 */
export class ZkPresenceClient {
  private readonly proverUrl: string;
  private readonly adapter: ChainAdapter;

  constructor(config: ZkPresenceClientConfig) {
    this.proverUrl = config.proverUrl;
    this.adapter = config.adapter;
  }

  /** Get the chain adapter. */
  get chain(): ChainAdapter {
    return this.adapter;
  }

  /**
   * Request proof generation for an attendance claim.
   * Returns a proof ID for status polling.
   *
   * @param _userSecret - 32-byte user secret (never leaves client)
   * @param _eventId - Event to prove attendance for
   * @param _attestationData - Mode-specific attestation data
   */
  async requestProof(
    _userSecret: Uint8Array,
    _eventId: bigint,
    _attestationData: unknown,
  ): Promise<{ proofId: string }> {
    // Phase 1: POST to prover service
    throw new Error('Not implemented — Phase 1');
  }

  /** Poll proof generation status. */
  async getProofStatus(_proofId: string): Promise<ProofStatus> {
    // Phase 1: GET from prover service
    throw new Error('Not implemented — Phase 1');
  }

  /** Retrieve a completed proof. */
  async getProof(_proofId: string): Promise<Proof> {
    // Phase 1: GET from prover service
    throw new Error('Not implemented — Phase 1');
  }

  /** Submit a proof on-chain via the chain adapter. */
  async submitProof(proof: Uint8Array, publicValues: Uint8Array): Promise<{ txHash: string }> {
    return this.adapter.submitProof(proof, publicValues);
  }
}
