---
name: debug-workflow
description: Structured debugging workflow for Otto's services and infrastructure. Auto-loaded when diagnosing errors or failures.
user-invocable: false
---

## Quick Diagnostics

### Service Health
```bash
# All services
systemctl status otto-memory whatsapp 2>/dev/null | grep -E "Active:|●"

# Docker containers (Postgres, Neo4j, Graphiti)
docker ps --format "{{.Names}}: {{.Status}}"

# Memory API
curl -sf http://localhost:8100/health | python3 -m json.tool

# Kernel status
curl -sf http://localhost:8100/kernel/status | python3 -m json.tool
```

### Recent Errors
```bash
# Memory API logs
journalctl -u otto-memory -n 50 --no-pager | grep -iE "error|exception|traceback"

# Latest heartbeat log
ls -t ~/otto/logs/heartbeat-*.log | head -1 | xargs tail -30

# Latest reflection log
ls -t ~/otto/logs/reflection-*.log | head -1 | xargs tail -30

# Failed tasks
curl -sf 'http://localhost:8100/tasks?status=failed&limit=5'
```

### Rate Limit Status
```bash
# Check sentinel
[ -f /tmp/otto-rate-limited ] && echo "RATE LIMITED ($(cat /tmp/otto-rate-limited))" || echo "No rate limit"

# Check API
curl -sf http://localhost:8100/kernel/providers/rate-limited
```

## Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| API 502/503 | otto-memory crashed | `sudo systemctl restart otto-memory` |
| DB connection error | Postgres down | `docker restart memory-postgres-1` |
| WhatsApp not sending | Session expired | Check auth_state, re-link if needed |
| Task exit code 124 | Timeout | Increase timeout or reduce scope |
| Task exit code None | Never started | Check queue status, check lock file |
| Neo4j connection refused | Container down | `docker restart memory-neo4j-1` |
| Graphiti 500 | Neo4j not ready | Restart neo4j first, wait 30s, restart graphiti |

## Debugging Protocol

1. **Reproduce**: Get the exact error message
2. **Locate**: Find which service/file/function failed
3. **Isolate**: Is it this service or a dependency?
4. **Root cause**: Why did it fail, not just what failed
5. **Fix**: Minimal change
6. **Verify**: Confirm the fix works
7. **Prevent**: Add monitoring or validation if appropriate
