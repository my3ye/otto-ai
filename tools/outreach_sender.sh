#!/bin/bash
# Web Assist Outreach Sender
# Sends approved/pending WhatsApp messages from outreach_queue
# Usage: outreach_sender.sh [--dry-run] [--limit N] [--approve-first]
#
# Modes:
#   --dry-run       Print messages without sending
#   --limit N       Max messages to send (default: 5)
#   --approve-all   Mark all pending as approved before sending

set -euo pipefail

WHATSAPP_URL="http://localhost:3001"
ADMIN_JID="94743806705@s.whatsapp.net"
DB_CONTAINER="memory-postgres-1"
DB_USER="otto"
DB_NAME="memory"
DRY_RUN=false
LIMIT=5
APPROVE_ALL=false
DELAY_SECONDS=30  # delay between messages to avoid spam flags

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --limit) LIMIT="$2"; shift 2 ;;
        --approve-all) APPROVE_ALL=true; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

db_query() {
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "$1" 2>/dev/null
}

# Optional: approve all pending first
if [[ "$APPROVE_ALL" == "true" ]]; then
    log "Approving all pending messages..."
    db_query "UPDATE outreach_queue SET status='approved', approved_at=NOW() WHERE status='pending';"
fi

# Fetch approved messages
MESSAGES=$(db_query "
SELECT id, business_name, phone, message_body
FROM outreach_queue
WHERE status = 'approved' AND sent_at IS NULL AND phone IS NOT NULL
ORDER BY lead_score DESC NULLS LAST
LIMIT $LIMIT;
")

if [[ -z "$MESSAGES" ]]; then
    log "No approved messages to send."
    exit 0
fi

SENT=0
FAILED=0

while IFS='|' read -r id business_name phone message_body; do
    [[ -z "$id" ]] && continue

    log "→ [$((SENT+FAILED+1))/$LIMIT] $business_name ($phone)"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "  DRY RUN: Would send to $phone"
        echo "  Message: ${message_body:0:100}..."
        SENT=$((SENT+1))
        continue
    fi

    # Format phone: strip +, ensure 94XXXXXXXXX@s.whatsapp.net
    CLEAN_PHONE=$(echo "$phone" | tr -d '+ -()' | sed 's/^0/94/')
    TARGET_JID="${CLEAN_PHONE}@s.whatsapp.net"

    # Build JSON payload
    JSON_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({'jid': sys.argv[1], 'message': sys.argv[2]}))
" "$TARGET_JID" "$message_body")

    RESPONSE=$(curl -sf -X POST "${WHATSAPP_URL}/send" \
        -H 'Content-Type: application/json' \
        -d "$JSON_PAYLOAD" 2>&1) && {

        # Mark as sent in DB
        db_query "UPDATE outreach_queue SET status='sent', sent_at=NOW() WHERE id='$id';"
        # Update lead outreach status
        db_query "UPDATE web_assist_leads SET outreach_status='contacted', outreach_at=NOW()
                  WHERE id=(SELECT lead_id FROM outreach_queue WHERE id='$id');"

        log "  ✓ Sent to $business_name"
        SENT=$((SENT+1))

        # Polite delay
        if [[ $SENT -lt $LIMIT ]]; then
            sleep $DELAY_SECONDS
        fi
    } || {
        log "  ✗ Failed: $RESPONSE"
        db_query "UPDATE outreach_queue SET status='failed' WHERE id='$id';"
        FAILED=$((FAILED+1))
    }

done <<< "$MESSAGES"

log "Done. Sent: $SENT, Failed: $FAILED"

# Notify Otto/admin
if [[ "$DRY_RUN" == "false" && $SENT -gt 0 ]]; then
    ~/otto/tools/whatsapp_send.sh "✅ Outreach sent: $SENT messages delivered to Web Assist leads. Reply to any responses and I'll handle them."
fi
