# Otto Music — Implementation Roadmap
**Every artist deserves to own their signal.**

*Last updated: 2026-03-20 | Status: Concept → Build*

---

## Executive Summary

Spotify pays $0.003 per stream. Labels own your masters and take 80%. The discovery algorithm is a black box optimized for ad revenue, not art.

Otto Music is not a streaming platform. It is a sovereign music ecosystem — four fronts operating as one: Music Manager (artist tooling), Music Player (the listening experience), Music Studio (creation tools), and Events/Festivals (live culture). Artists own masters by default. Smart contracts pay royalties on-chain, instantly. Discovery is community-governed, not corporate-optimized.

Otto Music is the cultural heartbeat of Tusita and the sonic identity of ONEON. It is not a Spotify clone on blockchain. It is what the music industry looks like when promotion is sovereign and extraction is engineered out.

---

## Phase 0: Architecture & Foundations
**Target: Weeks 1–8 | Budget: ~$20K dev equivalent**

### Core Architecture Decisions

**Storage Layer**
- Master files: IPFS (content-addressed, immutable) via Filecoin for persistence guarantees
- Metadata: on-chain (Ethereum/Base) — artist address, title, ISRC if available, royalty splits, release date
- Audio streaming: hybrid — IPFS CID resolution for ownership proof, CDN delivery for playback performance (Cloudflare R2 or equivalent)
- No single point of control. Labels cannot take down what the artist published.

**Royalty Contract Architecture**
- `OttoMusicRights.sol` — master ownership record (NFT-based, transferable, artist-minted)
- `RoyaltySplitter.sol` — configurable split: artist%, collaborators%, label% (0% if indie), Otto treasury%
- `StreamingPayment.sol` — micro-payment accumulator: batches per-stream credits, distributes on threshold or claim
- `PublishingRights.sol` — composition vs. master distinction; sync licensing hooks
- All contracts: EVM-first (Base + Ethereum), ONEON identity for artist verification

**ONEON Identity Integration**
- Artists: ONEON DID for sovereign identity (no platform can deplatform an artist's identity)
- Fans: ONEON DID for contribution history (discovery contributions → on-chain record)
- Authentication: ONEON login → Otto Music account, no email required
- Stub available in Phase 0, full integration when ONEON v1 ships

**Infrastructure**
- Backend API: FastAPI, stateless, runs on otto-machine initially
- DB: PostgreSQL (metadata indexing, play counts, fan records), Redis (real-time leaderboards)
- Indexer: event listener for royalty contract events → DB sync
- Dev environment: Docker Compose service stack

### Success Metrics
- Architecture document ratified
- Smart contract interfaces defined (not deployed yet)
- IPFS + CDN pipeline tested: upload → stream latency <3s
- Royalty calculation model validated (test vectors for split scenarios)
- ONEON identity stub functional

### Dependencies
- ONEON: basic DID spec (can proceed with ETH address as identity fallback)
- 505 Systems: governance hooks for discovery algorithm (can stub in Phase 0)

---

## Phase 1: Music Manager
**Target: Weeks 9–22 | Budget: ~$45K dev + $20K audit**

### Problem
Independent artists have no sovereign tooling. Bandcamp was the closest thing and Songtradr bought it for the data. DistroKids keeps your masters hostage behind annual fees. Stem Disintermediates labels but doesn't give artists governance. None of them pay royalties on-chain.

### Deliverables

**Artist Onboarding**
- ONEON DID or ETH wallet as identity (no email required)
- Artist profile: name, genre tags, links, bio — stored on-chain as metadata
- Verification: optional (KYC for certain features), not required to publish
- Dashboard: single view of all masters, royalty balance, listener stats

**Music Publishing**
- Upload flow: audio file → IPFS → CID recorded on-chain → NFT minted representing master
- Metadata standard: custom Otto Music schema (superset of ERC-7160 for multimedia)
- Royalty configuration: split percentages at publish time (collaborators added by wallet address)
- Formats supported: MP3, WAV, FLAC, AAC (all transcoded to streaming format, original stored)
- Album/EP/single grouping: playlist-style NFT wrapper

**Royalty Contracts — Deployed**
- `OttoMusicRights.sol` deployed on Base mainnet
- `RoyaltySplitter.sol` deployed, configurable at publish time
- `StreamingPayment.sol` deployed, accumulates stream credits
- Payment denomination: USDC initially (stable, no volatility exposure for artists)
- Minimum payout threshold: $1 equivalent (vs. Spotify's $50 minimum)
- Payout trigger: automatic at threshold or manual claim
- Security audit: pre-deployment (focus: reentrancy, split manipulation, rounding)

**Rights Management**
- Master vs. composition distinction: separate records, separate splits
- Sync licensing: artists can mark tracks as sync-available, set license terms
- Cover songs: attribution chain support (original → cover → royalty flow)
- Takedown resistance: on-chain record cannot be deleted; platform can de-index but not destroy

**Analytics Dashboard**
- Real-time: streams, listeners, royalty accumulation
- Historical: trend charts, geographic breakdown, discovery source
- Collaborator view: each collaborator sees their split's earnings
- Export: CSV for accounting, on-chain proof for legal disputes

### Success Metrics
- 50 beta artists onboarded
- 200+ tracks published with active royalty contracts
- First royalty payment distributed on-chain (any amount)
- Smart contract audit passed, no critical findings
- Artist dashboard: satisfaction score >4/5 (beta survey)
- Mean time to publish a track: <15 minutes

### Dependencies
- Base mainnet VPN/RPC access for contract deployment
- USDC payment integration (Circle or Uniswap USDC liquidity)
- Security audit firm engagement (Phase 0 prep)

---

## Phase 2: Music Player
**Target: Weeks 23–36 | Budget: ~$40K dev**

### Problem
Discovery is the real moat for Spotify. Their algorithm serves Spotify's ad revenue, not the artist's art. Listeners who discover artists early receive nothing for that cultural labor. Otto Music makes discovery sovereign: community-governed, transparent, and rewarded.

### Deliverables

**Web Player — Core Listening Experience**
- PWA (Progressive Web App): desktop + mobile, offline capable for downloaded tracks
- Audio engine: Web Audio API, gapless playback, lossless where available
- Queue management: smart queue, shuffle (VRF-seeded for fairness), repeat modes
- Player state: ONEON DID synced across devices (play history, queue, position)
- Interface: dark by default, sound-wave aesthetic, artist art takes center stage

**Discovery Engine — Community Governed**
- Feed algorithm: fully open-source, all weights publicly readable on-chain
- Curation pools: listeners stake small amounts to surfaces artists they believe in
- Early fan equity: if an artist you surfaced crosses a listener threshold (10K, 100K), you earn a retroactive discovery reward from their royalty pool
- Community playlists: curated by ONEON community members, not editorial teams
- Trending: driven by stake-weighted attention, not play counts (prevents gaming)

**Fan Equity System**
- `FanEquity.sol` — tracks who surfaced which artist before milestone thresholds
- Discovery contributions recorded on-chain at playlist add / share / stake action
- Milestone triggers: Otto Music oracle confirms listener count → contract releases discovery reward
- Fan leaderboard: public record of who discovered whom, when

**Social Layer**
- Follow: artists, curators, other listeners (ONEON DID-based, sovereign follows)
- Comments: on-chain annotations per track (IPFS stored, CID on-chain)
- Shares: generate shareable on-chain proof of listening (not just a link)
- Reactions: signal, not just emoji — reactions contribute to curation weight

**Promoted Discovery — Sovereign Advertising**
- Artists can promote tracks via transparent on-chain bid pools
- Bids are public: anyone can see how much is in the pool, what the current winning bid is
- Listeners opt-in to see promoted tracks; opt-in listeners receive 10% of promotion pool
- DAO-governed rules: no bid manipulation, minimum quality score required
- This is advertising that serves the listener because the listener controls what they see and gets paid for their attention

**Mobile App**
- React Native: iOS + Android
- ONEON DID auth: wallet connect via WalletConnect v2
- Offline playback: downloaded tracks, synced with on-chain ownership proof
- Push notifications: royalty payments, new releases from followed artists, curation rewards

### Success Metrics
- 1,000 active listeners (weekly active)
- 10,000 tracks in catalog
- 100 fan equity events: listeners rewarded for early discovery
- Discovery pool: >$10K staked in curation pools
- Community playlist: 50+ active curators
- Mobile app: iOS + Android live on app stores

### Dependencies
- Phase 1 complete (Music Manager + royalty contracts)
- `FanEquity.sol` (new contract for Phase 2, needs separate audit scope)
- ONEON social layer basic version (follow graph)
- Chainlink oracle for listener count milestone verification

---

## Phase 3: Music Studio
**Target: Weeks 37–52 | Budget: ~$55K dev**

### Problem
Professional music production tools cost $30K+/year for a mid-tier setup (Pro Tools, plugins, mastering suite, studio time). Otto Music Studio democratizes what only major labels could afford — not by replacing human creativity, but by removing the financial barriers to professional sound.

### Deliverables

**AI-Assisted Mastering**
- Auto-mastering pipeline: upload unmastered mix → AI analysis → reference matching → mastered output
- Loudness normalization: LUFS targeting for different distribution contexts (streaming, broadcast, vinyl)
- EQ/compression suggestions: AI recommends, artist approves, all processing audible before commitment
- Reference track matching: upload a reference, Studio matches your track's tonal profile
- Format output: mastered in FLAC/MP3/WAV, all formats

**Collaborative Creation**
- Session architecture: multi-track project stored on IPFS (project file + stems)
- Real-time collaboration: operational transformation for simultaneous track editing (like Figma, but for audio)
- Version history: every save is a CID snapshot — full rollback history, nothing is lost
- Contribution tracking: every edit attributed to a collaborator's ONEON DID
- Rights auto-generation: collaboration session → suggested royalty split based on contribution % → `RoyaltySplitter.sol` preconfigured

**AI-Assisted Composition**
- Melody suggestion: hum or describe, AI generates MIDI melody options
- Chord progression assistant: input a mood/genre, get progression suggestions with Roman numeral analysis
- Lyric assistant: co-write mode — artist writes, AI suggests continuations, rhyme alternatives
- Style transfer: take a beat and suggest instrumentation in a different genre
- All AI output is creative assistance, not replacement — artist owns the final work unconditionally

**Mixing Tools**
- Browser-based DAW (lite version): 16 tracks, basic EQ/comp/reverb/delay
- VST bridge: connect local DAW via plugin (sends stems to Studio for AI processing, returns)
- Stem separation: upload a mix, extract vocals/drums/bass/other independently
- Vocal tuning: pitch correction, formant shifting, harmonizer

**Sound Library**
- Community-contributed samples: all uploads carry artist attribution + sample license
- Royalty-free by default: contributions to library grant attribution rights only
- Curated packs: community-voted quality samples organized by genre/mood/instrument
- Sample chain: if a sample is used in a released track, original contributor earns micro-royalty

**Artwork Generation**
- AI artwork: describe the track's feeling, generate album art options
- Style presets: aligned with Otto Music visual aesthetic (dark, color burst, waveform-driven)
- Integration: artwork metadata linked to track NFT on publish
- Artist owns all generated artwork unconditionally

### Success Metrics
- 500+ tracks mastered via AI mastering suite
- 50+ collaborative sessions (2+ artists working together)
- Sound library: 10,000+ community-contributed samples
- Mobile mastering: functional on iOS (process a track from phone)
- Collaboration → publish pipeline: single flow from Studio session to published track with royalty contract

### Dependencies
- Phase 2 complete (Music Player catalog and audience base)
- AI audio models: fine-tuned on public domain music (no training on copyrighted material)
- IPFS storage: project files are larger (stems = GB per project), needs Filecoin deals
- Compute: GPU for mastering and AI composition (cloud or otto-machine GPU upgrade)

---

## Phase 4: Events & Festivals
**Target: Weeks 53–72 | Budget: ~$50K dev**

### Problem
Live music is the artist's primary revenue source (Spotify killed recorded revenue), and ticketing is Ticketmaster's territory — a 30%+ fee extraction machine with monopolistic venue contracts. Otto Music Events creates sovereign live music infrastructure: community-governed venues, transparent ticketing, Tusita as the physical destination.

### Deliverables

**Event Ticketing — Sovereign**
- `OttoTicket.sol` — NFT-based tickets: transferable, programmable, non-duplicatable
- Dynamic pricing: community-voted price bands, no Ticketmaster-style dynamic surge
- Resale rules: artist/DAO sets resale cap (e.g., max 110% face value) at contract level
- Royalty on resale: artist earns % on every secondary ticket sale (encoded in NFT contract)
- Fan-to-fan transfer: direct wallet-to-wallet, no platform fee on peer transfer
- Counterfeit prevention: on-chain verification at venue gate (QR code → contract check)

**Virtual Events**
- Livestream protocol: RTMP ingest → HLS delivery, ownership proof for paid streams
- Pay-per-view: `StreamingPayment.sol` adapted for live events
- Virtual venue: 3D space (Three.js or WebXR) for immersive online events
- Fan interaction: live on-chain reactions, community tipping during streams
- Recording: post-event, stream → IPFS archive, available to ticket holders

**Tusita Festival Integration**
- Tusita venues: physical community spaces listed as official Otto Music venues
- Tusita calendar: recurring events (weekly concerts, seasonal festivals) managed via DAO
- Tusita residencies: artists can apply for residency at Tusita — stay, create, perform
- Festival infrastructure: multi-stage event coordination, artist scheduling, community volunteer coordination
- Revenue model: Tusita events fund refuge infrastructure — ticket sales split between artists (70%), Tusita operations (20%), SOS Systems (10%)

**Community Event Governance**
- Event proposals: any community member can propose an event (stake required to prevent spam)
- Venue booking: DAO votes on venue assignments for community events
- Artist booking: contribution-weighted voting on who headlines major festivals
- Festival curation: community curates the experience, not a corporate promoter
- Budget transparency: all event finances on-chain, community can audit

**Artist Tour Coordination**
- Tour planning tools: city-by-city venue discovery, logistics tracking
- Community hosting: Otto Music community members can offer private venues/homes for intimate shows
- Cross-ecosystem: Otto Travel integration for artist and fan travel coordination
- Merchandise: Otto Market integration for physical/digital merch at events

### Success Metrics
- 100 live events (virtual + physical) ticketed through Otto Music
- Tusita first major festival: 500+ attendees, full on-chain ticketing
- Zero scalping incidents (resale cap enforced at contract level)
- Artist royalty on resale: first 100 secondary sales royalties distributed
- Tour coordination: 10 artists using tour planning tools
- SOS Systems funding: first event-to-refuge allocation executed

### Dependencies
- Tusita physical infrastructure: at least one venue operational
- Phase 3 complete (Studio community has artists with catalog ready to tour)
- Otto Travel: integration for fan/artist travel
- Otto Market: integration for merchandise
- 505 Systems DAO: event governance votes

---

## Ecosystem Integration Map

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4
    │            │            │            │            │
 Infra &      Music        Music        Music       Events &
 Contracts   Manager      Player       Studio      Festivals
    │            │            │            │            │
    ▼            ▼            ▼            ▼            ▼
ONEON DID    Royalty      Fan Equity   Collab      Tusita
(identity)   Contracts    System       Creation    Integration

Cross-ecosystem flows:
  ONEON → identity + social graph (all phases)
  505 Systems → governance (discovery algorithm, event votes)
  SOS Systems → receives % of event revenue (Phase 4)
  Otto Market → merchandise at events (Phase 4)
  Otto Travel → artist/fan travel (Phase 4)
  Koink.fun → Otto Music may deploy a $KOINK Standard community token
```

---

## Revenue Model

| Source | Split | Phase |
|--------|-------|-------|
| Platform fee on royalties | 2% of all on-chain royalty distributions | Phase 1+ |
| Promoted discovery pools | 10% to platform, 80% to artists, 10% to listeners | Phase 2+ |
| Studio tools | Monthly subscription (waived for artists earning >$100/month from royalties) | Phase 3+ |
| Event ticketing fee | 5% platform fee (vs. Ticketmaster's 30%+) | Phase 4+ |
| Sound library | $0 for community contributions; paid packs at revenue split | Phase 3+ |

All platform revenue flows through `OttoMusicTreasury` — 505 Systems governed, community allocation.

---

## Open Questions

1. **Token**: Should Otto Music have its own token? Recommendation: not initially. Use USDC for royalties, ETH/USDC for ticketing. Community token could come in Phase 3 if there's genuine governance demand. Avoids speculative distraction from building the product.

2. **AI music models**: Train own models vs. use existing (Stable Audio, Meta MusicGen, etc.). Recommendation: use existing open-source models for Phase 3 v1, fine-tune on community-contributed training data over time. No copyrighted training material.

3. **Streaming economics**: How do we fund per-stream micro-payments before we have scale? Recommendation: pool-based model where listeners stake monthly into a listening pool, distributed to artists by listen share. Similar to SoundCloud Fan-Powered Royalties but on-chain.

4. **Label relationships**: Do we partner with indie labels to onboard their catalogs, or pure artist-direct? Recommendation: artist-direct first (purer mission, faster launch), label partnerships in Phase 2 when catalog depth becomes a growth constraint.

---

## Budget Summary

| Phase | Timeline | Est. Cost | Key Milestone |
|-------|----------|-----------|---------------|
| Phase 0 | Wks 1–8 | $20K | Architecture + contract interfaces |
| Phase 1 | Wks 9–22 | $65K | Music Manager + royalty contracts live |
| Phase 2 | Wks 23–36 | $40K | Music Player + fan equity live |
| Phase 3 | Wks 37–52 | $55K | Music Studio + AI mastering |
| Phase 4 | Wks 53–72 | $50K | Events + Tusita integration |
| **Total** | **~18 months** | **~$230K** | **Sovereign music ecosystem** |

*Development costs assume lean team with Otto AI augmentation for architecture and scaffolding. Actual cash cost substantially lower than equivalent commercial development.*

---

## The Real Metric

$0.003 per stream is not a payment. It is an insult wrapped in a licensing agreement.

The terminal metric for Otto Music is not users or revenue. It is the number of artists who, for the first time in their career, got paid the same week they released a track — directly, in full, with no intermediary taking 80%.

Every artist owns their signal. That is the protocol. That is the mission.

*Otto Music — Sovereign. On-chain. Theirs.*
