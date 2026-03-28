# ONEON — Non-Technical User Onboarding Flow
*Design reference — 2026-03-28*

---

## Purpose

This document maps the complete onboarding journey for a user who has never heard of Web3.
They know: email, usernames, messaging apps, and apps that give them something for participating.
They do not know: wallets, gas, seed phrases, chains, transactions, keys, or DIDs.

Every step is written in plain language. Technical notes are bracketed — they exist for the
implementation team, not for users. No user ever sees the bracketed text.

---

## Design Principles

1. **Never name the mechanism.** Don't say "wallet," "blockchain," "gas," "transaction," "key," or "chain." Show the outcome, not the infrastructure.
2. **Every step earns its place.** If a screen doesn't give the user something (clarity, confidence, a reward), remove it.
3. **The friction is ours to carry.** The user clicks a link and posts something. We handle everything else.
4. **Progressive disclosure, not progressive explanation.** Complexity is offered only when the user reaches for it. Never pushed.
5. **Your handle is the product.** The moment a user claims their handle, something real and permanent happens. Make them feel that.

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         TIER 1 — "IT JUST WORKS"                                │
│                     (User never touches a wallet or sees gas)                   │
└─────────────────────────────────────────────────────────────────────────────────┘

  ARRIVAL                       CLAIM                         VERIFY
  ┌──────────┐                 ┌──────────┐                 ┌──────────────┐
  │ Landing  │    [types]      │ Handle + │   [sends link]  │ Email Check  │
  │ "The     │ ─────────────→  │ Email    │ ─────────────→  │ "Check your  │
  │  network │                 │ Screen   │                 │  inbox"      │
  │  is here"│                 └──────────┘                 └──────┬───────┘
  └──────────┘                                                      │
                                                                    │ [clicks link]
                                                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  BACKGROUND (user sees nothing of this)                                     │
  │  Smart account deployed on Base L2 (~$0.001, paymaster pays)               │
  │  Session keys configured (vote + post + message authorized, 30 days)       │
  │  DID registered: did:oneon:{handle}                                         │
  │  Identity tier: custodial                                                   │
  └─────────────────────────────────────────────────────────────────────────────┘
                                                                    │
                                                                    ▼
  IDENTITY                      FIRST ACTION                  VALUE DELIVERY
  ┌──────────┐                 ┌──────────────┐              ┌──────────────┐
  │ Welcome  │   [taps Vote    │ Action Flow  │  [completes] │ First Badge  │
  │ Screen   │ ─ or Post or ─→ │ (zero steps, │ ──────────→  │ "You're a   │
  │ "You're  │    Message]     │ just happens)│              │  Founder"   │
  │  @handle"│                 └──────────────┘              └──────┬───────┘
  └──────────┘                                                      │
                                                                    │
                              ┌────────────────────────────────────┘
                              │  PROFILE
                              ▼
                         ┌──────────────────────────────────────────┐
                         │  Profile Screen                          │
                         │  "This is yours. No one can take it."    │
                         │                                          │
                         │  [Optional — "I want to own this"]  ─────┼──→  Tier 2 Flow
                         └──────────────────────────────────────────┘

─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

┌─────────────────────────────────────────────────────────────────────────────────┐
│                  TIER 2 — "I WANT TO OWN THIS"  (Optional, user-initiated)      │
└─────────────────────────────────────────────────────────────────────────────────┘

  OPT-IN                       GUIDED EXPORT                 BACKUP
  ┌──────────────┐             ┌──────────────┐              ┌──────────────┐
  │ "What does   │  [confirms] │ "Here's your │  [copies]    │ "Choose 3    │
  │  owning it   │ ──────────→ │  key. Keep   │ ──────────→  │  guardians"  │
  │  mean?"      │             │  it safe."   │              │  (recovery)  │
  └──────────────┘             └──────────────┘              └──────────────┘
```

---

## Screen-by-Screen Copy

---

### Screen 1 — Landing / Arrival

**Context:** The user arrives at oneon.ink from a link or search. They have no prior context.
**Goal:** Create curiosity and a single clear action.
**[Technical note]:** Existing terminal-typewriter UX — `oneon-web/app/page.tsx`. No changes needed for Phase 1.

---

**Heading:**
> The network was always here.
> You just needed to find the door.

**Body:**
> ONEON is a network that belongs to no company.
> Your handle. Your messages. Your reputation. Yours — not ours.

**CTA:**
> Claim your handle

**Subtext below CTA:**
> Free to join. No technical knowledge needed.

---

### Screen 2 — Handle + Email

**Context:** The user taps "Claim your handle." They see a simple input form.
**Goal:** Collect the minimum information needed. Make claiming a handle feel significant.
**[Technical note]:** POST `/oneon/signup` — creates identity (waitlist→custodial), stores handle+email, initiates magic link send, triggers background smart account deployment.

---

**Heading:**
> Choose your name on the network.

**Helper text (above handle input):**
> This will be yours forever. No one else can have it.

**Handle input:**
> Placeholder: `@youhandle`

**Email input:**
> Placeholder: `your@email.com`
> Helper: We'll send you a link to confirm. No password needed.

**Button:**
> Claim @[handle]

**Validation (handle taken):**
> @[handle] is gone. Try @[handle]-[suggestion].

**Validation (handle available):**
> @[handle] is yours. ✓

**Legal note (small, below button):**
> By joining, you agree to the ONEON terms. Free. No card required.

---

### Screen 3 — Email Sent (Check Inbox)

**Context:** The user has submitted their handle and email. They're waiting.
**Goal:** Bridge the gap between submission and inbox check. Reduce drop-off at this step.
**[Technical note]:** Magic link valid 15 minutes. Tokenized, single-use. Triggers smart account creation in background so it's ready before the user clicks.

---

**Heading:**
> Check your inbox.

**Body:**
> We sent a link to **[email]**.
> Click it and you're in — no password, no more steps.

**Subtext:**
> Takes about 30 seconds.

**Help accordion (collapsed by default):**
> **Didn't get it?**
> Check spam first. Still nothing? → [Resend link]
> Wrong email? → [Start over]

**Waiting message (10s after page load):**
> Still here? It sometimes lands in spam — worth a check.

---

### Screen 4 — Email Confirmed (Magic Link Click)

**Context:** The user clicks the link in their email and lands on this screen.
**Goal:** The moment of confirmation. Fast, clear, permanent-feeling.
**[Technical note]:** POST `/oneon/auth/magic-link` — verifies token, activates session key, moves identity tier to `custodial`, returns `session_token`. Smart account already deployed in background (from Screen 2). This step is near-instant for the user.

---

**Heading:**
> You're in.

**Body:**
> @[handle] is yours.
> Everything is ready.

**Animation:** Brief, quiet. A sigil or mark that feels like a seal — something being made permanent.

**Auto-advance:** 2 seconds, then forward to Welcome screen.
*(No button needed. The moment should breathe.)*

---

### Screen 5 — Welcome / Identity Screen

**Context:** First real screen after verification. The user sees their handle, their place in the network.
**Goal:** The identity moment. They should feel that something real was created — not just an account.
**[Technical note]:** Identity tier = `custodial`. DID: `did:oneon:{handle}`. Smart account on Base L2 deployed and session keys active. User sees none of this. Their "address" is their handle.

---

**Heading:**
> Welcome, @[handle].

**Body:**
> You have an identity on the network now. It's permanent, portable, and belongs to no company.
> No one can take @[handle] from you.

**Primary action:**
> Explore the network →

**Secondary action (ghost button):**
> See what others are doing

**Bottom note (small):**
> Your identity was just created. It lives on a public network — not on our servers.
> *[Collapsed: "What does that mean? →"]* — links to a plain-language explainer.

---

### Screen 6 — First Action (Vote / Post / Message)

**Context:** The user takes their first real action on the network. This is where the "wallet" would have interrupted any other Web3 app. Here, nothing interrupts.
**Goal:** The action completes instantly. The user never knows a signed transaction occurred.
**[Technical note]:** Session key signs UserOp automatically (server-side, invisible.py). Paymaster sponsors gas. Bundler submits to Base L2. From user perspective: they tapped a button, and it worked.

Three variants depending on context:

---

#### Variant A — First Vote

**Action label:** Vote on a proposal

**Pre-action:**
> The network is deciding something. Your voice counts from day one.
> [Proposal title]

**Vote buttons:**
> [For]   [Against]   [Abstain]

**In-progress state (instant — <1 second):**
> Submitting your vote...

**Success state:**
> Your vote is in.
> It's recorded. It can't be changed or removed.

**Subtext:**
> You are now part of how this network governs itself.

---

#### Variant B — First Post

**Composer heading:**
> Say something to the network.

**Placeholder:**
> What's on your mind, @[handle]?

**Post button:**
> Post

**In-progress state (instant):**
> Posting...

**Success state:**
> Posted.
> It's permanent. It's yours.

**Subtext below post:**
> This is stored in a way no company controls.

---

#### Variant C — First Message

**Prompt:**
> Send a message to someone on the network.

**Input:**
> To: @[handle]

**Message input:**
> Placeholder: Your message

**Send button:**
> Send

**Success state:**
> Sent.
> Only you and @[recipient] can read it.

**Subtext:**
> Your messages are encrypted. Even ONEON can't read them.

---

### Screen 7 — First Badge (Value Delivery Moment)

**Context:** Shortly after first action, the user receives a badge. This is the "value delivery moment" — the first time the network gives something back.
**Goal:** Create a sense of earned recognition. The badge feels real, not hollow.
**[Technical note]:** W3C Verifiable Credential issued to user's DID. Credential type: `NetworkFounder` (or appropriate first-action credential). Stored on-chain via `ONEONCredentials.sol`. User sees: a badge and a name. Never sees "VC" or "DID" or "on-chain."

---

**Full-screen moment (brief modal or dedicated screen):**

**Badge visual:** Clean emblem. Not a cartoon. Something that looks like it belongs on a document.

**Heading:**
> You earned something.

**Badge name:**
> Network Founder

**Description:**
> This is a permanent record that you were here early.
> It can't be faked. It can't be taken away.
> You can carry it with you anywhere on the network.

**Subtext:**
> Every action you take on ONEON builds your reputation here.
> Not followers. Not likes. A record of what you actually did.

**Button:**
> See your profile

---

### Screen 8 — Profile

**Context:** The user's profile after onboarding completes.
**Goal:** Show what they've built — even in the first 2 minutes. Create a sense of permanence and ownership.
**[Technical note]:** Badges = VCs surfaced as achievements. "Identity" field shows handle + DID (handle only in Tier 1 view). Activity = signed actions on-chain.

---

**Profile header:**
> @[handle]

**Tagline (auto-generated for Tier 1, editable):**
> Member since [today's date].

**Badges section heading:**
> What you've earned

**Badges display:**
> [Network Founder badge]
> [First Vote badge — if voted]
> [First Message badge — if messaged]

**Activity section heading:**
> What you've done

**Activity items:**
> Voted on [proposal] — [timestamp]
> Joined the network — [timestamp]

**Bottom section — progressive disclosure:**

**"This is yours" callout (collapsible):**
> Your profile, your reputation, and your identity are stored on a public network — not in a database we control. If ONEON shut down tomorrow, your identity would still exist.

**Tier 2 prompt (small, never pushed):**
> Want to hold your own keys? → [I want full control]
> *Links to Tier 2 opt-in flow.*

---

## Summary: What the User Never Sees

| What happened (technical) | What the user saw |
|---|---|
| ERC-4337 smart account deployed on Base L2 | Nothing. It was instant. |
| Session keys configured (30-day auth scope) | Nothing. Actions just worked. |
| DID registered: `did:oneon:{handle}` | "Your handle is permanent." |
| Paymaster sponsored ~$0.001 in gas | Nothing. Free to use. |
| UserOp signed and submitted to bundler | A button that did what they expected. |
| W3C Verifiable Credential issued | "You earned a badge." |
| Encrypted key pair for XMTP messaging | "Only you can read this message." |

---

## Progressive Disclosure Ladder

The user is never forced to climb. Every rung is offered, never required.

```
RUNG 0  →  You have a handle. Things work.
RUNG 1  →  You have a reputation. Your actions are recorded.
RUNG 2  →  You have a record. Permanent, portable, ours to show.
RUNG 3  →  You have a key. [Tier 2 opt-in] — "Want full control?"
RUNG 4  →  You are the node. [Tier 3] — "Want to be the network?"
```

No pop-ups pushing upgrades. No "you're missing out" prompts.
The complexity is a door. It opens inward when the user pulls it.

---

## Error States

Every error must be written in the same plain language as the rest of the flow.

| Error | Copy |
|---|---|
| Handle taken | "@[handle] is already claimed. Try @[alternative]." |
| Email bounced | "We couldn't reach [email]. Try another?" |
| Magic link expired | "That link expired. [Send a new one]." |
| Action failed (network) | "Something went wrong on our end. Try again in a moment." |
| Action failed (rate limit) | "You're moving fast. Wait a moment and try again." |

**Rule:** Never show error codes. Never say "transaction failed." Never say "RPC error." Never blame the user. Own the problem.

---

## Voice Notes for Copywriters

- **"Permanent"** — use it often. This is the one thing Web3 provides that Web2 never could. Users feel it even if they don't know why.
- **"Yours"** — the second most important word in this flow. Everything the user touches becomes theirs.
- **No exclamation marks.** None. This isn't a signup form for a restaurant loyalty program.
- **No emojis** in system messages. Badges can have visual emblems. The voice is quiet authority.
- **Short sentences.** "You're in." "It's yours." "Only you can read this."
- **"Network" not "blockchain."** "Record" not "transaction." "Identity" not "wallet." "Earn" not "mint."
- **What they feel, not what it is.** "You have a voice here from day one" — not "your vote is recorded as an on-chain UserOp via ERC-4337."

---

## Implementation Notes (for Phase 1 build)

1. **Screen 2 triggers background deployment.** `POST /oneon/signup` initiates smart account deployment. By the time the user clicks the magic link, the account exists.
2. **Session keys are transparent.** The user never confirms an action. `invisible.py` signs automatically within pre-authorized scopes.
3. **Badge timing.** Issue `NetworkFounder` credential on first completed action (vote, post, or message) — not on signup. Earning requires doing.
4. **Tier 2 prompt placement.** Profile screen only. Never in the onboarding funnel. The moment a user has completed the flow and feels ownership, the prompt to "go deeper" is natural. In the funnel, it's noise.
5. **Magic link expiry.** 15 minutes. Keep it short — long expiry invites stale clicks. Show clear "resend" option.
6. **Error handling.** All errors in plain language. `invisible.py` must not surface chain-level error messages to the frontend API response. Translate everything.
