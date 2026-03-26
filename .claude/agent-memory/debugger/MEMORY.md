# Debugger Agent Memory

## Bug Patterns

- [webassist_supabase_schema_not_run.md](webassist_supabase_schema_not_run.md) — WebAssist wizard 500: Supabase configured but schema migrations not run
- [oms_mobile_responsiveness_patterns.md](oms_mobile_responsiveness_patterns.md) — OMS mobile layout bugs: double padding, fixed-width two-column layout, hardcoded margins, wrong height calc
- [baileys_double_connect_race.md](baileys_double_connect_race.md) — Baileys WhatsApp double-connect race: liveness monitor calling _sock.end() + start() creates two concurrent connections (symptoms: "Starting service" twice per cycle, AwaitingInitialSync x2)
- [project_athena_routing_bug.md](project_athena_routing_bug.md) — Athena line responding as Otto: admin check ran before account==athena routing, so Mev testing Athena's number got kernel (Otto) responses. Fix: move Athena account check before is_admin() in handler.py
- [smmu_threshold_fallback_missing.md](smmu_threshold_fallback_missing.md) — S-MMU threshold loop silent empty: all slices filtered by similarity threshold but legacy fallback not triggered. Fix: post-loop `if not loaded_ids` guard calling `_load_legacy_context()`
- [athena_outreach_wrong_port.md](athena_outreach_wrong_port.md) — Athena outreach sent from wrong WhatsApp: scripts used port 3001 (Otto/Ottolabs) instead of 3002 (Athena/WebAssist). OMS showed "sent" (curl returned 200) but messages came from wrong number. Fix: update WHATSAPP_URL in send scripts to 3002.
