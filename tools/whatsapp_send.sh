#!/bin/bash
# Send a WhatsApp message to Admin (Mev)
# Usage: whatsapp_send.sh "Your message here"

set -euo pipefail

WHATSAPP_URL="http://localhost:3001"
ADMIN_JID="94743806705@s.whatsapp.net"

if [ $# -eq 0 ]; then
    echo "Usage: $0 \"message\"" >&2
    exit 1
fi

MESSAGE="$1"

# Build JSON payload safely using python3 to handle escaping
JSON_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({'jid': sys.argv[1], 'message': sys.argv[2]}))
" "$ADMIN_JID" "$MESSAGE")

# Send via WhatsApp HTTP service
RESPONSE=$(curl -sf -X POST "${WHATSAPP_URL}/send" \
    -H 'Content-Type: application/json' \
    -d "$JSON_PAYLOAD" \
    2>&1) || {
    echo "Failed to send WhatsApp message: ${RESPONSE}" >&2
    exit 1
}

echo "Message sent to Admin"
