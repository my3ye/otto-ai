# Debugger Agent Memory

## Bug Patterns

- [webassist_supabase_schema_not_run.md](webassist_supabase_schema_not_run.md) — WebAssist wizard 500: Supabase configured but schema migrations not run
- [oms_mobile_responsiveness_patterns.md](oms_mobile_responsiveness_patterns.md) — OMS mobile layout bugs: double padding, fixed-width two-column layout, hardcoded margins, wrong height calc
- [baileys_double_connect_race.md](baileys_double_connect_race.md) — Baileys WhatsApp double-connect race: liveness monitor calling _sock.end() + start() creates two concurrent connections (symptoms: "Starting service" twice per cycle, AwaitingInitialSync x2)
- [project_athena_routing_bug.md](project_athena_routing_bug.md) — Athena line responding as Otto: admin check ran before account==athena routing, so Mev testing Athena's number got kernel (Otto) responses. Fix: move Athena account check before is_admin() in handler.py
- [smmu_threshold_fallback_missing.md](smmu_threshold_fallback_missing.md) — S-MMU threshold loop silent empty: all slices filtered by similarity threshold but legacy fallback not triggered. Fix: post-loop `if not loaded_ids` guard calling `_load_legacy_context()`
- [athena_outreach_wrong_port.md](athena_outreach_wrong_port.md) — Athena outreach sent from wrong WhatsApp: scripts used port 3001 (Otto/Ottolabs) instead of 3002 (Athena/WebAssist). OMS showed "sent" (curl returned 200) but messages came from wrong number. Fix: update WHATSAPP_URL in send scripts to 3002.
- [rl2f_research_apply_loop_broken.md](rl2f_research_apply_loop_broken.md) — Research pipeline findings never persisted to live config: hardcoded TP/SL in research_pipeline.py + no write-back step for Claude findings. 155 iterations of repeated "targets unreachable" findings. Fix: read TP/SL from config, add structured config_patch output, apply via whitelisted apply_config_patch().
- [oms_task_queue_visibility_gaps.md](oms_task_queue_visibility_gaps.md) — OMS task queue shows incomplete data: zombie tasks (running, no PID) block plans, "Needs Review" stat filter broken (key=completed not reviewed=false), kanban 100-limit hides older tasks, no plan DAG view, WF steps clutter Review column
- [dag_executor_unmet_deps.md](dag_executor_unmet_deps.md) — DAG plan tasks launched before deps complete: /tasks/{id}/run endpoint had no dependency check, heartbeat bypassed plan executor
- [context_loss_triple_bug.md](context_loss_triple_bug.md) — Context loss triple bug: streaming handler had zero history, persistence race on rapid msgs, conversation buried in lost-in-middle zone
