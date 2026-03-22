---
name: Token Launch Filtering & Anti-Sniper Research
description: Comprehensive research on anti-sniper/anti-bot mechanisms for crypto token launches — Solana, EVM, frontend, fair launch examples, anti-whale enforcement, VRF analysis
type: project
---

# Token Launch Filtering & Anti-Sniper Research (2026-03-17)

## Solana-Specific Mechanisms

### 1. Batch / Uniform Price Auction (Metaplex Genesis)
- Launched July 2025. Three modes: Launch Pool (proportional distribution), Presale (fixed price), Uniform Price Auction.
- UPA: all bids evaluated at auction close, clearing price = lowest bid that fully sells supply. All buyers pay same price.
- Key property: no benefit to submitting higher priority fees — bots cannot frontrun because price is not set until auction ends.
- Revenue: $422K in August 2025, 240% MoM growth. DeFiTuna, Collector's Crypt, Portals have used it.
- Source: https://blockworks.com/news/solana-cutting-mev-snipers

### 2. Meteora Alpha Vault (Anti-Sniper Suite)
- Deposit commitment period: users deposit SOL/USDC before public launch begins. After period closes, no withdrawals or new deposits.
- Two modes: Pro-Rata (unlimited deposits, pro-rata allocation at avg price) vs FCFS (first-come first-served up to cap).
- Stake escrow fee: charged in native SOL per vault account, sent to Meteora treasury — makes multi-wallet bypass prohibitively expensive.
- Projects can add vesting/lock on distributed tokens (1+ day lock) — discourages sniper bots that need to dump immediately.
- Optional per-user cap + wallet whitelist on FCFS mode.
- Fee Scheduler: configurable decaying fee structure — high fees at launch that decay over time, penalizing bots that must buy immediately.
- Rate Limiter (DAMM v2): size-based surcharges on large buys during launch window.
- Source: https://docs.meteora.ag/meteoras-anti-sniper-suite-a.s.s./meteoras-anti-sniper-suite

### 3. Orca Wavebreak ("Human-First" Launchpad)
- Launched July 29, 2025. First to claim "mechanically prevent sniping, bundling, sandwiching and wash trading."
- Integrates CAPTCHA with on-chain permission structure — CAPTCHA result generates a signed permission credential stored on-chain.
- Per-transaction buy caps enforce max token quantity per tx.
- Daily rewards pool for users (proportional to volume) — incentivizes human participation over bot extraction.
- Note: technical details of CAPTCHA-to-on-chain permission bridge not publicly documented.
- Source: https://www.okx.com/en-us/learn/orca-wavebreak-solana-defi

### 4. Heaven DEX (Sniper Tax)
- Vertically integrated launchpad + proprietary AMM DEX — tokens only list on Heaven's own DEX.
- "Sniper tax": linearly decaying fee applied for exactly 6 seconds after launch. After 6s, fee returns to normal.
- Deters bots that must execute in first block(s). Legitimate retail unaffected after 6s.
- Token classification system: Creator (serious projects, 1% fee), Community (memecoins, 0.1% fee), Blocked.
- Source: https://www.ainvest.com/news/heaven-dex-future-solana-memecoin-launchpads-paradigm-tokenomics-2508/

### 5. Believe App (Meteora Partnership, Dynamic Fee Bonding Curve)
- Social launch via X/Twitter reply — users don't need wallets.
- Anti-snipe fee: starts high at launch, decays dynamically as market cap grows, floors at 2% after graduation.
- Graduates to Meteora DLMM at $100K market cap.
- Limitation: at sub-$50K market cap, high fees are small in dollar terms and easily absorbed by bots.
- Source: https://solanacompass.com/learn/Lightspeed/the-solana-token-launchpad-coming-for-venture-capital-ryan-connor

### 6. Jito MEV Protection (DontFront)
- Jito Block Engine handles ~95% of Solana stake (as of April 2025).
- Bundle mechanism: up to 5 transactions execute atomically and sequentially in same block.
- DontFront: add public key starting with `jitodontfront` as read-only account in any instruction. Jito enforces the tx MUST appear at index 0 of any bundle — prevents frontrunning bundles.
- BAM (Bundle Assembly Marketplace): launched July 2025, uses TEE nodes, transaction flow private until execution.
- Best for: protecting individual user swaps from sandwich attacks. NOT a full launch protection system — it protects individual transactions, not the launch ordering itself.
- Source: https://solana.com/developers/guides/advanced/mev-protection

### 7. Pump.fun — Essentially Unprotected
- No native anti-sniper mechanism. Bots detect new tokens in 0.01s, execute in 0.05s. Regular users see tokens after 60s.
- 87% of total sniper profits occur within first 18 seconds of trading (March 2025 analysis of 50 launches).
- No commit-reveal, no VRF, no fee scheduler used by pump.fun itself.
- Source: https://solanacompass.com/learn/Lightspeed/what-weve-learned-from-pumpfuns-sniping-problem

---

## EVM-Specific Mechanisms

### 1. Uniswap v4 Continuous Clearing Auction (CCA)
- Built with Aztec. Live on v4. Available on Uniswap frontend as of late 2025.
- Block-by-block auction: fixed token supply released per block, clearing price = highest price at which all tokens for that block sell.
- Higher bids fill first; at clearing price, pro-rata fill. All participants in same block pay same price.
- Bids are spread across remaining blocks (user specifies max price + total spend). Early participants get better average price.
- At auction end: proceeds automatically seed a v4 pool at the discovered clearing price.
- Optional ZK Passport module for private/verifiable participation (with Self Protocol / ZK ID).
- Anti-sniper property: no benefit to high gas fees or MEV — all bids in a block settle simultaneously at one price.
- Source: https://blog.uniswap.org/continuous-clearing-auctions

### 2. Uniswap v4 Hooks for Launch Protection
- Hooks are smart contracts attached to v4 pool lifecycle: beforeSwap, afterSwap, beforeAddLiquidity, afterAddLiquidity, beforeRemoveLiquidity.
- Flaunch (Base): 30-minute fixed-price pre-launch period, then open market. Uses fee distribution hook — 100% of fees go to developer. "Progressive Bid Wall" hook: fees accumulate and auto-place 0.1 ETH limit buy orders below spot, creating price floor.
- Angstrom: only staked validators can execute swaps — fully permissioned DEX via hook.
- Generic patterns: hooks can enforce per-wallet trade caps, time-gated trading (first N blocks restricted), KYC allowlist checks, dynamic fee structures, max transaction size.
- Source: https://www.blocmates.com/articles/flaunch-redefining-launchpads-with-fixed-price-fair-launch

### 3. ERC-20 Smart Contract Anti-Bot Patterns

**Block-Level Cooldown (most common):**
```solidity
mapping(address => uint256) private _buyBlock;
modifier antiBot(address recipient) {
    require(_buyBlock[recipient] != block.number, "Same block buy detected");
    _buyBlock[recipient] = block.number;
    _;
}
```
Prevents multiple buys from same address in same block. Effective against basic sandwich bots.

**Address-Level Time Cooldown:**
- Mandatory wait between trades from same address (e.g., 300 seconds).
- Owner can disable by setting cooldown to 0.

**Max Wallet / Max Transaction:**
```solidity
require(balanceOf(recipient) + amount <= maxWalletToken, "Exceeds max wallet");
require(amount <= maxTxAmount, "Exceeds max tx");
```
DEX pair addresses must be exempted or all sells break once pool balance exceeds limit.

**First-N-Blocks Blacklist:**
- Addresses that buy within first 50 blocks get flagged/blacklisted during launch. Self-destructs after 50 blocks.
- Used heavily on BSC (37.36% of contracts) vs Ethereum (17.9% of contracts).

**tx.origin Check:**
```solidity
require(msg.sender == tx.origin, "No contract callers");
```
Blocks contract-to-contract calls (bot scripts deployed as contracts). BYPASS WARNING: EIP-7702 (Ethereum Pectra, May 2025) breaks this check — smart contracts can now make msg.sender == tx.origin.

### 4. LBP (Liquidity Bootstrapping Pool) — Copper.co / Fjord Foundry / Balancer
- Price starts at a high "magnified" level (97:3 token:collateral ratio, up to 99x magnification vs collateral deposited).
- Weight shifts automatically over time from 97:3 → 70:30, causing price to decline unless buyers participate.
- Anti-sniper property: bots buying at launch push price to absurd highs (50 bots buying at launch = price goes to hundreds of millions of market cap instantly). Economic disincentive to snipe.
- Runs 2-5 days typically. Fjord supports zero-collateral (virtual liquidity) LBPs.
- Source: https://docs.alchemist.wtf/copper/faqs

### 5. Gnosis Auction / CoW Protocol Batch Auctions
- Orders collected over time window, all settle at single clearing price simultaneously.
- Timing advantage eliminated — first and last bids within window treated equally.
- MEV eliminated — all orders settle in same batch.

---

## Frontend / Off-Chain Filtering

### 1. Allowlist Registration with Signature Proof (PREMINT model)
- Users connect wallet, PREMINT validates wallet ownership via signature (no tx permissions granted).
- Optional: require Twitter follow, Discord membership, minimum NFT/token holdings, wallet age.
- IP flagging: users signing up with multiple wallets from same IP get flagged.
- Creator exports CSV allowlist → uploads to smart contract as Merkle tree root.
- Used by 40,500+ projects, 5.9M+ wallets registered.
- Source: https://www.premint.xyz/

### 2. Discord/Twitter OAuth-Gated Allowlist
- User authenticates Discord/Twitter → backend verifies account age, follower count, etc. → if passes, signs an approval message → user submits signed approval in smart contract.
- Collab.Land: 6.5M+ verified wallets, handles Discord/Telegram gating.
- Prevents bot wallets from registering if they lack real social presence.
- Technical flow: Discord OAuth2 → backend issues signed proof → frontend submits `proof` + wallet address to contract.

### 3. Human Passport / Gitcoin Passport (Sybil Scoring)
- Formerly Gitcoin Passport, acquired by Holonym Foundation Dec 2024, now human.tech.
- Users collect "stamps" (Twitter, GitHub, ENS, Lens, Farcaster verified credentials) → aggregate score.
- Score ≥20 threshold typically used for gating. Free API, 2M+ users.
- Protected $430M+ in airdrop/grant funds.
- For launch: gate the registration form to score ≥ threshold, export passing wallets as allowlist.
- Source: https://human.tech/blog/human-passport-proof-of-personhood-and-sybil-resistance-for-web3

### 4. Cloudflare Turnstile
- CAPTCHA-alternative, runs in browser background. Returns signed token upon verification.
- Can gate the wallet registration endpoint — only verified humans can submit a wallet to the allowlist.
- Does NOT verify unique humans — one person can solve many Turnstile challenges. Raises cost for mass bot registration.
- Free tier available. Server-side validation via Cloudflare API.
- Source: https://developers.cloudflare.com/turnstile/

### 5. Wallet Age Check
- Via Solscan API, Etherscan API, or Helius: check first transaction timestamp of connecting wallet.
- Gate: reject wallets created < 30 days ago (standard) or < 90 days (stricter).
- Cheap to bypass: create wallet 30 days before launch. Better as one factor in a multi-factor stack.

### 6. ZK Passport (Self Protocol / zkPassport)
- ZK proof derived from government ID NFC chip (passport) or Aadhaar. No biometrics stored.
- Used in Uniswap CCA as optional module.
- Strongest identity gate: country-level filtering, age verification, unique person enforcement.
- Raised $9M, used by Google + Aave.

---

## Existing Project Examples

| Project | Chain | Mechanism | Result |
|---|---|---|---|
| Metaplex Genesis | Solana | Uniform Price Auction | $422K rev Aug 2025, 240% MoM growth |
| Orca Wavebreak | Solana | On-chain CAPTCHA + buy caps | Launched July 2025, "mechanically prevents sniping" claim |
| Heaven DEX | Solana | 6-second linearly decaying sniper tax + own AMM | LIGHT token +225% with buyback model |
| Meteora Alpha Vault | Solana | Commitment deposit + pro-rata/FCFS + stake escrow fee | Used by many Solana TGEs |
| Believe | Solana | Dynamic decay fee bonding curve, Meteora graduation | Viral via X/Twitter, $100K graduation threshold |
| Uniswap CCA | EVM (all v4 chains) | Block-by-block clearing auction + ZK Passport | Live on Uniswap frontend, Aztec was first project |
| Flaunch | Base (v4) | 30-min fixed price lock + Progressive Bid Wall hook | Fee redistribution to devs |
| Fjord Foundry LBP | EVM | Weight-shifting LBP, high initial price | Industry standard for DeFi project launches |
| Copper.co LBP | EVM | Same as Fjord (Balancer-based), 97:3 start ratio | Used by Merit Circle, many others |
| pump.fun | Solana | None — fully sniped | 87% sniper profits in first 18s |

---

## Anti-Whale Hard Cap Enforcement

### Smart Contract Patterns
- `require(balanceOf(recipient) + amount <= maxWalletToken)` — percentage of total supply (1-5% typical).
- Must exempt: DEX pair addresses, token vesting contracts, treasury multisig, staking contracts.
- Optional sunset: owner function `removeMaxWallet()` called after e.g. 24h from launch.

### Known Bypasses
1. **Multiple wallets**: simplest — create N wallets, each buys up to limit. Chainlink "Oldwhite" used 150+ wallets to accumulate 1.06M LINK worth $7M.
2. **Flash loan contract**: borrows, buys, sends to multiple controlled addresses in one tx.
3. **Contract proxy**: if only `msg.sender == tx.origin` check, EIP-7702 (Pectra, May 2025) breaks this.

### Countermeasures
1. **Stake escrow fee per account** (Meteora Alpha Vault): SOL fee per registration makes multi-wallet spam uneconomical.
2. **Deposit address clustering** (Nansen/Chainalysis): if wallets A+B both withdrew from Binance to same deposit address, they are same person — cap them jointly.
3. **World ID nullifier-based cap**: `nullifierInvested[nullifierHash] + amount <= MAX_PER_PERSON` — multiple wallets from same biometric person share one cap bucket. 38M+ users on World ID.
4. **Graph-based clustering** (TrustScan / TrustaLabs): 0-100 Sybil score, links wallets by funding pattern and transaction graph.
5. **On-chain CAPTCHA** (Wavebreak): permission credential required per transaction, making bot orchestration harder at scale.

---

## VRF for Launch Sequencing — Real vs. Marketing

### What VRF Actually Does
- Verifiable Random Function: off-chain oracle generates a cryptographically provable random number that cannot be predicted by the oracle operator or any on-chain participant.
- Switchboard v2: uses VRF counter + recent blockhash as input. Requires ~50 transactions to settle. V3 (SRS): uses Intel SGX enclave, single-transaction callback.
- Chainlink VRF: most widely used. Generates random values + on-chain proof. Cross-chain capable.

### What VRF Does NOT Do for Token Launches
- VRF cannot prevent a bot from being first to buy once the pool opens.
- VRF cannot sequence which buyer gets filled first in a DEX swap — that is determined by transaction ordering, not randomness.
- VRF IS useful for: randomized whitelist selection (lottery from a registered allowlist), randomized NFT minting order, randomized airdrop recipient selection.

### "Quantum Koinkulator" — Assessment
- No on-chain documentation found for this specific term. KOINK token / $KOINK Standard has no public technical documentation indexed.
- Assessment based on what VRF actually does: if "Quantum Koinkulator" uses VRF to RANDOMIZE THE ORDER in which pre-registered allowlist participants receive their allocation — this is legitimate and prevents first-come advantage.
- If it claims to prevent bots from buying on a live AMM/pool — this is marketing language. VRF cannot prevent a bot from submitting a swap transaction before a human.
- Likely interpretation: VRF-based lottery from a pre-registered allowlist. This is real protection IF combined with an allowlist gate (only registered humans participate). If the pool is open to all, VRF sequencing is theater.

### Honest Assessment of All "Fair Launch" Claims
- No mechanism is bot-proof if the pool is permissionlessly open. The most effective mechanisms either: (a) eliminate timing advantage entirely (batch auction / uniform price), or (b) gate participation to verified humans before trading opens (allowlist + identity).
- Decaying fees / sniper tax: economic deterrence only, not technical prevention. High-conviction bots absorb the fee.
- Time-based cooldowns: raise cost, do not eliminate bots. Bots use one wallet per token.

---

## Recommended Stack for Maximum Protection (Ranked by Effectiveness)

1. **Batch/Uniform Price Auction** — eliminates timing advantage entirely. Best for meaningful TGEs.
2. **Meteora Alpha Vault (Pro-Rata)** — commitment deposit + stake escrow fee counters multi-wallet. Best for Solana DeFi projects.
3. **LBP (Fjord/Copper)** — economic deterrence via high initial price. Good for EVM DeFi tokens with days-long price discovery.
4. **Allowlist + Human Passport score gate** — gate registration, export Merkle tree to contract. Best combined with any of the above.
5. **World ID nullifier cap** — enforce per-person hard cap, strongest anti-whale. Best for fair distribution goals.
6. **Decaying fee / sniper tax** — cheapest to implement, weakest on its own. Combine as a layer.
7. **tx.origin == msg.sender** — blocks contract bots but broken by EIP-7702 on Ethereum post-Pectra. Still valid on Solana (no equivalent upgrade yet).

## Sources
- https://blockworks.com/news/solana-cutting-mev-snipers
- https://docs.meteora.ag/meteoras-anti-sniper-suite-a.s.s./meteoras-anti-sniper-suite
- https://docs.meteora.ag/anti-sniper-suite/alpha-vault/alpha-vault-modes
- https://blog.uniswap.org/continuous-clearing-auctions
- https://help.fjordfoundry.com/fjord-foundry-docs/for-sale-participants/token-sale-types/liquidity-bootstrapping-pools-lbps
- https://docs.alchemist.wtf/copper/faqs
- https://solana.com/developers/guides/advanced/mev-protection
- https://www.adevarlabs.com/blog/on-chain-randomness-on-solana-predictability-manipulation-safer-alternatives-part1
- https://switchboardxyz.medium.com/verifiable-randomness-on-solana-46f72a46d9cf
- https://www.premint.xyz/
- https://human.tech/blog/human-passport-proof-of-personhood-and-sybil-resistance-for-web3
- https://developers.cloudflare.com/turnstile/
- https://www.coindesk.com/business/2022/12/12/chainlink-whale-oldwhite-used-more-than-150-wallets-to-avoid-staking-limits
- https://solanacompass.com/learn/Lightspeed/what-weve-learned-from-pumpfuns-sniping-problem
- https://www.okx.com/en-us/learn/orca-wavebreak-solana-defi
- https://www.ainvest.com/news/heaven-dex-future-solana-memecoin-launchpads-paradigm-tokenomics-2508/
- https://www.blocmates.com/articles/flaunch-redefining-launchpads-with-fixed-price-fair-launch
- https://forum.openzeppelin.com/t/how-can-i-protect-my-token-from-whales/26453
