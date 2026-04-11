/**
 * Core types for zkPresence — TypeScript mirrors of Rust types.
 *
 * These types match the on-chain and circuit-level data structures
 * defined in `crates/core/src/types.rs`.
 */

export type Hex = `0x${string}`;

/** Attestation modes supported by the circuit. */
export enum AttestationMode {
  /** QR code scan at venue. */
  QrCode = 0,
  /** Geohash proximity proof. */
  GeoProximity = 1,
  /** Direct organizer signature on identity commitment. */
  OrganizerSignature = 2,
}

/** Proof generation status. */
export enum ProofStatus {
  Queued = 'queued',
  Proving = 'proving',
  Complete = 'complete',
  Submitted = 'submitted',
  Failed = 'failed',
}

/** Public values committed by the ZK circuit (visible on-chain). */
export interface PublicValues {
  eventId: bigint;
  nullifier: Hex;
  identityCommitment: Hex;
  attestationMode: AttestationMode;
  timestamp: bigint;
  organizerPubkeyHash: Hex;
}

/** A generated ZK proof with metadata. */
export interface Proof {
  proofBytes: Hex;
  publicValues: PublicValues;
  vkeyHash: Hex;
  metadata: ProofMetadata;
}

/** Metadata about proof generation. */
export interface ProofMetadata {
  proverMode: 'mock' | 'local' | 'network';
  generationTimeMs: number;
  cycleCount: number;
}

/** Parameters for creating an on-chain event. */
export interface CreateEventParams {
  locationHash: Hex;
  startTime: Date;
  endTime: Date;
  organizerPubkeyHash: Hex;
}

/**
 * Chain adapter interface — abstracts blockchain interactions.
 * Implement this for each target chain (EVM, Solana, etc.).
 */
export interface ChainAdapter {
  readonly chainId: string;
  readonly name: string;

  /** Deploy the ZkPresence verifier contract. */
  deployVerifier(vkey: Hex): Promise<{ address: Hex; txHash: string }>;

  /** Create a new event on-chain. */
  createEvent(params: CreateEventParams): Promise<{ eventId: bigint; txHash: string }>;

  /** Submit a proof of attendance on-chain. */
  submitProof(proof: Uint8Array, publicValues: Uint8Array): Promise<{ txHash: string }>;

  /** Check if an identity commitment has attended an event. */
  hasAttended(eventId: bigint, commitment: Hex): Promise<boolean>;

  /** Check if a nullifier has been used. */
  isNullifierUsed(nullifier: Hex): Promise<boolean>;
}
