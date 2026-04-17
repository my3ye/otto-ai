#!/bin/bash
# Otto Task Monitor (Wink pattern — arXiv:2602.17037)
# Asynchronous lightweight monitor that watches task runner logs for misbehavior
# patterns and flags issues early, before the full compute budget is burned.
#
# Usage: task_monitor.sh <task_id> <log_file> <pid>
# Called by task_runner.sh after spawning the CLI process.
# Runs in background, checks log every 30 seconds.

set -euo pipefail

API="http://localhost:8100"
TASK_ID="${1:?Usage: task_monitor.sh <task_id> <log_file> <pid>}"
LOG_FILE="${2:?Missing log_file}"
PID="${3:?Missing pid}"
CHECK_INTERVAL=30  # seconds between checks
MAX_CHECKS=60      # stop after 30 minutes (60 * 30s)
MONITOR_LOG="/home/web3relic/otto/logs/tasks/monitor-${TASK_ID:0:8}.log"

mlog() { echo "$(date -Iseconds) [monitor] $*" >> "$MONITOR_LOG"; }

mlog "Wink monitor started for task ${TASK_ID:0:8} (PID=$PID, log=$LOG_FILE)"

PREV_SIZE=0
STALL_COUNT=0
LOOP_SIGNATURES=""
CHECK_NUM=0

while [ $CHECK_NUM -lt $MAX_CHECKS ]; do
    sleep $CHECK_INTERVAL
    CHECK_NUM=$((CHECK_NUM + 1))

    # Check if process is still running
    if ! kill -0 "$PID" 2>/dev/null; then
        mlog "Task process $PID has exited — monitor stopping"
        break
    fi

    # Check if log file exists
    if [ ! -f "$LOG_FILE" ]; then
        continue
    fi

    CURR_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo "0")

    # ── Pattern 1: Output stall (no new output for 5+ checks = 150s) ──
    if [ "$CURR_SIZE" -eq "$PREV_SIZE" ]; then
        STALL_COUNT=$((STALL_COUNT + 1))
        if [ $STALL_COUNT -eq 5 ]; then
            mlog "WARNING: output stalled for $(($STALL_COUNT * $CHECK_INTERVAL))s"
            # Log single alert (not on every check)
            curl -sf -X POST "${API}/episodic/events" \
                -H 'Content-Type: application/json' \
                -d "{\"content\": \"Wink monitor: task ${TASK_ID:0:8} output stalled for $(($STALL_COUNT * $CHECK_INTERVAL))s. Possible stuck process.\", \"event_type\": \"wink_alert\", \"importance\": 3}" \
                >> "$MONITOR_LOG" 2>&1 || true
        fi
        if [ $STALL_COUNT -ge 10 ]; then
            # 5 minutes of no output — likely stuck
            mlog "ALERT: task stalled for 5+ minutes — flagging for early termination"
            curl -sf -X POST "${API}/episodic/events" \
                -H 'Content-Type: application/json' \
                -d "{\"content\": \"Wink monitor: task ${TASK_ID:0:8} stalled 5+ minutes. Recommending early termination to save budget.\", \"event_type\": \"wink_critical\", \"importance\": 5}" \
                >> "$MONITOR_LOG" 2>&1 || true
            break
        fi
    else
        STALL_COUNT=0
    fi
    PREV_SIZE=$CURR_SIZE

    # ── Pattern 2: Repeated tool failures ──
    TOOL_FAILURES=$(tail -200 "$LOG_FILE" 2>/dev/null | grep -ciE "error:|failed|Error:|FAILED|exception|traceback" 2>/dev/null || echo "0")
    if [ "$TOOL_FAILURES" -gt 10 ]; then
        mlog "WARNING: high error rate in recent output ($TOOL_FAILURES error indicators)"
        curl -sf -X POST "${API}/episodic/events" \
            -H 'Content-Type: application/json' \
            -d "{\"content\": \"Wink monitor: task ${TASK_ID:0:8} showing $TOOL_FAILURES errors in recent output. Possible tool failure loop.\", \"event_type\": \"wink_alert\", \"importance\": 5}" \
            >> "$MONITOR_LOG" 2>&1 || true
    fi

    # ── Pattern 3: Reasoning loops (same phrases repeated) ──
    REPEATED=$(tail -100 "$LOG_FILE" 2>/dev/null | sort | uniq -d | wc -l 2>/dev/null || echo "0")
    if [ "$REPEATED" -gt 15 ]; then
        mlog "WARNING: possible reasoning loop detected ($REPEATED repeated lines in last 100)"
        curl -sf -X POST "${API}/episodic/events" \
            -H 'Content-Type: application/json' \
            -d "{\"content\": \"Wink monitor: task ${TASK_ID:0:8} has $REPEATED repeated output lines. Possible reasoning loop.\", \"event_type\": \"wink_alert\", \"importance\": 5}" \
            >> "$MONITOR_LOG" 2>&1 || true
    fi

    # ── Pattern 4: Budget/turns approaching limit ──
    TURNS_HIT=$(tail -50 "$LOG_FILE" 2>/dev/null | grep -ciE "max.turns|budget.*exceed|Reached max" 2>/dev/null || echo "0")
    if [ "$TURNS_HIT" -gt 0 ]; then
        mlog "INFO: task approaching turn/budget limits"
    fi

done

mlog "Wink monitor finished after $CHECK_NUM checks"
