# Reviewer Agent Memory

## Projects
- [project_polkadot_entry_review.md](project_polkadot_entry_review.md) — Polkadot ecosystem entry content stack review (2026-03-20): NEEDS_CHANGES (pre-submission). 10 patterns flagged. No blockers but code evidence gap is critical before W3F submission.

- [universe_page_audit.md](project_universe_page.md) — Universe page at mev.otto.lk/universe audit (2026-03-13): critical name display bug, 8 tasks created for public readiness
- [project_crypto_native.md](project_crypto_native.md) — Native crypto engine Phase 1 review (2026-03-19): NEEDS_CHANGES (minor). 8 patterns flagged for Phase 2 attention. No blockers.
- [project_bankr_oms_frontend.md](project_bankr_oms_frontend.md) — BANKR OMS Crypto Engine frontend review (commit c0e25a3, 2026-03-19): NEEDS_CHANGES (minor). React key on fragment bug, silent error suppression, duplicate fetch.
- [project_secrets_vault.md](project_secrets_vault.md) — OMS Secrets Vault review (2026-03-19): NEEDS_CHANGES. Unauthenticated read on /get/{key_name} for ["*"] secrets; dev-mode auth bypass when web_auth_token empty.
- [project_athena_agent.md](project_athena_agent.md) — Athena WhatsApp agent review (commit a1f37e1, 2026-03-21): NEEDS_CHANGES. Critical episodic_events INSERT uses wrong column names (description/agent_id don't exist, importance=0.9 vs INTEGER). Dead code block in handle_athena_message. Qualified leads will never surface in Otto context.
