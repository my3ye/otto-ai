# Debugger Agent Memory

## Bug Patterns

- [webassist_supabase_schema_not_run.md](webassist_supabase_schema_not_run.md) — WebAssist wizard 500: Supabase configured but schema migrations not run
- [oms_mobile_responsiveness_patterns.md](oms_mobile_responsiveness_patterns.md) — OMS mobile layout bugs: double padding, fixed-width two-column layout, hardcoded margins, wrong height calc
- [baileys_double_connect_race.md](baileys_double_connect_race.md) — Baileys WhatsApp double-connect race: liveness monitor calling _sock.end() + start() creates two concurrent connections (symptoms: "Starting service" twice per cycle, AwaitingInitialSync x2)
