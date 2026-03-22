---
name: OMS Mobile Responsiveness Patterns
description: Common mobile responsiveness bugs in OMS pages and their root causes
type: project
---

## Pattern 1: Shell Double-Padding

**Symptom:** Page content is excessively cramped on mobile despite responsive classes.

**Root cause:** `providers.tsx` AppShell already wraps `{children}` with `p-4 md:p-6`. Pages that ADD their own `p-4 md:p-6` get double padding (32px total on mobile sides instead of 16px).

**Fix:** Remove the page-level `p-4 md:p-6` from the root div. The shell handles it. Keep `space-y-6` for vertical spacing.

**Why it matters on small screens:** On 375px phone, double padding leaves only 311px content width. Many elements designed for 320px+ need to scroll unnecessarily.

**Files to check:** Any page in `~/interfaces/web-next/src/app/*/page.tsx` with `p-4 md:p-6` or `p-6` on the root div.

---

## Pattern 2: Fixed-Width Two-Column Layout

**Symptom:** Split-pane pages (email client, etc.) have an invisible right panel on mobile.

**Root cause:** Left panel uses `w-80` (320px) which occupies nearly the entire 375px viewport, leaving ~55px for the right panel.

**Fix:** Add `mobileDetailVisible` boolean state. Use conditional CSS classes:
- List: `hidden sm:flex sm:w-80 sm:shrink-0` when detail visible; `flex w-full sm:w-80 sm:shrink-0` when list visible
- Detail: `flex flex-1` when detail visible; `hidden sm:flex sm:flex-1` when list visible
- Add mobile back button: `<div className="sm:hidden">` with back navigation

**Files affected:** `inbox/page.tsx` (fixed 2026-03-17)

---

## Pattern 3: Hardcoded Horizontal Margins

**Symptom:** Banners/alerts appear with too much horizontal offset on mobile.

**Root cause:** Hardcoded `mx-6` doesn't adapt to smaller screens.

**Fix:** Change to `mx-4 sm:mx-6`.

---

## Pattern 4: Inbox Height Calculation Off

**Symptom:** Inbox panel is slightly taller than viewport, causing the outer shell to scroll instead of inner ScrollArea components.

**Root cause:** `h-[calc(100vh-4rem)]` only subtracts the header height (3rem = 48px = 4rem was wrong anyway) but not shell padding. Correct formula:
- Mobile: `h-[calc(100dvh-5rem)]` — header (3rem) + top/bottom shell p-4 (2×1rem)
- Desktop: `h-[calc(100dvh-6rem)]` — header (3rem) + top/bottom shell p-6 (2×1.5rem)

**Fix:** `h-[calc(100dvh-5rem)] md:h-[calc(100dvh-6rem)]`

---

## Shell Architecture Reference

```
SidebarProvider (max-h-svh overflow-hidden)
  AppSidebar
  main (flex flex-1 flex-col overflow-hidden)
    Header (h-12 = 3rem = 48px)
    div (flex min-h-0 flex-1 flex-col overflow-auto p-4 md:p-6)  ← PROVIDES PADDING
      {children}  ← pages should NOT add their own outer padding
```

**Why:** The innermost `div` is `overflow-auto` — if page content overflows it, the div scrolls (bad UX for fixed-height panels like inbox).

---

## Prevention Rule

**Added to agents (2026-03-17):** heartbeat.md and reflection.md both now include mobile responsiveness as a mandatory QA gate. All UI tasks must explicitly confirm mobile testing before being marked complete.
