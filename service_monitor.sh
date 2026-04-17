#!/bin/bash
# Otto Service Monitor
# Checks all registered live services and posts health results to the API.
# Runs as systemd timer: otto-service-monitor.timer (every 5 minutes)
# NO Claude CLI — no budget consumed. Pure bash.
#
# Usage: service_monitor.sh
# Logs: ~/otto/logs/service-monitor-YYYYMMDD.log

set -uo pipefail

API="http://localhost:8100"
LOG_FILE="/home/web3relic/otto/logs/service-monitor-$(date +%Y%m%d).log"
WHATSAPP_SEND="/home/web3relic/otto/tools/whatsapp_send.sh"

mkdir -p "$(dirname "$LOG_FILE")"

mlog() { echo "$(date -Iseconds) [svc-monitor] $*" | tee -a "$LOG_FILE"; }

mlog "Service monitor starting"

# Fetch all enabled services
SERVICES_JSON=$(curl -sf "${API}/services" 2>/dev/null) || {
    mlog "ERROR: Could not fetch services from API"
    exit 1
}

SERVICE_COUNT=$(echo "$SERVICES_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
mlog "Checking $SERVICE_COUNT services"

# Process each service
echo "$SERVICES_JSON" | python3 -c "
import json, sys
services = json.load(sys.stdin)
for s in services:
    print(s['id'], s['name'], s['check_method'], s['check_target'], s.get('check_timeout_s', 10))
" 2>/dev/null | while IFS=' ' read -r SVC_ID SVC_NAME CHECK_METHOD CHECK_TARGET CHECK_TIMEOUT; do

    START_MS=$(($(date +%s%N) / 1000000))
    STATUS="unknown"
    DETAILS=""

    case "$CHECK_METHOD" in

        systemd)
            # Check systemd unit (service or timer)
            UNIT_STATUS=$(systemctl is-active "$CHECK_TARGET" 2>/dev/null || echo "inactive")
            if [ "$UNIT_STATUS" = "active" ]; then
                STATUS="healthy"
                DETAILS="systemctl: active"
            else
                STATUS="down"
                DETAILS="systemctl: $UNIT_STATUS"
                mlog "FAIL $SVC_NAME: systemd unit $CHECK_TARGET is $UNIT_STATUS"
            fi
            ;;

        docker)
            # Check Docker container state
            CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' "$CHECK_TARGET" 2>/dev/null || echo "missing")
            if [ "$CONTAINER_STATUS" = "running" ]; then
                STATUS="healthy"
                DETAILS="docker: running"
            else
                STATUS="down"
                DETAILS="docker: $CONTAINER_STATUS"
                mlog "FAIL $SVC_NAME: container $CHECK_TARGET is $CONTAINER_STATUS"
            fi
            ;;

        http)
            # HTTP health check — expect 2xx response
            HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time "$CHECK_TIMEOUT" "$CHECK_TARGET" 2>/dev/null || echo "000")
            if echo "$HTTP_CODE" | grep -qE "^2[0-9]{2}$"; then
                STATUS="healthy"
                DETAILS="http: $HTTP_CODE"
            else
                STATUS="down"
                DETAILS="http: $HTTP_CODE (expected 2xx)"
                mlog "FAIL $SVC_NAME: HTTP $HTTP_CODE from $CHECK_TARGET"
            fi
            ;;

        process)
            # Check by process name or PID file
            if echo "$CHECK_TARGET" | grep -q "\.pid$"; then
                # PID file
                if [ -f "$CHECK_TARGET" ]; then
                    PID=$(cat "$CHECK_TARGET" 2>/dev/null || echo "")
                    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
                        STATUS="healthy"
                        DETAILS="process: pid=$PID alive"
                    else
                        STATUS="down"
                        DETAILS="process: pid file exists but process not running"
                    fi
                else
                    STATUS="down"
                    DETAILS="process: pid file not found: $CHECK_TARGET"
                fi
            else
                # Process name search
                PROC_COUNT=$(pgrep -fc "$CHECK_TARGET" 2>/dev/null || echo "0")
                if [ "$PROC_COUNT" -gt 0 ]; then
                    STATUS="healthy"
                    DETAILS="process: $PROC_COUNT matching '$CHECK_TARGET'"
                else
                    STATUS="down"
                    DETAILS="process: no process matching '$CHECK_TARGET'"
                    mlog "FAIL $SVC_NAME: no process matching $CHECK_TARGET"
                fi
            fi
            ;;

        script)
            # Custom health script — exit 0=healthy, 1=degraded, 2=down
            if [ -x "$CHECK_TARGET" ]; then
                SCRIPT_OUT=$(timeout "$CHECK_TIMEOUT" bash "$CHECK_TARGET" 2>&1 || true)
                SCRIPT_EXIT=$?
                case $SCRIPT_EXIT in
                    0) STATUS="healthy"; DETAILS="script: exit 0" ;;
                    1) STATUS="degraded"; DETAILS="script: exit 1 — $SCRIPT_OUT" ;;
                    *) STATUS="down"; DETAILS="script: exit $SCRIPT_EXIT — $SCRIPT_OUT" ;;
                esac
            else
                STATUS="unknown"
                DETAILS="script: not executable or not found: $CHECK_TARGET"
            fi
            ;;

        *)
            STATUS="unknown"
            DETAILS="unknown check_method: $CHECK_METHOD"
            mlog "WARN $SVC_NAME: unknown check_method=$CHECK_METHOD"
            ;;
    esac

    END_MS=$(($(date +%s%N) / 1000000))
    RESPONSE_MS=$((END_MS - START_MS))

    mlog "$SVC_NAME → $STATUS (${RESPONSE_MS}ms) — $DETAILS"

    # Post result to API
    HEARTBEAT_RESPONSE=$(curl -sf -X POST "${API}/services/${SVC_ID}/heartbeat" \
        -H 'Content-Type: application/json' \
        -d "{\"status\": \"${STATUS}\", \"response_time_ms\": ${RESPONSE_MS}, \"details\": \"$(echo "$DETAILS" | sed 's/"/\\"/g')\"}" \
        2>/dev/null) || mlog "WARN: Could not post heartbeat for $SVC_NAME"

    # Check if Mev alert was triggered
    if echo "$HEARTBEAT_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d.get('alert_mev') else 1)" 2>/dev/null; then
        SVC_DISPLAY=$(echo "$HEARTBEAT_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('service',''))" 2>/dev/null || echo "$SVC_NAME")
        mlog "ALERT: Sending WhatsApp alert for $SVC_NAME (down 30+ min)"
        "$WHATSAPP_SEND" "⚠️ Service down (30+ min): *${SVC_DISPLAY}* — ${DETAILS}" >> "$LOG_FILE" 2>&1 || \
            mlog "WARN: Could not send WhatsApp alert"
    fi

done

mlog "Service monitor complete"
