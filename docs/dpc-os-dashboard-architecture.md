# DPC OS Dashboard — System Architecture

## Design: DPC Operating System Dashboard

### Problem

505 Systems needs an interactive demonstration of how DPC (Dynamic Proximity Calculus) governance actually works — not a whitepaper, not a landing page, but a **living simulation** that visitors can click through. Each "Build" action triggers a visible cascade: contribution recorded, DPC score recalculated, governance weights shift, automation fires, rewards distributed. The goal is to make the invisible machinery of contribution-weighted governance tangible in under 60 seconds.

### Approach

A single-page Next.js application with 7 interconnected panels arranged in an OS-style dashboard. The entire state is client-side (no backend needed). A simulation engine processes events synchronously so users see cause-and-effect in real time. The aesthetic is a dark terminal OS — think Bloomberg Terminal meets Tron — with glowing accent colors that pulse when state changes propagate.

---

## 1. Panel Definitions

### Panel 1: Contribution Feed (Left Column, Top)
**Purpose:** Real-time stream of contributions entering the system.

| Field | Description |
|-------|-------------|
| Timestamp | Simulated time (advances with each Build) |
| Member | Avatar + handle of contributor |
| Type | One of 7: PHY, MAT, SKL, OPS, EDU, COM, DIG |
| Description | Auto-generated action label (e.g., "Deployed auth module", "Mentored 3 new members") |
| Is / Ec / Rw | Raw component scores for this contribution |
| Status | `VERIFIED` badge (appears after 200ms animation) |

**Behavior:** New entries appear at top with a glow-in animation. Feed holds last 20 entries, older ones fade out. Each entry shows a small colored dot matching the contribution type.

**shadcn/ui:** `ScrollArea`, `Badge`, `Avatar`

---

### Panel 2: DPC Score Engine (Center, Top)
**Purpose:** The core scoring visualization. Shows how P = f(Is, Ec, Rw) is computed in real time.

**Sub-components:**
- **Formula Display:** `P = f(Is, Ec, Rw)` rendered large, with each variable highlighting when it changes
- **Component Bars:** Three horizontal animated bars for Is, Ec, Rw of the currently-selected member
- **Score Output:** Large numeric DPC score with delta indicator (+/- from previous)
- **Decay Timer:** Visual countdown showing time-based decay rate (180d active / 60d inactive half-life)
- **Peak Score:** Small indicator showing all-time peak vs current (floor = 10% of peak)

**Behavior:** When a new contribution lands, the relevant component bar animates upward, the formula pulses, and the score output ticks to its new value with an odometer-style animation.

**shadcn/ui:** `Card`, `Progress`, `Badge`, `Tooltip`

---

### Panel 3: Governance Weight Board (Center, Middle)
**Purpose:** Shows how DPC scores translate to governance power via `sqrt(DPC) x activityMultiplier`.

**Sub-components:**
- **Weight Table:** All members ranked by governance weight, with columns: Rank, Member, DPC Score, sqrt(DPC), Activity Multiplier, Final Weight, % of Total
- **Whale Cap Indicator:** Visual bar showing the 5% cap threshold — if any member approaches it, the bar turns amber
- **Council Seats:** 5 domain icons (Protocol, Treasury, Community, Operations, Education) with seated member avatars
- **Power Distribution Chart:** Horizontal stacked bar showing weight distribution across all members

**Behavior:** After DPC recalculation, weights animate to new positions. Rank changes trigger a subtle slide animation. If a member crosses a DPC threshold for council eligibility, their row briefly glows.

**shadcn/ui:** `Table`, `Progress`, `Badge`, `Avatar`, `Tooltip`

---

### Panel 4: Automation Layer (Right Column, Top)
**Purpose:** Shows automation rules that fire based on system state changes.

**Rule Types:**
| Rule | Trigger | Action |
|------|---------|--------|
| `SCORE_THRESHOLD` | Member DPC crosses 500/1000/2000 | Unlock council eligibility |
| `DECAY_WARNING` | Member inactive > 60 days | Send notification |
| `WHALE_CAP` | Member weight > 4.5% of total | Flag for review |
| `QUORUM_CHECK` | Active weight > 15% threshold | Enable election |
| `REWARD_TRIGGER` | Contribution verified | Queue reward distribution |
| `ROTATION_DUE` | Council term expires (90d sim) | Trigger election cycle |

**Display:** Each rule is a row with: Rule Name, Condition (code-style), Status LED (green=armed, amber=firing, grey=dormant), Last Fired timestamp.

**Behavior:** When a rule fires, its row flashes with a pulse animation and the Status LED turns amber for 1 second. A small `>_` terminal cursor blinks next to active rules.

**shadcn/ui:** `Card`, `Badge`, `Switch` (to toggle rules on/off)

---

### Panel 5: Rewards Distribution (Right Column, Bottom)
**Purpose:** Shows how value flows back to contributors proportional to their governance weight.

**Sub-components:**
- **Reward Pool:** Large number showing total pool size (grows with each contribution cycle)
- **Distribution Table:** Member | Weight % | Reward Amount | Cumulative Total
- **Split Visualization:** Animated flow lines from pool to members (thickness proportional to weight)
- **Agent Tax:** Fixed 40% line item showing platform sustainability cut (per Core Value Loop spec)

**Behavior:** After automation fires `REWARD_TRIGGER`, the pool visually splits into member allocations with a cascading animation (top to bottom by weight). The 40% agent tax is always the first split, rendered in a distinct color.

**shadcn/ui:** `Card`, `Table`, `Badge`, `Separator`

---

### Panel 6: Member Registry (Left Column, Bottom)
**Purpose:** The identity layer — all participants in the simulation.

**Per Member:**
- Avatar (procedurally generated, color-coded by primary contribution type)
- Handle (e.g., `@nova`, `@reef`, `@arc`)
- DPC Score (live-updating)
- Contribution Types bitmap (colored dots for each active type)
- Activity Status: Active / Warning / Inactive
- Council Seat (if any)
- Join Date (simulated)

**Display:** Grid of member cards (4-6 members in simulation). Clicking a member selects them and the DPC Score Engine panel focuses on their breakdown.

**Behavior:** New members can be added via the simulation. Activity status changes color based on simulated time since last contribution.

**shadcn/ui:** `Card`, `Avatar`, `Badge`, `Button`

---

### Panel 7: Treasury (Bottom Bar, Full Width)
**Purpose:** Aggregate financial state of the simulation.

**Metrics (displayed as stat cards in a horizontal row):**
| Metric | Description |
|--------|-------------|
| Total Pool | Cumulative rewards available |
| Distributed | Total rewards sent to members |
| Agent Tax Collected | 40% sustainability fund |
| Active Contributors | Count of members with activity < 90d |
| Total Governance Weight | Sum of all sqrt(DPC) weights |
| Simulation Cycle | Current tick count |

**Behavior:** Numbers tick up with odometer animation when state changes. Each card has a small sparkline showing the metric's history over the last 20 cycles.

**shadcn/ui:** `Card`, `Badge`

---

## 2. State Schema

```typescript
// ─── Root State ───────────────────────────────────────────
interface DPCOSState {
  simulation: SimulationState;
  members: Record<string, Member>;
  contributions: Contribution[];
  scores: Record<string, DPCScore>;
  governance: GovernanceState;
  automation: AutomationState;
  rewards: RewardsState;
  treasury: TreasuryState;
  ui: UIState;
}

// ─── Simulation Control ──────────────────────────────────
interface SimulationState {
  cycle: number;                    // Current tick (increments per Build)
  simulatedTime: number;            // Unix timestamp in sim-world
  timeScale: number;                // Days per cycle (default: 7)
  isRunning: boolean;               // Auto-run mode
  speed: 'slow' | 'normal' | 'fast'; // Animation speed
  eventLog: SimEvent[];             // Ordered cascade log for current cycle
}

interface SimEvent {
  id: string;
  cycle: number;
  phase: 'contribute' | 'score' | 'govern' | 'automate' | 'reward';
  description: string;
  timestamp: number;
  data: Record<string, unknown>;
}

// ─── Members ─────────────────────────────────────────────
interface Member {
  id: string;
  handle: string;                   // @nova, @reef, etc.
  avatar: {
    seed: string;                   // For procedural generation
    primaryColor: string;           // Based on dominant contribution type
  };
  joinedAt: number;                 // Sim timestamp
  lastActiveAt: number;             // Sim timestamp of last contribution
  contributionTypeBitmap: number;   // 7-bit bitmap (PHY|MAT|SKL|OPS|EDU|COM|DIG)
  totalContributions: number;
  status: 'active' | 'warning' | 'inactive' | 'dormant';
  councilSeat: CouncilDomain | null;
}

// ─── Contributions ───────────────────────────────────────
type ContributionType = 'PHY' | 'MAT' | 'SKL' | 'OPS' | 'EDU' | 'COM' | 'DIG';

interface Contribution {
  id: string;
  memberId: string;
  type: ContributionType;
  description: string;
  cycle: number;
  timestamp: number;                // Sim time
  components: {
    is: number;                     // Structural Impact score (0-100)
    ec: number;                     // Consistent Energy score (0-100)
    rw: number;                     // Weighted Resonance score (0-100)
  };
  verified: boolean;
  rewardAmount: number;             // Set after reward distribution
}

// DPC component weights per contribution type (from smart contracts)
const CONTRIBUTION_WEIGHTS: Record<ContributionType, { is: number; ec: number; rw: number }> = {
  PHY: { is: 0.7, ec: 0.2, rw: 0.1 },
  MAT: { is: 0.8, ec: 0.1, rw: 0.1 },
  SKL: { is: 0.5, ec: 0.2, rw: 0.3 },
  OPS: { is: 0.2, ec: 0.6, rw: 0.2 },
  EDU: { is: 0.3, ec: 0.3, rw: 0.4 },
  COM: { is: 0.1, ec: 0.3, rw: 0.6 },
  DIG: { is: 0.6, ec: 0.2, rw: 0.2 },
};

// ─── DPC Scores ──────────────────────────────────────────
interface DPCScore {
  memberId: string;
  rawScore: number;                 // Current DPC (after decay)
  peakScore: number;                // All-time high
  lastUpdateCycle: number;
  lastActiveCycle: number;
  components: {
    is: number;                     // Accumulated Structural Impact
    ec: number;                     // Accumulated Consistent Energy
    rw: number;                     // Accumulated Weighted Resonance
  };
  decayRate: 'active' | 'inactive'; // 180d vs 60d half-life
  floorScore: number;               // peakScore * 0.10
  history: { cycle: number; score: number }[]; // Last 50 data points
}

// ─── Governance ──────────────────────────────────────────
type CouncilDomain = 'protocol' | 'treasury' | 'community' | 'operations' | 'education';

interface GovernanceState {
  weights: Record<string, GovernanceWeight>;
  councils: Record<CouncilDomain, CouncilState>;
  totalActiveWeight: number;
  whaleCapBps: number;              // 500 = 5%
  quorumThresholdBps: number;       // 1500 = 15%
  electionActive: boolean;
}

interface GovernanceWeight {
  memberId: string;
  dpcScore: number;
  sqrtDPC: number;
  activityMultiplier: number;       // 1.0, 0.5, 0.1, or 0.0
  finalWeight: number;              // sqrtDPC * activityMultiplier
  percentOfTotal: number;           // 0-100
  cappedWeight: number;             // After whale cap applied
  rank: number;
}

interface CouncilState {
  domain: CouncilDomain;
  seats: number;                    // Max seats (7)
  members: string[];                // Member IDs currently seated
  dpcThreshold: number;             // Min DPC to be eligible
  termStartCycle: number;
  termDurationCycles: number;       // 90 days / timeScale
  nextRotationCycle: number;
}

// DPC thresholds per domain (from ElectionEngine.sol)
const COUNCIL_DPC_THRESHOLDS: Record<CouncilDomain, number> = {
  protocol: 2000,
  treasury: 2000,
  community: 1000,
  operations: 1500,
  education: 500,
};

// ─── Automation ──────────────────────────────────────────
type AutomationRuleType =
  | 'SCORE_THRESHOLD'
  | 'DECAY_WARNING'
  | 'WHALE_CAP'
  | 'QUORUM_CHECK'
  | 'REWARD_TRIGGER'
  | 'ROTATION_DUE';

interface AutomationRule {
  id: string;
  type: AutomationRuleType;
  name: string;
  condition: string;                // Human-readable condition code
  enabled: boolean;
  status: 'armed' | 'firing' | 'dormant';
  lastFiredCycle: number | null;
  fireCount: number;
  action: string;                   // What happens when it fires
}

interface AutomationState {
  rules: AutomationRule[];
  firedThisCycle: string[];         // Rule IDs that fired this cycle
  log: { cycle: number; ruleId: string; result: string }[];
}

// ─── Rewards ─────────────────────────────────────────────
interface RewardsState {
  currentPool: number;              // Available for distribution
  distributions: Distribution[];
  agentTaxRate: number;             // 0.40 (40%)
  lastDistributionCycle: number;
}

interface Distribution {
  cycle: number;
  poolSize: number;
  agentTaxAmount: number;
  memberAllocations: {
    memberId: string;
    weightPercent: number;
    amount: number;
  }[];
}

// ─── Treasury ────────────────────────────────────────────
interface TreasuryState {
  totalPool: number;                // Cumulative rewards generated
  totalDistributed: number;         // Cumulative sent to members
  agentTaxCollected: number;        // Cumulative 40% tax
  activeContributors: number;
  totalGovernanceWeight: number;
  history: {
    cycle: number;
    pool: number;
    distributed: number;
    activeCount: number;
  }[];
}

// ─── UI State ────────────────────────────────────────────
interface UIState {
  selectedMemberId: string | null;
  activePanelPhase: SimEvent['phase'] | null; // Which panel is "lit up"
  cascadeStep: number;              // 0-4 during cascade animation
  showEventLog: boolean;
  theme: 'cyan' | 'green' | 'amber'; // Accent color variant
}
```

---

## 3. Click-Driven Simulation Loop

### The Build Button

A prominent `[ BUILD ]` button sits in the top-center toolbar. Each press executes a **5-phase cascade** that propagates through all panels in sequence, with visible delays between phases so the user can follow the data flow.

### Cascade Sequence

```
[BUILD pressed]
    |
    v
Phase 1: CONTRIBUTE (200ms)
    |- Select random member (or user-selected)
    |- Generate contribution (random type + components)
    |- Add to contribution feed with glow animation
    |- Update member's lastActiveAt and bitmap
    |- Contribution Feed panel border pulses
    |
    v
Phase 2: SCORE (400ms delay)
    |- Recalculate DPC for contributing member:
    |   newIs = oldIs + (contribution.is * WEIGHTS[type].is)
    |   newEc = oldEc + (contribution.ec * WEIGHTS[type].ec)
    |   newRw = oldRw + (contribution.rw * WEIGHTS[type].rw)
    |   rawScore = newIs + newEc + newRw
    |- Apply decay to ALL members (based on sim time elapsed):
    |   decayed = rawScore * 2^(-(elapsed / halfLife))
    |   halfLife = isActive ? 180 : 60 (in sim-days)
    |   floor = peakScore * 0.10
    |   finalScore = max(decayed, floor)
    |- Update peak score if new > peak
    |- Formula display animates component changes
    |- DPC Score Engine panel border pulses
    |
    v
Phase 3: GOVERN (400ms delay)
    |- Recalculate governance weights for ALL members:
    |   sqrtDPC = Math.sqrt(dpcScore)
    |   multiplier = getActivityMultiplier(lastActive, simTime)
    |     <=30d: 1.0 | <=60d: 0.5 | <=90d: 0.1 | >90d: 0.0
    |   weight = sqrtDPC * multiplier
    |- Apply whale cap (5% of total)
    |- Re-rank all members
    |- Check council eligibility changes
    |- Governance Weight Board panel border pulses
    |
    v
Phase 4: AUTOMATE (300ms delay)
    |- Evaluate ALL enabled rules against new state:
    |   SCORE_THRESHOLD: Check if any member crossed 500/1000/2000
    |   DECAY_WARNING: Check if any member inactive > 60 sim-days
    |   WHALE_CAP: Check if any weight > 4.5% of total
    |   QUORUM_CHECK: Check if totalActiveWeight > 15% threshold
    |   REWARD_TRIGGER: Always fires on new contribution
    |   ROTATION_DUE: Check if any council term expired
    |- Fire matching rules (status → 'firing')
    |- Automation panel rows flash for fired rules
    |
    v
Phase 5: REWARD (300ms delay)
    |- Add base reward (100 units) to pool
    |- Calculate agent tax: pool * 0.40
    |- Distribute remaining 60% by governance weight:
    |   for each active member:
    |     allocation = remainingPool * (memberWeight / totalWeight)
    |- Animate flow lines from pool to members
    |- Update treasury metrics
    |- Rewards + Treasury panels pulse
    |
    v
[CASCADE COMPLETE — all panels settle]
```

### Timing & Animation

| Phase | Delay Before | Animation Duration | Total |
|-------|-------------|-------------------|-------|
| CONTRIBUTE | 0ms | 200ms | 200ms |
| SCORE | 200ms | 400ms | 600ms |
| GOVERN | 200ms | 400ms | 600ms |
| AUTOMATE | 200ms | 300ms | 500ms |
| REWARD | 200ms | 300ms | 500ms |
| **Total cascade** | | | **~2.4s** |

During cascade, each active panel gets a glowing border in the accent color. Inactive panels dim slightly. This creates a visible "wave" of computation flowing through the OS.

### Auto-Run Mode

A toggle next to the Build button enables auto-run at configurable intervals (1s / 3s / 5s). In auto-run, the simulation picks random members and contribution types, demonstrating how the system evolves over many cycles. Users can still click Build manually to add specific contributions.

### Member Selection

Clicking a member in the Registry panel selects them. The next Build press generates a contribution for that member specifically (instead of random). The DPC Score Engine panel focuses on the selected member's breakdown.

---

## 4. Component Tree & Data Flow

### Component Hierarchy

```
<DPCOSApp>                                    // Root — holds useReducer state
  <ThemeProvider>                              // Dark theme + accent color
    <OSChrome>                                 // Window chrome, title bar, toolbar
      <Toolbar>                                // Top bar
        <BuildButton />                        // The main action button
        <AutoRunToggle />                      // Auto-simulation toggle
        <SpeedSelector />                      // slow/normal/fast
        <CycleCounter />                       // Current cycle display
        <SimClock />                           // Simulated date/time
        <ThemeSwitch />                        // cyan/green/amber accent
      </Toolbar>

      <PanelGrid>                              // CSS Grid layout (3 columns)

        {/* Left Column */}
        <Panel id="contributions" phase="contribute">
          <ContributionFeed>
            <ContributionEntry />              // Repeating, max 20
          </ContributionFeed>
        </Panel>

        <Panel id="registry" phase={null}>
          <MemberRegistry>
            <MemberCard />                     // 4-6 members, clickable
          </MemberRegistry>
        </Panel>

        {/* Center Column */}
        <Panel id="score-engine" phase="score">
          <DPCScoreEngine>
            <FormulaDisplay />                 // P = f(Is, Ec, Rw) animated
            <ComponentBars />                  // Is, Ec, Rw progress bars
            <ScoreOutput />                    // Big number with delta
            <DecayIndicator />                 // Half-life countdown
          </DPCScoreEngine>
        </Panel>

        <Panel id="governance" phase="govern">
          <GovernanceWeightBoard>
            <WeightTable />                    // Ranked member weights
            <WhaleCapBar />                    // 5% cap visualization
            <CouncilSeats />                   // 5 domain seat displays
            <PowerDistribution />              // Stacked bar chart
          </GovernanceWeightBoard>
        </Panel>

        {/* Right Column */}
        <Panel id="automation" phase="automate">
          <AutomationLayer>
            <AutomationRule />                 // 6 rules with status LEDs
          </AutomationLayer>
        </Panel>

        <Panel id="rewards" phase="reward">
          <RewardsDistribution>
            <RewardPool />                     // Pool amount
            <AgentTaxLine />                   // 40% cut
            <DistributionTable />              // Per-member allocations
            <FlowVisualization />              // Animated flow lines
          </RewardsDistribution>
        </Panel>

        {/* Bottom Row — Full Width */}
        <Panel id="treasury" phase="reward">
          <Treasury>
            <StatCard metric="totalPool" />
            <StatCard metric="distributed" />
            <StatCard metric="agentTax" />
            <StatCard metric="activeContributors" />
            <StatCard metric="totalWeight" />
            <StatCard metric="cycle" />
          </Treasury>
        </Panel>

      </PanelGrid>

      <EventLog />                             // Collapsible bottom drawer
    </OSChrome>
  </ThemeProvider>
</DPCOSApp>
```

### Data Flow Architecture

```
                    ┌──────────────┐
                    │  BuildButton │
                    └──────┬───────┘
                           │ dispatch({ type: 'BUILD' })
                           v
                    ┌──────────────┐
                    │   Reducer    │  ← Pure function, all logic here
                    │  (5 phases)  │
                    └──────┬───────┘
                           │ new state
                           v
              ┌────────────────────────────┐
              │     DPCOSContext.Provider   │
              └────────────┬───────────────┘
                           │
          ┌────────┬───────┼───────┬────────┬────────┐
          v        v       v       v        v        v
    [Feed]   [Score]  [Govern]  [Auto]  [Reward] [Treasury]
```

**State management:** `useReducer` + React Context. No external state library needed — the state is ~50KB max and updates synchronously.

**Why useReducer over useState:** The 5-phase cascade is a single atomic state transition. The reducer processes all phases and returns the complete new state. Animation timing is handled by the `<Panel>` component reading `ui.cascadeStep` and applying CSS transitions with staggered delays.

**Action Types:**

```typescript
type DPCAction =
  | { type: 'BUILD'; memberId?: string }           // Main action
  | { type: 'SET_CASCADE_STEP'; step: number }     // Animation sequencing
  | { type: 'SELECT_MEMBER'; memberId: string }    // Click member
  | { type: 'TOGGLE_AUTO_RUN' }                    // Auto mode
  | { type: 'SET_SPEED'; speed: 'slow' | 'normal' | 'fast' }
  | { type: 'TOGGLE_RULE'; ruleId: string }        // Enable/disable rule
  | { type: 'ADD_MEMBER'; handle: string }          // Add to simulation
  | { type: 'SET_THEME'; theme: 'cyan' | 'green' | 'amber' }
  | { type: 'RESET' };                              // Reset simulation
```

### Panel Component

Every panel shares a common wrapper that handles the cascade glow:

```typescript
interface PanelProps {
  id: string;
  title: string;
  phase: SimEvent['phase'] | null;  // Which cascade phase lights this up
  children: React.ReactNode;
}

// Panel glows when ui.activePanelPhase matches its phase prop
// Border color transitions from dim → accent → dim over 600ms
```

---

## 5. Key Design Decisions

- **Client-side only (no backend)**: because this is a demonstration/simulation, not a production governance system. All state lives in useReducer. Alternative: API-backed with real DPC scores from the Memory API — rejected because it adds deployment complexity and the goal is a self-contained demo.

- **useReducer over Zustand/Redux**: because the state transitions are simple (one action → deterministic new state) and the component tree is shallow (max 3 levels). Alternative: Zustand — would work fine but adds a dependency for no benefit at this scale.

- **Synchronous cascade with CSS animation delays**: because the reducer computes all 5 phases atomically and returns the final state, while CSS `transition-delay` creates the visual cascade. Alternative: async state updates with setTimeout between phases — rejected because it creates race conditions and makes the state non-deterministic.

- **shadcn/ui components throughout**: because the 505 management dashboard (web-next) already uses shadcn/ui with a Tron-inspired dark theme. Reuse the same component library. Alternative: fully custom components — rejected because it doubles the work for no user benefit.

- **Fixed 4-6 member simulation**: because it's enough to demonstrate DPC dynamics (score divergence, whale cap activation, council rotation) without overwhelming the UI. Alternative: user-configurable member count — can be added later as an extension.

- **7 real contribution types from the smart contracts**: because it grounds the simulation in the actual system being built. Not toy categories.

---

## 6. Color & Theme Guidance

### Base: Dark OS Terminal Aesthetic

```css
/* ─── Foundation ─── */
--bg-deep:        #050a12;          /* Deepest background */
--bg-panel:       #0a1628;          /* Panel background */
--bg-panel-hover: #0f1f38;          /* Panel hover/active */
--bg-surface:     #132743;          /* Elevated surface (cards within panels) */
--border-dim:     #1a2d4a;          /* Default borders */
--border-active:  var(--accent);     /* Active panel borders */
--text-primary:   #e2e8f0;          /* Primary text */
--text-secondary: #64748b;          /* Secondary/label text */
--text-muted:     #334155;          /* Dormant/disabled text */

/* ─── Accent Palette (Cyan default, switchable) ─── */

/* Cyan (default — matches Tron theme) */
--accent:         #06b6d4;          /* Primary accent */
--accent-dim:     #0e7490;          /* Subdued accent */
--accent-glow:    rgba(6,182,212,0.4);  /* Glow shadow color */
--accent-pulse:   rgba(6,182,212,0.15); /* Subtle pulse background */

/* Green (alternative — matrix vibe) */
--accent-green:       #22c55e;
--accent-green-dim:   #16a34a;
--accent-green-glow:  rgba(34,197,94,0.4);

/* Amber (alternative — warning/warm) */
--accent-amber:       #f59e0b;
--accent-amber-dim:   #d97706;
--accent-amber-glow:  rgba(245,158,11,0.4);

/* ─── Semantic Colors ─── */
--success:        #22c55e;          /* Verified, positive delta */
--warning:        #f59e0b;          /* Decay warning, approaching cap */
--danger:         #ef4444;          /* Inactive, cap exceeded */
--info:           #3b82f6;          /* Informational badges */

/* ─── Contribution Type Colors ─── */
--type-phy:       #f97316;          /* Physical Labor — orange */
--type-mat:       #a855f7;          /* Materials — purple */
--type-skl:       #06b6d4;          /* Skilled Trade — cyan */
--type-ops:       #3b82f6;          /* Operations — blue */
--type-edu:       #22c55e;          /* Education — green */
--type-com:       #ec4899;          /* Community — pink */
--type-dig:       #f59e0b;          /* Digital — amber */

/* ─── DPC Component Colors (for formula/bars) ─── */
--is-color:       #a855f7;          /* Structural Impact — purple */
--ec-color:       #06b6d4;          /* Consistent Energy — cyan */
--rw-color:       #ec4899;          /* Weighted Resonance — pink */
```

### Glow Effects

```css
/* Panel active glow */
.panel-active {
  box-shadow:
    0 0 1px var(--accent),
    0 0 8px var(--accent-glow),
    inset 0 0 8px var(--accent-pulse);
  border-color: var(--accent);
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
}

/* Score change pulse */
@keyframes score-pulse {
  0%   { text-shadow: 0 0 4px var(--accent-glow); }
  50%  { text-shadow: 0 0 20px var(--accent), 0 0 40px var(--accent-glow); }
  100% { text-shadow: 0 0 4px var(--accent-glow); }
}

/* Status LED */
.led-armed   { background: var(--success); box-shadow: 0 0 6px var(--success); }
.led-firing  { background: var(--warning); box-shadow: 0 0 12px var(--warning); animation: led-blink 0.3s 3; }
.led-dormant { background: var(--text-muted); }

/* Cascade wave — panels light up in sequence */
.panel[data-phase="contribute"] { transition-delay: 0ms; }
.panel[data-phase="score"]      { transition-delay: 400ms; }
.panel[data-phase="govern"]     { transition-delay: 800ms; }
.panel[data-phase="automate"]   { transition-delay: 1200ms; }
.panel[data-phase="reward"]     { transition-delay: 1600ms; }
```

### Typography

```css
/* Display — panel titles, score numbers */
font-family: 'Geist Mono', 'JetBrains Mono', monospace;

/* Body — descriptions, table content */
font-family: 'Inter', 'Geist Sans', sans-serif;

/* Code — conditions, formulas, addresses */
font-family: 'Geist Mono', monospace;
font-size: 0.8rem;
color: var(--text-secondary);
```

### Panel Chrome

Each panel has:
- **Title bar:** Left-aligned label in monospace, dim accent color, uppercase, 0.7rem
- **Corner brackets:** `[ ]` style decorators at top-left and bottom-right (Tron aesthetic)
- **Scan lines:** Subtle repeating 1px horizontal lines at 2% opacity over panel background
- **Border:** 1px solid `--border-dim`, transitions to `--accent` when active

---

## 7. Layout Grid

```
┌─────────────────────────────────────────────────────────────┐
│  [ DPC OS ]    [ BUILD ]  [Auto ▶]  [Speed: ●●○]  Cycle: 47│  ← Toolbar
├──────────────┬──────────────────────┬───────────────────────┤
│              │                      │                       │
│  CONTRIBUTION│    DPC SCORE ENGINE  │    AUTOMATION LAYER   │
│  FEED        │                      │                       │
│              │    P = f(Is,Ec,Rw)   │    ● SCORE_THRESHOLD  │
│  @nova PHY   │    ████████░░ Is     │    ● DECAY_WARNING    │
│  @reef SKL   │    ██████░░░░ Ec     │    ● WHALE_CAP        │
│  @arc  EDU   │    █████░░░░░ Rw     │    ● QUORUM_CHECK     │
│              │                      │    ● REWARD_TRIGGER    │
│              │    Score: 2,847 +123  │    ● ROTATION_DUE     │
│              │                      │                       │
├──────────────┼──────────────────────┼───────────────────────┤
│              │                      │                       │
│  MEMBER      │  GOVERNANCE WEIGHT   │  REWARDS DISTRIBUTION │
│  REGISTRY    │  BOARD               │                       │
│              │                      │  Pool: 12,400         │
│  [@nova]     │  #1 @nova  34.2%     │  Agent Tax: 4,960     │
│  DPC: 2847   │  #2 @reef  28.1%     │                       │
│  ●●●○○○○    │  #3 @arc   18.5%     │  @nova: 3,456         │
│              │  #4 @sol   12.8%     │  @reef: 2,840         │
│  [@reef]     │  #5 @zen    6.4%     │  @arc:  1,850         │
│  DPC: 1923   │                      │                       │
│  ●○●○○○○    │  ████████████████    │                       │
│              │  [P][T][C][O][E]     │                       │
├──────────────┴──────────────────────┴───────────────────────┤
│  TREASURY                                                    │
│  Pool: 47,200 │ Dist: 28,320 │ Tax: 18,880 │ Active: 5 │ C:47│
└─────────────────────────────────────────────────────────────┘
```

**CSS Grid:**
```css
.panel-grid {
  display: grid;
  grid-template-columns: 280px 1fr 300px;
  grid-template-rows: 1fr 1fr auto;
  gap: 2px;                          /* Minimal gap — panels nearly touch */
  height: calc(100vh - 48px);        /* Full viewport minus toolbar */
}

/* Panel positions */
.panel-contributions { grid-area: 1 / 1 / 2 / 2; }
.panel-registry      { grid-area: 2 / 1 / 3 / 2; }
.panel-score-engine  { grid-area: 1 / 2 / 2 / 3; }
.panel-governance    { grid-area: 2 / 2 / 3 / 3; }
.panel-automation    { grid-area: 1 / 3 / 2 / 4; }
.panel-rewards       { grid-area: 2 / 3 / 3 / 4; }
.panel-treasury      { grid-area: 3 / 1 / 4 / 4; }
```

---

## 8. Seed Data

The simulation starts with 5 pre-loaded members:

| Handle | Primary Type | Starting DPC | Council Seat | Personality |
|--------|-------------|-------------|-------------|-------------|
| `@nova` | DIG (Digital) | 2,400 | Protocol | Prolific coder, high Is |
| `@reef` | SKL (Skilled Trade) | 1,800 | None | Steady contributor, high Ec |
| `@arc` | EDU (Education) | 1,200 | Education | Mentor, high Rw |
| `@sol` | OPS (Operations) | 600 | None | New but consistent |
| `@zen` | COM (Community) | 300 | None | Just joined, building up |

This distribution demonstrates:
- Score divergence (300 to 2400 range)
- Council eligibility thresholds (nova above 2000, arc above 500)
- Different contribution type profiles
- Activity decay (zen is always "fresh", nova sometimes goes inactive)

---

## 9. Implementation Plan

### Phase 1: Skeleton (Day 1)
1. Initialize Next.js project at `/mnt/media/projects/dpc-os-dashboard/`
2. Install shadcn/ui, configure dark theme, add Geist Mono font
3. Build `<OSChrome>`, `<Toolbar>`, `<PanelGrid>`, and `<Panel>` shell components
4. Implement `useReducer` with state schema and `BUILD` action (no animations yet)
5. Wire up seed data and verify state transitions in console
6. **Commit: "Scaffold DPC OS Dashboard with state engine"**

### Phase 2: Score Engine (Day 1-2)
7. Build `<DPCScoreEngine>` with formula display, component bars, score output
8. Implement DPC calculation logic in reducer (contribution weights, decay, floor)
9. Build `<ContributionFeed>` with entry rendering
10. Build `<MemberRegistry>` with clickable member cards
11. Connect Build button → contribution → score recalculation flow
12. **Commit: "Add DPC score engine and contribution feed"**

### Phase 3: Governance + Automation (Day 2)
13. Build `<GovernanceWeightBoard>` with weight table and power distribution
14. Implement sqrt(DPC) governance weight calculation with whale cap
15. Build `<AutomationLayer>` with 6 rules and status LEDs
16. Implement rule evaluation in reducer
17. **Commit: "Add governance weights and automation layer"**

### Phase 4: Rewards + Treasury (Day 2-3)
18. Build `<RewardsDistribution>` with pool, tax, and allocation table
19. Build `<Treasury>` stat cards with sparklines
20. Implement reward distribution in reducer (40% tax, weight-proportional split)
21. **Commit: "Add rewards distribution and treasury"**

### Phase 5: Cascade Animation (Day 3)
22. Implement cascade timing with CSS transitions and `transition-delay`
23. Add panel glow effects, score pulse animation, LED blink
24. Add odometer-style number transitions for score and treasury
25. Implement auto-run mode with interval selector
26. **Commit: "Add cascade animations and auto-run mode"**

### Phase 6: Polish (Day 3-4)
27. Add CRT scanline overlay and noise texture
28. Responsive adjustments (minimum 1280px width, graceful stack on smaller)
29. Add collapsible event log drawer
30. Add keyboard shortcut: Space = Build, R = Reset
31. SEO meta tags, OG image
32. **Commit: "Polish UI, add event log, keyboard shortcuts"**

---

## 10. Risks

- **Animation jank on low-end devices:** CSS transitions are GPU-accelerated but 7 panels updating simultaneously could drop frames. Mitigation: use `will-change: transform, opacity` sparingly, and provide a "reduced motion" toggle that skips animations.

- **State grows unbounded over many cycles:** Contribution history and event log will accumulate. Mitigation: cap contribution feed at 20 entries, treasury history at 100 data points, event log at 200 entries (FIFO).

- **Formula accuracy vs readability:** The actual DPC math uses uint128 with 18 decimals and Babylonian sqrt. The dashboard simulation uses JavaScript floats. Mitigation: acceptable for demonstration purposes — add a footnote "Simplified for visualization. On-chain implementation uses fixed-point arithmetic."

- **Scope creep into real data:** The dashboard is a simulation, not a production governance UI. Mitigation: explicitly scope as client-side only in Phase 1. Backend integration (reading real DPC scores from Memory API or on-chain) is a Phase 7 extension, not in initial scope.

- **Mobile experience:** A 7-panel OS layout doesn't work on phones. Mitigation: set minimum viewport width of 1280px with a "Best viewed on desktop" notice. Mobile adaptation would be a separate UX project.

---

## 11. File Structure

```
dpc-os-dashboard/
├── app/
│   ├── layout.tsx                    # Root layout, fonts, metadata
│   ├── page.tsx                      # Single page — mounts <DPCOSApp>
│   └── globals.css                   # Theme variables, glow effects
├── components/
│   ├── os/
│   │   ├── os-chrome.tsx             # Window chrome wrapper
│   │   ├── toolbar.tsx               # Top toolbar
│   │   ├── panel.tsx                 # Shared panel wrapper (glow logic)
│   │   └── panel-grid.tsx            # CSS grid layout
│   ├── panels/
│   │   ├── contribution-feed.tsx     # Panel 1
│   │   ├── dpc-score-engine.tsx      # Panel 2
│   │   ├── governance-board.tsx      # Panel 3
│   │   ├── automation-layer.tsx      # Panel 4
│   │   ├── rewards-distribution.tsx  # Panel 5
│   │   ├── member-registry.tsx       # Panel 6
│   │   └── treasury.tsx              # Panel 7
│   ├── shared/
│   │   ├── stat-card.tsx             # Reusable stat display with sparkline
│   │   ├── led-indicator.tsx         # Status LED dot
│   │   ├── odometer.tsx             # Animated number display
│   │   ├── member-avatar.tsx        # Procedural avatar
│   │   └── type-badge.tsx            # Contribution type badge
│   └── ui/                           # shadcn/ui components (auto-generated)
├── lib/
│   ├── state/
│   │   ├── types.ts                  # All TypeScript interfaces
│   │   ├── reducer.ts                # Main reducer (5-phase cascade)
│   │   ├── context.tsx               # React context provider
│   │   └── seed-data.ts              # Initial 5-member state
│   ├── engine/
│   │   ├── dpc-calculator.ts         # P = f(Is, Ec, Rw) + decay
│   │   ├── governance-weight.ts      # sqrt(DPC) * activity multiplier
│   │   ├── automation-engine.ts      # Rule evaluation
│   │   ├── reward-distributor.ts     # Pool split logic
│   │   └── contribution-generator.ts # Random contribution factory
│   └── utils.ts                      # Formatting, colors, helpers
├── public/
│   └── og-image.png                  # Open Graph preview
├── package.json
├── tsconfig.json
├── next.config.ts
└── tailwind.config.ts                # Minimal — most in globals.css
```

---

## 12. Extension Points (Not in Scope, But Designed For)

1. **Real Data Mode:** Replace seed data + contribution generator with Memory API calls (`/sos/dpc-export` or on-chain reads). The reducer interface stays the same — only the data source changes.

2. **Multiplayer Simulation:** Add WebSocket support so multiple visitors see the same simulation state. Requires a small backend (the reducer runs server-side, clients receive state updates).

3. **Custom Scenarios:** Allow users to configure member count, starting DPC scores, contribution probabilities, and automation rules. Expose via a settings drawer.

4. **On-Chain Verification:** Each Build press could generate a mock transaction hash. In production mode, it could submit to a testnet DPCRegistry contract.

5. **Embeddable Widget:** Extract the simulation engine into a standalone package that can be embedded in 505.systems or any docs site via an iframe or Web Component.
