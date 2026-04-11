/**
 * EVM Chain Adapter — implements ChainAdapter for EVM-compatible chains.
 *
 * Phase 0: Stub implementation. Phase 1 will add viem integration
 * for actual on-chain interactions.
 */

import type { ChainAdapter, CreateEventParams, Hex } from '@zkpresence/sdk';
import type { ChainConfig } from './chains';

export interface EvmAdapterConfig {
  /** Chain configuration. */
  chain: ChainConfig;
  /** Deployed ZkPresence contract address. */
  contractAddress: Hex;
  /** RPC URL for the chain. */
  rpcUrl: string;
}

/**
 * EVM adapter for zkPresence on-chain interactions.
 *
 * Uses viem under the hood (peer dependency).
 * Phase 0: interface only — methods throw NotImplemented.
 */
export class EvmAdapter implements ChainAdapter {
  readonly chainId: string;
  readonly name: string;

  private readonly config: EvmAdapterConfig;

  constructor(config: EvmAdapterConfig) {
    this.config = config;
    this.chainId = config.chain.chainId.toString();
    this.name = config.chain.name;
  }

  async deployVerifier(_vkey: Hex): Promise<{ address: Hex; txHash: string }> {
    // Phase 1: Deploy ZkPresence contract via viem
    throw new Error('Not implemented — Phase 1');
  }

  async createEvent(_params: CreateEventParams): Promise<{ eventId: bigint; txHash: string }> {
    // Phase 1: Call createEvent on ZkPresence contract
    throw new Error('Not implemented — Phase 1');
  }

  async submitProof(
    _proof: Uint8Array,
    _publicValues: Uint8Array,
  ): Promise<{ txHash: string }> {
    // Phase 1: Call verifyAttendance on ZkPresence contract
    throw new Error('Not implemented — Phase 1');
  }

  async hasAttended(eventId: bigint, commitment: Hex): Promise<boolean> {
    void eventId;
    void commitment;
    // Phase 1: Call hasAttended view function
    throw new Error('Not implemented — Phase 1');
  }

  async isNullifierUsed(nullifier: Hex): Promise<boolean> {
    void nullifier;
    // Phase 1: Call isNullifierUsed view function
    throw new Error('Not implemented — Phase 1');
  }
}
