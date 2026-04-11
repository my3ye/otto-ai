/**
 * Supported EVM chain configurations.
 *
 * SP1 verifier gateway addresses are the same across all chains
 * (deployed via CREATE2 at a deterministic address).
 */

export interface ChainConfig {
  chainId: number;
  name: string;
  /** SP1 Verifier Gateway address (same across chains via CREATE2). */
  verifierGateway: `0x${string}`;
  /** Block explorer URL pattern. */
  explorerUrl: string;
}

/**
 * SP1 Verifier Gateway — deterministic address on all EVM chains.
 * See: https://docs.succinct.xyz/docs/verification/onchain/contract-addresses
 */
export const SP1_VERIFIER_GATEWAY = '0x3B6041173B80E77f038f3F2C0f9744f04837185e' as const;

export const chains: Record<string, ChainConfig> = {
  base: {
    chainId: 8453,
    name: 'Base',
    verifierGateway: SP1_VERIFIER_GATEWAY,
    explorerUrl: 'https://basescan.org',
  },
  baseSepolia: {
    chainId: 84532,
    name: 'Base Sepolia',
    verifierGateway: SP1_VERIFIER_GATEWAY,
    explorerUrl: 'https://sepolia.basescan.org',
  },
  arbitrum: {
    chainId: 42161,
    name: 'Arbitrum One',
    verifierGateway: SP1_VERIFIER_GATEWAY,
    explorerUrl: 'https://arbiscan.io',
  },
  ethereum: {
    chainId: 1,
    name: 'Ethereum',
    verifierGateway: SP1_VERIFIER_GATEWAY,
    explorerUrl: 'https://etherscan.io',
  },
  sepolia: {
    chainId: 11155111,
    name: 'Sepolia',
    verifierGateway: SP1_VERIFIER_GATEWAY,
    explorerUrl: 'https://sepolia.etherscan.io',
  },
};
