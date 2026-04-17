#!/usr/bin/env bash
# generate_demo.sh — Generate a landing page demo and deploy it
# Usage: ./tools/generate_demo.sh "Business Name" "brief description"
# Or:    ./tools/generate_demo.sh --random   (picks a random lead from DB)

set -euo pipefail

log() { echo "[demo] $*" >&2; }

DEMOS_DIR="/mnt/media/projects/x402t-demos"
DEMO_BASE_URL="https://demo.x402t.xyz"

# ── Resolve lead ──────────────────────────────────────────────
if [[ "${1:-}" == "--random" ]]; then
  log "Picking random lead from database..."
  LEAD_JSON=$(docker exec memory-postgres-1 psql -U otto -d memory -t -A -c "
    SELECT json_build_object(
      'name', name,
      'types', types,
      'address', address,
      'phone', phone,
      'website', website,
      'city', city,
      'country', country,
      'rating', rating,
      'reviews', user_ratings_total
    )
    FROM web_assist_leads
    WHERE business_status = 'OPERATIONAL'
      AND website IS NOT NULL
      AND rating IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 1;
  ")

  BUSINESS_NAME=$(echo "$LEAD_JSON" | jq -r '.name')
  TYPES=$(echo "$LEAD_JSON" | jq -r '.types')
  ADDRESS=$(echo "$LEAD_JSON" | jq -r '.address')
  PHONE=$(echo "$LEAD_JSON" | jq -r '.phone')
  WEBSITE=$(echo "$LEAD_JSON" | jq -r '.website')
  CITY=$(echo "$LEAD_JSON" | jq -r '.city')
  COUNTRY=$(echo "$LEAD_JSON" | jq -r '.country')
  RATING=$(echo "$LEAD_JSON" | jq -r '.rating')
  REVIEWS=$(echo "$LEAD_JSON" | jq -r '.reviews')

  log "Selected: $BUSINESS_NAME ($CITY, $COUNTRY) — $RATING stars, $REVIEWS reviews"

  BRIEF="Build a landing page for **${BUSINESS_NAME}** — a business located at ${ADDRESS}.

**Business details:**
- Name: ${BUSINESS_NAME}
- Types: ${TYPES}
- Location: ${ADDRESS}
- Phone: ${PHONE}
- Website: ${WEBSITE}
- City: ${CITY}, ${COUNTRY}
- Rating: ${RATING} stars (${REVIEWS} reviews on Google)

**Target audience:** People in ${CITY} looking for services this business provides. Both locals and visitors.

**Primary CTA:** Drive foot traffic, inquiries, or bookings.

**Tone:** Professional but approachable. Match the vibe to the industry."
else
  if [[ $# -lt 2 ]]; then
    log "Usage: $0 \"Business Name\" \"brief description of the business\""
    log "   or: $0 --random"
    exit 1
  fi
  BUSINESS_NAME="$1"
  shift
  BRIEF="Build a landing page for **${BUSINESS_NAME}**. $*"
fi

# ── Generate slug ─────────────────────────────────────────────
SLUG=$(echo "$BUSINESS_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
OUTPUT_FILE="${DEMOS_DIR}/demos/${SLUG}.html"

log "Slug: ${SLUG}"
log "Output: ${OUTPUT_FILE}"

# ── Check if demo already exists ──────────────────────────────
if [[ -f "$OUTPUT_FILE" ]]; then
  log "WARNING: ${OUTPUT_FILE} already exists. Overwriting."
fi

# ── Generate landing page via Claude agent ────────────────────
log "Generating landing page with landing-page agent (Sonnet 4.6)..."

AGENT_PROMPT="${BRIEF}

IMPORTANT: Skip the concept proposal phase — just pick the best creative direction and build it directly. Output the complete HTML file.

**Requirements:**
- Single self-contained HTML file with inline CSS and JS
- Make it feel like the product — the design should embody the business
- Include sections: Hero with CTA, About/Story, Key services/features, Social proof, Location/contact, Final CTA
- Mobile-first responsive design
- No stock photos — use evocative CSS gradients, shapes, and animations instead
- Make it screenshot-worthy

Write the final HTML to: ${OUTPUT_FILE}"

CLAUDECODE= claude --agent landing-page -p \
  --dangerously-skip-permissions \
  --model sonnet \
  --max-budget-usd 1 \
  "$AGENT_PROMPT" > /dev/null 2>&1

# ── Verify file was created ───────────────────────────────────
if [[ ! -f "$OUTPUT_FILE" ]]; then
  log "ERROR: Agent did not create ${OUTPUT_FILE}"
  exit 1
fi

FILE_SIZE=$(wc -c < "$OUTPUT_FILE")
log "Generated: ${OUTPUT_FILE} (${FILE_SIZE} bytes)"

# ── Deploy: commit and push ───────────────────────────────────
log "Deploying to Vercel..."
cd "$DEMOS_DIR"
git add "demos/${SLUG}.html"
git commit -m "Add demo: ${BUSINESS_NAME}" --author="ottomev <abraottomev@gmail.com>"
git push

# ── Wait for Vercel deployment ────────────────────────────────
log "Waiting for Vercel deployment..."
sleep 20

# ── Verify ────────────────────────────────────────────────────
DEMO_URL="${DEMO_BASE_URL}/${SLUG}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$DEMO_URL")

if [[ "$HTTP_CODE" == "200" ]]; then
  log ""
  log "========================================"
  log "LIVE: ${DEMO_URL}"
  log "========================================"
else
  log "WARNING: ${DEMO_URL} returned HTTP ${HTTP_CODE} (may still be deploying)"
  log "URL: ${DEMO_URL}"
fi

# Output the URL to stdout (for piping/capture)
echo "$DEMO_URL"
