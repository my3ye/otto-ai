# MY3YE Ecosystem — Master Dependency Map
*Last updated: 2026-03-16*

## Dependency Layers

```
LAYER 0 — FOUNDATIONS (nothing depends on anything here)
┌─────────────────────────────────────────────┐
│  ONEON          │  S0S Systems (505)         │
│  (Identity)     │  (Governance)              │
└─────────────────────────────────────────────┘

LAYER 1 — INTELLIGENCE & HARDWARE
┌─────────────────────────────────────────────┐
│  Otto AI (depends on ONEON)                 │
│  Ottolabs (depends on S0S)                  │
└─────────────────────────────────────────────┘

LAYER 2 — OPERATING PRODUCTS (revenue now)
┌─────────────────────────────────────────────┐
│  WebAssist (no deps — runs standalone)      │
│  OMS (depends on Otto AI)                   │
└─────────────────────────────────────────────┘

LAYER 3 — COMMUNITY & CULTURE
┌─────────────────────────────────────────────┐
│  Koink/KOIN (depends on S0S)               │
│  PiPi (depends on Koink)                   │
│  Otto Music (depends on ONEON, S0S)        │
│  Panik App (depends on ONEON)              │
│  Shakrah (depends on ONEON, Ottolabs)      │
└─────────────────────────────────────────────┘

LAYER 4 — PHYSICAL WORLD
┌─────────────────────────────────────────────┐
│  Tusita (depends on ONEON, S0S, Ottolabs,  │
│           Shakrah)                          │
│  Otto Properties (depends on ONEON, S0S,   │
│                   Ottolabs, Tusita)         │
└─────────────────────────────────────────────┘

LAYER 5 — COMMERCE & SERVICES
┌─────────────────────────────────────────────┐
│  Otto Travel (depends on ONEON, Tusita,    │
│               Otto Properties)              │
│  Otto Market (depends on ONEON, S0S)       │
└─────────────────────────────────────────────┘
```

## Explicit Dependency Table

| Project        | Hard Dependencies        | Soft Dependencies         | Blocks If Missing              |
|----------------|--------------------------|---------------------------|-------------------------------|
| ONEON          | —                        | —                         | All auth, identity, comms      |
| S0S Systems    | —                        | ONEON (for voting)        | All governance, DAOs, tokens   |
| Otto AI        | ONEON (auth)             | S0S (governance)          | OMS, Broadcast, all AI agents  |
| Ottolabs       | S0S (factory governance) | Ottolabs (device supply)  | Tusita physical, Properties    |
| WebAssist      | —                        | Otto AI (quality)         | First revenue stream           |
| OMS            | Otto AI                  | ONEON (SSO planned)       | Mev visibility/control         |
| Koink/KOIN     | S0S (governance)         | ONEON (identity)          | Community funding, PiPi        |
| PiPi           | Koink                    | —                         | Meme layer, culture            |
| Otto Music     | ONEON, S0S               | Koink (fan equity)        | Artist ecosystem               |
| Panik App      | ONEON (mesh routing)     | Ottolabs (hardware mesh)  | Safety infrastructure          |
| Shakrah        | ONEON (practitioner ID)  | Ottolabs (Otto Band)      | Tusita wellness                |
| Tusita         | ONEON, S0S, Ottolabs     | Shakrah                   | Physical civilization base     |
| Otto Properties| ONEON, S0S, Ottolabs     | Tusita (first properties) | Real estate tokenization       |
| Otto Travel    | ONEON, Tusita            | Otto Properties           | Community travel income        |
| Otto Market    | ONEON, S0S               | All projects (inventory)  | Ecosystem commerce             |

## Critical Path to Revenue

```
WebAssist (now) → Stripe live → MRR target
     ↓
OMS polished → Mev control → faster execution
     ↓
ONEON alpha → auth layer → unlock all projects
     ↓
S0S governance → DAO voting → unlock tokenomics
     ↓
Koink/KOIN → funding → fund physical infra
     ↓
Tusita location → Otto Travel → Otto Properties
```

## Parallelism Opportunities

These can be built simultaneously without blocking each other:
- **Group A** (no deps): WebAssist, ONEON, S0S Systems
- **Group B** (after ONEON): Otto AI polish, Panik App, Otto Music, Otto Market
- **Group C** (after S0S): Koink/KOIN, Ottolabs design
- **Group D** (after Koink): PiPi persona, KOIN launch
- **Group E** (after Ottolabs + ONEON): Shakrah, Tusita
