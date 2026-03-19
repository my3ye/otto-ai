#!/usr/bin/env bash
# Wire Stripe test API keys into WebAssist (Vercel + local .env)
#
# Usage: ./wire_stripe_keys.sh <sk_test_...> <pk_test_...> <whsec_...>
#
# This script:
#   1. Validates the key formats
#   2. Adds them to Vercel env (Production + Preview + Development)
#   3. Updates the local web-assist .env file
#   4. Triggers a Vercel redeploy
#   5. Stores confirmation in Otto's semantic memory

set -euo pipefail

STRIPE_SECRET_KEY="${1:-}"
STRIPE_PUBLISHABLE_KEY="${2:-}"
STRIPE_WEBHOOK_SECRET="${3:-}"

WEB_ASSIST_DIR="/mnt/media/projects/web-assist"

# ── Validation ──────────────────────────────────────────────────────────────

if [[ -z "$STRIPE_SECRET_KEY" || -z "$STRIPE_PUBLISHABLE_KEY" || -z "$STRIPE_WEBHOOK_SECRET" ]]; then
    echo "❌ Usage: $0 <sk_test_...> <pk_test_...> <whsec_...>"
    echo ""
    echo "All 3 keys required:"
    echo "  1. Secret key:        sk_test_... or sk_live_..."
    echo "  2. Publishable key:   pk_test_... or pk_live_..."
    echo "  3. Webhook secret:    whsec_..."
    echo ""
    echo "Get from: https://dashboard.stripe.com/test/apikeys"
    echo "Webhook:  https://dashboard.stripe.com/test/webhooks"
    echo "          URL: https://webassist.ink/api/payment/webhook"
    echo "          Events: checkout.session.completed, payment_intent.payment_failed"
    exit 1
fi

# Validate formats
if [[ ! "$STRIPE_SECRET_KEY" =~ ^sk_(test|live)_ ]]; then
    echo "❌ Invalid secret key format. Expected: sk_test_... or sk_live_..."
    exit 1
fi

if [[ ! "$STRIPE_PUBLISHABLE_KEY" =~ ^pk_(test|live)_ ]]; then
    echo "❌ Invalid publishable key format. Expected: pk_test_... or pk_live_..."
    exit 1
fi

if [[ ! "$STRIPE_WEBHOOK_SECRET" =~ ^whsec_ ]]; then
    echo "❌ Invalid webhook secret format. Expected: whsec_..."
    exit 1
fi

echo "✅ Key formats validated"
echo ""
echo "🔑 Wiring Stripe keys..."
echo "   Secret:    ${STRIPE_SECRET_KEY:0:15}..."
echo "   Publish:   ${STRIPE_PUBLISHABLE_KEY:0:15}..."
echo "   Webhook:   ${STRIPE_WEBHOOK_SECRET:0:15}..."
echo ""

# ── 1. Update local .env file ────────────────────────────────────────────────

ENV_FILE="$WEB_ASSIST_DIR/.env"

# Remove old Stripe entries if present
if grep -q "STRIPE_SECRET_KEY=" "$ENV_FILE" 2>/dev/null; then
    sed -i '/^STRIPE_SECRET_KEY=/d' "$ENV_FILE"
    sed -i '/^NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=/d' "$ENV_FILE"
    sed -i '/^STRIPE_WEBHOOK_SECRET=/d' "$ENV_FILE"
fi

# Append new values
cat >> "$ENV_FILE" << EOF

# Stripe Payment Integration (wired $(date -u +%Y-%m-%dT%H:%M:%SZ))
STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=$STRIPE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET
EOF

echo "✅ Local .env updated"

# ── 2. Wire into Vercel ──────────────────────────────────────────────────────

cd "$WEB_ASSIST_DIR"

echo ""
echo "📡 Adding to Vercel..."

# Remove old values first (ignore errors if not present)
vercel env rm STRIPE_SECRET_KEY production --yes 2>/dev/null || true
vercel env rm STRIPE_SECRET_KEY preview --yes 2>/dev/null || true
vercel env rm STRIPE_SECRET_KEY development --yes 2>/dev/null || true
vercel env rm NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY production --yes 2>/dev/null || true
vercel env rm NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY preview --yes 2>/dev/null || true
vercel env rm NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY development --yes 2>/dev/null || true
vercel env rm STRIPE_WEBHOOK_SECRET production --yes 2>/dev/null || true
vercel env rm STRIPE_WEBHOOK_SECRET preview --yes 2>/dev/null || true
vercel env rm STRIPE_WEBHOOK_SECRET development --yes 2>/dev/null || true

# Add new values
echo "$STRIPE_SECRET_KEY" | vercel env add STRIPE_SECRET_KEY production
echo "$STRIPE_SECRET_KEY" | vercel env add STRIPE_SECRET_KEY preview
echo "$STRIPE_SECRET_KEY" | vercel env add STRIPE_SECRET_KEY development

echo "$STRIPE_PUBLISHABLE_KEY" | vercel env add NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY production
echo "$STRIPE_PUBLISHABLE_KEY" | vercel env add NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY preview
echo "$STRIPE_PUBLISHABLE_KEY" | vercel env add NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY development

echo "$STRIPE_WEBHOOK_SECRET" | vercel env add STRIPE_WEBHOOK_SECRET production
echo "$STRIPE_WEBHOOK_SECRET" | vercel env add STRIPE_WEBHOOK_SECRET preview
echo "$STRIPE_WEBHOOK_SECRET" | vercel env add STRIPE_WEBHOOK_SECRET development

echo "✅ Vercel env vars set"

# ── 3. Trigger redeploy ──────────────────────────────────────────────────────

echo ""
echo "🚀 Triggering Vercel redeploy..."
vercel --prod --yes 2>&1 | tail -5
echo "✅ Redeploy triggered"

# ── 4. Store in Otto memory ──────────────────────────────────────────────────

KEY_MODE="test"
if [[ "$STRIPE_SECRET_KEY" =~ sk_live_ ]]; then
    KEY_MODE="live"
fi

curl -s -X POST http://localhost:8100/semantic/remember \
    -H 'Content-Type: application/json' \
    -d "{
        \"content\": \"Stripe $KEY_MODE keys wired into WebAssist (webassist.ink). Keys set in Vercel (production/preview/dev) and local .env. Webhook endpoint: https://webassist.ink/api/payment/webhook. Wired: $(date -u +%Y-%m-%dT%H:%M:%SZ)\",
        \"category\": \"infrastructure\",
        \"confidence\": 0.95
    }" > /dev/null

echo ""
echo "✅ Stored in Otto memory"

echo ""
echo "═══════════════════════════════════════════════════"
echo "✅ STRIPE KEYS WIRED SUCCESSFULLY"
echo "   Mode: $KEY_MODE"
echo "   Site: https://webassist.ink"
echo "   Webhook: https://webassist.ink/api/payment/webhook"
echo "═══════════════════════════════════════════════════"
echo ""
echo "⚠️  VERIFY: Visit https://webassist.ink and test the payment flow"
echo "   For webhooks: Make sure the webhook is registered in Stripe Dashboard"
echo "   pointing to https://webassist.ink/api/payment/webhook"
echo "   with events: checkout.session.completed, payment_intent.payment_failed"
